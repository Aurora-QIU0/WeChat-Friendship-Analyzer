<p align="center"><a href="../README.md">← 返回项目首页</a></p>

<h1 align="center">🐟 小鱼 Xiaoyu</h1>
<p align="center"><strong>有来有回，也懂得留白。</strong><br><sub>中文语音伙伴 · 人格资料 V1.1</sub></p>

<p align="center"><a href="character/system_prompt.md">复制提示词</a> · <a href="character/conversation_style.md">交流风格</a> · <a href="examples/daily_chat.md">看看怎么聊</a> · <a href="memory/memory_rules.md">记忆边界</a></p>

---

独立 AI 人格资料：短句、自然接话、适当幽默，兼顾情绪倾听和专业技术帮助。用于已有的小智语音设备，不需要修改 GPIO 或重新烧录固件。

## 从分析结果到人物资料

这是项目流程的最后一段：先用 WeFlow 提取，再校验并分析，最后到这里整合。完整流程见 [工作流](../docs/workflow.md)。

将分析结果中可复用的交流方式整理为风格规则，把人格、原创示例和用户明确确认的背景组合成提示词。删除不必要的第三方身份与私人细节，分别保存通用人格和私人记忆，然后按下列步骤接入小智。原始聊天 ZIP 不作为提示词上传。

## 快速使用

1. 打开 [三版系统提示词](character/system_prompt.md)，任选一版，仅复制代码框中的正文。完整版已包含 V1.1 交流风格，不要重复粘贴补充文件。
2. 登录 [小智官方控制台](https://xiaozhi.me/console/agents)，备份当前角色介绍，再将正文粘贴到对应智能体的角色介绍中并保存。字段限制以实际页面为准。
3. 按控制台提示重启设备或开启新对话，测试日常交流、疲惫时收尾和技术排查。云端角色名称与设备唤醒词独立；本仓库不修改设备唤醒词。

## 内容导航

| 内容 | 入口 |
|---|---|
| 人物资料与性格 | [人物资料](character/character_profile.md) · [性格](character/personality_traits.md) |
| 表达方式与互动节奏 | [风格说明](character/conversation_style.md) · [风格补充](character/style_prompt_addendum_v1_1.txt) |
| 情绪回应 | [情绪行为](character/emotion_behavior.md) |
| 原创示例 | [日常](examples/daily_chat.md) · [情绪支持](examples/emotional_support.md) · [幽默](examples/humorous_chat.md) · [技术](examples/technical_assistant.md) |
| 记忆结构 | [Schema](memory/memory_schema.json) · [用户空模板](memory/user_profile.example.json) · [记忆空模板](memory/memory_seed.example.json) |
| 接入边界 | [记忆规则](memory/memory_rules.md) · [配置索引](config/xiaoyu_config.json) |

## 先听听这种节奏

> **用户：** 程序终于能跑了。<br>
> **小鱼：** 这次总算听指挥了。是卡了很久的那一段吗？

原创示例用于展示语气，不是固定台词，也不是真实人物的聊天摘录。

## 三种背景能力

- 固定背景：将必要且获授权的信息放入角色介绍；后续更新需要修改配置。
- 官方记忆：以当前账户实际提供的功能为准；不能只凭模型口头确认判断保存成功。
- 自定义结构化记忆：本目录提供格式和接口设计，没有实现后台，也不保证官方平台可直接导入这些 JSON。

空模板用来复制到本地私人目录后填写。不要提交真实用户画像、私人记忆、聊天档案、密钥、部署备份或控制台截图。配置索引是项目格式，不是官方导入文件。公开示例均为原创，不是聊天摘录；人格不冒充现实人物、不虚构对方感情。
