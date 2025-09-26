#!/usr/bin/env python3
# Siver微信机器人 siver_wxbot
# 作者：https://siver.top

ver = "V2.1.0"         # 当前版本
ver_log = "日志：V2.1版本，新增接口支持，Openai ADK、Dify、扣子接口现在均支持使用"    # 日志
import time
import json
import re
import traceback
import email_send
from openai import OpenAI
import requests
from cozepy import COZE_CN_BASE_URL # 扣子官方python库
from cozepy import Coze, TokenAuth, Message, ChatStatus, MessageContentType, ChatEventType
from datetime import datetime, timedelta
from wxauto import WeChat
from wxauto.msgs import *

# -------------------------------
# 配置相关
# -------------------------------

# 配置文件路径
CONFIG_FILE = 'config.json'

# 全局配置字典及相关变量（将在 refresh_config 中更新）
config = {}
listen_list = []    # 监听的用户列表
api_key = ""        # API 密钥
base_url = ""       # API 基础 URL
AtMe = ""           # 机器人@的标识
bot_name = ""       # 机器人名字
cmd = ""            # 命令接收账号（管理员）
group = []          # 群聊ID
group_switch = None # 群机器人开关
group_welcome = False
group_welcome_msg = "欢迎新朋友！请先查看群公告！本消息由wxautox发送!"
model1 = ""         # 模型1标识
model2 = ""         # 模型2标识
model3 = ""         # 模型3标识
model4 = ""         # 模型4标识
prompt = ""         # AI提示词
# 当前使用的模型和 API 客户端
DS_NOW_MOD = ""
client = None

def is_err(id, err="无"):
    '''错误中断并发送邮件 
    id：邮件主题
    err:错误信息'''
    print(traceback.format_exc())
    print(err)
    email_send.send_email(subject=id, content='错误信息：\n'+traceback.format_exc()+"\nerr信息：\n"+str(err))
    while True:
        print("程序已保护现场，检查后请重启程序")
        time.sleep(100)
def now_time(time="%Y/%m/%d %H:%M:%S "):
    # 获取当前时间
    now = datetime.now()
    # 格式化时间为 YYYY/MM/DD HH:mm:ss
    formatted_time = now.strftime(time)
    return formatted_time

def check_wechat_window():
    """检测微信是否运行"""
    return wx.IsOnline()

def load_config():
    """
    从配置文件加载配置，并赋值给全局变量 config
    """
    global config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            config = json.load(file)
            print("配置文件加载成功")
    except Exception as e:
        print("打开配置文件失败，请检查配置文件！", e)
        while True:
            time.sleep(100)


def update_global_config():
    """
    将 config 中的配置项更新到全局变量中，并初始化 API 客户端
    """
    global listen_list, api_key, base_url, AtMe, cmd, group, model1, model2, model3, model4, prompt, DS_NOW_MOD, client, group_switch, bot_name
    listen_list = config.get('监听用户列表', [])
    api_key = config.get('api_key', "")
    base_url = config.get('base_url', "")
    # AtMe = "@"+wx.nickname+" " # 绑定AtMe
    cmd = config.get('管理员', "")
    group = (config.get('监听群组列表', ""))
    group_switch = config.get('群机器人开关', '')
    bot_name = config.get("机器人名字", '')
    model1 = config.get('model1', "")
    model2 = config.get('model2', "")
    model3 = config.get('model3', "")
    model4 = config.get('model4', "")
    prompt = config.get('prompt', "")
    # 默认使用模型1
    DS_NOW_MOD = model1
    # 初始化 OpenAI 客户端
    client = OpenAI(api_key=api_key, base_url=base_url)
    print(now_time()+"全局配置更新完成")


def refresh_config():
    """
    刷新配置：重新加载配置文件并更新全局变量
    """
    load_config()
    update_global_config()


