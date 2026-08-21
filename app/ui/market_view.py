# -*- coding: utf-8 -*-
"""插件市场页面：主窗口独立导航页。

- 列表展示市场插件（图标 + 名称/版本/作者/描述 + 安装/更新按钮）
- 图标支持两种形式（索引 entry["icon"]）：
  1) data URI（data:image/png;base64,...）——发布向导自动生成，无需额外托管
  2) http(s) 直链——后台线程下载后显示
- 发布向导：选择本地插件 + 选择本地 PNG/JPG 图标（自动 base64 内嵌），
  生成索引条目 JSON，引导到 GitHub 提交 PR 上架
"""
import base64
import hashlib
import json
import os
import shutil
import tempfile
import threading

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog,
                               QHBoxLayout, QLabel, QVBoxLayout, QWidget)
from qfluentwidgets import (BodyLabel, CaptionLabel, IndeterminateProgressRing,
                            MessageBoxBase, PrimaryPushButton, PushButton,
                            ScrollArea, SimpleCardWidget, StrongBodyLabel,
                            SubtitleLabel)

from app.services.market import INDEX_EDIT_URL, MarketClient
from app.services.plugins import plugin_manager
from app.ui.i18n import L

_ICON_SIZE = 40
_MAX_ICON_BYTES = 64 * 1024  # data URI 图标上限 64KB


def decode_data_uri_icon(v: str):
    """解析 data:image/...;base64,xxx → bytes；失败返回 None。"""
    if not isinstance(v, str) or not v.startswith("data:"):
        return None
    try:
        b64 = v.split(",", 1)[1]
        return base64.b64decode(b64)
    except Exception:
        return None


def load_icon_async(icon_field, callback):
    """异步取图标字节：data URI 立即回调；http(s) 后台下载后回调；无图标不回调。"""
    data = decode_data_uri_icon(icon_field)
    if data is not None:
        callback(data)
        return
    if isinstance(icon_field, str) and icon_field.startswith(("http://", "https://")):
        import requests

        def _work():
            try:
                r = requests.get(icon_field, timeout=8)
                r.raise_for_status()
                data = r.content
                QTimer.singleShot(0, lambda: callback(data))
            except Exception:
                pass
        threading.Thread(target=_work, daemon=True).start()


class PluginIconLabel(QLabel):
    """插件图标：无图标时显示首字母底色块。"""

    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setFixedSize(_ICON_SIZE, _ICON_SIZE)
        self.setAlignment(Qt.AlignCenter)
        name = entry.get("name", "?")
        if isinstance(name, (tuple, list)) and len(name) == 2:
            name = name[0] if L("中", "en") == "中" else name[1]
        self._fallback_text(name)

        def _set(data):
            pm = QPixmap()
            if pm.loadFromData(data):
                self.setPixmap(pm.scaled(_ICON_SIZE, _ICON_SIZE,
                                         Qt.KeepAspectRatio,
                                         Qt.SmoothTransformation))
        load_icon_async(entry.get("icon", ""), _set)

    def _fallback_text(self, name: str):
        ch = (str(name)[:1] or "?").upper()
        self.setText(ch)
        self.setStyleSheet(
            "color:white; font-size:18px; font-weight:600;"
            "background:#0078D4; border-radius:6px;")


