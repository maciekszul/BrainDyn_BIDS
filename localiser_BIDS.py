import sys
import json
import os.path as op
from utilities import files
import bids
import bids_validator
import glob

# BIDS converter script 
# Usage:
# localiser_BIDS <participant number 0-N> <JSON settings file>


# checking if the correct argument is used
# default JSON file with settings is "settings.json" 
try:
    index = int(sys.argv[1])
except:
    print("incorrect arguments")
    sys.exit()

try:
    json_file = sys.argv[2]
    print(json_file)
except:
    json_file = "settings.json"
    print(json_file)

# opening a json file
with open(json_file) as pipeline_file:
    parameters = json.load(pipeline_file)

raw_path = parameters["raw_path"]
print(raw_path)

# collect all folders in the directory
participants = files.get_folders_files(raw_path)[0]


