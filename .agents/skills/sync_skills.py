#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_skills.py - Multi-Platform 5-Replica Skills Synchronization Engine

Sole source of truth:
    c:\\Users\\24560\\Desktop\\study\\pidemo\\.agents\\skills\\

Mirror targets:
    1. C:\\Users\\24560\\.gemini\\skills\\
    2. C:\\Users\\24560\\.codex\\skills\\
    3. C:\\Users\\24560\\.claude\\skills\\
    4. C:\\Users\\24560\\.pi\\agent\\skills\\

Rules:
- Scans all skill folders (directories containing SKILL.md) in source.
- Performs bidirectional diff comparison before sync.
- Mirrors source skill folders into each target directory (overwriting modified files,
  adding missing files/dirs, cleaning up deleted files within those specific skill folders).
- Does NOT disturb other independent skills present in target directories.
- Verifies post-sync integrity (0 diff expected).
"""

import os
import sys
import shutil
import filecmp
import argparse

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SOURCE_SKILLS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "skills")
    if os.path.basename(os.path.dirname(__file__)) != "skills"
    else os.path.dirname(__file__)
)

DEFAULT_TARGETS = [
    os.path.expandvars(r"C:\Users\24560\.gemini\skills"),
    os.path.expandvars(r"C:\Users\24560\.codex\skills"),
    os.path.expandvars(r"C:\Users\24560\.claude\skills"),
    os.path.expandvars(r"C:\Users\24560\.pi\agent\skills"),
]

IGNORE_NAMES = {".git", "__pycache__", ".DS_Store", "*.pyc"}


def is_ignored(name):
    if name in IGNORE_NAMES:
        return True
    if name.endswith(".pyc") or name.endswith(".tmp"):
        return True
    return False


def get_source_skills(source_dir):
    """返回 source_dir 下包含 SKILL.md 的所有技能名称列表。"""
    skills = []
    for item in os.listdir(source_dir):
        p = os.path.join(source_dir, item)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, "SKILL.md")):
            skills.append(item)
    return sorted(skills)


def compare_trees(dir1, dir2):
    """递归比对两个目录，返回 (only_in_1, only_in_2, diff_files, same_files)。"""
    only_in_1, only_in_2, diff_files, same_files = [], [], [], []

    if not os.path.exists(dir2):
        for root, dirs, files in os.walk(dir1):
            dirs[:] = [d for d in dirs if not is_ignored(d)]
            for f in files:
                if not is_ignored(f):
                    rel = os.path.relpath(os.path.join(root, f), dir1)
                    only_in_1.append(rel)
        return only_in_1, only_in_2, diff_files, same_files

    dcmp = filecmp.dircmp(dir1, dir2, ignore=list(IGNORE_NAMES))

    def _collect(cmp):
        for f in cmp.left_only:
            p = os.path.join(cmp.left, f)
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for fn in files:
                        if not is_ignored(fn):
                            only_in_1.append(os.path.relpath(os.path.join(root, fn), dir1))
            elif not is_ignored(f):
                only_in_1.append(os.path.relpath(p, dir1))

        for f in cmp.right_only:
            p = os.path.join(cmp.right, f)
            if os.path.isdir(p):
                for root, _, files in os.walk(p):
                    for fn in files:
                        if not is_ignored(fn):
                            only_in_2.append(os.path.relpath(os.path.join(root, fn), dir2))
            elif not is_ignored(f):
                only_in_2.append(os.path.relpath(p, dir2))

        for f in cmp.diff_files:
            if not is_ignored(f):
                diff_files.append(os.path.relpath(os.path.join(cmp.left, f), dir1))

        for f in cmp.same_files:
            if not is_ignored(f):
                same_files.append(os.path.relpath(os.path.join(cmp.left, f), dir1))

        for sub in cmp.subdirs.values():
            _collect(sub)

    _collect(dcmp)
    return sorted(only_in_1), sorted(only_in_2), sorted(diff_files), sorted(same_files)


def sync_skill(source_path, target_path, dry_run=False):
    """将单个技能目录从 source_path 镜像同步到 target_path。"""
    only_in_src, only_in_tgt, diffs, _ = compare_trees(source_path, target_path)

    if not only_in_src and not only_in_tgt and not diffs:
        return True, 0, 0, 0

    if dry_run:
        return True, len(only_in_src), len(diffs), len(only_in_tgt)

    # 1. 复制/覆盖新增与变动文件
    for rel in only_in_src + diffs:
        src_f = os.path.join(source_path, rel)
        tgt_f = os.path.join(target_path, rel)
        os.makedirs(os.path.dirname(tgt_f), exist_ok=True)
        shutil.copy2(src_f, tgt_f)

    # 2. 清理目标中多余文件
    for rel in only_in_tgt:
        tgt_f = os.path.join(target_path, rel)
        if os.path.isfile(tgt_f) or os.path.islink(tgt_f):
            os.remove(tgt_f)
        elif os.path.isdir(tgt_f):
            shutil.rmtree(tgt_f, ignore_errors=True)

    # 清理可能产生的空目录
    for root, dirs, files in os.walk(target_path, topdown=False):
        for d in dirs:
            dp = os.path.join(root, d)
            if not os.listdir(dp):
                try:
                    os.rmdir(dp)
                except OSError:
                    pass

    return True, len(only_in_src), len(diffs), len(only_in_tgt)


def sync_all(dry_run=False, targets=None):
    source_dir = SOURCE_SKILLS_DIR
    target_dirs = targets or DEFAULT_TARGETS

    print("=" * 75)
    print(f"[*] Multi-Platform Skills Sync Engine ({len(target_dirs)}-Replica Mirror)")
    print(f"[*] Source (Sole Truth): {source_dir}")
    print(f"[*] Mode: {'DRY RUN (Diff Report Only)' if dry_run else 'APPLY MIRROR SYNC'}")
    print("=" * 75)

    if not os.path.exists(source_dir):
        print(f"[-] Source directory not found: {source_dir}", file=sys.stderr)
        return False

    skills = get_source_skills(source_dir)
    print(f"[+] Found {len(skills)} managed skills in source: {', '.join(skills)}")

    all_ok = True
    total_added = 0
    total_updated = 0
    total_removed = 0

    for target_dir in target_dirs:
        print("\n" + "-" * 75)
        print(f"[*] Target replica: {target_dir}")
        if not os.path.exists(target_dir):
            if dry_run:
                print(f"    [NOTICE] Target directory does not exist yet (will be created on sync).")
            else:
                os.makedirs(target_dir, exist_ok=True)
                print(f"    [OK] Created target directory: {target_dir}")

        for skill in skills:
            src_p = os.path.join(source_dir, skill)
            tgt_p = os.path.join(target_dir, skill)

            only_src, only_tgt, diffs, same = compare_trees(src_p, tgt_p)

            if not only_src and not only_tgt and not diffs:
                print(f"  [OK] {skill:<28} -> identical ({len(same)} files)")
                continue

            print(f"  [*] {skill:<28} -> DIFF DETECTED:")
            if only_src:
                print(f"      + Missing in target ({len(only_src)}): {', '.join(only_src[:5])}{'...' if len(only_src)>5 else ''}")
            if diffs:
                print(f"      ~ Modified ({len(diffs)}): {', '.join(diffs[:5])}{'...' if len(diffs)>5 else ''}")
            if only_tgt:
                print(f"      - Extra in target ({len(only_tgt)}): {', '.join(only_tgt[:5])}{'...' if len(only_tgt)>5 else ''}")

            ok, n_add, n_upd, n_del = sync_skill(src_p, tgt_p, dry_run=dry_run)
            total_added += n_add
            total_updated += n_upd
            total_removed += n_del
            if not ok:
                all_ok = False

            if not dry_run:
                # 校验同步后一致性
                v_src, v_tgt, v_diff, _ = compare_trees(src_p, tgt_p)
                if v_src or v_tgt or v_diff:
                    print(f"      [-] VERIFICATION FAILED after sync for {skill}!", file=sys.stderr)
                    all_ok = False
                else:
                    print(f"      [OK] Synced & verified identical.")

        # Root-level configuration files (e.g., requirements.txt)
        root_files = ["requirements.txt"]
        for rf in root_files:
            rf_src = os.path.join(source_dir, rf)
            rf_tgt = os.path.join(target_dir, rf)
            if os.path.exists(rf_src):
                if not os.path.exists(rf_tgt) or not filecmp.cmp(rf_src, rf_tgt, shallow=False):
                    print(f"  [*] {rf:<28} -> DIFF DETECTED (root file)")
                    if not dry_run:
                        shutil.copy2(rf_src, rf_tgt)
                        print(f"      [OK] Synced root file {rf}")
                    total_updated += 1
                else:
                    print(f"  [OK] {rf:<28} -> identical")

        # Root-level shared test suites and tools (e.g. tests/)
        shared_dirs = ["tests"]
        for sd in shared_dirs:
            sd_src = os.path.join(source_dir, sd)
            sd_tgt = os.path.join(target_dir, sd)
            if os.path.exists(sd_src):
                only_src, only_tgt, diffs, same = compare_trees(sd_src, sd_tgt)
                if not only_src and not only_tgt and not diffs:
                    print(f"  [OK] {sd:<28} -> identical ({len(same)} files)")
                    continue
                print(f"  [*] {sd:<28} -> DIFF DETECTED (shared dir):")
                if only_src:
                    print(f"      + Missing in target ({len(only_src)}): {', '.join(only_src[:5])}{'...' if len(only_src)>5 else ''}")
                if diffs:
                    print(f"      ~ Modified ({len(diffs)}): {', '.join(diffs[:5])}{'...' if len(diffs)>5 else ''}")
                if only_tgt:
                    print(f"      - Extra in target ({len(only_tgt)}): {', '.join(only_tgt[:5])}{'...' if len(only_tgt)>5 else ''}")
                ok, n_add, n_upd, n_del = sync_skill(sd_src, sd_tgt, dry_run=dry_run)
                total_added += n_add
                total_updated += n_upd
                total_removed += n_del
                if not ok:
                    all_ok = False
                if not dry_run:
                    v_src, v_tgt, v_diff, _ = compare_trees(sd_src, sd_tgt)
                    if v_src or v_tgt or v_diff:
                        print(f"      [-] VERIFICATION FAILED after sync for {sd}!", file=sys.stderr)
                        all_ok = False
                    else:
                        print(f"      [OK] Synced & verified identical.")

    print("\n" + "=" * 75)
    print(f"[*] Summary: added={total_added}, updated={total_updated}, removed={total_removed}")
    if all_ok:
        print(f"[OK] {len(target_dirs)}-replica synchronization successful and verified identical!")
    else:
        print(f"[-] Synchronization completed with errors.", file=sys.stderr)
    print("=" * 75)

    return all_ok


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-platform skills synchronization tool")
    parser.add_argument("--dry-run", action="store_true", help="Report differences without modifying targets")
    parser.add_argument("--target", action="append", help="Custom target directory (can specify multiple)")
    args = parser.parse_args()

    success = sync_all(dry_run=args.dry_run, targets=args.target)
    sys.exit(0 if success else 1)
