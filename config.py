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

# 任务状态常量
TASK_STATUS = {
    "PENDING": "待处理",
    "SCHEDULED": "已安排", 
    "IN_PROGRESS": "in_progress",
    "COMPLETED": "已完成",
    "DELAYED": "delayed",
    "ABANDONED": "已放弃"
}
