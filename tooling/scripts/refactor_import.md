## Refactor Imports Helper

`tooling/scripts/refactor_imports.py` performs bulk import rewrites without letting typos slip through. Common patterns:

```bash
# quick ad-hoc mapping
python tooling/scripts/refactor_imports.py --map old.module=new.module [--root .]

# store a migration in a file
cat > mappings.txt <<'EOF'
old.module=new.module
another.package=another.module
EOF
python tooling/scripts/refactor_imports.py --mapping-file mappings.txt --apply
```

Additional options:

* `--apply` – write in-place (dry-run otherwise)
* `--prefer-relative` – emit relative imports where possible (default: absolute)
* `--root PATH` – directory to scan (default: `src`)
* `--ensure-import path:module:symbol1,symbol2` – guarantee imports exist (runs after rewrites)
* `--export-map old=new` – rename entries inside `__all__`
* `--no-use-git` – scan filesystem instead of tracked files
* `--mapping-file file.txt` – load mappings line-by-line; supports comments

The script respects `.gitignore`/tracked files when using git discovery, so temporary folders or vendored code are left untouched unless `--no-use-git` is used. Use `--prefer-relative` when you want rewritten modules to become relative imports; abs paths remain the default.
