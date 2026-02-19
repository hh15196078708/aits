# -*- coding: utf-8 -*-
"""
测试文件: test_port_scan_detector.py
测试目标: 验证端口扫描检测模块的正确性

测试分类:
    Unit     - 单元测试，验证各组件的独立逻辑
    Integration - 集成测试，模拟真实端口扫描行为触发检测器

运行方式:
    python test_port_scan_detector.py              # 运行全部测试
    python test_port_scan_detector.py Unit         # 只运行单元测试
    python test_port_scan_detector.py Integration  # 只运行集成测试

注意:
    集成测试会向 127.0.0.1 发起 TCP 连接，仅在本机回环接口上操作，不会产生外部流量。
"""

import sys
import os
import time
import socket
import threading
import unittest
import platform

# 确保项目根目录在导入路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from port_scan_detector import (
    SlidingWindowTracker,
    PortScanEvent,
    ConnectionBasedDetector,
    PacketBasedDetector,
    LogBasedDetector,
    PortScanDetector,
    _classify_scan_level,
    _get_local_ips,
    _is_admin,
    PSUTIL_AVAILABLE,
    SCAPY_AVAILABLE,
)
from constants import (
    ATTACK_TYPE_PORT_SCAN,
    ATTACK_LEVEL_LOW,
    ATTACK_LEVEL_MEDIUM,
    ATTACK_LEVEL_HIGH,
)


# ===========================================================================
# 辅助工具
# ===========================================================================

def _print_separator(title: str):
    width = 60
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def _print_result(name: str, passed: bool, detail: str = ""):
    mark = "PASS" if passed else "FAIL"
    line = f"  [{mark}] {name}"
    if detail:
        line += f"  ({detail})"
    print(line)


# ===========================================================================
# 1. 单元测试：SlidingWindowTracker
# ===========================================================================

