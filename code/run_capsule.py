""" top level run script """

from pathlib import Path
import argparse
import glob
import subprocess
import os
import shutil
import re
from hdmf_zarr.nwb import NWBZarrIO
from pynwb import NWBHDF5IO

data_folder = Path("../data/")
results_folder = Path("../results/")
scratch_folder = Path("../scratch/")


def zarr_to_hdf5(zarr_path):
    hdf5_path = zarr_path.parent / zarr_path.stem
    with NWBZarrIO(str(zarr_path), mode='r') as read_io:  # Create Zarr IO object for read
        with NWBHDF5IO(hdf5_path, 'w') as export_io:  # Create HDF5 IO object for write
            export_io.export(src_io=read_io, write_args=dict(link_data=False))  # Export from Zarr to HDF5
    print(f'hdf5 file made: {hdf5_path}')
    shutil.rmtree(zarr_path)


def hdf5_to_zarr(hdf5_path):
    zarr_path = hdf5_path.parent / hdf5_path.name
    with NWBHDF5IO(hdf5_path, mode='r') as read_io:  # Create HDF5 IO object for read
        with NWBZarrIO(str(zarr_path), 'w') as export_io:  # Create Zarr IO object for write
            export_io.export(src_io=read_io, write_args=dict(link_data=False))  # Export from HDF5 to Zarr
    print(f'zarr file made: {zarr_path}')
    shutil.rmtree(hdf5_path)


def run():
    """ basic run function """
    parser = argparse.ArgumentParser()
    parser.add_argument("--dandiset_id", type=str, required=True)
    parser.add_argument("--raw_movies", type=str, required=True)
    parser.add_argument("--input_nwb_path", type=str, default=f'nwb')
    parser.add_argument("--filetype", type=str, default="hdf5", choices=['hdf5','zarr'])

    args = parser.parse_args()
    raw = args.raw_movies
    dandiset_id = args.dandiset_id
    input_nwb_path = data_folder / Path(args.input_nwb_path)
    print('input dir',input_nwb_path)

    # clear scratch folder
    for file in scratch_folder.iterdir():
        shutil.rmtree(file)
    print(f'cleared scratch folder: {list(scratch_folder.iterdir())}')

    # download dandiset metadata
    download_result = subprocess.run(["dandi", "download", f"DANDI:{dandiset_id}", '--download', 'dandiset.yaml', '--output-dir', str(scratch_folder)], capture_output=True, text=True)
    print('download result', download_result)
    # this folder should exist after successful download
    dandiset_dir = scratch_folder / dandiset_id
 
    # copy data files to scratch folder
    print('copying', input_nwb_path, dandiset_dir)
    shutil.copytree(str(input_nwb_path), str(dandiset_dir), dirs_exist_ok=True)
        # Extract the date from the filename using a regex that looks for YYYY-MM-DD format
    for nwb in dandiset_dir.iterdir():
        if nwb.suffix != ".nwb":
            continue
        match = re.search(r"\d{4}-\d{2}-\d{2}", nwb.stem)
        
        if match:
            date = match.group(0)  # Extract the date
        else:
            raise ValueError(f"No date found in the file name: {nwb.stem}")

    filetype = args.filetype
    print(f'upload filetype: {filetype}')
    # convert zarr nwbs to hdmf nwbs
    for filepath in dandiset_dir.iterdir():
        if filepath.is_dir() and filetype == 'hdf5':
            assert (filepath / ".zattrs").is_file(), f"{filepath.name} is not a valid Zarr folder"
            print(f'converting {filepath} to hdf5 from zarr')
            zarr_to_hdf5(filepath)
        elif filepath.suffix == '.nwb' and filetype == 'zarr':
            hdf5_to_zarr(filepath, output_nwb_dir)
            print(f'converting {filepath} to zarr from hdf5')
            hdf5_to_zarr(filepath)

    # run dandi organize on files to upload
    print('='*64,'organizing in',dandiset_dir)
    result = subprocess.run(["dandi", "organize", '--files-mode', 'move', '--dandiset-path', str(dandiset_dir)], capture_output=True, text=True)
    print('dandi organize run', result)

    # upload files
    print('='*64,'uploading!')

    for item in dandiset_dir.iterdir():
        if item.is_dir():  # Check if it's a directory
            organized_dir = item
            break  # Since we only need the first subdirectory
    for organized_nwbfile in organized_dir.iterdir(): 
        print("ORGANIZED FILE: ", organized_nwbfile) 
        if organized_nwbfile.suffix != ".nwb":
            continue
        dandi_stem = organized_nwbfile.stem
        dandi_stem_split = dandi_stem.split("_")
        
        date = date.replace("-", "+")
        if raw == "True":
            # Insert session_id and replace experiment_id with the extracted date
            dandi_stem_split.insert(1, f"ses-{date}-raw-movies")
        else:
            # Insert session_id and replace experiment_id with the extracted date
            dandi_stem_split.insert(1, f"ses-{date}")
        
        corrected_name = "_".join(dandi_stem_split) + ".nwb"
        organized_nwbfile.rename(organized_nwbfile.parent / corrected_name)
    result = subprocess.run(["dandi", "upload"], cwd=str(dandiset_dir), capture_output=True, text=True)
    print('dandi upload run', result)


if __name__ == "__main__": run()