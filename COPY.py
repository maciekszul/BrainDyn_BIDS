import os
import sys
import json
import shutil
import os.path as op
import subprocess as sp
from utilities import files

try:
    index = int(sys.argv[1])
except:
    print("incorrect arguments")
    sys.exit()

try:
    json_file = sys.argv[2]
    print("USING:", json_file)
except:
    json_file = "settings.json"
    print("USING:", json_file)


# opening a json file
with open(json_file) as pipeline_file:
    parameters = json.load(pipeline_file)

project_name = parameters["project_name"]
dataset_path = parameters["bids_path"]
nd_path = parameters["neurodocker_path"]

derivatives = op.join(dataset_path, "derivatives")
freesurfer = op.join(derivatives, "freesurfer")
files.make_folder(derivatives)
files.make_folder(freesurfer)


raw_fs = files.get_folders_files(freesurfer)[0]
raw_fs.sort()

in_path = raw_fs[index]

subject_id = in_path.split(os.sep)[-1]

wk_dir = op.join(freesurfer, subject_id, "mri")

t1_in = "T1.mgz"
t2_in = "T2.mgz"



t1_out = "{}_T1w.nii.gz".format(subject_id)
t2_out = "{}_T2w.nii.gz".format(subject_id)

os.chdir(wk_dir)

sp.call([
    "singularity",
    "run",
    nd_path,
    "mri_convert",
    t1_in,
    t1_out
])
print("T1:", t1_out)

sp.call([
    "singularity",
    "run",
    nd_path,
    "mri_convert",
    t2_in,
    t2_out
])
print("T2:", t2_out)

t1_in_path = op.join(wk_dir, t1_out)
t2_in_path = op.join(wk_dir, t2_out)

t1_out_path = op.join(dataset_path, project_name, subject_id, "anat", "{}_T1w.nii.gz".format(subject_id))
t2_out_path = op.join(dataset_path, project_name, subject_id, "anat", "{}_T2w.nii.gz".format(subject_id))

shutil.move(t1_in_path, t1_out_path)
shutil.move(t2_in_path, t2_out_path)