bl_info = {
    "name": "PathGraph for 3DMap",
    "blender": (2, 80, 0),
    "author": "Only.",
}

import getopt
import json
import os
import subprocess
import sys

import bmesh
import bpy
import networkx as nx
from bpy_extras.io_utils import ImportHelper


class CreateJsonOperator(bpy.types.Operator, ImportHelper):
    bl_idname = "pg.export_graph_json"
    bl_label = "Export Graph JSON (.json)"
    filename_ext = ".json"
    
    def execute(self, context):
        obj = bpy.context.active_object

        if obj.type != 'MESH':
            self.report({"WARNING"}, "Selected object isn't a Mesh")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(context.edit_object.data)
        pg_place = bm.verts.layers.string.get('pg_place')

        G = nx.Graph()

        # Добавление вершин и ребер в граф
        for v in bm.verts:
            G.add_node(v.index)
        for e in bm.edges:
            G.add_edge(e.verts[0].index, e.verts[1].index, weight=(e.verts[0].co-e.verts[1].co).length)
        
        adjacency_dict = nx.to_dict_of_dicts(G)

        vertices = []
        for v in bm.verts:
            vertices.append({
                'coords': (v.co.x, v.co.y, v.co.z),
                'place': v[pg_place].decode('UTF-8')
            })

        bm.free()
            
        filepath = bpy.context.active_object.name + ".json"

        with open(self.filepath, 'w') as json_file:
            json.dump({
                'verts': vertices,
                'graph': adjacency_dict
            }, json_file, indent=4)
        
            self.report({'INFO'}, f"JSON file '{filepath}' has been created.")

            return {'FINISHED'}

class CreateDataLayer(bpy.types.Operator):
    bl_idname = "pg.create_data_layer"
    bl_label = "Create Data Layer"

    def execute(self, context):
        bm = bmesh.from_edit_mesh(context.edit_object.data)
        bm.verts.layers.string.new('pg_place')
        bm.free()
        return {'FINISHED'}

class SaveDataToLayers(bpy.types.Operator):
    bl_idname = "pg.save_data_to_layers"
    bl_label = "Save Data"

    def execute(self, context):
        bm = bmesh.from_edit_mesh(context.edit_object.data)

        input_place = context.scene.pg_place_input

        pg_place = bm.verts.layers.string.get('pg_place')

        for v in bm.verts:
            if not v.select: continue
            v[pg_place] = bytes(input_place, 'UTF-8')

        bm.free()
        print('SAVE')
        return {'FINISHED'}

class VertexFlagMenu(bpy.types.Panel):
    bl_idname = "MESH_PT_vertex_flag_menu"
    bl_label = "Vertex Graph Flags"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Item"
    bl_context = 'mesh_edit'

    def draw(self, context):
        layout = self.layout
        
        bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
        pg_place = bm.verts.layers.string.get('pg_place')
        
        if (pg_place == None):
            layout.label(text="Layers doesnt exist")
            layout.operator("pg.create_data_layer", text="Create data layer")
            return

        # Show labels
        layout.prop(context.scene.vertex_info_props, 'show_labels')
        layout.prop(context.scene.vertex_info_props, 'show_indexes')
        layout.prop(context.scene.vertex_info_props, 'labels_size')
        layout.separator()
        
        # Check only one vertex select
        selected = [v for v in bm.verts if v.select]

        if bpy.types.Scene.pg_prev_vertex != str(selected):

            bpy.types.Scene.pg_prev_vertex = str(selected)
        
        if len(selected) == 0:
            layout.label(text="Nothing selected")
            return
        
        vertex = selected[0]
        
        bm.free()

        v_place = vertex[pg_place].decode('UTF-8')

        if len(selected) > 1:
            all_places = all(selected[0][pg_place] == v[pg_place] for v in selected)

            layout.label(text=f"Place: {v_place if all_places else 'Mixed'}")
        else:
            layout.label(text=f"Place: {v_place}")

        layout.separator()
        layout.prop(context.scene, 'pg_place_input')

        layout.operator("pg.save_data_to_layers", text="Save data")
        layout.separator()
        layout.operator("pg.export_graph_json", text="Export Graph JSON")


from blf import draw, position, size
from bpy_extras.view3d_utils import location_3d_to_region_2d


class VertexInfoLabelsProps(bpy.types.PropertyGroup):
    show_labels: bpy.props.BoolProperty(
        name='Show Labels',
        default=False
    )
    show_indexes: bpy.props.BoolProperty(
        name='Show Indexes',
        default=False
    )
    labels_size: bpy.props.IntProperty(
        name='Labels Size',
        default=20, 
        min=10,
        max=50,
    )

class VertexInfoLabels():
    handle = None
    areatype = None

    def __init__(self, context, areatype):
        self.areatype = areatype
        self.handle = self.create_handle(context)

    def __del__(self):
        print('del ================================= ')
        if self.handle:
            self.areatype.draw_handler_remove(self.handle, 'WINDOW') 
            self.handle = None

    def create_handle(self, context):
        handle = self.areatype.draw_handler_add(
            self.draw_region,
            (context,),
           'WINDOW', 'POST_PIXEL')  
        return handle

    def draw_region(self, context):
        context = bpy.context
        is_show_indexes = bpy.context.scene.vertex_info_props.show_indexes
        is_show_labels = bpy.context.scene.vertex_info_props.show_labels

        if not is_show_labels: return {'PASS_THROUGH'}
        font_id = 0

        if context.active_object.mode != 'EDIT': return {'PASS_THROUGH'}

        bm = bmesh.from_edit_mesh(context.edit_object.data)

        global_mat = context.active_object.matrix_world

        pg_place = bm.verts.layers.string.get('pg_place')

        rv3d = context.space_data.region_3d

        for v in bm.verts:
            pos = global_mat @ v.co
            pos_text = location_3d_to_region_2d(context.region, rv3d, pos)

            position(font_id, pos_text[0], pos_text[1], 0)
            size(font_id, bpy.context.scene.vertex_info_props.labels_size)
            draw(font_id, v.index if is_show_indexes else v[pg_place].decode('UTF-8'))

        return {'PASS_THROUGH'}
    

def register():
    bpy.utils.register_class(CreateJsonOperator)
    bpy.utils.register_class(VertexFlagMenu)

    bpy.utils.register_class(CreateDataLayer)
    bpy.utils.register_class(SaveDataToLayers)


    bpy.types.Scene.pg_prev_vertex = None
    bpy.types.Scene.pg_place_input = bpy.props.StringProperty(
        name="Place",
        description="Enter place name",
        default="",
        # update = lambda self, context: print(context.scene.pg_place_input)
    )

    bpy.utils.register_class(VertexInfoLabelsProps)
    bpy.types.Scene.vertex_info_props = bpy.props.PointerProperty(type=VertexInfoLabelsProps)
    bpy.types.Scene.vertex_info_class = VertexInfoLabels(bpy.context, bpy.types.SpaceView3D)

def unregister():
    bpy.utils.unregister_class(CreateJsonOperator)
    bpy.utils.unregister_class(VertexFlagMenu)

    bpy.utils.unregister_class(CreateDataLayer)
    bpy.utils.unregister_class(SaveDataToLayers)

    del bpy.types.Scene.pg_place_input
    del bpy.types.Scene.pg_prev_vertex

    bpy.types.Scene.vertex_info_class.__del__()
    del bpy.types.Scene.vertex_info_props
    bpy.utils.unregister_class(VertexInfoLabelsProps)


if __name__ == "__main__":
    register()