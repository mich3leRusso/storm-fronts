# storm-fronts

Weather charts and automatic front detection from ERA5 reanalysis data, for **any hour you choose** (ERA5 covers 1940 to a few days ago).

You give one or more hours. For each one, the program downloads exactly the data it needs and makes:

| Chart | What it shows |
|---|---|
| `pressure_<time>.png` | Mean sea-level pressure isobars, every 4 hPa |
| `temperature_<time>.png` | 850 hPa temperature isotherms, every 2 °C |
| `wind_gust_<time>.png` | Instantaneous 10 m wind gust (m/s), labelled lines every 10 m/s |
| `wind_<time>.png` | 10 m wind speed (shading) and direction (arrows), with isobars |
| `cloud_base_<time>.png` | Height of the lowest cloud base above ground (m). White means no cloud |
| `soil_moisture_<time>.png` | Volumetric soil water 7–28 cm deep (m³/m³), land only |
| `fronts_<time>.png` | Warm, cold, occluded and stationary fronts from a pretrained neural network, drawn over the isobars |

The fronts come from the pretrained network of Niebler et al. (2022), *Automated detection and classification of synoptic-scale fronts from atmospheric data grids*, Weather and Climate Dynamics 3, 113–137, https://doi.org/10.5194/wcd-3-113-2022. It was trained on the German weather service (DWD) front analyses over Europe and the North Atlantic. Nothing is trained here: the code only runs the published network.

---

## 1. Installation

You need Linux or macOS, an internet connection, and about 1.5 GB of disk space (Python packages, about 330 MB of data and the 115 MB network).

