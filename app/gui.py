# from PyQt5.QtWidgets import QStyle
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QScrollArea, QFrame, QPushButton,
                              QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import (QFont, QColor, QPainter, QPen, QBrush, QPixmap,
                           QPainterPath, QIcon)

import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from statictis import AppUsageMonitor
import os
import winreg
import sys


def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建的临时文件夹
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class RoundedBarChartWidget(QWidget):
    """圆角条形图控件，用于显示应用使用时间排行"""

    def __init__(self, data, parent=None):
        """
        初始化圆角条形图
        :param data: 应用使用数据字典 {应用名: 使用时间}
        :param parent: 父组件
        """
        super().__init__(parent)
        self.data = data
        self.max_value = max(data.values()) if data else 1
        self.setFixedHeight(len(data) * 40 + 20)  # 动态设置高度

    def paintEvent(self, event):
        """
        绘制圆角条形图
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 获取排序后的数据（降序）
        sorted_data = sorted(self.data.items(), key=lambda x: x[1], reverse=True)[:10]

        bar_height = 20
        spacing = 20
        left_margin = 120
        right_margin = 20
        top_margin = 10

        available_width = self.width() - left_margin - right_margin

        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.setPen(QColor("#333333"))

        for i, (app_name, value) in enumerate(sorted_data):
            y_pos = top_margin + i * (bar_height + spacing)

            # 绘制应用名称
            metrics = painter.fontMetrics()
            elided_name = metrics.elidedText(app_name, Qt.ElideRight, left_margin - 10)
            painter.drawText(10, y_pos + bar_height // 2 + 5, elided_name)

            # 绘制背景条
            bg_path = QPainterPath()
            bg_rect = QRectF(left_margin, y_pos, available_width, bar_height)
            bg_path.addRoundedRect(bg_rect, bar_height // 2, bar_height // 2)
            painter.fillPath(bg_path, QColor("#F0F0F0"))

            # 绘制进度条
            progress_width = (value / self.max_value) * available_width
            if progress_width > 0:
                progress_path = QPainterPath()
                progress_rect = QRectF(left_margin, y_pos, progress_width, bar_height)
                progress_path.addRoundedRect(progress_rect, bar_height // 2, bar_height // 2)

                # 使用渐变色
                gradient = QBrush(QColor("#0A84FF"))  # 苹果蓝
                painter.fillPath(progress_path, gradient)

            # 绘制数值
            time_text = self.format_time(value)
            text_width = metrics.horizontalAdvance(time_text)
            painter.drawText(left_margin + available_width - text_width - 5,
                             y_pos + bar_height // 2 + 5, time_text)

    def format_time(self, seconds):
        """
        格式化时间显示
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"


