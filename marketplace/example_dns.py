# -*- coding: utf-8 -*-
"""NetPulse 市场插件：注册自定义 "DNS" 测试协议 + 目标集提供者。

功能：
- register_protocol: 协议下拉框出现 DNS 项；目标填 DNS 服务器地址（如 223.5.5.5），端口 53
- register_target_provider: 压测页"插件目标"按钮可一键导入常用 DNS 服务器列表
- subscribe_metrics: 压测运行时实时接收 QPS/延迟指标
- on_test_start / on_test_end: 压测生命周期回调

自定义协议 handler 约定（在 worker 线程执行，须线程安全）：
    handler(config, timeout, state) -> (ok, err, nbytes)
    config: {"target", "port", "protocol", ...}
    state:  每个 worker 线程一份的字典，可存放 socket 等长连接资源
"""
import random
import socket
import struct


def _build_dns_query(domain: str) -> bytes:
    """构造一个标准递归 DNS A 记录查询报文。"""
    tid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    qname = b"".join(bytes([len(p)]) + p.encode() for p in domain.split(".")) + b"\x00"
    return header + qname + struct.pack(">HH", 1, 1)  # QTYPE=A, QCLASS=IN


def _dns_handler(c, timeout, state):
    """发一个 DNS 查询并等待响应；演示 state 复用 UDP socket。"""
    sock = state.get("sock")
    if sock is None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        state["sock"] = sock
        _STATES.append(state)  # 登记以便压测结束/卸载时统一清理
    q = _build_dns_query(f"w{random.randint(0, 999999)}.example.com")
    try:
        sock.sendto(q, (c["target"], int(c.get("port") or 53)))
        data, _ = sock.recvfrom(512)
        ok = len(data) >= 12 and (data[2] & 0x80)  # 响应报文且 QR=1
        return ok, None if ok else "bad_response", len(q)
    except OSError as e:
        # 出错后丢弃 socket，下次重建（复用坏 socket 会一直失败）
        try:
            sock.close()
        except OSError:
            pass
        state["sock"] = None
        s = str(e).lower()
        if "timed out" in s:
            return False, "timeout", len(q)
        if "unreachable" in s:
            return False, "unreachable", 0
        return False, "conn", 0


def _cleanup_state(state):
    sock = state.pop("sock", None)
    if sock:
        try:
            sock.close()
        except OSError:
            pass


# 收集所有 worker 的 state，压测结束/插件卸载时统一清理 socket
_STATES = []


class Plugin(NetPulsePlugin):
    name = ("DNS 协议示例", "DNS Protocol Example")
    version = "1.0"
    author = "NetPulse"
    description = ("注册自定义 DNS 测试协议与目标集提供者，演示插件扩展 API",
                   "Registers a custom DNS test protocol and target provider")

    def on_load(self, ctx):
        self._ctx = ctx
        ctx.register_protocol("DNS", _dns_handler)
        ctx.register_target_provider(("常用 DNS 服务器", "Common DNS servers"),
                                     self._dns_servers)
        ctx.subscribe_metrics(self._on_metrics)

    def _dns_servers(self):
        return ["223.5.5.5", "119.29.29.29", "8.8.8.8", "1.1.1.1"]

    def _on_metrics(self, snap):
        # 实时指标回调（主线程，约 500ms 一次）——可做自己的可视化/告警
        self._last_qps = snap.get("qps", 0.0)

    def on_test_start(self, configs):
        if any(c.get("protocol") == "DNS" for c in configs):
            self._ctx.logger.info(self._ctx.tr(
                f"DNS 协议插件：开始测试 {len(configs)} 个目标",
                f"DNS plugin: testing {len(configs)} target(s)"))

    def on_test_end(self, report):
        self._ctx.logger.info(self._ctx.tr(
            f"DNS 协议插件：测试结束，共 {report.get('total', 0)} 次查询",
            f"DNS plugin: finished, {report.get('total', 0)} queries total"))
        for st in list(_STATES):
            _cleanup_state(st)
        _STATES.clear()

    def on_unload(self):
        for st in list(_STATES):
            _cleanup_state(st)
        _STATES.clear()
