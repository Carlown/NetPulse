# -*- coding: utf-8 -*-
"""NetPulse 繁體中文語言包：把界面文字即時轉換為繁體中文。

工作原理（純插件實現，不修改宿主代碼）：
1. 替換 app.ui.i18n.L 與 app.services.plugins._i18n_text 兩個翻譯入口，
   並同步替換所有已導入模組中綁定的函數引用——此後新建的介面文字
   （對話框、InfoBar、動態文案、插件名稱等）自動輸出繁體。
2. 遍歷當前全部控制項，把已顯示的簡體文字逐一轉換：標籤、按鈕、
   下拉框選項、選單項、頁簽、工具提示、窗口標題等。
3. 停用 / 卸載 / 重載本插件時自動還原替換；已顯示的繁體文字重啟後恢復簡體。

簡繁映射表內置於本文件（零外部依賴），詞組優先處理一簡多繁歧義
（如「複製 / 恢復」「儘量 / 盡力」）。
"""

import re

# --------------------------------------------------------------------------
# 简繁映射表（简=繁，空格分隔；覆盖 NetPulse 界面全部用字 + 常用扩展）
# --------------------------------------------------------------------------
_ST_PAIRS = """
与=與 专=專 东=東 丢=丟 两=兩 严=嚴 个=個 临=臨 为=為 举=舉 义=義
乐=樂 习=習 书=書 买=買 乱=亂 于=於 产=產 们=們 价=價 众=眾 优=優
会=會 伟=偉 传=傳 伤=傷 侧=側 俭=儉 倾=傾 偿=償 儿=兒 关=關 兴=興
养=養 内=內 册=冊 冲=衝 决=決 况=況 冻=凍 净=淨 凉=涼 减=減 凑=湊
写=寫 区=區 协=協
准=準 几=幾 击=擊 划=劃 则=則 刚=剛 创=創 删=刪 别=別 剑=劍 办=辦
务=務 动=動 励=勵 劳=勞 势=勢 勋=勳 医=醫 华=華 单=單 卖=賣 卫=衛
厂=廠 历=歷 压=壓 厌=厭 县=縣 参=參 双=雙 发=發 变=變 叠=疊 号=號
吗=嗎 听=聽 启=啟 员=員 响=響 团=團 园=園 围=圍 图=圖 圆=圓 场=場
坏=壞 块=塊 坚=堅 墙=牆 声=聲 处=處 备=備 复=複 够=夠 头=頭 夹=夾
实=實 审=審 宽=寬 对=對 导=導 将=將 尝=嘗 尽=盡 层=層 属=屬 帧=幀
带=帶 帮=幫 并=並 广=廣 库=庫 应=應 开=開 异=異 弃=棄 张=張 弹=彈
强=強 归=歸 当=當 录=錄 彻=徹 径=徑 忧=憂 怀=懷 态=態 总=總 恳=懇
恶=惡 悬=懸 惊=驚 惧=懼 惨=慘 愤=憤 愿=願 户=戶 执=執 扩=擴 扫=掃
扬=揚 扰=擾 抛=拋 护=護 报=報 拟=擬 拨=撥 择=擇 挂=掛 挡=擋 挣=掙
挤=擠 挥=揮 损=損 换=換 据=據 携=攜 摆=擺 摇=搖 敌=敵 数=數 断=斷
无=無 旧=舊 时=時 显=顯 晓=曉 晕=暈 暂=暫 万=萬 机=機 权=權 条=條
来=來 极=極 构=構 标=標 栈=棧 栏=欄 样=樣 档=檔 检=檢 欢=歡 残=殘
气=氣 汉=漢 汇=匯 没=沒 浅=淺 测=測 浏=瀏 渐=漸 湾=灣 溃=潰 滚=滾
满=滿 点=點 热=熱 爱=愛 状=狀 独=獨 献=獻 环=環 现=現 电=電 画=畫
畅=暢 监=監 盘=盤 盖=蓋 码=碼 确=確 离=離 种=種 称=稱 稳=穩 筛=篩
签=簽 简=簡 类=類 紧=緊 红=紅 约=約 级=級 线=線 组=組 细=細 终=終
经=經 绑=綁 结=結 绘=繪 给=給 络=絡 绝=絕 统=統 继=繼 绪=緒 续=續
维=維 绿=綠 缓=緩 编=編 缩=縮 网=網 节=節 范=範 荐=薦 获=獲 蓝=藍
装=裝 见=見 观=觀 规=規 视=視 览=覽 觉=覺 触=觸 谢=謝 计=計 订=訂
认=認 让=讓 议=議 记=記 许=許 论=論 设=設 访=訪 证=證 识=識 诊=診
译=譯 试=試 话=話 询=詢 该=該 详=詳 语=語 误=誤 说=說 请=請 读=讀
调=調 负=負 贡=貢 财=財 责=責 败=敗 账=帳 质=質 贴=貼 费=費 资=資
赖=賴 趋=趨 跃=躍 车=車 轨=軌 转=轉 轮=輪 软=軟 轴=軸 轻=輕 载=載
较=較 辑=輯 输=輸 辖=轄 边=邊 达=達 迁=遷 过=過 运=運 还=還 这=這
进=進 远=遠 违=違 连=連 迟=遲 递=遞 逻=邏 适=適 选=選 采=採 释=釋
里=裡 钱=錢 钟=鐘 钮=鈕 链=鏈 销=銷 错=錯 键=鍵 长=長 门=門 闪=閃
闭=閉 问=問 闲=閒 间=間 阅=閱 阈=閾 队=隊 阴=陰 阶=階 际=際 险=險
随=隨 隐=隱 静=靜 页=頁 顶=頂 项=項 顺=順 须=須 预=預 频=頻 题=題
颜=顏 额=額 风=風 飞=飛 馈=饋 驻=駐 验=驗 黄=黃 骤=驟 储=儲 体=體
么=麼 从=從 仅=僅 仓=倉 后=後
"""

