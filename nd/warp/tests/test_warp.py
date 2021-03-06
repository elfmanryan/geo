import pytest
from nd.warp import (Reprojection, Resample, Alignment, get_bounds,
                     get_transform, get_crs, get_common_bounds,
                     get_common_extent, get_extent, get_resolution,
                     get_common_resolution)
from nd.warp.warp_ import _parse_crs, nrows, ncols, get_dims, _reproject
from nd.io import open_dataset, to_netcdf
from nd.testing import (generate_test_dataset, generate_test_dataarray,
                        assert_equal_crs)
import numpy as np
import xarray as xr
from numpy.testing import (assert_equal, assert_almost_equal, assert_raises,
                           assert_raises_regex)
from xarray.testing import assert_equal as xr_assert_equal
from xarray.testing import assert_identical as xr_assert_identical
import os
from rasterio.crs import CRS
from rasterio.coords import BoundingBox
from rasterio.errors import CRSError
import rasterio.warp
from affine import Affine


# Prepare test data
ds_params = [
    ('notime', {
        # Default
        'nx': 10,
        'ny': 20,
        'ntime': None,
        'crs': CRS({'init': 'epsg:4326'})
    }),
    ('notime_mercator', {
        # Default
        'nx': 10,
        'ny': 20,
        'ntime': None,
        'crs': CRS({'init': 'epsg:3395'})
    }),
    ('standard', {
        # Default
        'nx': 10,
        'ny': 20,
        'ntime': 1,
        'crs': CRS({'init': 'epsg:4326'})
    }),
    ('standard_mercator', {
        # Test Mercator Projection
        'nx': 10,
        'ny': 20,
        'ntime': 1,
        'crs': CRS({'init': 'epsg:3395'})
    }),
    ('ntime=5', {
        # Test temporal dimension
        'nx': 10,
        'ny': 20,
        'ntime': 5,
        'crs': CRS({'init': 'epsg:4326'})
    }),
    ('variables', {
        # Test different variables
        'nx': 10,
        'ny': 20,
        'ntime': 1,
        'crs': CRS({'init': 'epsg:4326'}),
        'var': ['v1', 'v2', 'v3']
    })
]

data_path = 'data/'
nc_path = os.path.join(data_path, 'slc.nc')
tif_path = os.path.join(data_path, 'slc.tif')
dim_path = os.path.join(data_path, 'slc.dim')
slc_files = [nc_path, tif_path, dim_path]
epsg4326 = CRS.from_epsg(4326)
sinusoidal = CRS.from_string('+proj=sinu +lon_0=0 +x_0=0 +y_0=0 '
                             '+ellps=WGS84 +datum=WGS84 +units=m no_defs')


def create_snap_ds(*args, **kwargs):
    ds = generate_test_dataset(*args, **kwargs)
    crs = get_crs(ds)
    t = get_transform(ds)
    i2m_string = ','.join(map(str, [t.a, t.d, t.b, t.e, t.c, t.f]))
    del ds.attrs['crs']
    del ds.attrs['transform']
    ds['crs'] = ((), 1)
    attrs = {'crs': crs.wkt,
             'i2m': i2m_string}
    ds['crs'].attrs = attrs
    return ds


@pytest.mark.parametrize('name,kwargs', ds_params)
def test_reprojection(name, kwargs):
    ds = generate_test_dataset(**kwargs)
    crs = _parse_crs('+init=epsg:4326')
    proj = Reprojection(crs=crs)
    reprojected = proj.apply(ds)
    assert_equal_crs(crs, get_crs(reprojected))


def test_reprojection_failure():
    ds = generate_test_dataset()
    transform = get_transform(ds)
    extent = get_extent(ds)
    with assert_raises_regex(
            ValueError, ".* must also specify the `width` and `height`.*"):
        proj = Reprojection(crs=epsg4326, transform=transform)
    with assert_raises_regex(
            ValueError, "Need to provide either `width` and `height` .*"):
        proj = Reprojection(crs=epsg4326, extent=extent)


@pytest.mark.parametrize('name,kwargs', ds_params)
def test_resample_to_resolution_tuple(name, kwargs):
    res = (0.05, 0.01)
    ds = generate_test_dataset(**kwargs)
    resampled = Resample(res=res).apply(ds)
    assert_almost_equal(res, get_resolution(resampled))


