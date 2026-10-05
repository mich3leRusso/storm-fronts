"""The charts. Each one saves a PNG and returns its path."""
import os

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib

matplotlib.use("Agg")  # charts go to files, no window
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap

from .ai import FRONT_COLOURS, ai_fronts

def wind_gust_chart(data, t, area, folder):
    """Instantaneous wind gust at 10 m above ground, every 2 m/s."""
    gust = data["surface"].i10fg.sel(valid_time=t).squeeze(drop=True)
    ax = _map(area, f"10 m wind gust (m/s), {t:%Y-%m-%d %H:%M} UTC")
    shading = ax.contourf(gust.longitude, gust.latitude, gust, levels=np.arange(0, 52, 2), cmap="viridis", alpha=0.8)
    _colorbar(ax, shading, "gust (m/s)")
    isogusts = ax.contour(gust.longitude, gust.latitude, gust, levels=[10, 20, 30, 40], colors="k", linewidths=0.6)
    ax.clabel(isogusts, fontsize=7)  # lines only every 10 m/s: every 2 m/s is a scribble over land
    return _save(folder, "wind_gust", t)


def wind_chart(data, t, area, folder):
    """10 m wind: speed shading, arrows for direction, isobars for context."""
    u = data["surface"].u10.sel(valid_time=t).squeeze(drop=True)
    v = data["surface"].v10.sel(valid_time=t).squeeze(drop=True)
    speed = np.hypot(u, v)
    ax = _map(area, f"10 m wind (m/s), {t:%Y-%m-%d %H:%M} UTC")
    shading = ax.contourf(speed.longitude, speed.latitude, speed, levels=np.arange(0, 36, 2), cmap="YlOrRd", alpha=0.7)
    _colorbar(ax, shading, "wind speed (m/s)")
    _isobars(ax, data, t, colors="gray", linewidths=0.5)
    step = 8  # one arrow every 8 grid points (2 degrees), otherwise it's a black carpet
    ax.quiver(u.longitude[::step], u.latitude[::step], u[::step, ::step], v[::step, ::step], scale=600, width=0.0015)
    return _save(folder, "wind", t)


def cloud_base_chart(data, t, area, folder):
    """Height of the lowest cloud base above ground; white where there is no cloud."""
    cbh = data["surface"].cbh.sel(valid_time=t).squeeze(drop=True)
    levels = [0, 250, 500, 1000, 1500, 2000, 3000, 4000, 6000, 10000]  # finer at low heights, where it matters
    ax = _map(area, f"Cloud base height (m above ground), {t:%Y-%m-%d %H:%M} UTC")
    shading = ax.contourf(cbh.longitude, cbh.latitude, cbh, levels=levels, cmap="turbo_r",
                          norm=BoundaryNorm(levels, 256))  # equal colour step per band, not per metre; red = low cloud
    _colorbar(ax, shading, "cloud base (m)", ticks=levels)
    return _save(folder, "cloud_base", t)


def soil_moisture_chart(data, t, area, folder):
    """Volumetric soil water in layer 2 (7-28 cm deep), land only."""
    swvl2 = _soil_water(data, t)
    ax = _map(area, f"Soil water 7-28 cm (m³/m³), {t:%Y-%m-%d %H:%M} UTC")
    shading = ax.contourf(swvl2.longitude, swvl2.latitude, swvl2, levels=np.arange(0, 0.55, 0.05), cmap="YlGnBu")
    _colorbar(ax, shading, "volumetric soil water (m³/m³)")
    return _save(folder, "soil_moisture", t)


def soil_moisture_change_chart(data1, t1, data2, t2, area, folder):
    """Change in soil water 7-28 cm deep from t1 to t2: blue wetter, red drier, white unchanged."""
    change = _soil_water(data2, t2) - _soil_water(data1, t1)
    ax = _map(area, f"Soil water 7-28 cm change (m³/m³)\n{t1:%Y-%m-%d %H:%M} -> {t2:%Y-%m-%d %H:%M} UTC")
    levels = np.arange(-0.1, 0.11, 0.02)
    shading = ax.contourf(change.longitude, change.latitude, change, levels=levels, cmap="RdBu", extend="both")
    _colorbar(ax, shading, "change in volumetric soil water (m³/m³)")
    path = os.path.join(folder, f"soil_moisture_change_{t1:%Y-%m-%dT%H%M}_to_{t2:%Y-%m-%dT%H%M}.png")
    plt.savefig(path, dpi=120)
    plt.close()
    return path


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
    ax.set_extent([w, e, s, n], crs=ccrs.PlateCarree())  # without crs, cartopy shows extra latitudes
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linewidth=0.3)
    ax.gridlines(draw_labels=True, linewidth=0.3)
    ax.set_title(title)
    return ax


def _soil_water(data, t):
    """Soil water layer 2 (swvl2), with the sea blanked."""
    soil = data["soil"].sel(valid_time=t).squeeze(drop=True)
    return soil.swvl2.where(soil.lsm > 0.5)


def _colorbar(ax, shading, label, **kw):
    """Colorbar right of the map, far enough not to touch the latitude labels."""
    return plt.colorbar(shading, ax=ax, shrink=0.7, pad=0.1, label=label, **kw)


def _isobars(ax, data, t, **style):
    msl = data["surface"].msl.sel(valid_time=t) / 100  # Pa -> hPa
    return ax.contour(msl.longitude, msl.latitude, msl, levels=np.arange(900, 1080, 4), **style)


def _save(folder, name, t):
    path = os.path.join(folder, f"{name}_{t:%Y-%m-%dT%H%M}.png")
    plt.savefig(path, dpi=120)
    plt.close()
    return path
