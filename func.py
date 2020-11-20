from utilities import files
import subprocess as sp
import os
import numpy as np

def dcm2niix_func(dcm2niix_path, dicom_path, output_path, file_name):
    # dcm2niix command line wrapper
    # man: http://manpages.ubuntu.com/manpages/focal/man1/dcm2niix.1.html
    # dcm2niiX version v1.0.20201102 IMPORTANT! Previous versions have
    # different options.

    try:
        sp.call([
            dcm2niix_path, # path set in settings.json
            "-6", # default level of compression (1-9, 1=fastest, 9=smallest)
            "-b", "y", # add bids metadata JSON
            "-ba", "n", # BIDS anonymised
            "-f", file_name, # file name
            "-i", "y", # ignore localizer and 2D images
            # "-l", "y", # lossless scaling of 16 bit integers
            "-m", "y", # merge slices regardless of acquisition params
            # "-n", # convert series with number, no number for all
            "-o", output_path, # output
            "-p", "n", # Philips scaling instead of display scaling (???)
            "-r", "n", # "y" renames files instead of converting
            "-s", "n", # converts a single file
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


def zero_padding_adder(path):
    # returns a filename with zero padded number
    filename = path.split(os.sep)[-1]
    filename = filename.split("_")
    filename[0] = filename[0].zfill(3)
    clean_filename = "_".join(filename)
    return clean_filename


def string_in_dict(string, dictionary):
    # returns a first key to a dictionary containing substrings that match
    # a given string. Assumption: ditionary contains list of strings.
    for key in dictionary.keys():
        if any([s in string for s in dictionary[key]]):
            return key
    else:
        return None


def retino(x):
    # returns a BIDS formatted chunk of the name
    if "retino" in x.seq_name:
        run = "_run-" + x.seq_name[3]
        return "".join(["task-", x.seq_name[5:11], "{}", x.seq_name[11:12], "{}", x.seq_name[12:]]).format(run, "dir-")
    else:
        return x["bids_after_id"]

def localiser(x):
    if "localiser_circle" in x.seq_name:
        return "".join(["task-localiserCIRCLE_", "dir-", x.seq_name[17:]])
    elif "localiser_faces" in x.seq_name:
        return "".join(["task-localiserFACES_", "dir-", x.seq_name[16:]])
    else:
        return x["bids_after_id"]


def other_anat(x):
    other_anat = [
        "mfc", "pdw", "mtw", "autoalign"
    ]
    if any([s in x["seq_name"] for s in other_anat]):
        return "".join(["run-{}_".format(x["run"]), "acq-", x["seq_name"]])
    else:
        return x["bids_after_id"]


def t_weighted(x):
    if "t1_sag" in x["seq_name"]:
        return "".join(["run-{}".format(x["run"]), "_T1w"])
    elif "t2_sag" in x["seq_name"]:
        return "".join(["run-{}".format(x["run"]), "_T2w"])
    else:
        return x["bids_after_id"]


def fmri_qc(x):
    if "fmri_" in x["seq_name"]:
       return "".join(["task-fmriQC", "_dir-", x["seq_name"][5:7], "_run-", str(x["run"]), x["seq_name"][44:]])
    else:
        return x["bids_after_id"]


def bids_out_path(x, subject_path):
    if x.bids_after_id != None:
        path_template = os.path.join(subject_path, x.modality)
        bids_filename = "".join(["sub-", x.sub_id, "_", x.bids_after_id])
        return "".join([path_template, os.sep, bids_filename])
    else:
        return None


def bids_filename(x):
    if x != None:
        return x.split(os.sep)[-1]
    else:
        return None

def bids_directory(x):
    if x != None:
        return os.path.join(os.sep, *x.split(os.sep)[:-1])
    else:
        return None


def dcm2_niix_conv(x, dcm2niix_path):
    # fuction that separately treats different modalities if that is necessary
    if "func" in str(x.modality):
        conv = dcm2niix_func(
            dcm2niix_path,
            x.absolute_path,
            x.bids_dir,
            x.bids_file
        )
        return conv
    elif "anat" in str(x.modality):
        conv = dcm2niix_func(
            dcm2niix_path,
            x.absolute_path,
            x.bids_dir,
            x.bids_file
        )
        return conv
    ########## GRE FIELD MAPPING IS MISSING ##########
    # elif "fmap" in x.modality:
    #     return "converted"
    else:
        return "omitted"