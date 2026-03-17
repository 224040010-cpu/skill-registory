#!/bin/bash
# Install Cursor skills from this repo

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$HOME/.cursor/skills"

echo "=== Cursor Skills Setup ==="
echo ""
echo "Source: $SCRIPT_DIR"
echo "Target: $SKILLS_DIR"
echo ""

# Create target directory
mkdir -p "$SKILLS_DIR"

# Count skills to install
SKILL_COUNT=$(find "$SCRIPT_DIR" -maxdepth 1 -type d ! -name ".*" ! -name "$(basename "$SCRIPT_DIR")" | wc -l)

# Copy all skill directories (skip files like README.md, setup.sh)
for skill in "$SCRIPT_DIR"/*/; do
    if [ -d "$skill" ]; then
        skill_name=$(basename "$skill")
        echo "Installing: $skill_name"
        cp -r "$skill" "$SKILLS_DIR/"
    fi
done

echo ""
echo "=== Installed $SKILL_COUNT skills ==="
echo ""
echo "Skills are now available in Cursor IDE."
echo ""
echo "Quick test - ask Claude:"
echo '  "What skills are available for EV charger development?"'
echo ""
echo "Done!"
