from utilities import files
import subprocess as sp

def dcm2niix_func(dcm2niix_path, dicom_path, nii_path):
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
            "-f", "%3s_%n_%p", # file name
            "-i", "y", # ignore localizer and 2D images
            # "-l", "y", # lossless scaling of 16 bit integers
            "-m", "y", # merge slices regardless of acquisition params
            # "-n", # convert series with number, no number for all
            "-o", nii_path, # output
            "-p", "n", # Philips scaling instead of display scaling (???)
            "-r", "n", # "y" renames files instead of converting
            "-s", "n", # converts a single file
            "-t", "n", # save patient details as text file
            "-v", "n", # verbosity level h/y/n
            # "-x", "y", # crop images
            "-y", "y", # compression method y/i/n 
            dicom_path
        ])
    except:
        print("exception")