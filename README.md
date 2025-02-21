# Siver微信机器人

[效果展示截图](./img.md)   
使用`wxauto`实现 | 作者仓库: [cluic/wxauto](https://github.com/cluic/wxauto)  
最新源码在`wxbot_preview.py`，`config_update.py`为配置工具源码.

---

## 🛠 首次配置

1. 运行 **`siver_wxbot配置查看修改器.exe`**
2. 若提示无配置文件，按指引创建新配置
3. **必填字段**（按提示填写）：
   - `api_key` - 调用API的密钥
   - `base_url` - 大模型接口地址
   - `AtMe` - 群聊中@机器人的标识符（需包含微信特殊符号）
   - `cmd` - 机器人给管理员的备注名（用于权限识别）
   - `bot_name` - 机器人身份标识词
   - `model1` ~ `model4` - 至少填写1个模型名称（最多4个）

4.剩余字段不修改，可通过消息指令来配置

---

## 🎮 操作指南

1. 启动主程序 `wxbot`
2. **用管理员账号**向机器人发送 `指令` 二字
3. 接收并查看机器人回复的操作指引
4. 通过指令交互完成以下操作：
   - 添加/删除监听对象
   - 配置群组机器人开关
   - 修改模型参数等

---

## ⚙ config.json 配置详解

### 📂 配置文件路径
通过 `config_update.py` 或 **配置查看修改器.exe** 编辑

---

### 🔑 主要字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `listen_list` | 列表 | 监听对象列表，启动后可通过消息自动添加（初始为空列表 `[]`） |
| `api_key` | 字符串 | 大模型API调用密钥 |
| `base_url` | 字符串 | 接口地址（默认硅基流动API） |
| `AtMe` | 字符串 | **需包含微信@的特殊后缀**，建议直接复制微信@内容 |
| `cmd` | 字符串 | 机器人对管理员的备注名（权限绑定标识） |
| `group` | 字符串 | 监听群组列表，可通过消息指令动态更新 |
| `group_switch` | 字符串 | 全局群聊机器人开关（`True`/`False`） |

---

### 🤖 模型配置
```json
"model1": "模型名称",  // 必填（至少1个）
"model2": "可选模型",  // 最多配置4个
"model3": "可选模型",
"model4": "可选模型"
```
*注：模型名称由API服务商提供*

---

### ⚡ 自动更新功能
- **监听列表(lis)** 和 **群组列表(group)** 支持通过消息指令动态修改
- 无需手动编辑配置文件即可增删监听对象/群组

---

## 📌 注意事项
1. 使用**微信官方客户端**（不要用WeChatUWP等第三方客户端）
2. 确保机器人账号已登录且窗口保持前台运行
3. `AtMe`字段必须包含微信@的特殊符号（建议直接复制微信@内容）
