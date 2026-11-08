"""Convert saved WeFlow raw /api/v1/messages JSON pages, without network access."""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from common import BEIJING, inspect, privacy_hits, require, sha256, unique_keys, reject_constant


TYPES = {1: 'text', 3: 'image', 34: 'voice', 43: 'video', 47: 'emoji',
         48: 'location', 42: 'contact', 50: 'call', 10000: 'system',
         266287972401: 'system', 244813135921: 'quote'}
MEDIA = {3: 'image', 34: 'voice', 43: 'video', 47: 'emoji'}


def convert(pages, expected_count):
    require(pages and type(expected_count) is int and expected_count > 0, '需要非空分页及正整数预期数量')
    rows, seen, warnings = [], set(), Counter()
    talker = None
    for page_number, page in enumerate(pages, 1):
        require(isinstance(page, dict) and page.get('success') is True, '只接受成功的 WeFlow 原始消息响应')
        current = page.get('talker')
        require(isinstance(current, str) and current and '@chatroom' not in current, '只支持单个非群聊会话')
        if talker is None:
            talker = current
        require(current == talker, '分页包含不同会话')
        require(type(page.get('hasMore')) is bool, '缺少有效 hasMore 标记')
        require(page['hasMore'] == (page_number < len(pages)), '分页链未结束或结束后仍有分页')
        messages = page.get('messages')
        require(isinstance(messages, list) and type(page.get('count')) is int
                and page['count'] == len(messages), '分页数量与 messages 不一致')
        for item in messages:
            require(isinstance(item, dict), '消息必须是对象')
            stamp, code, local_id = (item.get(k) for k in ('createTime', 'localType', 'localId'))
            require(type(stamp) is int and 0 < stamp < 10000000000, '时间须为有效秒级 Unix 整数')
            require(type(code) is int and code >= 0, 'localType 必须为非负整数')
            require(type(local_id) is int and local_id > 0, '缺少有效 localId')
            require(local_id not in seen, '消息 ID 重复；请核对分页，不自动去重')
            seen.add(local_id)
            try:
                displayed = datetime.fromtimestamp(stamp, BEIJING).isoformat(timespec='seconds')
            except (ValueError, OverflowError, OSError) as exc:
                raise ValueError('时间超出支持范围') from exc
            content = item.get('content')
            require(isinstance(content, str), 'content 缺失或不是字符串；不猜测正文')
            kind = TYPES.get(code, 'weflow_unknown')
            if kind == 'system':
                sender = '系统'
            else:
                require(type(item.get('isSend')) is int and item['isSend'] in (0, 1), '发送方向无法确认')
                require(item['isSend'] == 1 or item.get('senderUsername') == talker,
                        '接收消息发送者与会话不一致')
                sender = '我' if item['isSend'] else '好友'
            quote = item.get('quote')
            quote_content = None
            quote_status = 'not_applicable'
            if quote is not None:
                require(isinstance(quote, dict), 'quote 必须为对象')
                quote_content = quote.get('content')
                require(quote_content is None or isinstance(quote_content, str), '引用正文不是字符串')
                quote_status = 'available' if quote_content is not None else 'unknown'
            elif kind == 'quote' or item.get('replyToMessageId'):
                quote_status = 'unknown'
            if quote_status == 'unknown':
                warnings['quote_content_unavailable'] += 1
            attachment = MEDIA.get(code)
            if item.get('mediaType'):
                require(isinstance(item['mediaType'], str), 'mediaType 必须为字符串')
                attachment = item['mediaType'] if item['mediaType'] in {'image','voice','video','emoji','file'} else 'unknown'
            if kind == 'weflow_unknown':
                warnings['unclassified_type'] += 1
            if code == 49:
                warnings['compound_message_not_expanded'] += 1
            rows.append(dict(timestamp=stamp, datetime=displayed, sender=sender,
                message_type=kind, source_type_code=code, content=content,
                quote_content=quote_content, quote_status=quote_status,
                has_attachment=attachment is not None, attachment_type=attachment,
                readable_resource=None,
                resource_status='unknown' if attachment or kind == 'weflow_unknown' else 'not_applicable'))
    require(len(rows) == expected_count, '主消息数量与预期不符')
    rows.sort(key=lambda row: row['timestamp'])  # Equal timestamps retain input order.
    for index, row in enumerate(rows, 1):
        row['message_index'] = index
    audit = inspect(rows, 'main')
    require(not audit['errors'], '转换后的记录未通过通用校验')
    return rows, dict(warnings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', type=Path, help='同一私聊从第一页到最后一页的原始 JSON 响应')
    parser.add_argument('--expected-count', type=int, required=True, help='独立核对的主消息总数')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        require(not args.output.exists(), '输出已存在；请选择新路径')
        pages, hashes = [], []
        for path in args.inputs:
            pages.append(json.loads(path.read_text(encoding='utf-8-sig'),
                object_pairs_hook=unique_keys, parse_constant=reject_constant))
            hashes.append(sha256(path))
        rows, warnings = convert(pages, args.expected_count)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8', newline='\n') as target:
            for row in rows:
                target.write(json.dumps(row, ensure_ascii=False) + '\n')
        print(json.dumps({'records': len(rows), 'warnings': warnings,
            'privacy_pattern_hits': privacy_hits(rows), 'input_sha256_in_order': hashes,
            'output_sha256': sha256(args.output),
            'completeness': '仅确认输入数量与预期一致；不证明微信历史完整或分页无缺口'},
            ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        parser.exit(1, f'导入失败：{error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
