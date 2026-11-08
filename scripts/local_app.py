"""Loopback-only workspace. No persistence, remote requests, or database access."""
import argparse
import base64
import hashlib
import io
import json
import secrets
import zipfile
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from common import inspect, privacy_hits, require, unique_keys, reject_constant
from import_weflow import convert

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 32 * 1024 * 1024


def decode_json(text):
    return json.loads(text, object_pairs_hook=unique_keys, parse_constant=reject_constant)


def prepare(payload):
    files = payload.get('files')
    require(isinstance(files, list) and 0 < len(files) <= 100, '请选择 1–100 个文件')
    expected = payload.get('expected_count')
    require(expected is None or type(expected) is int and expected > 0, '预期总数须为正整数')
    mode = payload.get('format')
    require(mode in {'jsonl', 'json', 'weflow', 'zip'}, '请选择支持的格式')
    entries, hashes, excluded = [], [], []
    total = 0
    for file in files:
        require(isinstance(file, dict) and isinstance(file.get('name'), str), '文件信息无效')
        raw = base64.b64decode(file['data'], validate=True)
        total += len(raw)
        require(total <= LIMIT, '输入总大小超过 32 MiB')
        name = file['name'].replace('\\', '/').split('/')[-1]
        hashes.append({'name': name, 'sha256': hashlib.sha256(raw).hexdigest()})
        if mode == 'zip':
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                members = archive.infolist()
                require(len(members) <= 1000, 'ZIP 条目过多')
                require(sum(i.file_size for i in members) <= LIMIT, 'ZIP 展开大小超过 32 MiB')
                seen = set()
                for item in sorted(members, key=lambda i: i.filename):
                    if item.is_dir():
                        continue
                    basename = item.filename.replace('\\', '/').split('/')[-1]
                    if not (basename.startswith('messages_') and basename.endswith('.jsonl')):
                        excluded.append(basename)
                        continue
                    require(basename not in seen, 'ZIP 有重名主会话文件')
                    seen.add(basename)
                    entries.append((basename, archive.read(item).decode('utf-8-sig')))
        else:
            require('forwarded' not in name.lower(), '转发内嵌文件不得混入主会话')
            entries.append((name, raw.decode('utf-8-sig')))
    require(entries, '没有找到主会话记录；ZIP 仅接收 messages_*.jsonl')
    rows, warnings = [], {}
    if mode == 'weflow':
        require(expected is not None, 'WeFlow 转换必须提供独立核对的预期总数')
        rows, warnings = convert([decode_json(text) for _, text in entries], expected)
    else:
        for name, text in entries:
            if mode == 'json':
                part = decode_json(text)
                require(isinstance(part, list), 'JSON 须为符合本项目字段的消息数组')
            else:
                part = []
                for number, line in enumerate(text.splitlines(), 1):
                    try:
                        part.append(decode_json(line))
                    except ValueError as exc:
                        raise ValueError(f'{name} 第 {number} 行 JSON 无效') from exc
            require(all(isinstance(r, dict) for r in part), '每条消息须为对象')
            rows.extend(part)
    require(0 < len(rows) <= 100000, '主消息数量须为 1–100000')
    require(not any(r.get('sender') is None or r.get('parent_message_index') is not None
                    or r.get('forwarded_item_index') is not None for r in rows),
            '发现转发内嵌或未识别发送者记录，请独立保存')
    report = inspect(rows, 'main')
    if expected is not None and expected != len(rows):
        report['errors']['expected_count_mismatch'] += 1
    # A repeated text is only a review candidate, never automatically removed.
    signatures = Counter(json.dumps([r.get(k) for k in ('timestamp', 'sender', 'message_type', 'content', 'quote_content')],
                                    ensure_ascii=False, sort_keys=True) for r in rows)
    report['possible_duplicate_messages'] = sum(n - 1 for n in signatures.values() if n > 1)
    report['privacy_pattern_hits'] = privacy_hits(rows)
    report['expected_count_checked'] = expected is not None
    report['input_sha256'] = hashes
    report['excluded_files'] = excluded
    report['warnings'] = warnings
    report['missing_quote_snapshots'] = sum(r.get('quote_status') == 'unknown' for r in rows)
    report['attachment_resource_unknown'] = sum(r.get('has_attachment') is True and r.get('readable_resource') is None for r in rows)
    return {'rows': rows, 'report': report}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # Never log request data or query strings.

    def reply(self, status, content, mime='application/json; charset=utf-8'):
        data = content.encode('utf-8') if isinstance(content, str) else content
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)

    def trusted(self):
        return self.headers.get('Host') == self.server.authority

    def do_GET(self):
        if not self.trusted():
            return self.reply(403, '{}')
        assets = {'/': ('web/index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('web/app.js', 'text/javascript; charset=utf-8'),
                  '/style.css': ('web/style.css', 'text/css; charset=utf-8')}
        if self.path == '/api/bootstrap':
            prompt = (ROOT / 'xiaoyu/character/system_prompt.md').read_text(encoding='utf-8')
            versions = [block.split('```', 1)[0].strip() for block in prompt.split('```text')[1:]]
            return self.reply(200, json.dumps({'token': self.server.token, 'prompts': versions}, ensure_ascii=False))
        if self.path == '/api/demo':
            raw = (ROOT / 'examples/weflow_response.sample.json').read_bytes()
            result = prepare({'format': 'weflow', 'expected_count': 4, 'files': [
                {'name': 'weflow_response.sample.json', 'data': base64.b64encode(raw).decode()}]})
            return self.reply(200, json.dumps(result, ensure_ascii=False))
        if self.path not in assets:
            return self.reply(404, '{}')
        path, mime = assets[self.path]
        self.reply(200, (ROOT / path).read_bytes(), mime)

    def do_POST(self):
        if (not self.trusted() or self.headers.get('Origin') != 'http://' + self.server.authority
                or self.headers.get('X-Local-Token') != self.server.token):
            return self.reply(403, '{"error":"仅允许本机工作台请求"}')
        if self.path != '/api/inspect':
            return self.reply(404, '{}')
        try:
            size = int(self.headers.get('Content-Length', '0'))
            require(0 < size <= LIMIT * 2, '请求大小无效或过大')
            payload = decode_json(self.rfile.read(size).decode('utf-8'))
            require(isinstance(payload, dict), '请求须为对象')
            result = prepare(payload)
            self.reply(200, json.dumps(result, ensure_ascii=False, allow_nan=False))
        except (ValueError, TypeError, KeyError, OverflowError, OSError, zipfile.BadZipFile, RuntimeError):
            self.reply(400, json.dumps({'error': '文件未通过导入检查。请核对格式、分页顺序、数量、字段类型及 ZIP 大小；终端脚本可提供具体校验原因。'}, ensure_ascii=False))


def make_server(port):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.authority = f'127.0.0.1:{server.server_port}'
    server.token = secrets.token_urlsafe(32)
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    with make_server(args.port) as server:
        print(f'本地工作台：http://{server.authority}（Ctrl+C 停止；请保持此窗口打开）', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
