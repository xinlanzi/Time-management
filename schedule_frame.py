import json
import datetime
import time
import threading
from datetime import timedelta
import os

# 配置文件路径
FILE_PATH = "schedule.json"
FIXED_TASKS_PATH = "fixed_tasks.json"
SUMMARY_PATH = "summary.json"

# 难度对应默认时长(分钟)
DIFFICULTY_DURATION = {
    "简单": 60,
    "较难": 120,
    "困难": 180
}

class ScheduleManager:
    def __init__(self):
        self.schedule = self.load_schedule()
        self.fixed_tasks = self.load_fixed_tasks()
        self.summary = self.load_summary()
        self.running_tomato = None
        self.current_task = None
        self.reminder_event = threading.Event()

    def load_schedule(self):
        try:
            with open(FILE_PATH, 'r', encoding='utf-8') as f:
                schedule = json.load(f)
                # 遍历所有任务，为缺少status的任务补充默认值
                for task in schedule.get("items", []):
                    if "status" not in task:
                        task["status"] = "pending"  # 默认设为待处理
                return schedule
        except (FileNotFoundError, json.JSONDecodeError):
            return {"items": []}

    def load_fixed_tasks(self):
        """加载固定任务(吃饭、睡觉等)"""
        try:
            with open(FIXED_TASKS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "daily": [],  # 每日固定任务
                "weekly": []  # 每周特定时间任务
            }

    def load_summary(self):
        """加载总结数据"""
        try:
            with open(SUMMARY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "daily": {},
                "weekly": {},
                "monthly": {}
            }

    def save_schedule(self):
        """保存任务数据"""
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.schedule, f, ensure_ascii=False, indent=4)

    def save_fixed_tasks(self):
        """保存固定任务"""
        with open(FIXED_TASKS_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.fixed_tasks, f, ensure_ascii=False, indent=4)

    def save_summary(self):
        """保存总结数据"""
        with open(SUMMARY_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.summary, f, ensure_ascii=False, indent=4)

    def setup_fixed_tasks(self):
        """设置固定任务(仅首次运行或重置时调用)"""
        if self.fixed_tasks["daily"]:
            print("已检测到固定任务设置，是否重新设置？(y/n)")
            if input().lower() != 'y':
                return

        print("\n=== 设置每日固定任务 ===")
        # 睡觉时间
        sleep_start = input("请输入睡觉开始时间(例如 22:00): ")
        sleep_end = input("请输入起床时间(例如 06:00): ")
        
        # 早餐时间
        breakfast_start = input("请输入早餐开始时间(例如 07:00): ")
        breakfast_end = input("请输入早餐结束时间(例如 07:30): ")
        
        # 午餐时间
        lunch_start = input("请输入午餐开始时间(例如 12:00): ")
        lunch_end = input("请输入午餐结束时间(例如 13:00): ")
        
        # 晚餐时间
        dinner_start = input("请输入晚餐开始时间(例如 18:00): ")
        dinner_end = input("请输入晚餐结束时间(例如 19:00): ")
        
        # 可添加其他固定任务
        self.fixed_tasks["daily"] = [
            {"name": "睡觉", "start": self.time_to_minutes(sleep_start), "end": self.time_to_minutes(sleep_end)},
            {"name": "早餐", "start": self.time_to_minutes(breakfast_start), "end": self.time_to_minutes(breakfast_end)},
            {"name": "午餐", "start": self.time_to_minutes(lunch_start), "end": self.time_to_minutes(lunch_end)},
            {"name": "晚餐", "start": self.time_to_minutes(dinner_start), "end": self.time_to_minutes(dinner_end)}
        ]

        print("\n=== 设置本周固定任务 ===")
        while True:
            add_more = input("是否添加本周特定时间任务？(y/n): ")
            if add_more.lower() != 'y':
                break
            
            name = input("任务名称: ")
            date = input("日期(YYYY-MM-DD): ")
            start = input("开始时间(HH:MM): ")
            end = input("结束时间(HH:MM): ")
            
            self.fixed_tasks["weekly"].append({
                "name": name,
                "date": date,
                "start": self.time_to_minutes(start),
                "end": self.time_to_minutes(end)
            })

        self.save_fixed_tasks()
        print("固定任务设置完成！")

    def time_to_minutes(self, time_str):
        """将时间字符串转换为分钟数"""
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes

    def minutes_to_time(self, minutes):
        """将分钟数转换为时间字符串"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    def add_task(self):
        """添加新任务"""
        print("\n=== 添加新任务 ===")
        name = input("任务名称: ")
        difficulty = input("难度(简单/较难/困难): ")
        
        # 处理时长
        if difficulty in DIFFICULTY_DURATION:
            use_default = input(f"默认时长为{DIFFICULTY_DURATION[difficulty]}分钟，使用默认值？(y/n): ")
            if use_default.lower() == 'y':
                time_needed = DIFFICULTY_DURATION[difficulty]
            else:
                time_needed = int(input("请输入所需时间(分钟): "))
        else:
            time_needed = int(input("请输入所需时间(分钟): "))
        
        deadline = input("截止日期(YYYY-MM-DD): ")
        
        new_task = {
            "name": name,
            "difficulty": difficulty,
            "time_needed": time_needed,
            "remaining_time": time_needed,  # 剩余时间
            "deadline": deadline,
            "status": "pending",  # pending, in_progress, completed, delayed, abandoned
            "created_at": datetime.date.today().strftime("%Y-%m-%d")
        }
        
        self.schedule["items"].append(new_task)
        self.save_schedule()
        print(f"已添加任务: {name}")

    def modify_fixed_task(self):
        """修改固定任务"""
        print("\n=== 修改固定任务 ===")
        print("1. 每日固定任务")
        print("2. 每周固定任务")
        choice = input("选择类型: ")
        
        if choice == "1":
            for i, task in enumerate(self.fixed_tasks["daily"]):
                print(f"{i+1}. {task['name']}: {self.minutes_to_time(task['start'])} - {self.minutes_to_time(task['end'])}")
            
            idx = int(input("选择要修改的任务序号: ")) - 1
            if 0 <= idx < len(self.fixed_tasks["daily"]):
                start = input("新的开始时间(HH:MM): ")
                end = input("新的结束时间(HH:MM): ")
                self.fixed_tasks["daily"][idx]["start"] = self.time_to_minutes(start)
                self.fixed_tasks["daily"][idx]["end"] = self.time_to_minutes(end)
                self.save_fixed_tasks()
                print("修改完成")
        
        elif choice == "2":
            for i, task in enumerate(self.fixed_tasks["weekly"]):
                print(f"{i+1}. {task['name']}({task['date']}): {self.minutes_to_time(task['start'])} - {self.minutes_to_time(task['end'])}")
            
            idx = int(input("选择要修改的任务序号: ")) - 1
            if 0 <= idx < len(self.fixed_tasks["weekly"]):
                date = input("新的日期(YYYY-MM-DD): ")
                start = input("新的开始时间(HH:MM): ")
                end = input("新的结束时间(HH:MM): ")
                self.fixed_tasks["weekly"][idx]["date"] = date
                self.fixed_tasks["weekly"][idx]["start"] = self.time_to_minutes(start)
                self.fixed_tasks["weekly"][idx]["end"] = self.time_to_minutes(end)
                self.save_fixed_tasks()
                print("修改完成")

    def generate_timetable(self):
        """生成一周时间表"""
        today = datetime.date.today()
        week_schedule = {}
        
        # 初始化一周日期
        for i in range(7):
            date_str = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            week_schedule[date_str] = {
                "fixed": [],
                "tasks": []
            }
        
        # 添加每日固定任务
        for date_str in week_schedule:
            # 添加每日固定任务
            for task in self.fixed_tasks["daily"]:
                week_schedule[date_str]["fixed"].append(task.copy())
            
            # 添加每周特定任务
            for task in self.fixed_tasks["weekly"]:
                if task["date"] == date_str:
                    week_schedule[date_str]["fixed"].append(task.copy())
        
        # 按截止日期排序任务
        sorted_tasks = sorted(
            self.schedule["items"],
            key=lambda x: datetime.datetime.strptime(x["deadline"], "%Y-%m-%d")
        )
        
        # 安排任务
        for task in sorted_tasks:
            if task["status"] in ["completed", "abandoned"]:
                continue
                
            deadline = datetime.datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            days_diff = (deadline - today).days
            
            if 0 <= days_diff < 7:
                date_str = deadline.strftime("%Y-%m-%d")
                week_schedule[date_str]["tasks"].append(task)
        
        return week_schedule

    def print_timetable(self, timetable):
        """打印时间表"""
        for date_str, data in timetable.items():
            print(f"\n===== {date_str} =====")
            print("固定任务:")
            for task in sorted(data["fixed"], key=lambda x: x["start"]):
                start = self.minutes_to_time(task["start"])
                end = self.minutes_to_time(task["end"])
                print(f"  {start} - {end}: {task['name']}")
            
            print("\n待办任务:")
            for i, task in enumerate(data["tasks"]):
                print(f"  {i+1}. {task['name']} (剩余: {task['remaining_time']}分钟, 难度: {task['difficulty']})")

    def start_reminder_monitor(self):
        """启动提醒监控线程"""
        def monitor():
            while not self.reminder_event.is_set():
                now = datetime.datetime.now()
                current_time = now.hour * 60 + now.minute
                current_date = now.strftime("%Y-%m-%d")
                
                timetable = self.generate_timetable()
                if current_date in timetable:
                    # 检查当前时间是否有任务需要提醒
                    for task in timetable[current_date]["tasks"]:
                        # 简化处理：实际应用中需要更精确的时间匹配逻辑
                        pass
                
                time.sleep(60)  # 每分钟检查一次
        
        threading.Thread(target=monitor, daemon=True).start()

    def tomato_timer(self, task, total_minutes):
        """番茄钟计时器"""
        self.current_task = task
        cycles = (total_minutes // 25) + (1 if total_minutes % 25 > 0 else 0)
        remaining = total_minutes
        
        for i in range(cycles):
            work_time = min(25, remaining)
            print(f"\n开始第{i+1}个番茄钟，工作{work_time}分钟...")
            
            # 工作计时
            for t in range(work_time, 0, -1):
                if self.running_tomato is False:
                    print("番茄钟已停止")
                    return remaining - (work_time - t)
                print(f"剩余工作时间: {t}分钟", end='\r')
                time.sleep(60)
            
            remaining -= work_time
            print("\n工作时间结束！请休息5分钟")
            
            # 休息计时
            for t in range(5, 0, -1):
                if self.running_tomato is False:
                    print("番茄钟已停止")
                    return remaining
                print(f"剩余休息时间: {t}分钟", end='\r')
                time.sleep(60)
            
            print("\n休息结束！准备开始下一段工作")
            
            if remaining <= 0:
                break
        
        self.current_task = None
        return 0

    def start_task(self, task_name):
        """开始任务"""
        for task in self.schedule["items"]:
            if task["name"] == task_name and task["status"] in ["pending", "in_progress"]:
                print(f"\n准备开始任务: {task['name']}")
                print("有5分钟时间确认是否开始...")
                
                # 等待用户确认
                start_confirmed = False
                for _ in range(5):
                    confirm = input("是否开始？(y/n，5分钟内未确认将视为放弃): ")
                    if confirm.lower() == 'y':
                        start_confirmed = True
                        break
                    time.sleep(60)
                
                if not start_confirmed:
                    task["status"] = "abandoned"
                    self.save_schedule()
                    print("未确认，任务已标记为放弃")
                    return
                
                # 开始任务和番茄钟
                task["status"] = "in_progress"
                self.save_schedule()
                self.running_tomato = True
                
                remaining = self.tomato_timer(task, task["remaining_time"])
                
                if remaining <= 0:
                    print("\n任务完成！")
                    task["status"] = "completed"
                    task["remaining_time"] = 0
                else:
                    task["remaining_time"] = remaining
                    print(f"\n任务暂停，剩余时间: {remaining}分钟")
                    self.handle_task_interruption(task)
                
                self.save_schedule()
                self.running_tomato = None
                return
        
        print("未找到该任务或任务状态不允许开始")

    def handle_task_interruption(self, task):
        """处理任务中断"""
        print("\n1. 继续完成")
        print("2. 另安排时间")
        choice = input("请选择: ")
        
        if choice == "1":
            new_time = int(input("估计还需要多少分钟: "))
            task["remaining_time"] = new_time
        else:
            task["status"] = "delayed"
            new_deadline = input("请输入新的截止日期(YYYY-MM-DD): ")
            task["deadline"] = new_deadline

    def generate_daily_summary(self, date_str=None):
        """生成每日总结"""
        date = date_str or datetime.date.today().strftime("%Y-%m-%d")
        tasks = [t for t in self.schedule["items"] if t["created_at"] == date]
        
        summary = {
            "completed": 0,
            "overtime": 0,
            "delayed": 0,
            "abandoned": 0
        }
        
        for task in tasks:
            if task["status"] == "completed":
                summary["completed"] += 1
            elif task["status"] == "delayed":
                summary["delayed"] += 1
            elif task["status"] == "abandoned":
                summary["abandoned"] += 1
        
        self.summary["daily"][date] = summary
        self.save_summary()
        return summary

    def generate_weekly_summary(self):
        """生成每周总结"""
        today = datetime.date.today()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        week_end = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")
        week_key = f"{week_start}至{week_end}"
        
        all_tasks = self.schedule["items"]
        total = len(all_tasks)
        completed = len([t for t in all_tasks if t["status"] == "completed"])
        completion_rate = (completed / total) * 100 if total > 0 else 0
        
        # 计算上周完成率
        last_week_start = (today - timedelta(days=today.weekday() + 7)).strftime("%Y-%m-%d")
        last_week_end = (today - timedelta(days=today.weekday() + 1)).strftime("%Y-%m-%d")
        last_week_key = f"{last_week_start}至{last_week_end}"
        last_rate = self.summary["weekly"].get(last_week_key, {}).get("completion_rate", 0)
        
        # 生成鼓励语
        encouragement = "继续保持！"
        if completion_rate > last_rate and last_rate > 0:
            encouragement = "太棒了，比上周有进步！"
        elif completion_rate < last_rate and last_rate > 0:
            encouragement = "别灰心，下周继续努力！"
        
        summary = {
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": completion_rate,
            "encouragement": encouragement
        }
        
        self.summary["weekly"][week_key] = summary
        self.save_summary()
        return summary

    def print_summary(self, summary_type):
        """打印总结"""
        if summary_type == "daily":
            date = input("请输入日期(YYYY-MM-DD，留空则为今天): ") or datetime.date.today().strftime("%Y-%m-%d")
            summary = self.generate_daily_summary(date)
            print(f"\n===== {date} 总结 =====")
            print(f"完成任务: {summary['completed']}")
            print(f"超时任务: {summary['overtime']}")
            print(f"延后任务: {summary['delayed']}")
            print(f"放弃任务: {summary['abandoned']}")
        
        elif summary_type == "weekly":
            summary = self.generate_weekly_summary()
            week_key = list(self.summary["weekly"].keys())[-1]
            print(f"\n===== {week_key} 总结 =====")
            print(f"总任务数: {summary['total_tasks']}")
            print(f"完成任务数: {summary['completed_tasks']}")
            print(f"完成率: {summary['completion_rate']:.2f}%")
            print(f"鼓励: {summary['encouragement']}")

    def clear_all_data(self):
        """清空所有数据并重新初始化"""
        confirm = input("\n警告：此操作将删除所有任务数据，包括固定任务和总结！\n确定要继续吗？(y/n): ")
        if confirm.lower() != 'y':
            print("已取消操作")
            return
            
        # 删除数据文件
        for file_path in [FILE_PATH, FIXED_TASKS_PATH, SUMMARY_PATH]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 重新初始化数据
        self.schedule = {"items": []}
        self.fixed_tasks = {"daily": [], "weekly": []}
        self.summary = {"daily": {}, "weekly": {}, "monthly": {}}
        
        print("所有数据已清空，将重新设置固定任务")
        # 重新设置固定任务
        self.setup_fixed_tasks()

def schedule_tasks_automatically(self):
    """自动将待办任务插入到时间表的空闲时段，尽可能均匀分布任务"""
    timetable = self.generate_timetable()
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    if today not in timetable:
        print("无法获取今天的时间表")
        return
    
    # 获取今天的固定任务和待办任务
    fixed_tasks = sorted(timetable[today]["fixed"], key=lambda x: x["start"])
    pending_tasks = [t for t in timetable[today]["tasks"] if t["status"] in ["pending", "in_progress"]]
    
    if not pending_tasks:
        print("没有待安排的任务")
        return
    
    # 计算总的空闲时间段和总空闲时长
    free_time = self._calculate_free_time(fixed_tasks)
    total_free_duration = sum(end - start for start, end in free_time)
    
    # 计算所有任务需要的总时间
    total_task_duration = sum(task["remaining_time"] for task in pending_tasks)
    
    if total_task_duration > total_free_duration:
        print(f"可用时间不足，无法安排所有任务。需要{total_task_duration}分钟，仅可用{total_free_duration}分钟")
        return
    
    # 计算最大可能的总间隙时间（总空闲时间 - 总任务时间）
    total_possible_gap = total_free_duration - total_task_duration
    # 计算任务间的最大可能间隙（任务数+1个间隙，首尾各一个）
    max_gap_between_tasks = total_possible_gap // (len(pending_tasks) + 1)
    # 至少保留10分钟间隙
    min_gap = 10
    gap_between_tasks = max(max_gap_between_tasks, min_gap)
    
    print(f"自动安排任务，任务间最大可能间隙为{gap_between_tasks}分钟")
    
    # 按任务所需时间排序（先短后长，更容易均匀分布）
    pending_tasks.sort(key=lambda x: x["remaining_time"])
    
    # 合并所有空闲时间为一个连续的时间块（按时间顺序）
    free_time.sort()
    merged_free_time = []
    current_start, current_end = free_time[0]
    
    for start, end in free_time[1:]:
        if start <= current_end:
            # 重叠或相邻，合并
            current_end = max(current_end, end)
        else:
            merged_free_time.append((current_start, current_end))
            current_start, current_end = start, end
    merged_free_time.append((current_start, current_end))
    
    # 尝试在合并的空闲时间内均匀安排任务
    scheduled = []
    remaining_tasks = pending_tasks.copy()
    
    for start, end in merged_free_time:
        period_duration = end - start
        
        # 计算当前时间段可安排的任务数
        if not remaining_tasks:
            break
            
        # 当前时间段可分配的总时间（任务+间隙）
        available_time = period_duration
        # 计算最多可安排多少个任务
        max_possible_tasks = 0
        required_time = 0
        
        for i, task in enumerate(remaining_tasks):
            # 每个任务需要 任务时间 + 间隙时间（最后一个任务不需要）
            task_required = task["remaining_time"] + (gap_between_tasks if i < len(remaining_tasks)-1 else 0)
            if required_time + task_required <= available_time:
                required_time += task_required
                max_possible_tasks = i + 1
            else:
                break
                
        if max_possible_tasks == 0:
            continue
            
        # 选择前max_possible_tasks个任务
        tasks_to_schedule = remaining_tasks[:max_possible_tasks]
        remaining_tasks = remaining_tasks[max_possible_tasks:]
        
        # 计算实际可用空间（减去任务总时间）
        total_task_time = sum(task["remaining_time"] for task in tasks_to_schedule)
        available_gap_space = period_duration - total_task_time
        
        # 计算实际间隙（尽可能接近最大可能间隙）
        actual_gap = min(gap_between_tasks, available_gap_space // (len(tasks_to_schedule) + 1))
        
        # 安排任务
        current_position = start + actual_gap  # 起始间隙
        
        for task in tasks_to_schedule:
            task_end = current_position + task["remaining_time"]
            scheduled.append({
                "task": task,
                "start": self.minutes_to_time(current_position),
                "end": self.minutes_to_time(task_end)
            })
            # 加上间隙
            current_position = task_end + actual_gap
    
    # 显示安排结果
    if scheduled:
        print("\n=== 今日任务安排 ===")
        for item in sorted(scheduled, key=lambda x: self.time_to_minutes(x["start"])):
            print(f"{item['start']} - {item['end']}: {item['task']['name']}")
    else:
        print("没有可安排的任务或无法安排任何任务")
        
    if remaining_tasks:
        print("\n无法安排的任务:")
        for task in remaining_tasks:
            print(f"- {task['name']} (需要{task['remaining_time']}分钟)")

def _calculate_free_time(self, fixed_tasks):
    """计算一天中的空闲时间段"""
    # 一天的时间范围（00:00 - 24:00）
    day_start = 0  # 0分钟
    day_end = 24 * 60  # 1440分钟
    
    # 处理跨天的固定任务（如睡觉从22:00到6:00）
    fixed_periods = []
    for task in fixed_tasks:
        start = task["start"]
        end = task["end"]
        
        if start < end:  # 正常时间段（如7:00-8:00）
            fixed_periods.append((start, end))
        else:  # 跨天时间段（如22:00-6:00）
            fixed_periods.append((start, day_end))
            fixed_periods.append((day_start, end))
    
    # 按开始时间排序
    fixed_periods.sort()
    
    # 计算空闲时间
    free_time = []
    prev_end = day_start
    
    for start, end in fixed_periods:
        if start > prev_end:
            free_time.append((prev_end, start))
        prev_end = max(prev_end, end)
    
    # 检查最后一个固定任务到一天结束的时间
    if prev_end < day_end:
        free_time.append((prev_end, day_end))
    
    return free_time

def main():
    manager = ScheduleManager()
    # 首次运行时设置固定任务
    if not manager.fixed_tasks["daily"]:
        manager.setup_fixed_tasks()
    
    # 启动提醒监控
    manager.start_reminder_monitor()
    
    while True:
        print("\n=== 时间管理系统 ===")
        print("1. 查看任务列表")
        print("2. 添加新任务")
        print("3. 修改固定任务")
        print("4. 生成周时间表")
        print("5. 开始任务")
        print("6. 查看总结")
        print("7. 清空所有数据并重新开始")
        print("8. 退出")
        print("9. 自动安排今日任务")
        
        choice = input("请选择操作: ")
        
        if choice == "1":
            print("\n当前任务:")
            for i, task in enumerate(manager.schedule["items"]):
                print(f"{i+1}. {task['name']} (状态: {task['status']}, 剩余: {task['remaining_time']}分钟, 截止: {task['deadline']})")
        
        elif choice == "2":
            manager.add_task()
        
        elif choice == "3":
            manager.modify_fixed_task()
        
        elif choice == "4":
            timetable = manager.generate_timetable()
            manager.print_timetable(timetable)
        
        elif choice == "5":
            task_name = input("请输入要开始的任务名称: ")
            manager.start_task(task_name)
        
        elif choice == "6":
            print("\n1. 每日总结")
            print("2. 每周总结")
            sub_choice = input("选择总结类型: ")
            if sub_choice in ["1", "2"]:
                manager.print_summary("daily" if sub_choice == "1" else "weekly")
        
        elif choice == "7":
            manager.clear_all_data()
        
        elif choice == "8":
            manager.reminder_event.set()
            print("感谢使用，再见！")
        elif choice == "9":
            manager.schedule_tasks_automatically()
            break
        else:
            print("无效的选择，请重试。")

if __name__ == "__main__":
    main()
