"""Check record fields, order, duplicates and optional privacy patterns."""

import argparse
import json

from common import add_input_options, inspect, privacy_hits, read_jsonl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_input_options(parser)
    parser.add_argument("--check-privacy", action="store_true", help="检查已定义的隐私模式")
    args = parser.parse_args()
    try:
        rows = read_jsonl(args.inputs)
        report = inspect(rows, args.scope)
        if args.check_privacy:
            report["privacy_pattern_hits"] = privacy_hits(rows)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(bool(report["errors"] or report.get("privacy_pattern_hits")))
    except (ValueError, OSError) as error:
        parser.exit(1, f"校验失败：{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
