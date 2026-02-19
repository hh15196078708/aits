# -*- coding: utf-8 -*-
"""
实战测试: test_port_scan_live.py
功    能: 在本机演示完整的「端口扫描 → 检测 → 告警」全流程

原    理:
    1. 在本机随机端口上开启若干 TCP 监听（模拟真实服务器的开放端口）
    2. 启动「扫描模拟器」线程：向本机发起多端口 TCP 连接（模拟外部攻击者）
    3. 检测引擎实时统计扫描行为，超过阈值后输出告警
    4. 扫描结束后打印完整检测报告

不依赖:
    - psutil（可选，若已安装则额外运行一次真实连接监控验证）
    - scapy（可选，需管理员权限才会启动）
    - 服务端（完全离线可用）

运    行:
    python test_port_scan_live.py
"""

import sys
import os
import time
import socket
import threading
import queue
import platform
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logger import logger  # 使用与主程序相同的 logger，输出到同一日志文件
from port_scan_detector import (
    SlidingWindowTracker,
    PortScanEvent,
    _classify_scan_level,
    _is_admin,
    PSUTIL_AVAILABLE,
    SCAPY_AVAILABLE,
)
from constants import (
    ATTACK_LEVEL_LOW,
    ATTACK_LEVEL_MEDIUM,
    ATTACK_LEVEL_HIGH,
    DEFAULT_THRESHOLDS,
)

# ── 颜色输出（Windows CMD 需 Python 3.12 或 colorama，不支持则退化为纯文字） ──
try:
    import colorama
    colorama.init(autoreset=True)
    RED    = "\033[91m"
    YELLOW = "\033[93m"
    GREEN  = "\033[92m"
    CYAN   = "\033[96m"
    BOLD   = "\033[1m"
    RESET  = "\033[0m"
except ImportError:
    RED = YELLOW = GREEN = CYAN = BOLD = RESET = ""


# ===========================================================================
# 工具函数
# ===========================================================================

def _banner(text: str):
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  {text}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")


def _step(n: int, text: str):
    print(f"\n{CYAN}[步骤 {n}]{RESET} {text}")


def _ok(text: str):
    print(f"  {GREEN}✓{RESET}  {text}")


def _warn(text: str):
    print(f"  {YELLOW}⚠{RESET}  {text}")


def _alert(text: str):
    print(f"\n{RED}{BOLD}  !! 告警 !! {text}{RESET}")


def _info(text: str):
    print(f"       {text}")


def _get_free_ports(count: int) -> list:
    """随机获取 count 个可用端口"""
    ports = []
    socks = []
    for _ in range(count):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        ports.append(s.getsockname()[1])
        socks.append(s)
    for s in socks:
        s.close()
    return ports


# ===========================================================================
# 核心组件：在线检测引擎（不依赖 psutil）
# ===========================================================================

class LiveDetectionEngine:
    """
    实时端口扫描检测引擎

    工作方式：
        外部代码（服务端/扫描器）调用 record(src_ip, dst_port) 汇报连接事件，
        引擎维护滑动时间窗口并在超阈值时触发告警回调。

    与 ConnectionBasedDetector 的区别：
        - 不依赖 psutil
        - 不过滤本机IP（适合本地测试）
        - 可由任意来源（accept 回调、socket hook 等）驱动
    """

    def __init__(self, port_threshold: int = 20, time_window: float = 10.0):
        self.threshold = port_threshold
        self.time_window = time_window
        self._tracker = SlidingWindowTracker(time_window)
        self._reported: dict = {}           # src_ip -> last_alert_time
        self._report_cooldown = 30.0
        self._lock = threading.Lock()
        self.alert_callbacks = []           # Callable[[PortScanEvent], None]

    def record(self, src_ip: str, dst_port: int) -> bool:
        """
        记录一次连接事件，超阈值时触发告警。
        返回 True 表示本次记录导致了新告警。
        """
        ports_in_window = self._tracker.record(src_ip, dst_port)
        count = len(ports_in_window)

        if count < self.threshold:
            return False

        now = time.time()
        with self._lock:
            if now - self._reported.get(src_ip, 0) < self._report_cooldown:
                return False
            self._reported[src_ip] = now

        level = _classify_scan_level(count, self.threshold)
        event = PortScanEvent(
            source_ip=src_ip,
            target_ports=ports_in_window.copy(),
            scan_type="connect_scan",
            start_time=now - self.time_window,
            end_time=now,
            port_count=count,
            level=level,
            detection_method="live_test",
        )

        # 与主程序使用同一 logger，输出到日志文件和控制台
        logger.warning(
            f"[端口扫描告警] "
            f"源IP={src_ip} "
            f"扫描类型=connect_scan "
            f"端口数={count} "
            f"威胁等级={level} "
            f"检测方法=live_test"
        )

        for cb in self.alert_callbacks:
            try:
                cb(event)
            except Exception:
                pass
        return True

    def get_current_count(self, src_ip: str) -> int:
        """查询某IP当前窗口内的扫描端口数"""
        return len(self._tracker.get_ports(src_ip))