def save_config():
    """
    将当前的配置写回到配置文件
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as file:  # 写入配置文件
            json.dump(config, file, ensure_ascii=False, indent=4)  # 保留中文原格式 
    except Exception as e:  # 异常处理
        print("保存配置文件失败:", e)  # 显示错误信息   


def add_user(name):
    """
    添加用户至监听列表，并更新配置
    """
    if name not in config.get('监听用户列表', []):  # 检查用户是否已存在
        config['监听用户列表'].append(name)  # 添加用户到监听列表
        save_config()  # 保存配置
        refresh_config()  # 刷新配置
        print("添加后的  监听用户列表:", config['监听用户列表'])  # 显示添加后的列表
    else:
        print(f"用户 {name} 已在监听列表中")  # 显示用户已存在  


def remove_user(name):
    """
    从监听列表中删除指定用户，并更新配置
    """
    if name in listen_list:  # 检查用户是否存在
        config['监听用户列表'].remove(name)  # 从列表中删除用户
        save_config()  # 保存配置
        refresh_config()  # 刷新配置
        print("删除后的 监听用户列表:", config['监听用户列表'])  # 显示删除后的列表
    else:
        print(f"用户 {name} 不在监听列表中")


def set_group(new_group):
    """
    更改监听的群聊ID，并更新配置
    """
    config['监听群组列表'] = new_group  # 更新群聊ID
    save_config()  # 保存配置
    refresh_config()  # 刷新配置
    print("群组已更改为", config['监听群组列表'])  # 显示更新后的群聊ID

def add_group(name):
    """
    添加群组至监听列表，并更新配置
    """
    if name not in config.get('监听群组列表', []):  # 检查用户是否已存在
        config['监听群组列表'].append(name)  # 添加用户到监听列表
        save_config()  # 保存配置
        refresh_config()  # 刷新配置
        print("添加后的  监听群组列表:", config['监听群组列表'])  # 显示添加后的列表
    else:
        print(f"群组 {name} 已在监听列表中")  # 显示用户已存在  
def remove_group(name):
    """
    删除群组从监听列表，并更新配置
    """
    if name in config.get('监听群组列表', []):  # 检查用户是否存在
        config['监听群组列表'].remove(name)  # 从列表中删除用户
        save_config()  # 保存配置
        refresh_config()  # 刷新配置
        print("删除后的 监听群组列表:", config['监听群组列表'])  # 显示删除后的列表
    else:
        print(f"群组 {name} 不在监听列表中")

def set_group_switch(switch_value):
    """
    设置是否启用群机器人（"True" 或 "False"），并更新配置
    """
    config['群机器人开关'] = switch_value  # 更新群机器人开关状态
    save_config()  # 保存配置       
    refresh_config()  # 刷新配置
    print("群开关设置为", config['群机器人开关'])  # 显示更新后的开关状态
def set_config(id, new_content):
    """
    更改配置
    id:字段
    new_content:新的字段值
    """
    config[id] = new_content  # 更新
    save_config()  # 保存配置
    refresh_config()  # 刷新配置
    print(now_time()+id+"已更改为:", config[id])  # 显示更新后的

def split_long_text(text, chunk_size=2000):
    # 使用range生成切割起始位置序列：0, chunk_size, 2*chunk_size...
    # 通过列表推导式循环截取每个分段
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


def API_chat(message, model, stream, prompt):
    """
    根据配置的api_sdk来选择调用API
    """
    if config.get('api_sdk') == 'OpenAI SDK':
        print("使用OpenAI SDK接口")
        return deepseek_chat(message, model, stream, prompt)
    elif config.get('api_sdk') == 'Dify':
        print("使用Dify API接口")
        return DifyAPI(config).chat(message, model, stream, prompt)
    elif config.get('api_sdk') == 'Coze':
        print("使用Coze API接口")
        return CozeAPI(config).chat(message, model, stream, prompt)
    else:
        print("未配置API SDK，默认采用Openai SDK")
        return deepseek_chat(message, model, stream, prompt)
# -------------------------------
# Openai API 调用
# -------------------------------

def deepseek_chat(message, model, stream, prompt):
    """
    调用 DeepSeek API 获取对话回复

    参数:
        message (str): 用户输入的消息
        model (str): 使用的模型标识
        stream (bool): 是否使用流式输出

    返回:
        str: AI 返回的回复
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": message},
            ],
            stream=stream
        )
    except Exception as e:
        print("调用 DeepSeek API 出错:", e)
        raise

    # 流式输出处理
    if stream:
        reasoning_content = ""  # 思维链内容
        content = ""  # 回复内容    
        for chunk in response: 
            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content: # 判断是否为思维链
                chunk_message = chunk.choices[0].delta.reasoning_content # 获取思维链
                print(chunk_message, end="", flush=True)  # 打印思维链
                if chunk_message:
                    reasoning_content += chunk_message  # 累加思维链
            else:
                chunk_message = chunk.choices[0].delta.content # 获取回复
                print(chunk_message, end="", flush=True)  # 打印回复
                if chunk_message: 
                    content += chunk_message  # 累加回复
                
        print("\n")
        return content.strip()  # 返回回复内容

        full_response = ""
        for chunk in response:
            chunk_message = chunk.choices[0].delta.content
            print(chunk_message, end='', flush=True)
            if chunk_message:
                # print(chunk_message, end='', flush=True)
                full_response += chunk_message
        print("\n")
        return full_response.strip()
    else:
        output = response.choices[0].message.content  # 获取回复内容
        print(output)  # 打印回复
        return output  # 返回回复内容