class AppleStyleWindow(QMainWindow):
    """主窗口，采用苹果风格设计"""

    def __init__(self):
        """
        初始化主窗口
        """
        super().__init__()
        self.monitor = AppUsageMonitor("usage_data.db")
        self.init_ui()
        self.monitor.start_monitoring()

        # 设置定时器定期刷新数据
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(60000)  # 每分钟刷新一次

        # 初始加载数据
        self.refresh_data()

        # 设置苹果风格外观
        self.setup_apple_style()

        # 添加系统托盘图标
        self.setup_system_tray()

    def setup_system_tray(self):
        """设置系统托盘图标"""
        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)

        # 设置图标
        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # 如果没有图标文件，使用默认图标
            self.tray_icon.setIcon(QIcon())  # 使用空图标

        # 创建托盘菜单
        tray_menu = QMenu()

        # 显示/隐藏窗口动作
        show_action = tray_menu.addAction("显示")
        show_action.triggered.connect(self.show_window)

        # 退出动作
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self.quit_application)

        self.tray_icon.setContextMenu(tray_menu)

        # 连接托盘图标激活信号
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # 显示托盘图标
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        """处理托盘图标点击事件"""
        if reason == QSystemTrayIcon.Trigger:
            # 单击托盘图标时切换显示/隐藏状态
            if self.isHidden():
                self.show_window()
            else:
                self.hide()

    def show_window(self):
        """显示窗口"""
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_application(self):
        """退出应用程序"""
        self.tray_icon.hide()
        self.close()

    def closeEvent(self, event):
        """
        重写关闭事件，实现最小化到托盘
        """
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Screen Time",
            "应用程序已在后台运行",
            QSystemTrayIcon.Information,
            2000
        )

    def setup_apple_style(self):
        """
        设置苹果风格窗口外观
        """
        self.setWindowFlags(Qt.FramelessWindowHint)  # 无边框窗口
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 添加窗口阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

    def set_auto_start(self, enable=True):
        """
        设置开机自启动
        :param enable: True为开启自启动，False为关闭自启动
        """
        # 获取当前程序路径
        app_path = sys.argv[0]

        # 注册表项名称
        app_name = "ScreenTimeMonitor"

        if enable:
            # 打开启动项注册表键
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            # 设置自启动
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
        else:
            # 删除注册表项
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE
                )
                winreg.DeleteValue(key, app_name)
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass  # 如果键不存在则忽略

    def is_auto_start_enabled(self):
        """
        检查是否已设置开机自启动
        :return: True表示已启用，False表示未启用
        """
        app_name = "ScreenTimeMonitor"
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False

    def init_ui(self):
        """
        初始化用户界面
        """
        self.setWindowTitle("Screen Time")
        self.setGeometry(100, 100, 500, 700)

        icon_path = resource_path("icon.png")  # 图标文件路径
        if os.path.exists(icon_path):
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))

        # 创建中央部件
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        central_widget.setStyleSheet("""
            #centralWidget {
                background-color: rgba(255, 255, 255, 230);
                border-radius: 15px;
            }
        """)
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建标题栏
        self.create_header(main_layout)

        # 创建内容区域
        self.create_content_area(main_layout)

        # 创建底部按钮栏
        self.create_footer(main_layout)

    def create_header(self, parent_layout):
        """
        创建标题栏(带窗口控制按钮)
        """
        header = QWidget()
        header.setStyleSheet("""
            background-color: rgba(255, 255, 255, 230);
            border-bottom: 1px solid #EEEEEE;
            border-radius: 15px 15px 0 0;
        """)

        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        # 顶部控制栏
        control_bar = QWidget()
        control_bar.setFixedHeight(30)
        control_bar.setStyleSheet("background-color: transparent;")
        control_layout = QHBoxLayout(control_bar)
        control_layout.setContentsMargins(10, 0, 10, 0)
        control_layout.setAlignment(Qt.AlignRight)

        # 最小化按钮
        minimize_button = QPushButton("—")
        minimize_button.setFixedSize(20, 20)
        minimize_button.setStyleSheet("""
            QPushButton {
                background-color: #FFBD2E;
                border: none;
                border-radius: 10px;
                color: #333;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF9500;
            }
        """)
        minimize_button.clicked.connect(self.showMinimized)

        # 关闭按钮
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #FF5F56;
                border: none;
                border-radius: 10px;
                color: #333;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF3B30;
            }
        """)
        close_button.clicked.connect(self.close)

        control_layout.addWidget(minimize_button)
        control_layout.addWidget(close_button)

        # 标题区域
        title_area = QWidget()
        title_area.setStyleSheet("background-color: transparent;")
        title_layout = QVBoxLayout(title_area)
        title_layout.setContentsMargins(20, 5, 20, 15)

        # 标题
        title_label = QLabel("Screen Time")
        title_label.setFont(QFont("Arial", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #333333;")
        title_layout.addWidget(title_label)

        # 总使用时间
        self.total_time_label = QLabel("Today: 00:00")
        self.total_time_label.setFont(QFont("Arial", 12))
        self.total_time_label.setAlignment(Qt.AlignCenter)
        self.total_time_label.setStyleSheet("color: #888888; margin-top: 5px;")
        title_layout.addWidget(self.total_time_label)

        header_layout.addWidget(control_bar)
        header_layout.addWidget(title_area)

        parent_layout.addWidget(header)

    def create_content_area(self, parent_layout):
        """
        创建内容滚动区域
        """
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
                border-radius: 4px;
                margin: 0px 2px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 0.2);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(0, 0, 0, 0.3);
            }
        """)

        # 内容容器
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(0)
        self.content_layout.setContentsMargins(0, 0, 0, 20)

        scroll_area.setWidget(self.content_widget)
        parent_layout.addWidget(scroll_area)

    def create_footer(self, parent_layout):
        """
        创建底部按钮栏
        """
        footer = QWidget()
        footer.setStyleSheet("""
            background-color: rgba(255, 255, 255, 230);
            border-top: 1px solid #EEEEEE;
            border-radius: 0 0 15px 15px;
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 15, 20, 15)

        # 查看图表按钮
        chart_button = QPushButton("View Detailed Chart")
        chart_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton:pressed {
                background-color: #004799;
            }
        """)
        chart_button.clicked.connect(self.show_chart)

        # 自启动设置按钮
        auto_start_button = QPushButton("Toggle Auto Start")
        auto_start_button.setStyleSheet("""
            QPushButton {
                background-color: #34C759;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2DA448;
            }
            QPushButton:pressed {
                background-color: #218838;
            }
        """)
        auto_start_button.clicked.connect(self.toggle_auto_start)

        footer_layout.addWidget(chart_button)
        footer_layout.addWidget(auto_start_button)

        parent_layout.addWidget(footer)

    def toggle_auto_start(self):
        """切换开机自启动状态"""
        is_enabled = self.is_auto_start_enabled()
        self.set_auto_start(not is_enabled)

        # 显示状态消息
        status = "enabled" if not is_enabled else "disabled"
        self.tray_icon.showMessage(
            "Screen Time",
            f"Auto start has been {status}",
            QSystemTrayIcon.Information,
            2000
        )

    def refresh_data(self):
        """
        刷新应用使用数据
        """
        # 清除现有内容 (保持不变)
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 获取今天的数据
        raw_usage_data = self.monitor.get_today_usage()

        usage_data = {}
        for app_name, duration in raw_usage_data.items():
            clean_name = app_name.replace(".exe", "").replace(".EXE", "")
            clean_name = clean_name.capitalize()

            # 3. 特殊名称映射 (可选)
            name_map = {
                'Winword': 'Word',
                'Excel': 'Excel',
                'Powerpnt': 'PowerPoint',
                'Msedge': 'Edge',
                'Code': 'VS Code',
                'Explorer': '桌面/文件'
            }
            display_name = name_map.get(clean_name, clean_name)

            # 合并时间 (防止 Word.exe 和 WINWORD.EXE 分开计算)
            if display_name in usage_data:
                usage_data[display_name] += duration
            else:
                usage_data[display_name] = duration
        # ---------------------------

        # 计算总使用时间
        total_seconds = sum(usage_data.values())

        # 更新总时间标签
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        self.total_time_label.setText(f"Today: {hours}h {minutes}m")

        # 如果没有数据，显示提示信息
        if not usage_data:
            # ... (保持不变)
            no_data_label = QLabel("No app usage data available")
            no_data_label.setAlignment(Qt.AlignCenter)
            no_data_label.setStyleSheet("""
                color: #888888; 
                padding: 50px;
                font-size: 14px;
            """)
            self.content_layout.addWidget(no_data_label)
            return

        # 创建圆角条形图 (传入清洗后的数据)
        chart_widget = RoundedBarChartWidget(usage_data)
        self.content_layout.addWidget(chart_widget)

    def show_chart(self):
        """
        显示详细使用情况图表
        """
        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False

        # 获取本周数据
        weekly_data = self.monitor.get_weekly_usage()

        if not weekly_data:
            return

        # 按使用时间排序并取前10个应用
        top_apps = dict(sorted(weekly_data.items(), key=lambda x: x[1], reverse=True)[:10])

        # 创建图表窗口
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor('#F5F5F7')  # 苹果浅灰背景

        # 准备数据
        apps = list(top_apps.keys())
        # 修改数据处理行:
        times = [t / 60 for t in top_apps.values()]

        # 创建水平条形图
        bars = ax.barh(range(len(apps)), times, color='#007AFF', height=0.7)

        # 设置Y轴标签
        ax.set_yticks(range(len(apps)))
        ax.set_yticklabels(apps)

        # 设置图表样式
        # 保持x轴标签为小时:
        ax.set_xlabel('Minutes', fontsize=12, color='#333333')
        ax.set_title('Weekly App Usage', fontsize=16, pad=20, color='#333333')
        ax.grid(axis='x', alpha=0.3, color='#CCCCCC')
        ax.set_facecolor('#FFFFFF')

        # 设置坐标轴颜色
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#CCCCCC')
        ax.spines['left'].set_color('#CCCCCC')
        ax.tick_params(colors='#333333')

        # 在条形图上显示数值
        for i, (bar, time_val) in enumerate(zip(bars, times)):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                    f'{time_val:.1f}m', va='center', fontsize=10, color='#333333')

        # 反转Y轴使最长的应用在最上面
        ax.invert_yaxis()

        # 调整布局
        plt.tight_layout()

        # 创建新的Qt窗口显示图表
        chart_window = QMainWindow(self)
        chart_window.setWindowTitle("Detailed Usage Chart")
        chart_window.setGeometry(150, 150, 900, 600)
        # 设置图标
        icon_path = resource_path("icon.png")
        if os.path.exists(icon_path):
            from PySide6.QtGui import QIcon
            chart_window.setWindowIcon(QIcon(icon_path))

        chart_window.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
        """)

        # 创建画布并添加到窗口
        canvas = FigureCanvas(fig)
        chart_window.setCentralWidget(canvas)
        chart_window.show()

    def closeEvent(self, event):
        """
        窗口关闭事件处理
        """
        self.monitor.stop_monitoring()
        event.accept()

    def mousePressEvent(self, event):
        """
        鼠标按下事件，用于实现窗口拖动
        """
        self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
        event.accept()

    def mouseMoveEvent(self, event):
        """
        鼠标移动事件，用于实现窗口拖动
        """
        if hasattr(self, 'drag_position'):
            self.move(event.globalPos() - self.drag_position)
        event.accept()


def main():
    """
    主函数，启动应用程序
    """
    app = QApplication(sys.argv)

    # 设置应用程序样式
    app.setStyle('Fusion')

    # 创建并显示主窗口
    window = AppleStyleWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
