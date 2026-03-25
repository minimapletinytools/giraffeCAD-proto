#!/usr/bin/env python3
"""Test script to verify Float conversion in dimension constructors."""

from code_goes_here.rule import inches, feet, mm, cm, m, shaku, sun, bu, degrees, radians
from sympy import Float

def test_dimension_constructors():
    """Test that all dimension constructors return Float."""
    tests = [
        ("inches(3)", inches(3)),
        ("feet(8)", feet(8)),
        ("mm(90)", mm(90)),
        ("cm(9)", cm(9)),
        ("m(1)", m(1)),
        ("shaku(1)", shaku(1)),
        ("sun(1)", sun(1)),
        ("bu(1)", bu(1)),
        ("degrees(90)", degrees(90)),
        ("radians(3.14159)", radians(3.14159)),
    ]
    
    print("Testing dimension constructors:")
    all_float = True
    for name, value in tests:
        is_float = isinstance(value, Float)
        status = "✓" if is_float else "✗"
        print(f"  {status} {name}: {type(value).__name__} = {value}")
        all_float = all_float and is_float
    
    print(f"\nAll values are Float: {all_float}")
    return all_float

if __name__ == "__main__":
    success = test_dimension_constructors()
    exit(0 if success else 1)
