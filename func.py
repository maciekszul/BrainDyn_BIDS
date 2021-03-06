import subprocess as sp
import os
import json


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
            "-f", '%2s-%d', # file name
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


def get_filename(path):
    return path.split(os.sep)[-1].split("-")[-1].split(".")[0].lower()


def string_in_dict(string, dictionary, else_value):
    # returns a first key to a dictionary containing substrings that match
    # a given string. Assumption: ditionary contains list of strings.
    for key in dictionary.keys():
        if any([s in string for s in dictionary[key]]):
            return key
    else:
        return else_value


def t_weighted(x):
    if "t1w" in x["sequence_name"]:
        return "".join(["{}_".format(x["sub_id"]), "T1w"])
    elif ("t2_sag" in x["sequence_name"]) and x["run"] == 1:
        return "".join(["{}_".format(x["sub_id"]), "T2w"])
    else:
        return x["bids_file"]


def retino(x):
    if (x["modality"] == "func") and ("retino" in x["sequence_name"]):
        contrast_label = None
        run = x["sequence_name"][3]
        if "sbref" in x["sequence_name"]:
            contrast_label = "sbref"
        if "sbref" not in x["sequence_name"]:
            contrast_label = "bold"
        return "{0}_task-PRF_dir-AP_run-{1}_{2}".format(
            x["sub_id"],
            run,
            contrast_label
        )
    elif (x["modality"] == "fmap") and ("retino" in x["sequence_name"]):
        run = x["sequence_name"][3]
        dir_label = None
        if "sbref" in x["sequence_name"]:
            dir_label = "sbref"
        if "sbref" not in x["sequence_name"]:
            dir_label = ""
        return "{0}_dir-PRF{1}_run-{2}_epi".format(
            x["sub_id"],
            dir_label,
            run
        )
    else:
        return x["bids_file"]

def localiser(x):
    if (x["modality"] == "func") and ("localiser" in x["sequence_name"]):
        contrast_label = None
        task_subname = None
        if "sbref" in x["sequence_name"]:
            contrast_label = "sbref"
        if "sbref" not in x["sequence_name"]:
            contrast_label = "bold"
        if "circle" in x["sequence_name"]:
            task_subname = "flicker"
        if "faces" in x["sequence_name"]:
            task_subname = "faces"
        return "{0}_task-{1}_dir-AP_{2}".format(
            x["sub_id"],
            task_subname,
            contrast_label
        )
    
    elif (x["modality"] == "fmap") and ("localiser" in x["sequence_name"]):
        dir_label = None
        task_subname = None
        if "sbref" in x["sequence_name"]:
            dir_label = "sbref"
        if "sbref" not in x["sequence_name"]:
            dir_label = ""
        if "circle" in x["sequence_name"]:
            task_subname = "flicker"
        if "faces" in x["sequence_name"]:
            task_subname = "faces"
        return "{0}_dir-{1}{2}_epi".format(
            x["sub_id"],
            task_subname,
            dir_label
        )
    else:  
        return x["bids_file"]


def run_scrape(row):
    if "run" in row.sequence_name:
        return int(row.sequence_name.split("_")[0][3])
    else:
        return row.run


def bids_directory(x, subject_path, ext):
    if x.bids_file != None:
        return os.path.join(subject_path, x.modality, x.bids_file + ext)
    else:
        return None


def update_JSON_file(file_path, key, value, replace=True):
    # adds key with value to the existing JSON file
    # returns a status of the update
    with open(file_path) as json_file:
        json_d = json.load(json_file)
    
    key_exists = any(key == k for k in json_d.keys())
    status = None
    if key_exists and not replace:
        status = "entry_exists_not_replaced"

    else:
        json_d[key] = value
        status = "entry_added_or_replaced" 

    with open(file_path, "w") as out:
        json.dump(json_d, out)
    
    return status