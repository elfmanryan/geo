
#
import pathlib
import sys
import importlib
import cv2
import rasterio
import numpy as np
import xarray as xr
import pandas as pd
from lxml import etree
import gdal
import argparse
import scipy
from geo import change, utils
import xarray as xr
from affine import Affine
from collections import defaultdict
import os
from rasterio.enums import ColorInterp





if __name__ == "__main__":
    ds = xr.open_dataset('rondonia2017.nc')
    xr_ds = change.change_detection(ds, alpha=0.01, ml=7, coord_names=('lat', 'lon', 'time'))



    array0 = xr_ds.isel(time=0)['change'].values.astype(np.ubyte)
    array1 = xr_ds.isel(time=-1)['change'].values.astype(np.ubyte)


    def _get_range_2d_ndarray(ndarray):
        max_ = ndarray.max(axis=0)
        min_ = ndarray.min(axis=0)

        print(f"     max: {max(max_)}, min: {min(min_)} n")

    times = xr_ds.time.values

    for i, t in enumerate(times):
        data2d = xr_ds.isel(time=i)['change'].values.astype(np.ubyte)
        print(f"at time index: {i}:")
        _get_range_2d_ndarray(data2d)



    # print(result0.minmax[0].min, result0.minmax[1].max)
    # print(result0)
    # print(results1)

    #print(array0)
    #print(array1)


    # raster_folder = pathlib.Path('sample_tifs')
    # netcdf_xf_to_raster()