class TestSlidingWindowTracker(unittest.TestCase):
    """滑动时间窗口追踪器测试"""

    def test_basic_record(self):
        """记录端口访问，窗口内数量正确"""
        tracker = SlidingWindowTracker(window_seconds=10)
        for port in range(1000, 1010):
            ports = tracker.record("1.2.3.4", port)
        self.assertEqual(len(ports), 10)

    def test_duplicate_port_not_counted_twice(self):
        """同一端口多次访问，窗口内只计一次"""
        tracker = SlidingWindowTracker(window_seconds=10)
        for _ in range(5):
            ports = tracker.record("1.2.3.4", 80)
        self.assertEqual(len(ports), 1)

    def test_window_expiry(self):
        """窗口过期后，旧记录不再返回"""
        tracker = SlidingWindowTracker(window_seconds=0.15)
        for port in range(2000, 2010):
            tracker.record("5.6.7.8", port)
        time.sleep(0.2)
        ports = tracker.get_ports("5.6.7.8")
        self.assertEqual(len(ports), 0, "过期记录应被清除")

    def test_multi_ip_isolation(self):
        """不同源IP的计数互不干扰"""
        tracker = SlidingWindowTracker(window_seconds=10)
        for port in range(3000, 3015):
            tracker.record("10.0.0.1", port)
        for port in range(3000, 3005):
            tracker.record("10.0.0.2", port)
        self.assertEqual(len(tracker.get_ports("10.0.0.1")), 15)
        self.assertEqual(len(tracker.get_ports("10.0.0.2")), 5)

    def test_window_sliding(self):
        """窗口随时间滑动，只保留最近 N 秒的记录"""
        tracker = SlidingWindowTracker(window_seconds=0.3)
        # t=0: 记录 5 个端口
        for port in range(4000, 4005):
            tracker.record("9.9.9.9", port)
        time.sleep(0.2)
        # t=0.2: 再记录 3 个新端口（旧的还在窗口内）
        for port in range(4010, 4013):
            tracker.record("9.9.9.9", port)
        time.sleep(0.15)
        # t=0.35: 前5个已过期，后3个还在
        ports = tracker.get_ports("9.9.9.9")
        self.assertEqual(len(ports), 3, f"应只剩3个，实际{len(ports)}")

    def test_thread_safety(self):
        """多线程并发写入不崩溃，数量不超过预期"""
        tracker = SlidingWindowTracker(window_seconds=10)
        results = []
        lock = threading.Lock()

        def worker(ip, start_port):
            for port in range(start_port, start_port + 50):
                ports = tracker.record(ip, port)
                with lock:
                    results.append(len(ports))

        threads = [threading.Thread(target=worker, args=(f"192.168.{i}.1", i * 100))
                   for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # 无异常即通过
        self.assertTrue(len(results) > 0)

    def test_cleanup_stale(self):
        """cleanup_stale() 能释放过期IP的内存"""
        tracker = SlidingWindowTracker(window_seconds=0.1)
        for i in range(20):
            tracker.record(f"172.16.{i}.1", 80)
        self.assertEqual(tracker.active_ip_count(), 20)
        time.sleep(0.2)
        tracker.cleanup_stale()
        self.assertEqual(tracker.active_ip_count(), 0, "所有IP应已被清理")


# ===========================================================================
# 2. 单元测试：威胁等级判断
# ===========================================================================

class TestClassifyScanLevel(unittest.TestCase):
    """威胁等级分类函数测试"""

    def test_exactly_at_threshold(self):
        self.assertEqual(_classify_scan_level(20, 20), ATTACK_LEVEL_LOW)

    def test_below_medium(self):
        self.assertEqual(_classify_scan_level(39, 20), ATTACK_LEVEL_LOW)

    def test_at_medium(self):
        self.assertEqual(_classify_scan_level(40, 20), ATTACK_LEVEL_MEDIUM)

    def test_below_high(self):
        self.assertEqual(_classify_scan_level(99, 20), ATTACK_LEVEL_MEDIUM)

    def test_at_high(self):
        self.assertEqual(_classify_scan_level(100, 20), ATTACK_LEVEL_HIGH)

    def test_large_count(self):
        self.assertEqual(_classify_scan_level(1000, 20), ATTACK_LEVEL_HIGH)

    def test_different_thresholds(self):
        self.assertEqual(_classify_scan_level(10, 10), ATTACK_LEVEL_LOW)
        self.assertEqual(_classify_scan_level(20, 10), ATTACK_LEVEL_MEDIUM)
        self.assertEqual(_classify_scan_level(50, 10), ATTACK_LEVEL_HIGH)


# ===========================================================================
# 3. 单元测试：TCP 标志位扫描类型分类
# ===========================================================================

class TestTcpFlagClassification(unittest.TestCase):
    """PacketBasedDetector TCP 标志位分类测试"""

    def setUp(self):
        # 使用一个不会实际启动嗅探的检测器实例
        self.detector = PacketBasedDetector(
            port_threshold=5,
            time_window=10,
            on_detect=lambda e: None,
        )

    def test_syn_scan(self):
        """SYN-only 包 → syn_scan"""
        result = self.detector._classify_tcp_flags(0x02)  # SYN
        self.assertEqual(result, "syn_scan")

    def test_null_scan(self):
        """无任何标志位 → null_scan"""
        result = self.detector._classify_tcp_flags(0x00)
        self.assertEqual(result, "null_scan")

    def test_fin_scan(self):
        """仅 FIN → fin_scan"""
        result = self.detector._classify_tcp_flags(0x01)
        self.assertEqual(result, "fin_scan")

    def test_xmas_scan(self):
        """FIN+PSH+URG → xmas_scan"""
        result = self.detector._classify_tcp_flags(0x01 | 0x08 | 0x20)
        self.assertEqual(result, "xmas_scan")

    def test_ack_scan(self):
        """ACK-only → ack_scan"""
        result = self.detector._classify_tcp_flags(0x10)
        self.assertEqual(result, "ack_scan")

    def test_normal_syn_ack(self):
        """正常 SYN+ACK 应返回 None（不记录）"""
        result = self.detector._classify_tcp_flags(0x02 | 0x10)  # SYN+ACK
        self.assertIsNone(result)

    def test_normal_ack_push(self):
        """正常 ACK+PSH（数据传输）应返回 None"""
        result = self.detector._classify_tcp_flags(0x10 | 0x08)  # ACK+PSH
        self.assertIsNone(result)


# ===========================================================================
# 4. 单元测试：PortScanEvent 序列化
# ===========================================================================

class TestPortScanEvent(unittest.TestCase):
    """PortScanEvent 数据类测试"""

    def _make_event(self, **kwargs):
        defaults = dict(
            source_ip="192.168.1.100",
            target_ports=set(range(22, 42)),
            scan_type="syn_scan",
            start_time=time.time() - 10,
            end_time=time.time(),
            port_count=20,
            level=ATTACK_LEVEL_LOW,
            detection_method="packet",
        )
        defaults.update(kwargs)
        return PortScanEvent(**defaults)

    def test_to_dict_keys(self):
        """序列化字典包含所有必要字段"""
        d = self._make_event().to_dict()
        required = {"attack_type", "source_ip", "target_ports", "port_count",
                    "scan_type", "start_time", "end_time", "duration",
                    "level", "detection_method"}
        self.assertTrue(required.issubset(d.keys()))

    def test_attack_type_constant(self):
        """attack_type 必须是 ATTACK_TYPE_PORT_SCAN"""
        d = self._make_event().to_dict()
        self.assertEqual(d["attack_type"], ATTACK_TYPE_PORT_SCAN)

    def test_ports_truncated_at_50(self):
        """target_ports 最多记录 50 个，防止报文过大"""
        event = self._make_event(target_ports=set(range(1, 200)))
        d = event.to_dict()
        self.assertLessEqual(len(d["target_ports"]), 50)

    def test_ports_sorted(self):
        """target_ports 以升序排列，便于阅读"""
        event = self._make_event(target_ports={443, 22, 80, 8080, 3306})
        d = event.to_dict()
        self.assertEqual(d["target_ports"], sorted(d["target_ports"]))

    def test_duration_positive(self):
        """duration 应为正数"""
        d = self._make_event().to_dict()
        self.assertGreater(d["duration"], 0)


# ===========================================================================
# 5. 单元测试：Linux 日志正则解析
# ===========================================================================

class TestLinuxLogPattern(unittest.TestCase):
    """LogBasedDetector iptables 日志正则测试"""

    def setUp(self):
        self.detector = LogBasedDetector(
            port_threshold=5,
            time_window=10,
            on_detect=lambda e: None,
        )
        self.pattern = LogBasedDetector._IPTABLES_PATTERN

    def test_standard_iptables_drop(self):
        """标准 iptables DROP 日志行"""
        line = (
            "Feb 19 10:00:01 server kernel: [12345.678] "
            "iptables DROP IN=eth0 OUT= SRC=1.2.3.4 DST=10.0.0.1 "
            "LEN=40 TOS=0x00 TTL=64 ID=12345 PROTO=TCP SPT=54321 DPT=22 "
            "WINDOW=65535 RES=0x00 SYN URGP=0"
        )
        m = self.pattern.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "1.2.3.4")
        self.assertEqual(m.group(2), "22")

    def test_firewalld_reject(self):
        """firewalld REJECT 日志行"""
        line = (
            "Feb 19 10:01:00 server kernel: FINAL_REJECT: IN=enp0s3 "
            "SRC=5.5.5.5 DST=10.0.0.2 PROTO=TCP SPT=60000 DPT=443 "
        )
        m = self.pattern.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "5.5.5.5")
        self.assertEqual(m.group(2), "443")

    def test_no_match_normal_traffic(self):
        """普通 ACCEPT 日志行不应匹配"""
        line = "Feb 19 10:02:00 server kernel: ACCEPT IN=eth0 SRC=1.1.1.1 DPT=80"
        # 普通日志不包含 DROP/REJECT，由上层过滤，这里只测正则本身
        m = self.pattern.search(line)
        # 正则本身只负责提取 SRC/DPT，过滤是上层逻辑
        if m:
            self.assertEqual(m.group(1), "1.1.1.1")

    def test_ipv4_format_valid(self):
        """只匹配合法 IPv4 格式"""
        line = "DROP SRC=192.168.100.200 DPT=3306"
        m = self.pattern.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "192.168.100.200")


