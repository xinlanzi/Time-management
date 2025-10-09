from time_utils import TimeUtils
from data_handler import DataHandler

class FixedTaskManager:
    def __init__(self):
        self.fixed_tasks = DataHandler.load_fixed_tasks()

    def setup_fixed_tasks(self):
        """首次设置或重置固定任务"""
        if self.fixed_tasks["daily"]:
            if input("已检测到固定任务，是否重新设置？(y/n)").lower() != 'y':
                return

        # 设置每日固定任务
        print("\n=== 设置每日固定任务 ===")
        self.fixed_tasks["daily"] = [
            self._input_daily_task("睡觉"),
            self._input_daily_task("早餐"),
            self._input_daily_task("午餐"),
            self._input_daily_task("晚餐")
        ]

        # 设置每周固定任务
        print("\n=== 设置本周固定任务 ===")
        while input("是否添加每周特定任务？(y/n): ").lower() == 'y':
            self.fixed_tasks["weekly"].append(self._input_weekly_task())

        DataHandler.save_fixed_tasks(self.fixed_tasks)
        print("固定任务设置完成！")

    def _input_daily_task(self, task_name):
        """输入每日任务的时间并返回格式化数据"""
        start = input(f"请输入{task_name}开始时间(例如 22:00): ")
        end = input(f"请输入{task_name}结束时间(例如 06:00): ")
        return {
            "name": task_name,
            "start": TimeUtils.time_to_minutes(start),
            "end": TimeUtils.time_to_minutes(end)
        }

    def _input_weekly_task(self):
        """输入每周任务的时间并返回格式化数据"""
        name = input("任务名称: ")
        date = input("日期(YYYY-MM-DD): ")
        start = input("开始时间(HH:MM): ")
        end = input("结束时间(HH:MM): ")
        return {
            "name": name,
            "date": date,
            "start": TimeUtils.time_to_minutes(start),
            "end": TimeUtils.time_to_minutes(end)
        }

    def modify_fixed_task(self):
        """修改已有固定任务"""
        print("\n=== 修改固定任务 ===")
        choice = input("1. 每日固定任务\n2. 每周固定任务\n选择类型: ")

        if choice == "1":
            self._modify_daily_tasks()
        elif choice == "2":
            self._modify_weekly_tasks()

    def _modify_daily_tasks(self):
        """修改每日固定任务"""
        for i, task in enumerate(self.fixed_tasks["daily"]):
            start = TimeUtils.minutes_to_time(task["start"])
            end = TimeUtils.minutes_to_time(task["end"])
            print(f"{i+1}. {task['name']}: {start} - {end}")

        idx = int(input("选择要修改的任务序号: ")) - 1
        if 0 <= idx < len(self.fixed_tasks["daily"]):
            start = input("新的开始时间(HH:MM): ")
            end = input("新的结束时间(HH:MM): ")
            self.fixed_tasks["daily"][idx]["start"] = TimeUtils.time_to_minutes(start)
            self.fixed_tasks["daily"][idx]["end"] = TimeUtils.time_to_minutes(end)
            DataHandler.save_fixed_tasks(self.fixed_tasks)
            print("修改完成")

    def _modify_weekly_tasks(self):
        """修改每周固定任务"""
        for i, task in enumerate(self.fixed_tasks["weekly"]):
            start = TimeUtils.minutes_to_time(task["start"])
            end = TimeUtils.minutes_to_time(task["end"])
            print(f"{i+1}. {task['name']}({task['date']}): {start} - {end}")

        idx = int(input("选择要修改的任务序号: ")) - 1
        if 0 <= idx < len(self.fixed_tasks["weekly"]):
            date = input("新的日期(YYYY-MM-DD): ")
            start = input("新的开始时间(HH:MM): ")
            end = input("新的结束时间(HH:MM): ")
            self.fixed_tasks["weekly"][idx]["date"] = date
            self.fixed_tasks["weekly"][idx]["start"] = TimeUtils.time_to_minutes(start)
            self.fixed_tasks["weekly"][idx]["end"] = TimeUtils.time_to_minutes(end)
            DataHandler.save_fixed_tasks(self.fixed_tasks)
            print("修改完成")