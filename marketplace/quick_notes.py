# -*- coding: utf-8 -*-
"""NetPulse example plugin: a small bilingual notes page.

The note is stored through PluginContext, so it survives app restarts while
remaining isolated from the host application's other settings.
"""


class Plugin(NetPulsePlugin):
    name = ("快速备注", "Quick Notes")
    version = "1.0"
    author = "NetPulse"
    description = ("记录一条本地备注并显示当前应用版本",
                   "Save a local note and show the current app version")
    icon = "EDIT"
    category = "tool"

    def on_load(self, ctx):
        self._ctx = ctx
        self._note = str(ctx.get("note", ""))

    def create_widget(self, parent):
        from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
        from qfluentwidgets import BodyLabel, PlainTextEdit, PushButton, StrongBodyLabel, InfoBar

        page = QWidget(parent)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 24, 36, 24)
        layout.setSpacing(12)

        layout.addWidget(StrongBodyLabel(
            self._ctx.tr("快速备注", "Quick Notes"), page))
        layout.addWidget(BodyLabel(
            self._ctx.tr(f"当前版本：{self._ctx.app_version}",
                         f"Current version: {self._ctx.app_version}"), page))

        editor = PlainTextEdit(page)
        editor.setPlaceholderText(self._ctx.tr(
            "输入一条本地备注…", "Write a local note…"))
        editor.setPlainText(self._note)
        editor.setMinimumHeight(150)
        layout.addWidget(editor)

        actions = QHBoxLayout()
        save = PushButton(self._ctx.tr("保存备注", "Save note"), page)
        clear = PushButton(self._ctx.tr("清空", "Clear"), page)
        actions.addWidget(save)
        actions.addWidget(clear)
        actions.addStretch(1)
        layout.addLayout(actions)

        def save_note():
            self._note = editor.toPlainText()
            self._ctx.set("note", self._note)
            InfoBar.success(
                self._ctx.tr("已保存", "Saved"),
                self._ctx.tr("备注已保存到插件私有配置。",
                             "The note was saved to plugin-private settings."),
                parent=page.window())

        def clear_note():
            editor.clear()
            self._note = ""
            self._ctx.set("note", "")

        save.clicked.connect(save_note)
        clear.clicked.connect(clear_note)
        return page
