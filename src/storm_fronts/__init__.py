"""storm-fronts: for each chosen hour, download ERA5 and draw pressure, temperature and AI-front charts.

Usage: uv run storm-fronts 2024-01-21T18:00 [more hours] [--area N W S E]
"""
import argparse
import os

import pandas as pd

from .charts import (cloud_base_chart, fronts_chart, pressure_chart, soil_moisture_change_chart, soil_moisture_chart,
                     temperature_chart, wind_chart, wind_gust_chart)
from .download import download

DATA = "data"      # downloaded ERA5 files
CHARTS = "charts"  # output PNGs
DEFAULT_AREA = [75, -70, 30, 40]  # N, W, S, E: North Atlantic + Europe, the network's training area
FEATURES= {"pressure_chart": pressure_chart, 
           "temperature_chart": temperature_chart,
            "wind_gust_chart": wind_gust_chart,
            "wind_chart": wind_chart, 
            "cloud_base_chart": cloud_base_chart,
            "soil_moisture_chart": soil_moisture_chart,
           }
# changes between the first and the last of --times
DIFFS = {"soil_moisture": soil_moisture_change_chart}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--times", nargs="+", help="one or more hours (UTC), e.g. 2024-01-21T18:00")
    parser.add_argument("--area", default=DEFAULT_AREA, nargs=4, type=float, metavar=("N", "W", "S", "E"), help="lat/lon box, default 75 -50 30 40")
    parser.add_argument("--charts_features", default=FEATURES.keys(), nargs="+", help=f"Implemented features: {FEATURES}")
    parser.add_argument("--diff", nargs="+", choices=DIFFS, default=[],
                        help="change charts between the first and the last of --times")
    args = parser.parse_args()

    area_name = "_".join(f"{x:g}" for x in args.area)
    data_by_time = {}
    for time in args.times:
        t = pd.Timestamp(time).floor("h")
        case = f"{t:%Y-%m-%dT%H%M}_{area_name}"  # one folder per hour + area
        data = data_by_time[t] = download(t, args.area, os.path.join(DATA, case))

        out = os.path.join(CHARTS, case)
        os.makedirs(out, exist_ok=True)
        for chart in args.charts_features:
            print(FEATURES[chart](data, t, args.area, out))

    if args.diff:
        (t1, data1), (t2, data2) = list(data_by_time.items())[0], list(data_by_time.items())[-1]
        out = os.path.join(CHARTS, f"{t1:%Y-%m-%dT%H%M}_to_{t2:%Y-%m-%dT%H%M}_{area_name}")
        os.makedirs(out, exist_ok=True)
        for diff in args.diff:
            print(DIFFS[diff](data1, t1, data2, t2, args.area, out))
