# Siver_wxbot

# Siver微信机器人

使用wxauto实现  作者仓库:https://github.com/cluic/wxauto

最新源码在preview，config_updata.py为siver_wxbot配置查看修改器源码

**config.json文件说明:**

config.json可通过config_updata.py或者打包好的siver_wxbot配置查看修改器.exe编辑

lis列表为监听列表，内容填空([]里面不要有东西)，启动程序后可通过发送消息自动添加

api与url填写你要调用的ai大模型接口url与api即可（默认硅基流动接口，调用的接口需支持openai的python库）。

AtMe填写在群中@你的机器人号出现的内容，建议复制粘贴过去，微信@的末尾有一个特殊符号

cmd字段值填写你的机器人号给大号的备注名，这样就将你的这个大号设置为管理员账号

model1与model2填写你要调用的模型名称，由你的接口服务商提供

group为监听的群组名称，首次配置暂时不用填写可通过发送消息自动修改

group_switch为群机器人开关

bot_name为你向机器人询问你是谁时回复的特定关键词，详情参照1.2版本更新内容

操作方式，首次配置完成后，启动程序之后，使用你的管理员账号向机器人小号发送 “指令” 二字，即可收到机器人号向你回复的消息指令，接下来根据消息指令的提示自由设置即可

