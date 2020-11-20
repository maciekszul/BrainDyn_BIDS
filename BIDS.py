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
# File "dataset_description.json" has to be provided but it is not necessary for
# running the script.

# Dataset needs to be directly from XNAT with path:
# <recording identifier>/scans/0n_sequence

# requires "utilities" module either in folder or in PYTHONPATH
# git clone https://github.com/maciekszul/utilities.git


################################################################################
# TO DO:
# * GRE FIELD MAPPING !!!!!!!!! (look at "func.py" as well)
# * AUTOMATED BIDS VALIDATION + LOG
# * README (dependencies [python3 + dcm2nix + utilities], usage)
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
raw_df["date"] = date
raw_df["time"] = time
raw_df["modality"] = raw_df.clean_file_name.apply(lambda x: string_in_dict(x, modality))
raw_df["run"] = None
raw_df["bids_after_id"] = None
raw_df["bids_out"] = None
raw_df["bids_dir"] = None
raw_df["bids_file"] = None

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
raw_df.bids_after_id = raw_df.apply(retino, axis=1)
raw_df.bids_after_id = raw_df.apply(localiser, axis=1)
raw_df.bids_after_id = raw_df.apply(other_anat, axis=1)
raw_df.bids_after_id = raw_df.apply(t_weighted, axis=1)
raw_df.bids_after_id = raw_df.apply(fmri_qc, axis=1)
########## GRE FIELD MAPPING IS MISSING ##########

# creating a basic folder structure if nonexistent
project_path = op.join(bids_path, proj)
files.make_folder(project_path)

subject_path = op.join(project_path, "sub-" + sub_id)
files.make_folder(subject_path)

[files.make_folder(op.join(subject_path, m)) for m in modality.keys()]

# paths for log and input for dcm2niix
raw_df.bids_out = raw_df.apply(lambda x: bids_out_path(x, subject_path), axis=1)
raw_df.bids_dir = raw_df.bids_out.apply(bids_directory)
raw_df.bids_file = raw_df.bids_out.apply(bids_filename)

# conversion to nii and BIDS format
# raw_df["conversion_status"] = None
# raw_df.conversion_status = raw_df.apply(
#     lambda x: dcm2_niix_conv(x, dcm2niix_path), axis=1
# )

# save the log with a timestamp
now = datetime.now()
timestamp = datetime.timestamp(now)

# raw_df.to_csv(
#     op.join(bids_path, "{}_sub-{}_converter-log_{}.tsv".format(proj, sub_id, timestamp)),
#     sep="\t", 
#     index=False
# )

# check whether there are misc files in the bids folder, copy if not
misc_misc = files.get_files("MISC", "", "", wp=False)[2]
bids_misc = files.get_files(project_path,"","", wp=False)[2]
if all(file in bids_misc for file in misc_misc):
    for misc_file in files.get_folders_files("MISC")[1]:
        shutil.copy(
            misc_file,
            project_path
        )

# open random JSON from converted dataset
with open("".join([raw_df.bids_out.unique().tolist()[0], ".json"])) as conv_js:
    converted_json = json.load(conv_js)

# open the participans.json
with open(op.join(project_path, "participants.json")) as pp_js:
    participant_json = json.load(pp_js)

new_entry = {
    "participant_id": "sub-" + sub_id,
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

tsv_df = pd.read_csv(pp_tsv_path, sep="\t", index_col=None)

if new_entry["participant_id"] not in tsv_df["participant_id"].to_list():
    tsv_df = tsv_df.append(new_entry, ignore_index=True)
    tsv_df.to_csv(pp_tsv_path, sep="\t", index=False)
else:
    print(new_entry["participant_id"], "Existing entry")