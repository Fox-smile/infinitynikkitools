import os
import time
import tkinter as tk
from tkinter import messagebox, filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import queue
import json
import sys
import subprocess

# 配置文件路径
config_file = "config.json"

# 用于线程之间的通信
msg_queue = queue.Queue()

# 标记已经处理过的文件，避免重复处理
processed_files = set()

# 获取已保存的截图文件夹路径
def get_saved_screenshot_folder():
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config.get("screenshot_folder", None)
    return None

# 将截图文件夹路径保存到配置文件中
def save_screenshot_folder(path):
    config = {"screenshot_folder": path}
    with open(config_file, 'w') as f:
        json.dump(config, f)

# 提示用户选择截图文件夹并保存
def ask_user_for_screenshot_folder():
    root = tk.Tk()
    root.withdraw()  # 不显示主窗口
    folder_selected = filedialog.askdirectory(title="选择游戏截图文件夹")
    
    if folder_selected:
        save_screenshot_folder(folder_selected)
        return folder_selected
    else:
        messagebox.showerror("错误", "未选择文件夹")
        return None

# 主线程中显示弹窗并返回结果
def ask_save_in_main_thread(filename):
    def show_popup():
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口

        # 强制弹窗在最前端
        root.attributes("-topmost", True)

        # 使用 messagebox 询问是否保存截图
        result = messagebox.askyesno("保存截图", f"是否保存截图: {filename}")

        # 将结果传递给主线程
        msg_queue.put(result)

    # 将弹窗显示放到主线程中
    show_popup()

# 处理文件变更事件
class ScreenshotHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:  # 如果是文件夹创建事件，忽略
            return
        
        filename = os.path.basename(event.src_path)
        
        # 如果文件已经被处理过，跳过
        if filename in processed_files:
            return
        
        if event.src_path.endswith('.jpg') or event.src_path.endswith('.jpeg'):  # 过滤JPEG文件
            print(f"检测到新截图: {filename}")

            # 在文件保存后稍微延迟一下，确保文件写入完成
            time.sleep(1)  # 延迟1秒钟，等文件保存完成
            processed_files.add(filename)  # 标记该文件为已处理

            # 弹窗询问是否保存（直接调用主线程弹窗）
            ask_save_in_main_thread(filename)

            # 等待弹窗返回结果
            result = msg_queue.get()  # 获取弹窗返回的结果
            if not result:  # 用户选择不保存
                try:
                    os.remove(event.src_path)  # 删除截图
                    print(f"已删除截图: {filename}")
                except Exception as e:
                    print(f"删除截图失败: {e}")

# 监控文件夹
def monitor_folder():
    # 获取已保存的截图文件夹路径
    screenshot_folder = get_saved_screenshot_folder()

    if screenshot_folder is None:
        # 第一次运行或未找到已保存路径，提示用户选择路径
        screenshot_folder = ask_user_for_screenshot_folder()

        # 如果选择了路径，重启程序
        if screenshot_folder:
            # 重启程序
            print("路径已设置，正在重启程序...")
            sys.exit(subprocess.call([sys.executable, __file__]))  # 重启程序

    if screenshot_folder:
        event_handler = ScreenshotHandler()
        observer = Observer()
        observer.schedule(event_handler, screenshot_folder, recursive=False)
        observer.start()
        print(f"开始监控文件夹: {screenshot_folder}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    else:
        print("未设置截图保存路径，无法监控截图文件夹")

if __name__ == "__main__":
    monitor_folder()
