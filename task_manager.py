import datetime
import time
import threading
from config import DIFFICULTY_DURATION, TASK_STATUS
from data_handler import DataHandler
from time_utils import TimeUtils

class TaskManager:
    def __init__(self):
        self.schedule = DataHandler.load_schedule()
        self.current_task = None
        self.running_tomato = None
        self.reminder_event = threading.Event()

    def add_task(self):
        """添加新任务"""
        print("\n=== 添加新任务 ===")
        name = input("任务名称: ")
        difficulty = input("难度(简单/较难/困难): ")

        # 处理任务时长
        if difficulty in DIFFICULTY_DURATION:
            if input(f"默认时长{DIFFICULTY_DURATION[difficulty]}分钟，使用默认值？(y/n): ").lower() == 'y':
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
            "remaining_time": time_needed,
            "deadline": deadline,
            "status": TASK_STATUS["PENDING"],
            "created_at": datetime.date.today().strftime("%Y-%m-%d")
        }

        self.schedule["items"].append(new_task)
        DataHandler.save_schedule(self.schedule)
        print(f"已添加任务: {name}")

    def start_task(self, task_name):
        """开始指定任务（含番茄钟）"""
        for task in self.schedule["items"]:
            if task["name"] == task_name and task["status"] in [TASK_STATUS["PENDING"], TASK_STATUS["IN_PROGRESS"]]:
                self._confirm_and_start(task)
                return
        print("未找到该任务或任务状态不允许开始")

    def _confirm_and_start(self, task):
        """确认并启动任务"""
        print(f"\n准备开始任务: {task['name']}")
        print("有5分钟时间确认是否开始...")

        # 等待用户确认
        start_confirmed = False
        for _ in range(5):
            if input("是否开始？(y/n，5分钟内未确认将视为放弃): ").lower() == 'y':
                start_confirmed = True
                break
            time.sleep(60)

        if not start_confirmed:
            task["status"] = TASK_STATUS["ABANDONED"]
            DataHandler.save_schedule(self.schedule)
            print("未确认，任务已标记为放弃")
            return

        # 启动番茄钟
        task["status"] = TASK_STATUS["IN_PROGRESS"]
        DataHandler.save_schedule(self.schedule)
        self.running_tomato = True
        remaining = self._tomato_timer(task, task["remaining_time"])

        # 更新任务状态
        if remaining <= 0:
            print("\n任务完成！")
            task["status"] = TASK_STATUS["COMPLETED"]
            task["remaining_time"] = 0
        else:
            task["remaining_time"] = remaining
            print(f"\n任务暂停，剩余时间: {remaining}分钟")
            self._handle_interruption(task)

        DataHandler.save_schedule(self.schedule)
        self.running_tomato = None

    def _tomato_timer(self, task, total_minutes):
        """番茄钟计时器（25分钟工作+5分钟休息）"""
        self.current_task = task
        cycles = (total_minutes // 25) + (1 if total_minutes % 25 > 0 else 0)
        remaining = total_minutes

        for i in range(cycles):
            work_time = min(25, remaining)
            print(f"\n开始第{i+1}个番茄钟，工作{work_time}分钟...")

            # 工作计时
            for t in range(work_time, 0, -1):
                if not self.running_tomato:
                    print("番茄钟已停止")
                    return remaining - (work_time - t)
                print(f"剩余工作时间: {t}分钟", end='\r')
                time.sleep(60)

            remaining -= work_time
            print("\n工作时间结束！请休息5分钟")

            # 休息计时
            for t in range(5, 0, -1):
                if not self.running_tomato:
                    print("番茄钟已停止")
                    return remaining
                print(f"剩余休息时间: {t}分钟", end='\r')
                time.sleep(60)

            print("\n休息结束！准备开始下一段工作")
            if remaining <= 0:
                break

        self.current_task = None
        return 0

    def _handle_interruption(self, task):
        """处理任务中断（暂停/延期）"""
        choice = input("\n1. 继续完成\n2. 另安排时间\n请选择: ")
        if choice == "1":
            task["remaining_time"] = int(input("估计还需要多少分钟: "))
        else:
            task["status"] = TASK_STATUS["DELAYED"]
            task["deadline"] = input("请输入新的截止日期(YYYY-MM-DD): ")

    def start_reminder_monitor(self):
        """启动提醒监控线程（每分钟检查一次）"""
        def monitor():
            while not self.reminder_event.is_set():
                now = datetime.datetime.now()
                current_time = now.hour * 60 + now.minute
                current_date = now.strftime("%Y-%m-%d")
                # 此处可扩展具体提醒逻辑
                time.sleep(60)

        threading.Thread(target=monitor, daemon=True).start()