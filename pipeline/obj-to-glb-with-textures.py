"""
AC Visualizer: OBJ → GLB Pipeline with Correct Texture Mapping
================================================================
Imports OBJ from 3ds Max, applies textures from Maps/ folder based on
mesh names (matching original 3ds Max material assignments), cleans up
the scene (keeps only indoor unit), and exports optimized GLB.

Usage:
  blender --background --python pipeline/obj-to-glb-with-textures.py -- \
    --input "models/samsung windfree/Samsung Windfree Split Air Conditioner Vray.obj" \
    --maps "models/samsung windfree/Maps" \
    --output "models/samsung-windfree.glb" \
    --keep-indoor
"""

import bpy
import sys
import os
import math

# ============================================================================
# Parse arguments after "--"
# ============================================================================
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

# Defaults
INPUT_OBJ = None
MAPS_DIR = None
OUTPUT_GLB = None
KEEP_INDOOR = False

i = 0
while i < len(argv):
    if argv[i] == "--input" and i + 1 < len(argv):
        INPUT_OBJ = argv[i + 1]; i += 2
    elif argv[i] == "--maps" and i + 1 < len(argv):
        MAPS_DIR = argv[i + 1]; i += 2
    elif argv[i] == "--output" and i + 1 < len(argv):
        OUTPUT_GLB = argv[i + 1]; i += 2
    elif argv[i] == "--keep-indoor":
        KEEP_INDOOR = True; i += 1
    else:
        i += 1

if not INPUT_OBJ:
    print("ERROR: --input is required")
    sys.exit(1)

if not OUTPUT_GLB:
    # Auto-generate output name
    base = os.path.splitext(os.path.basename(INPUT_OBJ))[0]
    OUTPUT_GLB = os.path.join(os.path.dirname(INPUT_OBJ), base + ".glb")

if not MAPS_DIR:
    # Default: look for Maps/ in same directory as OBJ
    MAPS_DIR = os.path.join(os.path.dirname(INPUT_OBJ), "Maps")

print(f"Input OBJ: {INPUT_OBJ}")
print(f"Maps dir:  {MAPS_DIR}")
print(f"Output:    {OUTPUT_GLB}")

# ============================================================================
# Clear scene
# ============================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)

# ============================================================================
# Import OBJ
# ============================================================================
print("\n--- Importing OBJ ---")
bpy.ops.wm.obj_import(
    filepath=os.path.abspath(INPUT_OBJ),
    forward_axis='NEGATIVE_Z',
    up_axis='Y',
    import_vertex_groups=True,
)

# List all imported objects
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
print(f"Imported {len(meshes)} mesh objects:")
for obj in meshes:
    dims = obj.dimensions
    print(f"  {obj.name:40s} | {dims.x*100:.0f}x{dims.y*100:.0f}x{dims.z*100:.0f} cm")

# ============================================================================
# Filter indoor unit (keep only objects with suffix 002 or common indoor parts)
# ============================================================================
if KEEP_INDOOR and len(meshes) > 8:
    print("\n--- Filtering indoor unit ---")
    # Indoor unit meshes typically have "002" suffix in WindFree model
    # Also keep shared parts like Innner_Part, Lock, swing
    indoor_keywords = ['002', 'innner', 'lock', 'swing_001']
    outdoor_keywords = ['003', '001']  # 001/003 are often outdoor unit parts

    to_remove = []
    for obj in meshes:
        name_lower = obj.name.lower()
        is_indoor = any(kw in name_lower for kw in indoor_keywords)
        is_outdoor = any(kw in name_lower for kw in outdoor_keywords) and not is_indoor
        if is_outdoor:
            to_remove.append(obj)
            print(f"  REMOVING: {obj.name}")

    for obj in to_remove:
        bpy.data.objects.remove(obj, do_unlink=True)

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    print(f"Remaining: {len(meshes)} objects")

# ============================================================================
# Load textures from Maps/ directory
# ============================================================================
print("\n--- Loading textures ---")
texture_files = {}
if os.path.isdir(MAPS_DIR):
    for f in os.listdir(MAPS_DIR):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tga', '.bmp', '.tiff')):
            filepath = os.path.join(MAPS_DIR, f)
            texture_files[f.lower()] = filepath
            print(f"  Found: {f}")
else:
    print(f"  WARNING: Maps directory not found: {MAPS_DIR}")

def load_image(filename_lower):
    """Load an image by lowercase filename from Maps/"""
    if filename_lower in texture_files:
        path = os.path.abspath(texture_files[filename_lower])
        img = bpy.data.images.load(path)
        return img
    return None

# ============================================================================
# Create materials based on mesh names and apply correct textures
# Samsung WindFree texture mapping (from original 3ds Max scene):
#   - AC_Body (main body): white plastic, Samsung logo top-left
#   - Body_Lower_Part: white/light gray, Samsung logo texture
#   - AC_Uper_Fence / Ac_Net: white with Front Mesh Alpha (dot pattern)
#   - AC_Digital_Display: dark with Display Logo 01 (LED display)
#   - Ac_swing: glossy white (air deflector)
#   - Innner_Part: dark gray
#   - Lower_Machine: dark inner parts
#   - Lock: metallic gray
# ============================================================================
print("\n--- Creating materials ---")

