# Helper script

The purpose of this helper script is to create a basic starting base for the creation of a schematic by using mecabricks collada files.

It generates a basic schematic with one step with all the pieces within.
It also generates all the pieces in the .obj format.

You can also use the script to deduplicate your .obj files.

## Installation

You have to do the following steps (in any order):

- Use the requirement.txt
- Install PyMesh (not the pip version which is another package) (more info here : https://pymesh.readthedocs.io/en/latest/installation.html)

## Usage

- Create a folder called "obj_files" in the same folder as the script.
- Modify the collada_file variable in the script, in line 10 (collada_file = 'Your collada.dae')
- Run the script