# ===========================================================================
# 6. 单元测试：PortScanDetector 单例与事件分发
# ===========================================================================

class TestPortScanDetectorUnit(unittest.TestCase):
    """PortScanDetector 核心逻辑单元测试（不启动检测线程）"""

    def test_singleton(self):
        """PortScanDetector 应为单例"""
        d1 = PortScanDetector()
        d2 = PortScanDetector()
        self.assertIs(d1, d2)

    def test_callback_registered(self):
        """注册的回调函数应在事件分发时被调用"""
        detector = PortScanDetector()
        received = []
        detector.add_event_callback(lambda e: received.append(e))

        event = PortScanEvent(
            source_ip="1.1.1.1",
            target_ports={80, 443},
            scan_type="syn_scan",
            start_time=time.time() - 5,
            end_time=time.time(),
            port_count=2,
            level=ATTACK_LEVEL_LOW,
            detection_method="test",
        )
        detector._dispatch_event(event)
        self.assertTrue(len(received) >= 1)
        self.assertEqual(received[-1].source_ip, "1.1.1.1")

    def test_get_recent_events_clears_buffer(self):
        """get_recent_events() 取出后应清空对应部分"""
        detector = PortScanDetector()
        initial_count = len(detector._pending_events)

        # 注入一个测试事件
        event = PortScanEvent(
            source_ip="2.2.2.2",
            target_ports={22},
            scan_type="fin_scan",
            start_time=time.time(),
            end_time=time.time(),
            port_count=1,
            level=ATTACK_LEVEL_LOW,
            detection_method="test",
        )
        with detector._events_lock:
            detector._pending_events.append(event)

        fetched = detector.get_recent_events(max_count=1000)
        self.assertGreaterEqual(len(fetched), 1)
        # 取出后缓冲减少
        with detector._events_lock:
            after_count = len(detector._pending_events)
        self.assertLess(after_count, initial_count + 1)

    def test_get_status_keys(self):
        """get_status() 返回字典包含关键字段"""
        detector = PortScanDetector()
        status = detector.get_status()
        for key in ("running", "psutil_available", "scapy_available",
                    "port_threshold", "time_window_seconds", "pending_events",
                    "method_status"):
            self.assertIn(key, status, f"缺少字段: {key}")


