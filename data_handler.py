import json
import os
from config import FILE_PATH, FIXED_TASKS_PATH, SUMMARY_PATH, TASK_STATUS

class DataHandler:
    @staticmethod
    def load_schedule():
        """加载任务数据，为缺失状态的任务补充默认值"""
        try:
            with open(FILE_PATH, 'r', encoding='utf-8') as f:
                schedule = json.load(f)
                for task in schedule.get("items", []):
                    if "status" not in task:
                        task["status"] = TASK_STATUS["PENDING"]
                return schedule
        except (FileNotFoundError, json.JSONDecodeError):
            return {"items": []}

    @staticmethod
    def load_fixed_tasks():
        """加载固定任务(每日/每周)"""
        try:
            with open(FIXED_TASKS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"daily": [], "weekly": []}

    @staticmethod
    def load_summary():
        """加载总结数据"""
        try:
            with open(SUMMARY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"daily": {}, "weekly": {}, "monthly": {}}

    @staticmethod
    def save_schedule(schedule):
        """保存任务数据"""
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(schedule, f, ensure_ascii=False, indent=4)

    @staticmethod
    def save_fixed_tasks(fixed_tasks):
        """保存固定任务"""
        with open(FIXED_TASKS_PATH, 'w', encoding='utf-8') as f:
            json.dump(fixed_tasks, f, ensure_ascii=False, indent=4)

    @staticmethod
    def save_summary(summary):
        """保存总结数据"""
        with open(SUMMARY_PATH, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=4)

    @staticmethod
    def clear_all_data():
        """清空所有数据文件"""
        for path in [FILE_PATH, FIXED_TASKS_PATH, SUMMARY_PATH]:
            if os.path.exists(path):
                os.remove(path)