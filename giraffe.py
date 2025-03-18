"""filename.py

   First FreeCAD Script

"""

import FreeCAD
from FreeCAD import Placement, Rotation, Vector
import FreeCADGui

DOC_NAME = "Wiki_Example"
#DOC = FreeCAD.newDocument(DOC_NAME)
#FreeCAD.setActiveDocument(DOC.Name)
DOC = FreeCAD.activeDocument()

ROT0 = Rotation(0, 0, 0)
VEC0 = Vector(0, 0, 0)

# Helper function

def set_view():
    """Rearrange View."""
    if not FreeCAD.GuiUp:
        return
    doc = FreeCADGui.ActiveDocument
    if doc is None:
        return
    view = doc.ActiveView
    if view is None:
        return
    # Check if the view is a 3D view:
    if not hasattr(view, "getSceneGraph"):
        return
    view.viewAxometric()
    view.fitAll()

# Script functions

def my_box(name, len, wid, hei):
    """Create a box."""
    obj_b = DOC.addObject("Part::Box", name)
    obj_b.Length = len
    obj_b.Width = wid
    obj_b.Height = hei

    DOC.recompute()

    return obj_b

def my_cyl(name, ang, rad, hei):
    """Create a Cylinder."""
    obj = DOC.addObject("Part::Cylinder", name)
    obj.Angle = ang
    obj.Radius = rad
    obj.Height = hei

    DOC.recompute()

    return obj

def fuse_obj(name, obj_0, obj_1):
    """Fuse two objects."""
    obj = DOC.addObject("Part::Fuse", name)
    obj.Base = obj_0
    obj.Tool = obj_1
    obj.Refine = True
    DOC.recompute()

    return obj


print("poop")
print("Creating a box meow meow")
obj1 = my_box("test_cube", 5, 5, 5)
obj2 = my_cyl("test_cyl", 360, 2.5, 5)
obj3 = fuse_obj("test_fuse", obj1, obj2)woo

set_view()
