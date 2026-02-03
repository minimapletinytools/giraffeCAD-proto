#!/bin/bash
# Installation script for Horsey Viewer extension

echo "🐴 Installing Horsey Viewer extension..."

# Determine the extension directory
if [ -d "$HOME/.cursor/extensions" ]; then
    EXT_DIR="$HOME/.cursor/extensions/horsey-viewer"
    EDITOR="Cursor"
elif [ -d "$HOME/.vscode/extensions" ]; then
    EXT_DIR="$HOME/.vscode/extensions/horsey-viewer"
    EDITOR="VSCode"
else
    echo "❌ Could not find VSCode or Cursor extensions directory"
    echo "Creating VSCode extensions directory..."
    mkdir -p "$HOME/.vscode/extensions"
    EXT_DIR="$HOME/.vscode/extensions/horsey-viewer"
    EDITOR="VSCode"
fi

echo "Installing to: $EXT_DIR"

# Create directory and copy files
mkdir -p "$EXT_DIR"
cp -r . "$EXT_DIR/"

# Clean up unnecessary files in the extension directory
rm -f "$EXT_DIR/install.sh"
rm -f "$EXT_DIR/test-frame.py"
rm -rf "$EXT_DIR/.vscode"

echo "✅ Horsey Viewer installed successfully!"
echo ""
echo "Next steps:"
echo "1. Reload $EDITOR: Cmd+Shift+P → 'Developer: Reload Window'"
echo "2. Open a Python file with a build_frame() function"
echo "3. Run command: 'Render Horsey'"
echo ""
echo "Test file available at: $(pwd)/test-frame.py"
