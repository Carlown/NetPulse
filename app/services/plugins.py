"""NetPulse 插件系统：发现、加载、卸载、启用/禁用第三方扩展。

插件目录：%APPDATA%/NetPulse/plugins/
插件格式：
  1) 单文件插件：xxx.py（定义 NetPulsePlugin 子类）
  2) 文件夹插件：xxx/main.py（定义 NetPulsePlugin 子类）
插件 ID = 文件名 / 文件夹名（唯一且稳定）。

安全提示：插件是第三方代码，运行于主程序进程内，拥有同等权限。
请仅安装可信来源的插件；插件行为同样受本工具免责声明约束。
"""
import importlib.util
import os
import shutil
import sys
import traceback

from PySide6.QtCore import QObject, Signal

from app.services.logger import log
from app.services.settings import settings

PLUGIN_API_VERSION = 1


def plugins_dir() -> str:
    """插件目录（自动创建）。"""
    base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                        "NetPulse", "plugins")
    os.makedirs(base, exist_ok=True)
    return base


def _i18n_text(v):
    """元组 (中文, 英本) 按当前界面语言取值；普通字符串原样返回。"""
    from app.ui.i18n import current_lang
    if isinstance(v, (tuple, list)) and len(v) == 2:
        return str(v[0]) if current_lang() == "zh-CN" else str(v[1])
    return str(v)


class NetPulsePlugin:
    """插件基类：插件继承此类实现扩展功能。

    插件文件中可直接使用 NetPulsePlugin（宿主已注入模块命名空间），
    也可 from app.services.plugins import NetPulsePlugin。
    """

    id = "unknown"                # 由宿主按文件/文件夹名覆盖
    name = "Unnamed Plugin"       # 显示名，可为 (中文, 英文)
    version = "1.0"
    author = ""
    description = ""              # 简介，可为 (中文, 英文)
    api_version = PLUGIN_API_VERSION

    def on_load(self, ctx: "PluginContext"):
        """加载时调用，可初始化资源、注册扩展（协议/导出器/目标源/指标订阅）。"""
        pass

    def on_unload(self):
        """卸载时调用，可释放资源。注册项由宿主自动清理。"""
        pass

    def create_widget(self, parent):
        """返回插件主页面控件（加入主窗口导航）；返回 None 则不添加页面。"""
        return None

    def page_title(self):
        """导航页标题。"""
        t = getattr(self, "title", None)
        return _i18n_text(t) if t else _i18n_text(self.name)

    # ---------- 压测生命周期（可选实现） ----------
    def on_test_start(self, configs):
        """每次压测开始时调用（主线程）。configs 为目标配置 dict 列表。"""
        pass

    def on_test_end(self, report):
        """每次压测结束/停止后调用（主线程）。report 为汇总报告 dict。"""
        pass