def create_principled_material(name, color=(0.9, 0.9, 0.9, 1.0), roughness=0.3,
                                metallic=0.0, alpha_tex=None, bump_tex=None,
                                diffuse_tex=None, emissive_tex=None):
    """Create a Principled BSDF material with optional textures"""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Clear default nodes
    for node in nodes:
        nodes.remove(node)

    # Output node
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)

    # Principled BSDF
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic

    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # Diffuse texture (color map)
    if diffuse_tex:
        img = load_image(diffuse_tex)
        if img:
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = img
            tex_node.location = (-400, 200)
            links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
            print(f"    + diffuse: {diffuse_tex}")

    # Alpha map (transparency)
    if alpha_tex:
        img = load_image(alpha_tex)
        if img:
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = img
            tex_node.location = (-400, -100)
            links.new(tex_node.outputs['Color'], bsdf.inputs['Alpha'])
            mat.blend_method = 'CLIP'
            mat.alpha_threshold = 0.5
            print(f"    + alpha: {alpha_tex}")

    # Bump map
    if bump_tex:
        img = load_image(bump_tex)
        if img:
            img.colorspace_settings.name = 'Non-Color'
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = img
            tex_node.location = (-600, -300)

            bump_node = nodes.new('ShaderNodeBump')
            bump_node.inputs['Strength'].default_value = 0.15
            bump_node.location = (-200, -300)

            links.new(tex_node.outputs['Color'], bump_node.inputs['Height'])
            links.new(bump_node.outputs['Normal'], bsdf.inputs['Normal'])
            print(f"    + bump: {bump_tex}")

    # Emissive texture (for displays)
    if emissive_tex:
        img = load_image(emissive_tex)
        if img:
            tex_node = nodes.new('ShaderNodeTexImage')
            tex_node.image = img
            tex_node.location = (-400, 400)
            links.new(tex_node.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = 2.0
            print(f"    + emissive: {emissive_tex}")

    return mat

# Create all materials
print("  Body (main):")
mat_body = create_principled_material(
    "AC_Body_White",
    color=(0.95, 0.95, 0.95, 1.0),
    roughness=0.25,
    diffuse_tex="samsung logo.jpg",  # Samsung logo on body
)

print("  Body Lower:")
mat_body_lower = create_principled_material(
    "AC_Body_Lower",
    color=(0.93, 0.93, 0.93, 1.0),
    roughness=0.3,
)

print("  Fence/Net (WindFree mesh):")
mat_fence = create_principled_material(
    "AC_WindFree_Mesh",
    color=(1.0, 1.0, 1.0, 1.0),
    roughness=0.35,
    alpha_tex="front mesh alpha.jpg",
    bump_tex="front mesh bump.jpg",
)

print("  Display:")
mat_display = create_principled_material(
    "AC_Display",
    color=(0.05, 0.05, 0.05, 1.0),
    roughness=0.4,
    metallic=0.1,
    emissive_tex="display logo 01.jpg",
)

print("  Swing (air flap):")
mat_swing = create_principled_material(
    "AC_Swing",
    color=(0.94, 0.94, 0.94, 1.0),
    roughness=0.15,
)

print("  Inner parts:")
mat_inner = create_principled_material(
    "AC_Inner",
    color=(0.15, 0.15, 0.15, 1.0),
    roughness=0.6,
    metallic=0.1,
)

print("  Lock/hinge:")
mat_lock = create_principled_material(
    "AC_Lock",
    color=(0.55, 0.55, 0.55, 1.0),
    roughness=0.4,
    metallic=0.2,
)

# ============================================================================
# Assign materials to meshes based on name
# ============================================================================
print("\n--- Assigning materials ---")
for obj in meshes:
    n = obj.name.lower()

    if 'digital_display' in n:
        mat = mat_display
    elif 'ac_body' in n and 'lower' not in n:
        mat = mat_body
    elif 'body_lower' in n:
        mat = mat_body_lower
    elif 'fence' in n or 'net' in n:
        mat = mat_fence
    elif 'swing' in n:
        mat = mat_swing
    elif 'inner' in n or 'lower_machine' in n:
        mat = mat_inner
    elif 'lock' in n:
        mat = mat_lock
    else:
        mat = mat_body  # fallback

    # Clear existing materials and assign new one
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    print(f"  {obj.name:40s} → {mat.name}")

# ============================================================================
# Center and scale
# ============================================================================
print("\n--- Centering model ---")
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

# Calculate bounding box of all objects
import mathutils
min_co = mathutils.Vector((float('inf'),) * 3)
max_co = mathutils.Vector((float('-inf'),) * 3)
for obj in meshes:
    for corner in obj.bound_box:
        world_co = obj.matrix_world @ mathutils.Vector(corner)
        min_co = mathutils.Vector([min(a, b) for a, b in zip(min_co, world_co)])
        max_co = mathutils.Vector([max(a, b) for a, b in zip(max_co, world_co)])

size = max_co - min_co
center = (min_co + max_co) / 2
print(f"  Bounding box: {size.x*100:.0f} x {size.y*100:.0f} x {size.z*100:.0f} cm")
print(f"  Center: ({center.x:.3f}, {center.y:.3f}, {center.z:.3f})")

# ============================================================================
# Export GLB
# ============================================================================
print(f"\n--- Exporting GLB: {OUTPUT_GLB} ---")

# Make sure output directory exists
os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_GLB)), exist_ok=True)

bpy.ops.export_scene.gltf(
    filepath=OUTPUT_GLB,
    export_format='GLB',
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_image_format='AUTO',
    export_apply=True,
)

# Check output file size
if os.path.exists(OUTPUT_GLB):
    size_mb = os.path.getsize(OUTPUT_GLB) / (1024 * 1024)
    print(f"\nSUCCESS: {OUTPUT_GLB} ({size_mb:.2f} MB)")
else:
    print(f"\nERROR: Output file not created!")

print("\n========================================")
print("Pipeline complete!")