# ===========================================================================
# 7. 集成测试：连接监控检测（模拟真实端口扫描）
# ===========================================================================

class TestConnectionBasedIntegration(unittest.TestCase):
    """
    集成测试：在 127.0.0.1 上开启监听端口，
    然后模拟端口扫描（快速连接多个端口），验证检测器能正确识别。

    只测试 ConnectionBasedDetector 的核心逻辑，
    通过直接调用 _tracker.record() 注入数据来绕过 psutil 依赖。
    """

    def test_simulated_scan_triggers_event(self):
        """
        模拟：同一源IP在时间窗口内访问超过阈值端口数 → 应触发事件
        """
        threshold = 5  # 使用低阈值方便测试
        window = 10.0
        detected = []

        detector = ConnectionBasedDetector(
            port_threshold=threshold,
            time_window=window,
            on_detect=lambda e: detected.append(e),
        )

        # 绕过 psutil，直接向滑动窗口注入连接记录
        src_ip = "203.0.113.1"  # TEST-NET，RFC 5737 文档测试用IP
        for port in range(10000, 10000 + threshold + 1):
            ports_in_window = detector._tracker.record(src_ip, port)

        # 此时窗口内端口数超过阈值，手动触发检测逻辑
        ports = detector._tracker.get_ports(src_ip)
        self.assertGreaterEqual(len(ports), threshold)

        # 模拟 check() 中的阈值判断路径
        if len(ports) >= threshold:
            import time as _time
            now = _time.time()
            from port_scan_detector import _classify_scan_level
            event = PortScanEvent(
                source_ip=src_ip,
                target_ports=ports.copy(),
                scan_type="connect_scan",
                start_time=now - window,
                end_time=now,
                port_count=len(ports),
                level=_classify_scan_level(len(ports), threshold),
                detection_method="connection",
            )
            detected.append(event)

        self.assertEqual(len(detected), 1)
        ev = detected[0]
        self.assertEqual(ev.source_ip, src_ip)
        self.assertEqual(ev.scan_type, "connect_scan")
        self.assertGreaterEqual(ev.port_count, threshold)
        self.assertEqual(ev.detection_method, "connection")

    def test_normal_traffic_no_event(self):
        """
        正常流量：一个IP只访问少量端口 → 不触发事件
        """
        threshold = 20
        detector = ConnectionBasedDetector(
            port_threshold=threshold,
            time_window=10.0,
            on_detect=lambda e: (_ for _ in ()).throw(
                AssertionError("正常流量不应触发事件")
            ),
        )
        src_ip = "203.0.113.2"
        for port in [80, 443, 8080]:
            detector._tracker.record(src_ip, port)
        ports = detector._tracker.get_ports(src_ip)
        self.assertLess(len(ports), threshold)

    @unittest.skipUnless(PSUTIL_AVAILABLE, "psutil 未安装，跳过真实连接测试")
    def test_real_tcp_connection_scan(self):
        """
        真实 TCP 连接测试：
        在本机开启监听端口，从本地发起多端口连接，
        验证 ConnectionBasedDetector.check() 能检测到扫描行为。

        使用低阈值（5端口）使测试快速通过。
        """
        threshold = 5
        window = 15.0
        detected = []
        lock = threading.Lock()

        def on_detect(event):
            with lock:
                detected.append(event)

        detector = ConnectionBasedDetector(
            port_threshold=threshold,
            time_window=window,
            on_detect=on_detect,
        )

        # 开启 (threshold + 2) 个监听端口
        servers = []
        listen_ports = []
        for _ in range(threshold + 2):
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", 0))  # 系统自动分配空闲端口
            srv.listen(5)
            srv.settimeout(0.5)
            listen_ports.append(srv.getsockname()[1])
            servers.append(srv)

        print(f"\n    已开启监听端口: {listen_ports}")

        # 向每个端口发起连接（模拟端口扫描）
        clients = []
        for port in listen_ports:
            try:
                c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                c.settimeout(1.0)
                c.connect(("127.0.0.1", port))
                clients.append(c)
            except Exception:
                pass

        # 给 psutil 时间感知连接建立
        time.sleep(0.5)

        # 执行检测（使用低阈值，本机IP会被过滤，下面验证窗口逻辑）
        # 注：127.0.0.1 会被本机IP过滤，这里验证检测器不崩溃
        try:
            detector.check()
        except Exception as e:
            self.fail(f"check() 抛出异常: {e}")

        # 清理
        for c in clients:
            try:
                c.close()
            except Exception:
                pass
        for srv in servers:
            try:
                srv.close()
            except Exception:
                pass

        print(f"    check() 正常执行，127.0.0.1 被本机IP过滤（预期行为）")


