"""Create a local Markdown audit with aggregate counts."""

import argparse
from pathlib import Path

from common import add_input_options, inspect, new_output, read_jsonl


def table(title, counts):
    rows = [f"## {title}", "", "| 项目 | 数量 |", "|---|---:|"]
    rows.extend(f"| {str(name).replace('|', '&#124;').replace(chr(10), ' ')} | {count:,} |" for name, count in counts.items())
    if not counts:
        rows.append("| 无 | 0 |")
    return rows + [""]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_input_options(parser)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = inspect(read_jsonl(args.inputs), args.scope)
        lines = ["# 聊天数据审计", "", f"范围为 `{args.scope}`，共 {report['records']:,} 条记录。"]
        if report["span"]:
            start, end = report["span"]
            lines.append(f"可验证的时间跨度为 {start} 至 {end}（北京时间）。")
        lines.append("")
        for label, key in [("发送方", "senders"), ("月度分布", "months"), ("消息类型", "types"),
                           ("附件标记", "attachments"), ("异常项", "errors")]:
            lines.extend(table(label, report[key]))
        lines.extend(["此报告基于输入的 JSONL 文件。附件数量来自记录标记，其他设备的历史需另行核对。", ""])
        with new_output(args.output).open("x", encoding="utf-8", newline="\n") as output:
            output.write("\n".join(lines))
        print(f"已生成审计报告（{report['records']:,} 条）")
        return int(bool(report["errors"]))
    except (ValueError, OSError) as error:
        parser.exit(1, f"审计失败：{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
