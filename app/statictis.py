# statistic.py
import sqlite3
import sys
import threading
from datetime import datetime
from typing import Dict, List
import time
import psutil
import win32gui
import win32process
import os


def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建的临时文件夹
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")


class AppUsageMonitor:

    def __init__(self, db_file="usage_data.db"):
        self.db_file = db_file
        self.running = False
        self.monitor_thread = None

        # 记录当前正在统计的应用状态
        self.last_active_app = None
        self.start_time = None

        self.init_database()

    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
           CREATE TABLE IF NOT EXISTS app_usage(
               id INTEGER PRIMARY KEY AUTOINCREMENT,  
               app_name TEXT NOT NULL,
               date TEXT NOT NULL,
               usage_time REAL NOT NULL,
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
               UNIQUE(app_name,date)
           )
           ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_app_name_date
            ON app_usage(app_name,date)
        ''')
        conn.commit()
        conn.close()

    def update_usage_data(self, app_name: str, duration: float):
        """更新应用使用时长"""
        # 忽略小于 1 秒的短暂切换
        if duration < 1:
            return

        today = datetime.now().strftime("%Y-%m-%d")
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            cursor.execute('''
                       INSERT OR REPLACE INTO app_usage (app_name, date, usage_time)
                       VALUES (?, ?, 
                           COALESCE((SELECT usage_time FROM app_usage WHERE app_name=? AND date=?), 0) + ?
                       )
                   ''', (app_name, today, app_name, today, duration))
            conn.commit()
            conn.close()
            # print(f"[DEBUG] Saved: {app_name} + {duration:.2f}s")
        except Exception as e:
            print(f"Update usage error: {e}")

    def get_active_process_name(self) -> str:
        """
        核心逻辑：获取当前前台活动窗口的 exe 名称
        """
        try:
            # 1. 获取前台窗口句柄
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return None

            # 2. 获取进程ID (PID)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            # 3. 获取进程名称
            process = psutil.Process(pid)
            name = process.name()

            return name
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return None
        except Exception:
            return None

    # --- 保持原有查询接口不变，兼容你的 GUI ---
    def get_today_usage(self) -> Dict[str, float]:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT app_name, usage_time FROM app_usage WHERE date = ?', (today,))
        results = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in results}

    def get_weekly_usage(self) -> Dict[str, float]:
        from datetime import timedelta
        today = datetime.now()
        week_dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        placeholders = ','.join('?' * len(week_dates))
        query = f'SELECT app_name,SUM(usage_time) FROM app_usage WHERE date IN ({placeholders}) GROUP BY app_name'
        cursor.execute(query, week_dates)
        results = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in results}

    # ... get_monthly_usage 代码保持不变 ...

    def monitor_loop(self):
        """
        新的循环监控逻辑：基于焦点切换
        """
        check_interval = 30.0  # 每30秒检查一次

        # 定义不需要记录的系统进程
        ignore_apps = ['LockApp.exe', 'SearchApp.exe', 'ShellExperienceHost.exe']

        while self.running:
            try:
                current_app = self.get_active_process_name()
                now = time.time()

                if not current_app:
                    time.sleep(check_interval)
                    continue

                # 刚开始运行
                if self.last_active_app is None:
                    self.last_active_app = current_app
                    self.start_time = now

                # 如果切换了应用
                elif current_app != self.last_active_app:
                    # 1. 结算上一个应用的时间
                    duration = now - self.start_time
                    if self.last_active_app not in ignore_apps:
                        self.update_usage_data(self.last_active_app, duration)

                    # 2. 开始记录新应用
                    self.last_active_app = current_app
                    self.start_time = now

                # 如果应用没变，但是时间过长（例如每隔30秒），强制保存一次，防止程序崩溃数据丢失
                elif (now - self.start_time) > 30:
                    duration = now - self.start_time
                    if self.last_active_app not in ignore_apps:
                        self.update_usage_data(self.last_active_app, duration)
                    # 重置开始时间，避免重复叠加
                    self.start_time = now

                time.sleep(check_interval)

            except Exception as e:
                print(f"Monitor loop error: {e}")
                time.sleep(5)

    def start_monitoring(self):
        if self.running: return
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        self.running = False
        # 退出前保存最后一次状态
        if self.last_active_app and self.start_time:
            duration = time.time() - self.start_time
            self.update_usage_data(self.last_active_app, duration)