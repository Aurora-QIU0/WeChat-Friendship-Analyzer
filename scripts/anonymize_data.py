"""Keep only approved fields and apply explicit sender aliases."""

import argparse
import json
from pathlib import Path

from common import SAFE_FIELDS, add_input_options, inspect, new_output, privacy_hits, read_jsonl, require


def parse_aliases(entries):
    aliases = {}
    for entry in entries:
        old, separator, new = entry.partition("=")
        require(separator and old.strip() and new.strip() and "系统" not in (old, new), "别名需采用 原标签=新标签，系统标签固定")
        require(old not in aliases and new not in aliases.values(), "别名映射重复")
        aliases[old] = new
    return aliases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_input_options(parser)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--alias", action="append", default=[])
    args = parser.parse_args()
    try:
        aliases = parse_aliases(args.alias)
        records = []
        originals = read_jsonl(args.inputs)
        main_labels = {row["sender"] for row in originals if isinstance(row.get("sender"), str)}
        require(len({aliases.get(label, label) for label in main_labels}) == len(main_labels), "别名会把不同发送者合并")
        for original in originals:
            row = {key: value for key, value in original.items() if key in SAFE_FIELDS}
            for field in ("sender", "source_sender_label"):
                value = row.get(field)
                if isinstance(value, str) and value in aliases:
                    row[field] = aliases[value]
            records.append(row)
        errors = inspect(records, args.scope)["errors"]
        require(not errors, "整理结果未通过结构校验 " + json.dumps(errors, ensure_ascii=False))
        hits = privacy_hits(records)
        require(not hits, "发现需人工核对的模式，输出未写入 " + json.dumps(hits, ensure_ascii=False))
        with new_output(args.output).open("x", encoding="utf-8", newline="\n") as destination:
            for row in records:
                destination.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"已写入 {len(records):,} 条，正文及引用逐字保留")
    except (ValueError, OSError) as error:
        parser.exit(1, f"整理失败：{error}\n")


if __name__ == "__main__":
    main()
