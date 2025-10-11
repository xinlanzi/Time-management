import tkinter as tk

class PomodoroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("番茄钟（Run 窗口可用）")
        self.root.geometry("300x150")

        self.label = tk.Label(root, text="00:00", font=("Arial", 48))
        self.label.pack(pady=20)

        self.status_label = tk.Label(root, text="准备开始任务", font=("Arial", 12))
        self.status_label.pack()

        self.running = False
        self.remaining = 0
        self.cycle = 1

        self.start_btn = tk.Button(root, text="开始番茄钟", command=self.start_pomodoro)
        self.start_btn.pack(side=tk.LEFT, padx=10)

        self.quit_btn = tk.Button(root, text="退出", command=self.quit_app)
        self.quit_btn.pack(side=tk.RIGHT, padx=10)

    def update_time(self):
        if self.remaining > 0 and self.running:
            mins, secs = divmod(self.remaining, 60)
            self.label.config(text=f"{mins:02d}:{secs:02d}")
            self.remaining -= 1
            self.root.after(1000, self.update_time)  # 1秒后再次调用自己
        elif self.running:
            # 当前阶段结束
            self.label.config(text="00:00")
            self.start_next_phase()

    def start_next_phase(self):
        if self.status_label.cget("text").startswith("第"):
            # 工作阶段结束，进入休息
            self.status_label.config(text="休息时间")
            self.remaining = 5 * 60
        else:
            # 休息阶段结束，进入下一轮工作
            self.cycle += 1
            self.status_label.config(text=f"第 {self.cycle} 轮 - 工作中")
            self.remaining = 25 * 60
        self.update_time()

    def start_pomodoro(self):
        if not self.running:
            self.running = True
            self.status_label.config(text=f"第 {self.cycle} 轮 - 工作中")
            self.remaining = 25 * 60
            self.update_time()

    def quit_app(self):
        self.running = False
        self.root.destroy()

def run_pomodoro():
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()
