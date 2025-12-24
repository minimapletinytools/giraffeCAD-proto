# Giraffe

A library for programmatic timber frame CAD design. It can integrate with my CAD applications or output to IFC format.

Giraffe is written as an **agent friendly** library meaning it was designed to be easily understood and used by agents. 

## Integrations and formats

- Fusion 360
- Rhino (WIP)
- Bledner (WIP)
- IFC file format (WIP)


## Development Setup

### 1. Clone the Repository

Currently, the best/easiest way to use Giraffe is to clone the repo. Dependencies are managed locally in the repo which is makes it a lot easier for most CAD scripting interfaces.

```bash
git clone <repository-url>
cd giraffeCAD-proto
```

### 2. Create and Activate Virtual Environment  (TODO add support)

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

## Running Tests

### One-Time Testing

To run the test suite once:

```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Run all tests
python -m pytest code_goes_here/ -v

# Or run specific test files
python -m pytest code_goes_here/test_moothymoth.py -v
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



## Trying out Examples

TODO

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