# 词组级转换（一简多繁消歧，先于逐字转换执行；输出即为最终繁体）
_WORDS = {
    "头发": "頭髮", "干净": "乾淨", "干扰": "干擾",
    "恢复": "恢復", "复制": "複製", "重复": "重複",
    "日志": "日誌", "合并": "合併", "计划": "計劃", "日历": "日曆",
    "尽量": "儘量", "尽快": "儘快", "尽可能": "儘可能",
}

_S2T = {}
for _pair in _ST_PAIRS.split():
    _k, _v = _pair.split("=")
    _S2T[_k] = _v

_WORDS_SORTED = sorted(_WORDS.items(), key=lambda kv: len(kv[0]), reverse=True)
_HAS_HAN = re.compile("[\u3400-\u9fff\uf900-\ufaff]")


def s2t(s):
    """简体 → 繁体：词组优先，再逐字转换；非字符串或无汉字原样返回。"""
    if not isinstance(s, str) or not _HAS_HAN.search(s):
        return s
    for k, v in _WORDS_SORTED:
        if k in s:
            s = s.replace(k, v)
    return "".join(_S2T.get(c, c) for c in s)


# --------------------------------------------------------------------------
# 翻译入口替换：模块属性 + 所有已导入模块中的函数引用
# --------------------------------------------------------------------------
_patched = False
_orig = {}


def _swap_refs(old, new):
    """把所有已导入模块中绑定的 old 函数引用替换为 new（按对象身份匹配）。"""
    import sys
    for mod in list(sys.modules.values()):
        if mod is None:
            continue
        try:
            ns = vars(mod)
        except TypeError:
            continue
        for k, v in list(ns.items()):
            if v is old:
                try:
                    setattr(mod, k, new)
                except Exception:
                    pass


def install():
    """启用繁体化：替换翻译函数并转换现有界面。重复调用安全。"""
    global _patched
    if _patched:
        return
    import app.ui.i18n as i18n
    import app.services.plugins as pmod

    orig_L = i18n.L
    orig_it = pmod._i18n_text

    def L_tw(zh, en):
        return s2t(orig_L(zh, en))

    def it_tw(v):
        return s2t(orig_it(v))

    _orig["L"] = orig_L
    _orig["_i18n_text"] = orig_it
    i18n.L = L_tw
    pmod._i18n_text = it_tw
    try:
        _swap_refs(orig_L, L_tw)
        _swap_refs(orig_it, it_tw)
    except Exception:
        pass
    _patched = True
    try:
        convert_ui()
    except Exception:
        pass


def uninstall():
    """停用繁体化：还原翻译函数。已显示的繁体文字重启后恢复简体。"""
    global _patched
    if not _patched:
        return
    import app.ui.i18n as i18n
    import app.services.plugins as pmod
    orig_L = _orig.get("L")
    orig_it = _orig.get("_i18n_text")
    if orig_L is not None:
        cur = i18n.L
        i18n.L = orig_L
        try:
            _swap_refs(cur, orig_L)
        except Exception:
            pass
    if orig_it is not None:
        cur = pmod._i18n_text
        pmod._i18n_text = orig_it
        try:
            _swap_refs(cur, orig_it)
        except Exception:
            pass
    _orig.clear()
    _patched = False


# --------------------------------------------------------------------------
# 存量界面转换：遍历控件，逐个转换显示文字
# --------------------------------------------------------------------------
def _set(getter, setter):
    """读取文字 → 转换 → 有变化才写回。任何控件异常都吞掉。"""
    try:
        t = getter()
        if isinstance(t, str) and t:
            nt = s2t(t)
            if nt != t:
                setter(nt)
    except (AttributeError, TypeError, RuntimeError):
        pass


