"""
Quickly visualize datasets.

TODO: Update to work with xarray Dataset rather than GDAL.

"""
import os
import imageio
import cv2
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
try:
    from mpl_toolkits.basemap import Basemap
except ImportError:
    pass


CMAPS = {
    'jet': cv2.COLORMAP_JET,
    'hsv': cv2.COLORMAP_HSV,
    'hot': cv2.COLORMAP_HOT,
    'cool': cv2.COLORMAP_COOL
}


def _cmap_from_str(cmap):
    if cmap in CMAPS:
        return CMAPS[cmap]
    else:
        return cmap


def colorize(labels, N=None, nan_vals=[], cmap='jet'):
    """
    Apply a color map to a map of integer labels.

    Parameters
    ----------
    labels : np.array, shape (M,N)
        The labeled image.
    N : int, optional
        The number of colors to use (default: 10)

    Returns
    -------
    np.array, shape (M,N,3)
        A colored image in BGR space, ready to be handled by OpenCV.
    """
    if N is None:
        N = min(10, len(np.unique(labels)))
    data = (labels % N) * (255/(N-1))
    data_gray = cv2.cvtColor(data.astype(np.uint8), cv2.COLOR_GRAY2RGB)
    data_color = cv2.applyColorMap(data_gray, _cmap_from_str(cmap))
    for nv in nan_vals:
        data_color[labels == nv] = 0
    # data_color[labels == MASK_VAL] = 255
    return data_color


def to_rgb(data, output=None, vmin=None, vmax=None, pmin=2, pmax=98,
           categorical=False, mask=None, size=None, cmap=None):
    """Turn some data into a numpy array representing an RGB image.

    Parameters
    ----------
    data : list of DataArray
    output : str
        file path
    vmin : float or list of float
        minimum value, or list of values per channel (default: None).
    vmax : float or list of float
        maximum value, or list of values per channel (default: None).
    pmin : float
        lowest percentile to plot (default: 2). Ignored if vmin is passed.
    pmax : float
        highest percentile to plot (default: 98). Ignored if vmax is passed.

    Returns
    -------
    np.ndarray or None
        Returns the generate RGB image if output is None, else returns None.
    """

    if isinstance(data, list):
        n_channels = len(data)
    elif isinstance(data, xr.DataArray) or isinstance(data, np.ndarray):
        n_channels = 1
        data = [data]
    else:
        raise ValueError("`data` must be a DataArray or list of DataArrays")

    values = [np.asarray(d) for d in data]
    shape = data[0].shape + (n_channels,)

    if vmin is not None:
        if isinstance(vmin, (int, float)):
            vmin = [vmin] * n_channels
    if vmax is not None:
        if isinstance(vmax, (int, float)):
            vmax = [vmax] * n_channels

    if categorical:
        colored = colorize(values[0], nan_vals=[0])

    else:
        im = np.empty(shape)

        for i in range(n_channels):
            channel = values[i]
            # Stretch
            if vmin is not None:
                minval = vmin[i]
            else:
                minval = np.percentile(channel, pmin)
            if vmax is not None:
                maxval = vmax[i]
            else:
                maxval = np.percentile(channel, pmax)
            if maxval > minval:
                channel = (channel - minval) / (maxval - minval) * 255

            im[:, :, i] = channel
        im = np.clip(im, 0, 255).astype(np.uint8)
        if n_channels == 1:
            colored = cv2.cvtColor(im[:, :, 0], cv2.COLOR_GRAY2BGR)
            if cmap is not None:
                # colored is now in BGR
                colored = cv2.applyColorMap(colored, _cmap_from_str(cmap))
        else:
            # im is in RGB
            colored = cv2.cvtColor(im, cv2.COLOR_RGB2BGR)
        # if output is not None:
        #     colored = cv2.cvtColor(colored, cv2.COLOR_RGB2BGR)

    if mask is not None:
        colored[~mask] = 0

    if size is not None:
        if size[0] is None:
            size = (int(colored.shape[0] * size[1] / colored.shape[1]),
                    size[1])
        elif size[1] is None:
            size = (size[0],
                    int(colored.shape[1] * size[0] / colored.shape[0]))
        colored = cv2.resize(colored, (size[1], size[0]))

    if output is None:
        return cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
    else:
        cv2.imwrite(output, colored)


def plot_image(src, name, N=1):
    """
    A simple convenience function for plotting a GDAL dataset as an image.

    Parameters
    ----------
    src : osgeo.gdal.Dataset or np.ndarray
        The input data.
    name : str
        The filename including extension.
    N : int, opt
        The number
    """
    try:
        data = src.ReadAsArray()
    except AttributeError:
        data = src

    # RESAMPLE
    data_ = data[::N, ::N]

    plt.figure(figsize=(20, 20))
    plt.imshow(data_, vmin=0, vmax=255)
    plt.savefig(name)


def write_video(ds, path, timestamp=True, width=None, height=None, fps=1,
                codec=None, rgb=lambda d: [d.C11, d.C22, d.C11/d.C22]):
    """
    Create a video from an xarray.Dataset.

    Parameters
    ----------
    ds : xarray.Dataset or xarray.DataArray
        The dataset must have dimensions 'y', 'x', and 'time'.
    path : str
        The output file path of the video.
    timestamp : bool, optional
        Whether to print the timestamp in the upper left corner
        (default: True).
    width : int, optional
        The width of the video (default: ds.dim['x'])
    height : int, optional
        The height of the video (default: ds.dim['y'])
    fps : int, optional
        Frames per second (default: 1).
    codec : str, optional
        fourcc codec (see http://www.fourcc.org/codecs.php)
    rgb : callable, optional
        A callable that takes a Dataset as input and returns a list of
        R, G, B channels. By default will compute the C11, C22, C11/C22
        representation.
        For a DataArray, the video will be grayscale.
    """
    # Font properties for timestamp
    font = cv2.FONT_HERSHEY_SIMPLEX
    bottomLeftCornerOfText = (20, 40)
    fontScale = 1
    fontColor = (0, 0, 0)
    lineType = 2

    # For a DataArray, the video is grayscale.
    if isinstance(ds, xr.DataArray):
        def rgb(d):
            return d

    # Use coords rather than dims so it also works for DataArray
    if height is None:
        height = ds.coords['y'].size
    if width is None:
        width = ds.coords['x'].size

    _, ext = os.path.splitext(path)

    writer_kwargs = {
        'mode': 'I',
        'fps': fps,
    }
    if ext != '.gif':
        writer_kwargs['macro_block_size'] = None
        writer_kwargs['ffmpeg_log_level'] = 'error'
        if codec is None:
            codec = 'libx264'
        writer_kwargs['codec'] = codec

    with imageio.get_writer(path, **writer_kwargs) as writer:
        for t in ds.time.values:
            d = ds.sel(time=t)
            frame = to_rgb(rgb(d))
            frame = cv2.resize(frame, (width, height))
            if timestamp:
                cv2.putText(frame, str(t)[:10],
                            bottomLeftCornerOfText,
                            font,
                            fontScale,
                            fontColor,
                            lineType)
            writer.append_data(frame)
