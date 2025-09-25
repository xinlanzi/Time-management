'''
帮我写一个python代码，要求是：
1.文件读入，提取本地文件，在其中提取以前的时间表
2.输入一个新事项，包括：难易程度，完成需要的时间，事项名称，事项的截止日期
3.每个用户前置一个固定的睡眠时间和吃饭时间，工作时间
4.可以单独更改之前固定的时间，修改方式：查找事项名称，选定之后对时间进行更改
5.根据前置内容提供一个大致的时间表
6.在这个时间表中插入输入的新事项，并保证每日的休息时间尽量平均（可以对其他不固定的事项进行重新排序）
7.暂时实现一周的功能
'''

import json
import datetime
from datetime import timedelta

# 默认配置文件路径
FILE_PATH = "schedule.json"

# 默认固定时间（分钟表示，例如 22:00 = 22*60 = 1320）
DEFAULT_SLEEP_START = 22 * 60
DEFAULT_SLEEP_END = 6 * 60
DEFAULT_LUNCH_START = 12 * 60
DEFAULT_LUNCH_END = 13 * 60
DEFAULT_WORK_START = 9 * 60
DEFAULT_WORK_END = 18 * 60

class ScheduleManager:
    def __init__(self):
        self.schedule = self.load_schedule()
        self.fixed_times = self.load_fixed_times()
    
    def load_schedule(self):
        """加载本地时间表数据"""
        try:
            with open(FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"items": []}
    
    def load_fixed_times(self):
        """加载固定时间配置"""
        # 可以从文件加载，这里先用默认值
        return {
            "sleep_start": DEFAULT_SLEEP_START,
            "sleep_end": DEFAULT_SLEEP_END,
            "lunch_start": DEFAULT_LUNCH_START,
            "lunch_end": DEFAULT_LUNCH_END,
            "work_start": DEFAULT_WORK_START,
            "work_end": DEFAULT_WORK_END
        }
    
    def save_schedule(self):
        """保存时间表数据到本地文件"""
        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.schedule, f, ensure_ascii=False, indent=4)
    
    def add_item(self, difficulty, time_needed, name, deadline):
        """添加新事项"""
        new_item = {
            "difficulty": difficulty,
            "time_needed": time_needed,
            "name": name,
            "deadline": deadline,
            "type": "normal"
        }
        self.schedule["items"].append(new_item)
        self.save_schedule()
        print(f"已添加新事项: {name}")
    
    def modify_item(self, name, new_time):
        """修改事项时间"""
        for item in self.schedule["items"]:
            if item["name"] == name:
                item["time_needed"] = new_time
                self.save_schedule()
                print(f"已修改事项 {name} 的时间为 {new_time} 分钟")
                return
        print(f"未找到事项: {name}")
    
    def generate_timetable(self):
        """生成一周时间表"""
        today = datetime.date.today()
        week_schedule = {}
        
        # 初始化一周的日期
        for i in range(7):
            date_str = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            week_schedule[date_str] = {
                "fixed": [],
                "items": []
            }
        
        # 添加固定时间
        for date_str in week_schedule:
            week_schedule[date_str]["fixed"].append({
                "name": "睡眠",
                "start": self.fixed_times["sleep_start"],
                "end": self.fixed_times["sleep_end"]
            })
            week_schedule[date_str]["fixed"].append({
                "name": "午餐",
                "start": self.fixed_times["lunch_start"],
                "end": self.fixed_times["lunch_end"]
            })
            week_schedule[date_str]["fixed"].append({
                "name": "工作",
                "start": self.fixed_times["work_start"],
                "end": self.fixed_times["work_end"]
            })
        
        # 安排事项（简化版算法）
        for item in self.schedule["items"]:
            deadline = datetime.datetime.strptime(item["deadline"], "%Y-%m-%d").date()
            days_diff = (deadline - today).days
            
            if 0 <= days_diff < 7:
                date_str = deadline.strftime("%Y-%m-%d")
                week_schedule[date_str]["items"].append(item)
        
        return week_schedule
    
    def print_timetable(self, timetable):
        """打印时间表"""
        for date_str, schedule_data in timetable.items():
            print(f"\n日期: {date_str}")
            print("固定时间:")
            for fixed in schedule_data["fixed"]:
                start_time = f"{fixed['start']//60:02d}:{fixed['start']%60:02d}"
                end_time = f"{fixed['end']//60:02d}:{fixed['end']%60:02d}"
                print(f"  {start_time} - {end_time}: {fixed['name']}")
            
            print("事项安排:")
            for item in schedule_data["items"]:
                print(f"  {item['name']} (难度: {item['difficulty']}, 耗时: {item['time_needed']}分钟)")

def main():
    manager = ScheduleManager()
    
    while True:
        print("\n=== 时间表管理系统 ===")
        print("1. 查看当前事项")
        print("2. 添加新事项")
        print("3. 修改事项时间")
        print("4. 生成时间表")
        print("5. 退出")
        
        choice = input("请选择操作: ")
        
        if choice == "1":
            print("\n当前事项:")
            for item in manager.schedule["items"]:
                print(f"- {item['name']} (难度: {item['difficulty']}, 耗时: {item['time_needed']}分钟, 截止日期: {item['deadline']})")
        
        elif choice == "2":
            difficulty = input("请输入事项难度 (1-5): ")
            time_needed = int(input("请输入完成需要的时间 (分钟): "))
            name = input("请输入事项名称: ")
            deadline = input("请输入截止日期 (YYYY-MM-DD): ")
            manager.add_item(difficulty, time_needed, name, deadline)
        
        elif choice == "3":
            name = input("请输入要修改的事项名称: ")
            new_time = int(input("请输入新的时间 (分钟): "))
            manager.modify_item(name, new_time)
        
        elif choice == "4":
            timetable = manager.generate_timetable()
            manager.print_timetable(timetable)
        
        elif choice == "5":
            print("感谢使用，再见！")
            break
        
        else:
            print("无效的选择，请重试。")

if __name__ == "__main__":
    main()
