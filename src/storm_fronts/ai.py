"""Front detection with the pretrained network of Niebler et al. (2022), https://doi.org/10.5194/wcd-3-113-2022.

The network was trained on German weather service (DWD) front analyses over 75-30N, 50W-40E.
Input: ERA5 model levels 105..137 (every 4th) of t, q, u, v, w plus surface pressure.
"""
from functools import cache

import numpy as np
import torch

from .fdu3d import FDU2DNetLargeEmbedCombineModular

WEIGHTS = "models/niebler_dwd.pth"  # relative to the project root
LEVELS = [105, 109, 113, 117, 121, 125, 129, 133, 137]

# Pressure on each model level is p = A + B * surface pressure (L137 coefficients, as in the original code)
A = np.array([11901.339844, 8880.453125, 6168.53125, 3955.960938, 2294.242188, 1143.25, 424.414063, 62.78125, 0.0])
B = np.array([0.576692, 0.680643, 0.770798, 0.843881, 0.8999, 0.94086, 0.969513, 0.9885, 1.0])

# (mean, variance) used to normalise each input, hard-coded in the original reader (readNetCDF.getMeanVar)
NORM = {
    "t": (275.355461, 320.404803),
    "q": (5.57926815e-03, 2.72627785e-05),
    "u": (1.27024432, 67.4232481),
    "v": (0.10213897, 43.6244384),
    "w": (5.87718196e-03, 4.77972548e-02),
    "sp": (86521.1548, 1.49460630e08),
    "kmPerLon": (0.64, 0.09),
}

# output classes 1..4 (0 is "no front") and the colour each is drawn in
FRONT_COLOURS = {"warm": "red", "cold": "blue", "occluded": "purple", "stationary": "green"}


def ai_fronts(ml, lnsp, t, threshold=0.5):
    """Run the network for hour `t`.

    Returns (front, lat, lon): front[i, j] is 0 for no front, else 1 warm, 2 cold, 3 occluded, 4 stationary.
    A grid point is a front when the network gives it at least `threshold` probability of being one.
    """
    x, lat, lon = _inputs(ml, lnsp, t)
    with torch.no_grad():
        scores = _network()(torch.from_numpy(x[None]))
    prob = torch.softmax(scores, dim=1)[0].numpy()  # (5, lat, lon): background, warm, cold, occluded, stationary
    front = np.where(1 - prob[0] >= threshold, prob[1:].argmax(axis=0) + 1, 0)
    return front, lat, lon


@cache
def _network():
    net = FDU2DNetLargeEmbedCombineModular(in_channel=55, out_channel=5, kernel_size=5,
                                           sub_blocks=(3, 3, 3), embedding_factor=6)
    net.load_state_dict(torch.load(WEIGHTS, map_location="cpu"))
    return net.eval()


def _inputs(ml, lnsp, t):
    """The 55 input channels, built exactly as the original reader does.

    Order: t, q, u, v, w, pressure (9 levels each, top to bottom), then km per degree of longitude.
    The grid is cropped to multiples of 8, because the network halves it three times.
    """
    ml = ml.sel(valid_time=t).sel(model_level=LEVELS)
    surface_pressure = np.exp(lnsp.lnsp.sel(valid_time=t).squeeze(drop=True).values)
    ny, nx = ml.sizes["latitude"] // 8 * 8, ml.sizes["longitude"] // 8 * 8
    lat, lon = ml.latitude.values[:ny], ml.longitude.values[:nx]
    assert lat[0] > lat[-1], "network expects latitude north -> south"

    channels = {v: ml[v].values[:, :ny, :nx] for v in ("t", "q", "u", "v", "w")}
    channels["sp"] = A[:, None, None] + B[:, None, None] * surface_pressure[None, :ny, :nx]
    km_per_lon = 6365.831 * np.cos(np.radians(np.abs(lat))) * 2 * np.pi * 0.25 / 360
    km_per_lon = np.clip(km_per_lon, 0.1, 30) / 27.7762
    channels["kmPerLon"] = np.broadcast_to(km_per_lon[:, None], (ny, nx))[None]

    x = np.concatenate([(c - NORM[name][0]) / np.sqrt(NORM[name][1]) for name, c in channels.items()])
    return x.astype(np.float32), lat, lon