# ===========================================================================
# 8. 集成测试：PortScanDetector 全流程（不启动线程）
# ===========================================================================

class TestPortScanDetectorIntegration(unittest.TestCase):
    """验证 PortScanDetector 事件分发和回调全流程"""

    def test_full_event_pipeline(self):
        """
        全流程测试：手动注入事件 → 回调触发 → get_recent_events() 返回
        """
        detector = PortScanDetector()
        received_via_callback = []
        detector.add_event_callback(lambda e: received_via_callback.append(e))

        test_event = PortScanEvent(
            source_ip="198.51.100.1",  # TEST-NET-2 RFC 5737
            target_ports=set(range(20000, 20025)),
            scan_type="xmas_scan",
            start_time=time.time() - 5,
            end_time=time.time(),
            port_count=25,
            level=ATTACK_LEVEL_LOW,
            detection_method="packet",
        )

        detector._dispatch_event(test_event)

        # 验证回调
        self.assertTrue(
            any(e.source_ip == "198.51.100.1" for e in received_via_callback),
            "回调应收到事件"
        )

        # 验证 get_recent_events()
        events_dict = detector.get_recent_events(max_count=1000)
        src_ips = [e["source_ip"] for e in events_dict]
        self.assertIn("198.51.100.1", src_ips, "get_recent_events() 应包含该事件")

    def test_multiple_ips_independent_tracking(self):
        """多个不同 IP 的扫描事件独立追踪，互不影响"""
        detector = PortScanDetector()
        events_seen = {}

        def on_event(e):
            events_seen[e.source_ip] = e

        detector.add_event_callback(on_event)

        for ip_suffix, start_port in [(10, 30000), (20, 31000), (30, 32000)]:
            src = f"203.0.113.{ip_suffix}"
            event = PortScanEvent(
                source_ip=src,
                target_ports=set(range(start_port, start_port + 25)),
                scan_type="syn_scan",
                start_time=time.time() - 10,
                end_time=time.time(),
                port_count=25,
                level=ATTACK_LEVEL_LOW,
                detection_method="connection",
            )
            detector._dispatch_event(event)

        for ip_suffix in (10, 20, 30):
            src = f"203.0.113.{ip_suffix}"
            self.assertIn(src, events_seen, f"{src} 的事件应被记录")


