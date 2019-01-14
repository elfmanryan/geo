"""This script calls the xchange code on an an example folder of date"""


import argparse
import pathlib
# import sys
# import importlib
# import cv2
# import rasterio
# import numpy as np
# import xarray as xr
# import pandas as pd
# from lxml import etree
from osgeo import gdal
from nd import utils
from nd import change
#from nd.change.omnibus_ import _change_detection as cd
from nd.io import rasterio_


parser = argparse.ArgumentParser()
parser.add_argument(
    "--input-dir",
    type=pathlib.Path,
    help="Option to point to raw .zip files in an different folder",)

parser.add_argument(
    "--save-path",
    type=pathlib.Path,
    help="Option to pass a path to save the output",)
args = parser.parse_args()



if __name__ == "__main__":

    raster_folder = pathlib.Path('../../sample_tifs')

    results = list(raster_folder.glob("**/*cd_sq*"))
    print(f"found {len(results)} results")

    if args.save_path:
        save_path = args.save_path
        #also add the date range here?
    else:
        date_1 = str(utils.get_date_time(str(results[0]))[0])
        date_2 = str(utils.get_date_time(str(results[-1]))[0])
        save_folder = pathlib.Path('sample_tifs') / 'outputs'

        save_folder.mkdir(exist_ok=True, parents=True)
        save_path = save_folder / (f"from{date_1}_to{date_2}_cd_.tif")

    # if save_path.exists():
    #     save_path.unlink()

    bands = {1: 'C11', 2: 'C12__im', 3: 'C12__re', 4: 'C22'}

    xds = rasterio_.rasters_to_xarray(results[:4], band_name_dict=bands)
    print(xds)

    #xr = xr.open_dataset('rondonia2017.nc')

    #use omnibus_.py fo change detection

    xdscd = change_detection(xds, alpha=0.01, n=9) #9 multilooks #

    print(xdscd)
    print('has shape {}'.format(xdscd.shape))

   # print('\n')
    # print("gdal info on change ouput raster:")
    # info = gdal.Info(str(save_path.resolve()), format='json', stats=True)
    # print(info)
    #utils.xarray_to_raster(xdscd, save_path=save_path, variable_name='change', set_no_data=255, data_type='uint8')