def _convert_widget(w):
    from PySide6.QtWidgets import (QGroupBox, QLineEdit, QPlainTextEdit,
                                   QTextEdit)

    # 1) 可编辑控件：只转换占位提示，绝不动用户输入内容
    if isinstance(w, (QLineEdit, QTextEdit, QPlainTextEdit)):
        _set(w.placeholderText, w.setPlaceholderText)
    else:
        # 2) 通用 text()/setText()：QLabel、各类按钮、导航项、Pivot 项……
        #    （QLineEdit 已在上面排除，不会碰到用户输入；
        #      纯 QWidget 没有 text 属性，用 getattr 探测避免报错）
        text = getattr(w, "text", None)
        setText = getattr(w, "setText", None)
        if callable(text) and callable(setText):
            _set(text, setText)

        # 3) 下拉框选项。注意 qfluentwidgets 的 ComboBox 继承 QPushButton
        #    而非 QComboBox，isinstance 判不到，改用鸭子类型检测。
        itemText = getattr(w, "itemText", None)
        setItemText = getattr(w, "setItemText", None)
        if callable(itemText) and callable(setItemText):
            try:
                n = w.count()
            except (AttributeError, TypeError, RuntimeError):
                n = 0
            for i in range(n):
                _set(lambda i=i: itemText(i),
                     lambda t, i=i: setItemText(i, t))

        # 4) 页签标题（QTabWidget / QTabBar / qfluentwidgets Pivot 等鸭子类型）
        tabText = getattr(w, "tabText", None)
        setTabText = getattr(w, "setTabText", None)
        if callable(tabText) and callable(setTabText):
            try:
                n = w.count()
            except (AttributeError, TypeError, RuntimeError):
                n = 0
            for i in range(n):
                _set(lambda i=i: tabText(i),
                     lambda t, i=i: setTabText(i, t))

        # 5) 分组标题
        if isinstance(w, QGroupBox):
            _set(w.title, w.setTitle)

    # 6) 关联菜单动作（含托盘 RoundMenu、下拉菜单的项）
    for act in w.actions():
        _set(act.text, act.setText)
        _set(act.toolTip, act.setToolTip)

    # 7) 工具提示与窗口标题
    _set(w.toolTip, w.setToolTip)
    _set(w.windowTitle, w.setWindowTitle)


def convert_ui():
    """遍历当前所有控件，把已存在的简体文字转换为繁体（可随时重复调用）。"""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return
    for w in app.allWidgets():
        try:
            _convert_widget(w)
        except Exception:
            continue  # 单个控件异常（如 C++ 对象已销毁）不影响其余转换


# --------------------------------------------------------------------------
# 插件主体
# --------------------------------------------------------------------------
class Plugin(NetPulsePlugin):
    name = ("繁體中文語言包", "Traditional Chinese Language Pack")
    version = "1.0"
    author = "NetPulse"
    description = (
        "將 NetPulse 界面文字即時轉換為繁體中文（啟用即生效，無需重啟）；"
        "停用並重啟後恢復簡體。",
        "Converts the NetPulse UI to Traditional Chinese instantly; "
        "disable and restart to revert.")
    icon = "LANGUAGE"      # FluentIcon 名
    category = "ui"        # 市场分类：界面

    def on_load(self, ctx):
        self._ctx = ctx
        install()

    def on_unload(self):
        uninstall()

    def create_widget(self, parent):
        from PySide6.QtWidgets import QWidget, QVBoxLayout
        from qfluentwidgets import (BodyLabel, InfoBar, PrimaryPushButton,
                                    SimpleCardWidget, SubtitleLabel)

        w = QWidget(parent)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(12)

        card = SimpleCardWidget(w)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(10)
        cl.addWidget(SubtitleLabel(self._ctx.tr("繁體中文語言包",
                                                "Traditional Chinese Language Pack")))
        cl.addWidget(BodyLabel(self._ctx.tr(
            "已啟用：界面文字已轉換為繁體中文，此後打開的視窗與提示也會自動使用繁體。",
            "Enabled: UI text has been converted; newly opened dialogs follow suit.")))
        cl.addWidget(BodyLabel(self._ctx.tr(
            "若個別文字未及時更新，可點擊下方按鈕重新轉換；"
            "停用本插件並重啟軟體即可恢復簡體。",
            "Click the button below to re-convert; disable this plugin and "
            "restart to revert.")))

        btn = PrimaryPushButton(self._ctx.tr("重新轉換界面", "Re-convert UI"))

        def _redo():
            convert_ui()
            InfoBar.success(self._ctx.tr("已重新轉換", "Re-converted"),
                            self._ctx.tr("界面文字已刷新為繁體中文",
                                         "UI text refreshed"),
                            parent=w.window())

        btn.clicked.connect(_redo)
        cl.addWidget(btn)

        lay.addWidget(card)
        lay.addStretch(1)
        return w
