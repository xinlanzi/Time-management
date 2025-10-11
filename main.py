from task_manager import TaskManager
from fixed_task_manager import FixedTaskManager
from timetable_manager import TimetableManager
from summary_manager import SummaryManager
from data_handler import DataHandler
from clock import Clock

def main():
    # 初始化各模块
    task_manager = TaskManager()
    fixed_task_manager = FixedTaskManager()
    timetable_manager = TimetableManager(task_manager, fixed_task_manager)
    summary_manager = SummaryManager(task_manager)

    # 首次运行设置固定任务
    if not fixed_task_manager.fixed_tasks["daily"]:
        fixed_task_manager.setup_fixed_tasks()

    # 启动提醒监控
    task_manager.start_reminder_monitor()

    # 主交互循环
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
        print("10.启动番茄钟计时")

        choice = input("请选择操作: ")

        if choice == "1":
            # 查看任务列表
            print("\n当前任务:")
            for i, task in enumerate(task_manager.schedule["items"]):
                print(f"{i+1}. {task['name']} (状态: {task['status']}, 剩余: {task['remaining_time']}分钟, 截止: {task['deadline']})")

        elif choice == "2":
            # 添加新任务
            task_manager.add_task()

        elif choice == "3":
            # 修改固定任务
            fixed_task_manager.modify_fixed_task()

        elif choice == "4":
            # 生成周时间表
            timetable = timetable_manager.generate_week_timetable()
            timetable_manager.print_timetable(timetable)

        elif choice == "5":
            # 开始任务
            task_name = input("请输入要开始的任务名称: ")
            task_manager.start_task(task_name)

        elif choice == "6":
            # 查看总结
            sub_choice = input("1. 每日总结\n2. 每周总结\n选择总结类型: ")
            if sub_choice in ["1", "2"]:
                summary_manager.print_summary("daily" if sub_choice == "1" else "weekly")

        elif choice == "7":
            # 清空所有数据
            if input("\n警告：此操作将删除所有数据！确定继续？(y/n): ").lower() == 'y':
                DataHandler.clear_all_data()
                # 重新初始化
                task_manager = TaskManager()
                fixed_task_manager = FixedTaskManager()
                timetable_manager = TimetableManager(task_manager, fixed_task_manager)
                summary_manager = SummaryManager(task_manager)
                fixed_task_manager.setup_fixed_tasks()
                print("数据已清空并重新初始化")

        elif choice == "8":
            # 退出程序
            task_manager.reminder_event.set()
            print("感谢使用，再见！")
            break

        elif choice == "9":
            # 自动安排今日任务
            timetable_manager.auto_schedule_today_tasks()

        elif choice == "10":
            print("--- 启动番茄钟 ---")
            my_clock = Clock()
            my_clock.main()

        else:
            print("无效的选择，请重试。")

if __name__ == "__main__":

    main()


