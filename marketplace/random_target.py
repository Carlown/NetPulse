# -*- coding: utf-8 -*-
"""NetPulse 插件：随机测试目标生成器。

一键生成随机内网 IP / 端口组合，方便快速填充测试表单。
仅用于演示一键发布流程。
"""
import random


class Plugin(NetPulsePlugin):
    name = ("随机目标生成器", "Random Target Generator")
    version = "1.0"
    author = "NetPulse"
    description = ("一键生成随机内网 IP 和端口，用于快速填充测试表单",
                   "Generate random private IPs and ports for quick test forms")

    def on_load(self, ctx):
        self._ctx = ctx
        self._count = ctx.get("gen_count", 0)

    def create_widget(self, parent):
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        from qfluentwidgets import (StrongBodyLabel, BodyLabel, PushButton,
                                    InfoBar, LineEdit)

        w = QWidget(parent)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(12)
        lay.addWidget(StrongBodyLabel(
            self._ctx.tr("随机测试目标生成器", "Random Test Target Generator")))
        lay.addWidget(BodyLabel(self._ctx.tr(
            "点击按钮生成一个随机内网 IP + 端口组合，可直接复制到测试表单中。",
            "Click to generate a random private IP + port, ready to paste into test forms.")))

        self._ipEdit = LineEdit(w)
        self._ipEdit.setReadOnly(True)
        self._ipEdit.setPlaceholderText(self._ctx.tr("生成的目标会显示在这里",
                                                     "Generated target appears here"))
        lay.addWidget(self._ipEdit)

        def _gen():
            ip = ".".join(str(random.randint(1, 254)) for _ in range(4))
            port = random.randint(1024, 65535)
            self._ipEdit.setText(f"{ip}:{port}")
            self._count += 1
            self._ctx.set("gen_count", self._count)

        def _copy():
            from PySide6.QtWidgets import QApplication
            text = self._ipEdit.text()
            if text:
                QApplication.clipboard().setText(text)
                InfoBar.success(self._ctx.tr("已复制", "Copied"), text,
                                parent=w.window(), duration=2000)

        genBtn = PushButton(self._ctx.tr("生成随机目标", "Generate Random Target"))
        genBtn.clicked.connect(_gen)
        lay.addWidget(genBtn)

        copyBtn = PushButton(self._ctx.tr("复制", "Copy"))
        copyBtn.clicked.connect(_copy)
        lay.addWidget(copyBtn)

        lay.addWidget(BodyLabel(self._ctx.tr(
            f"历史累计生成 {self._count} 次",
            f"{self._count} generated historically")))
        lay.addStretch(1)
        return w

    def on_unload(self):
        pass
