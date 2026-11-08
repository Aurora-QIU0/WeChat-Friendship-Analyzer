"""Package approved JSONL files and verify a local round-trip."""

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

from common import inspect, new_output, privacy_hits, read_jsonl, require, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="按时间顺序传入主会话 JSONL")
    parser.add_argument("--forwarded", type=Path, help="独立的合并转发 JSONL")
    parser.add_argument("--document", type=Path, action="append", default=[], help="附带已检查的 Markdown 说明或审计报告")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        require(args.output.suffix.lower() == ".zip", "输出文件须为 ZIP")
        files, totals = {}, {}
        directories = {"main": "01_聊天记录", "forwarded": "03_辅助资料"}
        scopes = [("main", args.inputs)]
        if args.forwarded:
            scopes.append(("forwarded", [args.forwarded]))
        for scope, paths in scopes:
            rows = read_jsonl(paths)
            errors, hits = inspect(rows, scope)["errors"], privacy_hits(rows)
            require(not errors and not hits, f"{scope} 校验未通过 " + json.dumps({"errors": errors, "privacy_hits": hits}))
            totals[scope] = len(rows)
            for path in paths:
                require(path.suffix.lower() == ".jsonl" and "\\" not in path.name, "输入文件须为普通 JSONL 路径")
                member = f"friendship_analysis/{directories[scope]}/{path.name}"
                require(member.casefold() not in {name.casefold() for name in files}, "包内文件名重复")
                files[member] = path
        for path in args.document:
            require(path.suffix.lower() == ".md" and "\\" not in path.name, "数据说明须为 Markdown 文件")
            require(not privacy_hits([{"text": path.read_text(encoding="utf-8")}]), "数据说明包含需核对的隐私模式")
            member = f"friendship_analysis/02_数据说明/{path.name}"
            require(member.casefold() not in {name.casefold() for name in files}, "包内文件名重复")
            files[member] = path
        output = new_output(args.output)
        checksums = {member: sha256(path) for member, path in files.items()}
        with tempfile.TemporaryDirectory(dir=output.parent, prefix=".package-") as tmp:
            temp = Path(tmp)
            archive = temp / "payload.zip"
            with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
                for member, source in files.items():
                    bundle.write(source, member)
            with zipfile.ZipFile(archive) as bundle:
                require(bundle.namelist() == list(files) and bundle.testzip() is None, "ZIP 目录或 CRC 核验失败")
                extracted = temp / "check"
                bundle.extractall(extracted)
            for member, source in files.items():
                require(checksums[member] == sha256(extracted / member) == sha256(source), "原件与解压副本摘要不一致")
            for scope, paths in scopes:
                copies = [extracted / "friendship_analysis" / directories[scope] / path.name for path in paths]
                rows = read_jsonl(copies)
                require(len(rows) == totals[scope] and not inspect(rows, scope)["errors"] and not privacy_hits(rows),
                        "试解压后的 JSONL 未通过复核")
            for path in args.document:
                copy = extracted / "friendship_analysis" / "02_数据说明" / path.name
                require(not privacy_hits([{"text": copy.read_text(encoding="utf-8")}]), "试解压后的数据说明未通过隐私检查")
            archive_digest = sha256(archive)
            with output.open("xb") as destination, archive.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    destination.write(chunk)
            require(sha256(output) == archive_digest, "写出后的 ZIP 摘要不一致")
        print(json.dumps({"records": totals, "zip_sha256": archive_digest, "file_sha256": checksums}, indent=2))
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        parser.exit(1, f"打包失败：{error}\n")


if __name__ == "__main__":
    main()
