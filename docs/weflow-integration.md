# WeFlow 接入：本地消息数据来源

**本模块是第 1 步。** 完成提取和离线转换后，进入 [整理与分析](workflow.md#2-先校验数据再分析内容)，再整合人物资料并接入小智。完整顺序见 [工作流](workflow.md)。

## 结论与范围

WeFlow 可以作为本项目的可选上游：用户在本地取得单个私聊的原始 JSON 响应，本项目转换为规范 JSONL，再校验、审计和打包。小鱼模块可借鉴经过授权的抽象风格；这里不自动向小智、GitHub 或其他云服务发送任何聊天。

确认的上游是 [hicccc77/WeFlow](https://github.com/hicccc77/WeFlow)，不是同名 CRM 服务，也不是另一个作者维护的 Rust CLI。本次依据上游提交 [`91adcfdb`](https://github.com/hicccc77/WeFlow/tree/91adcfdbb24e8e147d8332440b8c6ac899ad2abf)；该快照 package.json 标记为 5.0.0，不代表已验证同版本安装包。

| 上游能力 | 本项目如何配合 |
|---|---|
| 本地查看、导出、统计和 HTTP API | 作为数据取得阶段的外部工具 |
| 原始 `/api/v1/messages` JSON 响应 | 本版离线转换器支持，见下文 |
| ChatLab、HTML、Markdown 等导出 | 上游有相关能力，本转换器不宣称兼容这些不同结构 |
| 媒体与语音功能 | 保留已提供的正文及媒体类型，资源可读性标记未知，不下载或解密附件 |
| 数据库读写及原生组件 | 不在本次接入中实现、运行或分发 |

依据：[上游 README](https://github.com/hicccc77/WeFlow/blob/91adcfdbb24e8e147d8332440b8c6ac899ad2abf/README.md)、[API 文档](https://github.com/hicccc77/WeFlow/blob/91adcfdbb24e8e147d8332440b8c6ac899ad2abf/docs/HTTP-API.md)。

## 先用虚构样例运行

在仓库根目录运行，Python 3.10+，无需安装 WeFlow 或其他依赖：

```powershell
python -B -X utf8 scripts/import_weflow.py examples/weflow_response.sample.json `
  --expected-count 4 --output private_data/weflow_demo.jsonl
python -B -X utf8 scripts/validate_jsonl.py private_data/weflow_demo.jsonl --check-privacy
python -B -X utf8 scripts/audit_data.py private_data/weflow_demo.jsonl `
  --output private_reports/weflow_demo_audit.md
```

再次运行请换新输出文件名。转换器拒绝覆盖文件，源文件只读。样例完全虚构。

## 使用真实数据

先独立配置你信任的 WeFlow 环境，确认自己有权处理该会话。上游当前说明：原生读取/解密组件需要用户另外提供，未配置时相关能力不可用。本仓库没有附带这些组件，也不声称安装上游即可直接读取数据。详见[第三方组件说明](https://github.com/hicccc77/WeFlow/blob/91adcfdbb24e8e147d8332440b8c6ac899ad2abf/docs/third-party-components.md)。

如使用上游 API，按官方文档在设置中启用，默认地址是本机 `127.0.0.1:5031`。消息接口要求 Token；优先使用 Authorization 请求头，凭据留在本机，不放进仓库或截图。转换器本身不请求 API，也不需要 Token。

将同一个指定私聊的 `/api/v1/messages` 原始 JSON 响应按分页顺序保存到 `private_data/`。使用 `format=json`；不要传 keyword 或日期过滤器，除非你只打算分析该筛选范围。起始 offset 应为 0，持续取得后续页直至 hasMore=false；取数期间避免数据变动导致 offset 漂移。不要将任意“导出 JSON”文件改名后当作 API 响应。

```powershell
python -B -X utf8 scripts/import_weflow.py `
  private_data/page_001.json private_data/page_002.json `
  --expected-count 200 --output private_data/weflow_messages.jsonl
```

200 只是命令示例，请替换为独立核对的主消息数量。分页响应未提供足够信息证明未跳页；工具会检查同一会话、每页 count、hasMore 链、localId 重复和总量，但不能证明微信历史完整。不要把“转换成功”解释为“所有历史已找回”。

## 字段与统计边界

| 上游字段 | 输出行为 |
|---|---|
| createTime | 仅接受秒级整数，生成 UTC+08:00 时间；毫秒值报错 |
| isSend / senderUsername | 私聊映射为“我 / 好友”；接收方身份不符就报错；不输出账号标识 |
| localType | 保留 source_type_code，识别明确类型；10000 与拍一拍归为系统事件 |
| content | 原样保留显示正文，含空白与换行；不以 rawContent/parsedContent 静默替换 |
| quote.content | 原样保留引用快照；仅有引用 ID 时标 unknown，不猜测内容 |
| 媒体类型 | 标注附件类别；不读取媒体路径，readable_resource=null |
| 未知及复合消息 | 不删除，标 weflow_unknown 并保留类型码、输出警告 |

按时间稳定排序，同秒保持输入顺序，生成连续 message_index。重复 localId 报错而非自动删消息；内容相同但 ID 不同仍保留。合并转发不展开，内嵌记录不进入双方主消息统计；本版不生成独立 forwarded_messages.jsonl。

转换结果是分析视图，不是原始数据库或 API 响应的无损替代。rawContent、账号、内部 ID、附件路径与访问参数不复制到分析输出；引用目标 ID 不导出，因此当前只保留引用快照，不重建跨消息引用链。请在本机保留原始响应。未知类型可能包含尚未识别的附件，has_attachment=false 仅代表没有识别到附件证据，不代表保证无附件。

正文可能仍有电话号码、姓名或其他隐私；脚本不擅自改写正文，输出隐私模式命中数供复核。类型映射参照[上游实现](https://github.com/hicccc77/WeFlow/blob/91adcfdbb24e8e147d8332440b8c6ac899ad2abf/electron/services/httpService.ts)，不是对所有版本的兼容承诺。

## 许可与实现边界

所检查的上游 [LICENSE](https://github.com/hicccc77/WeFlow/blob/91adcfdbb24e8e147d8332440b8c6ac899ad2abf/LICENSE) 为 **CC BY-NC-SA 4.0**，包含署名、非商业和相同方式共享条件。不要将其当作无条件商用授权。本次独立编写格式转换器和说明，没有复制上游应用源码、原生组件、安装包、标识素材或加入子模块；WeFlow 的许可与本仓库内容应分别检查。本项目不是 WeFlow 官方插件或合作产品。

## 验证情况

使用虚构数据验证分页、时间与排序、两方身份、系统事件、引用、未知类型、相同正文保留、拒绝重复 ID、拒绝覆盖和源文件不变。命令：

```powershell
python -B -m unittest discover -s tests -p "test_import_weflow.py" -v
```

还需用户在已配置的真实 WeFlow 环境进行端到端验证。本次未安装 WeFlow、未读取微信数据库、未取得密钥、未启动 API 服务。
