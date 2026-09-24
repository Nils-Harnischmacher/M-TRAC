import sys, os, csv
import bpy
import math
from datetime import datetime
import importlib
from pathlib import Path

# Helpers
#from  VQ4M_Lib.models.model_helpers import helpers 
from VQ4M_Lib.models.model_helpers.helpers import mm, new_collection, add_mat

# Modellib 
from  VQ4M_Lib.models import LP_screen as LP_screen
LP_screen= importlib.reload(LP_screen)
from  VQ4M_Lib.models import LP_conectorBox as LP_conectorBox
LP_conectorBox= importlib.reload(LP_conectorBox)
from  VQ4M_Lib.models import LP_pouches as LP_pouches
LP_pouches= importlib.reload(LP_pouches)


#Pipelinelib 

from VQ4M_Lib import camera as camLib 
camlib = importlib.reload(camLib)
from VQ4M_Lib import shake as shakeLib
shakelib = importlib.reload(shakeLib)
from VQ4M_Lib import lighting as lightLib 
lightlib = importlib.reload(lightLib)
from VQ4M_Lib import rendering as renderLib 
renderLib = importlib.reload(renderLib)

from VQ4M_Lib import general as genLib
genlib = importlib.reload(genLib)

from VQ4M_Lib import boundingbox as bb
bb = importlib.reload(bb)



def create_lifepak(asset_path=""):
    # === settings ===
    dims = {
        "body_w": 349,     # width (X)
        "body_h": 355,     # height (Z)
        "body_d": 124,     # depth (Y)
        "corner_r": 50,    # body corner radius
        "bevel_seg": 4,
        "bezel_w":349*0.82,
        "bezel_h":355*0.82,
        "screen_w": 200,
        "screen_h": 250,
        "screen_margin": 18,
        "bezel_thick": 8,
        "glass_inset": 2.5,
        "conectorBox_w": 100,

        "pouch_w": 125,
        "pouch_h": 300,
        "pouch_d": 124,
        "pcover_depht_l":50,
        "pouch_gap": 8,
        "handle_span": 300,
        "handle_height": 100,
        "handle_thick": 25,
        "handle_foot_w": 38,
        "handle_foot_d": 30,
        "button_r": 11,
        "button_h": 7,
        "port_r": 6,
        "zip_tab_w": 26,
        "zip_tab_h": 6,
        "zip_tab_d": 2.5,
    }

    col = new_collection("LIFEPAK")
    col_ui = new_collection("UI", parent=col)
    col_pouches = new_collection("Pouches", parent=col)
    col_misc = new_collection("Misc", parent=col)

    mat_body    = add_mat("Body_Dark", (0.05, 0.05, 0.06, 1))
    mat_bezel   = add_mat("Bezel_Graphite", (0.06, 0.06, 0.07, 1))
    mat_glass   = add_mat("Screen_Glass", (0.03, 0.03, 0.03, 0.25))
    mat_green   = add_mat("Button_Green", (0.12, 0.7, 0.2, 1))
    mat_orange  = add_mat("Button_Orange", (1.0, 0.45, 0.1, 1))
    mat_red  = add_mat("Button_red", (1.0, 0.045, 0.1, 1))
    mat_zip     = add_mat("Zip_Pull", (0.2, 0.2, 0.22, 1))



    # === model setup ===

    main=LP_screen.make_main_body(mm(dims["body_w"]), mm(dims["body_d"]), mm(dims["body_h"]), mm(dims["corner_r"]),mat_body, col)
    length_y = mm(30)
    boarder_width= mm(dims["body_w"])-mm(dims["bezel_w"])
    LP_screen.make_pyramidal_bezel(0,main.location.y+ mm(dims["body_d"])/2+length_y/2,0,mm(dims["body_w"]),mm(dims["body_h"]),length_y,boarder_width/2,mm(10),mm(dims["corner_r"]),name="bumb_bezel")
    bezel= LP_screen.make_screen_bezel(mm(dims["bezel_w"]), mm(dims["bezel_h"]),mm(dims["bezel_thick"]), mm(dims["body_d"]), mm(20),mat_bezel , col)
    screen=LP_screen.make_screen(mm(dims["screen_w"]), mm(dims["screen_h"]),mm(dims["screen_margin"]),mm(dims["glass_inset"]),mm(dims["bezel_w"]), mm(dims["bezel_thick"]),bezel,mat_glass,col,asset_path=asset_path)
    LP_screen.make_handle(mm(dims["body_h"]),dims, col)
    LP_screen.make_buttons(mm(dims["button_h"]),mm(dims["screen_w"]), mm(dims["screen_margin"]), bezel.location.y, mat_green, mat_orange, mat_bezel, mat_red,col)
    port_block=LP_conectorBox.make_conector_cube(mm(dims["conectorBox_w"]),(mm(dims["body_w"])/2+mm(dims["conectorBox_w"])/2), mm(dims["body_d"]), mm(dims["body_h"])-mm(20), col)
    LP_conectorBox.make_conectors(mm(dims["conectorBox_w"]), (mm(dims["body_w"])/2+mm(dims["conectorBox_w"])/2),bezel.location.y,mat_body, col_ui) 
    LP_pouches.create_base_pouch_left(mm(dims["pouch_w"]),mm(dims["pouch_d"]),mm(dims["pouch_h"]),mm(dims["pcover_depht_l"]),mm(dims["corner_r"]),edge_r=mm(20),location=(mm(dims["body_w"])/2+mm(dims["conectorBox_w"])+mm(dims["pouch_w"])/2,0,0))
    LP_pouches.create_base_pouch_right(mm(dims["pouch_w"]),mm(dims["pouch_d"]),mm(dims["pouch_h"]),mm(dims["pcover_depht_l"]),mm(dims["corner_r"]),edge_r=mm(20),location=(-mm(dims["body_w"])/2-mm(dims["pouch_w"])/2,0,0))
    return screen