class DifyAPI:
    """Dify API 交互类"""
    def __init__(self, config):
        self.config = config
        self.DS_NOW_MOD = config.get('model1')  # 默认使用模型1
        self.api_key = "Bearer " + config.get('api_key')
        self.base_url = config.get('base_url')
        # self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    def chat(self, message, model=None, stream=True, prompt=None):
        """
        调用 Dify API 获取对话回复
        """
        # print("=== 简单文本对话 ===")
        response = self.run_dify_conversation(
            query=message,
            response_mode="blocking"
        )
        
        if "event" in response and response["event"] == "message":
            result = self.handle_blocking_response(response)
            print(f"🤖 AI回复: {result['answer']}")
            print(f"会话ID: {result['conversation_id']}")
            return result['answer']
        else:
            print(f"❌ 错误: {response.get('error', 'Unknown error')}")
            return "API返回错误，请稍后再试"

    def handle_blocking_response(self, response_data):
        """
        处理阻塞模式(blocking)的响应
        """
        if response_data.get("event") == "message":
            return {
                "success": True,
                "conversation_id": response_data.get("conversation_id"),
                "answer": response_data.get("answer", ""),
                "message_id": response_data.get("message_id"),
                "metadata": response_data.get("metadata", {}),
                "usage": response_data.get("usage", {}),
                "retriever_resources": response_data.get("retriever_resources", [])
            }
        else:
            return {
                "success": False,
                "error": f"Unexpected event type: {response_data.get('event')}",
                "raw_response": response_data
            }
    def run_dify_conversation(self,
        query=str,
        inputs={},
        conversation_id=None,
        files=[],
        auto_generate_name=True,
        response_mode="blocking"
    ):
        """
        执行Dify对话工作流API，严格遵循官方文档规范
        官方文档：https://docs.dify.ai/api/chat-messages
        
        :param query: 用户输入/提问内容
        :param inputs: App定义的变量值
        :param conversation_id: 会话ID（用于多轮对话）
        :param files: 文件列表（支持Vision能力）
        :param auto_generate_name: 是否自动生成标题
        :param response_mode: 响应模式（blocking/streaming）
        :return: API响应数据
        """
        # API端点
        # url = "http://121.37.67.153:8088/v1/chat-messages"
        url = self.base_url
        # 设置请求头
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }
        
        # 构建符合文档要求的请求体
        payload = {
            "inputs": inputs,
            "query": query,
            "response_mode": response_mode,
            "user": "api-user",  # 用户标识
            "conversation_id": conversation_id,
            "auto_generate_name": auto_generate_name
        }
        
        # 添加文件参数（如果提供）
        if files:
            payload["files"] = files
        
        try:
            # 发送请求
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()  # 检查HTTP错误
            
            # 解析响应
            if response_mode == "blocking":
                return response.json()
            else:
                # 流式响应需要特殊处理（此处只返回原始响应）
                return {"raw_stream": response.text}
                
        except requests.exceptions.RequestException as e:
            # 详细的错误处理
            error_info = {
                "error_type": "request_error",
                "message": str(e)
            }
            
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_info.update({
                        "status_code": e.response.status_code,
                        "error_code": error_data.get("code", "unknown"),
                        "api_message": error_data.get("message", "No error details")
                    })
                except:
                    error_info["response_text"] = e.response.text
                    
            return {"success": False, "error": error_info}
