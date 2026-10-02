# json-diff

Compare two JSON files without printing any field values. It reports added, removed, and changed paths with a total for each kind.

## Use

Requires Python 3.10+; no packages to install.

```sh
python json_diff.py before.json after.json
python json_diff.py before.json after.json --limit 20
```

Object paths use JSON-quoted keys and array paths use numeric indexes. Duplicate object keys and non-standard numeric constants are rejected. Each UTF-8 input is limited to 16 MiB. The report shows at most 100 paths by default; `--limit` can raise that to 1,000. Comparisons stop at 250,000 visited nodes to bound work. Values are never printed.

Exit status is `0` when files are equal, `1` when differences are found, and `2` when an input cannot be read or parsed.

## License

MIT
