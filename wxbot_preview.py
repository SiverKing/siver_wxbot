#!/usr/bin/env python3
# 作者：https://siver.top
# 版本：1.7
ver = "1.7"         # 当前版本
import time
import json
import re
import traceback
from wxauto import WeChat
from openai import OpenAI

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
cmd = ""            # 命令接收账号（管理员）
group = ""          # 群聊ID
model1 = ""         # 模型1标识
model2 = ""         # 模型2标识
model3 = ""         # 模型3标识
model4 = ""         # 模型4标识
# 当前使用的模型和 API 客户端
DS_NOW_MOD = ""
client = None

# DS API 模型常量（可根据需要更换）
DS_R1 = "deepseek-reasoner"
DS_V3 = "deepseek-chat"
siliconflow_DS_R1 = "deepseek-ai/DeepSeek-R1"
siliconflow_DS_V3 = "deepseek-ai/DeepSeek-V3"


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
    global listen_list, api_key, base_url, AtMe, cmd, group, model1, model2, model3, model4, DS_NOW_MOD, client
    listen_list = config.get('listen_list', [])
    api_key = config.get('api_key', "")
    base_url = config.get('base_url', "")
    AtMe = config.get('AtMe', "")
    cmd = config.get('cmd', "")
    group = config.get('group', "")
    model1 = config.get('model1', "")
    model2 = config.get('model2', "")
    model3 = config.get('model3', "")
    model4 = config.get('model4', "")
    # 默认使用模型1
    DS_NOW_MOD = model1
    # 初始化 OpenAI 客户端
    client = OpenAI(api_key=api_key, base_url=base_url)
    print("全局配置更新完成")


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
        with open(CONFIG_FILE, 'w', encoding='utf-8') as file:
            json.dump(config, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print("保存配置文件失败:", e)


def add_user(name):
    """
    添加用户至监听列表，并更新配置
    """
    if name not in config.get('listen_list', []):
        config['listen_list'].append(name)
        save_config()
        refresh_config()
        print("添加后的 Listen List:", config['listen_list'])
    else:
        print(f"用户 {name} 已在监听列表中")


def remove_user(name):
    """
    从监听列表中删除指定用户，并更新配置
    """
    if name in config.get('listen_list', []):
        config['listen_list'].remove(name)
        save_config()
        refresh_config()
        print("删除后的 Listen List:", config['listen_list'])
    else:
        print(f"用户 {name} 不在监听列表中")


def set_group(new_group):
    """
    更改监听的群聊ID，并更新配置
    """
    config['group'] = new_group
    save_config()
    refresh_config()
    print("群组已更改为", config['group'])


def set_group_switch(switch_value):
    """
    设置是否启用群机器人（"True" 或 "False"），并更新配置
    """
    config['group_switch'] = switch_value
    save_config()
    refresh_config()
    print("群开关设置为", config['group_switch'])

def split_long_text(text, chunk_size=2000):
    """将长文本分割为指定长度的段落"""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

# -------------------------------
# DeepSeek API 调用
# -------------------------------

def deepseek_chat(message, model, stream):
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
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": message},
            ],
            stream=stream
        )
    except Exception as e:
        print("调用 DeepSeek API 出错:", e)
        raise

    # 流式输出处理
    if stream:
        reasoning_content = ""
        content = ""
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content: # 判断是否为思维链
                chunk_message = chunk.choices[0].delta.reasoning_content # 获取思维链
                print(chunk_message, end="", flush=True)
                if chunk_message:
                    reasoning_content += chunk_message
            else:
                chunk_message = chunk.choices[0].delta.content # 获取回复
                print(chunk_message, end="", flush=True)
                if chunk_message:
                    content += chunk_message
                
        print("\n")
        return content.strip()

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
        output = response.choices[0].message.content
        print(output)
        return output


# -------------------------------
# 微信机器人逻辑
# -------------------------------

# 微信客户端对象，全局变量
wx = None


def init_wx_listeners():
    """
    初始化微信监听器，根据配置添加监听用户和群聊
    """
    global wx
    wx = WeChat()
    # 添加管理员监听
    wx.AddListenChat(who=cmd)
    print("添加管理员监听完成")
    # 添加个人用户监听
    for user in listen_list:
        wx.AddListenChat(who=user)
    # 如果群机器人开关开启，则添加群聊监听
    if config.get('group_switch', "False") == "True":
        wx.AddListenChat(who=config.get('group', ""))
        print("群组监听设置完成")
    print("监听器初始化完成")