@pytest.mark.parametrize('name,kwargs', ds_params)
def test_resample_to_resolution_float(name, kwargs):
    res = 0.05
    ds = generate_test_dataset(**kwargs)
    resampled = Resample(res=res).apply(ds)
    assert_almost_equal((res, res), get_resolution(resampled))


@pytest.mark.parametrize('resample_kwargs', [{'width': 25}, {'height': 25}])
@pytest.mark.parametrize('name,kwargs', ds_params)
def test_resample_to_width_or_height(name, kwargs, resample_kwargs):
    ds = generate_test_dataset(**kwargs)
    resampled = Resample(**resample_kwargs).apply(ds)
    if 'width' in resample_kwargs:
        assert_equal(resample_kwargs['width'], ncols(resampled))
    elif 'height' in resample_kwargs:
        assert_equal(resample_kwargs['height'], nrows(resampled))

    # Make sure aspect ratio is preserved
    assert_equal(
        int(ncols(resampled) / nrows(resampled)),
        int(ncols(ds) / nrows(ds))
    )


@pytest.mark.parametrize('crs', [
    CRS.from_string('+init=epsg:4326')
])
def test_parse_crs(crs):
    assert_equal_crs(crs, _parse_crs(crs))
    assert_equal_crs(crs, _parse_crs(crs.to_string()))
    assert_equal_crs(crs, _parse_crs(crs.to_dict()))
    assert_equal_crs(crs, _parse_crs(crs.wkt))
    assert_equal_crs(crs, _parse_crs(crs.to_epsg()))


@pytest.mark.parametrize('invalidcrs', [
    'not_a_crs'
])
def test_parse_crs_fails(invalidcrs):
    with assert_raises(CRSError):
        _parse_crs(invalidcrs)


@pytest.mark.skip(reason="This currently fails due to SNAP saving "
                         "inconsistent datasets.")
def test_equal_datasets():
    ds0 = open_dataset(slc_files[0])
    for f in slc_files[1:]:
        ds = open_dataset(f)
        assert_equal(ds0['x'].values, ds['x'].values,
                     'x coordinates are not equal')
        assert_equal(ds0['y'].values, ds['y'].values,
                     'y coordinates are not equal')
        assert_equal(get_transform(ds0), get_transform(ds),
                     'transforms are not equal')
        assert_equal_crs(get_crs(ds0), get_crs(ds),
                         'CRS are not equal')
        assert_equal(get_resolution(ds0), get_resolution(ds),
                     'resolutions are not equal')
        assert_equal(get_bounds(ds0), get_bounds(ds),
                     'bounds are not equal')
        assert_equal(get_extent(ds0), get_extent(ds),
                     'extents are not equal')
        ds.close()
    ds0.close()


@pytest.mark.parametrize('name,kwargs', ds_params)
def test_nrows(name, kwargs):
    ds = generate_test_dataset(**kwargs)
    assert_equal(nrows(ds), kwargs['ny'])


@pytest.mark.parametrize('name,kwargs', ds_params)
def test_ncols(name, kwargs):
    ds = generate_test_dataset(**kwargs)
    assert_equal(ncols(ds), kwargs['nx'])


@pytest.mark.parametrize('name,kwargs', ds_params)
def test_get_transform(name, kwargs):
    ds = generate_test_dataset(**kwargs)
    bounds = get_bounds(ds)
    resx = (bounds.right - bounds.left) / (ds.dims['x'] - 1)
    resy = (bounds.bottom - bounds.top) / (ds.dims['y'] - 1)
    xoff = bounds.left
    yoff = bounds.top
    transform = Affine(resx, 0, xoff, 0, resy, yoff)
    assert_equal(
        get_transform(ds), transform
    )


# Test extraction of SNAP-style transform information.
@pytest.mark.parametrize('crs', [
    CRS.from_epsg(4326),
    CRS.from_epsg(3395),
])
def test_get_transform_from_variable(crs):
    ds = generate_test_dataset(crs=crs)
    snap_ds = create_snap_ds(crs=crs)
    assert_equal(
        get_transform(ds),
        get_transform(snap_ds)
    )


