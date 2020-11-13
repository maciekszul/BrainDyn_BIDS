import sys
import json
import os
import os.path as op
import subprocess as sp
import pandas as pd
from utilities import files
import bids
import bids_validator
import glob
import nibabel as nb
import dcm2bids as d2b
from func import dcm2niix_func

# BIDS converter script 
# Usage:
# localiser_BIDS <participant number 0-N> <JSON settings file>

# requires "utilities" module either in folder or in PYTHONPATH
# git clone https://github.com/maciekszul/utilities.git
#  
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

raw_path = parameters["raw_path"]

# path to converter
dcm2niix_path = parameters["dcm2niix_path"]

# output path
output_path = parameters["nii_output"]

# collect all folders in the directory
participants = files.get_folders_files(raw_path)[0]

participant = participants[index]
participant_name = participant.split(os.sep)[-1]
participant_output = op.join(output_path, participant_name)
files.make_folder(participant_output)

# getting the directory of the MRI scans for dcm2niix conversion. All operations
# assuming the participant folder contains only "resources" and "scans"
folders_lv1 = files.get_folders_files(participant)[0]
folders_lv1.sort() 
scans = files.get_folders_files(folders_lv1[1])[0]

print("OUTPUT:", participant_output)

try:
    nii_first = files.get_files(participant_output, "", ".nii")[1][0]
    print("Output folder is not empty:", op.exists(nii_first))

except:
    for folder in scans:
        # setting paths
        folder_name = folder.split(os.sep)[-1]
        dicom_path = op.join(folder, "DICOM")
        nii_path = op.join(participant_output, folder_name)
        # files.make_folder(nii_path)

        # run the dcm2niix command line function
        # details and settings in func.py file
        # script ignores the 2D files and acquisition related localisers
        dcm2niix_func(dcm2niix_path, dicom_path, participant_output)

# collect all *.nii and *.json files and create a list of pairings
nii_all = files.get_files(participant_output, "", ".nii")[2]
json_all = files.get_files(participant_output, "", ".json")[2]
nii_all.sort()
json_all.sort()
nii_size = [op.getsize(i)/(1024*1024) for i in nii_all] # size in MB

# data frame to help specify which files are not useful
# selecting all files for now
df_all = pd.DataFrame.from_dict({
        "nii": nii_all,
        "nii_size": nii_size,
        "json": json_all
    })

df_all["seq"] = df_all["nii"].apply(lambda x: x.split(os.sep)[-1][4:])

# dictionary which guides the selection of the dataset
# https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html#fieldmap-data
# to do:
# * folder structure
# * README
# * CHANGES
# * participants.tsv
#       - link with dataset conversion (indicator o a converted dataset)
# * dataset_description.json
# * fieldmaps require an "intended for" entry (MORE INFO)
# * dcm2nii .json has to be modified for the BIDS
# * multiple sessions?
# * where they belong?:
#       mfc_smaps_v1a_QBC
#       mfc_smaps_v1a_Array
#       mfc_seste_b1map_v1f_tra
#       mfc_smaps_v1a_QBC
#       mfc_smaps_v1a_Array
#       
bids_guidance = {
    "anat": [
        "AUTOALIGN", "LOCA_T1_FL2D_SAG", "T1_SAG_1mmiso_p3_TR2100_TI900",
        "T2_SAG_0.8mm_p3_TR3000_TEeff97_pe95"
    ],

    "func": [
        "fMRI_AP_TR1300_2iso_MB4_noPAT_pf78_BW2480_QC", 
        "fMRI_PA_TR1300_2iso_MB4_noPAT_pf78_BW2480_QC",
        "retino_AP", "retino_PA", "localiser_faces_AP", "localiser_faces_PA", 
        "localiser_circles_AP", "localiser_circles_PA",
        "mtw_mfc_3dflash_v1l_R4",
    ],

    "dwi": [
        ""
    ], 

    "fmap": [
        "gre_field_mapping_1acq_rl_tra_e2", 
        "gre_field_mapping_1acq_rl_tra_e2_ph"
    ]
}

