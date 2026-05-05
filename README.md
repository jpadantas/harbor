# HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar

HARBOR is a reference implementation for estimating **ship heading** and generating **future-location projection heatmaps** from a **single Synthetic Aperture Radar (SAR)** intensity image. The method combines morphological processing, skeleton-based shape analysis, local intensity heuristics, and probabilistic behavioral modeling — calibrated with real-world AIS telemetry data.

This repository provides supplementary and reproducible material for the article:

> **HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar**  
> *Joao P. A. Dantas, Paulo F. Silva Filho, Jelton A. Cunha, and Gabriel Dietzsch, 2026 – Under Review*

---

## Overview

Traditional trajectory estimation requires multiple sequential satellite captures or AIS (Automatic Identification System) telemetry, which is often unavailable, incomplete, corrupted, or intentionally disabled (e.g., by vessels engaged in illegal activity).

**HARBOR** addresses the **single-image inference** case by:

1. Detecting vessel-like bright targets in SAR amplitude data
2. Skeletonizing detected structures
3. Extracting endpoints and identifying the longest geodesic pair
4. Inferring **bow vs. stern** using local intensity comparison
5. Assigning a **size-based behavioral movement prior** (calibrated from AIS data)
6. Projecting future vessel positions over a configurable time horizon using probabilistic Gaussian heatmaps

---

## Repository Structure

```text
harbor/
├── setup.bat                        ← Creates virtualenv + installs dependencies
├── run.bat                          ← Calibrates from AIS and runs the pipeline
├── requirements.txt
├── .gitignore
├── LICENSE
├── README.md
├── src/
│   ├── harbor.py                    ← Main SAR pipeline
│   └── calibrate_from_ais.py        ← AIS calibration script
├── data/
│   ├── AIS_Dataset.xlsx             ← AIS telemetry dataset (tracked in git)
│   ├── ais_calibration.json         ← Calibrated movement priors (auto-generated)
│   ├── Previsão_de_embarcações.ipynb
│   └── *.tif                        ← Place SAR images here
├── plots/                           ← Generated output figures (gitignored)
└── extra/                           ← Local scratch data (gitignored)
```

---

## Quick Start (Windows)

### 1. First-time setup

Double-click **`setup.bat`** or run from the terminal:

```bat
setup.bat
```

This will:
- Create a Python virtual environment (`.venv/`)
- Install all dependencies from `requirements.txt`

### 2. Run the full pipeline

Place one or more SAR `.tif` images in the `data/` folder, then double-click **`run.bat`** or:

```bat
run.bat
```

This will automatically:
1. **Generate AIS calibration** from `data/AIS_Dataset.xlsx` → `data/ais_calibration.json`
2. **Run HARBOR** on every `*.tif` image found in `data/`, using the calibrated priors
3. **Save all output figures** to `plots/`

---

## Manual Usage

### Run HARBOR with AIS calibration
```bash
python src/harbor.py \
    --input data/your_sar_image.tif \
    --output-dir plots \
    --threshold 0.99 \
    --future-minutes 360 \
    --calibration data/ais_calibration.json
```

### Run HARBOR with hardcoded defaults (no calibration)
```bash
python src/harbor.py \
    --input data/your_sar_image.tif \
    --output-dir plots
```

### Regenerate calibration from AIS data
```bash
python src/calibrate_from_ais.py \
    --input data/AIS_Dataset.xlsx \
    --output data/ais_calibration.json \
    --min-points 5
```

### All CLI arguments

#### `harbor.py`

| Argument | Default | Description |
|----------|---------|-------------|
| `--input` | *required* | Path to SAR intensity GeoTIFF |
| `--output-dir` | `plots` | Folder to store exported figures |
| `--threshold` | `0.99` | Normalized intensity threshold for vessel detection |
| `--future-minutes` | `360` | Projection time horizon (minutes) |
| `--calibration` | *(none)* | Path to AIS calibration JSON; uses hardcoded defaults if omitted |

#### `calibrate_from_ais.py`

| Argument | Default | Description |
|----------|---------|-------------|
| `--input` | *required* | Path to AIS dataset (`.xlsx`) |
| `--output` | `data/ais_calibration.json` | Output path for calibration JSON |
| `--min-points` | `5` | Minimum AIS records per vessel to include in statistics |

---

## AIS-Calibrated Movement Priors

The script `calibrate_from_ais.py` analyses a real AIS dataset to derive empirical speed and angular spread parameters, replacing the original hardcoded estimates.

Vessels are classified by **physical length** (from the AIS `Length` field):

| Category | Length | Vessels | Speed (calibrated) | Spread (calibrated) |
|----------|--------|---------|-------------------|---------------------|
| **Small** | < 50 m | 8 174 | 4.5 kn | 31.09° |
| **Medium** | 50–200 m | 1 587 | 10.0 kn | 5.31° |
| **Large** | ≥ 200 m | 818 | 9.6 kn | 2.35° |

> **Key insight:** Large and medium vessels navigate with a **much more stable heading** than originally assumed (spread 2–5° vs. hardcoded 20–25°). The calibrated values produce significantly tighter, more realistic future-position heatmaps for those classes.

The calibration output is saved as `data/ais_calibration.json` and loaded automatically by `run.bat`.

---

## Generated Output Files

| File | Description |
|------|-------------|
| `plots/sar_normalized.png` | Normalized SAR input image |
| `plots/sar_with_directions.png` | Bounding boxes + heading arrows per vessel |
| `plots/sar_with_projection_Xmin.png` | Gaussian heatmap of projected future positions |

---

## Methodological Assumptions

- SAR input contains clear bright scatterers suitable for vessel detection
- Skeleton endpoints approximate vessel bow and stern extremities
- Higher local intensity at an endpoint corresponds to the bow (heuristic; may be scene-dependent)
- Vessel motion is forward along the inferred heading with Gaussian angular spread
- Speed prior correlates with physical vessel length (calibrated from AIS data)

---

## Citation

Please cite as:

```bibtex
@article{dantas2026harbor,
  title  = {HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar},
  author = {Dantas, Joao P. A. and Silva Filho, Paulo F. and Cunha, Jelton A. and Dietzsch, Gabriel},
  year   = {2026},
}
```

---

## License

Distributed under the **MIT License**. See `LICENSE` for details.

---

## Contributions

Contributions are welcome!  
Please open an **Issue** or **Pull Request** to collaborate, improve, or validate the method.