class MarketCard(SimpleCardWidget):
    """单个市场插件卡片。"""

    def __init__(self, entry: dict, view: "MarketView", parent=None):
        super().__init__(parent)
        self.entry = entry
        self.view = view
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(14)

        lay.addWidget(PluginIconLabel(entry, self))

        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(StrongBodyLabel(
            f"{self._txt(entry.get('name'))}  v{entry.get('version', '?')}", self))
        meta = " · ".join(str(x) for x in
                          (entry.get("author"), self._txt(entry.get("description"))) if x)
        dlab = CaptionLabel(meta, self)
        dlab.setWordWrap(True)
        col.addWidget(dlab)
        lay.addLayout(col, 1)

        self.btn = PrimaryPushButton(self)
        self.btn.setFixedWidth(96)
        self.btn.clicked.connect(self._install)
        lay.addWidget(self.btn, 0, Qt.AlignVCenter)
        self.refresh_state()

    @staticmethod
    def _txt(v):
        if isinstance(v, (tuple, list)) and len(v) == 2:
            return v[0] if L("中", "en") == "中" else v[1]
        return str(v)

    def refresh_state(self):
        st = MarketClient.installed_state(self.entry)
        if st == "same":
            self.btn.setText(L("已安装", "Installed"))
            self.btn.setEnabled(False)
        elif st == "update":
            self.btn.setText(L("更新", "Update"))
            self.btn.setEnabled(True)
        else:
            self.btn.setText(L("安装", "Install"))
            self.btn.setEnabled(True)

    def _install(self):
        self.btn.setEnabled(False)
        self.btn.setText(L("下载中…", "Downloading…"))
        self.view.install_card(self)


