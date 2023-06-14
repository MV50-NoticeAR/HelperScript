import xml.etree.ElementTree as ET
import json
import numpy as np
from scipy.spatial.transform import Rotation as R

import collections
collections.Callable = collections.abc.Callable # Workaround, see : https://stackoverflow.com/questions/69515086/error-attributeerror-collections-has-no-attribute-callable-using-beautifu
import pymesh

collada_file = 'Your collada.dae'
debug=False
verbose=True
replaceToConvention=True
KeepNonDuplicatesTemp=False

def export_obj_file(name, vertices, faces):
    pymesh_mesh = pymesh.form_mesh(vertices, faces)
    pymesh.save_mesh(f"obj_files/{name}.obj", pymesh_mesh)

import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation as R

def fetch_mesh_data(node_id, root, ns):
    # Find the node with the specified id
    node = root.find(f".//c:node[@id='{node_id}']", ns)
    if node is None:
        return None

    # Extract geometry URL from the node
    geom_url_element = node.find("./c:instance_geometry", ns)
    if geom_url_element is None:
        return None

    # Remove leading '#' from the URL
    mesh_name = geom_url_element.attrib['url'].lstrip('#')

    # Find the geometry node with the extracted URL
    geometry_node = root.find(f".//c:geometry[@id='{mesh_name}']", ns)
    if geometry_node is None:
        return None

    # Extract vertex positions
    vertices_source_node = geometry_node.find(".//c:source[@id='{}-positions']".format(mesh_name), ns)
    if vertices_source_node is None:
        return None
    vertices_float_array_node = vertices_source_node.find(".//c:float_array", ns)
    vertices = np.array(list(map(float, vertices_float_array_node.text.split()))).reshape((-1, 3))

    # Extract faces
    triangles_node = geometry_node.find(".//c:triangles", ns)
    p_node = triangles_node.find(".//c:p", ns)

    # Check if vertex data is not the first input in the list
    # It's always good to check this assumption when working with different 3D models
    vertex_offset = int(triangles_node.find(".//c:input[@semantic='VERTEX']", ns).attrib['offset'])
    # Find all <input> elements
    inputs = triangles_node.findall(".//c:input", ns)

    max_offset = -1  # Initialize the max_offset variable to a negative value

    # Iterate over the <input> elements and update max_offset if necessary
    for input_element in inputs:
        offset = int(input_element.attrib.get("offset", 0))
        max_offset = max(max_offset, offset)

    print("Max offset value for any 'input':", max_offset)

    face_indices = np.array(list(map(int, p_node.text.split())))
    face_indices = face_indices[vertex_offset::max_offset+1]
    if debug==True:
        print("Max face indices : " + str(max(face_indices)))
        print("Len vertices : " + str(len(vertices)))

    faces = face_indices.reshape((-1, 3))

    return vertices, faces

def fetch_material(node, root, ns):
    # Find the material used in the node
    instance_material = node.find('./c:instance_geometry/c:bind_material/c:technique_common/c:instance_material', ns)
    if instance_material is None:
        return None

    # Get the target material id
    material_id = instance_material.attrib['target'].lstrip('#')

    # Find the material node with the extracted id
    material_node = root.find(f".//c:material[@id='{material_id}']", ns)
    if material_node is None:
        return None

    # Get the target effect id from the material node
    instance_effect = material_node.find('.//c:instance_effect', ns)
    if instance_effect is None:
        return None

    # Extract the id of the effect
    effect_id = instance_effect.attrib['url'].lstrip('#')

    # Find the effect node with the extracted id
    effect_node = root.find(f".//c:effect[@id='{effect_id}']", ns)
    if effect_node is None:
        return None

    # Extract the color from the effect node
    color_node = effect_node.find(".//c:profile_COMMON/c:technique/c:phong/c:diffuse/c:color", ns)
    if color_node is None:
        return None

    # Return the color values as an RGB hex string
    color_values = list(map(float, color_node.text.split()))
    color_hex = ''.join(f"{int(c*255):02x}" for c in color_values[:3])

    return color_hex

unique_meshes = set()

# Parse the XML file
tree = ET.parse(collada_file)
root = tree.getroot()

# Namespaces in the COLLADA file
ns = {'c': 'http://www.collada.org/2005/11/COLLADASchema'}

# Initialize the structures
schematic = {
    "name": "Test schematic",
    "picture": "test.png",
    "author": root.find('.//c:author', ns).text,
    "description": "This is a test schematic.",
    "version": root.attrib['version'],
    "steps": []
}

# Set of unique meshes to export as OBJ files
unique_meshes = set()