@pytest.mark.parametrize('name,kwargs', ds_params)
def test_get_crs(name, kwargs):
    ds = generate_test_dataset(**kwargs)
    assert_equal_crs(get_crs(ds), kwargs['crs'])


@pytest.mark.parametrize('fmt,result', [
    ('proj', '+init=epsg:4326 +no_defs'),
    ('dict', {'init': 'epsg:4326', 'no_defs': True}),
    ('wkt', epsg4326.wkt)
])
def test_get_crs_formats(fmt, result):
    ds = generate_test_dataset(crs=CRS.from_epsg(4326))
    assert_equal(get_crs(ds, format=fmt), result)


# Test extraction of SNAP-style CRS information.
@pytest.mark.parametrize('crs', [
    CRS.from_epsg(4326),
    CRS.from_epsg(3395),
])
def test_get_crs_from_variable(crs):
    snap_ds = create_snap_ds(crs=crs)
    assert_equal_crs(crs, get_crs(snap_ds))


@pytest.mark.parametrize('f', slc_files)
def test_resolution_equal_transform_from_real_data(f):
    ds = open_dataset(f)
    res = get_resolution(ds)
    tf = get_transform(ds)
    ds.close()
    assert_almost_equal(res, (tf.a, abs(tf.e)))


@pytest.mark.parametrize('name,kwargs', ds_params)
def test_get_resolution(name, kwargs):
    ds = generate_test_dataset(**kwargs)
    res = get_resolution(ds)
    bounds = get_bounds(ds)
    resx = abs(bounds.right - bounds.left) / (ncols(ds) - 1)
    resy = abs(bounds.bottom - bounds.top) / (nrows(ds) - 1)
    assert_almost_equal(res, (resx, resy))


def test_get_bounds_dataset():
    bounds = (-10.0, 50.0, 0.0, 60.0)
    ds = generate_test_dataset(extent=bounds)
    assert_equal(bounds, get_bounds(ds))


def test_get_bounds_dataarray():
    bounds = (-10.0, 50.0, 0.0, 60.0)
    da = generate_test_dataarray(extent=bounds)
    assert_equal(bounds, get_bounds(da))


def test_get_extent_dataset():
    extent = (-10.0, 50.0, 0.0, 60.0)
    ds = generate_test_dataset(extent=extent, crs=epsg4326)
    assert_equal(extent, get_extent(ds))


def test_get_extent_dataarray():
    extent = (-10.0, 50.0, 0.0, 60.0)
    da = generate_test_dataarray(extent=extent, crs=epsg4326)
    assert_equal(extent, get_extent(da))


def test_get_common_bounds():
    bounds = [
        (-10.0, 50.0, 0.0, 60.0),
        (-12.0, 40.0, -2.0, 52.0),
        (-13.0, 50.0, -3.0, 60.0),
        (-9.0, 51.0, 1.0, 61.0)
    ]
    datasets = [generate_test_dataset(extent=ext) for ext in bounds]
    assert_equal(
        get_common_bounds(datasets),
        (-13.0, 40.0, 1.0, 61.0)
    )


def test_get_common_extent():
    bounds = [
        (-10.0, 50.0, 0.0, 60.0),
        (-12.0, 40.0, -2.0, 52.0),
        (-13.0, 50.0, -3.0, 60.0),
        (-9.0, 51.0, 1.0, 61.0)
    ]
    common_extent = (-13.0, 40.0, 1.0, 61.0)
    datasets = [generate_test_dataset(extent=ext) for ext in bounds]

    # Reproject such that the projected bounds change,
    # but the extent remains the same:
    proj = Reprojection(crs=sinusoidal)
    datasets_sinu = [proj.apply(ds) for ds in datasets]

    common_bounds = get_common_bounds(datasets_sinu)
    expected_result = BoundingBox(*rasterio.warp.transform_bounds(
        sinusoidal, epsg4326, **common_bounds._asdict()
    ))

    assert_raises(AssertionError, assert_equal,
                  common_bounds, common_extent)
    assert_almost_equal(get_common_extent(datasets_sinu),
                        expected_result)