class PluginContext:
    """提供给插件的宿主上下文（受限的便捷接口）。"""

    def __init__(self, pid: str):
        self.plugin_id = pid
        from app.services.updater import APP_VERSION
        self.app_version = APP_VERSION
        self.logger = log

    # 双语助手
    @staticmethod
    def tr(zh: str, en: str) -> str:
        from app.ui.i18n import L
        return L(zh, en)

    # 插件私有配置（命名空间隔离，持久化在主配置的 plugin_data 下）
    def get(self, key, default=None):
        data = settings.plugin_data or {}
        return data.get(self.plugin_id, {}).get(key, default)

    def set(self, key, value):
        data = dict(settings.plugin_data or {})
        slot = dict(data.get(self.plugin_id, {}))
        slot[key] = value
        data[self.plugin_id] = slot
        settings.set("plugin_data", data)

    # ---------- 扩展注册（on_load 中调用） ----------
    def register_protocol(self, name: str, handler):
        """注册自定义测试协议，压测页协议下拉框会出现该项。

        handler(config: dict, timeout: float, state: dict) -> (ok, err, nbytes)
        - 在 worker 线程执行，必须线程安全、可重入
        - config: {"target", "port", "protocol", "packet_size", "headers", ...}
        - state: 每个 worker 线程一份的字典，可存放 socket 等长连接资源
        - 返回 (成功?, 错误码或None, 发送字节数)
        """
        plugin_manager._register_protocol(self.plugin_id, name, handler)

    def register_exporter(self, label, callback):
        """注册报告导出器，压测页"导出报告"菜单出现该项。

        callback(report: dict, path: str) —— 把汇总报告写出到 path（主线程调用）。
        label 可为 (中文, 英文) 元组。
        """
        plugin_manager._register_exporter(self.plugin_id, label, callback)

    def register_target_provider(self, label, callback):
        """注册目标集提供者，压测页出现"插件目标"按钮。

        callback() -> [str] —— 返回目标地址列表（主线程调用）。
        label 可为 (中文, 英文) 元组。
        """
        plugin_manager._register_target_provider(self.plugin_id, label, callback)

    def subscribe_metrics(self, callback):
        """订阅实时压测指标（QPS/延迟/成功失败计数等）。

        callback(snapshot: dict) 在主线程周期调用（压测运行期间约 500ms 一次）。
        """
        plugin_manager._subscribe_metrics(self.plugin_id, callback)


class _PluginRecord:
    """一个已发现的插件条目。"""

    def __init__(self, path: str):
        self.path = path              # main.py 完整路径
        self.plugin = None            # NetPulsePlugin 实例（未加载为 None）
        self.error = None             # 加载错误信息

    @property
    def pid(self) -> str:
        """插件 ID：main.py 所在目录名（文件夹插件）或文件名去扩展。"""
        d = os.path.dirname(self.path)
        root = plugins_dir()
        if os.path.dirname(d) == root:
            return os.path.basename(d)
        return os.path.splitext(os.path.basename(self.path))[0]

    @property
    def disabled(self) -> bool:
        return self.pid in set(settings.plugins_disabled or [])

    @property
    def state(self) -> str:
        """loaded / disabled / error / unloaded"""
        if self.disabled:
            return "disabled"
        if self.error:
            return "error"
        return "loaded" if self.plugin else "unloaded"


