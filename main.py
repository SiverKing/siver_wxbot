#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""main.py
siver_wxbot 配置管理器 V2.0
说明：
    本脚本用于加载和编辑新版配置文件（config.json），同时集成了机器人控制功能，
    包括启动、关闭、重启机器人，并将机器人线程的输出捕获后显示在UI界面的文本框内。
    
作者：https://siver.top
"""

import json         # 处理JSON数据
import os           # 文件操作
import tkinter as tk    # 图形界面库
from tkinter import messagebox, ttk, simpledialog  # 弹窗、主题控件及简单对话框
import ttkbootstrap as ttk   # 美化版tkinter组件库
import sys
import traceback    # 异常追踪
import threading    # 多线程支持
import ctypes       # 用于在线程中抛出异常
import inspect      # 检查对象类型
import queue        # 队列，用于线程间传递数据
import wxbot_preview  # 导入机器人服务模块

# 配置文件名称常量
CONFIG_FILE = "config.json"

def _async_raise(tid, exctype):
    """
    在线程中抛出异常（仅限 CPython，不安全）
    参数：
        tid: 线程ID
        exctype: 要抛出的异常类型
    """
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("无效的线程 ID")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(tid), None)
        raise SystemError("PyThreadState_SetAsyncExc 失败")

class QueueWriter:
    """
    将写入的文本放入队列，用于捕获机器人线程的输出
    """
    def __init__(self, out_queue):
        self.out_queue = out_queue

    def write(self, text):
        if text:
            self.out_queue.put(text)

    def flush(self):
        pass

class Tooltip:
    """
    自定义提示工具类：当鼠标悬停在问号图标上时显示帮助提示信息
    """
    def __init__(self, widget, text):
        self.widget = widget      # 绑定提示的组件
        self.text = text          # 提示文本
        self.tooltip_window = None
        # 绑定鼠标进入和离开事件
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        """显示提示信息"""
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)  # 移除窗口装饰
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(
            self.tooltip_window,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padding=5
        )
        label.pack()

    def hide_tooltip(self, event=None):
        """隐藏提示信息"""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class ConfigEditor:
    """
    配置管理器类：
    1. 加载、显示、保存新版配置文件（config.json），支持文本、列表、多行、开关等输入组件；
    2. 提供机器人控制功能，包括启动、关闭、重启机器人，并将机器人的标准输出显示在界面上。
    """
    def __init__(self, root):
        self.root = root
        self.root.title("siver_wxbot 管理器 V2.0  https://siver.top")
        self.root.geometry("800x800")
        
        # 机器人控制相关属性
        self.bot_thread = None   # 机器人线程引用
        self.status_var = tk.StringVar(value="状态：未运行")
        self.status_style = "inverse-danger"  # 初始状态显示红色（未运行）
        self.output_queue = queue.Queue()     # 队列用于捕获机器人线程的输出
        
        # 配置项提示说明，字段名称需与配置文件中保持一致
        self.tooltips = {
            "鼠标放在？？上查看提示": "鼠标放在？？上查看提示",
            "api_key": "在此处填写从开放平台获取的API密钥",
            "base_url": "填写开放平台的接口网址/链接",
            "model1": "你在开发平台要调用的模型名称",
            "model2": "你在开发平台要调用的模型名称",
            "model3": "你在开发平台要调用的模型名称",
            "model4": "你在开发平台要调用的模型名称",
            "prompt": "系统提示词，用于定义机器人的基本行为和回复规则",
            "管理员": "管理员名称，用于识别机器人管理者",
            "监听用户列表": "需要监听的用户列表（每行一个用户ID）...",
            "机器人名字": "机器人在被询问身份时回复的名称",
            "监听群组列表": "需要监听的群组列表（每行一个群组名称）...",
            "群机器人开关": "启用/禁用群机器人功能",
            "备忘录1": "备忘信息1，用于记录重要信息",
            "备忘录2": "备忘信息2，用于记录其他信息"
        }
        
        self.style = ttk.Style(theme="minty")
        self.setup_ui()
        self.load_config()
        # 开始定时更新机器人输出显示
        self.update_output()
    
    def setup_ui(self):
        """构建主界面布局"""
        # 状态区域：显示机器人当前状态
        status_frame = ttk.Frame(self.root)
        status_frame.pack(pady=5, fill=tk.X)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, bootstyle=self.status_style)
        self.status_label.pack()
        
        # 主容器区域，用于放置配置项（带滚动功能）
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = tk.Canvas(main_frame)
        self.scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        # 绑定鼠标滚轮事件（适用于 Windows/macOS，Linux下可另外绑定<Button-4>/<Button-5>）
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        # 输出区域：用于显示机器人线程的输出
        output_frame = ttk.Frame(self.root)
        output_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(5,10))
        ttk.Label(output_frame, text="机器人输出：").pack(anchor="w")
        self.output_text = tk.Text(output_frame, height=10, state=tk.DISABLED)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # 按钮区域：配置保存/重新加载、启动/关闭/重启机器人
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="保存配置", command=self.save_config, bootstyle="success").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重新加载", command=self.load_config, bootstyle="info").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="启动机器人", command=self.start_bot, bootstyle="primary").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭机器人", command=self.stop_bot, bootstyle="danger").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="重启机器人", command=self.restart_bot, bootstyle="warning").pack(side=tk.LEFT, padx=5)
    
    def on_mousewheel(self, event):
        """
        处理鼠标滚轮事件，使配置项区域能够上下滚动
        Windows/macOS 下 event.delta 的值一般为 120 的倍数
        """
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def create_field(self, parent, key, value):
        """
        根据配置项字段名创建对应的输入组件
        """
        # ✅ 不显示 api_sdk_list
        if key == "api_sdk_list":
            return None  

        field_frame = ttk.Frame(parent)
        field_frame.pack(fill=tk.X, pady=5)
        label = ttk.Label(field_frame, text=f"{key}:", width=20)
        label.pack(side=tk.LEFT)

        if key == "api_sdk":
            sdk_list = self.config.get("api_sdk_list", [])
            widget = self.create_combobox_field(field_frame, key, value, sdk_list)
        elif key in ["监听用户列表", "监听群组列表"]:
            widget = self.create_list_field(field_frame, key, value)
        elif key == "prompt":
            widget = self.create_multiline_field(field_frame, value)
        elif key == "群机器人开关":
            widget = self.create_switch_field(field_frame, key, value)
        elif "api" in key.lower() or "备忘录" in key:
            widget = self.create_secret_field(field_frame, key, value)
        else:
            widget = self.create_text_field(field_frame, key, value)

        self.add_help_tooltip(field_frame, key)
        return widget

    
    def add_help_tooltip(self, parent, key):
        """在输入组件旁添加问号图标，鼠标悬停时显示该配置项的说明"""
        tooltip_text = self.tooltips.get(key, "暂无说明")
        help_icon = ttk.Label(parent, text="？？", cursor="question_arrow")
        help_icon.pack(side=tk.LEFT, padx=5)
        Tooltip(help_icon, tooltip_text)
    
    def create_text_field(self, parent, key, value):
        """创建普通文本输入框"""
        entry = ttk.Entry(parent, width=40)
        entry.insert(0, str(value))
        entry.pack(side=tk.LEFT, expand=True)
        return entry
    
    def create_secret_field(self, parent, key, value):
        """
        创建加密字段输入框：
        使用星号隐藏输入内容，并提供眼睛按钮切换显示模式
        """
        frame = ttk.Frame(parent)
        entry = ttk.Entry(frame, width=35, show="*")
        entry.insert(0, value)
        entry.pack(side=tk.LEFT, expand=True)
        ttk.Button(frame, text="👁", width=2,
                   command=lambda: self.toggle_visibility(entry),
                   bootstyle="link").pack(side=tk.LEFT)
        frame.pack(side=tk.LEFT, expand=True)
        return entry
    
    def toggle_visibility(self, entry):
        """切换加密字段的显示状态：显示或隐藏实际内容"""
        current_show = entry.cget("show")
        entry.config(show="" if current_show == "*" else "*")
    
    def create_switch_field(self, parent, key, value):
        """
        创建开关控件：
        将字符串或布尔值转换为布尔变量，并根据状态显示“启用”或“禁用”
        """
        bool_value = value if isinstance(value, bool) else value.lower() == "true"
        var = tk.BooleanVar(value=bool_value)
        switch = ttk.Checkbutton(
            parent,
            text="启用" if var.get() else "禁用",
            variable=var,
            bootstyle="round-toggle",
            command=lambda: switch.config(text="启用" if var.get() else "禁用")
        )
        switch.pack(side=tk.LEFT)
        return var
    def create_field(self, parent, key, value):
        """
        根据配置项字段名创建对应的输入组件
        """
        field_frame = ttk.Frame(parent)
        field_frame.pack(fill=tk.X, pady=5)
        label = ttk.Label(field_frame, text=f"{key}:", width=20)
        label.pack(side=tk.LEFT)

        # 特殊处理 api_sdk 下拉框
        if key == "api_sdk":
            sdk_list = self.config.get("api_sdk_list", [])
            widget = self.create_combobox_field(field_frame, key, value, sdk_list)
        elif key == "api_sdk_list":
            # 直接显示为只读，不让编辑
            widget = self.create_list_field(field_frame, key, value)
            widget.config(state=tk.DISABLED)
        elif key in ["监听用户列表", "监听群组列表"]:
            widget = self.create_list_field(field_frame, key, value)
        elif key == "prompt":
            widget = self.create_multiline_field(field_frame, value)
        elif key == "群机器人开关":
            widget = self.create_switch_field(field_frame, key, value)
        elif "api" in key.lower() or "备忘录" in key:
            widget = self.create_secret_field(field_frame, key, value)
        else:
            widget = self.create_text_field(field_frame, key, value)

        self.add_help_tooltip(field_frame, key)
        return widget

    def create_combobox_field(self, parent, key, value, values):
        """创建下拉选择框"""
        combobox = ttk.Combobox(
            parent,
            values=values,
            state="readonly",
            width=37
        )

        # ✅ 启动/加载时，强制设置显示值
        if value and value in values:
            combobox.set(value)   # 显示配置文件里的值
        elif values:  
            combobox.set(values[0])  # 如果配置里的值不在候选项里，默认第一个
        else:
            combobox.set("")  # 候选项为空时保持空

        combobox.pack(side=tk.LEFT, expand=True)
        return combobox

    def create_list_field(self, parent, key, value):
        """
        创建可编辑列表控件，用于“监听用户列表”和“监听群组列表”
        """
        frame = ttk.Frame(parent)
        listbox = tk.Listbox(frame, width=30, height=4)
        scrollbar = ttk.Scrollbar(frame, orient="vertical")
        for item in value:
            listbox.insert(tk.END, item)
        listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)
        
        btn_frame = ttk.Frame(frame)
        ttk.Button(btn_frame, text="＋ 添加", command=lambda: self.add_list_item(listbox),
                   bootstyle="outline-success").pack(fill=tk.X)
        ttk.Button(btn_frame, text="－ 删除", command=lambda: self.remove_list_item(listbox),
                   bootstyle="outline-danger").pack(fill=tk.X, pady=5)
        
        listbox.pack(side=tk.LEFT)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        btn_frame.pack(side=tk.LEFT, padx=5)
        frame.pack(side=tk.LEFT, expand=True)
        return listbox
    
    def add_list_item(self, listbox):
        """弹出对话框添加新项目到列表中"""
        new_item = simpledialog.askstring("添加项目", "请输入新项目:")
        if new_item:
            listbox.insert(tk.END, new_item)
    
    def remove_list_item(self, listbox):
        """删除列表中选中的项"""
        try:
            index = listbox.curselection()[0]
            listbox.delete(index)
        except IndexError:
            pass
    
    def create_multiline_field(self, parent, value):
        """创建多行文本输入框，适用于较长文本，如系统提示词"""
        frame = ttk.Frame(parent)
        text = tk.Text(frame, width=50, height=5, wrap=tk.WORD)
        scroll = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.insert("1.0", value)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        return text
    
    def load_config(self):
        try:
            # 清空旧有的配置项控件
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            if not os.path.exists(CONFIG_FILE):
                # 默认配置字典
                base_config = {
                    "鼠标放在？？上查看提示": "鼠标放在？？上查看提示",
                    "api_sdk_list": ["OpenAI SDK", "Dify", "Coze"],  # ✅ 永远存在
                    "api_sdk": "Coze",
                    "api_key": "your-api-key",
                    "base_url": "https://api.example.com/v1",
                    "model1": "模型名称1",
                    "model2": "模型名称2",
                    "model3": "模型名称3",
                    "model4": "模型名称4",
                    "prompt": "请输入系统提示词...",
                    "管理员": "管理员名称",
                    "监听用户列表": [],
                    "机器人名字": "机器人名称",
                    "监听群组列表": [],
                    "群机器人开关": "False",
                    "备忘录1": "备忘信息1",
                    "备忘录2": "备忘信息2",
                }
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(base_config, f, ensure_ascii=False, indent=4)
                messagebox.showinfo("提示", f"已创建默认配置文件：\n{os.path.abspath(CONFIG_FILE)}\n请根据需求修改配置")

            # 读取配置文件
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                self.config = json.load(f)

            # ✅ 跳过 api_sdk_list，不显示在UI
            self.fields = {}
            for key, value in self.config.items():
                if key == "api_sdk_list":  # 不显示
                    continue
                self.fields[key] = self.create_field(self.scrollable_frame, key, value)
        except json.JSONDecodeError:
            messagebox.showerror("配置文件错误", "配置文件格式不正确，请检查JSON语法")
        except Exception as e:
            messagebox.showerror("加载错误", f"加载配置失败: {str(e)}\n{traceback.format_exc()}")
    
    def save_config(self):
        try:
            new_config = {}
            for key, widget in self.fields.items():
                if key in ["监听用户列表", "监听群组列表"]:
                    new_config[key] = list(widget.get(0, tk.END))
                elif key == "群机器人开关":
                    new_config[key] = "True" if widget.get() else "False"
                elif isinstance(widget, tk.Text):
                    new_config[key] = widget.get("1.0", tk.END).strip()
                elif isinstance(widget, ttk.Combobox):
                    new_config[key] = widget.get()
                else:
                    new_config[key] = widget.get()

            # ✅ 永远保留 api_sdk_list
            new_config["api_sdk_list"] = self.config.get("api_sdk_list", ["OpenAI SDK", "Dify", "Coze"])

            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_config, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", "配置已保存，建议重启机器人以生效")
            self.load_config()
        except Exception as e:
            messagebox.showerror("保存错误", f"保存配置失败: {str(e)}")
    
    def start_bot(self):
        """
        启动机器人：
            1. 如果已有机器人线程在运行，则提示已运行；
            2. 启动新线程运行 wxbot_service.wxbot_service_main()，
               并将线程的标准输出重定向到队列中。
        """
        try:
            if self.bot_thread and self.bot_thread.is_alive():
                self.status_var.set("状态：机器人已在运行")
                return
            # 启动前先清空输出区域
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete("1.0", tk.END)
            self.output_text.config(state=tk.DISABLED)
            
            def run_bot():
                try:
                    # 重定向标准输出和错误输出到队列
                    old_stdout = sys.stdout
                    old_stderr = sys.stderr
                    sys.stdout = QueueWriter(self.output_queue)
                    sys.stderr = QueueWriter(self.output_queue)
                    # 如需COM初始化，可导入 pythoncom（仅在需要时）
                    try:
                        import pythoncom
                        pythoncom.CoInitialize()
                    except ImportError:
                        pass
                    wxbot_preview.start_bot()
                except Exception as e:
                    print("机器人运行时出错：", e)
                finally:
                    try:
                        import pythoncom
                        pythoncom.CoUninitialize()
                    except ImportError:
                        pass
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
            
            self.bot_thread = threading.Thread(target=run_bot, daemon=True)
            self.bot_thread.start()
            # 修改状态显示为绿色（运行中）
            self.status_style = "inverse-success"
            self.status_label.config(bootstyle=self.status_style)
            self.status_var.set("状态：机器人启动成功")
        except Exception as e:
            error_msg = f"启动失败：{str(e)}\n{traceback.format_exc()}"
            self.status_var.set("状态：启动失败")
            messagebox.showerror("启动错误", error_msg)
    
    def stop_bot(self):
        """
        关闭机器人：
            如果机器人线程正在运行，则使用 _async_raise 抛出 KeyboardInterrupt 异常停止线程，
            并更新状态显示。
        """
        try:
            if self.bot_thread and self.bot_thread.is_alive():
                # _async_raise(self.bot_thread.ident, KeyboardInterrupt)
                # self.bot_thread.join(timeout=10)
                wxbot_preview.stop_bot() # 调用 wxbot_preview 模块的停止函数
                self.status_style = "inverse-danger"
                self.status_label.config(bootstyle=self.status_style)
                self.status_var.set("状态：机器人已关闭")
                self.bot_thread = None
            else:
                self.status_var.set("状态：没有运行中的机器人")
        except Exception as e:
            error_msg = f"关闭失败：{str(e)}\n{traceback.format_exc()}"
            self.status_var.set("状态：关闭失败")
            messagebox.showerror("关闭错误", error_msg)
    
    def restart_bot(self):
        """先关闭机器人，再启动机器人"""
        self.stop_bot()
        self.start_bot()
    
    def update_output(self):
        """
        定时检查输出队列，将机器人线程的输出显示在文本框中
        每100毫秒检查一次
        """
        try:
            while not self.output_queue.empty():
                text = self.output_queue.get_nowait()
                self.output_text.config(state=tk.NORMAL)
                self.output_text.insert(tk.END, text)
                self.output_text.see(tk.END)
                self.output_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.root.after(100, self.update_output)

def main():
    """程序入口函数：创建窗口并启动主事件循环"""
    root = ttk.Window()
    app = ConfigEditor(root)
    root.mainloop()

if __name__ == "__main__":
    main()
