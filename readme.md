# Screen Time Monitor

一个用于监控Windows系统中应用程序使用时长的工具，采用Python开发，具有美观的苹果风格界面。

## 功能特点

- 🕐 实时监控前台应用程序使用时间
- 📊 可视化数据显示（今日使用统计和周度排行榜）
- 🖱️ 苹果风格的现代化界面设计
- 📉 系统托盘最小化运行
- 🔧 开机自启动功能
- 📈 图表展示详细使用情况

## 实现思路

### 1. 应用监控机制

通过以下技术栈实现应用使用时长监控：

1. **窗口句柄获取**：使用 `win32gui.GetForegroundWindow()` 获取当前前台窗口句柄
2. **进程信息提取**：通过 `win32process.GetWindowThreadProcessId()` 获取窗口对应的进程ID
3. **应用名称识别**：利用 `psutil.Process(pid).name()` 获取进程名称
4. **时间统计逻辑**：
   - 每30秒检查一次前台应用变化
   - 应用切换时结算前一个应用的使用时间
   - 忽略系统进程（如LockApp.exe等）
   - 长时间使用同一应用时定期保存数据防止丢失

### 2. 数据存储

采用SQLite数据库持久化存储使用数据：

- **数据库结构**：
  - `app_name`: 应用程序名称
  - `date`: 使用日期
  - `usage_time`: 使用时长（秒）
  - `created_at`: 记录创建时间

- **数据聚合**：
  - 按天统计各应用使用时长
  - 支持今日、本周等时间维度查询

### 3. 用户界面

使用PySide6构建现代化图形界面：

- 无边框窗口设计，支持拖拽移动
- 圆角进度条可视化展示应用使用排行
- 系统托盘图标，支持后台运行
- 详细图表展示（使用matplotlib生成）

## 技术架构

```python
# 核心监控类
class AppUsageMonitor:
    def get_active_process_name(self) -> str:  # 获取当前活动进程
    def monitor_loop(self):  # 监控循环
    def update_usage_data(self, app_name: str, duration: float):  # 更新使用数据
```


## 安装与使用

### 环境要求

- Windows 10/11
- Python 3.8+

### 依赖安装

```bash
pip install -r requirements.txt
```


### 运行方式

1. **开发模式**：
   ```bash
   python main.py
   ```


2. **打包运行**：
   使用PyInstaller打包后直接运行生成的exe文件

## 使用说明

1. 启动应用后将在系统托盘运行
2. 点击托盘图标可显示/隐藏主界面
3. 界面展示今日应用使用排行
4. 可查看周度使用情况图表
5. 支持设置开机自启动

## 注意事项

- 应用需管理员权限以获取完整的进程信息
- 首次运行会自动创建数据库文件
- 数据每30秒更新一次以平衡准确性和系统资源消耗