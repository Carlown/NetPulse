"""首次启动免责声明与目标授权对话框。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from qfluentwidgets import BodyLabel, CheckBox, MessageBoxBase, SubtitleLabel, TextEdit

from app.ui.i18n import L

DISCLAIMER_ZH = (
    "本工具仅用于对您拥有所有权或已获得书面授权的目标进行性能测试。\n\n"
    "1. 未经授权对他人系统进行压力测试在大多数司法辖区属于违法行为；\n"
    "2. 您需确保测试速率与并发在目标系统承受范围内；\n"
    "3. 所有测试操作将被记录审计日志；\n"
    "4. 使用本工具产生的一切后果由使用者本人承担。\n\n"
    "继续使用即表示您已阅读、理解并同意以上条款。"
)

DISCLAIMER_EN = (
    "This tool is ONLY for performance testing targets you own or have written authorization for.\n\n"
    "1. Stress testing systems without authorization is illegal in most jurisdictions;\n"
    "2. You must ensure the rate and concurrency stay within the target's capacity;\n"
    "3. All test operations are recorded in the audit log;\n"
    "4. You assume full responsibility for any consequences of using this tool.\n\n"
    "By continuing you confirm that you have read, understood and agree to the terms above."
)


class DisclaimerDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(L("免责声明与使用条款", "Disclaimer & Terms of Use"), self)
        self.contentLabel = BodyLabel(DISCLAIMER_ZH if settings_lang() else DISCLAIMER_EN, self)
        self.contentLabel.setWordWrap(True)
        self.agreeBox = CheckBox(L("我已知晓并同意以上全部条款", "I have read and agree to all terms above"), self)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.contentLabel)
        self.viewLayout.addWidget(self.agreeBox)

        self.yesButton.setText(L("接受", "Accept"))
        self.yesButton.setEnabled(False)
        self.cancelButton.setText(L("退出", "Exit"))
        self.agreeBox.toggled.connect(lambda c: self.yesButton.setEnabled(c))
        self.widget.setMinimumWidth(520)


class AuthDialog(MessageBoxBase):
    """目标授权确认：勾选两项 + 填写授权说明。"""

    def __init__(self, host: str, parent: QWidget = None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel(L("目标授权确认", "Target Authorization"), self)
        self.hostLabel = BodyLabel(L(f"目标：{host}", f"Target: {host}"), self)
        self.cb1 = CheckBox(L("我确认拥有该目标，或已获得目标所有者的书面授权",
                              "I own this target or have written authorization from its owner"), self)
        self.cb2 = CheckBox(L("我理解未授权压测属违法行为，并愿意承担全部法律责任",
                              "I understand unauthorized stress testing is illegal and I accept full liability"), self)
        self.noteEdit = TextEdit(self)
        self.noteEdit.setPlaceholderText(L("授权说明（必填，如：自有服务器 / 合同编号等）",
                                           "Authorization note (required, e.g. own server / contract no.)"))
        self.noteEdit.setFixedHeight(72)

        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.hostLabel)
        self.viewLayout.addWidget(self.cb1)
        self.viewLayout.addWidget(self.cb2)
        self.viewLayout.addWidget(self.noteEdit)

        self.yesButton.setText(L("确认授权", "Confirm"))
        self.yesButton.setEnabled(False)
        self.cancelButton.setText(L("取消", "Cancel"))
        self.widget.setMinimumWidth(520)

        self.cb1.toggled.connect(self._check)
        self.cb2.toggled.connect(self._check)
        self.noteEdit.textChanged.connect(self._check)

    def note(self):
        return self.noteEdit.toPlainText().strip()

    def _check(self):
        self.yesButton.setEnabled(self.cb1.isChecked() and self.cb2.isChecked()
                                  and len(self.note()) >= 3)


def settings_lang():
    from app.services.settings import settings
    return settings.language == "zh-CN"