class CozeAPI:
    """Coze API 交互类"""
    def __init__(self, config):
        self.config = config
        self.DS_NOW_MOD = config.get('model1')  # 默认使用模型1
        self.bot_id = config.get('model1') # 在 Coze 中创建一个机器人实例，从网页链接中复制最后一个数字作为机器人的 ID 。
        self.user_id = "SiverWxBot" # 机器人用户标识
        self.api_key = config.get('api_key')
        self.base_url = COZE_CN_BASE_URL # 采用扣子官方定义api地址
        # self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)
        self.coze = Coze(auth=TokenAuth(token=self.api_key), base_url=self.base_url) # 实例化扣子api对象

    def chat(self, message, model=None, stream=True, prompt=None):
        """
        调用 Coze API 获取对话回复
        """
        # 调用 coze.chat.stream 方法来创建一个聊天。该 create 方法属于流式传输类型。
        # 聊天，并将返回一个聊天迭代器。开发人员应使用该迭代器进行迭代以获取……
        # 记录聊天事件并进行处理。
        chunk_message = ""
        try:
            for event in self.coze.chat.stream(
                bot_id=self.bot_id,
                user_id=self.user_id+str(time.time()),
                additional_messages=[
                    Message.build_user_question_text(message),
                ],
            ):
                if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                    # print(event.message.content, end="", flush=True)
                    chunk_message += event.message.content # 拼接流式回答
                    

                if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
                    # print()
                    print(f"token消耗:{event.chat.usage.token_count}")

            print(f"扣子回复：{chunk_message}")
            return chunk_message
        except Exception as e:
            print(level="ERROR", message=f"❌ 调用Coze接口错误: {e}")
            return "API返回错误，请稍后再试"

# -------------------------------
# 微信机器人逻辑
# -------------------------------

# 微信客户端对象，全局变量
wx = None


def init_wx_listeners():
    """
    初始化微信监听器，根据配置添加监听用户和群聊
    """
    global wx, AtMe
    if not wx:
        print("本次未获取客户端，正在初始化微信客户端...")
        wx = WeChat()

    AtMe = "@"+wx.nickname # 绑定AtMe
    print('启动wxautox监听器...')
    wx.StartListening() # 启动监听器
    # 添加管理员监听
    wx.AddListenChat(nickname=cmd, callback=message_handle_callback)
    print("添加管理员监听完成")
    # 添加个人用户监听
    for user in listen_list:
        wx.AddListenChat(nickname=user, callback=message_handle_callback)
    # 如果群机器人开关开启，则添加群聊监听
    if group_switch == "True":
        for user in group:
            wx.AddListenChat(nickname=user, callback=message_handle_callback)
        print("群组监听设置完成")
    # print(config.get('group', ""))
    print("监听器初始化完成")
def message_handle_callback(msg, chat):
    """消息处理回调"""
    text = datetime.now().strftime("%Y/%m/%d %H:%M:%S ") + f'类型：{msg.type} 属性：{msg.attr} 窗口：{chat.who} 发送人：{msg.sender_remark} - 消息：{msg.content}'
    print(text)
    if isinstance(msg, FriendMessage): # 好友群友的消息
        process_message(chat, msg)
    elif isinstance(msg, SystemMessage): # 系统的消息
        if group_welcome: # 群新人欢迎语开关
            send_group_welcome_msg(chat, msg) # 获取子窗口对象与消息对象送入处理

def wx_send_ai(chat, message):
    # 默认：回复 AI 生成的消息
    # chat.SendMsg("已接收，请耐心等待回答")
    try:
        reply = API_chat(message.content, DS_NOW_MOD, stream=True, prompt=prompt)
    except Exception:
        print(traceback.format_exc())
        reply = "API返回错误，请稍后再试"
            
    if len(reply) >= 2000:
        segments = split_long_text(reply)
        # 处理分段后的内容
        for index, segment in enumerate(segments, 1):
            # print(f"第 {index} 段内容（{len(segment)} 字符）: {segment}")
            reply_ = segment
            chat.SendMsg(reply_)
    else:
        chat.SendMsg(reply)
