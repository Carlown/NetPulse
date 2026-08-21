# -*- coding: utf-8 -*-
"""插件市场对话框：浏览/安装/更新市场插件；发布向导生成索引条目。"""
import hashlib
import json
import os
import shutil

from PySide6.QtCore import QUrl, Qt, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout,
                               QScrollArea, QVBoxLayout, QWidget)
from qfluentwidgets import (BodyLabel, CaptionLabel, IndeterminateProgressRing,
                            MessageBoxBase, PrimaryPushButton, PushButton,
                            StrongBodyLabel)

from app.services.market import INDEX_EDIT_URL, MarketClient
from app.services.plugins import plugin_manager
from app.ui.i18n import L


class MarketRow(QWidget):
    """市场中单个插件条目。"""

    def __init__(self, entry: dict, dialog: "MarketDialog", parent=None):
        super().__init__(parent)
        self.entry = entry
        self.dialog = dialog
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 10, 4, 10)
        lay.setSpacing(12)

        def _txt(v):
            if isinstance(v, (tuple, list)) and len(v) == 2:
                return v[0] if L("中", "en") == "中" else v[1]
            return str(v)

        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(StrongBodyLabel(
            f"{_txt(entry.get('name'))}  v{entry.get('version', '?')}", self))
        meta = " · ".join(str(x) for x in (entry.get("author"), _txt(entry.get("description"))) if x)
        dlab = CaptionLabel(meta, self)
        dlab.setWordWrap(True)
        col.addWidget(dlab)
        lay.addLayout(col, 1)

        self.btn = PrimaryPushButton(self)
        self.btn.setFixedWidth(96)
        self.btn.clicked.connect(self._install)
        lay.addWidget(self.btn, 0, Qt.AlignTop)
        self.refresh_state()

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
        self.dialog.install_row(self)