@pytest.mark.parametrize('mode,fn', [
    ('min', np.min),
    ('max', np.max),
    ('mean', np.mean)
])
def test_get_common_resolution(mode, fn):
    bounds = [
        (-10.0, 50.0, 0.0, 60.0),
        (-12.0, 40.0, -2.0, 52.0),
        (-13.0, 50.0, -3.0, 60.0),
        (-9.0, 51.0, 1.0, 61.0)
    ]
    datasets = [generate_test_dataset(extent=ext) for ext in bounds]
    res = np.array([get_resolution(ds) for ds in datasets])
    common_res = tuple(fn(res, axis=0))
    assert_equal(get_common_resolution(datasets, mode=mode),
                 common_res)


def test_get_common_resolution_invalid_mode():
    datasets = [generate_test_dataset() for i in range(3)]
    with assert_raises_regex(ValueError,
                             "Unsupported mode: 'invalid'"):
        get_common_resolution(datasets, mode='invalid')


def test_get_common_resolution_different_projections():
    crs = [epsg4326, sinusoidal]
    datasets = [generate_test_dataset(crs=c) for c in crs]
    with assert_raises_regex(ValueError,
                             "All datasets must have the same projection."):
        get_common_resolution(datasets)


@pytest.mark.parametrize('generator', [
    generate_test_dataset,
    generate_test_dataarray
])
def test_get_dims(generator):
    dims = {'x': 5, 'y': 10, 'time': 15}
    ds = generator(nx=dims['x'], ny=dims['y'], ntime=dims['time'])
    assert_equal(get_dims(ds), dims)


def test_reproject_no_hidden_effects():
    src_crs = epsg4326
    dst_crs = sinusoidal
    ds = generate_test_dataset(crs=src_crs)
    ds_copy = ds.copy(deep=True)
    projected = _reproject(ds_copy, dst_crs=dst_crs)
    xr_assert_identical(ds, ds_copy)


@pytest.mark.parametrize('generator', [
    generate_test_dataset,
    generate_test_dataarray
])
def test_reproject(generator):
    src_crs = epsg4326
    dst_crs = sinusoidal
    ds = generator(crs=src_crs)
    src_bounds = get_bounds(ds)
    dst_bounds_latlon = BoundingBox(
        left=src_bounds.left - 1,
        bottom=src_bounds.bottom - 1,
        right=src_bounds.right + 1,
        top=src_bounds.top + 1,
    )
    dst_bounds = BoundingBox(*rasterio.warp.transform_bounds(
        src_crs, dst_crs, **dst_bounds_latlon._asdict()
    ))
    dst_width, dst_height = 35, 21
    resx = (dst_bounds.right - dst_bounds.left) / (dst_width - 1)
    resy = (dst_bounds.bottom - dst_bounds.top) / (dst_height - 1)
    res = (abs(resx), abs(resy))
    xoff = dst_bounds.left
    yoff = dst_bounds.top
    dst_transform = Affine(resx, 0, xoff, 0, resy, yoff)

    projected = [
        _reproject(ds, dst_crs=dst_crs, dst_transform=dst_transform,
                   width=dst_width, height=dst_height),
        _reproject(ds, dst_crs=dst_crs, dst_transform=dst_transform,
                   extent=dst_bounds),
        _reproject(ds, dst_crs=dst_crs, extent=dst_bounds,
                   res=res),
        _reproject(ds, dst_crs=dst_crs, extent=dst_bounds,
                   width=dst_width, height=dst_height)
    ]
    for proj in projected[1:]:
        xr_assert_equal(proj, projected[0])
        assert_almost_equal(get_resolution(proj), res)
        assert_almost_equal(get_bounds(proj), dst_bounds)
        assert_almost_equal(get_transform(proj), dst_transform)
        assert_equal_crs(get_crs(proj), dst_crs)


