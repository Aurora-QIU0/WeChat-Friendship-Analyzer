# WeChat Friendship Analyzer

微信好友会话的本地数据整理与分析工作流。本项目提供数据审计、JSONL 校验、字段整理、ZIP 交付和关系分析提示词。示例对话为虚构。

## 快速开始

在项目根目录运行以下命令。需要 Python 3.10 或更高版本，脚本使用标准库。

```powershell
python -B -X utf8 scripts/validate_jsonl.py examples/sample_messages.jsonl --check-privacy
python -B -X utf8 scripts/audit_data.py examples/sample_messages.jsonl --output private_reports/demo_audit.md
python -B -X utf8 scripts/anonymize_data.py examples/sample_messages.jsonl --alias "示例用户A=user_a" --alias "示例用户B=user_b" --output private_data/demo_checked.jsonl
python -B -X utf8 scripts/package_data.py private_data/demo_checked.jsonl --document docs/data-format.md --output personal_exports/demo.zip
```

脚本输入为已经合法取得的结构化 JSONL。输出命令使用新路径，重复执行时请为产物换一个文件名。打包脚本接收按时间排序的多个主会话文件，可用 `--forwarded` 指定独立的转发内嵌记录，用 `--document` 附带 Markdown 说明。脚本输出每个输入文件和 ZIP 的 SHA-256。

| 入口 | 用途 |
|---|---|
| [数据工作流](docs/workflow.md) | 从授权可读导出到交付 |
| [数据格式](docs/data-format.md) | 字段、顺序与统计边界 |
| [隐私约定](docs/privacy.md) | 本地目录、隐私检查和分享前核对 |
| [分析方法](docs/analysis-methodology.md) | 互动统计与关系分析的证据口径 |
| [JSON Schema](templates/message_schema.json) | 可复用的字段模板 |
| [分析提示词](templates/analysis_prompt.md) | 九个分析维度和报告结构 |
| [报告目录说明](reports/README.md) | 公共模板与私人报告的存放方式 |

## 当前范围

本骨架实现了从 JSONL 到审计和打包的基本命令。微信迁移和可读导出由使用者完成，统计命令的结果可作为后续人工或 AI 分析的输入。公开发布前可由项目持有人选择许可。