class PluginManager(QObject):
    """插件管理器：扫描目录、安全加载、启停、导入、删除。"""

    loaded = Signal(object)   # NetPulsePlugin 实例
    unloaded = Signal(str)    # 插件 ID
    changed = Signal()        # 列表/状态变化（设置页刷新）

    def __init__(self):
        super().__init__()
        self._records = []    # [_PluginRecord]
        # 扩展注册表（key -> {"pid": 插件ID, "label": 标签, "fn": 回调}）
        self._protocols = {}        # 协议名(大写) -> handler
        self._exporters = {}        # 导出器名 -> {"label", "fn"}
        self._target_providers = {} # 提供者名 -> {"label", "fn"}
        self._metric_subs = []      # [{"pid", "fn"}]
        self._ensure_example()
        self.discover()

    # ---------- 扩展注册表（由 PluginContext 调用） ----------
    def _register_protocol(self, pid, name, handler):
        key = str(name).strip().upper()
        if not key:
            return
        self._protocols[key] = {"pid": pid, "fn": handler}
        self.changed.emit()

    def _register_exporter(self, pid, label, callback):
        key = f"{pid}::{id(callback)}"
        self._exporters[key] = {"pid": pid, "label": label, "fn": callback}

    def _register_target_provider(self, pid, label, callback):
        key = f"{pid}::{id(callback)}"
        self._target_providers[key] = {"pid": pid, "label": label, "fn": callback}
        self.changed.emit()

    def _subscribe_metrics(self, pid, callback):
        self._metric_subs.append({"pid": pid, "fn": callback})

    def _cleanup_registrations(self, pid: str):
        """插件卸载时清理它的全部注册项。"""
        self._protocols = {k: v for k, v in self._protocols.items() if v["pid"] != pid}
        self._exporters = {k: v for k, v in self._exporters.items() if v["pid"] != pid}
        self._target_providers = {k: v for k, v in self._target_providers.items() if v["pid"] != pid}
        self._metric_subs = [s for s in self._metric_subs if s["pid"] != pid]

    # ---------- 供引擎/界面查询 ----------
    def protocol_names(self):
        """已注册的插件协议名列表（大写）。"""
        return sorted(self._protocols.keys())

    def protocol_handler(self, name: str):
        """取协议 handler；未注册返回 None。"""
        ent = self._protocols.get(str(name).strip().upper())
        return ent["fn"] if ent else None

    def exporters(self):
        """[(显示名, callback)] 导出器列表。"""
        return [(_i18n_text(v["label"]), v["fn"]) for v in self._exporters.values()]

    def target_providers(self):
        """[(显示名, callback)] 目标集提供者列表。"""
        return [(_i18n_text(v["label"]), v["fn"]) for v in self._target_providers.values()]

    # ---------- 压测事件分发（主线程调用） ----------
    def notify_test_start(self, configs):
        from app.ui.i18n import L
        for rec in self._records:
            if rec.plugin is not None:
                try:
                    rec.plugin.on_test_start(configs)
                except Exception as e:
                    log.error(L(f"插件 on_test_start 回调失败: {rec.pid}: {e}",
                                f"Plugin on_test_start failed: {rec.pid}: {e}"))

    def notify_test_end(self, report):
        from app.ui.i18n import L
        for rec in self._records:
            if rec.plugin is not None:
                try:
                    rec.plugin.on_test_end(report)
                except Exception as e:
                    log.error(L(f"插件 on_test_end 回调失败: {rec.pid}: {e}",
                                f"Plugin on_test_end failed: {rec.pid}: {e}"))

    def dispatch_metrics(self, snapshot: dict):
        """转发实时指标给订阅插件（主线程，异常不中断）。"""
        from app.ui.i18n import L
        for sub in list(self._metric_subs):
            try:
                sub["fn"](snapshot)
            except Exception as e:
                log.error(L(f"插件指标回调失败: {e}", f"Plugin metrics callback failed: {e}"))

    # ---------- 发现 ----------
    def _ensure_example(self):
        """首次运行时在插件目录放置示例插件，演示 API 用法。"""
        p = os.path.join(plugins_dir(), "example_hello.py")
        if not os.path.exists(p):
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(EXAMPLE_PLUGIN)
            except Exception:
                pass
        p2 = os.path.join(plugins_dir(), "example_dns.py")
        if not os.path.exists(p2):
            try:
                with open(p2, "w", encoding="utf-8") as f:
                    f.write(EXAMPLE_DNS_PLUGIN)
            except Exception:
                pass

    def discover(self):
        """扫描插件目录，合并式更新记录列表：同 ID 保留原 record（含已加载实例），
        避免设置页刷新时把已加载插件重置为未加载。"""
        old = {r.pid: r for r in self._records}
        self._records = []
        root = plugins_dir()
        try:
            entries = sorted(os.listdir(root))
        except Exception:
            entries = []
        for entry in entries:
            path = os.path.join(root, entry)
            main_py = None
            if entry.endswith(".py") and entry != "__init__.py":
                main_py = path
            elif os.path.isdir(path) and os.path.isfile(os.path.join(path, "main.py")):
                main_py = os.path.join(path, "main.py")
            if main_py:
                fresh = _PluginRecord(main_py)
                prev = old.get(fresh.pid)
                self._records.append(prev if prev is not None else fresh)
        return self._records

    def records(self):
        return list(self._records)

    def record(self, pid: str):
        for r in self._records:
            if r.pid == pid:
                return r
        return None

    # ---------- 加载 / 卸载 ----------
    def load_all(self) -> int:
        """加载所有未禁用的插件，返回成功数量。"""
        n = 0
        for rec in self.records():
            if self.load(rec):
                n += 1
        return n

    def load(self, rec: _PluginRecord) -> bool:
        """安全加载单个插件（异常捕获，不拖垮主程序）。"""
        if rec.plugin is not None or rec.disabled:
            return rec.plugin is not None
        pid = rec.pid
        rec.error = None
        try:
            mod_name = f"netpulse_plugin_{pid}"
            spec = importlib.util.spec_from_file_location(mod_name, rec.path)
            mod = importlib.util.module_from_spec(spec)
            # 注入基类，插件文件无需 import 即可继承；sys.modules 注册支持包内相对导入
            mod.__dict__["NetPulsePlugin"] = NetPulsePlugin
            mod.__dict__["PluginContext"] = PluginContext
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            cls = self._find_plugin_class(mod)
            if cls is None:
                raise RuntimeError(
                    f"no NetPulsePlugin subclass found in {os.path.basename(rec.path)}")
            plugin = cls()
            plugin.id = pid
            plugin.on_load(PluginContext(pid))
            rec.plugin = plugin
            from app.ui.i18n import L
            log.info(L(f"插件已加载：{pid}", f"Plugin loaded: {pid}"))
            self.loaded.emit(plugin)
            self.changed.emit()
            return True
        except Exception as e:
            rec.error = f"{e}"
            detail = traceback.format_exc(limit=3)
            from app.ui.i18n import L
            log.error(L(f"插件加载失败：{pid} — {e}", f"Plugin load failed: {pid} — {e}")
                      + "\n" + detail)
            self.changed.emit()
            return False

    @staticmethod
    def _find_plugin_class(mod):
        """在模块命名空间中查找 NetPulsePlugin 子类（取最后定义的）。"""
        found = None
        for obj in vars(mod).values():
            if (isinstance(obj, type) and issubclass(obj, NetPulsePlugin)
                    and obj is not NetPulsePlugin and obj.__module__ == mod.__name__):
                found = obj
        return found

    def unload(self, pid: str) -> bool:
        """卸载插件（调用 on_unload 并通知界面移除页面）。"""
        rec = self.record(pid)
        if rec is None or rec.plugin is None:
            return False
        try:
            rec.plugin.on_unload()
        except Exception:
            pass
        rec.plugin = None
        self._cleanup_registrations(pid)
        from app.ui.i18n import L
        log.info(L(f"插件已卸载：{pid}", f"Plugin unloaded: {pid}"))
        self.unloaded.emit(pid)
        self.changed.emit()
        return True

    # ---------- 启停 / 导入 / 删除 ----------
    def set_enabled(self, pid: str, enabled: bool):
        """启用/禁用插件（禁用立即卸载，启用立即加载）。"""
        dis = set(settings.plugins_disabled or [])
        if enabled:
            dis.discard(pid)
        else:
            dis.add(pid)
        settings.set("plugins_disabled", sorted(dis))
        if not enabled:
            self.unload(pid)
        else:
            rec = self.record(pid)
            if rec and rec.plugin is None:
                self.load(rec)

    def reload(self, pid: str) -> bool:
        """重新加载插件（先卸载再加载）。"""
        rec = self.record(pid)
        if rec is None:
            return False
        self.unload(pid)
        self.discover()
        rec = self.record(pid)
        return self.load(rec) if rec else False

    def import_from(self, src: str):
        """把 .py 文件或文件夹复制进插件目录并加载。返回 (成功?, 消息)。"""
        from app.ui.i18n import L
        if not os.path.exists(src):
            return False, L("源路径不存在", "Source path not found")
        root = plugins_dir()
        base = os.path.basename(os.path.abspath(src).rstrip("\\/"))
        if not base or base in (".", ".."):
            return False, L("无效的插件路径", "Invalid plugin path")
        dst = os.path.join(root, base)
        entry = None
        try:
            if os.path.isdir(src):
                if not os.path.isfile(os.path.join(src, "main.py")):
                    return False, L("文件夹插件必须包含 main.py", "Folder plugin must contain main.py")
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                entry = os.path.join(dst, "main.py")
            else:
                if not src.endswith(".py"):
                    return False, L("仅支持 .py 插件文件", "Only .py plugin files supported")
                shutil.copy2(src, dst)
                entry = dst
        except Exception as e:
            return False, L(f"复制失败：{e}", f"Copy failed: {e}")
        self.discover()
        rec = self.record(_PluginRecord(entry).pid)
        ok = self.load(rec) if rec else False
        if ok:
            return True, L(f"插件已导入：{base}", f"Plugin imported: {base}")
        msg = L("插件导入但加载失败，请检查插件代码", "Imported but failed to load; check plugin code")
        if rec and rec.error:
            msg += f"\n{rec.error}"
        return False, msg

    def remove(self, pid: str) -> bool:
        """卸载并删除插件文件/文件夹。"""
        from app.ui.i18n import L
        rec = self.record(pid)
        if rec is None:
            return False
        self.unload(pid)
        root = plugins_dir()
        # 计算插件根路径（文件夹或 .py 文件）
        d = os.path.dirname(rec.path)
        target = d if os.path.dirname(d) == root else rec.path
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
        except Exception as e:
            log.error(L(f"插件删除失败：{pid} — {e}", f"Plugin remove failed: {pid} — {e}"))
            return False
        self.discover()
        self.changed.emit()
        return True


