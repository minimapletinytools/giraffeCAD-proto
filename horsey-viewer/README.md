# Horsey Viewer - VSCode Extension for GiraffeCAD

A VSCode extension for viewing timber frame structures created with GiraffeCAD.

WIP WIP WIP

## Features

- **Render Horsey** command: Import and visualize timber frames from Python files
- Automatically calls the `build_frame()` function in your Python file
- Displays frame data in a formatted webview
- Shows timber details, accessories, and complete structure information

## Usage

1. Open a Python file that defines a `build_frame()` function returning a `Frame` object
2. Run the command: **Render Horsey** (via Command Palette: Cmd+Shift+P / Ctrl+Shift+P)
3. View the rendered frame data in a new panel

> **Note:** Originally wanted to use `raise()` (as in "raising a frame" in timber framing), but that's a Python keyword, so we use `build_frame()` instead.

## Requirements

- Python 3.6+
- GiraffeCAD library must be importable from your Python file

## Installation

1. Copy the `horsey-viewer` directory to your VSCode extensions folder:
   - macOS/Linux: `~/.vscode/extensions/`
   - Windows: `%USERPROFILE%\.vscode\extensions\`

2. Reload VSCode

Or install from source:

```bash
cd horsey-viewer
npm install
```

Then press F5 in VSCode to launch the extension in development mode.

## Example

Create a Python file with a `build_frame()` function:

```python
from code_goes_here.timber import *
from code_goes_here.construction import *

def build_frame():
    timber1 = create_timber(
        bottom_position=create_v3(0, 0, 0),
        length=mm(1000),
        size=create_v2(mm(100), mm(100)),
        length_direction=create_v3(0, 0, 1),
        width_direction=create_v3(1, 0, 0),
        name="Test Timber"
    )

    frame = Frame.from_joints([], [timber1], name="Test Frame")
    return frame
```

Run **Render Horsey** to see the frame!

You can also use the included `test-frame.py` for testing.

## Development

This extension is part of the GiraffeCAD project for timber frame design and visualization.

## Roadmap

- [ ] Add Three.js 3D visualization
- [ ] Interactive timber inspection
- [ ] Export to various CAD formats
- [ ] Real-time preview on file changes
