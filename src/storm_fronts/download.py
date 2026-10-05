"""Download the ERA5 data for one hour from the Copernicus Climate Data Store (CDS)."""
import os

import cdsapi
import xarray as xr

CREDENTIALS = "cdsapirc"  # CDS token file, in the project root
ML_LEVELS = "105/109/113/117/121/125/129/133/137"  # every 4th model level, surface to ~700 hPa
MARGIN = 6  # degrees added around the area for the network: its output is garbage in a ~5 deg band at the edges


def requests(t, area):
    """What to download for hour `t` (pandas Timestamp) and area (N, W, S, E).

    Returns {key: (file name, CDS dataset, request)}.
    """
    n, w, s, e = area
    surface_and_levels = {
        "product_type": "reanalysis",
        "date": f"{t:%Y-%m-%d}",
        "time": [f"{t:%H}:00"],
        "area": [n, w, s, e],
        "data_format": "netcdf",
    }
    # model levels (MARS-style request), on a bigger area so the network's edge band can be cut off
    model_levels = {
        "class": "ea", "expver": "1", "stream": "oper", "type": "an", "levtype": "ml",
        "date": f"{t:%Y-%m-%d}",
        "time": f"{t:%H}",
        "grid": "0.25/0.25",
        "area": f"{min(n + MARGIN, 90)}/{w - MARGIN}/{max(s - MARGIN, -90)}/{e + MARGIN}",
        "format": "netcdf",
    }
    return {
        "surface": ("era5_surface.nc", "reanalysis-era5-single-levels", surface_and_levels | {"variable": [
            "mean_sea_level_pressure",      # msl
            "instantaneous_10m_wind_gust",  # i10fg
            "10m_u_component_of_wind",      # u10
            "10m_v_component_of_wind",      # v10
            "cloud_base_height",            # cbh, NaN where there is no cloud
        ]}),
        # own file: adding it to era5_surface.nc would break folders where that file is already downloaded
        "soil": ("era5_soil.nc", "reanalysis-era5-single-levels",
                 surface_and_levels | {"variable": [
                     "volumetric_soil_water_layer_2",  # swvl2, 7-28 cm deep
                     "land_sea_mask",                  # lsm, to blank the sea (soil water there is meaningless)
                 ]}),
        "p850": ("era5_850.nc", "reanalysis-era5-pressure-levels",
                 surface_and_levels | {"variable": ["temperature"], "pressure_level": ["850"]}),
        # t, u, v, q, w (omega) on the model levels: network input
        "ml": ("era5_ml.nc", "reanalysis-era5-complete",
               model_levels | {"param": "130/131/132/133/135", "levelist": ML_LEVELS}),
        # log of surface pressure (stored on model level 1): network input
        "lnsp": ("era5_lnsp.nc", "reanalysis-era5-complete",
                 model_levels | {"param": "152", "levelist": "1"}),
    }


def download(t, area, folder):
    """Download the data for hour `t` into `folder`, skipping files already there.

    Returns {key: xarray Dataset}, with the keys of `requests`.
    """
    os.environ.setdefault("CDSAPI_RC", CREDENTIALS)
    os.makedirs(folder, exist_ok=True)
    data = {}
    for key, (name, dataset, request) in requests(t, area).items():
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            cdsapi.Client().retrieve(dataset, request, path + ".part")
            os.replace(path + ".part", path)  # only a complete download gets the real name
            print(f"saved {path}")
        data[key] = xr.open_dataset(path)
    return data
