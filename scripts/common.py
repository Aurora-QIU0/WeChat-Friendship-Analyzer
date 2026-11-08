"""Shared reader and checks for the offline JSONL commands."""

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

BEIJING = timezone(timedelta(hours=8))
REQUIRED = {"timestamp", "datetime", "sender", "message_type", "content", "quote_content", "has_attachment"}
OPTIONAL = {
    "source_type_code", "quote_status", "attachment_type", "readable_resource", "resource_status",
    "message_index", "forwarded_bundle_id", "parent_message_index", "forwarded_item_index",
    "source_sender_label", "sender_status",
}
SAFE_FIELDS = REQUIRED | OPTIONAL
SUSPICIOUS = {
    "wechat_id": re.compile(r"\bwxid_[a-z0-9_]+", re.I),
    "windows_path": re.compile(r"(?<![a-z0-9_])[a-z]:[\\/](?![\\/])|(?<!\\)\\\\[^\\\s]+\\", re.I),
    "credential_pattern": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:数据库密钥|微信登录密码|db[_ -]?key)\s*[:：=]\s*[a-z0-9_+/=-]{8,}", re.I),
    "possible_cn_mobile": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_keys(pairs):
    value = dict(pairs)
    require(len(value) == len(pairs), "对象有重复键")
    return value


def reject_constant(value):
    raise ValueError(f"非法 JSON 常量 {value}")


def read_jsonl(paths):
    rows = []
    for path in paths:
        with path.open(encoding="utf-8") as source:
            for number, line in enumerate(source, 1):
                try:
                    row = json.loads(line, object_pairs_hook=unique_keys, parse_constant=reject_constant)
                    require(isinstance(row, dict), "记录不是 JSON 对象")
                except ValueError as error:
                    raise ValueError(f"{path.name} 第 {number} 行无法解析为唯一键 JSON 对象") from error
                rows.append(row)
    require(rows, "没有消息记录")
    return rows


def inspect(rows, scope):
    errors, senders, months, kinds, attachments = (Counter() for _ in range(5))
    stamps, indices, serialized = [], [], set()
    for row in rows:
        if REQUIRED - row.keys():
            errors["missing_fields"] += 1
        if row.keys() - SAFE_FIELDS:
            errors["unknown_fields"] += 1
        signature = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if signature in serialized:
            errors["duplicate_rows"] += 1
        serialized.add(signature)
        stamp = row.get("timestamp")
        if type(stamp) is int and stamp > 0:
            try:
                moment = datetime.fromtimestamp(stamp, BEIJING)
            except (OverflowError, OSError, ValueError):
                errors["invalid_time"] += 1
            else:
                stamps.append(stamp)
                months[moment.strftime("%Y-%m")] += 1
                if row.get("datetime") != moment.isoformat(timespec="seconds"):
                    errors["display_time_mismatch"] += 1
        else:
            errors["invalid_time"] += 1
        sender, kind = row.get("sender"), row.get("message_type")
        if isinstance(sender, str) and sender.strip() and scope == "main":
            senders[sender] += 1
            if (sender == "系统") != (kind == "system"):
                errors["system_label_mismatch"] += 1
        elif sender is None and scope == "forwarded":
            senders["未核实"] += 1
        else:
            errors["invalid_sender"] += 1
        if isinstance(kind, str) and kind:
            kinds[kind] += 1
        else:
            errors["invalid_type"] += 1
        if not isinstance(row.get("content"), str) or not isinstance(row.get("quote_content"), (str, type(None))):
            errors["invalid_text"] += 1
        if type(row.get("has_attachment")) is not bool:
            errors["invalid_attachment_flag"] += 1
        elif row["has_attachment"]:
            category = row.get("attachment_type") or "未分类"
            attachments[category if isinstance(category, str) else "无效类别"] += 1
        if any(isinstance(row.get(name), (dict, list)) for name in OPTIONAL):
            errors["non_scalar_metadata"] += 1
        if "message_index" in row:
            index = row["message_index"]
            if type(index) is int and index > 0:
                indices.append(index)
            else:
                errors["invalid_index"] += 1
    if any(a > b for a, b in zip(stamps, stamps[1:])):
        errors["time_out_of_order"] += 1
    if indices and (len(indices) != len(rows) or any(b != a + 1 for a, b in zip(indices, indices[1:]))):
        errors["index_not_contiguous"] += 1
    if scope == "main" and len(senders.keys() - {"系统"}) > 2:
        errors["more_than_two_senders"] += 1
    span = [datetime.fromtimestamp(stamp, BEIJING).isoformat(timespec="seconds")
            for stamp in (min(stamps), max(stamps))] if stamps else None
    return {"records": len(rows), "senders": senders, "months": dict(sorted(months.items())), "types": kinds,
            "attachments": attachments, "span": span, "errors": errors}


def privacy_hits(rows):
    hits = Counter()
    for row in rows:
        for value in row.values():
            if isinstance(value, str):
                hits.update(name for name, pattern in SUSPICIOUS.items() if pattern.search(value))
    return hits


def new_output(path):
    require(not path.exists(), "输出文件已存在，请选择新的路径")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_input_options(parser):
    parser.add_argument("inputs", nargs="+", type=Path, help="按时间顺序传入 JSONL 文件")
    parser.add_argument("--scope", choices=("main", "forwarded"), default="main")
