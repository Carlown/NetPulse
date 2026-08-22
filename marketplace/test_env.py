# -*- coding: utf-8 -*-
"""NetPulse 测试环境插件：查看当前运行环境的真实信息。

数据全部来自标准库实时采集（Python / 系统 / 网络 / 时区），
点击「刷新」重新采集。图标使用 test_env.png（与本文件同目录）。
"""

import os
import platform
import socket
import time
import datetime


class Plugin(NetPulsePlugin):
    name = ("测试环境", "Test Environment")
    version = "1.0"
    author = "NetPulse"
    description = ("查看当前运行环境：Python、操作系统、网络、时区等真实信息，可随时刷新。",
                   "Inspect the runtime environment: Python, OS, network, timezone and more.")
    icon = "test_env.png"     # 图片路径（相对本插件文件）
    category = "tool"

    def on_load(self, ctx):
        self._ctx = ctx

    # ---------- 数据采集 ----------
    def _collect(self):
        try:
            hostname = socket.gethostname()
        except Exception:
            hostname = "-"
        try:
            # 取默认路由出口的本地 IP（不做外网请求）
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                local_ip = socket.gethostbyname(hostname)
            except Exception:
                local_ip = "-"
        try:
            tz = time.tzname[0] if time.tzname else "-"
            utc_off = datetime.datetime.now().astimezone().strftime("%z")
        except Exception:
            tz, utc_off = "-", ""
        return [
            ("NetPulse", self._ctx.app_version or "-"),
            ("Python", f"{platform.python_version()} ({platform.python_implementation()})"),
            ("操作系统", f"{platform.system()} {platform.release()} ({platform.machine()})"),
            ("主机名", hostname),
            ("本机 IP", local_ip),
            ("时区", f"{tz} (UTC{utc_off})" if utc_off else tz),
            ("当前时间", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("插件目录", os.path.dirname(os.path.abspath(__file__))),
        ]

    # ---------- 页面 ----------
    def create_widget(self, parent):
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout
        from qfluentwidgets import (TitleLabel, SubtitleLabel, BodyLabel,
                                    CaptionLabel, PushButton, SimpleCardWidget)

        w = QWidget(parent)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(16)

        lay.addWidget(SubtitleLabel(self._ctx.tr("测试环境", "Test Environment")))
        hint = CaptionLabel(self._ctx.tr(
            "以下信息由标准库实时采集，点击「刷新」重新获取。",
            "Collected live from the standard library. Click Refresh to reload."))
        lay.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(4)
        lay.addLayout(grid)

        def fill():
            while grid.count():
                item = grid.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for i, (k, v) in enumerate(self._collect()):
                kl = BodyLabel(k, w)
                kl.setObjectName("k")
                vl = BodyLabel(str(v), w)
                vl.setWordWrap(True)
                grid.addWidget(kl, i, 0)
                grid.addWidget(vl, i, 1)

        fill()

        btn = PushButton(self._ctx.tr("刷新", "Refresh"))
        btn.clicked.connect(fill)
        lay.addWidget(btn)
        lay.addStretch(1)
        return w

    def on_unload(self):
        pass
