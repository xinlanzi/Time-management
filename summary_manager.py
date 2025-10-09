import datetime
from datetime import timedelta
from data_handler import DataHandler

class SummaryManager:
    def __init__(self, task_manager):
        self.task_manager = task_manager  # 依赖TaskManager实例
        self.summary = DataHandler.load_summary()

    def generate_daily_summary(self, date_str=None):
        """生成指定日期的每日总结"""
        date = date_str or datetime.date.today().strftime("%Y-%m-%d")
        tasks = [t for t in self.task_manager.schedule["items"] if t["created_at"] == date]

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
        DataHandler.save_summary(self.summary)
        return summary

    def generate_weekly_summary(self):
        """生成本周总结"""
        today = datetime.date.today()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        week_end = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")
        week_key = f"{week_start}至{week_end}"

        all_tasks = self.task_manager.schedule["items"]
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
        DataHandler.save_summary(self.summary)
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