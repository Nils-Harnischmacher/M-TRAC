import bpy, json
import numpy as np
JSON_PATH = bpy.path.abspath("//matrix.json")  

def ensure_compositor():
    scene = bpy.context.scene
    scene.use_nodes = True
    nt = scene.node_tree
    nodes = nt.nodes
    links = nt.links
    return nt, nodes, links
def create_ccm_group(name="CameraCCM"):

    ng = bpy.data.node_groups.new(name, 'CompositorNodeTree')
    if bpy.app.version >= (4, 0, 0):
        iface = ng.interface
        iface.new_socket(name="Image", in_out='INPUT',  socket_type='NodeSocketColor')
        iface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    else:
        ng.inputs.new('NodeSocketColor', 'Image')
        ng.outputs.new('NodeSocketColor', 'Image')
    nodes = ng.nodes
    links = ng.links
    inp  = nodes.new('NodeGroupInput');  inp.location  = (-600, 0)
    outp = nodes.new('NodeGroupOutput'); outp.location = (800, 0)
    sep  = nodes.new('CompositorNodeSepRGBA');  sep.location  = (-400, 0)
    comb = nodes.new('CompositorNodeCombRGBA'); comb.location = (600, 0)
    def add_math(op, loc):
        n = nodes.new('CompositorNodeMath')
        n.operation = op
        n.use_clamp = True
        n.location = loc
        return n
    
    r_mul_r = add_math('MULTIPLY', (-150, 200))
    r_mul_g = add_math('MULTIPLY', (-150, 150))
    r_mul_b = add_math('MULTIPLY', (-150, 100))
    r_add1  = add_math('ADD',       (50,  180))
    r_add2  = add_math('ADD',       (250, 180))

    g_mul_r = add_math('MULTIPLY', (-150,  20))
    g_mul_g = add_math('MULTIPLY', (-150, -30))
    g_mul_b = add_math('MULTIPLY', (-150, -80))
    g_add1  = add_math('ADD',       (50,    0))
    g_add2  = add_math('ADD',       (250,   0))

    b_mul_r = add_math('MULTIPLY', (-150, -160))
    b_mul_g = add_math('MULTIPLY', (-150, -210))
    b_mul_b = add_math('MULTIPLY', (-150, -260))
    b_add1  = add_math('ADD',       (50,  -180))
    b_add2  = add_math('ADD',       (250, -180))

    links.new(inp.outputs['Image'], sep.inputs['Image'])

    for mul, ch in [(r_mul_r, 'R'), (g_mul_r, 'R'), (b_mul_r, 'R')]:
        links.new(sep.outputs[ch], mul.inputs[0])
    for mul, ch in [(r_mul_g, 'G'), (g_mul_g, 'G'), (b_mul_g, 'G')]:
        links.new(sep.outputs[ch], mul.inputs[0])
    for mul, ch in [(r_mul_b, 'B'), (g_mul_b, 'B'), (b_mul_b, 'B')]:
        links.new(sep.outputs[ch], mul.inputs[0])

    links.new(r_mul_r.outputs[0], r_add1.inputs[0]); links.new(r_mul_g.outputs[0], r_add1.inputs[1])
    links.new(r_add1.outputs[0],  r_add2.inputs[0]); links.new(r_mul_b.outputs[0], r_add2.inputs[1])

    links.new(g_mul_r.outputs[0], g_add1.inputs[0]); links.new(g_mul_g.outputs[0], g_add1.inputs[1])
    links.new(g_add1.outputs[0],  g_add2.inputs[0]); links.new(g_mul_b.outputs[0], g_add2.inputs[1])

    links.new(b_mul_r.outputs[0], b_add1.inputs[0]); links.new(b_mul_g.outputs[0], b_add1.inputs[1])
    links.new(b_add1.outputs[0],  b_add2.inputs[0]); links.new(b_mul_b.outputs[0], b_add2.inputs[1])

    links.new(r_add2.outputs[0], comb.inputs['R'])
    links.new(g_add2.outputs[0], comb.inputs['G'])
    links.new(b_add2.outputs[0], comb.inputs['B'])

    links.new(comb.outputs['Image'], outp.inputs['Image'])

    return ng, {
        "r_mul_r": r_mul_r, "r_mul_g": r_mul_g, "r_mul_b": r_mul_b, "r_add2": r_add2,
        "g_mul_r": g_mul_r, "g_mul_g": g_mul_g, "g_mul_b": g_mul_b, "g_add2": g_add2,
        "b_mul_r": b_mul_r, "b_mul_g": b_mul_g, "b_mul_b": b_mul_b, "b_add2": b_add2,
        "input": inp
    }


def load_matrix(json_path):
    with open(json_path, "r") as f:
        d = json.load(f)
    W = np.array(d["matrix_3x3_rowmajor"], dtype=float)  # row-major
    b = np.array(d.get("offset",[0,0,0]), dtype=float)
    return W, b

def apply_to_scene(ng, nodes_map):
    nt, nodes, links = ensure_compositor()
    rl = next((n for n in nodes if n.type=="R_LAYERS"), None)
    comp = next((n for n in nodes if n.type=="COMPOSITE"), None)
    viewer = next((n for n in nodes if n.type=="VIEWER"), None) or nodes.new('CompositorNodeViewer')
    group_node = nodes.new('CompositorNodeGroup')
    group_node.node_tree = ng
    rl.location = (-600, 0)
    group_node.location = (-200, 0)
    comp.location = (250, 0)
    viewer.location = (250, -150)
    links.new(rl.outputs['Image'], group_node.inputs['Image'])
    links.new(group_node.outputs['Image'], comp.inputs['Image'])
    links.new(group_node.outputs['Image'], viewer.inputs['Image'])

def set_weights(nodes_map, W, b):
    nodes_map["r_mul_r"].inputs[1].default_value = float(W[0,0])
    nodes_map["r_mul_g"].inputs[1].default_value = float(W[0,1])
    nodes_map["r_mul_b"].inputs[1].default_value = float(W[0,2])
    nodes_map["g_mul_r"].inputs[1].default_value = float(W[1,0])
    nodes_map["g_mul_g"].inputs[1].default_value = float(W[1,1])
    nodes_map["g_mul_b"].inputs[1].default_value = float(W[1,2])
    nodes_map["b_mul_r"].inputs[1].default_value = float(W[2,0])
    nodes_map["b_mul_g"].inputs[1].default_value = float(W[2,1])
    nodes_map["b_mul_b"].inputs[1].default_value = float(W[2,2])
    nodes_map["r_add2"].inputs[1].default_value = float(b[0])
    nodes_map["g_add2"].inputs[1].default_value = float(b[1])
    nodes_map["b_add2"].inputs[1].default_value = float(b[2])


