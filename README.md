<p align="center">
  <img src="assets/readme-hero.svg" alt="WeChat Friendship Analyzer — 本地聊天数据整理工具" width="100%">
</p>

<h1 align="center">微信会话数据整理与分析</h1>

<p align="center">把授权取得的聊天记录整理成可审计、可复核的分析数据包。</p>

<p align="center">
  <a href="#快速开始"><strong>快速开始</strong></a> ·
  <a href="#文档与模板">文档与模板</a> ·
  <a href="examples/sample_messages.jsonl">查看虚构样例</a>
</p>

## 从 JSONL 到可验证的数据包

| 步骤 | 工具 | 你会得到 |
| :--- | :--- | :--- |
| **01 · 校验** | [validate_jsonl.py](scripts/validate_jsonl.py) | 检查字段、时间顺序、重复记录和可选的隐私模式 |
| **02 · 审计** | [audit_data.py](scripts/audit_data.py) | 汇总发送方、月份、消息类型和附件标记 |
| **03 · 整理** | [anonymize_data.py](scripts/anonymize_data.py) | 应用显式发送者别名，生成保留正文与引用的独立副本 |
| **04 · 交付** | [package_data.py](scripts/package_data.py) | 生成 ZIP，试解压并核对 SHA-256 |

## 快速开始

在项目根目录打开 PowerShell。脚本使用 **Python 3.10+** 标准库。以下命令使用仓库中的虚构对话。

**1. 校验样例并生成审计报告**

```powershell
$sample = "examples/sample_messages.jsonl"
python -B -X utf8 scripts/validate_jsonl.py $sample --check-privacy
python -B -X utf8 scripts/audit_data.py $sample `
  --output private_reports/demo_audit.md
```

**2. 整理发送者标签并打包**

```powershell
$sample = "examples/sample_messages.jsonl"
$checked = "private_data/demo_checked.jsonl"
python -B -X utf8 scripts/anonymize_data.py $sample `
  --alias "示例用户A=user_a" --alias "示例用户B=user_b" `
  --output $checked
python -B -X utf8 scripts/package_data.py $checked `
  --document docs/data-format.md --output personal_exports/demo.zip
```

报告和 ZIP 分别写入 `private_reports/` 与 `personal_exports/`。再次运行时请使用新的输出文件名。处理真实会话时，按时间顺序传入多个主会话 JSONL，合并转发内嵌记录可通过 `--forwarded` 单独附带。

## 文档与模板

| 开始整理 | 开始分析 |
| :--- | :--- |
| [本地工作流](docs/workflow.md) · 从可读导出到交付 | [分析方法](docs/analysis-methodology.md) · 指标和证据口径 |
| [数据格式](docs/data-format.md) · 字段、顺序与统计范围 | [分析提示词](templates/analysis_prompt.md) · 九个分析维度 |
| [JSON Schema](templates/message_schema.json) · 字段模板 | [报告目录说明](reports/README.md) · 报告保存方式 |

> [!NOTE]
> 本工具以已经授权取得的可读 JSONL 为输入。真实聊天记录、媒体和私人报告请保存在本机的忽略目录中。详见[隐私约定](docs/privacy.md)。
