import sys
import shutil
import json
import os
import os.path as op
import subprocess as sp
import pandas as pd
import numpy as np
from utilities import files
# from func import *


def dcm2niix_func(dcm2niix_path, dicom_path, output_path):
    # dcm2niix command line wrapper
    # man: http://manpages.ubuntu.com/manpages/focal/man1/dcm2niix.1.html
    # dcm2niiX version v1.0.20201102 IMPORTANT! Previous versions have
    # different options.

    try:
        sp.call([
            dcm2niix_path, # path set in settings.json
            "-1", # default level of compression (1-9, 1=fastest, 9=smallest)
            "-b", "y", # add bids metadata JSON
            "-ba", "n", # BIDS anonymised
            "-f", '%2s-%p', # file name
            "-i", "y", # ignore localizer and 2D images
            # "-l", "y", # lossless scaling of 16 bit integers
            "-m", "y", # merge slices regardless of acquisition params
            # "-n", # convert series with number, no number for all
            "-o", output_path, # output
            "-t", "n", # save patient details as text file
            "-v", "n", # verbosity level h/y/n
            # "-x", "y", # crop images
            "-y", "y", # compression method y/i/n 
            "-z", "y",
            dicom_path
        ])
        return "converted"
    except:
        return "problems"

raw_path = "/home/mjszul/datasets/xnat_disasters/sub-139/ses-mri/IRM_BRAINDYN_139_20200919_0930"
output_path = "/home/mjszul/datasets/xnat_check"
seq_folders = files.get_folders_files(raw_path)[0]
seq_folders.sort()
seq_folders = seq_folders[:-2]
seq_folders = [op.join(i, "DICOM") for i in seq_folders]

for dicom_path in seq_folders:
    dcm2niix_func(
        "dcm2niix",
        dicom_path,
        output_path
    )
