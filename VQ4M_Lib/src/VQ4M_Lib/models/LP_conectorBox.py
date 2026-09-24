import bpy
from math import radians
from VQ4M_Lib.models.model_helpers.helpers import mm, relink, round_corners
from VQ4M_Lib.models.model_helpers.geometry_helpers import make_button_pill,make_spo2_connector
from VQ4M_Lib.models.model_helpers import gen_materials 

def make_conector_cube(width,x, body_d, body_h, col):

    bpy.ops.mesh.primitive_cube_add(size=1,location=(x, 0, 0))
    port_block = bpy.context.active_object
    port_block.name = "PortBlock"
    port_block.scale = (width, body_d, body_h)
    relink(port_block, col)
    round_corners(port_block, width=mm(20), segments=20, profile=0.5)
    gen_materials.assign_single_material(port_block,gen_materials.pulsOx_screen_cover())
    return port_block

def make_conectors(width, x, y,mat,col_ui):
    #make_spo2_connector(cable_len=width/2,sp_con_r= mm(12),sp_con_h = mm(110),ports_x=x, y=y, sp_vertices=128,col_ui=col_ui)
    temp_ip = make_button_pill("Temp_IP",  x, mm(20), y,mat=mat, radius_mm=14, length_mm=55,h=mm(2),col_ui=col_ui)
    temp_ip.rotation_euler.y = radians(90)
    temp_ip = make_button_pill("CO2",  x, -mm(45),y,  mat=mat, radius_mm=14, length_mm=55,h=mm(2),col_ui=col_ui)
    temp_ip.rotation_euler.y = radians(90)
    temp_ip = make_button_pill("NIB",  x, -mm(100),y,  mat=mat, radius_mm=14, length_mm=14,h=mm(2),col_ui=col_ui)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y, -mm(140)))
    port_block = bpy.context.active_object
    port_block.name = "USB_port"
    port_block.scale = (mm(28), mm(2),mm(28))
    port_block.data.materials.append(mat)
