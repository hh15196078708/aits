# -*- coding: utf-8 -*-
"""
模块名称: ip_blocker.py
模块功能: IP 自动拉黑管理器

功能说明:
    1. 可配置开关（ip_blocker.enabled），默认关闭
    2. 开启后，对检测到攻击行为的 IP 在防火墙层面执行封禁
    3. 支持服务端下发白名单：白名单内的 IP 不执行封禁，已封禁的自动解封
    4. 跨平台支持：Windows (netsh advfirewall)、Linux (iptables)、macOS (pfctl)
    5. 封禁状态持久化至 client_config.json，程序重启后自动恢复

使用方式:
    from ip_blocker import ip_blocker
    ip_blocker.start()
    ip_blocker.maybe_block_ip("1.2.3.4", "sql_injection", "high")
    ip_blocker.update_whitelist(["10.0.0.0/8", "192.168.1.1"])
    ip_blocker.stop()
"""

import ipaddress
import subprocess
import sys
import threading
from typing import List, Optional, Set

from config_manager import config_manager
from constants import (
    ATTACK_LEVEL_HIGH,
    ATTACK_LEVEL_LOW,
    ATTACK_LEVEL_MEDIUM,
    IP_BLOCKER_BLOCK_OUTBOUND,
    IP_BLOCKER_ENABLED,
    IP_BLOCKER_MIN_ATTACK_LEVEL,
    IP_BLOCKER_RULE_NAME_PREFIX,
    IP_BLOCKER_WHITELIST_SYNC_INTERVAL,
)
from logger import logger

# 攻击级别排序（用于最低级别过滤）
_LEVEL_ORDER = {
    ATTACK_LEVEL_LOW:    0,
    ATTACK_LEVEL_MEDIUM: 1,
    ATTACK_LEVEL_HIGH:   2,
}


