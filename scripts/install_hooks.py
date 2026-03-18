#!/usr/bin/env python3
"""
install_hooks.py — Install local Git hooks for skill registry governance.

Installs:
  pre-push   — blocks direct push to master/main; requires going through
               incoming/** → PR workflow instead.
  commit-msg — warns if a commit message is missing a conventional prefix.

Usage:
    python scripts/install_hooks.py
    python scripts/install_hooks.py --uninstall
"""

import sys
import stat
import argparse
from pathlib import Path

REPO_ROOT  = Path(__file__).parent.parent
HOOKS_DIR  = REPO_ROOT / ".git" / "hooks"

# ── Hook content ──────────────────────────────────────────────────────────────

PRE_PUSH_HOOK = """\
#!/usr/bin/env bash
# pre-push hook — installed by scripts/install_hooks.py
#
# Blocks direct push to master/main.
# Enforces the three-layer CI workflow:
#   1. Push to incoming/**          (Layer 1 pre-check)
#   2. Open PR to master            (Layer 2 admission gate)
#   3. Merge via PR                 (Layer 3 post-merge)

PROTECTED_BRANCHES="master main"
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
REMOTE=$1

for branch in $PROTECTED_BRANCHES; do
    if [ "$CURRENT_BRANCH" = "$branch" ]; then
        echo ""
        echo "  [pre-push] Direct push to '$branch' is not allowed."
        echo ""
        echo "  The skill registry uses a three-layer CI workflow:"
        echo "    1. Push your changes to:  incoming/<your-feature>"
        echo "       git push origin HEAD:incoming/<your-feature>"
        echo "    2. Open a Pull Request to master on GitHub."
        echo "       The Admission Gate will run automatically."
        echo "    3. Merge only when CI passes."
        echo ""
        echo "  To bypass this check (emergency only):"
        echo "    git push --no-verify"
        echo ""
        exit 1
    fi
done

exit 0
"""

COMMIT_MSG_HOOK = """\
#!/usr/bin/env bash
# commit-msg hook — installed by scripts/install_hooks.py
#
# Warns (does not block) if commit message lacks a conventional prefix.

COMMIT_MSG_FILE=$1
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

PREFIXES="feat fix refactor docs test chore ci style perf build revert"
FIRST_LINE=$(echo "$COMMIT_MSG" | head -1)

has_prefix=false
for prefix in $PREFIXES; do
    if echo "$FIRST_LINE" | grep -qE "^${prefix}[(].*[)]:"; then
        has_prefix=true
        break
    fi
done

# Also allow merge commits and [skip ci] commits
if echo "$FIRST_LINE" | grep -qE "^(Merge|Revert|chore:.*\\[skip ci\\])"; then
    has_prefix=true
fi

if [ "$has_prefix" = "false" ]; then
    echo ""
    echo "  [commit-msg] Warning: commit message does not follow Conventional Commits."
    echo "  Expected: feat|fix|refactor|docs|test|chore|ci(<scope>): <description>"
    echo "  Got:      $FIRST_LINE"
    echo "  (This is a warning only — commit will proceed.)"
    echo ""
fi

exit 0
"""


# ── Installer ─────────────────────────────────────────────────────────────────

def install_hook(name: str, content: str):
    path = HOOKS_DIR / name
    path.write_text(content, encoding="utf-8")
    # Make executable (chmod +x)
    current = path.stat().st_mode
    path.chmod(current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"  [OK] Installed {path}")


def uninstall_hook(name: str):
    path = HOOKS_DIR / name
    if path.exists():
        path.unlink()
        print(f"  [OK] Removed {path}")
    else:
        print(f"  [--] Not found: {path}")


def main():
    parser = argparse.ArgumentParser(description="Install/uninstall Git hooks")
    parser.add_argument("--uninstall", action="store_true",
                        help="Remove installed hooks")
    args = parser.parse_args()

    if not HOOKS_DIR.exists():
        print(f"ERROR: .git/hooks not found at {HOOKS_DIR}")
        print("       Are you running this from the repository root?")
        sys.exit(1)

    hooks = [
        ("pre-push",   PRE_PUSH_HOOK),
        ("commit-msg", COMMIT_MSG_HOOK),
    ]

    if args.uninstall:
        print("\nUninstalling Git hooks...")
        for name, _ in hooks:
            uninstall_hook(name)
    else:
        print("\nInstalling Git hooks...")
        for name, content in hooks:
            # Back up existing hook if present and not ours
            existing = HOOKS_DIR / name
            if existing.exists():
                text = existing.read_text(encoding="utf-8", errors="replace")
                if "install_hooks.py" not in text:
                    backup = HOOKS_DIR / f"{name}.bak"
                    backup.write_text(text)
                    print(f"  [bak] Backed up existing hook to {backup}")
            install_hook(name, content)

    print()
    print("Done.")
    print()
    if not args.uninstall:
        print("  pre-push:   blocks direct push to master/main")
        print("              use 'git push origin HEAD:incoming/<branch>' instead")
        print("  commit-msg: warns on non-conventional commit messages")
        print()
        print("  To bypass (emergency): git push --no-verify")
        print("  To uninstall:          python scripts/install_hooks.py --uninstall")
    print()


if __name__ == "__main__":
    main()