1. **Install [uv](https://docs.astral.sh/uv/)**, the Python package manager used by this project:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
2. **Install the dependencies** from the project folder. uv installs Python 3.11 and all packages into `.venv/`. PyTorch is the CPU-only build, so no GPU is needed.
   ```bash
   cd storm-fronts
   uv sync
   ```
3. **Download the pretrained network** (115 MB) into `models/`. It isn't kept in git.
   ```bash
   mkdir -p models
   curl -L -o models/niebler_dwd.pth \
     https://media.githubusercontent.com/media/stnie/FrontDetection/master/Scripts_and_Examples/Trained_Examples/DWD/PreTrainedNetwork.pth
   sha256sum models/niebler_dwd.pth
   # must print d7e7b6fae9dfa6558d81224d13f1e67386292c5c13a97ef17f3b1a6620386642
   ```

## 2. ECMWF / Copernicus account (one time only)

The data come from the Copernicus Climate Data Store (CDS).

1. Create a free account at https://cds.climate.copernicus.eu and log in.
2. **Accept the licences.** Without them, downloads fail with `403 ... required licences not accepted`. Go to each dataset page, open the *Download* tab, scroll to *Terms of use* and accept:
   - ERA5 hourly data on single levels: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download
   - ERA5 hourly data on pressure levels: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-pressure-levels?tab=download
   - ERA5 complete (model levels): https://cds.climate.copernicus.eu/datasets/reanalysis-era5-complete?tab=download
3. **Add your API token.** Copy the token from your CDS profile page into a file called `cdsapirc` in the project folder:
   ```
   url: https://cds.climate.copernicus.eu/api
   key: <your-personal-access-token>
   ```
   `cdsapirc` is in `.gitignore`, so your token is never committed.

## 3. Run

Always run from the project folder. Give one or more hours, in UTC, in the format `YYYY-MM-DDTHH:MM`:

```bash
uv run storm-fronts --times 2024-01-21T18:00                       # one hour, all charts
uv run storm-fronts --times 2024-01-21T12:00 2024-01-22T00:00      # several hours
uv run storm-fronts --times 2024-01-21T18:00 --area 65 -40 40 5    # custom lat/lon box: N W S E
uv run storm-fronts --times 2024-01-21T18:00 --charts_features wind_chart wind_gust_chart   # only some charts
uv run storm-fronts --times 2024-01-19T00:00 2024-01-21T21:00 --diff soil_moisture          # + change chart
```

- `--area` defaults to `75 -70 30 40` (North Atlantic + Europe). The network was trained on `75 -50 30 40`, so fronts are most reliable inside that box. West of 50°W they are less reliable.
- Minutes are ignored, because ERA5 is hourly: `18:30` becomes `18:00`.
- `--charts_features` picks which charts to make: `pressure_chart`, `temperature_chart`, `wind_gust_chart`, `wind_chart`, `cloud_base_chart`, `soil_moisture_chart`. Default: all of them.
- `--diff soil_moisture` also makes a **change** chart between the first and the last hour of `--times`: soil water at the last hour minus soil water at the first. Blue means wetter, red drier, white unchanged. It's saved in `charts/<first hour>_to_<last hour>_<area>/`. The absolute soil moisture chart barely changes during a storm, because winter soil is already near saturation. The change chart shows where the rain was actually stored.

For each hour:

1. **Download.** Four small files for that hour only. If they are already there from an earlier run, nothing is downloaded.
   - The model-level data (`reanalysis-era5-complete`) are stored on tape at ECMWF and wait in a shared queue, so each new hour can take **from a few minutes to an hour**. The terminal shows `accepted` → `running` → `successful`. You can follow the request under *Your requests* on the CDS website.
   - If a download is interrupted, nothing broken is left behind. It is saved as `*.nc.part` and only renamed at the end, so just run the command again.
2. **Charts.** Pressure, temperature, then fronts (the network takes a few seconds on CPU).

## 4. Where the output is stored

Each hour + area gets its own folder, named `<hour>_<N>_<W>_<S>_<E>`. For example, `2024-01-21T1800_75_-70_30_40`:

| Path | Content |
|---|---|
| `charts/2024-01-21T1800_75_-70_30_40/pressure_2024-01-21T1800.png` | Pressure chart |
| `charts/2024-01-21T1800_75_-70_30_40/temperature_2024-01-21T1800.png` | Temperature chart |
| `charts/2024-01-21T1800_75_-70_30_40/fronts_2024-01-21T1800.png` | AI fronts chart |
| `data/2024-01-21T1800_75_-70_30_40/era5_msl.nc` | Downloaded: mean sea-level pressure |
| `data/2024-01-21T1800_75_-70_30_40/era5_850.nc` | Downloaded: 850 hPa temperature |
| `data/2024-01-21T1800_75_-70_30_40/era5_ml.nc` | Downloaded: t, q, u, v, w on 9 model levels, surface to about 700 hPa, area + 6° margin (network input; the network is unreliable near the edges, so the margin is dropped after it runs) |
| `data/2024-01-21T1800_75_-70_30_40/era5_lnsp.nc` | Downloaded: log of surface pressure (network input) |
| `models/niebler_dwd.pth` | Pretrained network weights (step 1.3) |

You can delete `data/` at any time to free space. Charts already made stay in `charts/`.

## 5. Project layout

All code is in `src/storm_fronts/`. The data go to `data/` and the charts to `charts/`.

| File | Role |
|---|---|
| `__init__.py` | Command line: for each hour, `download()` then the three charts |
| `download.py` | What to request from the CDS for one hour (`requests`) and the download itself (`download`) |
| `charts.py` | `pressure_chart`, `temperature_chart`, `fronts_chart`, plus small map helpers |
| `ai.py` | Builds the 55 network inputs from the model-level data, exactly as the original code does, and runs the network (`ai_fronts`) |
| `fdu3d.py` | Network definition, copied unchanged from https://doi.org/10.5281/zenodo.5783934 (MIT License) |

## 6. Sharing the project

Share only the code and the environment description. Everything else is rebuilt or downloaded:

| Share | Don't share | Why |
|---|---|---|
| `src/`, `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`, `.gitignore` | | Enough to rebuild everything |
| | `.venv/` | Several GB and tied to your machine. Others run `uv sync` |
| | `cdsapirc` | Your personal CDS token. Each person uses their own (section 2) |
| | `models/` | 115 MB. Downloaded with step 1.3 |
| | `data/` | Re-downloaded automatically |

`.venv/`, `cdsapirc`, `models/` and the `.nc` data files are already in `.gitignore`. Add `charts/` too if you don't want the images committed.

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| `403 Client Error ... required licences not accepted` | Accept the licence of the dataset named in the error (section 2.2) |
| `401` or authentication error | Check `cdsapirc`: it must be in the project folder and contain your token |
| Download stuck on `accepted` / `running` | Normal for model-level data on tape. Leave it running |
| `FileNotFoundError: models/niebler_dwd.pth` | Do step 1.3, and run from the project folder |
| Error parsing the hour | Use `YYYY-MM-DDTHH:MM`, e.g. `2024-01-21T18:00` |
| CDS error for a very recent hour | ERA5 is published about 5 days late. Choose an older hour |

## 8. Limitations

- The fronts haven't been checked against the official Met Office / Met Éireann analysis charts. Compare them before relying on them.
- The fronts are drawn as grid points (0.25°), not smoothed lines with front symbols.
- The network was trained on 2012–2019 data with DWD analyses. It may disagree with the Met Office's style of drawing fronts.
