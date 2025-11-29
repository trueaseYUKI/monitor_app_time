import sqlite3
import threading
from datetime import datetime
from typing import Dict, List
import time
import psutil


class AppUsageMonitor:

    def __init__(self,db_file="usage_data.db"):
        """
        初始化应用使用监视器
            Args:
                db_file:SQLite数据库文件路径
        """
        self.db_file = db_file
        self.running = False
        self.current_apps = {} # 存储当前正在运行的应用信息
        self.init_database() # 初始化数据库表结构

    def init_database(self):
        """
        初始化数据库表结构
        :return:
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # 创建应用使用记录表
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

        # 创建索引，提高查询效率
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_app_name_date
            ON app_usage(app_name,date)
        ''')

        # 提交，关闭连接
        conn.commit()
        conn.close()

    def update_usage_data(self,app_name:str,duration:float):
        """
        更新应用的使用时长数据到数据库
        Args：
        :param app_name: 应用名称
        :param duration: 使用时长(s)
        :return:
        """

        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # 使用Insert OR Replace 来更新或插入数据
        cursor.execute('''
                   INSERT OR REPLACE INTO app_usage (app_name, date, usage_time)
                   VALUES (?, ?, 
                       COALESCE((SELECT usage_time FROM app_usage WHERE app_name=? AND date=?), 0) + ?
                   )
               ''', (app_name, today, app_name, today, duration))

        conn.commit()
        conn.close()

    def get_today_usage(self) -> Dict[str,float]:
        """
        获取今天应用的使用情况：
        :return: 应用名称和使用时长的映射
        """
        today = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT app_name,usage_time
            FROM app_usage
            WHERE date = ?
        ''',(today,))

        results = cursor.fetchall()
        conn.close()

        return {row[0]:row[1] for row in results}


    def get_weekly_usage(self)->Dict[str,float]:
        """
        获取本周应用的使用情况：
        :return: 应用名称：使用时长的映射
        """
        from datetime import  timedelta
        today = datetime.now()
        # 这里是将当前天数往前推7天，timedelta(days=i): 表示i天的时间间隔
        week_dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(week_dates))
        cursor.execute(
            f'''
            SELECT app_name,SUM(usage_time)
            FROM app_usage
            WHERE date IN {placeholders}
            GROUP BY app_name
            ''',week_dates)

        results = cursor.fetchall()
        conn.close()

        return {row[0]:row[1] for row in results}

    def get_monthly_usage(self) -> Dict[str, float]:
        """
        获取本月的应用使用情况

        Returns:
            应用名称到使用时长的映射
        """
        today = datetime.now()
        # 统计起始时间：这里替换时间的day为1号
        first_day = today.replace(day=1).strftime('%Y-%m-%d')
        # 统计结束时间：这里使用今天
        last_day = today.strftime('%Y-%m-%d')

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute('''
              SELECT app_name, SUM(usage_time) 
              FROM app_usage 
              WHERE date BETWEEN ? AND ?
              GROUP BY app_name
          ''', (first_day, last_day))

        results = cursor.fetchall()
        conn.close()

        return {row[0]: row[1] for row in results}

    def get_active_window_title(self) -> str:
        """
        获取当前活动窗口的标题（Windows平台）
        :return: 返回当前窗口的标题
        """
        try:
            import win32gui
            return win32gui.GetWindowText(win32gui.GetForegroundWindow())
        except:
            print("[get_active_window_title]获取窗口标题失败")
            return ""

    def get_process_info(self)->List[Dict]:
        """
        获取当前运行的进程信息
        :return: 包含进程信息的列表
        """

        processes = []
        # 获取一个可迭代的进程列表信息
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'exe': proc.info['exe'] or ''
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes  # 添加返回语句

    def monitor_loop(self):
        """
        循环监控，持续收集应用使用数据
        :return:
        """
        error_count = 0
        while self.running:
            try:
                # 获取当前运行的进程
                current_processes = self.get_process_info()
                # active_window = self.get_active_window_title()

                # 处理新启动的应用
                for proc in current_processes:
                    app_name = proc['name']
                    if app_name not in self.current_apps:
                        # 新应用启动，记录开始时间
                        self.current_apps[app_name] = {
                            'start_time': time.time(),
                            'last_update': time.time()
                        }
                    else:
                        # 已运行应用，更新使用时长
                        now = time.time()
                        duration = now - self.current_apps[app_name]['last_update']
                        self.current_apps[app_name]['last_update'] = now
                        self.update_usage_data(app_name, duration)

                # 处理已关闭的应用
                current_names = [proc['name'] for proc in current_processes]
                closed_apps = set(self.current_apps.keys()) - set(current_names)
                for app_name in closed_apps:
                    # 计算最终使用时长并移除记录
                    duration = time.time() - self.current_apps[app_name]['start_time']
                    self.update_usage_data(app_name, duration)
                    del self.current_apps[app_name]

                time.sleep(60+(2 * error_count))  # 每60s检查一次，每次出问题就往后多推迟出错次数 * 2s

            except Exception as e:
                error_count += 1
                print(f"监控过程中出现错误: {e}")
                time.sleep(20)

    def start_monitoring(self):
        """
        启动监控线程
        :return:
        """
        self.running = True
        self.current_apps = {}  # 初始化当前应用记录
        # 这里线程启动运行monitor_loop方法
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """
        停止监控并保存数据
        """
        self.running = False
        # 保存剩余的应用使用数据
        for app_name in list(self.current_apps.keys()):
            duration = time.time() - self.current_apps[app_name]['start_time']
            self.update_usage_data(app_name, duration)