def find_new_group_friend(msg, flag):
    '''
    寻找新的群好友
    msg：系统消息
    flag：若是邀请的消息则填3，扫描二维码的消息则填1
    '''
    text = msg
    try:
        first_quote_content = text.split('"')[flag]
    except:
        first_quote_content = text.split('"')[1]
    # print("新人:", first_quote_content)  # 输出: Gary10
    return first_quote_content
def send_group_welcome_msg(chat, message):
    '''
    监听群组欢迎新人
    '''
    print(now_time()+f"{chat.who} 系统消息:", message.content)
    if "加入群聊" in message.content:
        new_friend = find_new_group_friend(message.content, 1) # 扫码加入
        print(f"{chat.who} 新群友:", new_friend)
        time.sleep(2) # 等待2秒微信刷新
        chat.SendMsg(msg=group_welcome_msg, at=new_friend)
    elif "加入了群聊" in message.content:
        new_friend = find_new_group_friend(message.content, 3) # 个人邀请
        print(f"{chat.who} 新群友:", new_friend)
        time.sleep(2) # 等待2秒微信刷新
        chat.SendMsg(msg=group_welcome_msg, at=new_friend)
    return
def process_message(chat, message):
    """
    处理收到的单条消息，并根据不同情况调用 DeepSeek API 或执行命令

    参数:
        chat: 消息所属的会话对象（包含 who 等信息）
        message: 消息对象（包含 type, sender, content 等信息）
    """
    global DS_NOW_MOD, group_welcome, group_welcome_msg
    # 只处理好友消息
    if message.attr != 'friend':
        return

    print(now_time()+f"\n{chat.who} 窗口 {message.sender} 说：{message.content}")
    # print(message.info) # 原始消息


    # 检查是否为需要监听的对象：在 listen_list 中，或为指定群聊且群开关开启
    is_monitored = chat.who in listen_list or (
        chat.who in group and group_switch == "True"
    ) or (
        chat.who == cmd)
    if not is_monitored:
        return

    # 如果用户询问“你是谁”，直接回复机器人名称
    if message.content == '你是谁' or re.sub(AtMe, "", message.content).strip() == '你是谁':
        chat.SendMsg('我是' + bot_name)
        return 


    # 群聊中：只有包含 @ 才回复
    if chat.who in group:
        if AtMe in message.content:
            # 去除@标识后获取消息内容
            content_without_at = re.sub(AtMe, "", message.content).strip()
            print(now_time()+f"群组 {chat.who} 消息：",content_without_at)
            try:
                reply = API_chat(content_without_at, DS_NOW_MOD, stream=True, prompt=prompt)
            except Exception:
                print(traceback.format_exc())
                reply = "请稍后再试"
            # 回复消息，并 @ 发送者
            chat.SendMsg(msg=reply, at=message.sender)
            return
        return

    # 命令处理：当消息来自指定命令账号时，执行相应的管理操作
    if chat.who == cmd:
        if "/添加用户" in message.content:
            try:
                user_to_add = re.sub("/添加用户", "", message.content).strip()
                add_user(user_to_add)
                init_wx_listeners()
                chat.SendMsg(message.content + ' 完成\n' + ", ".join(listen_list))
            except:
                user_to_add = re.sub("/添加用户", "", message.content).strip()
                remove_user(user_to_add)
                init_wx_listeners()
                chat.SendMsg(message.content + ' 失败\n请检查添加的用户是否为好友或者备注是否正确或者备注名 昵称中是否含有非法中文字符\n当前用户：\n'+", ".join(listen_list))
        elif "/删除用户" in message.content:
            user_to_remove = re.sub("/删除用户", "", message.content).strip()
            # if is_wxautox: # 如果是wxautox则删除监听窗口
            wx.RemoveListenChat(user_to_remove) # 删除监听窗口
            remove_user(user_to_remove)
            # init_wx_listeners()
            chat.SendMsg(message.content + ' 完成\n' + ", ".join(listen_list))
        elif "/当前用户" == message.content:
            chat.SendMsg(message.content + '\n' + ", ".join(listen_list))
        elif "/当前群" == message.content:
            chat.SendMsg(message.content + '\n'+ ", ".join(group))
        elif "/群机器人状态" == message.content:
            if group_switch == 'False':
                chat.SendMsg(message.content + '为关闭')
            else:
                chat.SendMsg(message.content + '为开启')
        elif "/添加群" in message.content:
            try:
                new_group = re.sub("/添加群", "", message.content).strip()
                # if is_wxautox: # 如果是wxautox则删除群组监听窗口
                # wx.RemoveListenChat(config.get('group')) # 删除群组监听窗口
                add_group(new_group)
                init_wx_listeners()
                chat.SendMsg(message.content + ' 完成\n' + ", ".join(group))
            except Exception:
                print(traceback.format_exc())
                remove_group(new_group)
                set_group_switch("False")
                init_wx_listeners()
                chat.SendMsg(message.content + ' 失败\n请重新配置群名称或者检查机器人号是否在群内\n当前群:\n' + ", ".join(group) + '\n当前群机器人状态:'+group_switch)
        elif "/删除群" in message.content:
            group_to_remove = re.sub("/删除群", "", message.content).strip()
            wx.RemoveListenChat(group_to_remove) # 删除监听窗口
            remove_group(group_to_remove) # 在配置中删除
            chat.SendMsg(message.content + ' 完成\n' + ", ".join(group))
        elif message.content == "/开启群机器人":
            try:
                set_group_switch("True")
                init_wx_listeners()
                chat.SendMsg(message.content + ' 完成\n' +'当前群：\n'+", ".join(group))
            except Exception as e:
                print(traceback.format_exc())
                set_group_switch("False")
                init_wx_listeners()
                chat.SendMsg(message.content + ' 失败\n请重新配置群名称或者检查机器人号是否在群或者群名中是否含有非法中文字符\n当前群:'+ ", ".join(group) +'\n当前群机器人状态:'+group_switch)
        elif message.content == "/关闭群机器人":
            set_group_switch("False")
            # if is_wxautox: # 如果是wxautox则删除群组监听窗口
            for user in group:
                wx.RemoveListenChat(user) # 删除群组监听窗口
            # init_wx_listeners()
            chat.SendMsg(message.content + ' 完成\n' +'当前群：\n' + ", ".join(group))
        elif message.content == "/开启群机器人欢迎语":
            group_welcome = True
            chat.SendMsg(message.content + ' 完成\n' +'当前群：\n' + ", ".join(group))
        elif message.content == "/关闭群机器人欢迎语":
            group_welcome = False
            chat.SendMsg(message.content + ' 完成\n' +'当前群：\n' + ", ".join(group))
        elif message.content == "/群机器人欢迎语状态":
            if group_welcome:
                chat.SendMsg("/群机器人欢迎语状态 为开启\n" +'当前群：\n' + ", ".join(group))
            else:
                chat.SendMsg("/群机器人欢迎语状态 为关闭\n" +'当前群：\n' + ", ".join(group))
        elif message.content == "/当前群机器人欢迎语":
            chat.SendMsg(message.content + '\n' +group_welcome_msg)
        elif "/更改群机器人欢迎语为" in message.content:
            new_welcome = re.sub("/更改群机器人欢迎语为", "", message.content).strip()
            group_welcome_msg = new_welcome
            chat.SendMsg('群机器人欢迎语已更新\n' + group_welcome_msg)
        elif message.content == "/当前模型":
            chat.SendMsg(message.content + " " + DS_NOW_MOD)
        elif message.content == "/切换模型1": # 1
            # global DS_NOW_MOD
            DS_NOW_MOD = model1
            chat.SendMsg(message.content + ' 完成\n当前模型:' + DS_NOW_MOD)
        elif message.content == "/切换模型2": # 2
            # global DS_NOW_MOD
            DS_NOW_MOD = model2
            chat.SendMsg(message.content + ' 完成\n当前模型:' + DS_NOW_MOD)
        elif message.content == "/切换模型3": # 3
            # global DS_NOW_MOD
            DS_NOW_MOD = model3
            chat.SendMsg(message.content + ' 完成\n当前模型:' + DS_NOW_MOD)
        elif message.content == "/切换模型4": # 4
            # global DS_NOW_MOD
            DS_NOW_MOD = model4
            chat.SendMsg(message.content + ' 完成\n当前模型:' + DS_NOW_MOD)
        elif message.content == "/当前AI设定":
            chat.SendMsg('当前AI设定：\n' + config['prompt'])
        elif "/更改AI设定为" in message.content or "/更改ai设定为" in message.content:
            if "AI设定" in message.content:
                new_prompt = re.sub("/更改AI设定为", "", message.content).strip()
            else:
                new_prompt = re.sub("/更改ai设定为", "", message.content).strip()
            config['prompt'] = new_prompt
            save_config()
            refresh_config()
            chat.SendMsg('AI设定已更新\n' + config['prompt'])
        elif message.content == "/更新配置":
            refresh_config()
            init_wx_listeners()
            chat.SendMsg(message.content + ' 完成\n')
        elif message.content == "/当前版本":
            global ver
            chat.SendMsg(message.content + 'wxbot_' + ver + '\n' + ver_log + '\n作者:https://siver.top')
        elif message.content == "/指令" or message.content == "指令":
            commands = (
                '指令列表[发送中括号里内容]：\n'
                '[/当前用户] (返回当前监听用户列表)\n'
                '[/添加用户***] （将用户***添加进监听列表）\n'
                '[/删除用户***]\n'
                '[/当前群]\n'
                '[/添加群***] \n'
                '[/删除群***] \n'
                '[/开启群机器人]\n'
                '[/关闭群机器人]\n'
                '[/群机器人状态]\n'
                '[/开启群机器人欢迎语]\n'
                '[/关闭群机器人欢迎语]\n'
                '[/群机器人欢迎语状态]\n'
                '[/当前群机器人欢迎语]\n'
                '[/更改群机器人欢迎语为***]\n'
                '[/当前模型] （返回当前模型）\n'
                '[/切换模型1] （切换回复模型为配置中的 model1）\n'
                '[/切换模型2]\n'
                '[/切换模型3]\n'
                '[/切换模型4]\n'
                '[/当前AI设定] （返回当前AI设定）\n'
                '[/更改AI设定为***] （更改AI设定，***为AI设定）\n'
                '[/更新配置] （若在程序运行时修改过配置，请发送此指令以更新配置）\n'
                '[/当前版本] (返回当前版本)\n'
                '作者:https://siver.top  若有非法传播请告知'
            )
            chat.SendMsg(commands)
        else:
            # 默认：回复 AI 生成的消息
            wx_send_ai(chat, message)
        return

    # 普通好友消息：先提示已接收，再调用 AI 接口获取回复
    wx_send_ai(chat, message)

run_flag = True  # 运行标记，用于控制程序退出
def main():
    # 输出版本信息
    global ver, run_flag
    print(f"wxbot\n版本: wxbot_{ver}\n作者: https://siver.top")
    
    # 加载配置并更新全局变量
    refresh_config()

    try:
        # 初始化微信监听器
        init_wx_listeners()
    except Exception as e:
        print(traceback.format_exc())
        print("初始化微信监听器失败，请检查微信是否启动登录正确")
        run_flag = False

    wait_time = 100  
    check_interval = 10  # 每10次循环检查一次进程状态
    check_counter = 0
    print(now_time()+'siver_wxbot初始化完成，开始监听消息(作者:https://siver.top)')
    # wx.SendMsg('siver_wxbot初始化完成', who=cmd)
    # 主循环：保持运行
    while run_flag:
        time.sleep(wait_time)  # 等待1秒
    print(now_time()+'siver_wxbot已停止运行')

def start_bot():
    """启动机器人"""
    main()  # 执行主函数
def stop_bot():
    """停止机器人"""
    wx.StopListening() # 停止wxauto监听器
    run_flag = False  # 停止主循环
    print(now_time()+'siver_wxbot已停止运行')

if __name__ == "__main__":
    main()  # 执行主函数

