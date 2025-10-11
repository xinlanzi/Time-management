import datetime
from time_utils import TimeUtils
from config import TASK_STATUS

class TimetableManager:
    def __init__(self, task_manager, fixed_task_manager):
        self.task_manager = task_manager  # 依赖TaskManager实例
        self.fixed_task_manager = fixed_task_manager  # 依赖FixedTaskManager实例

    def generate_week_timetable(self):
        """生成一周时间表（含固定任务和待办任务）"""
        week_dates = TimeUtils.get_week_dates()
        week_schedule = {date: {"fixed": [], "tasks": []} for date in week_dates}

        # 添加固定任务
        for date_str in week_schedule:
            # 每日固定任务
            week_schedule[date_str]["fixed"].extend(self.fixed_task_manager.fixed_tasks["daily"])
            # 每周特定任务
            week_schedule[date_str]["fixed"].extend([
                task for task in self.fixed_task_manager.fixed_tasks["weekly"]
                if task["date"] == date_str
            ])

        # 添加待办任务（按截止日期排序）
        sorted_tasks = sorted(
            self.task_manager.schedule["items"],
            key=lambda x: datetime.datetime.strptime(x["deadline"], "%Y-%m-%d")
        )
        for task in sorted_tasks:
            if task["status"] in [TASK_STATUS["COMPLETED"], TASK_STATUS["ABANDONED"]]:
                continue
            deadline = datetime.datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            if deadline.strftime("%Y-%m-%d") in week_schedule:
                week_schedule[deadline.strftime("%Y-%m-%d")]["tasks"].append(task)

        return week_schedule

    def print_timetable(self, timetable):
        """打印时间表"""
        for date_str, data in timetable.items():
            print(f"\n===== {date_str} =====")
            print("固定任务:")
            for task in sorted(data["fixed"], key=lambda x: x["start"]):
                start = TimeUtils.minutes_to_time(task["start"])
                end = TimeUtils.minutes_to_time(task["end"])
                print(f"  {start} - {end}: {task['name']}")

            print("\n待办任务:")
            for i, task in enumerate(data["tasks"]):
                print(f"  {i+1}. {task['name']} (剩余: {task['remaining_time']}分钟, 难度: {task['difficulty']})")

    def auto_schedule_today_tasks(self):
        """自动安排今日任务到空闲时段"""
        timetable = self.generate_week_timetable()
        today = datetime.date.today().strftime("%Y-%m-%d")
        if today not in timetable:
            print("无法获取今天的时间表")
            return

        # 获取今日固定任务和待办任务（统一筛选：按需选择包含 SCHEDULED 或仅 PENDING）
        fixed_tasks = sorted(timetable[today]["fixed"], key=lambda x: x["start"])
        pending_tasks = [t for t in timetable[today]["tasks"] if t["status"] == TASK_STATUS["PENDING"] or t["status"] == TASK_STATUS["SCHEDULED"]]

        if not pending_tasks:
            print("没有待安排的任务")
            return

        # 计算空闲时间和所需时间
        free_time = TimeUtils.calculate_free_time(fixed_tasks)
        total_free = sum(end - start for start, end in free_time)
        total_needed = sum(task["remaining_time"] for task in pending_tasks)

        if total_needed > total_free:
            print(f"可用时间不足：需要{total_needed}分钟，仅{total_free}分钟可用")
            return

        # 排序任务、合并空闲时间（删除重复的 pending_tasks 初始化）
        pending_tasks.sort(key=lambda x: x["remaining_time"])
        merged_free = self._merge_free_time(free_time)
        
        # 直接使用之前筛选好的 pending_tasks 安排
        scheduled = self._schedule_tasks_in_free_time(merged_free, pending_tasks, total_free, total_needed)
        self._print_scheduled_tasks(scheduled, pending_tasks)

    def _merge_free_time(self, free_time):
        """合并重叠的空闲时间段"""
        if not free_time:
            return []
        free_time.sort()
        merged = [list(free_time[0])]
        for start, end in free_time[1:]:
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1][1] = max(last_end, end)
            else:
                merged.append([start, end])
        return merged

    def _schedule_tasks_in_free_time(self, merged_free, tasks, total_free, total_needed):
        """在空闲时间内均匀安排任务"""
        total_gap = total_free - total_needed
        min_gap = 10  # 最小间隙10分钟
        gap = max(total_gap // (len(tasks) + 1), min_gap)
        scheduled = []
        remaining_tasks = tasks.copy()

        for start, end in merged_free:
            if not remaining_tasks:
                break
            period_duration = end - start
            max_tasks = self._calculate_max_tasks(remaining_tasks, period_duration, gap)
            if max_tasks == 0:
                continue
            to_schedule = remaining_tasks[:max_tasks]
            remaining_tasks = remaining_tasks[max_tasks:]
            # 标记已安排的任务状态为"SCHEDULED"
            for task in to_schedule:
                task["status"] = TASK_STATUS["SCHEDULED"]  # 更新状态
            
            scheduled.extend(self._place_tasks_in_period(start, end, to_schedule, gap))

        return scheduled

    def _calculate_max_tasks(self, tasks, period_duration, gap):
        """计算当前时段可安排的最大任务数"""
        required = 0
        max_tasks = 0
        for i, task in enumerate(tasks):
            add_gap = gap if i < len(tasks) - 1 else 0
            if required + task["remaining_time"] + add_gap <= period_duration:
                required += task["remaining_time"] + add_gap
                max_tasks = i + 1
            else:
                break
        return max_tasks

    def _place_tasks_in_period(self, start, end, tasks, gap):
        """将任务放置到具体时间段内"""
        scheduled = []
        current_pos = start + gap  # 起始间隙
        total_task_time = sum(t["remaining_time"] for t in tasks)
        actual_gap = min(gap, (end - start - total_task_time) // (len(tasks) + 1))

        for task in tasks:
            task_end = current_pos + task["remaining_time"]
            scheduled.append({
                "task": task,
                "start": TimeUtils.minutes_to_time(current_pos),
                "end": TimeUtils.minutes_to_time(task_end)
            })
            current_pos = task_end + actual_gap
        return scheduled

    def _print_scheduled_tasks(self, scheduled, remaining_tasks):
        """打印安排结果"""
        if scheduled:
            print("\n=== 今日任务安排 ===")
            for item in sorted(scheduled, key=lambda x: TimeUtils.time_to_minutes(x["start"])):
                print(f"{item['start']} - {item['end']}: {item['task']['name']}")
        else:
            print("没有可安排的任务")

        if remaining_tasks:
            print("\n无法安排的任务:")
            for task in remaining_tasks:
                print(f"- {task['name']} (需要{task['remaining_time']}分钟)")
