import sys
import json
import shutil
import os.path as op
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
mri_path = parameters["mri_path"]

raw_fs = files.get_folders_files(mri_path)[0]
raw_fs = [i for i in raw_fs if "synth" in i]
raw_fs = [i for i in raw_fs if "pilot" not in i]
raw_fs.sort()

in_path = raw_fs[index]
print("INPUT FOLDER:", in_path)

derivatives = op.join(dataset_path, "derivatives")
freesurfer = op.join(derivatives, "freesurfer")
files.make_folder(derivatives)
files.make_folder(freesurfer)

subject_id = "sub-" + in_path.split("/")[-1].split("-")[0]

out_path = op.join(freesurfer, subject_id)

t1_in = op.join(in_path, "mri", "T1.mgz")
t2_in = op.join(in_path, "mri", "T1.mgz")

t1_out = op.join(dataset_path, project_name, "anat", subject_id, "T1w.nii.gz")
t2_out = op.join(dataset_path, project_name, "anat", subject_id, "T2w.nii.gz")

print("OUTPUT FOLDER:", out_path)