EXAMPLE_PLUGIN = '''# -*- coding: utf-8 -*-
"""NetPulse 示例插件：演示插件 API 基本用法。

插件开发说明：
- 继承 NetPulsePlugin（宿主已自动注入，无需 import）
- name / description 支持 (中文, 英文) 元组，自动跟随界面语言
- create_widget(parent) 返回的控件会作为独立页面加入主窗口导航
- on_load(ctx) / on_unload() 管理生命周期
- ctx.get(key) / ctx.set(key, value) 读写插件私有配置（自动持久化）
- 插件是第三方代码，请仅安装可信来源的插件
"""


class Plugin(NetPulsePlugin):
    name = ("你好插件", "Hello Plugin")
    version = "1.0"
    author = "NetPulse"
    description = ("示例插件：演示 NetPulse 插件 API，可在 设置 → 插件 中禁用或删除",
                   "Example plugin demonstrating the plugin API; disable or remove it in Settings → Plugins")

    def on_load(self, ctx):
        # ctx: plugin_id / app_version / logger / tr() / get() / set()
        self._ctx = ctx
        self._count = ctx.get("click_count", 0)

    def create_widget(self, parent):
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        from qfluentwidgets import StrongBodyLabel, BodyLabel, PushButton, InfoBar

        w = QWidget(parent)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(12)
        lay.addWidget(StrongBodyLabel(self._ctx.tr("你好，来自插件！", "Hello from plugin!")))
        lay.addWidget(BodyLabel(self._ctx.tr(
            "这是 NetPulse 的示例插件页面。你可以在 设置 → 插件 中禁用、重新加载或删除它。",
            "This is the NetPulse example plugin page. Disable, reload or remove it in Settings → Plugins.")))
        btn = PushButton(self._ctx.tr("点我试试", "Click me"))

        def _click():
            self._count += 1
            self._ctx.set("click_count", self._count)
            InfoBar.success(self._ctx.tr("插件运行正常", "Plugin works"),
                            self._ctx.tr(f"已点击 {self._count} 次（计数已持久化）",
                                         f"Clicked {self._count} times (persisted)"),
                            parent=w.window())

        btn.clicked.connect(_click)
        lay.addWidget(btn)
        lay.addStretch(1)
        return w

    def on_unload(self):
        pass
'''

EXAMPLE_DNS_PLUGIN = '''# -*- coding: utf-8 -*-
"""NetPulse 示例插件：注册自定义 "DNS" 测试协议 + CSV 目标集提供者。

演示插件 API 的扩展能力：
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
    qname = b"".join(bytes([len(p)]) + p.encode() for p in domain.split(".")) + b"\\x00"
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
'''

# 全局单例（与 settings/log 同风格）
plugin_manager = PluginManager()