for visual_scene in root.findall('.//c:visual_scene', ns):
    step = {
        "name": visual_scene.attrib['name'],
        "description": "This is a step",
        "pieces": []
    }

    for node in visual_scene.findall('.//c:node', ns):
        # Fetch the color associated with this node
        color = fetch_material(node, root, ns)

        matrix = node.find('.//c:matrix', ns).text.split()
        matrix = np.array(matrix, dtype=float).reshape(4, 4)

        position = matrix[:3, 3]

        rotation_matrix = matrix[:3, :3]
        rotation = R.from_matrix(rotation_matrix).as_quat()

        piece = {
            "model": node.attrib['id'],
            # Add color to the piece if it was found
            "color": color if color else "FEFEFE",
            "position": {
                "x": position[0],
                "y": position[1],
                "z": position[2]
            },
            "rotation": {
                "x": rotation[0],
                "y": rotation[1],
                "z": rotation[2],
                "w": rotation[3]
            }
        }
        step["pieces"].append(piece)

        unique_meshes.add(node.attrib['id'])

    schematic["steps"].append(step)

for mesh_name in unique_meshes:
    mesh_data = fetch_mesh_data(mesh_name, root, ns)
    if mesh_data is not None:
        vertices, faces = mesh_data
        export_obj_file(mesh_name, vertices, faces)
        if verbose==True:
            print(f"Mesh '{mesh_name}' found.")
    else:
        print(f"Mesh '{mesh_name}' not found.")

# Write to JSON file
with open('intermediate.json', 'w') as f:
    json.dump(schematic, f, indent=4)

## Sorting the pieces in each step based on the y coordinate

import json

# Read the JSON data
with open('intermediate.json') as file:
    data = json.load(file)

# Iterate over each step
for step in data['steps']:
    # # Sort the pieces in the step based on the x coordinate
    # step['pieces'].sort(key=lambda piece: piece['position']['y'])

    # # Sort the pieces in the step based on the x coordinate, and if x is the same, sort based on y coordinate
    # step['pieces'].sort(key=lambda piece: (piece['position']['y'], piece['position']['x']))

    # Sort the pieces in the step based on the x, y, and z coordinates
    step['pieces'].sort(key=lambda piece: (piece['position']['y'], piece['position']['x'], piece['position']['z']))

# Write the updated JSON data to a file
with open('final.json', 'w') as file:
    json.dump(data, file, indent=4)

## Cleanup

import os
import hashlib
import json

def get_hash(file_path):
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for line in f:
            if line.startswith(b'v') or line.startswith(b'f'):
                hasher.update(line)
    return hasher.hexdigest()

def modify_obj_file(file_path):
    temp_file_path = f"{file_path}_temp"
    with open(file_path, 'r') as src_file, open(temp_file_path, 'w') as dest_file:
        for line in src_file:
            if line.startswith(('v ', 'f ')):
                parts = line.split()
                if line.startswith('v '):
                    parts[1:] = [f"{float(part):.3f}" for part in parts[1:]]
                else:
                    parts[1:] = [part.split('/')[0] + '.000' if '.' not in part else part for part in parts[1:]] # unless it contains a dot already
                line = ' '.join(parts) + '\n'
            dest_file.write(line)
    return temp_file_path

def find_duplicates(directory):
    hash_keys = dict()
    duplicates = set()

    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".obj"):  # Only process .obj files
                file_path = os.path.join(dirpath, filename)
                temp_file_path = modify_obj_file(file_path)
                file_hash = get_hash(temp_file_path)
                if file_hash not in hash_keys:
                    hash_keys[file_hash] = (file_path, temp_file_path)
                else:
                    duplicates.add((file_path, temp_file_path))

    return hash_keys, list(duplicates)


def update_json(file_path, hash_keys):
    with open(file_path, 'r') as f:
        data = json.load(f)

    for step in data["steps"]:
        for piece in step["pieces"]:
            model = piece["model"]
            old_file = f"obj_files/{model}.obj"
            new_file = hash_keys[get_hash(old_file + "_temp")][0]
            new_model = os.path.splitext(os.path.basename(new_file))[0]
            piece["model"] = new_model

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

def remove_duplicates(duplicates):
    def sort_key(file_pair):
        filename = os.path.basename(file_pair[0])
        return not filename.lower().startswith("part_")

    duplicates.sort(key=sort_key)

    for file_path, temp_file_path in duplicates:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        print(f"Removed '{file_path}' and '{temp_file_path}'.")

def clean_temp_files(directory):
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(".obj_temp"):
                file_path = os.path.join(dirpath, filename)
                os.remove(file_path)

hash_keys, duplicates = find_duplicates('obj_files/')
update_json('final.json', hash_keys)
remove_duplicates(duplicates)
if not KeepNonDuplicatesTemp==True:
    clean_temp_files('obj_files/')

print("Done !")
