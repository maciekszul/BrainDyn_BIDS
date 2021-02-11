import sys
import shutil
import json
from datetime import datetime
import os
import os.path as op
import subprocess as sp
import pandas as pd
import numpy as np
from utilities import files
from func import *

"""
DOC
"""


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

# raw DICOM path
raw_path = parameters["raw_path"]

# path to converter
dcm2niix_path = parameters["dcm2niix_path"]

# bids path
bids_path = parameters["bids_path"]

# project name
project_name = parameters["project_name"]

# modality split JSON file
mod_split_path = parameters["modality_json_path"]
with open(mod_split_path) as mod_file:
    modality = json.load(mod_file)

modality = {k.lower(): [i.lower()for i in v] for k, v in modality.items()}

# get the separate xnat recordings, treated as separate participants
recordings = files.get_folders_files(raw_path)[0]
recordings.sort()
recording = recordings[index] # if there is no such path script will throw an error
sub_id = recording.split(os.sep)[-1]
recording = op.join(recording, "ses-mri")
recording = files.get_folders_files(recording)[0][0]

seq_folders = files.get_folders_files(recording)[0]
seq_folders.sort()
seq_folders = seq_folders[:-2]
seq_folders = [op.join(i, "DICOM") for i in seq_folders]

# creating a basic folder structure if nonexistent
project_path = op.join(bids_path, project_name)
files.make_folder(project_path)

subject_path = op.join(project_path, sub_id)
files.make_folder(subject_path)

tmp_path = op.join(bids_path, "tmp")
tmp_sub_path = op.join(tmp_path, sub_id)
files.make_folder(tmp_path)
files.make_folder(tmp_sub_path)

[files.make_folder(op.join(subject_path, m)) for m in modality.keys()]

# converting the DICOM to NIFTI in a temporary folder
for dicom_path in seq_folders:
    dcm2niix_func(
        "dcm2niix",
        dicom_path,
        tmp_sub_path
    )

print("TEMPORARY FOLDER:", tmp_sub_path)

nifti_tmp = files. get_files(tmp_sub_path, "", ".nii.gz")[2]
nifti_tmp.sort()
json_tmp = files. get_files(tmp_sub_path, "", ".json")[2]
json_tmp.sort()

# creating a dataframe to log and manipulate the paths
conversion_log = pd.DataFrame.from_dict(
    {
        "nifti_in": nifti_tmp,
        "json_in": json_tmp
    }
)

conversion_log["project_name"] = project_name
conversion_log["sub_id"] = sub_id

conversion_log["sequence_name"] = conversion_log.nifti_in.apply(get_filename)
conversion_log["modality"] = conversion_log.sequence_name.apply(
    lambda x: string_in_dict(x, modality, None)
)

conversion_log["run"] = 1
conversion_log["run"] = conversion_log.apply(run_scrape, axis=1)

conversion_log["bids_file"] = None
conversion_log["bids_file"] = conversion_log.apply(t_weighted, axis=1)

conversion_log.bids_file = conversion_log.apply(retino, axis=1)
conversion_log.bids_file = conversion_log.apply(localiser, axis=1)

# save the log with a timestamp
now = datetime.now()
timestamp = datetime.timestamp(now)

# adding the IntendedFor where applies
conversion_log["IntendedFor"] = None
func = conversion_log.loc[conversion_log.modality == "func"].reset_index()
fmap = conversion_log.loc[conversion_log.modality == "fmap"].reset_index()
fmap.IntendedFor = func.bids_file.apply(lambda x: "func/"+ x)
for ix, row in fmap.iterrows():
    conversion_log.at[row["index"], "IntendedFor"] = row.IntendedFor

# output paths
conversion_log["nifti_out"] = None
conversion_log["json_out"] = None
conversion_log.nifti_out = conversion_log.apply(
    lambda x: bids_directory(x, subject_path, ".nii.gz"), axis=1
)

conversion_log.json_out = conversion_log.apply(
    lambda x: bids_directory(x, subject_path, ".json"), axis=1
)

# TO DO
# copy files from tmp to BIDS
out_df = conversion_log.iloc[conversion_log.json_out.dropna().index]

json_zip = zip(out_df.json_in.to_list(), out_df.json_out.to_list())
nii_zip = zip(out_df.nifti_in.to_list(), out_df.nifti_out.to_list())

[shutil.move(fin, fout) for (fin, fout) in json_zip]
[shutil.move(fin, fout) for (fin, fout) in nii_zip]


# BELOW TO REVIEW
# check whether there are misc files in the bids folder, copy if not
misc_misc = files.get_files("MISC", "", "", wp=False)[2]
bids_misc = files.get_files(project_path,"","", wp=False)[2]
if not all(file in bids_misc for file in misc_misc):
    for misc_file in files.get_folders_files("MISC")[1]:
        shutil.copy(
            misc_file,
            project_path
        )



# open random JSON from converted dataset
with open(out_df.json_out.unique().tolist()[0]) as conv_js:
    converted_json = json.load(conv_js)

# open the participants.json
with open(op.join(project_path, "participants.json")) as pp_js:
    participant_json = json.load(pp_js)

new_entry = {
    "participant_id": sub_id,
    "age": converted_json["PatientBirthDate"],
    "sex": converted_json["PatientSex"],
}

# TSV creation if there is no such file
pp_tsv_path = op.join(project_path, "participants.tsv")
if not op.exists(pp_tsv_path):
    tsv_headers = list(new_entry.keys())
    tsv_dict = {i: [] for i in tsv_headers}
    tsv_df = pd.DataFrame.from_dict(tsv_dict)
    tsv_df.to_csv(pp_tsv_path, sep="\t", index=False)

# updating the participant entry
tsv_df = pd.read_csv(pp_tsv_path, sep="\t", index_col=None)

if new_entry["participant_id"] not in tsv_df["participant_id"].to_list():
    tsv_df = tsv_df.append(new_entry, ignore_index=True)
    tsv_df.to_csv(pp_tsv_path, sep="\t", index=False)
else:
    print(new_entry["participant_id"], "Existing entry")

# task name
bold = conversion_log.bids_file.str.contains("bold", na=False)
for name in ["PRF", "faces", "flicker"]:
    name_file = conversion_log.bids_file.str.contains(name, na=False)
    json_paths = conversion_log.json_out.loc[bold & name_file].tolist()
    for jsonfile in json_paths:
        update_JSON_file(
            jsonfile, 
            "TaskName", 
            name
            )

# conversion of the t1 with fslroi
neurodocker = parameters["neurodocker_path"]
t1 = conversion_log.bids_file.str.contains("T1w", na=False)
t1_path = conversion_log.nifti_out.loc[t1].tolist()[0]
sp.call(
    ["singularity", "run", neurodocker, "fslroi", t1_path, t1_path, "0", "1"]
)

# saving a log
conversion_log.to_csv(
    op.join(bids_path, "{}_{}_converter-log_{}.tsv".format(
        project_name, 
        sub_id, 
        timestamp)
            ),
    sep="\t", 

    index=False
)