def process_message(chat, message):
    """
    处理收到的单条消息，并根据不同情况调用 DeepSeek API 或执行命令

    参数:
        chat: 消息所属的会话对象（包含 who 等信息）
        message: 消息对象（包含 type, sender, content 等信息）
    """
    global DS_NOW_MOD
    # 只处理好友消息
    if message.type != 'friend':
        return

    print(f"\n{message.sender} 问：{message.content}")

    # 检查是否为需要监听的对象：在 listen_list 中，或为指定群聊且群开关开启
    is_monitored = chat.who in listen_list or (
        chat.who == config.get('group', "") and config.get('group_switch') == "True"
    ) or (
        chat.who == cmd)
    if not is_monitored:
        return

    # 如果用户询问“你是谁”，直接回复机器人名称
    if message.content == '你是谁' or re.sub(AtMe, "", message.content) == '你是谁':
        chat.SendMsg('我是' + config.get('bot_name', 'wxbot'))
        return

    # 群聊中：只有包含 @ 才回复
    if chat.who == config.get('group', ""):
        if AtMe in message.content:
            # 去除@标识后获取消息内容
            content_without_at = re.sub(AtMe, "", message.content)
            try:
                reply = deepseek_chat(content_without_at, DS_NOW_MOD, stream=True)
            except Exception:
                print(traceback.format_exc())
                reply = "API返回错误，请稍后再试"
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
                chat.SendMsg(message.content + ' 完成\n' + "  ".join(config.get('listen_list', [])))
            except:
                user_to_add = re.sub("/添加用户", "", message.content).strip()
                remove_user(user_to_add)
                init_wx_listeners()
                chat.SendMsg(message.content + ' 失败\n请检查添加的用户是否为好友或者备注是否正确\n当前用户：\n'+"  ".join(config.get('listen_list', [])))
        elif "/删除用户" in message.content:
            user_to_remove = re.sub("/删除用户", "", message.content).strip()
            remove_user(user_to_remove)
            init_wx_listeners()
            chat.SendMsg(message.content + ' 完成\n' + "  ".join(config.get('listen_list', [])))
        elif "/当前用户" == message.content:
            chat.SendMsg(message.content + '\n' + "  ".join(config.get('listen_list', [])))
        elif "/当前群" == message.content:
            chat.SendMsg(message.content + ' '+ config.get('group'))
        elif "/群机器人状态" == message.content:
            if config.get('group_switch') == 'False':
                chat.SendMsg(message.content + '为关闭')
            else:
                chat.SendMsg(message.content + '为开启')
        elif "/更改群为" in message.content:
            try:
                new_group = re.sub("/更改群为", "", message.content).strip()
                set_group(new_group)
                init_wx_listeners()
                chat.SendMsg(message.content + ' 完成\n')
            except:
                set_group('(暂无监听群)')
                set_group_switch("False")
                init_wx_listeners()
                chat.SendMsg(message.content + ' 失败\n请重新配置群名称或者检查机器人号是否在群内\n当前配置群名称:'+config.get('group')+'\n当前群机器人状态:'+config.get('group_switch'))
        elif message.content == "/开启群机器人":
            try:
                set_group_switch("True")
                init_wx_listeners()
                chat.SendMsg(message.content + ' 完成\n' +'当前群：'+config.get('group'))
            except:
                set_group_switch("False")
                init_wx_listeners()
                chat.SendMsg(message.content + ' 失败\n请重新配置群名称或者检查机器人号是否在群内\n当前配置群名称:'+config.get('group')+'\n当前群机器人状态:'+config.get('group_switch'))
        elif message.content == "/关闭群机器人":
            set_group_switch("False")
            init_wx_listeners()
            chat.SendMsg(message.content + ' 完成\n' +'当前群：'+config.get('group'))
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
        elif message.content == "/更新配置":
            refresh_config()
            init_wx_listeners()
            chat.SendMsg(message.content + ' 完成\n')
        elif message.content == "/当前版本":
            global ver
            chat.SendMsg(message.content + 'wxbot_' +ver + '\n作者:https://siver.top')
        elif message.content == "/指令" or message.content == "指令":
            commands = (
                '指令列表（发送引号内内容）：\n'
                '"/当前用户" (返回当前监听用户列表)\n'
                '"/添加用户***" （将用户***添加进监听列表）\n'
                '"/删除用户***"\n'
                '"/当前群"\n'
                '"/更改群为***" （更改监听的群，只能监听一个群）\n'
                '"/开启群机器人"\n'
                '"/关闭群机器人"\n'
                '"/群机器人状态"\n'
                '"/当前模型" （返回当前模型）\n'
                '"/切换模型1" （切换回复模型为配置中的 model1）\n'
                '"/切换模型2" （切换回复模型为配置中的 model2）\n'
                '"/切换模型3" （切换回复模型为配置中的 model3）\n'
                '"/切换模型4" （切换回复模型为配置中的 model4）\n'
                '"/更新配置" （若在程序运行时手动修改过 config.json，请发送此指令以更新配置）\n'
                '"/当前版本" (返回当前版本)\n'
                '作者:https://siver.top  若有非法传播请告知'
            )
            chat.SendMsg(commands)
        else:
            # 默认：回复 AI 生成的消息
            chat.SendMsg("已接收，请耐心等待回答")
            try:
                reply = deepseek_chat(message.content, DS_NOW_MOD, stream=True)
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
        return

    # 普通好友消息：先提示已接收，再调用 AI 接口获取回复
    chat.SendMsg("已接收，请耐心等待回答")
    try:
        reply = deepseek_chat(message.content, DS_NOW_MOD, stream=True)
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


def main():
    # 输出版本信息
    # ver = "1.3"
    global ver
    print(f"wxbot\n版本: wxbot_{ver}\n作者: https://siver.top")
    
    # 加载配置并更新全局变量
    refresh_config()
    
    set_group_switch("False") # 首次启动关闭群机器人
    print("首次启动群机器人设置为 关闭")

    # 初始化微信监听器
    init_wx_listeners()
    
    wait_time = 1  # 每1秒检查一次新消息
    print('siver_wxbot初始化完成，开始监听消息(作者:https://siver.top)')
    # 主循环：持续监听并处理消息
    while True:
        try:
            messages_dict = wx.GetListenMessage()
            # 遍历所有监听的会话
            for chat in messages_dict:
                for message in messages_dict.get(chat, []):
                    process_message(chat, message)
        except Exception as e:
            print("处理消息时发生异常:", e)
            print(traceback.format_exc())
        time.sleep(wait_time)



main()