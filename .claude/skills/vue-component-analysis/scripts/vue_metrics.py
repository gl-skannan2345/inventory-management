#!/usr/bin/env python3
"""Collect structural metrics for Vue single-file components (SFCs).

Usage:
    python3 vue_metrics.py [PATH ...]      # files or directories (default: client/src)
    python3 vue_metrics.py --json [PATH ...]

The script only reads files and prints findings. It uses regexes, not a full
Vue parser, so every hit is a candidate for review, not a verified defect.
"""
import json
import re
import sys
from pathlib import Path

DEFAULT_ROOT = "client/src"

# Thresholds used to flag a component for review. Tune them here.
LIMITS = {
    "lines": 400,           # whole file
    "script_lines": 250,
    "computed": 15,
    "watchers": 5,
    "functions": 25,
    "props": 10,
    "template_inline_handlers": 8,
}


def section(text, tag):
    m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", text, re.S)
    return m.group(1) if m else ""


def count(pattern, text, flags=0):
    return len(re.findall(pattern, text, flags))


def analyze(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    template = section(text, "template")
    script = section(text, "script")
    style = section(text, "style")

    # Props: defineProps({...}) keys or props: {...} option keys.
    props = 0
    dp = re.search(r"defineProps\s*\(\s*\{(.*?)\}\s*\)", script, re.S)
    if dp:
        props = count(r"^\s*\w+\s*:", dp.group(1), re.M)
    else:
        op = re.search(r"\bprops\s*:\s*\{(.*?)\n\s{0,4}\}", script, re.S)
        if op:
            props = count(r"^\s*\w+\s*:", op.group(1), re.M)

    # Template loops without :key, and loops keyed on index.
    vfor_lines = [
        i for i, line in enumerate(template.splitlines(), 1) if "v-for" in line
    ]
    vfor_no_key = 0
    vfor_index_key = 0
    lines_t = template.splitlines()
    # Only look at the opening tag that carries v-for, so a :key on a
    # neighbouring element is not mistaken for this loop's key.
    for m in re.finditer(r"<[\w-]+(?:\s[^>]*)?\bv-for\s*=", template):
        end = template.find(">", m.end())
        opening = template[m.start() : end + 1] if end != -1 else template[m.start():]
        if not re.search(r"\s:key\s*=|\skey\s*=", opening):
            vfor_no_key += 1
        # Require the whole quoted value to be the index, so "item.id" does not match "i".
        if re.search(r"""(?::|\s)key\s*=\s*["'](index|idx|i)["']""", opening):
            vfor_index_key += 1

    # Inline arrow functions / complex expressions in template event handlers.
    inline_handlers = count(r"@\w[\w.-]*=\"[^\"]*(=>|\([^)]*\)\s*=>)", template)

    # Function calls inside template bindings (re-evaluated on every render).
    template_calls = count(r"(?<!@)(?<!v-on:)\b(?:format|filter|get|calc|compute)\w*\s*\(", template)

    # Watchers and computeds (Composition API and Options API).
    watchers = count(r"\bwatch(?:Effect)?\s*\(", script)
    computed = count(r"\bcomputed\s*\(", script)

    functions = count(r"\bfunction\s+\w+\s*\(|\bconst\s+\w+\s*=\s*(?:async\s*)?\(|\bconst\s+\w+\s*=\s*(?:async\s*)?function", script)

    # Reactive containers that might hold large data sets.
    large_refs = re.findall(r"\bconst\s+(\w+)\s*=\s*ref\(\s*\[", script)

    # Date methods used without a visible validity check (project common issue #2).
    date_calls = count(r"\.getMonth\(\)|\.getFullYear\(\)|\.getDate\(\)", script)
    date_checks = count(r"isNaN\(|Number\.isNaN|isValid", script)

    # Hard-coded hex colors in style blocks (design tokens may already exist).
    hex_colors = count(r"#[0-9a-fA-F]{3,8}\b", style)

    # Repeated identical template lines suggest copy-paste markup.
    norm = [re.sub(r"\s+", " ", l).strip() for l in lines_t]
    norm = [l for l in norm if len(l) > 40 and not l.startswith("<!--")]
    dup_lines = sorted({l for l in norm if norm.count(l) > 2})

    metrics = {
        "file": str(path),
        "lines": text.count("\n") + 1,
        "script_lines": script.count("\n") + 1 if script else 0,
        "template_lines": template.count("\n") + 1 if template else 0,
        "style_lines": style.count("\n") + 1 if style else 0,
        "props": props,
        "computed": computed,
        "watchers": watchers,
        "functions": functions,
        "vfor": len(vfor_lines),
        "vfor_without_key": vfor_no_key,
        "vfor_index_key": vfor_index_key,
        "template_inline_handlers": inline_handlers,
        "template_calls": template_calls,
        "large_ref_arrays": large_refs,
        "date_method_calls": date_calls,
        "date_validity_checks": date_checks,
        "hardcoded_hex_colors": hex_colors,
        "repeated_template_lines": dup_lines[:5],
    }

    flags = []
    if metrics["lines"] > LIMITS["lines"]:
        flags.append(f"file is {metrics['lines']} lines (> {LIMITS['lines']})")
    if metrics["script_lines"] > LIMITS["script_lines"]:
        flags.append(f"script block is {metrics['script_lines']} lines (> {LIMITS['script_lines']})")
    if computed > LIMITS["computed"]:
        flags.append(f"{computed} computed properties (> {LIMITS['computed']})")
    if watchers > LIMITS["watchers"]:
        flags.append(f"{watchers} watchers (> {LIMITS['watchers']})")
    if functions > LIMITS["functions"]:
        flags.append(f"{functions} functions (> {LIMITS['functions']})")
    if props > LIMITS["props"]:
        flags.append(f"{props} props (> {LIMITS['props']})")
    if inline_handlers > LIMITS["template_inline_handlers"]:
        flags.append(f"{inline_handlers} inline template handlers (> {LIMITS['template_inline_handlers']})")
    if vfor_no_key:
        flags.append(f"{vfor_no_key} v-for without :key")
    if vfor_index_key:
        flags.append(f"{vfor_index_key} v-for keyed on index")
    if date_calls and not date_checks:
        flags.append("date methods called with no NaN/validity check")
    if dup_lines:
        flags.append(f"{len(dup_lines)} template line(s) repeated 3+ times (possible copy-paste)")
    metrics["flags"] = flags
    return metrics


def collect(paths):
    files = []
    for p in paths:
        pth = Path(p)
        if pth.is_dir():
            files.extend(sorted(pth.rglob("*.vue")))
        elif pth.suffix == ".vue":
            files.append(pth)
    return files


def main(argv):
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"] or [DEFAULT_ROOT]
    results = [analyze(f) for f in collect(args)]
    if as_json:
        print(json.dumps(results, indent=2))
        return
    for r in sorted(results, key=lambda r: -len(r["flags"])):
        if not r["flags"]:
            continue
        print(f"\n{r['file']}  ({r['lines']} lines)")
        for f in r["flags"]:
            print(f"  - {f}")
    clean = sum(1 for r in results if not r["flags"])
    print(f"\nScanned {len(results)} components; {len(results) - clean} flagged, {clean} clean.")


if __name__ == "__main__":
    main(sys.argv[1:])