def test_reprojection_nan_values():
    src_crs = epsg4326
    dst_crs = sinusoidal
    ds = generate_test_dataset(crs=src_crs)
    bounds = get_bounds(ds)
    proj = Reprojection(crs=dst_crs)
    warped = proj.apply(ds)
    xgrid, ygrid = np.meshgrid(warped.x, warped.y)
    lon, lat = rasterio.warp.transform(dst_crs, src_crs, xgrid.flatten(),
                                       ygrid.flatten())
    lon = np.array(lon).reshape(xgrid.shape)
    lat = np.array(lat).reshape(ygrid.shape)

    inside_bounds = np.logical_and(
        np.logical_and(lon >= bounds.left, lon <= bounds.right),
        np.logical_and(lat >= bounds.bottom, lat <= bounds.top)
    )
    for v in warped.data_vars:
        if not set(warped[v].dims).issuperset({'y', 'x'}):
            continue
        dim_order = tuple(set(warped[v].dims) - {'y', 'x'}) + ('y', 'x')
        values = warped[v].transpose(*dim_order).values
        # Check that pixels strictly inside the original bounds are not NaN
        assert np.isnan(values[..., inside_bounds]).sum() == 0
        # Pixel outside of the original bounds should be mostly NaN,
        # although some pixels near the edges may have values.
        outside_values = values[..., ~inside_bounds]
        assert np.isnan(outside_values).sum() / outside_values.size > 0.5


def test_reproject_coordinates():
    ds = generate_test_dataset(crs=epsg4326)
    dims = get_dims(ds)
    ds.coords['lat'] = ds['y']
    ds.coords['lon'] = ds['x']
    ds.coords['altitude'] = (('y', 'x'),
                             np.zeros((dims['y'], dims['x'])))
    proj = Reprojection(crs=sinusoidal)
    warped = proj.apply(ds)
    for c in ds.coords:
        if c in ['lat', 'lon']:
            continue
        assert c in warped.coords
        assert_equal(ds[c].dims, warped[c].dims)


@pytest.mark.parametrize('extent', [
    None, (-10.0, 50.0, 0.0, 60.0)
])
@pytest.mark.parametrize('from_files', [True, False])
def test_alignment(tmpdir, extent, from_files):
    datapath = tmpdir.mkdir('data')
    path = tmpdir.mkdir('aligned')
    bounds = [
        (-10.0, 50.0, 0.0, 60.0),
        (-12.0, 40.0, -2.0, 52.0),
        (-13.0, 50.0, -3.0, 60.0),
        (-9.0, 51.0, 1.0, 61.0)
    ]
    datasets = [generate_test_dataset(extent=ext) for ext in bounds]
    if extent is None:
        common_bounds = get_common_bounds(datasets)
    else:
        common_bounds = extent
    files = [str(datapath.join('data_%d.nc' % i))
             for i in range(len(datasets))]
    if from_files:
        for ds, f in zip(datasets, files):
            to_netcdf(ds, f)
        datasets = files
    Alignment(extent=extent).apply(datasets, path=str(path))
    aligned = [open_dataset(str(f)) for f in path.listdir()]
    for ds in aligned:
        assert_equal(get_bounds(ds), common_bounds)
        assert_equal(
            get_transform(ds),
            get_transform(aligned[0])
        )
        xr_assert_equal(ds['x'], aligned[0]['x'])
        xr_assert_equal(ds['y'], aligned[0]['y'])


# def test_align(tmpdir):
#     path = tmpdir.mkdir('aligned')
#     # [llcrnrlon, llcrnrlat, urcrnrlon, urcrnrlat]
#     extent1 = (-10, 50, 0, 60)
#     extent2 = (-8, 52, 2, 62)
#     ds1 = generate_test_dataset(extent=extent1)
#     ds2 = generate_test_dataset(extent=extent2)
#     warp.align([ds1, ds2], path)
#     # Check whether the aligned files have been created
#     assert_equal(os.listdir(path), ['data0_aligned.nc', 'data1_aligned.nc'])
#     # Open the aligned files
#     ds1_aligned = from_netcdf(str(path.join('data0_aligned.nc')))
#     ds2_aligned = from_netcdf(str(path.join('data1_aligned.nc')))
#     assert_equal(
#         warp._get_extent(ds1_aligned),
#         warp._get_extent(ds2_aligned)
#     )
#     xr_assert_equal(
#         ds1_aligned.lat, ds2_aligned.lat
#     )
#     xr_assert_equal(
#         ds1_aligned.lon, ds2_aligned.lon
#     )
