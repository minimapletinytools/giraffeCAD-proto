# GiraffeCAD

A Python library for programmatic timber frame design with Fusion 360 integration.

## Overview

GiraffeCAD is a timber framing design library that allows you to:
- Create timber structures programmatically using Python
- Define complex joints (mortise and tenon, etc.)
- Visualize designs in Autodesk Fusion 360
- Generate precise cutting instructions

The library uses SymPy for mathematical operations and includes a custom `Orientation` class for 3D rotations.

## Development Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd giraffeCAD-proto
```

### 2. Create and Activate Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Development Dependencies

```bash
pip install pytest
```

## Running Tests

To run the test suite:

```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Run all tests
./venv/bin/python -m pytest tests/ -v

# Or run specific test files
./venv/bin/python -m pytest tests/test_giraffe.py -v
./venv/bin/python -m pytest tests/test_moothymoth.py -v
```

The test suite includes:
- **Vector and matrix operations** - Testing SymPy-based vector math
- **Orientation class** - Testing 3D rotation matrices and Euler angles
- **Timber creation** - Testing timber geometry and positioning
- **Joint construction** - Testing mortise and tenon joint generation
- **Random testing** - Using randomly generated orientations to verify mathematical properties

## Running the Sawhorse Example

### Basic Python Example

```bash
# Activate virtual environment
source venv/bin/activate

# Run the sawhorse example
python sawhorse_example.py
```

This will create a sawhorse structure with all timbers and joints, printing a summary of the generated components.

### Fusion 360 Integration

To render the sawhorse example in Autodesk Fusion 360:

#### 1. Setup Fusion 360 Script Environment

1. Navigate to the `giraffetest/` directory in the project
2. Install local dependencies for Fusion 360's isolated Python environment:

```bash
cd giraffetest
pip install --target libs sympy
```

#### 2. Add Script to Fusion 360

1. Open Autodesk Fusion 360
2. Go to **Design** workspace
3. Click **Utilities** → **ADD-INS** → **Scripts and Add-Ins** (or just `s` and type in "scripts and add-ins")
4. Click the **+** button next to "My Scripts"
5. Navigate to the `giraffetest/` folder and select it
6. You should now see "giraffetest" in your scripts list

#### 3. Run the Script

1. Select "giraffetest" from the scripts list
2. Click **Run**
3. The script will:
   - Clear any existing design
   - Generate the sawhorse geometry using `sawhorse_example.py`
   - Render all timbers as 3D components in Fusion 360
   - Apply proper transformations and positioning

#### 4. What You'll See

The script creates a complete sawhorse with:
- **Left Mudsill** - Bottom support beam (left side)
- **Right Mudsill** - Bottom support beam (right side) 
- **Top Beam** - Horizontal work surface
- **Left Post** - Vertical support connecting mudsill to beam
- **Right Post** - Vertical support connecting mudsill to beam
- **Stretcher** - Horizontal cross-brace between posts

Each timber is rendered as a separate component with:
- Correct dimensions and cross-sections
- Proper 3D positioning and orientation
- Material assignment (wood)
- Named components for easy identification

#### 5. Troubleshooting Fusion 360

If you encounter issues:

1. **Import errors**: Ensure `sympy` is installed in the `libs/` directory
2. **Path issues**: The script uses dynamic path importing to load GiraffeCAD modules
3. **Permission errors**: Make sure Fusion 360 has access to the script directory
4. **Python version**: Fusion 360 uses its own Python environment

Check the Fusion 360 console for detailed error messages.

## Project Structure

```
giraffeCAD-proto/
├── giraffe.py              # Core timber framing library
├── moothymoth.py           # 3D orientation/rotation class
├── sawhorse_example.py     # Complete sawhorse example
├── requirements.txt        # Python dependencies
├── tests/                  # Test suite
│   ├── test_giraffe.py
│   └── test_moothymoth.py
└── giraffetest/           # Fusion 360 integration
    ├── giraffetest.py     # Main Fusion 360 script
    ├── giraffe_render_fusion360.py  # Fusion 360 rendering
    ├── test_local.py      # Local testing script
    ├── libs/              # Local dependencies for Fusion 360
    └── README.md          # Fusion 360 specific documentation
```

## Core Concepts

### Timbers
- Defined by length, cross-sectional size, position, and orientation
- Support naming for easy identification
- Can be extended, joined, and cut with joints

### Orientations
- 3D rotations using SymPy matrices
- Support for Euler angles (ZYX sequence)
- Cardinal direction constants (north, south, east, west, up, down)

### Joints
- Mortise and tenon joints with customizable dimensions
- Support for multiple timber connections
- Automatic cut operation generation

### Coordinate System
- Right-hand coordinate system
- Z-up (vertical), Y-north, X-east
- All measurements in meters

## Dependencies

- **SymPy** (≥1.12.0) - Symbolic mathematics and matrix operations
- **Pytest** - Testing framework (development only)

## License

See LICENSE file for details.
