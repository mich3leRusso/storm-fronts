"""storm-fronts: for each chosen hour, download ERA5 and draw pressure, temperature and AI-front charts.

Usage: uv run storm-fronts 2024-01-21T18:00 [more hours] [--area N W S E]
"""
import argparse
import os

import pandas as pd

from .charts import fronts_chart, pressure_chart, temperature_chart
from .download import download

DATA = "data"      # downloaded ERA5 files
CHARTS = "charts"  # output PNGs
DEFAULT_AREA = [75, -70, 30, 40]  # N, W, S, E: North Atlantic + Europe, the network's training area


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("times", nargs="+", help="one or more hours (UTC), e.g. 2024-01-21T18:00")
    parser.add_argument("--area", nargs=4, type=float, metavar=("N", "W", "S", "E"), default=DEFAULT_AREA,
                        help="lat/lon box, default 75 -50 30 40")
    args = parser.parse_args()

    for time in args.times:
        t = pd.Timestamp(time).floor("h")  # ERA5 is hourly
        case = f"{t:%Y-%m-%dT%H%M}_" + "_".join(f"{x:g}" for x in args.area)  # one folder per hour + area
        data = download(t, args.area, os.path.join(DATA, case))

        out = os.path.join(CHARTS, case)
        os.makedirs(out, exist_ok=True)
        for chart in (pressure_chart, temperature_chart, fronts_chart):
            print(chart(data, t, args.area, out))
