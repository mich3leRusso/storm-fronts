"""The three charts: pressure, temperature, AI fronts. Each one saves a PNG and returns its path."""
import os

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib

matplotlib.use("Agg")  # charts go to files, no window
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap

from .ai import FRONT_COLOURS, ai_fronts


def pressure_chart(data, t, area, folder):
    """Mean sea-level pressure isobars every 4 hPa."""
    ax = _map(area, f"Mean sea-level pressure (hPa), {t:%Y-%m-%d %H:%M} UTC")
    ax.clabel(_isobars(ax, data, t, colors="k", linewidths=0.7), fontsize=7)
    return _save(folder, "pressure", t)


def temperature_chart(data, t, area, folder):
    """850 hPa isotherms every 2 C."""
    t850 = data["p850"].t.sel(valid_time=t).squeeze(drop=True) - 273.15  # K -> C
    levels = np.arange(-50, 40, 2)
    ax = _map(area, f"850 hPa temperature (C), {t:%Y-%m-%d %H:%M} UTC")
    ax.contourf(t850.longitude, t850.latitude, t850, levels=levels, cmap="RdBu_r", alpha=0.6)
    isotherms = ax.contour(t850.longitude, t850.latitude, t850, levels=levels, colors="k", linewidths=0.5)
    ax.clabel(isotherms, fontsize=7)
    return _save(folder, "temperature", t)


def fronts_chart(data, t, area, folder):
    """Fronts from the pretrained network, over the isobars."""
    front, lat, lon = ai_fronts(data["ml"], data["lnsp"], t)

    # the network ran on area + margin: keep only the requested area
    n, w, s, e = area
    inside = (lat[:, None] <= n) & (lat[:, None] >= s) & (lon[None, :] >= w) & (lon[None, :] <= e)
    front = np.where(inside & (front > 0), front, np.nan)

    legend = ", ".join(f"{colour} {name}" for name, colour in FRONT_COLOURS.items())
    ax = _map(area, f"AI fronts ({legend})\n{t:%Y-%m-%d %H:%M} UTC")
    _isobars(ax, data, t, colors="gray", linewidths=0.6)
    ax.pcolormesh(lon, lat, front, cmap=ListedColormap(list(FRONT_COLOURS.values())), vmin=0.5, vmax=4.5)
    return _save(folder, "fronts", t)


def _map(area, title):
    """Empty map of the area with coastlines, borders and a lat/lon grid."""
    n, w, s, e = area
    ax = plt.figure(figsize=(10, 6)).add_subplot(projection=ccrs.PlateCarree())
    ax.set_extent([w, e, s, n])
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3)
    ax.gridlines(draw_labels=True, linewidth=0.3)
    ax.set_title(title)
    return ax


def _isobars(ax, data, t, **style):
    msl = data["msl"].msl.sel(valid_time=t) / 100  # Pa -> hPa
    return ax.contour(msl.longitude, msl.latitude, msl, levels=np.arange(900, 1080, 4), **style)


def _save(folder, name, t):
    path = os.path.join(folder, f"{name}_{t:%Y-%m-%dT%H%M}.png")
    plt.savefig(path, dpi=120)
    plt.close()
    return path
