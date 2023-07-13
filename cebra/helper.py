#
# (c) All rights reserved. ECOLE POLYTECHNIQUE FÉDÉRALE DE LAUSANNE,
# Switzerland, Laboratory of Prof. Mackenzie W. Mathis (UPMWMATHIS) and
# original authors: Steffen Schneider, Jin H Lee, Mackenzie W Mathis. 2023.
#
# Source code:
# https://github.com/AdaptiveMotorControlLab/CEBRA
#
# Please see LICENSE.md for the full license document:
# https://github.com/AdaptiveMotorControlLab/CEBRA/LICENSE.md
#
"""Collection of helper functions that did not fit into own modules."""

import io
import pathlib
import tempfile
import urllib
import warnings
import zipfile
from typing import List, Union

import numpy as np
import numpy.typing as npt
import requests
import torch

import cebra.data


def download_file_from_url(url: str) -> str:
    """Download a fole from ``url``.

    Args:
        url: Url to fetch for the file.

    Returns:
        The path to the downloaded file.
    """
    with tempfile.NamedTemporaryFile() as tf:
        filename = tf.name + ".h5"
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return filename


def download_file_from_zip_url(url, file="montblanc_tracks.h5"):
    """Directly extract files without writing the archive to disk."""
    with tempfile.TemporaryDirectory() as tf:
        foldername = tf

    resp = urllib.request.urlopen(url)
    with zipfile.ZipFile(io.BytesIO(resp.read())) as zf:
        for member in zf.infolist():
            try:
                zf.extract(member, path=foldername)
            except zipfile.error:
                pass
    return pathlib.Path(foldername) / "data" / file


def _is_integer(y: Union[npt.NDArray, torch.Tensor]) -> bool:
    """Check if the values in ``y`` are :py:class:`int`.

    Args:
        y: An array, either as a :py:func:`numpy.array` or a :py:class:`torch.Tensor`.

    Returns:
        ``True`` if ``y`` contains :py:class:`int`.
    """
    return (isinstance(y, np.ndarray) and np.issubdtype(y.dtype, np.integer)
           ) or (isinstance(y, torch.Tensor) and
                 (not torch.is_floating_point(y) and not torch.is_complex(y)))


def _is_floating(y: Union[npt.NDArray, torch.Tensor]) -> bool:
    """Check if the values in ``y`` are :py:class:`int`.

    Note:
        There is no ``torch`` method to check that the ``dtype`` of a :py:class:`torch.Tensor`
        is a :py:class:`float`, consequently, we check that it is not :py:class:`int` nor
        :py:class:`complex`.

    Args:
        y: An array, either as a :py:func:`numpy.array` or a :py:class:`torch.Tensor`.

    Returns:
        ``True`` if ``y`` contains :py:class:`float`.
    """

    return (isinstance(y, np.ndarray) and
            np.issubdtype(y.dtype, np.floating)) or (isinstance(
                y, torch.Tensor) and torch.is_floating_point(y))


def get_loader_options(dataset: "cebra.data.Dataset") -> List[str]:
    """Return all possible dataloaders for the given dataset.

    Notes:
        This function is deprecated and will be removed in an upcoming version of CEBRA.
        Please use :py:mod:`cebra.data.helper.get_loader_options` instead, which is an
        exact copy.
    """

    import cebra.data.helper
    warnings.warn(
        "The 'get_loader_options' function has been moved to 'cebra.data.helpers' module. "
        "Please update your imports.", DeprecationWarning)
    return cebra.data.helper.get_loader_options
