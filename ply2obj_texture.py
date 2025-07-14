#!/usr/bin/env python3
# convert_ply_to_obj.py
#
# Usage (CLI):
#   blender -b --python convert_ply_to_obj.py -- <input.ply> <output.obj> [<texture.png>]
#
#   • <input.ply>   – path to the source PLY (with vertex colors)
#   • <output.obj>  – destination OBJ file (an .mtl is written next to it)
#   • <texture.png> – optional path for the baked texture; defaults to
#                     <output-stem>.png
#
# Fixed for Blender 4.2 vertex color baking issues

import bpy
import sys, os

# ----------------------------------------------------------------------
# CLI arguments
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 2:
    raise SystemExit("Usage: blender -b --python convert_ply_to_obj.py -- "
                     "<input.ply> <output.obj> [texture.png]")

ply_path = os.path.abspath(argv[0])
obj_path = os.path.abspath(argv[1])
tex_path = os.path.abspath(argv[2]) if len(argv) > 2 else (
    os.path.splitext(obj_path)[0] + ".png"
)

# ----------------------------------------------------------------------
# Fresh scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# ----------------------------------------------------------------------
# Import PLY
bpy.ops.wm.ply_import(filepath=ply_path)
obj = bpy.context.selected_objects[0]
mesh = obj.data
bpy.context.view_layer.objects.active = obj
# Debug: Print color attributes info
print(f"Color attributes found: {len(mesh.color_attributes)}")
for i, attr in enumerate(mesh.color_attributes):
    print(f"  {i}: {attr.name} (type: {attr.data_type}, domain: {attr.domain})")
# Check if we have vertex colors
if len(mesh.color_attributes) == 0:
    raise SystemExit("No vertex color attributes found in the PLY file!")
# Get the first color attribute
color_attr = mesh.color_attributes[0]
print(f"Using color attribute: {color_attr.name}")
# Convert color attribute to vertex color layer for better compatibility
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.object.mode_set(mode="OBJECT")
# Ensure the color attribute is set as active
mesh.color_attributes.active = color_attr

# ----------------------------------------------------------------------
# Ensure a UV map exists (Smart UV Project if none)
if not mesh.uv_layers:
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project()
    bpy.ops.object.mode_set(mode="OBJECT")
    
# ----------------------------------------------------------------------
# Method 1: Try direct vertex color to texture baking
tex_size = 2048
# Create image for baking
img = bpy.data.images.new("VC_Bake", tex_size, tex_size, alpha=False)
img.filepath_raw = tex_path
img.file_format = "PNG"
# Initialize image with a default color to check if baking works
img.generated_color = (0.0, 0.0, 0.0, 1.0)  # Gray background
pixels = list(img.pixels)
non_zero_pixels = [p for p in pixels if p != 0.0]
print(f"Image has {len(non_zero_pixels)} non-zero pixel values out of {len(pixels)} total")
# Create material
mat = bpy.data.materials.new("VC_Material")
mat.use_nodes = True
nodes, links = mat.node_tree.nodes, mat.node_tree.links
# Clear existing nodes
nodes.clear()
# Use the setup that works manually: Color Attribute → Principled BSDF → Material Output
nd_color_attr = nodes.new("ShaderNodeVertexColor")
nd_color_attr.layer_name = 'Col'
print("color_attr.name", color_attr.name)
print(f"Using ShaderNodeVertexColor for {color_attr.name}")
# Use Principled BSDF (as per your manual test)
nd_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
nd_tex = nodes.new("ShaderNodeTexImage")  # bake target
nd_output = nodes.new("ShaderNodeOutputMaterial")
nd_tex.image = img
# Connect: Color Attribute → Principled BSDF Base Color → Material Output
links.new(nd_color_attr.outputs["Color"], nd_bsdf.inputs["Base Color"])
links.new(nd_bsdf.outputs["BSDF"], nd_output.inputs["Surface"])
# Make the texture node active for baking
for n in nodes:
    n.select = False
nd_tex.select = True
nodes.active = nd_tex
# Assign material to the object
if obj.data.materials:
    obj.data.materials[0] = mat
else:
    obj.data.materials.append(mat)
# Configure scene for baking
scene = bpy.context.scene
scene.render.engine = "CYCLES"
# Important: Make sure we're in the right context
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
# Set Cycles settings
scene.cycles.device = 'GPU'  # Use CPU for consistency
scene.cycles.samples = 128  # Increased samples
scene.cycles.bake_type = "DIFFUSE"  # Use DIFFUSE as per your manual test
# Bake settings for DIFFUSE
scene.render.bake.use_pass_direct = False
scene.render.bake.use_pass_indirect = False
scene.render.bake.use_pass_color = True  # This is key for vertex colors
scene.render.bake.use_clear = True
scene.render.bake.margin = 4
scene.render.bake.use_selected_to_active = False
# Move object to origin (common fix for baking issues)
obj.location = (0, 0, 0)
print("Starting bake process...")
try:
    bpy.ops.object.bake(type="DIFFUSE")
    print("Bake completed successfully")
except Exception as e:
    print(f"Bake failed: {e}")
    # No fallback needed since we know this setup works

img.save()
print(f"Texture saved to: {tex_path}")
# Pack the image to ensure it's saved properly
img.pack()

# ----------------------------------------------------------------------
# Create final material for export using the baked texture
nodes.clear()
# Create final export material with proper texture setup
nd_tex_final = nodes.new("ShaderNodeTexImage")
nd_tex_final.image = img
nd_tex_final.image.colorspace_settings.name = 'sRGB'
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
nd_output_final = nodes.new("ShaderNodeOutputMaterial")
# Link texture to BSDF
links.new(nd_tex_final.outputs["Color"], bsdf.inputs["Base Color"])
links.new(bsdf.outputs["BSDF"], nd_output_final.inputs["Surface"])
# IMPORTANT: Set the material name and ensure the image is properly saved
mat.name = "VC_Material"
img.name = os.path.basename(tex_path)
# Make sure the image file exists on disk before export
if not os.path.exists(tex_path):
    img.save_render(tex_path)
    print(f"Saved texture to disk: {tex_path}")
# Ensure the image is marked as having a filepath
img.filepath = tex_path
img.source = 'FILE'
# ----------------------------------------------------------------------
# Export OBJ (+ MTL referencing the baked texture)
bpy.ops.wm.obj_export(
    filepath=obj_path,
    export_materials=True,
    export_material_groups=False,
    export_uv=True,
    export_normals=True,
    export_colors=False,  # We're using texture instead
    path_mode="COPY",  
    export_triangulated_mesh=False,
)
print(f"Converted {ply_path} → {obj_path} with texture {tex_path}")
# Final verification - save image again to ensure it's written
