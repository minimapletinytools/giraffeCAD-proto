# Giraffe

A library for programmatic timber frame CAD design. It can integrate with my CAD applications or output to IFC format.

Giraffe is written as an **agent friendly** library meaning it was designed to be easily understood and used by agents. 

## Integrations and formats

- **Fusion 360** - Full CSG support with feature-based modeling
- **FreeCAD** - Full CSG support with direct shape creation
- **Rhino** - Basic geometry support (WIP)
- **Blender** - Planned
- **IFC file format** - Planned

## Quick Start

```bash
# Clone and setup (only first time)
git clone <repository-url>
cd giraffeCAD-proto
./setup_dev.sh

# Activate venv (each time you reopen the terminal)
source venv/bin/activate

# Run tests
python3 -m pytest code_goes_here/ -v
```

## Development Setup

### 1. Clone the Repository

Currently, the best/easiest way to use Giraffe is to clone the repo. Dependencies are managed locally in the repo which makes it a lot easier for most CAD scripting interfaces.

```bash
git clone <repository-url>
cd giraffeCAD-proto
```

**Note:** The project uses Python 3.9.6. If you use `pyenv`, it will automatically use the correct version from `.python-version`.

### 2. Create and Activate Virtual Environment

For local development and testing, it's recommended to use a virtual environment:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Quick Setup:** You can also use the provided setup script:

```bash
./setup_dev.sh

# Or use make
make setup
```

### Note on CAD Integrations

The virtual environment is **only for local development and testing**. When using Giraffe with CAD applications, those programs use their own Python environments:

- **Fusion 360**: Uses embedded Python with bundled libraries in `fusion360/libs/`
- **Rhino**: Uses RhinoPython environment
- **Local testing**: Uses your venv

This is why dependencies are also vendored in `fusion360/libs/` for CAD environments. The venv setup does not affect CAD integrations.

## Running Tests

### Quick Commands

If you have `make` installed:

```bash
make test           # Run all tests
make test-verbose   # Run tests with verbose output
make test-cov       # Run tests with coverage report
```

### Manual Testing

To run the test suite manually:

```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Run all tests
python3 -m pytest code_goes_here/ -v

# Or run specific test files
python3 -m pytest code_goes_here/test_moothymoth.py -v

# Run with coverage
python3 -m pytest code_goes_here/ --cov=code_goes_here --cov-report=html
```

### Automatic Testing (Recommended for Development)

For continuous development, you can have tests run automatically whenever you save changes to your code:

```bash
# Install pytest-watch (one-time setup)
pip install pytest-watch

# Activate venv
source venv/bin/activate 

# Start automatic testing - watches all Python files and runs tests on changes
ptw code_goes_here/
```

**How it works:**
- `ptw` (pytest-watch) monitors your Python files for changes
- When you save a file, it automatically runs the test suite
- Shows immediate feedback as you develop
- Press `Ctrl+C` to stop the auto-testing

## Development Workflow

### Makefile Commands

The project includes a `Makefile` with common development tasks:

```bash
make help          # Show all available commands
make setup         # Setup development environment
make test          # Run all tests
make test-verbose  # Run tests with verbose output
make test-cov      # Run tests with coverage report
make clean         # Remove build artifacts and cache files
```

### Cleaning Build Artifacts

To clean up Python cache files and test artifacts:

```bash
make clean

# Or manually:
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
rm -rf htmlcov/ .coverage .pytest_cache/
```

### Activating/Deactivating Virtual Environment

```bash
# Activate (do this each time you open a new terminal)
source venv/bin/activate

# Your prompt will change to show (venv)
# Now all python/pip commands use the venv

# Deactivate when done
deactivate
```

## Trying out Examples

### FreeCAD Integration

To render structures in FreeCAD (open source, free):

1. **Install FreeCAD** (version 0.19 or later)
   - Download from https://www.freecad.org/
   - Or use package manager: `brew install freecad` (macOS)

2. **Set up macro folder** (one-time setup):
   - Open FreeCAD
   - Go to **Edit** → **Preferences** → **Python** → **Macro**
   - Click **Add** under "Macro path"
   - Navigate to and select: `/path/to/giraffeCAD-proto/freecad`
   - Click **OK**

3. **Run the renderer**:
   - Open FreeCAD
   - Go to **Macro** → **Macros...**
   - Select `render_example.py` from the list
   - Click **Execute**
   
   The rendered structure will appear in FreeCAD's 3D view!

### Fusion 360 Integration

To render the example in Autodesk Fusion 360:

#### 1. Setup Fusion 360 Script Environment

1. Navigate to the `fusion360/` directory in the project
2. Install local dependencies for Fusion 360's isolated Python environment:

```bash
cd fusion360
pip install --target libs sympy
```

#### 2. Add Script to Fusion 360

1. Open Autodesk Fusion 360
2. Go to **Design** workspace
3. Click **Utilities** → **ADD-INS** → **Scripts and Add-Ins** (or just `s` and type in "scripts and add-ins")
4. Click the **+** button next to "My Scripts"
5. Navigate to the `fusion360/` folder and select it
6. You should now see "giraffetest" in your scripts list

#### 3. Run the Script

1. Select "giraffetest" from the scripts list
2. Click **Run**
3. The script will:
   - Clear any existing design
   - Generate the sawhorse geometry using your selected example
   - Render all timbers as 3D components in Fusion 360
   - Apply proper transformations and positioning

#### 4. What You'll See

TODO

#### 5. Troubleshooting Fusion 360

If you encounter issues:

1. **Import errors**: Ensure `sympy` is installed in the `libs/` directory
2. **Path issues**: The script uses dynamic path importing to load GiraffeCAD modules
3. **Permission errors**: Make sure Fusion 360 has access to the script directory
4. **Python version**: Fusion 360 uses its own Python environment

Check the Fusion 360 console for detailed error messages.

### Rhino Integration

The Rhino renderer currently supports basic geometry but does not yet support CSG operations (joints/cuts). See [`rhino/README.md`](rhino/README.md) for current capabilities and usage.

## Architecture

GiraffeCAD uses a modular architecture with shared utilities across rendering backends:

```
code_goes_here/
├── timber.py              # Core timber and joint data structures
├── meowmeowcsg.py        # CSG (Constructive Solid Geometry) operations
├── moothymoth.py         # Orientation and rotation utilities
├── rendering_utils.py    # Shared rendering utilities (NEW!)
└── basic_joints.py       # Joint construction functions

fusion360/
└── giraffe_render_fusion360.py   # Fusion 360 renderer

freecad/
└── giraffe_render_freecad.py     # FreeCAD renderer (NEW!)

rhino/
└── giraffe_render_rhino.py       # Rhino renderer (basic)
```

### Shared Rendering Utilities

The `rendering_utils.py` module provides common functions used across all rendering backends:
- SymPy to float conversion
- Structure extent calculation (for sizing infinite geometry)
- Coordinate transformations
- Timber corner calculations

This minimizes code duplication and ensures consistent behavior across different CAD platforms.