# ===========================================================================
# 核心组件：TCP 监听服务器（在 accept 时汇报到检测引擎）
# ===========================================================================

class ScanTargetServer:
    """
    模拟被扫描的服务器，在每次接受 TCP 连接时通知检测引擎。
    每个端口一个实例，运行在独立守护线程中。
    """

    def __init__(self, port: int, engine: LiveDetectionEngine):
        self.port = port
        self.engine = engine
        self._sock = None
        self._stop = threading.Event()

    def start(self) -> bool:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", self.port))
            s.listen(64)
            s.settimeout(0.3)
            self._sock = s
            t = threading.Thread(target=self._loop, daemon=True)
            t.start()
            return True
        except OSError:
            return False

    def _loop(self):
        while not self._stop.is_set():
            try:
                conn, addr = self._sock.accept()
                remote_ip = addr[0]
                # 汇报给检测引擎：src_ip 访问了 self.port
                self.engine.record(remote_ip, self.port)
                conn.close()
            except socket.timeout:
                continue
            except Exception:
                break

    def stop(self):
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass


# ===========================================================================
# 核心组件：端口扫描模拟器
# ===========================================================================

class PortScanSimulator:
    """
    模拟外部攻击者对本机发起端口扫描。

    策略:
        - connect_scan: 标准 TCP 全连接扫描（默认）
        - 可配置并发线程数和扫描速率
    """

    def __init__(self, target: str = "127.0.0.1", timeout: float = 0.15,
                 workers: int = 10):
        self.target = target
        self.timeout = timeout
        self.workers = workers
        self.results = {"open": [], "closed": [], "error": []}
        self._lock = threading.Lock()

    def scan(self, ports: list,
             on_attempt=None,
             progress_cb=None) -> dict:
        """
        扫描给定端口列表。

        参数:
            ports:       要扫描的端口号列表
            on_attempt:  每次连接尝试后的回调 on_attempt(port, success)
            progress_cb: 进度回调 progress_cb(done, total)
        """
        self.results = {"open": [], "closed": [], "error": []}
        task_q = queue.Queue()
        for p in ports:
            task_q.put(p)

        done_count = [0]
        total = len(ports)

        def worker():
            while True:
                try:
                    port = task_q.get_nowait()
                except queue.Empty:
                    break
                success = False
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(self.timeout)
                    err = s.connect_ex((self.target, port))
                    success = (err == 0)
                    s.close()
                    with self._lock:
                        if success:
                            self.results["open"].append(port)
                        else:
                            self.results["closed"].append(port)
                except Exception:
                    with self._lock:
                        self.results["error"].append(port)
                finally:
                    task_q.task_done()

                if on_attempt:
                    on_attempt(port, success)
                with self._lock:
                    done_count[0] += 1
                if progress_cb:
                    progress_cb(done_count[0], total)

        threads = [threading.Thread(target=worker, daemon=True)
                   for _ in range(min(self.workers, len(ports)))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return self.results


# ===========================================================================
# 测试场景
# ===========================================================================

class PortScanLiveTest:
    """端口扫描检测实战测试主控"""

    # 测试参数（低于生产阈值，方便本地快速复现）
    PORT_THRESHOLD = 15      # 触发告警所需的最少端口数
    TIME_WINDOW    = 10.0    # 滑动窗口（秒）
    NUM_OPEN_PORTS = 20      # 在本机开启的监听端口数量
    SCAN_EXTRA     = 80      # 额外扫描的关闭端口数（制造更真实的场景）
    ATTACKER_IP    = "127.0.0.1"  # 扫描源（本机回环，不过滤）
    SCAN_WORKERS   = 20      # 并发扫描线程数

    def __init__(self):
        self.engine = LiveDetectionEngine(
            port_threshold=self.PORT_THRESHOLD,
            time_window=self.TIME_WINDOW,
        )
        self.servers: list[ScanTargetServer] = []
        self.listen_ports: list[int] = []
        self.alerts: list[PortScanEvent] = []
        self._alert_lock = threading.Lock()

        # 注册告警回调
        self.engine.alert_callbacks.append(self._on_alert)

    # ── 告警处理 ────────────────────────────────────────────────────────────

    def _on_alert(self, event: PortScanEvent):
        with self._alert_lock:
            self.alerts.append(event)
        level_color = {
            ATTACK_LEVEL_LOW: YELLOW,
            ATTACK_LEVEL_MEDIUM: YELLOW,
            ATTACK_LEVEL_HIGH: RED,
        }.get(event.level, YELLOW)

        _alert(
            f"检测到端口扫描！"
            f"  来源IP={event.source_ip}"
            f"  扫描端口数={event.port_count}"
            f"  威胁等级={level_color}{event.level.upper()}{RESET}"
        )
        sample = sorted(event.target_ports)[:10]
        _info(f"部分扫描端口: {sample}{'...' if len(event.target_ports) > 10 else ''}")

    # ── 场景一：基础扫描检测 ─────────────────────────────────────────────────

    def run_basic_scan_test(self):
        _banner("场景一：基础端口扫描检测（connect_scan）")

        # 步骤1：开启监听端口
        _step(1, f"在本机开启 {self.NUM_OPEN_PORTS} 个 TCP 监听端口（模拟服务器）")
        self.listen_ports = _get_free_ports(self.NUM_OPEN_PORTS)
        for port in self.listen_ports:
            srv = ScanTargetServer(port, self.engine)
            if srv.start():
                self.servers.append(srv)
        _ok(f"已开启 {len(self.servers)} 个监听端口")
        _info(f"端口列表（前10个）: {sorted(self.listen_ports)[:10]}")

        # 构造扫描端口列表：开放端口 + 关闭端口混合
        closed_ports = []
        base = random.randint(20000, 50000)
        for p in range(base, base + self.SCAN_EXTRA):
            if p not in self.listen_ports:
                closed_ports.append(p)
        scan_ports = self.listen_ports + closed_ports[:self.SCAN_EXTRA]
        random.shuffle(scan_ports)

        # 步骤2：执行端口扫描
        _step(2, f"启动扫描模拟器，扫描 {len(scan_ports)} 个端口 "
                 f"（{len(self.listen_ports)} 开放 + {len(closed_ports[:self.SCAN_EXTRA])} 关闭）")
        print(f"  并发线程: {self.SCAN_WORKERS}  超时: 0.15s  目标: {self.ATTACKER_IP}")

        start_time = time.time()
        simulator = PortScanSimulator(
            target="127.0.0.1",
            timeout=0.15,
            workers=self.SCAN_WORKERS,
        )

        # 进度显示
        progress_bar = [""] * 1
        def show_progress(done, total):
            pct = done * 100 // total
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r  扫描进度 [{bar}] {pct:3d}%  ({done}/{total})", end="", flush=True)

        results = simulator.scan(scan_ports, progress_cb=show_progress)
        elapsed = time.time() - start_time
        print()  # 换行

        # 步骤3：等待检测引擎处理（服务端接受连接需要少许时间）
        _step(3, "等待检测引擎完成告警判定...")
        time.sleep(0.5)

        # 打印扫描结果
        _ok(f"扫描完成，耗时 {elapsed:.2f}s")
        _info(f"开放端口: {len(results['open'])} 个")
        _info(f"关闭端口: {len(results['closed'])} 个")
        _info(f"检测器窗口内已记录端口数: "
              f"{self.engine.get_current_count(self.ATTACKER_IP)}")

        # 步骤4：验证检测结果
        _step(4, "检测结果验证")
        with self._alert_lock:
            alert_count = len(self.alerts)

        if alert_count > 0:
            _ok(f"检测成功！共触发 {alert_count} 次告警")
            for i, ev in enumerate(self.alerts, 1):
                _info(f"告警 #{i}: 来源={ev.source_ip}  端口数={ev.port_count}  "
                      f"等级={ev.level}  方式={ev.detection_method}")
        else:
            current = self.engine.get_current_count(self.ATTACKER_IP)
            _warn(f"未触发告警（当前窗口内记录 {current} 个端口，阈值 {self.PORT_THRESHOLD}）")
            _info("提示: 可能原因 —— 开放端口太少被检测器接收，"
                  "可适当降低 PORT_THRESHOLD 或增加 NUM_OPEN_PORTS")

        # 清理
        self._stop_servers()
        return alert_count > 0

    # ── 场景二：渐进式扫描（验证滑动窗口） ──────────────────────────────────

    def run_gradual_scan_test(self):
        _banner("场景二：渐进式扫描 & 滑动时间窗口验证")

        engine2 = LiveDetectionEngine(port_threshold=10, time_window=5.0)
        alerts2 = []
        engine2.alert_callbacks.append(
            lambda e: alerts2.append(e) or _alert(
                f"[渐进扫描] 检测到扫描！端口数={e.port_count} 等级={e.level}"
            )
        )

        _step(1, "模拟慢速扫描：每 0.3s 扫描一个端口，共 15 个")
        print(f"  检测阈值: 10 端口 / 5 秒时间窗口")

        for i, port in enumerate(range(9000, 9015), 1):
            engine2.record("203.0.113.1", port)
            current = engine2.get_current_count("203.0.113.1")
            bar = "▌" * current + " " * (15 - current)
            print(f"\r  [{bar}] 已记录 {current:2d}/10 端口（端口 {port}）", end="", flush=True)
            time.sleep(0.3)

        print()
        time.sleep(0.2)

        if alerts2:
            _ok(f"渐进扫描检测成功，触发 {len(alerts2)} 次告警")
        else:
            _warn("渐进扫描未触发告警（检查阈值配置）")

        _step(2, "等待时间窗口过期（5 秒）后确认状态重置...")
        for remaining in range(5, 0, -1):
            print(f"\r  倒计时 {remaining}s ...", end="", flush=True)
            time.sleep(1)
        print()

        count_after = engine2.get_current_count("203.0.113.1")
        if count_after == 0:
            _ok(f"时间窗口已过期，记录清零（当前计数: {count_after}）")
        else:
            _warn(f"窗口内仍有 {count_after} 条记录（窗口可能尚未完全过期）")

        return len(alerts2) > 0

    # ── 场景三：多IP并发扫描 ────────────────────────────────────────────────

    def run_multi_ip_test(self):
        _banner("场景三：多攻击者并发扫描（IP 独立追踪）")

        engine3 = LiveDetectionEngine(port_threshold=10, time_window=10.0)
        alerts3 = {}

        def on_alert(e):
            alerts3[e.source_ip] = e
            _alert(f"来源 {e.source_ip} 扫描了 {e.port_count} 个端口（{e.level}）")

        engine3.alert_callbacks.append(on_alert)

        attackers = {
            "10.0.0.1": list(range(7000, 7025)),   # 25 个端口 → HIGH
            "10.0.0.2": list(range(7100, 7112)),   # 12 个端口 → LOW
            "10.0.0.3": list(range(7200, 7207)),   # 7 个端口  → 不触发
        }

        _step(1, f"模拟 {len(attackers)} 个攻击者并发扫描")

        threads = []
        for ip, ports in attackers.items():
            def worker(ip=ip, ports=ports):
                for p in ports:
                    engine3.record(ip, p)
                    time.sleep(0.02)
            t = threading.Thread(target=worker, daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        time.sleep(0.2)
        _step(2, "检测结果")
        for ip, ports in attackers.items():
            count = engine3.get_current_count(ip)
            detected = ip in alerts3
            status = f"{GREEN}已检测{RESET}" if detected else f"{YELLOW}未达阈值{RESET}"
            print(f"  {ip}  扫描了 {len(ports):2d} 个端口  {status}")

        expected_detected = {"10.0.0.1", "10.0.0.2"}
        expected_not = {"10.0.0.3"}
        ok = (expected_detected.issubset(set(alerts3.keys())) and
              not expected_not.intersection(set(alerts3.keys())))
        if ok:
            _ok("多IP独立追踪验证通过")
        else:
            _warn(f"结果与预期不符，实际检测到: {set(alerts3.keys())}")

        return ok

    # ── psutil 真实连接验证（如果可用） ─────────────────────────────────────

    def run_psutil_test(self):
        if not PSUTIL_AVAILABLE:
            _warn("psutil 未安装，跳过真实连接监控测试")
            _info("安装命令: pip install psutil")
            return None

        _banner("场景四：psutil 真实连接监控（需已安装 psutil）")

        import psutil

        engine4 = LiveDetectionEngine(port_threshold=8, time_window=10.0)
        alerts4 = []
        engine4.alert_callbacks.append(
            lambda e: alerts4.append(e) or _alert(
                f"[psutil] 检测到来自 {e.source_ip} 的扫描，端口数={e.port_count}"
            )
        )

        # 开启监听端口
        ports = _get_free_ports(12)
        servers = []
        for p in ports:
            srv = ScanTargetServer(p, engine4)
            if srv.start():
                servers.append(srv)

        _step(1, f"已开启 {len(servers)} 个监听端口，开始真实连接扫描")

        simulator = PortScanSimulator(target="127.0.0.1", timeout=0.15, workers=15)
        results = simulator.scan(ports)
        time.sleep(0.5)

        # 同时用 psutil 轮询验证（独立统计）
        psutil_engine = LiveDetectionEngine(port_threshold=8, time_window=10.0)
        psutil_alerts = []
        psutil_engine.alert_callbacks.append(
            lambda e: psutil_alerts.append(e)
        )

        try:
            conns = psutil.net_connections(kind="tcp")
            for conn in conns:
                if conn.laddr and conn.raddr:
                    if conn.laddr.port in ports:
                        psutil_engine.record(conn.raddr.ip, conn.laddr.port)
        except Exception as e:
            _warn(f"psutil.net_connections() 异常: {e}")

        for srv in servers:
            srv.stop()

        _ok(f"服务端检测告警: {len(alerts4)} 次")
        _ok(f"psutil 检测告警: {len(psutil_alerts)} 次")

        return len(alerts4) > 0

    # ── 辅助：停止所有测试服务器 ────────────────────────────────────────────

    def _stop_servers(self):
        for srv in self.servers:
            srv.stop()
        self.servers.clear()

    # ── 汇总报告 ────────────────────────────────────────────────────────────

    def print_summary(self, results: dict):
        _banner("测试汇总报告")
        total = len(results)
        passed = sum(1 for v in results.values() if v is True)
        skipped = sum(1 for v in results.values() if v is None)
        failed = total - passed - skipped

        for name, result in results.items():
            if result is True:
                status = f"{GREEN}通过{RESET}"
            elif result is None:
                status = f"{YELLOW}跳过{RESET}"
            else:
                status = f"{RED}失败{RESET}"
            print(f"  {name:<30} {status}")

        print(f"\n  共 {total} 个场景: "
              f"{GREEN}{passed} 通过{RESET}  "
              f"{YELLOW}{skipped} 跳过{RESET}  "
              f"{RED}{failed} 失败{RESET}")

        print(f"\n  运行环境:")
        print(f"    系统:    {platform.system()} {platform.release()}")
        print(f"    psutil:  {'已安装' if PSUTIL_AVAILABLE else '未安装 (pip install psutil)'}")
        print(f"    scapy:   {'已安装' if SCAPY_AVAILABLE else '未安装 (pip install scapy)'}")
        print(f"    管理员:  {'是（可启用数据包嗅探）' if _is_admin() else '否（数据包嗅探不可用）'}")


# ===========================================================================
# 主入口
# ===========================================================================

def main():
    _banner("端口扫描检测 — 本机实战测试")
    print(f"  检测阈值: {PortScanLiveTest.PORT_THRESHOLD} 端口 / "
          f"{PortScanLiveTest.TIME_WINDOW} 秒时间窗口")
    print(f"  系统:     {platform.system()} {platform.release()}")
    print(f"  psutil:   {'可用' if PSUTIL_AVAILABLE else '不可用'}")

    tester = PortScanLiveTest()
    results = {}

    # 场景一：基础扫描
    results["场景一：基础 connect_scan 检测"] = tester.run_basic_scan_test()

    # 场景二：渐进式扫描
    results["场景二：渐进式扫描 + 窗口验证"] = tester.run_gradual_scan_test()

    # 场景三：多IP并发
    results["场景三：多攻击者并发扫描"] = tester.run_multi_ip_test()

    # 场景四：psutil验证（可选）
    results["场景四：psutil 真实连接监控"] = tester.run_psutil_test()

    # 汇总
    tester.print_summary(results)


if __name__ == "__main__":
    main()
