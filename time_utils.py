import datetime
from datetime import timedelta

class TimeUtils:
    @staticmethod
    def time_to_minutes(time_str):
        """将时间字符串(HH:MM)转换为分钟数"""
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes

    @staticmethod
    def minutes_to_time(minutes):
        """将分钟数转换为时间字符串(HH:MM)"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    @staticmethod
    def get_week_dates():
        """获取当前周的7天日期字符串(YYYY-MM-DD)"""
        today = datetime.date.today()
        return [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    @staticmethod
    def calculate_free_time(fixed_tasks):
        """计算一天中的空闲时间段（返回分钟数区间列表）"""
        day_start = 0  # 00:00（分钟）
        day_end = 24 * 60  # 24:00（分钟）
        fixed_periods = []

        # 处理跨天任务（如22:00-06:00）
        for task in fixed_tasks:
            start = task["start"]
            end = task["end"]
            if start < end:
                fixed_periods.append((start, end))
            else:
                fixed_periods.append((start, day_end))
                fixed_periods.append((day_start, end))

        # 排序并计算空闲时间
        fixed_periods.sort()
        free_time = []
        prev_end = day_start

        for start, end in fixed_periods:
            if start > prev_end:
                free_time.append((prev_end, start))
            prev_end = max(prev_end, end)
        if prev_end < day_end:
            free_time.append((prev_end, day_end))

        return free_time