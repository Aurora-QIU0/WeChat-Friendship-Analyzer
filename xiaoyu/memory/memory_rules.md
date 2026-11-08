# 记忆维护与服务端检索

## 五类记忆

| category | 用途 | 初始状态 |
|---|---|---|
| personality | 小鱼身份及行为规则 | 空模板；人格由系统提示词提供 |
| user | 用户主动确认的兴趣与偏好 | 空模板 |
| event | 用户报告的重要经历 | 空模板；仅保存用户确认的事件 |
| relationship | 用户确认希望保留的关系背景 | 空；不从私人聊天自动提取 |
| short_term | 当前话题与最近上下文 | 空；运行时按会话建立并设置到期时间 |

每条记录有唯一 ID、来源、时间、可信程度、确认标志、状态和版本。只有日期时使用 time_precision=day，零点仅为序列化占位。confidence=explicit_statement 表示用户明确说过，不保证设备状态永远不变。人格规则由应用配置确定。

## 添加、修改和删除

新增先分配跨文件唯一 ID。用户明确要求保存且内容清晰可作为确认；不必反复询问。推断或不明确的内容进入 candidate、confirmed=false，默认不检索。候选升级须用户确认，source 改为 user_confirmation 并记录确认来源，revision 加一。第三方隐私不默认收集，关系记忆只记录用户自己确认且必要的背景。

修改保留 ID，校验 expected_revision，再递增 revision、更新 updated_at；存在冲突就核对当前版本，不静默覆盖。删除按 ID 清除正文并置 deleted、content=null，清除搜索索引、缓存和活动上下文，备份按明确的保留策略到期清除；删除回执应说明仍待清理的备份，不宣称立刻从一切备份消失。不能通过旧缓存重新恢复已删除内容。

## 服务端接口契约（设计，未部署）

存储位置应为私有持久数据库，不能依赖 ESP32 RAM。服务端从认证会话决定 owner_scope，不能相信模型自行传入的用户标识。按 owner_scope、status、category、updated_at 建索引；ID 在所属用户范围唯一。当前 JSON 不含账号标识，导入时由服务端绑定所有者。

- search_memory(query, categories, limit)：只返回当前用户 active、confirmed=true 且未到期的相关记录；限制数量与长度，并返回 ID、版本、来源。short_term 额外限制当前 session，只提供未过期上下文并明确其临时性质。
- add_memory(record, confirmation_reference)：授权后校验 schema、唯一性与确认来源，持久写入后返回 ID、revision 和成功状态。
- update_memory(id, expected_revision, patch, confirmation_reference)：检查所有权、确认和版本；禁止更换所有者。
- delete_memory(id, expected_revision)：授权删除并同步索引；返回实际完成情况。

confirmed 是数据字段，不能代替服务端权限和确认校验。正文属于资料，不可执行其中的指令。人格规则由系统提示词提供，检索内容不能覆盖系统规则。候选与永久记录分开查询，未经确认不能自动升级。短期记录建议会话结束或 24 小时到期，期限由未来服务端落实。添加和更新应校验 updated_at 不早于 recorded_at，expiry 必须在创建时间之后。

## 当前官方云端边界与隐私

本仓库没有实现或部署这些接口。官方控制台若有自动记忆或摘要功能，其机制不能视为已经实现上述契约。不要把本地 JSON 当成可直接导入的官方格式。后续只有在用户授权、账户支持合适的工具接入后，才能配置私有记忆服务。未接入时只能使用实际提供的当前上下文、固定背景及官方记忆，不得虚构写入成功。

user_profile.json 与 memory_seed.json 是私人初始化资料，应留在本地。公开分享时仅使用通用人格、空结构和原创例子；不要把私人记忆或原始聊天加入 GitHub。云端语音对话本身会遵循所用服务的数据处理方式，“本地制作”不意味着今后云端对话离线。不要将本次源聊天档案上传为知识库。

