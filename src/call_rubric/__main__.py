"""CLI: python3 -m call_rubric grade <file-or-dir> [--config config.json] [--json]"""
import argparse
import json
import pathlib
import sys

from .rubric import grade, load_config


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="call_rubric")
    ap.add_argument("cmd", choices=["grade"])
    ap.add_argument("path")
    ap.add_argument("--config")
    ap.add_argument("--json", action="store_true", help="print full JSON reports")
    a = ap.parse_args(argv)

    p = pathlib.Path(a.path)
    files = sorted(p.glob("*.json")) if p.is_dir() else [p]
    cfg = load_config(a.config)
    reports = []
    for f in files:
        reports.append(grade(json.loads(f.read_text("utf-8")), cfg))
    if a.json:
        print(json.dumps(reports, indent=2, ensure_ascii=False))
    else:
        print(f"{'id':32} {'overall':>7}  {'pass':5} flags")
        for r in reports:
            codes = ",".join(sorted({f['code'] for f in r['flags']})) or "-"
            print(f"{str(r['id']):32} {r['overall']:7.2f}  {'yes' if r['passed'] else 'NO':5} {codes}")
    return 0 if all(r["passed"] for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