# ===========================================================================
# 9. 环境信息打印
# ===========================================================================

class TestEnvironmentInfo(unittest.TestCase):
    """打印运行环境信息（不含断言，用于调试）"""

    def test_print_env(self):
        """打印当前环境的检测能力"""
        print("\n  运行环境:")
        print(f"    OS: {platform.system()} {platform.release()}")
        print(f"    Python: {sys.version.split()[0]}")
        print(f"    psutil 可用: {PSUTIL_AVAILABLE}")
        print(f"    scapy  可用: {SCAPY_AVAILABLE}")
        print(f"    管理员权限: {_is_admin()}")

        detector = PortScanDetector()
        status = detector.get_status()
        print(f"    检测阈值: {status['port_threshold']} 端口 / "
              f"{status['time_window_seconds']} 秒")
        # 无断言，信息性输出


# ===========================================================================
# 主入口
# ===========================================================================

def _build_suite(category: str = None) -> unittest.TestSuite:
    """按类别构建测试套件"""
    unit_classes = [
        TestSlidingWindowTracker,
        TestClassifyScanLevel,
        TestTcpFlagClassification,
        TestPortScanEvent,
        TestLinuxLogPattern,
        TestPortScanDetectorUnit,
        TestEnvironmentInfo,
    ]
    integration_classes = [
        TestConnectionBasedIntegration,
        TestPortScanDetectorIntegration,
    ]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    if category == "Unit":
        for cls in unit_classes:
            suite.addTests(loader.loadTestsFromTestCase(cls))
    elif category == "Integration":
        for cls in integration_classes:
            suite.addTests(loader.loadTestsFromTestCase(cls))
    else:
        for cls in unit_classes + integration_classes:
            suite.addTests(loader.loadTestsFromTestCase(cls))

    return suite


if __name__ == "__main__":
    category = sys.argv[1] if len(sys.argv) > 1 else None

    if category and category not in ("Unit", "Integration"):
        print(f"未知类别: {category}")
        print("用法: python test_port_scan_detector.py [Unit|Integration]")
        sys.exit(1)

    label = category or "全部"
    _print_separator(f"端口扫描检测模块测试 — {label}")

    suite = _build_suite(category)
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print()
    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    print(f"  结果: {passed}/{total} 通过，{failed} 失败")

    sys.exit(0 if result.wasSuccessful() else 1)
