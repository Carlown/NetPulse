"""启动画面（Splash Screen）：带进度条的圆角启动加载页，支持深色/浅色主题。"""
import json
import os
import sys

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import (QPainter, QPixmap, QFont, QColor, QBrush,
                            QLinearGradient, QRadialGradient, QPainterPath,
                            QRegion)
from PySide6.QtWidgets import QApplication, QSplashScreen

APP_VERSION = "1.0.5"

SPLASH_W = 520
SPLASH_H = 380
RADIUS = 18


def _read_saved_theme() -> bool:
    """快速读取保存的主题设置，不导入完整settings模块。返回True=深色。"""
    try:
        root = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(root, "NetPulse", "settings.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("theme", "light") != "light"
    except Exception:
        pass
    return False  # 默认浅色


def _resource_path(rel: str) -> str:
    """兼容 PyInstaller 打包的资源路径。"""
    if getattr(sys, "_MEIPASS", None):
        return os.path.join(sys._MEIPASS, rel)
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, rel)


def _render_content(progress=0.0, status_text="", shimmer_pos=-0.3, dark=True) -> QPixmap:
    """渲染启动画面内容（不含圆角，由窗口蒙版负责圆角裁剪）。"""
    pm = QPixmap(SPLASH_W, SPLASH_H)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)

    w, h = SPLASH_W, SPLASH_H

    # 创建圆角路径裁剪整个内容区
    content_path = QPainterPath()
    content_path.addRoundedRect(0, 0, w, h, RADIUS, RADIUS)
    p.setClipPath(content_path)

    if dark:
        # === 深色主题 ===
        bg_top = QColor(32, 36, 54)
        bg_bottom = QColor(18, 20, 32)
        glow_color1 = QColor(0, 130, 230, 70)
        glow_color2 = QColor(0, 120, 212, 35)
        line_color = QColor(255, 255, 255, 40)
        name_color = QColor(255, 255, 255)
        sub_color = QColor(130, 140, 165)
        track_color = QColor(255, 255, 255, 22)
        pct_color = QColor(110, 120, 145)
        status_color = QColor(170, 180, 200)
        ver_color = QColor(90, 100, 120)
        icon_color = QColor(0, 120, 212)
        fill_start = QColor(0, 150, 255)
        fill_end = QColor(0, 110, 215)
        hl_color = QColor(255, 255, 255, 90)
        shimmer_color = QColor(255, 255, 255, 100)
    else:
        # === 浅色主题 ===
        bg_top = QColor(250, 251, 255)
        bg_bottom = QColor(238, 242, 250)
        glow_color1 = QColor(0, 120, 212, 30)
        glow_color2 = QColor(0, 100, 200, 18)
        line_color = QColor(0, 0, 0, 20)
        name_color = QColor(30, 35, 50)
        sub_color = QColor(100, 110, 130)
        track_color = QColor(0, 0, 0, 15)
        pct_color = QColor(130, 135, 150)
        status_color = QColor(70, 80, 100)
        ver_color = QColor(160, 165, 180)
        icon_color = QColor(0, 120, 212)
        fill_start = QColor(0, 140, 255)
        fill_end = QColor(0, 100, 200)
        hl_color = QColor(255, 255, 255, 120)
        shimmer_color = QColor(255, 255, 255, 140)

    # 渐变背景
    grad = QLinearGradient(0, 0, 0, h)
    grad.setColorAt(0, bg_top)
    grad.setColorAt(1, bg_bottom)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(0, 0, w, h, RADIUS, RADIUS)

    # 右上角光晕
    glow = QRadialGradient(QPointF(w - 50, 40), 220)
    glow.setColorAt(0, glow_color1)
    glow.setColorAt(1, QColor(glow_color1.red(), glow_color1.green(), glow_color1.blue(), 0))
    p.setBrush(QBrush(glow))
    p.drawRoundedRect(0, 0, w, h, RADIUS, RADIUS)

    # 左下角光晕
    glow2 = QRadialGradient(QPointF(50, h - 80), 160)
    glow2.setColorAt(0, glow_color2)
    glow2.setColorAt(1, QColor(glow_color2.red(), glow_color2.green(), glow_color2.blue(), 0))
    p.setBrush(QBrush(glow2))
    p.drawRoundedRect(0, 0, w, h, RADIUS, RADIUS)

    # 顶部高光细线
    line_grad = QLinearGradient(0, 0, w, 0)
    line_grad.setColorAt(0, QColor(line_color.red(), line_color.green(), line_color.blue(), 0))
    line_grad.setColorAt(0.3, line_color)
    line_grad.setColorAt(0.7, line_color)
    line_grad.setColorAt(1, QColor(line_color.red(), line_color.green(), line_color.blue(), 0))
    p.setBrush(QBrush(line_grad))
    p.drawRect(12, 2, w - 24, 1)

    # Logo
    logo_path = _resource_path("app_logo.png")
    logo_drawn = False
    if os.path.exists(logo_path):
        try:
            logo = QPixmap(logo_path)
            if not logo.isNull():
                logo_size = 110
                scaled = logo.scaled(logo_size, logo_size,
                                     Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_y = 50
                p.drawPixmap(int((w - scaled.width()) / 2), logo_y, scaled)
                logo_drawn = True
        except Exception:
            pass

    if not logo_drawn:
        icon_font = QFont("Segoe UI", 58, QFont.Bold)
        p.setFont(icon_font)
        p.setPen(icon_color)
        p.drawText(0, 45, w, 130, Qt.AlignCenter, "N")
        name_y = 190
    else:
        name_y = 180

    # 应用名称
    name_font = QFont("Segoe UI", 26, QFont.DemiBold)
    p.setFont(name_font)
    p.setPen(name_color)
    p.drawText(0, name_y, w, 44, Qt.AlignCenter, "NetPulse")

    # 副标题
    sub_font = QFont("Segoe UI", 9)
    p.setFont(sub_font)
    p.setPen(sub_color)
    p.drawText(0, name_y + 48, w, 20, Qt.AlignCenter,
               "Network Stress Testing & Performance Monitoring")

    # 进度条
    bar_margin_x = 70
    bar_width = w - bar_margin_x * 2
    bar_height = 5
    bar_y = h - 80

    # 进度条轨道（背景）
    track_rect = QRectF(bar_margin_x, bar_y, bar_width, bar_height)
    p.setPen(Qt.NoPen)
    p.setBrush(track_color)
    p.drawRoundedRect(track_rect, bar_height / 2, bar_height / 2)

    # 进度条填充
    fill_width = bar_width * (progress / 100.0)
    if fill_width > 0.5:
        fill_rect = QRectF(bar_margin_x, bar_y, fill_width, bar_height)
        fill_grad = QLinearGradient(bar_margin_x, bar_y, bar_margin_x + fill_width, bar_y)
        fill_grad.setColorAt(0, fill_start)
        fill_grad.setColorAt(1, fill_end)
        p.setBrush(QBrush(fill_grad))
        p.drawRoundedRect(fill_rect, bar_height / 2, bar_height / 2)

        # 顶部高光
        hl_rect = QRectF(bar_margin_x + 3, bar_y + 1, max(0, fill_width - 6), 1)
        hl_grad = QLinearGradient(hl_rect.left(), 0, hl_rect.right(), 0)
        hl_grad.setColorAt(0, QColor(hl_color.red(), hl_color.green(), hl_color.blue(), 0))
        hl_grad.setColorAt(0.5, hl_color)
        hl_grad.setColorAt(1, QColor(hl_color.red(), hl_color.green(), hl_color.blue(), 0))
        p.setBrush(QBrush(hl_grad))
        p.drawRect(hl_rect)

        # 流光扫光
        if progress < 100:
            shimmer_rel = shimmer_pos
            shimmer_x = bar_margin_x + fill_width * shimmer_rel
            sw = 80.0
            sx = max(bar_margin_x, shimmer_x - sw / 2)
            sw_clamped = min(sw, bar_margin_x + fill_width - sx)
            if sw_clamped > 0:
                sh_rect = QRectF(sx, bar_y, sw_clamped, bar_height)
                sh_grad = QLinearGradient(sh_rect.left(), bar_y, sh_rect.right(), bar_y)
                sh_grad.setColorAt(0, QColor(shimmer_color.red(), shimmer_color.green(), shimmer_color.blue(), 0))
                sh_grad.setColorAt(0.5, shimmer_color)
                sh_grad.setColorAt(1, QColor(shimmer_color.red(), shimmer_color.green(), shimmer_color.blue(), 0))
                p.setBrush(QBrush(sh_grad))
                clip = QPainterPath()
                clip.addRoundedRect(fill_rect, bar_height / 2, bar_height / 2)
                p.setClipPath(clip)
                p.drawRoundedRect(sh_rect, bar_height / 2, bar_height / 2)
                p.setClipping(False)
                # 重置裁剪
                p.setClipPath(content_path)

    # 进度百分比
    pct_font = QFont("Segoe UI", 9)
    p.setFont(pct_font)
    p.setPen(pct_color)
    p.drawText(bar_margin_x, bar_y - 20, bar_width, 16,
               Qt.AlignRight, f"{int(progress)}%")

    # 状态文字
    if status_text:
        status_font = QFont("Segoe UI", 9)
        p.setFont(status_font)
        p.setPen(status_color)
        p.drawText(bar_margin_x, bar_y - 20, bar_width, 16,
                   Qt.AlignLeft, status_text)

    # 版本号
    ver_font = QFont("Segoe UI", 8)
    p.setFont(ver_font)
    p.setPen(ver_color)
    p.drawText(0, h - 22, w - 18, 16, Qt.AlignRight, f"v{APP_VERSION}")

    p.end()
    return pm


class SplashScreen(QSplashScreen):
    """带品牌 Logo、进度条和加载状态文字的圆角启动画面，支持深色/浅色主题。"""

    def __init__(self, dark=True):
        self._dark = dark
        self._progress = 0.0
        self._target_progress = 0
        self._status_text = ""
        self._shimmer_pos = -0.3
        self._main_win = None

        initial_pm = _render_content(self._progress, self._status_text, self._shimmer_pos, self._dark)
        super().__init__(initial_pm)

        # 设置窗口标志：无边框 + 始终在最前
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen)
        # 启用透明背景，实现圆角效果
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)

        # 设置圆角蒙版，让窗口本身就是圆角形状
        self._update_mask()

        # 居中到屏幕
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(
                (sg.width() - SPLASH_W) // 2 + sg.x(),
                (sg.height() - SPLASH_H) // 2 + sg.y()
            )

        # 流光动画定时器
        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.timeout.connect(self._on_tick)
        self._shimmer_timer.start(16)

    def set_dark(self, dark: bool):
        """切换主题（深色/浅色），立即重绘。"""
        if self._dark != dark:
            self._dark = dark
            self._update_pixmap()

    def _update_mask(self):
        """设置窗口圆角蒙版，让窗口四角真正透明。"""
        path = QPainterPath()
        path.addRoundedRect(0, 0, SPLASH_W, SPLASH_H, RADIUS, RADIUS)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def resizeEvent(self, event):
        """窗口大小变化时更新蒙版。"""
        super().resizeEvent(event)
        self._update_mask()

    def _on_tick(self):
        """每一帧更新流光位置并重绘。"""
        self._shimmer_pos += 0.012
        if self._shimmer_pos > 1.3:
            self._shimmer_pos = -0.3
        self._update_pixmap()

    def _update_pixmap(self):
        """更新显示的 pixmap。"""
        pm = _render_content(self._progress, self._status_text, self._shimmer_pos, self._dark)
        self.setPixmap(pm)
        QApplication.processEvents()

    def set_progress(self, percent: int, text: str = ""):
        """设置进度条百分比和状态文字，带平滑动画。"""
        self._target_progress = max(0, min(100, percent))
        if text:
            self._status_text = text

        if not hasattr(self, '_prog_anim') or self._prog_anim is None:
            self._prog_anim = QPropertyAnimation(self, b"_progress_val", self)
            self._prog_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._prog_anim.setDuration(400)
            self._prog_anim.valueChanged.connect(lambda _: self._update_pixmap())
        self._prog_anim.stop()
        self._prog_anim.setStartValue(self._progress)
        self._prog_anim.setEndValue(float(self._target_progress))
        self._prog_anim.start()

    def _get_progress_val(self):
        return self._progress

    def _set_progress_val(self, val):
        self._progress = val

    _progress_val = Property(float, _get_progress_val, _set_progress_val)

    def show_message(self, text: str):
        """兼容旧接口：仅更新文字。"""
        self._status_text = text
        self._update_pixmap()

    def finish_with_window(self, main_window):
        """记录主窗口引用，准备关闭。"""
        self._main_win = main_window

    def finish_splash(self):
        """完成启动：关闭启动画面（主窗口由调用方负责显示）。"""
        self._shimmer_timer.stop()
        if hasattr(self, '_prog_anim') and self._prog_anim and self._prog_anim.state() == QPropertyAnimation.Running:
            self._prog_anim.stop()
        self.close()


def create_splash(dark=None) -> SplashScreen:
    """创建并显示启动画面。dark=None时自动读取保存的主题设置。"""
    if dark is None:
        dark = _read_saved_theme()
    splash = SplashScreen(dark=dark)
    splash.show()
    QApplication.processEvents()
    return splash
