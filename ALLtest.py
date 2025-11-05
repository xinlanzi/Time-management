import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import requests
import json
from datetime import datetime, timedelta
import pytz
import threading
import time
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# ---------------------- 配置参数 ----------------------
OPENAI_API_KEY = "your-openai-api-key"  # 替换为你的API密钥
BASE_URL = "https://api.openai.com/v1/chat/completions"
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

# ---------------------- AI助手类 ----------------------
class AIAssistant:
    """AI助手类"""
    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def parse_task(self, user_input):
        """解析任务信息"""
        if not self.api_key:
            return {"error": "请配置OpenAI API密钥"}
            
        prompt = f"""
        请解析以下任务描述，提取开始时间、结束时间和任务名称，
        以JSON格式返回，包含task_name, start_time(YYYY-MM-DD HH:MM:SS), end_time(YYYY-MM-DD HH:MM:SS)
        如果没有指定时间，默认开始时间为当前时间后30分钟，持续1小时
        当前时间: {get_current_time()}
        
        任务描述: {user_input}
        """
        
        try:
            response = requests.post(
                BASE_URL,
                headers=self.headers,
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            return json.loads(response.json()["choices"][0]["message"]["content"])
        except Exception as e:
            return {"error": f"解析失败: {str(e)}"}

# ---------------------- 任务管理类 ----------------------
class TaskManager:
    """任务管理类"""
    def __init__(self, user_id):
        self.user_id = user_id
        
    def add_task(self, task_name, start_time, end_time):
        """添加任务"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        try:
            # 检查时间冲突
            if self.check_conflict(start_time, end_time):
                return False, "任务时间冲突"
                
            cursor.execute('''
                INSERT INTO tasks (user_id, task_name, start_time, end_time, create_time)
                VALUES (?, ?, ?, ?, ?)
            ''', (self.user_id, task_name, start_time, end_time, get_current_time()))
            conn.commit()
            return True, "任务添加成功"
        except Exception as e:
            return False, f"添加失败: {str(e)}"
        finally:
            conn.close()
    
    def check_conflict(self, start_time, end_time):
        """检查时间冲突"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM tasks 
            WHERE user_id=? AND status != 2 
            AND (
                (start_time < ? AND end_time > ?) OR
                (start_time < ? AND end_time > ?)
            )
        ''', (self.user_id, end_time, start_time, end_time, start_time))
        
        conflict = cursor.fetchone() is not None
        conn.close()
        return conflict
    
    def get_today_tasks(self):
        """获取今日任务"""
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
        return tasks
    
    def update_task_status(self, task_id, status):
        """更新任务状态"""
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

# ---------------------- 用户管理类 ----------------------
class UserManager:
    """用户管理类"""
    def __init__(self):
        self.current_user = None
        
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
            self.current_user = (user[0], user[1])
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
        
        # 初始化数据库
        init_database()
        
        # 创建界面
        self.create_login_ui()
        
        # 实时时间更新
        self.time_label = None
        self.update_time()
    
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
        ttk.Label(top_frame, text=f"当前用户: {self.user_manager.current_user[1]}").pack(side=tk.RIGHT, padx=10)
        ttk.Button(top_frame, text="登出", command=self.logout).pack(side=tk.RIGHT)
        
        # 中间框架 - 任务列表
        mid_frame = ttk.Frame(self.root, padding="10")
        mid_frame.pack(expand=True, fill=tk.BOTH)
        
        ttk.Label(mid_frame, text="今日任务", font=("Arial", 16)).pack(anchor=tk.W, pady=10)
        
        # 任务列表
        columns = ("id", "任务名称", "开始时间", "结束时间", "状态", "操作")
        self.task_tree = ttk.Treeview(mid_frame, columns=columns, show="headings")
        
        for col in columns:
            self.task_tree.heading(col, text=col)
            width = 50 if col == "id" else 150 if col in ["开始时间", "结束时间"] else 100
            self.task_tree.column(col, width=width, anchor=tk.CENTER)
        
        self.task_tree.pack(expand=True, fill=tk.BOTH)
        
        # 底部按钮
        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="添加任务", command=self.add_task_dialog).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="AI智能添加", command=self.ai_add_task).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="刷新任务", command=self.refresh_tasks).pack(side=tk.RIGHT, padx=10)
        
        # 加载任务
        self.refresh_tasks()
        
        # 绑定任务列表事件
        self.task_tree.bind("<ButtonRelease-1>", self.on_task_click)
    
    def update_time(self):
        """更新时间显示"""
        current_time = get_current_time()
        if self.time_label:
            self.time_label.config(text=current_time)
        # 每秒更新一次
        self.root.after(1000, self.update_time)
    
    def refresh_tasks(self):
        """刷新任务列表"""
        if not self.user_manager.current_user:
            return
            
        # 清空现有项
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
            
        # 获取今日任务
        tasks = self.task_manager.get_today_tasks()
        status_map = {0: "未开始", 1: "进行中", 2: "已完成"}
        
        for task in tasks:
            task_id, name, start, end, status = task
            status_text = status_map.get(status, "未知")
            
            # 根据状态设置颜色
            tag = "completed" if status == 2 else "in_progress" if status == 1 else ""
            self.task_tree.insert("", tk.END, values=(
                task_id, name, start.split(" ")[1], end.split(" ")[1], status_text, "操作"
            ), tags=(tag,))
        
        # 设置标签样式
        self.task_tree.tag_configure("completed", foreground="gray")
        self.task_tree.tag_configure("in_progress", foreground="blue")
    
    def on_task_click(self, event):
        """任务列表点击事件"""
        region = self.task_tree.identify_region(event.x, event.y)
        item = self.task_tree.identify_row(event.y)
        
        if not item or region != "cell":
            return
            
        column = int(self.task_tree.identify_column(event.x).replace("#", ""))
        if column == 6:  # 操作列
            task_id = self.task_tree.item(item, "values")[0]
            status = self.task_tree.item(item, "values")[4]
            
            if status == "未开始":
                self.task_manager.update_task_status(task_id, 1)
            elif status == "进行中":
                self.task_manager.update_task_status(task_id, 2)
            elif status == "已完成":
                self.task_manager.update_task_status(task_id, 0)
                
            self.refresh_tasks()
    
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
                
            success, msg = self.task_manager.add_task(name, start, end)
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
            
        # 确认任务信息
        confirm_msg = f"""
        任务名称: {task_info['task_name']}
        开始时间: {task_info['start_time']}
        结束时间: {task_info['end_time']}
        
        是否确认添加?
        """
        
        if messagebox.askyesno("确认任务", confirm_msg):
            success, msg = self.task_manager.add_task(
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
            self.task_manager = TaskManager(self.user_manager.current_user[0])
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
        """登出处理"""
        success, msg = self.user_manager.logout()
        messagebox.showinfo("登出结果", msg)
        self.create_login_ui()
    
    def clear_window(self):
        """清空窗口"""
        for widget in self.root.winfo_children():
            widget.destroy()

# ---------------------- 程序入口 ----------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = TimeManagementApp(root)
    root.mainloop()