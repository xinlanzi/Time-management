import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import requests
import json
from datetime import datetime, timedelta
import pytz
import http.client
import threading
import time
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# ---------------------- 配置参数 ----------------------
OPENAI_API_KEY = "sk-VRUmYADdlWqzDldwsgBheyhoQpjwomEA5rO3zA7jdS4wa2Fp"  # 替换为你的API密钥
BASE_URL = "api.metaihub.cn"
DB_NAME = "time_management.db"
TIMEZONE = pytz.timezone("Asia/Shanghai")
REMINDER_TIME = 3  # 任务开始前提醒分钟数

# ---------------------- 工具函数 ----------------------
def get_current_time():
    """获取当前时间字符串"""
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

def get_current_date():
    """获取当前日期字符串"""
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d")

def str_to_datetime(time_str):
    """字符串转datetime对象"""
    return TIMEZONE.localize(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S"))

def datetime_to_str(dt):
    """datetime对象转字符串"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_days_in_month(year, month):
    """获取指定月份的所有日期"""
    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year
    
    # 获取当月第一天
    first_day = datetime(year, month, 1)
    # 获取下个月第一天
    next_first_day = datetime(next_year, next_month, 1)
    # 计算当月天数
    days_in_month = (next_first_day - first_day).days
    
    return [datetime(year, month, day) for day in range(1, days_in_month + 1)]

def is_time_expired(time_str):
    """判断时间是否已过期"""
    try:
        task_time = str_to_datetime(time_str)
        return task_time < datetime.now(TIMEZONE)
    except:
        return False

def get_weekday_name(weekday):
    """将0-6的星期数转换为中文星期名"""
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return weekdays[weekday]

# 首先在工具函数部分添加一个计算屏幕右下角位置的函数
def get_bottom_right_position(width, height):
    """计算屏幕右下角的位置坐标"""
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()
    # 右下角留出一点边距
    x = screen_width - width - 20
    y = screen_height - height - 80  # 考虑任务栏高度
    return f"{width}x{height}+{x}+{y}"

# ---------------------- 数据库初始化 ----------------------
def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            create_time TEXT NOT NULL
        )
    ''')
    
    # 任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status INTEGER DEFAULT 0,  -- 0:未开始 1:进行中 2:已完成
            create_time TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# ---------------------- 内存存储（用于游客模式） ----------------------
class InMemoryStorage:
    """内存存储类，用于游客模式的数据管理"""
    def __init__(self):
        self.tasks = []  # 存储格式: (task_id, task_name, start_time, end_time, status)
        self.next_task_id = 1  # 自增ID
    
    def add_task(self, task_name, start_time, end_time):
        """添加任务"""
        # 检查时间冲突
        for task in self.tasks:
            _, _, s, e, status = task
            if status != 2 and (
                (s < end_time and e > start_time) or
                (s < end_time and e > start_time)
            ):
                return False, "任务时间冲突", None
        
        task_id = self.next_task_id
        self.tasks.append((task_id, task_name, start_time, end_time, 0))
        self.next_task_id += 1
        return True, "任务添加成功", task_id
    
    def get_today_tasks(self):
        """获取今日任务"""
        today = get_current_date()
        return [task for task in self.tasks if task[2].startswith(today)]
    
    def update_task_status(self, task_id, status):
        """更新任务状态"""
        for i, task in enumerate(self.tasks):
            if task[0] == task_id:
                self.tasks[i] = (task[0], task[1], task[2], task[3], status)
                return True, "状态更新成功"
        return False, "任务不存在"
    
    def get_weekly_tasks(self):
        """获取本周所有任务"""
        today = datetime.now(TIMEZONE)
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        start_date = monday.strftime("%Y-%m-%d")
        end_date = sunday.strftime("%Y-%m-%d")
        
        weekly_tasks = []
        for task in self.tasks:
            task_date = task[2].split(" ")[0]
            if start_date <= task_date <= end_date:
                weekly_tasks.append(task)
        
        return weekly_tasks, start_date, end_date
    
    def delete_task(self, task_id):
        """删除任务"""
        for i, task in enumerate(self.tasks):
            if task[0] == task_id:
                deleted_task = self.tasks.pop(i)
                return True, "任务已删除", deleted_task
        return False, "任务不存在", None
    
    def add_recurring_tasks(self, task_name, start_time_str, end_time_str, recurrence_type, weekdays=None):
        """添加固定重复任务"""
        try:
            # 解析时间部分
            start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
            end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
            
            # 获取当前月份
            now = datetime.now(TIMEZONE)
            year, month = now.year, now.month
            
            # 获取当月所有日期
            month_days = get_days_in_month(year, month)
            
            # 筛选符合条件的日期
            target_days = []
            if recurrence_type == 'daily':
                target_days = month_days
            elif recurrence_type == 'weekly' and weekdays:
                for day in month_days:
                    if day.weekday() in weekdays:
                        target_days.append(day)
            
            if not target_days:
                return False, "没有符合条件的日期", None
            
            added_task_ids = []
            for day in target_days:
                # 组合日期和时间
                task_start = datetime.combine(day, start_time)
                task_end = datetime.combine(day, end_time)
                
                # 转换为带时区的datetime
                task_start_tz = TIMEZONE.localize(task_start)
                task_end_tz = TIMEZONE.localize(task_end)
                
                # 检查时间是否已过
                if task_end_tz < datetime.now(TIMEZONE):
                    continue
                
                # 检查冲突
                conflict = False
                for t in self.tasks:
                    _, _, s, e, status = t
                    if status != 2 and (
                        (s < datetime_to_str(task_end_tz) and e > datetime_to_str(task_start_tz)) or
                        (s < datetime_to_str(task_end_tz) and e > datetime_to_str(task_start_tz))
                    ):
                        conflict = True
                        break
                
                if not conflict:
                    task_id = self.next_task_id
                    self.tasks.append((
                        task_id,
                        task_name,
                        datetime_to_str(task_start_tz),
                        datetime_to_str(task_end_tz),
                        0
                    ))
                    added_task_ids.append(task_id)
                    self.next_task_id += 1
            
            if added_task_ids:
                return True, f"成功添加 {len(added_task_ids)} 个任务", added_task_ids
            else:
                return False, "没有添加任何任务，可能全部时间冲突或已过期", None
                
        except Exception as e:
            return False, f"添加失败: {str(e)}", None

    # 更新任务的方法
    def update_task(self, task_id, new_name=None, new_start=None, new_end=None):
        """更新任务信息"""
        for i, task in enumerate(self.tasks):
            if task[0] == task_id:
                # 保留原信息，只更新提供的新值
                name = new_name if new_name else task[1]
                start = new_start if new_start else task[2]
                end = new_end if new_end else task[3]
                
                # 检查时间冲突（如果时间有变更）
                if new_start or new_end:
                    for t in self.tasks:
                        if t[0] != task_id and t[4] != 2 and (
                            (t[2] < end and t[3] > start) or
                            (start < t[3] and end > t[2])
                        ):
                            return False, "任务时间冲突"
                
                self.tasks[i] = (task[0], name, start, end, task[4])
                return True, "任务更新成功"
        return False, "任务不存在"

# ---------------------- AI助手类 ----------------------
class AIAssistant:
    """AI助手类"""
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Apifox/1.0.0(https://www.apifox.cn)",
            "Content-Type": "application/json"
        }

    def parse_task(self, user_input, historical_tasks=None):
        """解析任务信息，结合历史任务数据给出合理时间建议"""
        if not self.api_key:
            return {"error": "请配置API密钥"}
        
        # 构建历史任务提示信息
        history_prompt = ""
        if historical_tasks:
            history_prompt = "用户历史任务安排参考：\n"
            for task in historical_tasks[:5]:  # 取最近5个任务作为参考
                task_id, name, start, end, status = task
                history_prompt += f"- {name}: {start} 至 {end}\n"
            history_prompt += "\n请参考用户的历史任务时间安排习惯，推荐合理的任务时间，避免冲突\n"
        
        # 提示词优化，加入历史任务参考
        prompt = f"""
            {history_prompt}
            请解析以下任务描述，提取或推荐合适的开始时间、结束时间和任务名称，
            按以下格式返回（每行一个键值对，用=分隔）：
            task_name=任务名称
            start_time=YYYY-MM-DD HH:MM:SS
            end_time=YYYY-MM-DD HH:MM:SS
            如果没有指定时间，请根据用户历史习惯推荐合理的时间，默认时长1小时
            当前时间: {get_current_time()}
            任务描述: {user_input}
        """
        
        try:
            conn = http.client.HTTPSConnection(BASE_URL)
            conn.request("POST", "/v1/chat/completions", body=json.dumps({
                "model": "gpt-5-codex",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,  # 降低随机性，提高时间安排的合理性
                "max_tokens": 2048
            }), headers=self.headers)
            response = conn.getresponse()
            data = response.read()
            json_data = json.loads(data)
            raw_response = json_data["choices"][0]["message"]["content"].strip()

            # 解析键值对格式为字典
            task_info = {}
            for line in raw_response.split('\n'):
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    task_info[key.strip()] = value.strip()

            # 验证必要字段
            required = ["task_name", "start_time", "end_time"]
            if not all(k in task_info for k in required):
                return {"error": "AI返回信息不完整，缺少必要字段"}
            
            return task_info

        except Exception as e:
            return {"error": f"解析失败: {str(e)}"}

# ---------------------- 任务管理类 ----------------------
class TaskManager:
    """任务管理类"""
    def __init__(self, user_id, is_guest=False):
        self.user_id = user_id
        self.is_guest = is_guest
        if self.is_guest:
            self.memory_storage = InMemoryStorage()
        
    def add_task(self, task_name, start_time, end_time):
        """添加任务"""
        if self.is_guest:
            return self.memory_storage.add_task(task_name, start_time, end_time)
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            # 检查时间冲突
            if self.check_conflict(start_time, end_time):
                return False, "任务时间冲突", None
                
            cursor.execute('''
                INSERT INTO tasks (user_id, task_name, start_time, end_time, create_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.user_id, task_name, start_time, end_time, get_current_time()))
            conn.commit()
            task_id = cursor.lastrowid  # 获取刚插入的任务ID
            return True, "任务添加成功", task_id
        except Exception as e:
            return False, f"添加失败: {str(e)}", None
        finally:
            conn.close()
    
    def check_conflict(self, start_time, end_time, exclude_task_id=None):
        """检查时间冲突，可排除指定任务ID"""
        if self.is_guest:
            for task in self.memory_storage.tasks:
                if (exclude_task_id is None or task[0] != exclude_task_id) and task[4] != 2 and (
                    (task[2] < end_time and task[3] > start_time) or
                    (start_time < task[3] and end_time > task[2])
                ):
                    return True
            return False
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM tasks 
            WHERE user_id=? AND status != 2 
            AND (
                (start_time < ? AND end_time > ?) OR
                (start_time < ? AND end_time > ?)
            )
        '''
        params = [self.user_id, end_time, start_time, end_time, start_time]
        
        # 如果有排除的任务ID，添加条件
        if exclude_task_id is not None:
            query += " AND task_id != ?"
            params.append(exclude_task_id)
        
        cursor.execute(query, params)
        conflict = cursor.fetchone() is not None
        conn.close()
        return conflict
    
    def get_today_tasks(self):
        """获取今日任务，包含超时判断"""
        if self.is_guest:
            tasks = self.memory_storage.get_today_tasks()
        else:
            today = get_current_date()
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT task_id, task_name, start_time, end_time, status 
                FROM tasks 
                WHERE user_id=? AND start_time LIKE ? 
                ORDER BY start_time
            ''', (self.user_id, f"{today}%"))
            
            tasks = cursor.fetchall()
            conn.close()
        
        # 检查并更新已超时但未完成的任务状态
        updated_tasks = []
        for task in tasks:
            task_id, name, start, end, status = task
            # 3表示已超时状态
            if status in [0, 1] and is_time_expired(end):
                if self.is_guest:
                    self.memory_storage.update_task_status(task_id, 3)
                else:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE tasks SET status=3 WHERE task_id=? AND user_id=?",
                        (task_id, self.user_id)
                    )
                    conn.commit()
                    conn.close()
                updated_tasks.append((task_id, name, start, end, 3))
            else:
                updated_tasks.append(task)
        
        return updated_tasks
    
    def update_task(self, task_id, new_name=None, new_start=None, new_end=None):
        """更新任务信息"""
        if self.is_guest:
            return self.memory_storage.update_task(task_id, new_name, new_start, new_end)
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            # 获取当前任务信息
            cursor.execute(
                "SELECT task_name, start_time, end_time FROM tasks WHERE task_id=? AND user_id=?",
                (task_id, self.user_id)
            )
            task = cursor.fetchone()
            if not task:
                return False, "任务不存在"
                
            # 保留原信息，只更新提供的新值
            name = new_name if new_name else task[0]
            start = new_start if new_start else task[1]
            end = new_end if new_end else task[2]
            
            # 检查时间冲突（如果时间有变更）
            if new_start or new_end:
                if self.check_conflict(start, end, exclude_task_id=task_id):
                    return False, "任务时间冲突"
            
            # 更新任务
            cursor.execute('''
                UPDATE tasks SET task_name=?, start_time=?, end_time=? 
                WHERE task_id=? AND user_id=?
            ''', (name, start, end, task_id, self.user_id))
            conn.commit()
            return True, "任务更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"
        finally:
            conn.close()

    def update_task_status(self, task_id, status):
        """更新任务状态"""
        if self.is_guest:
            return self.memory_storage.update_task_status(task_id, status)
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "UPDATE tasks SET status=? WHERE task_id=? AND user_id=?",
                (status, task_id, self.user_id)
            )
            conn.commit()
            return True, "状态更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"
        finally:
            conn.close()

    def get_weekly_tasks(self):
        """获取本周所有任务（从周一到周日）"""
        if self.is_guest:
            return self.memory_storage.get_weekly_tasks()
            
        today = datetime.now(TIMEZONE)
        # 计算本周一的日期
        monday = today - timedelta(days=today.weekday())
        # 计算本周日的日期
        sunday = monday + timedelta(days=6)
        
        # 格式化日期字符串
        start_date = monday.strftime("%Y-%m-%d")
        end_date = sunday.strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT task_id, task_name, start_time, end_time, status 
            FROM tasks 
            WHERE user_id=? 
            AND start_time BETWEEN ? AND ? 
            ORDER BY start_time
        ''', (self.user_id, f"{start_date} 00:00:00", f"{end_date} 23:59:59"))
        
        tasks = cursor.fetchall()
        conn.close()
        return tasks, start_date, end_date
    
    def delete_task(self, task_id):
        """删除任务并返回被删除的任务信息用于撤销"""
        if self.is_guest:
            return self.memory_storage.delete_task(task_id)
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            # 先查询任务信息
            cursor.execute(
                "SELECT task_name, start_time, end_time, status FROM tasks WHERE task_id=? AND user_id=?",
                (task_id, self.user_id)
            )
            task = cursor.fetchone()
            if not task:
                return False, "任务不存在", None
                
            # 删除任务
            cursor.execute(
                "DELETE FROM tasks WHERE task_id=? AND user_id=?",
                (task_id, self.user_id)
            )
            conn.commit()
            # 返回被删除的任务信息
            return True, "任务已删除", (task_id, task[0], task[1], task[2], task[3])
        except Exception as e:
            return False, f"删除失败: {str(e)}", None
        finally:
            conn.close()

    def add_recurring_tasks(self, task_name, start_time_str, end_time_str, recurrence_type, weekdays=None):
        """添加固定重复任务"""
        if self.is_guest:
            return self.memory_storage.add_recurring_tasks(
                task_name, start_time_str, end_time_str, recurrence_type, weekdays
            )
            
        try:
            # 解析时间部分（忽略日期）
            start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
            end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
            
            # 获取当前月份
            now = datetime.now(TIMEZONE)
            year, month = now.year, now.month
            
            # 获取当月所有日期
            month_days = get_days_in_month(year, month)
            
            # 筛选符合条件的日期
            target_days = []
            if recurrence_type == 'daily':
                # 每天都添加
                target_days = month_days
            elif recurrence_type == 'weekly' and weekdays:
                # 只添加指定星期几的日期
                for day in month_days:
                    # weekday()返回0-6，0是周一
                    if day.weekday() in weekdays:
                        target_days.append(day)
            
            if not target_days:
                return False, "没有符合条件的日期"
            
            # 批量添加任务
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # 记录添加成功的任务ID
            added_task_ids = []
            
            for day in target_days:
                # 组合日期和时间
                task_start = datetime.combine(day, start_time)
                task_end = datetime.combine(day, end_time)
                
                # 转换为带时区的datetime
                task_start_tz = TIMEZONE.localize(task_start)
                task_end_tz = TIMEZONE.localize(task_end)
                
                # 检查时间是否已过
                if task_end_tz < datetime.now(TIMEZONE):
                    continue
                
                # 检查冲突
                if not self.check_conflict(
                    datetime_to_str(task_start_tz), 
                    datetime_to_str(task_end_tz)
                ):
                    cursor.execute('''
                        INSERT INTO tasks (user_id, task_name, start_time, end_time, create_time)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        self.user_id, 
                        task_name, 
                        datetime_to_str(task_start_tz), 
                        datetime_to_str(task_end_tz), 
                        get_current_time()
                    ))
                    added_task_ids.append(cursor.lastrowid)
            
            conn.commit()
            conn.close()
            
            if added_task_ids:
                return True, f"成功添加 {len(added_task_ids)} 个任务", added_task_ids
            else:
                return False, "没有添加任何任务，可能全部时间冲突或已过期"
                
        except Exception as e:
            return False, f"添加失败: {str(e)}", None

# ---------------------- 用户管理类 ----------------------
class UserManager:
    """用户管理类"""
    def __init__(self):
        self.current_user = None  # 格式: (user_id, username, is_guest)
        self.guest_user_id = -1
        self.guest_username = "游客"
        
    def login(self, username, password):
        """登录"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id, username FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.current_user = (user[0], user[1], False)
            return True, "登录成功"
        return False, "用户名或密码错误"
    
    def register(self, username, password):
        """注册"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, password, create_time) VALUES (?, ?, ?)",
                (username, password, get_current_time())
            )
            conn.commit()
            return True, "注册成功"
        except sqlite3.IntegrityError:
            return False, "用户名已存在"
        finally:
            conn.close()
    
    def logout(self):
        """登出"""
        self.current_user = None
        return True, "登出成功"
    
    def enter_guest_mode(self):
        """进入游客模式"""
        self.current_user = (self.guest_user_id, self.guest_username, True)
        return True, "已进入游客模式"

# ---------------------- 主应用类 ----------------------
class TimeManagementApp:
    """主应用类"""
    def __init__(self, root):
        self.root = root
        self.root.title("时间管理系统")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 初始化组件
        self.user_manager = UserManager()
        self.ai_assistant = AIAssistant(OPENAI_API_KEY)
        self.task_manager = None
        
        # 撤销功能相关
        self.undo_stack = []  # 存储被删除的任务信息用于撤销
        self.weekly_window = None  # 用于引用每周任务窗口
        
        # 初始化数据库
        init_database()
        
        # 创建界面
        self.create_login_ui()
        
        # 实时时间更新
        self.time_label = None
        self.update_time()
        
        # 绑定Ctrl+Z快捷键
        self.root.bind("<Control-z>", self.undo_delete)

        # 添加任务提醒相关变量
        self.reminder_checking = False
        self.reminder_thread = None
        
        # 启动任务提醒检查
        self.start_reminder_check()

    def start_reminder_check(self):
        """启动任务提醒检查线程"""
        if not self.reminder_checking:
            self.reminder_checking = True
            self.reminder_thread = threading.Thread(target=self.check_reminders, daemon=True)
            self.reminder_thread.start()
    
    # 在check_reminders方法中添加对结束时间的检查
    def check_reminders(self):
        """定时检查是否有即将开始或结束的任务"""
        while self.reminder_checking:
            if self.task_manager:  # 确保任务管理器已初始化
                # 获取今天所有未完成的任务
                today_tasks = self.task_manager.get_today_tasks()
                now = datetime.now(TIMEZONE)
                
                for task in today_tasks:
                    task_id, task_name, start_time_str, end_time_str, status = task
                    
                    # 检查即将开始的任务
                    if status in [0, 1]:
                        try:
                            start_time = str_to_datetime(start_time_str)
                            # 计算时间差（秒）
                            time_diff = (start_time - now).total_seconds()
                            
                            # 检查是否在提醒时间范围内（正负5秒，防止错过）
                            if abs(time_diff) <= 5:
                                # 在主线程中显示提醒窗口
                                self.root.after(0, lambda t=task: self.show_task_reminder(t))
                                # 避免重复提醒，暂时标记为已提醒（实际状态不变）
                                time.sleep(10)  # 10秒内不再提醒同一个任务
                        except Exception as e:
                            print(f"检查任务开始提醒时出错: {e}")
                    
                    # 检查进行中任务是否到达结束时间
                    if status == 1:  # 只处理进行中的任务
                        try:
                            end_time = str_to_datetime(end_time_str)
                            # 计算时间差（秒）
                            time_diff = (end_time - now).total_seconds()
                            
                            # 检查是否在结束时间前后5秒内
                            if abs(time_diff) <= 5:
                                # 在主线程中显示结束提醒窗口
                                self.root.after(0, lambda t=task: self.show_task_end_reminder(t))
                                # 避免重复提醒
                                time.sleep(10)
                        except Exception as e:
                            print(f"检查任务结束提醒时出错: {e}")
            
            # 每3秒检查一次
            time.sleep(3)
    
    def show_task_reminder(self, task):
        """显示任务开始提醒弹窗（右下角）"""
        task_id, task_name, start_time_str, end_time_str, status = task
        
        # 创建提醒窗口
        reminder_window = tk.Toplevel(self.root)
        reminder_window.title("任务提醒")
        # 设置窗口大小和右下角位置
        reminder_window.geometry(get_bottom_right_position(300, 150))
        # 设置窗口置顶
        reminder_window.attributes("-topmost", True)
        # 去除窗口图标
        reminder_window.iconbitmap(default="")
        
        frame = ttk.Frame(reminder_window, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        
        # 提醒信息
        ttk.Label(
            frame, 
            text=f"任务 '{task_name}' 即将开始！", 
            font=("Arial", 12)
        ).pack(pady=10)
        
        ttk.Label(
            frame, 
            text=f"开始时间: {start_time_str.split(' ')[1]}", 
            foreground="gray"
        ).pack(pady=5)
        
        # 按钮框架
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)
        
        # 开始任务按钮
        def start_task():
            self.task_manager.update_task_status(task_id, 1)  # 标记为进行中
            self.refresh_tasks()
            reminder_window.destroy()
        
        # 稍后提醒按钮（10分钟后）
        def remind_later():
            reminder_window.destroy()
            # 记录稍后提醒的任务，10分钟后再次检查
            threading.Thread(
                target=self.delayed_reminder, 
                args=(task, 10*60),  # 10分钟
                daemon=True
            ).start()
        
        ttk.Button(btn_frame, text="开始任务", command=start_task).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="稍后提醒", command=remind_later).pack(side=tk.LEFT, padx=10)
    
    def delayed_reminder(self, task, delay_seconds):
        """延迟提醒任务"""
        time.sleep(delay_seconds)
        # 再次检查任务状态，如果还是未开始则再次提醒
        task_id = task[0]
        # 重新获取任务最新状态
        today_tasks = self.task_manager.get_today_tasks()
        for t in today_tasks:
            if t[0] == task_id and t[4] in [0, 1]:  # 仍未开始或进行中
                self.root.after(0, lambda task=t: self.show_task_reminder(task))
                break
    
    def create_login_ui(self):
        """创建登录界面"""
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="50")
        frame.pack(expand=True)
        
        ttk.Label(frame, text="时间管理系统", font=("Arial", 24)).pack(pady=30)
        
        # 用户名
        ttk.Label(frame, text="用户名:").pack(anchor=tk.W, pady=5)
        self.username_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.username_var, width=30).pack(pady=5)
        
        # 密码
        ttk.Label(frame, text="密码:").pack(anchor=tk.W, pady=5)
        self.password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.password_var, show="*", width=30).pack(pady=5)
        
        # 按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="登录", command=self.login).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="注册", command=self.register).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="游客登录", command=self.enter_guest_mode).pack(side=tk.LEFT, padx=10)
    
    # 添加任务结束提醒窗口
    def show_task_end_reminder(self, task):
        """显示任务结束提醒弹窗（右下角）"""
        task_id, task_name, start_time_str, end_time_str, status = task
        
        # 创建提醒窗口
        reminder_window = tk.Toplevel(self.root)
        reminder_window.title("任务结束提醒")
        # 设置窗口大小和右下角位置
        reminder_window.geometry(get_bottom_right_position(350, 180))
        # 设置窗口置顶
        reminder_window.attributes("-topmost", True)
        # 去除窗口图标
        reminder_window.iconbitmap(default="")
        
        frame = ttk.Frame(reminder_window, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        
        # 提醒信息
        ttk.Label(
            frame, 
            text=f"任务 '{task_name}' 已到结束时间！", 
            font=("Arial", 12)
        ).pack(pady=10)
        
        ttk.Label(
            frame, 
            text=f"原计划结束时间: {end_time_str.split(' ')[1]}", 
            foreground="gray"
        ).pack(pady=5)
        
        # 按钮框架
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)
        
        # 标记为已完成按钮
        def mark_completed():
            self.task_manager.update_task_status(task_id, 2)  # 标记为已完成
            self.refresh_tasks()
            reminder_window.destroy()
        
        # 继续任务按钮
        def continue_task():
            reminder_window.destroy()
            # 10分钟后再次提醒
            threading.Thread(
                target=self.delayed_end_reminder, 
                args=(task, 10*60),  # 10分钟
                daemon=True
            ).start()
        
        # 推迟任务按钮
        def postpone_task():
            # 获取当前时间
            now = datetime.now(TIMEZONE)
            # 默认推迟30分钟
            default_end = now + timedelta(minutes=30)
            
            # 打开时间选择对话框
            new_end_str = simpledialog.askstring(
                "推迟任务", 
                f"请输入新的结束时间\n格式: {default_end.strftime('%Y-%m-%d %H:%M:%S')}",
                parent=reminder_window,
                initialvalue=default_end.strftime("%Y-%m-%d %H:%M:%S")
            )
            
            if new_end_str:
                try:
                    # 验证时间格式
                    new_end = str_to_datetime(new_end_str)
                    # 确保新时间在当前时间之后
                    if new_end > now:
                        # 更新任务结束时间（需要先修改TaskManager类，添加更新任务时间的方法）
                        if self.update_task_end_time(task_id, new_end_str):
                            messagebox.showinfo("成功", "任务已推迟")
                            self.refresh_tasks()
                            reminder_window.destroy()
                        else:
                            messagebox.showerror("错误", "无法更新任务时间")
                    else:
                        messagebox.showwarning("警告", "新时间必须晚于当前时间")
                except ValueError:
                    messagebox.showwarning("警告", "时间格式不正确")
        
        ttk.Button(btn_frame, text="已完成", command=mark_completed).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="继续完成", command=continue_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="推迟任务", command=postpone_task).pack(side=tk.LEFT, padx=5)

    # 添加延迟结束提醒方法
    def delayed_end_reminder(self, task, delay_seconds):
        """延迟检查任务结束时间"""
        time.sleep(delay_seconds)
        # 重新获取任务最新状态
        today_tasks = self.task_manager.get_today_tasks()
        for t in today_tasks:
            if t[0] == task[0] and t[4] == 1:  # 仍为进行中
                self.root.after(0, lambda task=t: self.show_task_end_reminder(task))
                break

    # 添加更新任务结束时间的方法
    def update_task_end_time(self, task_id, new_end_time):
        """更新任务的结束时间"""
        if self.task_manager.is_guest:
            # 处理游客模式
            for i, task in enumerate(self.task_manager.memory_storage.tasks):
                if task[0] == task_id:
                    # 检查新时间是否晚于开始时间
                    if new_end_time > task[2]:  # task[2]是开始时间
                        self.task_manager.memory_storage.tasks[i] = (
                            task[0], task[1], task[2], new_end_time, task[4]
                        )
                        return True
                    return False
                    
        # 处理登录用户模式
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            # 先检查开始时间
            cursor.execute(
                "SELECT start_time FROM tasks WHERE task_id=? AND user_id=?",
                (task_id, self.user_manager.current_user[0])
            )
            result = cursor.fetchone()
            if not result:
                return False
                
            start_time = result[0]
            if new_end_time <= start_time:
                return False
                
            # 更新结束时间
            cursor.execute(
                "UPDATE tasks SET end_time=? WHERE task_id=? AND user_id=?",
                (new_end_time, task_id, self.user_manager.current_user[0])
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"更新任务结束时间出错: {e}")
            return False
        finally:
            conn.close()

    def enter_guest_mode(self):
        """进入游客模式"""
        success, msg = self.user_manager.enter_guest_mode()
        messagebox.showinfo("提示", msg)
        
        if success:
            # 初始化游客模式的任务管理器
            self.task_manager = TaskManager(
                self.user_manager.current_user[0], 
                is_guest=self.user_manager.current_user[2]
            )
            self.undo_stack = []  # 清空撤销栈
            self.create_main_ui()
    
    def create_main_ui(self):
        """创建主界面"""
        self.clear_window()
        
        # 顶部框架 - 显示时间和用户信息
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        # 实时时间
        self.time_label = ttk.Label(top_frame, text="", font=("Arial", 12))
        self.time_label.pack(side=tk.LEFT)
        
        # 用户信息和登出按钮
        user_type = "游客" if self.user_manager.current_user[2] else "用户"
        ttk.Label(top_frame, text=f"当前{user_type}: {self.user_manager.current_user[1]}").pack(side=tk.RIGHT, padx=10)
        ttk.Button(top_frame, text="登出", command=self.logout).pack(side=tk.RIGHT)
        
        # 中间框架 - 任务列表
        mid_frame = ttk.Frame(self.root, padding="10")
        mid_frame.pack(expand=True, fill=tk.BOTH)
        
        ttk.Label(mid_frame, text="今日任务", font=("Arial", 16)).pack(anchor=tk.W, pady=10)
        
        # 任务列表
        columns = ("id", "任务名称", "开始时间", "结束时间", "状态", "操作", "删除")
        self.task_tree = ttk.Treeview(mid_frame, columns=columns, show="headings")
        self.task_tree.bind("<Double-1>", self.on_task_double_click)
        
        for col in columns:
            self.task_tree.heading(col, text=col)
            if col == "id":
                width = 50
            elif col in ["开始时间", "结束时间"]:
                width = 150
            elif col in ["操作", "删除"]:
                width = 80
            else:
                width = 100
            self.task_tree.column(col, width=width, anchor=tk.CENTER)
        
        self.task_tree.pack(expand=True, fill=tk.BOTH)
        
        # 底部按钮
        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="添加任务", command=self.add_task_dialog).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="AI智能添加", command=self.ai_add_task).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="刷新任务", command=self.refresh_tasks).pack(side=tk.RIGHT, padx=10)
        ttk.Button(btn_frame, text="查看每周任务", command=self.view_weekly_tasks).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="添加固定任务", command=self.add_recurring_task_dialog).pack(side=tk.LEFT, padx=10)
        
        # 加载任务
        self.refresh_tasks()
        
        # 绑定任务列表事件
        self.task_tree.bind("<ButtonRelease-1>", self.on_task_click)
    
    def on_task_double_click(self, event):
        """处理任务项双击事件"""
        # 获取双击的项目
        item = self.task_tree.selection()
        if item:
            # 获取任务ID（假设任务ID存储在第一列）
            task_id = int(self.task_tree.item(item, "values")[0])
            self.edit_task(task_id)

    def add_recurring_task_dialog(self):
        """添加固定任务对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加固定任务")
        dialog.geometry("400x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        
        # 任务名称
        ttk.Label(frame, text="任务名称:").pack(anchor=tk.W, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=40).pack(pady=5)
        
        # 重复类型
        ttk.Label(frame, text="重复类型:").pack(anchor=tk.W, pady=5)
        recurrence_var = tk.StringVar(value="daily")
        recurrence_frame = ttk.Frame(frame)
        recurrence_frame.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(recurrence_frame, text="每天", variable=recurrence_var, value="daily").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(recurrence_frame, text="每周", variable=recurrence_var, value="weekly").pack(side=tk.LEFT, padx=10)
        
        # 每周重复选项
        self.weekday_vars = [tk.BooleanVar() for _ in range(7)]
        weekday_frame = ttk.Frame(frame)
        weekday_frame.pack(fill=tk.X, pady=5)
        
        for i in range(7):
            ttk.Checkbutton(
                weekday_frame, 
                text=get_weekday_name(i), 
                variable=self.weekday_vars[i]
            ).pack(side=tk.LEFT, padx=5)
        
        # 开始时间（仅时间部分）
        ttk.Label(frame, text="开始时间 (HH:MM:SS):").pack(anchor=tk.W, pady=5)
        start_var = tk.StringVar(value="09:00:00")
        ttk.Entry(frame, textvariable=start_var, width=40).pack(pady=5)
        
        # 结束时间（仅时间部分）
        ttk.Label(frame, text="结束时间 (HH:MM:SS):").pack(anchor=tk.W, pady=5)
        end_var = tk.StringVar(value="10:00:00")
        ttk.Entry(frame, textvariable=end_var, width=40).pack(pady=5)
        
        # 按钮
        def save_recurring_task():
            name = name_var.get()
            recurrence_type = recurrence_var.get()
            start_time = start_var.get()
            end_time = end_var.get()
            
            if not name or not start_time or not end_time:
                messagebox.showwarning("警告", "请填写所有字段")
                return
                
            # 验证时间格式
            try:
                datetime.strptime(start_time, "%H:%M:%S")
                datetime.strptime(end_time, "%H:%M:%S")
            except ValueError:
                messagebox.showwarning("警告", "时间格式不正确，请使用HH:MM:SS")
                return
                
            # 处理每周重复的情况
            weekdays = None
            if recurrence_type == "weekly":
                weekdays = [i for i in range(7) if self.weekday_vars[i].get()]
                if not weekdays:
                    messagebox.showwarning("警告", "请至少选择一个星期几")
                    return
            
            # 添加固定任务
            success, msg, _ = self.task_manager.add_recurring_tasks(
                name, start_time, end_time, recurrence_type, weekdays
            )
            messagebox.showinfo("结果", msg)
            if success:
                dialog.destroy()
                self.refresh_tasks()
        
        ttk.Button(frame, text="保存", command=save_recurring_task).pack(pady=10)
        
        # 绑定重复类型变化事件，控制星期选择框的状态
        def toggle_weekday_frame(*args):
            state = "normal" if recurrence_var.get() == "weekly" else "disabled"
            for child in weekday_frame.winfo_children():
                child.config(state=state)
        
        recurrence_var.trace_add("write", toggle_weekday_frame)
        # 初始状态设置
        toggle_weekday_frame()

    def update_time(self):
        """更新时间显示"""
        current_time = get_current_time()
        if self.time_label:
            self.time_label.config(text=current_time)
        # 每秒更新一次
        self.root.after(1000, self.update_time)
    
    def refresh_tasks(self):
        """刷新任务列表，包含超时任务处理"""
        if not self.user_manager.current_user:
            return
            
        # 清空现有项
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
            
        # 获取今日任务
        tasks = self.task_manager.get_today_tasks()
        # 添加"已超时"和"已拖延"状态
        status_map = {0: "未开始", 1: "进行中", 2: "已完成", 3: "已超时", 4: "已拖延"}
        
        for task in tasks:
            task_id, name, start, end, status = task
            status_text = status_map.get(status, "未知")
            
            # 根据状态设置颜色
            tag = "completed" if status == 2 else "in_progress" if status == 1 else \
                "expired" if status == 3 else "delayed" if status == 4 else ""
            self.task_tree.insert("", tk.END, values=(
                task_id, name, start.split(" ")[1], end.split(" ")[1], status_text, 
                "重新添加" if status == 3 else "更改", "删除"
            ), tags=(tag,))
        
        # 设置标签样式
        self.task_tree.tag_configure("completed", foreground="gray")
        self.task_tree.tag_configure("in_progress", foreground="blue")
        self.task_tree.tag_configure("expired", foreground="red")  # 超时任务红色显示
        self.task_tree.tag_configure("delayed", foreground="orange")  # 拖延任务橙色显示
        
    def on_task_click(self, event):
        """任务列表点击事件，包含重新添加功能"""
        region = self.task_tree.identify_region(event.x, event.y)
        item = self.task_tree.identify_row(event.y)
        
        if not item or region != "cell":
            return
            
        column = int(self.task_tree.identify_column(event.x).replace("#", ""))
        task_id = self.task_tree.item(item, "values")[0]
        status_text = self.task_tree.item(item, "values")[4]
        
        if column == 6:  # 操作列
            # 处理超时任务的重新添加
            if status_text == "已超时":
                # 获取原任务信息
                task_name = self.task_tree.item(item, "values")[1]
                original_start = self.task_tree.item(item, "values")[2]
                original_end = self.task_tree.item(item, "values")[3]
                
                # 创建时间选择对话框
                dialog = tk.Toplevel(self.root)
                dialog.title("选择新时间")
                dialog.geometry("300x200")
                dialog.transient(self.root)
                dialog.grab_set()
                
                frame = ttk.Frame(dialog, padding="20")
                frame.pack(expand=True, fill=tk.BOTH)
                
                # 新开始时间
                ttk.Label(frame, text="新开始时间:").pack(anchor=tk.W, pady=5)
                now = datetime.now(TIMEZONE)
                default_start = datetime_to_str(now)
                start_var = tk.StringVar(value=default_start)
                ttk.Entry(frame, textvariable=start_var).pack(pady=5)
                
                # 新结束时间（默认延后1小时）
                ttk.Label(frame, text="新结束时间:").pack(anchor=tk.W, pady=5)
                default_end = datetime_to_str(now + timedelta(hours=1))
                end_var = tk.StringVar(value=default_end)
                ttk.Entry(frame, textvariable=end_var).pack(pady=5)
                
                # 时间格式提示
                ttk.Label(frame, text="时间格式: YYYY-MM-DD HH:MM:SS", font=("Arial", 8)).pack(pady=5)
                
                def confirm_new_time():
                    new_start = start_var.get()
                    new_end = end_var.get()
                    
                    # 验证时间格式
                    try:
                        str_to_datetime(new_start)
                        str_to_datetime(new_end)
                    except ValueError:
                        messagebox.showwarning("警告", "时间格式不正确")
                        return
                        
                    # 验证时间顺序
                    if str_to_datetime(new_start) >= str_to_datetime(new_end):
                        messagebox.showwarning("警告", "结束时间必须晚于开始时间")
                        return
                        
                    # 验证时间是否在当前时间之后
                    if str_to_datetime(new_start) < datetime.now(TIMEZONE):
                        if not messagebox.askyesno("提示", "开始时间在当前时间之前，是否继续？"):
                            return
                    
                    # 添加新任务
                    success, msg, new_task_id = self.task_manager.add_task(
                        task_name, new_start, new_end
                    )
                    if success:
                        # 将原任务状态改为已拖延
                        self.task_manager.update_task_status(task_id, 4)
                        messagebox.showinfo("成功", "任务已重新添加")
                        dialog.destroy()
                        self.refresh_tasks()
                    else:
                        messagebox.showerror("失败", msg)
                
                ttk.Button(frame, text="确认", command=confirm_new_time).pack(pady=10)
                
            else:
                # 原有状态更改逻辑
                status_map = {"未开始": 0, "进行中": 1, "已完成": 2, "已拖延": 4}
                current_status = status_map[status_text]
                
                if current_status == 0:
                    self.task_manager.update_task_status(task_id, 1)
                elif current_status == 1:
                    self.task_manager.update_task_status(task_id, 2)
                elif current_status == 2:
                    self.task_manager.update_task_status(task_id, 0)
                elif current_status == 4:
                    self.task_manager.update_task_status(task_id, 1)
                    
                self.refresh_tasks()
                
        elif column == 7:  # 删除列
            task_name = self.task_tree.item(item, "values")[1]
            self.confirm_delete(task_id, task_name, is_weekly=False)
    
    def add_task_dialog(self):
        """添加任务对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加任务")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        
        # 任务名称
        ttk.Label(frame, text="任务名称:").pack(anchor=tk.W, pady=5)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=40).pack(pady=5)
        
        # 开始时间
        ttk.Label(frame, text="开始时间:").pack(anchor=tk.W, pady=5)
        start_var = tk.StringVar(value=get_current_time())
        ttk.Entry(frame, textvariable=start_var, width=40).pack(pady=5)
        
        # 结束时间
        ttk.Label(frame, text="结束时间:").pack(anchor=tk.W, pady=5)
        end_var = tk.StringVar(value=datetime_to_str(str_to_datetime(get_current_time()) + timedelta(hours=1)))
        ttk.Entry(frame, textvariable=end_var, width=40).pack(pady=5)
        
        # 按钮
        def save_task():
            name = name_var.get()
            start = start_var.get()
            end = end_var.get()
            
            if not name or not start or not end:
                messagebox.showwarning("警告", "请填写所有字段")
                return
                
            success, msg, _ = self.task_manager.add_task(name, start, end)
            messagebox.showinfo("结果", msg)
            if success:
                dialog.destroy()
                self.refresh_tasks()
        
        ttk.Button(frame, text="保存", command=save_task).pack(pady=10)
    
    def ai_add_task(self):
        """AI智能添加任务"""
        task_desc = simpledialog.askstring("AI添加任务", "请描述你的任务:")
        if not task_desc:
            return
            
        # 显示加载中
        loading = tk.Toplevel(self.root)
        loading.title("处理中")
        loading.geometry("200x100")
        loading.transient(self.root)
        loading.grab_set()
        
        ttk.Label(loading, text="AI正在解析任务...").pack(expand=True)
        self.root.update()
        
        # 解析任务
        task_info = self.ai_assistant.parse_task(task_desc)
        loading.destroy()
        
        if "error" in task_info:
            messagebox.showerror("错误", task_info["error"])
            return
            
        # 检查必要字段是否存在
        required_fields = ["task_name", "start_time", "end_time"]
        if not all(field in task_info for field in required_fields):
            messagebox.showerror("错误", "AI 返回的任务信息不完整")
            return
            
        # 确认任务信息
        confirm_msg = f"""
        任务名称: {task_info['task_name']}
        开始时间: {task_info['start_time']}
        结束时间: {task_info['end_time']}
        
        是否确认添加?
        """
        
        if messagebox.askyesno("确认任务", confirm_msg):
            success, msg, _ = self.task_manager.add_task(
                task_info['task_name'],
                task_info['start_time'],
                task_info['end_time']
            )
            messagebox.showinfo("结果", msg)
            if success:
                self.refresh_tasks()
    
    def login(self):
        """登录处理"""
        username = self.username_var.get()
        password = self.password_var.get()
        
        if not username or not password:
            messagebox.showwarning("警告", "请输入用户名和密码")
            return
            
        success, msg = self.user_manager.login(username, password)
        messagebox.showinfo("登录结果", msg)
        
        if success:
            self.task_manager = TaskManager(
                self.user_manager.current_user[0],
                is_guest=self.user_manager.current_user[2]
            )
            self.undo_stack = []  # 清空撤销栈
            self.create_main_ui()
    
    def register(self):
        """注册处理"""
        username = self.username_var.get()
        password = self.password_var.get()
        
        if not username or not password:
            messagebox.showwarning("警告", "请输入用户名和密码")
            return
            
        success, msg = self.user_manager.register(username, password)
        messagebox.showinfo("注册结果", msg)
    
    def logout(self):
        """登出时停止提醒检查"""
        self.reminder_checking = False
        if self.reminder_thread:
            self.reminder_thread.join(timeout=1)

        """登出处理"""
        success, msg = self.user_manager.logout()
        messagebox.showinfo("登出结果", msg)
        self.create_login_ui()
    
    def clear_window(self):
        """清空窗口"""
        for widget in self.root.winfo_children():
            widget.destroy()

    def edit_task(self, task_id):
        """编辑任务对话框"""
        # 获取任务当前信息
        today_tasks = self.task_manager.get_today_tasks()
        task = next((t for t in today_tasks if t[0] == task_id), None)
        
        if not task:
            messagebox.showerror("错误", "任务不存在")
            return
            
        task_id, task_name, start_time_str, end_time_str, status = task
        
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑任务")
        edit_window.geometry("400x300")
        edit_window.resizable(False, False)
        edit_window.transient(self.root)  # 设置为主窗口的子窗口
        edit_window.grab_set()  # 模态窗口
        
        frame = ttk.Frame(edit_window, padding="20")
        frame.pack(expand=True, fill=tk.BOTH)
        
        # 任务名称
        ttk.Label(frame, text="任务名称:").pack(anchor=tk.W, pady=5)
        name_var = tk.StringVar(value=task_name)
        ttk.Entry(frame, textvariable=name_var, width=40).pack(pady=5)
        
        # 开始时间
        ttk.Label(frame, text="开始时间:").pack(anchor=tk.W, pady=5)
        start_var = tk.StringVar(value=start_time_str)
        ttk.Entry(frame, textvariable=start_var, width=40).pack(pady=5)
        ttk.Label(frame, text="格式: YYYY-MM-DD HH:MM:SS", foreground="gray").pack(anchor=tk.W)
        
        # 结束时间
        ttk.Label(frame, text="结束时间:").pack(anchor=tk.W, pady=5)
        end_var = tk.StringVar(value=end_time_str)
        ttk.Entry(frame, textvariable=end_var, width=40).pack(pady=5)
        ttk.Label(frame, text="格式: YYYY-MM-DD HH:MM:SS", foreground="gray").pack(anchor=tk.W)
        
        # 按钮
        def save_changes():
            new_name = name_var.get().strip()
            new_start = start_var.get().strip()
            new_end = end_var.get().strip()
            
            if not new_name:
                messagebox.showwarning("警告", "任务名称不能为空")
                return
                
            # 验证时间格式
            try:
                str_to_datetime(new_start)
                str_to_datetime(new_end)
            except ValueError:
                messagebox.showwarning("警告", "时间格式不正确")
                return
                
            # 验证时间顺序
            if new_start >= new_end:
                messagebox.showwarning("警告", "结束时间必须晚于开始时间")
                return
                
            # 更新任务
            success, msg = self.task_manager.update_task(
                task_id, new_name, new_start, new_end
            )
            
            if success:
                messagebox.showinfo("成功", msg)
                self.refresh_tasks()
                edit_window.destroy()
            else:
                messagebox.showerror("错误", msg)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="保存", command=save_changes).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="取消", command=edit_window.destroy).pack(side=tk.LEFT, padx=10)

    def view_weekly_tasks(self):
    
        """查看每周任务，合并相同日期和星期几的栏目"""
        # 关闭已有的每周任务窗口
        if self.weekly_window and isinstance(self.weekly_window, tk.Toplevel) and self.weekly_window.winfo_exists():
            self.weekly_window.destroy()
        
        self.weekly_window = tk.Toplevel(self.root)
        self.weekly_window.title("每周任务")
        self.weekly_window.geometry("1000x600")
        self.weekly_window.transient(self.root)
        
        # 获取本周任务
        tasks, start_date, end_date = self.task_manager.get_weekly_tasks()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 按日期分组任务
        date_tasks = {}
        for task in tasks:
            task_id, name, start_time, end_time, status = task
            task_date = start_time.split(" ")[0]  # 提取日期部分
            if task_date not in date_tasks:
                date_tasks[task_date] = []
            date_tasks[task_date].append(task)
        
        # 创建主框架
        main_frame = ttk.Frame(self.weekly_window, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # 创建标题
        title = f"{start_date} 至 {end_date} 任务安排"
        ttk.Label(main_frame, text=title, font=("Arial", 16)).pack(anchor=tk.W, pady=10)
        
        # 创建滚动区域
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 状态映射
        status_map = {0: "未开始", 1: "进行中", 2: "已完成", 3: "已超时", 4: "已拖延"}
        
        # 按日期顺序显示任务组
        current_date = start_dt
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            weekday = get_weekday_name(current_date.weekday())
            
            # 创建日期分组框架
            date_frame = ttk.LabelFrame(
                scrollable_frame, 
                text=f"{date_str} {weekday}",
                padding="10"
            )
            date_frame.pack(fill=tk.X, pady=5, padx=5)
            
            # 显示该日期的任务
            if date_str in date_tasks and date_tasks[date_str]:
                # 创建任务表格
                columns = ("id", "任务名称", "开始时间", "结束时间", "状态", "操作")
                tree = ttk.Treeview(date_frame, columns=columns, show="headings", height=min(5, len(date_tasks[date_str])))
                
                for col in columns:
                    tree.heading(col, text=col)
                    if col == "id":
                        width = 50
                    elif col in ["开始时间", "结束时间"]:
                        width = 100
                    elif col == "操作":
                        width = 80
                    else:
                        width = 150
                    tree.column(col, width=width, anchor=tk.CENTER)
                
                # 添加任务
                for task in date_tasks[date_str]:
                    task_id, name, start, end, status = task
                    status_text = status_map.get(status, "未知")
                    
                    tag = "completed" if status == 2 else "in_progress" if status == 1 else \
                          "expired" if status == 3 else "delayed" if status == 4 else ""
                    tree.insert("", tk.END, values=(
                        task_id, name, start.split(" ")[1], end.split(" ")[1], status_text, "更改"
                    ), tags=(tag,))
                
                # 设置标签样式
                tree.tag_configure("completed", foreground="gray")
                tree.tag_configure("in_progress", foreground="blue")
                tree.tag_configure("expired", foreground="red")
                tree.tag_configure("delayed", foreground="orange")
                
                # 绑定点击事件
                tree.bind("<ButtonRelease-1>", lambda e, t=tree: self.on_weekly_task_click(e, t))
                tree.pack(fill=tk.X)
            else:
                # 无任务提示
                ttk.Label(date_frame, text="当天没有任务", foreground="gray").pack(pady=5)
            
            current_date += timedelta(days=1)
        
        # 刷新按钮
        ttk.Button(main_frame, text="刷新", command=self.view_weekly_tasks).pack(pady=10)
        
    # 绑定点击事件
    def on_weekly_task_click(event):
        region = weekly_tree.identify_region(event.x, event.y)
        item = weekly_tree.identify_row(event.y)
        
        if not item or region != "cell":
            return
            
        column = int(weekly_tree.identify_column(event.x).replace("#", ""))
        task_id = int(weekly_tree.item(item, "values")[0])
        status_text = weekly_tree.item(item, "values")[4]
        
        # 操作列 - 处理重新添加
        if column == 6:
            if status_text == "已超时":
                # 获取原任务信息
                task_name = weekly_tree.item(item, "values")[1]
                original_start = weekly_tree.item(item, "values")[2]
                original_end = weekly_tree.item(item, "values")[3]
                
                # 创建时间选择对话框
                dialog = tk.Toplevel(self.weekly_window)
                dialog.title("选择新时间")
                dialog.geometry("300x200")
                dialog.transient(self.weekly_window)
                dialog.grab_set()
                
                frame = ttk.Frame(dialog, padding="20")
                frame.pack(expand=True, fill=tk.BOTH)
                
                # 新开始时间
                ttk.Label(frame, text="新开始时间:").pack(anchor=tk.W, pady=5)
                now = datetime.now(TIMEZONE)
                default_start = datetime_to_str(now)
                start_var = tk.StringVar(value=default_start)
                ttk.Entry(frame, textvariable=start_var).pack(pady=5)
                
                # 新结束时间（默认延后1小时）
                ttk.Label(frame, text="新结束时间:").pack(anchor=tk.W, pady=5)
                default_end = datetime_to_str(now + timedelta(hours=1))
                end_var = tk.StringVar(value=default_end)
                ttk.Entry(frame, textvariable=end_var).pack(pady=5)
                
                # 时间格式提示
                ttk.Label(frame, text="时间格式: YYYY-MM-DD HH:MM:SS", font=("Arial", 8)).pack(pady=5)
                
                def confirm_new_time():
                    new_start = start_var.get()
                    new_end = end_var.get()
                    
                    # 验证时间格式
                    try:
                        str_to_datetime(new_start)
                        str_to_datetime(new_end)
                    except ValueError:
                        messagebox.showwarning("警告", "时间格式不正确")
                        return
                        
                    # 验证时间顺序
                    if str_to_datetime(new_start) >= str_to_datetime(new_end):
                        messagebox.showwarning("警告", "结束时间必须晚于开始时间")
                        return
                        
                    # 检查时间冲突
                    if self.task_manager.check_conflict(new_start, new_end):
                        messagebox.showwarning("警告", "新时间与已有任务冲突")
                        return
                        
                    # 添加新任务
                    success, msg, new_task_id = self.task_manager.add_task(
                        task_name, new_start, new_end
                    )
                    
                    if success:
                        # 将原任务状态改为已拖延
                        self.task_manager.update_task_status(task_id, 4)
                        messagebox.showinfo("成功", f"任务已重新添加，新任务ID: {new_task_id}")
                        dialog.destroy()
                        # 刷新两个界面的任务列表
                        self.refresh_tasks()
                        # 重新创建每周任务窗口以刷新数据
                        self.view_weekly_tasks()
                    else:
                        messagebox.showerror("失败", msg)
                
                ttk.Button(frame, text="确认", command=confirm_new_time).pack(pady=10)
                ttk.Button(frame, text="取消", command=dialog.destroy).pack()
        
        # 删除列
        elif column == 7:
            if messagebox.askyesno("确认", "确定要删除此任务吗?"):
                success, msg, deleted_task = self.task_manager.delete_task(task_id)
                if success:
                    self.undo_stack.append(deleted_task)
                    messagebox.showinfo("提示", msg)
                    # 刷新两个界面
                    self.refresh_tasks()
                    self.view_weekly_tasks()
                else:
                    messagebox.showerror("错误", msg)
    
        weekly_tree.bind("<ButtonRelease-1>", on_weekly_task_click)

    def refresh_weekly_tasks(self):
        """刷新每周任务列表"""
        if not hasattr(self, 'weekly_tree'):
            return
        
        # 清空现有项
        for item in self.weekly_tree.get_children():
            self.weekly_tree.delete(item)
        
        # 获取本周任务
        tasks, _, _ = self.task_manager.get_weekly_tasks()
        status_map = {0: "未开始", 1: "进行中", 2: "已完成", 3: "已超时", 4: "已拖延"}
        
        # 检查并更新已超时但未完成的任务状态
        updated_tasks = []
        for task in tasks:
            task_id, name, start, end, status = task
            # 检查是否已超时
            if status in [0, 1] and is_time_expired(end):
                self.task_manager.update_task_status(task_id, 3)
                updated_tasks.append((task_id, name, start, end, 3))
            else:
                updated_tasks.append(task)
        
        # 添加到列表
        for task in updated_tasks:
            task_id, name, start, end, status = task
            status_text = status_map.get(status, "未知")
            date_part = start.split(" ")[0]
            start_time_part = start.split(" ")[1]
            end_time_part = end.split(" ")[1]
            
            # 设置标签颜色
            tag = "completed" if status == 2 else "in_progress" if status == 1 else \
                "expired" if status == 3 else "delayed" if status == 4 else ""
            self.weekly_tree.insert("", tk.END, values=(
                task_id, name, date_part, start_time_part, end_time_part, 
                status_text, "更改", "删除"
            ), tags=(tag,))
        
        # 设置标签样式
        self.weekly_tree.tag_configure("completed", foreground="gray")
        self.weekly_tree.tag_configure("in_progress", foreground="blue")
        self.weekly_tree.tag_configure("expired", foreground="red")
        self.weekly_tree.tag_configure("delayed", foreground="orange")

    def on_weekly_task_click(self, event):
        """每周任务列表点击事件"""
        region = self.weekly_tree.identify_region(event.x, event.y)
        item = self.weekly_tree.identify_row(event.y)
        
        if not item or region != "cell":
            return
        
        column = int(self.weekly_tree.identify_column(event.x).replace("#", ""))
        task_id = int(self.weekly_tree.item(item, "values")[0])
        
        if column == 7:  # 删除列
            if messagebox.askyesno("确认", "确定要删除此任务吗？"):
                success, msg, deleted_task = self.task_manager.delete_task(task_id)
                messagebox.showinfo("结果", msg)
                if success and deleted_task:
                    self.undo_stack.append(deleted_task)
                    self.refresh_weekly_tasks()
                    self.refresh_tasks()  # 同步刷新主页面
        
        elif column == 6:  # 操作列
            # 获取当前任务状态
            status_text = self.weekly_tree.item(item, "values")[5]
            status_map_rev = {"未开始": 0, "进行中": 1, "已完成": 2, "已超时": 3, "已拖延": 4}
            current_status = status_map_rev.get(status_text, 0)
            
            # 状态切换逻辑
            new_status = 1 if current_status == 0 else 2 if current_status in [1, 3, 4] else 0
            
            # 更新状态
            success, msg = self.task_manager.update_task_status(task_id, new_status)
            if success:
                self.refresh_weekly_tasks()
                self.refresh_tasks()  # 同步刷新主页面
            else:
                messagebox.showerror("错误", msg)
                
    def confirm_delete(self, task_id, task_name, is_weekly):
        """确认删除任务"""
        if messagebox.askyesno("确认删除", f"确定要删除任务 '{task_name}' 吗？"):
            success, msg, deleted_task = self.task_manager.delete_task(task_id)
            if success:
                # 将删除的任务信息存入撤销栈
                self.undo_stack.append(deleted_task)
                messagebox.showinfo("提示", msg)
                
                # 刷新任务列表
                self.refresh_tasks()
                if is_weekly and self.weekly_window:
                    self.weekly_window.destroy()
                    self.view_weekly_tasks()
            else:
                messagebox.showerror("错误", msg)

    def ai_add_task(self):
        """AI智能添加任务（结合历史数据）"""
        task_desc = simpledialog.askstring("AI添加任务", "请描述你的任务:")
        if not task_desc:
            return
            
        # 获取用户历史任务（最近10条）作为参考
        historical_tasks = []
        if not self.user_manager.current_user[2]:  # 非游客用户
            # 从数据库获取历史任务
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_id, task_name, start_time, end_time, status 
                FROM tasks 
                WHERE user_id=? 
                ORDER BY start_time DESC 
                LIMIT 10
            ''', (self.user_manager.current_user[0],))
            historical_tasks = cursor.fetchall()
            conn.close()
        else:
            # 游客用户从内存存储获取
            historical_tasks = sorted(
                self.task_manager.memory_storage.tasks,
                key=lambda x: x[2],  # 按开始时间排序
                reverse=True
            )[:10]
        
        # 显示加载中
        loading = tk.Toplevel(self.root)
        loading.title("处理中")
        loading.geometry("200x100")
        loading.transient(self.root)
        loading.grab_set()
        
        ttk.Label(loading, text="AI正在分析任务...").pack(expand=True)
        self.root.update()
        
        # 传入历史任务解析新任务
        task_info = self.ai_assistant.parse_task(task_desc, historical_tasks)
        loading.destroy()
        
        if "error" in task_info:
            messagebox.showerror("错误", task_info["error"])
            return
            
        # 检查必要字段
        required_fields = ["task_name", "start_time", "end_time"]
        if not all(field in task_info for field in required_fields):
            messagebox.showerror("错误", "AI 返回的任务信息不完整")
            return
            
        # 确认任务信息
        confirm_msg = f"""
        任务名称: {task_info['task_name']}
        开始时间: {task_info['start_time']}
        结束时间: {task_info['end_time']}
        
        是否确认添加?
        """
        
        if messagebox.askyesno("确认任务", confirm_msg):
            # 检查时间冲突
            if self.task_manager.check_conflict(task_info['start_time'], task_info['end_time']):
                messagebox.showwarning("冲突", "任务时间与现有任务冲突")
                return
                
            success, msg, _ = self.task_manager.add_task(
                task_info['task_name'],
                task_info['start_time'],
                task_info['end_time']
            )
            messagebox.showinfo("结果", msg)
            if success:
                self.refresh_tasks()
    
    def undo_delete(self, event=None):
        """撤销删除操作 (Ctrl+Z)"""
        if not self.undo_stack:
            messagebox.showinfo("提示", "没有可撤销的操作")
            return
            
        # 从撤销栈中取出最近删除的任务
        task_info = self.undo_stack.pop()
        task_id, task_name, start_time, end_time, status = task_info
        
        if self.user_manager.current_user[2]:  # 游客模式
            # 重新添加到内存
            self.task_manager.memory_storage.tasks.append(task_info)
            messagebox.showinfo("提示", f"已撤销删除：{task_name}")
            self.refresh_tasks()
            if self.weekly_window:
                self.weekly_window.destroy()
                self.view_weekly_tasks()
        else:  # 普通用户
            # 重新添加到数据库
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO tasks (task_id, user_id, task_name, start_time, end_time, status, create_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (task_id, self.user_manager.current_user[0], task_name, start_time, end_time, status, get_current_time()))
                conn.commit()
                messagebox.showinfo("提示", f"已撤销删除：{task_name}")
                
                # 刷新任务列表
                self.refresh_tasks()
                if self.weekly_window:
                    self.weekly_window.destroy()
                    self.view_weekly_tasks()
            except Exception as e:
                messagebox.showerror("错误", f"撤销失败: {str(e)}")
            finally:    
                conn.close()

# ---------------------- 程序入口 ----------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = TimeManagementApp(root)
    root.mainloop()