class MarketView(ScrollArea):
    """插件市场导航页。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("marketView")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        root = QVBoxLayout(self.view)
        root.setContentsMargins(36, 24, 36, 24)
        root.setSpacing(16)

        root.addWidget(SubtitleLabel(L("插件市场", "Plugin Marketplace"), self.view))

        # 工具栏
        bar = QHBoxLayout()
        tip = CaptionLabel(L(
            "插件来自社区作者，安装前请自行评估（详见免责声明）。",
            "Plugins are community code; review before installing (see disclaimer)."), self.view)
        bar.addWidget(tip, 1)
        self.pubBtn = PushButton(L("发布插件…", "Publish a Plugin…"), self.view)
        self.pubBtn.clicked.connect(self._publish)
        bar.addWidget(self.pubBtn)
        self.refreshBtn = PushButton(L("刷新", "Refresh"), self.view)
        self.refreshBtn.clicked.connect(self._load)
        bar.addWidget(self.refreshBtn)
        root.addLayout(bar)

        # 状态行
        self.statusLabel = CaptionLabel(L("正在加载市场…", "Loading marketplace…"), self.view)
        root.addWidget(self.statusLabel)
        self.spinner = IndeterminateProgressRing(self.view)
        self.spinner.setFixedSize(28, 28)
        root.addWidget(self.spinner, 0, Qt.AlignCenter)

        # 插件卡片列表
        self.listHost = QWidget(self.view)
        self.listLay = QVBoxLayout(self.listHost)
        self.listLay.setContentsMargins(0, 0, 0, 0)
        self.listLay.setSpacing(8)
        self.listLay.addStretch(1)
        root.addWidget(self.listHost)
        root.addStretch(1)

        self.client = MarketClient()
        self.client.index_ready.connect(self._on_index)
        self.client.fetch_error.connect(self._on_error)
        self.client.download_ready.connect(self._on_downloaded)
        self.client.download_failed.connect(self._on_download_failed)
        # 插件启停/删除后刷新按钮状态
        plugin_manager.changed.connect(lambda: QTimer.singleShot(0, self._refresh_buttons))
        self._load()

    # ---------- 加载 ----------
    def _load(self):
        self.statusLabel.setText(L("正在加载市场…", "Loading marketplace…"))
        self.spinner.show()
        self._clear_cards()
        self.client.fetch_index()

    def _clear_cards(self):
        while self.listLay.count() > 1:
            item = self.listLay.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def _on_index(self, entries, from_cache):
        from app.services.updater import APP_VERSION, _ver_tuple
        self.spinner.hide()
        shown = 0
        for e in entries:
            minv = str(e.get("min_app", ""))
            if minv and _ver_tuple(minv) > _ver_tuple(APP_VERSION):
                continue  # 需要更新程序才能安装，暂不展示
            self.listLay.insertWidget(self.listLay.count() - 1, MarketCard(e, self))
            shown += 1
        src = L("（离线缓存）", " (offline cache)") if from_cache else ""
        if shown:
            self.statusLabel.setText(L(f"共 {shown} 个插件{src}", f"{shown} plugin(s){src}"))
        else:
            self.statusLabel.setText(L(
                f"暂无可安装的插件{src}", f"No installable plugins{src}"))

    def _on_error(self, msg):
        self.spinner.hide()
        self.statusLabel.setText(L(
            f"市场加载失败：{msg}\n请检查网络后点击“刷新”。",
            f"Failed to load marketplace: {msg}\nCheck your network and hit Refresh."))

    def _refresh_buttons(self):
        for i in range(self.listLay.count()):
            w = self.listLay.itemAt(i).widget()
            if isinstance(w, MarketCard):
                w.refresh_state()

    # ---------- 安装流 ----------
    def install_card(self, card: MarketCard):
        self._active_card = card
        self.client.install(card.entry)

    def _on_downloaded(self, entry, tmp_path):
        ok, msg = plugin_manager.import_from(tmp_path)
        try:
            shutil.rmtree(os.path.dirname(tmp_path), ignore_errors=True)
        except Exception:
            pass
        from qfluentwidgets import InfoBar
        if ok:
            InfoBar.success(L("安装成功", "Installed"),
                            L(f"{entry.get('id')} 已安装并启用",
                              f"{entry.get('id')} installed and enabled"),
                            parent=self.window(), duration=4000)
        else:
            InfoBar.error(L("安装失败", "Install failed"), msg,
                          parent=self.window(), duration=6000)
        self._refresh_buttons()

    def _on_download_failed(self, pid, msg):
        from qfluentwidgets import InfoBar
        InfoBar.error(L("下载失败", "Download failed"),
                      L(f"{pid}：{msg}", f"{pid}: {msg}"),
                      parent=self.window(), duration=6000)
        self._refresh_buttons()

    # ---------- 发布 ----------
    def _publish(self):
        PublishDialog(self.window()).exec()


class PublishDialog(MessageBoxBase):
    """发布向导：生成含图标的索引条目 JSON，引导提交 PR 上架。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(L("发布插件到市场", "Publish to Marketplace"))
        self.widget.setMinimumWidth(600)
        self._icon_data_uri = ""

        self.titleLabel = StrongBodyLabel(L("发布插件到市场", "Publish to Marketplace"))
        self.viewLayout.addWidget(self.titleLabel)

        steps = BodyLabel(L(
            "上架流程（免费，无需服务器）：\n"
            "1. 把插件 .py 文件托管到任意可公开直链下载的地址（推荐你自己的 GitHub 仓库）；\n"
            "2. 生成下方条目 JSON，把 file 改成插件的下载直链；\n"
            "3. 打开提交页面，把条目加入 plugins 数组并提交 PR，合并后即上架。",
            "How publishing works (free, no server):\n"
            "1. Host your plugin .py file anywhere publicly downloadable (your GitHub repo recommended);\n"
            "2. Generate the entry below and set file to the direct download URL;\n"
            "3. Open the submission page, add the entry to the plugins array and open a PR. "
            "It goes live once merged."))
        steps.setWordWrap(True)
        self.viewLayout.addWidget(steps)

        row = QHBoxLayout()
        row.addWidget(BodyLabel(L("本地插件", "Local plugin")))
        self.combo = QComboBox()
        for rec in plugin_manager.records():
            if rec.plugin is not None:
                self.combo.addItem(f"{rec.pid} (v{getattr(rec.plugin, 'version', '?')})", rec.pid)
        row.addWidget(self.combo, 1)
        self.viewLayout.addLayout(row)

        # 图标选择
        irow = QHBoxLayout()
        self.iconPreview = QLabel(L("无图标", "No icon"))
        self.iconPreview.setFixedSize(_ICON_SIZE, _ICON_SIZE)
        self.iconPreview.setAlignment(Qt.AlignCenter)
        irow.addWidget(self.iconPreview)
        pickBtn = PushButton(L("选择图标 (PNG/JPG)…", "Pick Icon (PNG/JPG)…"))
        pickBtn.clicked.connect(self._pick_icon)
        irow.addWidget(pickBtn)
        irow.addStretch(1)
        self.viewLayout.addLayout(irow)

        from qfluentwidgets import TextEdit
        self.jsonBox = TextEdit()
        self.jsonBox.setReadOnly(True)
        self.jsonBox.setFixedHeight(190)
        self.viewLayout.addWidget(self.jsonBox)

        btns = QHBoxLayout()
        genBtn = PushButton(L("生成条目", "Generate"))
        genBtn.clicked.connect(self._generate)
        btns.addWidget(genBtn)
        copyBtn = PushButton(L("复制 JSON", "Copy JSON"))
        copyBtn.clicked.connect(self._copy)
        btns.addWidget(copyBtn)
        openBtn = PushButton(L("打开提交页面", "Open Submission Page"))
        openBtn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(INDEX_EDIT_URL)))
        btns.addWidget(openBtn)
        btns.addStretch(1)
        self.viewLayout.addLayout(btns)

        tip = CaptionLabel(L(
            "图标会以 base64 内嵌进索引（上限 64KB），无需额外托管；sha256 用于完整性校验。",
            "The icon is base64-embedded in the index (max 64KB), no extra hosting needed; "
            "sha256 is for integrity."))
        tip.setWordWrap(True)
        self.viewLayout.addWidget(tip)

        self.yesButton.setText(L("关闭", "Close"))
        self.cancelButton.hide()
        QTimer.singleShot(0, self._generate)

    def _pick_icon(self):
        path, _ = QFileDialog.getOpenFileName(
            self, L("选择图标", "Pick an icon"),
            "", L("图片 (*.png *.jpg *.jpeg)", "Images (*.png *.jpg *.jpeg)"))
        if not path:
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception as e:
            from qfluentwidgets import InfoBar
            InfoBar.error(L("读取失败", "Read failed"), str(e), parent=self.window())
            return
        if len(data) > _MAX_ICON_BYTES:
            from qfluentwidgets import InfoBar
            InfoBar.warning(L("图标过大", "Icon too large"),
                            L(f"上限 64KB，当前 {len(data) // 1024}KB",
                              f"Max 64KB, got {len(data) // 1024}KB"),
                            parent=self.window())
            return
        ext = "png" if path.lower().endswith(".png") else "jpeg"
        self._icon_data_uri = f"data:image/{ext};base64," + base64.b64encode(data).decode()
        pm = QPixmap()
        if pm.loadFromData(data):
            self.iconPreview.setPixmap(pm.scaled(_ICON_SIZE, _ICON_SIZE,
                                                 Qt.KeepAspectRatio,
                                                 Qt.SmoothTransformation))
        self._generate()

    def _generate(self):
        pid = self.combo.currentData()
        rec = plugin_manager.record(pid) if pid else None
        if rec is None or rec.plugin is None:
            self.jsonBox.setPlainText("")
            return
        p = rec.plugin
        digest = ""
        try:
            with open(rec.path, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
        except Exception:
            pass

        def _tup(v):
            return list(v) if isinstance(v, (tuple, list)) else [str(v), str(v)]

        entry = {
            "id": rec.pid,
            "name": _tup(getattr(p, "name", rec.pid)),
            "version": str(getattr(p, "version", "1.0")),
            "author": str(getattr(p, "author", "") or ""),
            "description": _tup(getattr(p, "description", "")),
            "file": f"https://raw.githubusercontent.com/YOUR_NAME/YOUR_REPO/main/{rec.pid}.py",
            "sha256": digest,
            "min_app": "1.0.7",
            "homepage": "https://github.com/Carlown/NetPulse",
        }
        if self._icon_data_uri:
            entry["icon"] = self._icon_data_uri
        self.jsonBox.setPlainText(json.dumps(entry, ensure_ascii=False, indent=2))

    def _copy(self):
        QApplication.clipboard().setText(self.jsonBox.toPlainText())
        from qfluentwidgets import InfoBar
        InfoBar.success(L("已复制", "Copied"),
                        L("条目 JSON 已复制到剪贴板", "Entry JSON copied to clipboard"),
                        parent=self.window(), duration=2500)
