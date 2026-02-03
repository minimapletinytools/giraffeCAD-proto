#!/usr/bin/env python3
"""
Runner script for Horsey Viewer VSCode extension.
Imports a Python file, calls its 'raise' function, and serializes the Frame to JSON.
"""

import sys
import os
import json
import importlib.util
from pathlib import Path

def serialize_sympy(obj):
    """Convert Sympy objects to strings for JSON serialization."""
    # Handle Sympy Rational, Integer, etc.
    if hasattr(obj, 'evalf'):
        return str(obj)
    elif hasattr(obj, '__float__'):
        try:
            return float(obj)
        except:
            return str(obj)
    return str(obj)

def serialize_vector(vec):
    """Serialize a Sympy Matrix (vector) to a list."""
    if vec is None:
        return None
    try:
        # Convert matrix to list of floats
        return [serialize_sympy(vec[i, 0]) for i in range(vec.shape[0])]
    except:
        return str(vec)

def serialize_frame(frame):
    """
    Serialize a Frame object to a JSON-compatible dictionary.

    Args:
        frame: Frame object with cut_timbers and accessories

    Returns:
        dict: JSON-serializable representation of the Frame
    """

    frame_data = {
        'name': frame.name if hasattr(frame, 'name') else None,
        'timber_count': len(frame.cut_timbers),
        'accessories_count': len(frame.accessories) if hasattr(frame, 'accessories') else 0,
        'timbers': [],
        'accessories': []
    }

    # Serialize each cut timber
    for cut_timber in frame.cut_timbers:
        timber = cut_timber.timber

        timber_data = {
            'name': timber.name if hasattr(timber, 'name') else None,
            'length': serialize_sympy(timber.length),
            'width': serialize_sympy(timber.size[0, 0]),
            'height': serialize_sympy(timber.size[1, 0]),
            'bottom_position': serialize_vector(timber.get_bottom_position_global()),
            'length_direction': serialize_vector(timber.get_length_direction_global()),
            'width_direction': serialize_vector(timber.get_width_direction_global()),
            'height_direction': serialize_vector(timber.get_height_direction_global()),
            'cuts_count': len(cut_timber.cuts) if hasattr(cut_timber, 'cuts') else 0,
            'end_cuts': {
                'top': cut_timber.end_cuts[0] is not None if hasattr(cut_timber, 'end_cuts') else False,
                'bottom': cut_timber.end_cuts[1] is not None if hasattr(cut_timber, 'end_cuts') else False
            }
        }

        frame_data['timbers'].append(timber_data)

    # Serialize accessories
    if hasattr(frame, 'accessories'):
        for accessory in frame.accessories:
            acc_data = {
                'type': type(accessory).__name__,
                'details': {}
            }

            # Try to extract common accessory attributes
            if hasattr(accessory, 'position'):
                acc_data['details']['position'] = serialize_vector(accessory.position)
            if hasattr(accessory, 'orientation'):
                acc_data['details']['orientation'] = str(accessory.orientation)
            if hasattr(accessory, 'size'):
                acc_data['details']['size'] = serialize_sympy(accessory.size)
            if hasattr(accessory, 'shape'):
                acc_data['details']['shape'] = str(accessory.shape)

            frame_data['accessories'].append(acc_data)

    return frame_data

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'No Python file path provided'}))
        sys.exit(1)

    file_path = sys.argv[1]

    # Check if file exists
    if not os.path.exists(file_path):
        print(json.dumps({'error': f'File not found: {file_path}'}))
        sys.exit(1)

    try:
        # Get the module name from the file path
        module_name = Path(file_path).stem

        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            print(json.dumps({'error': f'Could not load module from {file_path}'}))
            sys.exit(1)

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Check if the module has a 'build_frame' function
        # (originally wanted 'raise' but that's a Python keyword)
        if not hasattr(module, 'build_frame'):
            print(json.dumps({'error': 'Module does not have a "build_frame" function'}))
            sys.exit(1)

        # Call the build_frame function
        frame = module.build_frame()

        # Check if it returned a Frame object
        if not hasattr(frame, 'cut_timbers'):
            print(json.dumps({'error': 'The "raise" function did not return a valid Frame object'}))
            sys.exit(1)

        # Serialize the frame to JSON
        frame_data = serialize_frame(frame)

        # Output as JSON
        print(json.dumps(frame_data, indent=2))

    except Exception as e:
        import traceback
        error_data = {
            'error': str(e),
            'traceback': traceback.format_exc()
        }
        print(json.dumps(error_data))
        sys.exit(1)

if __name__ == '__main__':
    main()