class MarketDialog(MessageBoxBase):
    """插件市场：拉取索引 → 列表展示 → 一键安装/更新。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        from app.services.settings import settings
        from app.services.updater import APP_VERSION, is_newer
        self.client = MarketClient()
        self.setWindowTitle(L("插件市场", "Plugin Marketplace"))
        self.widget.setMinimumSize(600, 480)

        vl = QVBoxLayout(self.widget)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(StrongBodyLabel(L("插件市场", "Plugin Marketplace")))
        head.addStretch(1)
        pubBtn = PushButton(L("发布插件…", "Publish a Plugin…"))
        pubBtn.clicked.connect(lambda: PublishDialog(self).exec())
        head.addWidget(pubBtn)
        refreshBtn = PushButton(L("刷新", "Refresh"))
        refreshBtn.clicked.connect(self._load)
        head.addWidget(refreshBtn)
        vl.addLayout(head)

        self.statusLabel = CaptionLabel(L("正在加载市场…", "Loading marketplace…"))
        vl.addWidget(self.statusLabel)

        self.spinner = IndeterminateProgressRing()
        self.spinner.setFixedSize(28, 28)
        vl.addWidget(self.spinner, 0, Qt.AlignCenter)

        self.scroll = QScrollArea(self.widget)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea{border:none;}")
        self.listHost = QWidget()
        self.listLay = QVBoxLayout(self.listHost)
        self.listLay.setContentsMargins(4, 0, 4, 0)
        self.listLay.setSpacing(2)
        self.listLay.addStretch(1)
        self.scroll.setWidget(self.listHost)
        vl.addWidget(self.scroll, 1)

        warn = CaptionLabel(L(
            "市场插件来自社区作者，运行时拥有与主程序相同的权限，请自行评估后再安装。",
            "Marketplace plugins are community code with full app privileges. "
            "Review before installing."))
        warn.setWordWrap(True)
        vl.addWidget(warn)

        self.yesButton.setText(L("关闭", "Close"))
        self.cancelButton.hide()

        self.client.index_ready.connect(self._on_index)
        self.client.fetch_error.connect(self._on_error)
        self.client.download_ready.connect(self._on_downloaded)
        self.client.download_failed.connect(self._on_download_failed)
        # 低于 min_app 的条目不允许安装（API 兼容）
        self._app_ver = APP_VERSION

        self._load()

    def _load(self):
        self.statusLabel.setText(L("正在加载市场…", "Loading marketplace…"))
        self.spinner.show()
        self._clear_rows()
        self.client.fetch_index()

    def _clear_rows(self):
        while self.listLay.count() > 1:
            item = self.listLay.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def _on_index(self, entries, from_cache):
        self.spinner.hide()
        rows = []
        for e in entries:
            # min_app 兼容检查
            minv = str(e.get("min_app", ""))
            if minv:
                from app.services.updater import _ver_tuple
                if _ver_tuple(minv) > _ver_tuple(self._app_ver):
                    rows.append(f'{e.get("id")} (requires app v{minv})')
                    continue
            rows.append(e)
        n = len(rows)
        src = L("（离线缓存）", " (offline cache)") if from_cache else ""
        self.statusLabel.setText(L(f"共 {n} 个插件{src}", f"{n} plugin(s){src}"))
        for e in rows:
            if isinstance(e, str):
                cap = CaptionLabel(e)
                self.listLay.insertWidget(self.listLay.count() - 1, cap)
            else:
                self.listLay.insertWidget(self.listLay.count() - 1, MarketRow(e, self))

    def _on_error(self, msg):
        self.spinner.hide()
        self.statusLabel.setText(L(
            f"市场加载失败：{msg}",
            f"Failed to load marketplace: {msg}"))

    # ---------- 安装流 ----------
    def install_row(self, row: MarketRow):
        self._active_row = row
        self.client.install(row.entry)

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
        # 刷新全部行状态（可能影响同名/更新项）
        for i in range(self.listLay.count()):
            w = self.listLay.itemAt(i).widget()
            if isinstance(w, MarketRow):
                w.refresh_state()

    def _on_download_failed(self, pid, msg):
        from qfluentwidgets import InfoBar
        InfoBar.error(L("下载失败", "Download failed"),
                      L(f"{pid}：{msg}", f"{pid}: {msg}"),
                      parent=self.window(), duration=6000)
        for i in range(self.listLay.count()):
            w = self.listLay.itemAt(i).widget()
            if isinstance(w, MarketRow):
                w.refresh_state()


class PublishDialog(MessageBoxBase):
    """发布向导：生成索引条目 JSON（含 sha256），引导提交 PR 上架。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(L("发布插件到市场", "Publish to Marketplace"))
        self.widget.setMinimumSize(560, 460)

        vl = QVBoxLayout(self.widget)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)
        vl.addWidget(StrongBodyLabel(L("发布插件到市场", "Publish to Marketplace")))
        steps = BodyLabel(L(
            "上架流程（无需服务器，全部免费）：\n"
            "1. 把插件 .py 文件托管到任意可公开直链下载的地址（推荐你自己的 GitHub 仓库）；\n"
            "2. 修改下方生成的条目 JSON，把 file 改成插件的下载直链；\n"
            "3. 打开提交页面，把条目加入 plugins 数组，提交 PR；仓库维护者合并后即上架。",
            "How publishing works (free, no server needed):\n"
            "1. Host your plugin .py file anywhere publicly downloadable (your GitHub repo recommended);\n"
            "2. Edit the generated entry below: set file to the direct download URL;\n"
            "3. Open the submission page, add the entry to the plugins array and open a PR. "
            "It goes live once merged."))
        steps.setWordWrap(True)
        vl.addWidget(steps)

        row = QHBoxLayout()
        row.addWidget(BodyLabel(L("选择本地插件", "Local plugin")))
        self.combo = QComboBox()
        for rec in plugin_manager.records():
            if rec.plugin is not None:
                self.combo.addItem(f"{rec.pid} (v{getattr(rec.plugin, 'version', '?')})", rec.pid)
        row.addWidget(self.combo, 1)
        vl.addLayout(row)

        self.jsonLabel = CaptionLabel(L("生成的条目（file 与 sha256 请按最终托管文件为准）",
                                        "Generated entry (file/sha256 must match the hosted file)"))
        vl.addWidget(self.jsonLabel)

        from qfluentwidgets import TextEdit
        self.jsonBox = TextEdit()
        self.jsonBox.setReadOnly(True)
        self.jsonBox.setFixedHeight(150)
        vl.addWidget(self.jsonBox)

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
        vl.addLayout(btns)

        tip = CaptionLabel(L(
            "sha256 用于完整性校验：托管文件内容变化后必须更新哈希值。",
            "sha256 is for integrity: update the hash whenever the hosted file changes."))
        tip.setWordWrap(True)
        vl.addWidget(tip)

        self.yesButton.setText(L("关闭", "Close"))
        self.cancelButton.hide()
        QTimer.singleShot(0, self._generate)

    def _generate(self):
        pid = self.combo.currentData()
        rec = plugin_manager.record(pid) if pid else None
        if rec is None or rec.plugin is None:
            self.jsonBox.setPlainText("")
            return
        p = rec.plugin
        # 找插件源文件计算 sha256（文件夹插件用其打包前 main.py）
        src = rec.path
        digest = ""
        try:
            with open(src, "rb") as f:
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
        self.jsonBox.setPlainText(json.dumps(entry, ensure_ascii=False, indent=2))

    def _copy(self):
        QApplication.clipboard().setText(self.jsonBox.toPlainText())
        from qfluentwidgets import InfoBar
        InfoBar.success(L("已复制", "Copied"),
                        L("条目 JSON 已复制到剪贴板", "Entry JSON copied to clipboard"),
                        parent=self.window(), duration=2500)
