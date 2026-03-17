#!/bin/bash
# Installation script for Horsey Viewer extension

echo "🐴 Installing Horsey Viewer extension..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

VSCODE_EXT_DIR="$HOME/.vscode/extensions/horsey-viewer"
CURSOR_EXT_DIR="$HOME/.cursor/extensions/horsey-viewer"

#TARGETS=("$VSCODE_EXT_DIR" "$CURSOR_EXT_DIR")
#EDITORS=("VSCode" "Cursor")
TARGETS=("$CURSOR_EXT_DIR")
EDITORS=("Cursor")


for i in "${!TARGETS[@]}"; do
    EXT_DIR="${TARGETS[$i]}"
    EDITOR="${EDITORS[$i]}"

    echo "Installing to $EDITOR: $EXT_DIR"
    mkdir -p "$EXT_DIR"

    cp -R "$SCRIPT_DIR"/. "$EXT_DIR"/

    rm -f "$EXT_DIR/install.sh"
    rm -f "$EXT_DIR/test-frame.py"
    rm -rf "$EXT_DIR/.vscode"
done

echo "✅ Horsey Viewer installed successfully in VSCode and Cursor!"
echo ""
echo "Next steps:"
echo "1. Reload VSCode and Cursor: Cmd+Shift+P → 'Developer: Reload Window'"
echo "2. Open a Python file with a build_frame() function"
echo "3. Run command: 'Render Horsey'"
echo ""
echo "Test file available at: $SCRIPT_DIR/test-frame.py"
