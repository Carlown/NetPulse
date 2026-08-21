# -*- coding: utf-8 -*-
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
