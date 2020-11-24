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


# BIDS converter script 
# Usage:
# BIDS_script <participant number 0-N> <JSON settings file>

# Before running the script, the output bids folder has to be created manually
# along with the "participants.json". It is used to create a "participant.tsv".
# More info in the BIDS documentation on:
# https://bids-specification.readthedocs.io/en/stable/03-modality-agnostic-files.html#participants-file

# Dataset needs to be directly from XNAT with path:
# <recording identifier>/scans/0n_sequence

# requires "utilities" module either in folder or in PYTHONPATH
# git clone https://github.com/maciekszul/utilities.git


################################################################################
# TO DO:
# * AUTOMATED BIDS VALIDATION + LOG
################################################################################


# checking if the correct argument is used
# default JSON file with settings is "settings.json" 
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

# modality split JSON file
mod_split_path = parameters["modality_json_path"]
with open(mod_split_path) as mod_file:
    modality = json.load(mod_file)

modality = {k.lower(): [i.lower()for i in v] for k, v in modality.items()}

# get the separate xnat recordings, treated as separate participants
recordings = files.get_folders_files(raw_path)[0]
recordings.sort()
recording = recordings[index] # if there is no such path script will throw an error

# get the project, ID, date and time from the folder name (assuming CERMEP/XNAT naming scheme)
proj, sub_id, date, time = recording.split(os.sep)[1:][-1].split("_")[1:]

raw_seq_path = op.join(raw_path, recording, "scans")
raw_seq = files.get_folders_files(raw_seq_path)[0]

# creating a data frame to store and tidy up all the paths and basic info.
df_dict = {"absolute_path": raw_seq}
raw_df = pd.DataFrame.from_dict(df_dict)
raw_df["clean_file_name"] = raw_df.absolute_path.apply(zero_padding_adder)
raw_df["seq_name"] = raw_df.clean_file_name.apply(lambda x: x[4:])
raw_df["seq_name"] = raw_df.seq_name.str.lower()
raw_df = raw_df.sort_values("clean_file_name", ignore_index=True)
raw_df["project_name"] = proj
raw_df["sub_id"] = sub_id
raw_df["modality"] = raw_df.seq_name.apply(lambda x: string_in_dict(x, modality, None))
raw_df["run"] = None
raw_df["bids_dir"] = None
raw_df["bids_file"] = None
raw_df["IntendedFor"] = None
raw_df["date"] = date
raw_df["time"] = time
################################################################################
# massively PITA way to assign run numbers to unnumbered duplicates and fixing
# the names to conform to BIDS
################################################################################
uniq_seq = raw_df.seq_name.unique().tolist()
for u_seq in uniq_seq:
    chunk = (raw_df.loc[(raw_df.seq_name == u_seq)])
    chunk_range = zip(chunk.index.to_list(), list(np.arange(chunk.shape[0])+1))

    for ix, run_n in chunk_range:
        raw_df.at[ix, "run"] = run_n

# fixing the names

raw_df.bids_file = raw_df.apply(t_weighted, axis=1)
raw_df.bids_file = raw_df.apply(retino, axis=1)
raw_df.bids_file = raw_df.apply(localiser, axis=1)

# adding the IntendedFor where applies
func = raw_df.loc[raw_df.modality == "func"].reset_index()
fmap = raw_df.loc[raw_df.modality == "fmap"].reset_index()
fmap.IntendedFor = func.bids_file.apply(lambda x: "func/"+ x)
for ix, row in fmap.iterrows():
    raw_df.at[row["index"], "IntendedFor"] = row.IntendedFor


# creating a basic folder structure if nonexistent
project_path = op.join(bids_path, proj)
files.make_folder(project_path)

subject_path = op.join(project_path, "sub-" + sub_id)
files.make_folder(subject_path)

[files.make_folder(op.join(subject_path, m)) for m in modality.keys()]

# # paths for log and input for dcm2niix
raw_df.bids_dir = raw_df.apply(lambda x: bids_directory(x, subject_path), axis=1)

# conversion to nii and BIDS format
raw_df["conversion_status"] = None
raw_df.conversion_status = raw_df.apply(
    lambda x: dcm2_niix_conv(x, dcm2niix_path), axis=1
)

# save the log with a timestamp
now = datetime.now()
timestamp = datetime.timestamp(now)

raw_df.to_csv(
    op.join(bids_path, "{}_sub-{}_converter-log_{}.tsv".format(proj, sub_id, timestamp)),
    sep="\t", 

    index=False
)

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
with open(files.get_files(raw_df.bids_dir.unique().tolist()[1], "", ".json")[2][0]) as conv_js:
    converted_json = json.load(conv_js)

# open the participans.json
with open(op.join(project_path, "participants.json")) as pp_js:
    participant_json = json.load(pp_js)

new_entry = {
    "participant_id": "sub-" + sub_id,
    "age": converted_json["PatientBirthDate"],
    "sex": converted_json["PatientSex"],
}

# add fields to JSON files

# task name
bold = raw_df.bids_file.str.contains("bold", na=False)
for name in ["PRF", "circle", "faces"]:
    name_file = raw_df.bids_file.str.contains(name, na=False)
    file_names = raw_df.bids_file.loc[bold & name_file].tolist()
    file_paths = raw_df.bids_dir.loc[bold & name_file].tolist()
    for p, f in zip(file_paths, file_names):
        update_JSON_file(
            op.join(p, f + ".json"), 
            "TaskName", 
            name
            )

# IntendedFor
for ix, row in raw_df.loc[raw_df.IntendedFor.str.contains("bold", na=False)].iterrows():
    update_JSON_file(
        op.join(row.bids_dir, row.bids_file + ".json"),
        "IntendedFor",
        row.IntendedFor + ".nii.gz"
    )

# TSV creation if there is no such file
pp_tsv_path = op.join(project_path, "participants.tsv")
if not op.exists(pp_tsv_path):
    tsv_headers = list(new_entry.keys())
    tsv_dict = {i: [] for i in tsv_headers}
    tsv_df = pd.DataFrame.from_dict(tsv_dict)
    tsv_df.to_csv(pp_tsv_path, sep="\t", index=False)

tsv_df = pd.read_csv(pp_tsv_path, sep="\t", index_col=None)

if new_entry["participant_id"] not in tsv_df["participant_id"].to_list():
    tsv_df = tsv_df.append(new_entry, ignore_index=True)
    tsv_df.to_csv(pp_tsv_path, sep="\t", index=False)
else:
    print(new_entry["participant_id"], "Existing entry")
