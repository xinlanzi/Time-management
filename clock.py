import time
import winsound  # 仅适用于Windows系统，用于提示音

class Clock:
    def countdown(self, minutes):
        """倒计时函数，接收分钟数作为参数"""
        seconds = minutes * 60
        while seconds > 0:
            # 计算剩余的小时、分钟和秒
            mins, secs = divmod(seconds, 60)
            # 格式化显示时间
            time_format = f"{mins:02d}:{secs:02d}"
            # 打印时间，\r使光标回到行首，实现刷新效果
            print(f"剩余时间：{time_format}", end="\r")
            # 暂停1秒
            time.sleep(1)
            seconds -= 1

        print(f"\n{minutes}分钟计时结束！")
        # 播放提示音，频率440Hz，持续1000毫秒
        winsound.Beep(440, 1000)

    def main(self):
        print("准备开始任务")
        print("按Ctrl+C停止程序")

        try:
            cycle = 1
            while True:
                print(f"===== 第{cycle}轮 =====")
                print("开始工作！")
                self.countdown(25)

                print("休息时间~")
                self.countdown(5)

                print("休息时间结束，准备工作吧！")
                cycle += 1
                # 短暂停顿后开始下一轮
                time.sleep(2)
        except KeyboardInterrupt:
            print("工作结束！！")

if __name__ == "__main__":
    clock = Clock()
    clock.main()
