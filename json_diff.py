#!/usr/bin/env python3
"""Compare JSON structure while keeping all values out of the output."""

import argparse
import json
from pathlib import Path
import sys


MAX_BYTES = 16 * 1024 * 1024
MAX_LIMIT = 1_000
MAX_NODES = 250_000


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object key")
        result[key] = value
    return result


def reject_constant(_value):
    raise ValueError("non-standard number")


def load_json(path):
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_BYTES + 1)
    except OSError:
        raise ValueError(f"{path}: cannot read file") from None
    if len(raw) > MAX_BYTES:
        raise ValueError(f"{path}: file exceeds the {MAX_BYTES}-byte limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        raise ValueError(f"{path}: input is not valid UTF-8") from None
    try:
        return json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant)
    except json.JSONDecodeError as error:
        raise ValueError(f"{path}:{error.lineno}:{error.colno}: invalid JSON") from None
    except ValueError:
        raise ValueError(f"{path}: duplicate object key or non-standard JSON number") from None
    except RecursionError:
        raise ValueError(f"{path}: JSON nesting is too deep") from None


def compare(before, after, limit):
    counts = {"added": 0, "removed": 0, "changed": 0}
    rows = []
    visited = 0

    def record(kind, path):
        nonlocal visited
        visited += 1
        if visited > MAX_NODES:
            raise ValueError(f"comparison exceeds the {MAX_NODES}-node limit")
        counts[kind] += 1
        if len(rows) < limit:
            rows.append((kind, path if len(path) <= 240 else path[:237] + "..."))

    def object_children(path, left, right):
        for key in right:
            child = f"{path}[{json.dumps(key, ensure_ascii=True)}]"
            if key not in left:
                record("added", child)
            else:
                yield child, left[key], right[key]
        for key in left:
            if key not in right:
                record("removed", f"{path}[{json.dumps(key, ensure_ascii=True)}]")

    def array_children(path, left, right):
        common = min(len(left), len(right))
        for index in range(common):
            yield f"{path}[{index}]", left[index], right[index]
        for index in range(common, len(left)):
            record("removed", f"{path}[{index}]")
        for index in range(common, len(right)):
            record("added", f"{path}[{index}]")

    frames = [iter((("$", before, after),))]
    while frames:
        try:
            path, left, right = next(frames[-1])
        except StopIteration:
            frames.pop()
            continue
        visited += 1
        if visited > MAX_NODES:
            raise ValueError(f"comparison exceeds the {MAX_NODES}-node limit")
        if type(left) is not type(right):
            record("changed", path)
        elif isinstance(left, dict):
            frames.append(iter(object_children(path, left, right)))
        elif isinstance(left, list):
            frames.append(iter(array_children(path, left, right)))
        elif left != right:
            record("changed", path)
    return counts, rows


def main():
    parser = argparse.ArgumentParser(description="Compare JSON files and report changed paths, never values.")
    parser.add_argument("before", type=Path, help="original JSON file")
    parser.add_argument("after", type=Path, help="updated JSON file")
    parser.add_argument("--limit", type=int, default=100, help="maximum paths to print (1–1000)")
    args = parser.parse_args()
    if not 1 <= args.limit <= MAX_LIMIT:
        parser.error(f"--limit must be from 1 to {MAX_LIMIT}")

    try:
        before = load_json(args.before)
        after = load_json(args.after)
    except ValueError as error:
        print(f"json-diff: {error}", file=sys.stderr)
        return 2

    try:
        counts, rows = compare(before, after, args.limit)
    except ValueError as error:
        print(f"json-diff: {error}", file=sys.stderr)
        return 2
    total = sum(counts.values())
    if not total:
        print("No differences found.")
        return 0
    markers = {"added": "+", "removed": "-", "changed": "~"}
    for kind, path in rows:
        print(f"{markers[kind]} {path}")
    print(
        f"Added: {counts['added']}; removed: {counts['removed']}; "
        f"changed: {counts['changed']}."
    )
    if total > len(rows):
        print(f"{total - len(rows)} more path(s) omitted.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