class IPBlocker:
    """
    IP 自动拉黑管理器（单例）

    职责:
        - 维护内存中的白名单和已封禁IP集合
        - 对符合条件的攻击IP调用平台防火墙命令进行封禁
        - 定期从服务端同步白名单，并对新白名单中已封禁的IP自动解封
        - 封禁状态持久化，程序重启后在非 Windows 平台重新应用防火墙规则
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if IPBlocker._initialized:
            return

        self._enabled: bool = IP_BLOCKER_ENABLED
        self._running: bool = False
        self._stop_event = threading.Event()

        # 白名单：精确IP或CIDR网段字符串集合
        self._whitelist: Set[str] = set()
        self._whitelist_lock = threading.Lock()

        # 已封禁IP集合（精确IP）
        self._blocked_ips: Set[str] = set()
        self._blocked_lock = threading.Lock()

        # 白名单同步线程
        self._sync_thread: Optional[threading.Thread] = None

        # 最低触发封禁的攻击级别
        self._min_level_order: int = _LEVEL_ORDER.get(IP_BLOCKER_MIN_ATTACK_LEVEL, 0)

        # 平台标识
        self._platform: str = sys.platform  # 'win32' | 'linux' | 'darwin'

        # 从配置文件恢复持久化状态
        self._load_persisted_state()

        IPBlocker._initialized = True

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def start(self) -> bool:
        """
        启动 IP 拉黑功能。
        - 立即执行一次白名单同步
        - 在非 Windows 平台重新应用已持久化的封禁规则
        - 启动后台白名单同步线程

        返回: True=成功启动，False=功能已禁用
        """
        if not self._enabled:
            logger.info("IP拉黑功能已禁用（ip_blocker.enabled=false），跳过启动")
            return False

        if self._running:
            return True

        self._running = True
        self._stop_event.clear()

        # 非 Windows 平台在重启后防火墙规则会丢失，需要重新应用
        if self._platform != "win32":
            self._reapply_blocked_ips()

        # 立即同步一次白名单
        self._sync_whitelist()

        # 启动后台白名单同步线程
        self._sync_thread = threading.Thread(
            target=self._whitelist_sync_loop,
            name="IPBlockerWhitelistSync",
            daemon=True,
        )
        self._sync_thread.start()

        with self._blocked_lock:
            blocked_count = len(self._blocked_ips)
        with self._whitelist_lock:
            whitelist_count = len(self._whitelist)

        logger.info(
            f"IP拉黑功能已启动（平台: {self._platform}，"
            f"已封禁: {blocked_count} 个IP，白名单: {whitelist_count} 条）"
        )
        return True

    def stop(self) -> None:
        """停止 IP 拉黑功能（不解除已封禁的IP）"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=3)

        logger.info("IP拉黑功能已停止")

    # ------------------------------------------------------------------
    # 主接口
    # ------------------------------------------------------------------

    def maybe_block_ip(self, ip: str, attack_type: str = "",
                       level: str = ATTACK_LEVEL_LOW) -> bool:
        """
        判断并（可能）封禁攻击来源IP。

        参数:
            ip:          攻击来源IP地址
            attack_type: 攻击类型（仅用于日志记录）
            level:       攻击级别（low/medium/high）

        返回:
            True  = 已触发封禁
            False = 未触发（功能关闭/白名单/级别不达标/已封禁/IP无效）
        """
        if not self._enabled:
            return False

        if not ip or not self._is_valid_ip(ip):
            return False

        # 级别过滤
        if _LEVEL_ORDER.get(level, 0) < self._min_level_order:
            return False

        # 白名单检查
        if self.is_whitelisted(ip):
            logger.debug(f"IP {ip} 在白名单中，跳过封禁")
            return False

        # 去重：已封禁则跳过
        with self._blocked_lock:
            if ip in self._blocked_ips:
                return False

        # 执行防火墙封禁
        success = self._block_ip_in_firewall(ip)
        if success:
            with self._blocked_lock:
                self._blocked_ips.add(ip)
            self._persist_blocked_ips()
            logger.info(
                f"已封禁攻击IP: {ip}（类型: {attack_type}，级别: {level}）"
            )
        else:
            logger.warning(f"封禁IP {ip} 失败（可能权限不足或防火墙不可用）")

        return success

    def is_whitelisted(self, ip: str) -> bool:
        """
        检查IP是否在白名单中。
        支持精确IP匹配和CIDR网段匹配（如 10.0.0.0/8）。
        """
        with self._whitelist_lock:
            if ip in self._whitelist:
                return True
            try:
                ip_obj = ipaddress.ip_address(ip)
                for entry in self._whitelist:
                    if "/" in entry:
                        try:
                            if ip_obj in ipaddress.ip_network(entry, strict=False):
                                return True
                        except ValueError:
                            pass
            except ValueError:
                pass
        return False

    def update_whitelist(self, ips: List[str]) -> None:
        """
        更新白名单（由服务端下发）。

        - 替换当前白名单
        - 对已在白名单中但仍被封禁的IP自动解封
        - 持久化新白名单
        """
        new_whitelist: Set[str] = set()
        for entry in ips:
            entry = entry.strip()
            if entry:
                new_whitelist.add(entry)

        with self._whitelist_lock:
            self._whitelist = new_whitelist

        config_manager.set_ip_whitelist(list(new_whitelist))

        # 对白名单中已封禁的IP执行解封
        with self._blocked_lock:
            to_unblock = [ip for ip in self._blocked_ips
                          if self._ip_in_set(ip, new_whitelist)]

        for ip in to_unblock:
            self._unblock_ip_in_firewall(ip)
            with self._blocked_lock:
                self._blocked_ips.discard(ip)
            logger.info(f"IP {ip} 已加入白名单，已自动解封")

        if to_unblock:
            self._persist_blocked_ips()

        logger.info(f"IP白名单已更新，共 {len(new_whitelist)} 条，解封 {len(to_unblock)} 个IP")

    def set_enabled(self, enabled: bool) -> None:
        """
        动态开启或关闭IP自动拉黑功能（服务端下发指令时调用）。

        - 开启时：若当前未在运行，自动调用 start()
        - 关闭时：停止后台白名单同步线程，不解除已封禁的IP
        """
        self._enabled = enabled
        if enabled and not self._running:
            self.start()
        elif not enabled and self._running:
            self._running = False
            self._stop_event.set()
            if self._sync_thread and self._sync_thread.is_alive():
                self._sync_thread.join(timeout=3)
            self._stop_event.clear()
        logger.info(f"IP自动拉黑功能已{'开启' if enabled else '关闭'}")

    def force_block_ip(self, ip: str) -> bool:
        """
        强制封禁指定IP（服务端下发封禁指令时调用）。

        与 maybe_block_ip 的区别：
        - 不检查 _enabled 标志（服务端指令优先）
        - 不检查攻击级别
        - 仍然检查白名单（白名单内的IP不封禁）

        参数:
            ip: 要封禁的IP地址

        返回:
            True  = 封禁成功或已封禁
            False = IP无效、在白名单中或防火墙操作失败
        """
        if not ip or not self._is_valid_ip(ip):
            logger.warning(f"force_block_ip: 无效的IP地址 '{ip}'")
            return False

        # 白名单检查（仍然遵守白名单）
        if self.is_whitelisted(ip):
            logger.warning(f"IP {ip} 在白名单中，忽略服务端封禁指令")
            return False

        # 去重：已封禁则返回 True
        with self._blocked_lock:
            if ip in self._blocked_ips:
                return True

        # 执行防火墙封禁
        success = self._block_ip_in_firewall(ip)
        if success:
            with self._blocked_lock:
                self._blocked_ips.add(ip)
            self._persist_blocked_ips()
            logger.info(f"已按服务端指令封禁IP: {ip}")
        else:
            logger.warning(f"按服务端指令封禁IP {ip} 失败（可能权限不足）")

        return success

    def get_status(self) -> dict:
        """返回当前封禁状态摘要"""
        with self._blocked_lock:
            blocked_list = list(self._blocked_ips)
        with self._whitelist_lock:
            whitelist_count = len(self._whitelist)
        return {
            "enabled":         self._enabled,
            "running":         self._running,
            "blocked_count":   len(blocked_list),
            "blocked_ips":     blocked_list,
            "whitelist_count": whitelist_count,
        }

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ------------------------------------------------------------------
    # 防火墙操作（平台分发）
    # ------------------------------------------------------------------

    def _block_ip_in_firewall(self, ip: str) -> bool:
        """根据平台调用对应防火墙命令封禁IP"""
        try:
            if self._platform == "win32":
                return self._block_windows(ip)
            elif self._platform.startswith("linux"):
                return self._block_linux(ip)
            elif self._platform == "darwin":
                return self._block_macos(ip)
            else:
                logger.warning(f"不支持的平台 '{self._platform}'，无法执行IP封禁")
                return False
        except Exception as e:
            logger.error(f"封禁IP {ip} 时发生异常: {e}")
            return False

    def _unblock_ip_in_firewall(self, ip: str) -> bool:
        """根据平台调用对应防火墙命令解封IP"""
        try:
            if self._platform == "win32":
                return self._unblock_windows(ip)
            elif self._platform.startswith("linux"):
                return self._unblock_linux(ip)
            elif self._platform == "darwin":
                return self._unblock_macos(ip)
            else:
                return False
        except Exception as e:
            logger.error(f"解封IP {ip} 时发生异常: {e}")
            return False

    # ---- Windows (netsh advfirewall) ----------------------------------------

    def _block_windows(self, ip: str) -> bool:
        """
        Windows 防火墙封禁：先删除同名规则（幂等），再添加 BLOCK 规则。
        规则名格式：SafeClient_Block_IN_<IP>
        """
        rule_in = f"{IP_BLOCKER_RULE_NAME_PREFIX}IN_{ip}"
        try:
            # 先尝试删除（保证幂等，忽略失败）
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule",
                 f"name={rule_in}"],
                capture_output=True, timeout=10
            )
            # 添加入站封禁规则
            ret = subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name={rule_in}", "dir=in", "action=block",
                 f"remoteip={ip}", "enable=yes"],
                capture_output=True, timeout=10
            )
            if ret.returncode != 0:
                return False

            if IP_BLOCKER_BLOCK_OUTBOUND:
                rule_out = f"{IP_BLOCKER_RULE_NAME_PREFIX}OUT_{ip}"
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "delete", "rule",
                     f"name={rule_out}"],
                    capture_output=True, timeout=10
                )
                subprocess.run(
                    ["netsh", "advfirewall", "firewall", "add", "rule",
                     f"name={rule_out}", "dir=out", "action=block",
                     f"remoteip={ip}", "enable=yes"],
                    capture_output=True, timeout=10
                )
            return True
        except Exception as e:
            logger.error(f"Windows封禁IP {ip} 失败: {e}")
            return False

    def _unblock_windows(self, ip: str) -> bool:
        """删除 Windows 防火墙中对应的封禁规则"""
        rule_in  = f"{IP_BLOCKER_RULE_NAME_PREFIX}IN_{ip}"
        rule_out = f"{IP_BLOCKER_RULE_NAME_PREFIX}OUT_{ip}"
        try:
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule",
                 f"name={rule_in}"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule",
                 f"name={rule_out}"],
                capture_output=True, timeout=10
            )
            return True
        except Exception as e:
            logger.error(f"Windows解封IP {ip} 失败: {e}")
            return False

    # ---- Linux (iptables) ---------------------------------------------------

    def _block_linux(self, ip: str) -> bool:
        """
        Linux iptables 封禁：使用 -C 检查规则是否已存在，避免重复添加。
        """
        try:
            # 检查入站规则是否已存在
            check_in = subprocess.run(
                ["iptables", "-C", "INPUT", "-s", ip, "-j", "DROP"],
                capture_output=True, timeout=5
            )
            if check_in.returncode != 0:
                ret = subprocess.run(
                    ["iptables", "-I", "INPUT", "-s", ip, "-j", "DROP"],
                    capture_output=True, timeout=10
                )
                if ret.returncode != 0:
                    return False

            if IP_BLOCKER_BLOCK_OUTBOUND:
                check_out = subprocess.run(
                    ["iptables", "-C", "OUTPUT", "-d", ip, "-j", "DROP"],
                    capture_output=True, timeout=5
                )
                if check_out.returncode != 0:
                    subprocess.run(
                        ["iptables", "-I", "OUTPUT", "-d", ip, "-j", "DROP"],
                        capture_output=True, timeout=10
                    )
            return True
        except Exception as e:
            logger.error(f"Linux封禁IP {ip} 失败: {e}")
            return False

    def _unblock_linux(self, ip: str) -> bool:
        """Linux iptables 解封"""
        try:
            subprocess.run(
                ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"],
                capture_output=True, timeout=10
            )
            subprocess.run(
                ["iptables", "-D", "OUTPUT", "-d", ip, "-j", "DROP"],
                capture_output=True, timeout=10
            )
            return True
        except Exception as e:
            logger.error(f"Linux解封IP {ip} 失败: {e}")
            return False

    # ---- macOS (pfctl) ------------------------------------------------------

    def _block_macos(self, ip: str) -> bool:
        """
        macOS pfctl 封禁：将全部需要封禁的IP写入 anchor 文件后加载。
        """
        try:
            anchor_file = "/tmp/safeclient_blocked.conf"
            with self._blocked_lock:
                all_blocked = set(self._blocked_ips) | {ip}
            rules = "".join(
                f"block in quick from {b} to any\n" for b in all_blocked
            )
            with open(anchor_file, "w") as f:
                f.write(rules)
            ret = subprocess.run(
                ["pfctl", "-a", "SafeClient", "-f", anchor_file],
                capture_output=True, timeout=10
            )
            return ret.returncode == 0
        except Exception as e:
            logger.error(f"macOS封禁IP {ip} 失败: {e}")
            return False

    def _unblock_macos(self, ip: str) -> bool:
        """macOS pfctl 解封：重新生成 anchor 规则（排除指定IP）"""
        try:
            anchor_file = "/tmp/safeclient_blocked.conf"
            with self._blocked_lock:
                remaining = self._blocked_ips - {ip}
            if remaining:
                rules = "".join(
                    f"block in quick from {b} to any\n" for b in remaining
                )
                with open(anchor_file, "w") as f:
                    f.write(rules)
                subprocess.run(
                    ["pfctl", "-a", "SafeClient", "-f", anchor_file],
                    capture_output=True, timeout=10
                )
            else:
                # 无剩余规则，清空 anchor
                subprocess.run(
                    ["pfctl", "-a", "SafeClient", "-F", "rules"],
                    capture_output=True, timeout=10
                )
            return True
        except Exception as e:
            logger.error(f"macOS解封IP {ip} 失败: {e}")
            return False

    # ------------------------------------------------------------------
    # 白名单同步
    # ------------------------------------------------------------------

    def _whitelist_sync_loop(self) -> None:
        """后台线程：每隔 IP_BLOCKER_WHITELIST_SYNC_INTERVAL 秒从服务端拉取白名单"""
        while not self._stop_event.is_set():
            self._stop_event.wait(IP_BLOCKER_WHITELIST_SYNC_INTERVAL)
            if not self._stop_event.is_set():
                self._sync_whitelist()

    def _sync_whitelist(self) -> None:
        """从服务端拉取最新白名单并更新本地"""
        try:
            from network_client import network_client
            client_id = config_manager.get_client_id()
            if not client_id:
                return
            success, whitelist_ips, error = network_client.fetch_ip_whitelist(client_id)
            if success and whitelist_ips is not None:
                self.update_whitelist(whitelist_ips)
            elif not success:
                logger.debug(f"白名单同步失败: {error}")
        except Exception as e:
            logger.debug(f"白名单同步异常: {e}")

    # ------------------------------------------------------------------
    # 启动时重新应用已持久化的封禁规则（针对 Linux/macOS）
    # ------------------------------------------------------------------

    def _reapply_blocked_ips(self) -> None:
        """
        程序重启后，Linux/macOS 防火墙规则会丢失，需要重新应用。
        同时检查持久化列表中的IP是否已在白名单中（若在则跳过并从列表移除）。
        """
        with self._blocked_lock:
            blocked_copy = list(self._blocked_ips)

        if not blocked_copy:
            return

        still_blocked = []
        for ip in blocked_copy:
            if self.is_whitelisted(ip):
                # 已在白名单，不再封禁
                logger.info(f"IP {ip} 在白名单中，跳过重新封禁")
                continue
            if self._block_ip_in_firewall(ip):
                still_blocked.append(ip)
            else:
                logger.warning(f"重新应用封禁规则失败: {ip}")

        with self._blocked_lock:
            self._blocked_ips = set(still_blocked)

        if still_blocked:
            logger.info(f"已重新应用 {len(still_blocked)} 个IP的封禁规则")
        self._persist_blocked_ips()

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def _load_persisted_state(self) -> None:
        """从 config_manager 恢复白名单和已封禁IP"""
        try:
            whitelist = config_manager.get_ip_whitelist()
            if whitelist:
                with self._whitelist_lock:
                    self._whitelist = set(whitelist)

            blocked = config_manager.get_blocked_ips()
            if blocked:
                with self._blocked_lock:
                    self._blocked_ips = set(blocked)
        except Exception:
            pass

    def _persist_blocked_ips(self) -> None:
        """将已封禁IP列表持久化到 client_config.json"""
        try:
            with self._blocked_lock:
                blocked_copy = list(self._blocked_ips)
            config_manager.set_blocked_ips(blocked_copy)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """检查字符串是否为合法的IP地址"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def _ip_in_set(ip: str, ip_set: Set[str]) -> bool:
        """检查IP是否属于集合（支持精确匹配和CIDR匹配）"""
        if ip in ip_set:
            return True
        try:
            ip_obj = ipaddress.ip_address(ip)
            for entry in ip_set:
                if "/" in entry:
                    try:
                        if ip_obj in ipaddress.ip_network(entry, strict=False):
                            return True
                    except ValueError:
                        pass
        except ValueError:
            pass
        return False


# 全局单例
ip_blocker = IPBlocker()
