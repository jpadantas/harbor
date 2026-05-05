# HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

HARBOR is a reference implementation for estimating **ship heading** and generating **future-location projection heatmaps** from a **single Synthetic Aperture Radar (SAR)** intensity image. The method combines morphological processing, skeleton-based shape analysis, local intensity heuristics, and probabilistic behavioral modeling — calibrated with real-world AIS telemetry data.

This repository provides supplementary and reproducible material for the article:

> **HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar**  
> *Joao P. A. Dantas, Paulo F. Silva Filho, Jelton A. Cunha, and Gabriel Dietzsch, 2026*

---

## 📖 Overview

Traditional trajectory estimation requires multiple sequential satellite captures or AIS (Automatic Identification System) telemetry. However, AIS is often unavailable, incomplete, corrupted, or intentionally disabled (e.g., by vessels engaged in illicit activities).

**HARBOR** addresses the **single-image inference** case by:

1. Detecting vessel-like bright targets in SAR amplitude data.
2. Skeletonizing detected structures to determine shape orientation.
3. Inferring **bow vs. stern** using a local intensity heuristic (with relative intensity confidence flagging).
4. Assigning a **size-based behavioral movement prior** calibrated from historical AIS data.
5. Projecting future vessel positions over a configurable time horizon using probabilistic Gaussian heatmaps.

---

## 📂 Repository Structure

```text
harbor/
├── setup.bat                        ← Creates virtualenv + installs dependencies
├── run.bat                          ← Calibrates from AIS and runs the pipeline
├── requirements.txt
├── .gitignore
├── LICENSE
├── README.md
├── src/
│   ├── harbor.py                    ← Main SAR inference pipeline
│   └── calibrate_from_ais.py        ← AIS statistical calibration script
├── scripts/                         ← Auxiliary scripts to generate paper figures (e.g. generate_fig4.py)
├── paper/                           ← LaTeX source files for the manuscript
├── data/
│   ├── AIS_Dataset.xlsx             ← AIS telemetry dataset
│   ├── ais_calibration.json         ← Calibrated movement priors (auto-generated)
│   └── *.tif                        ← Place your input SAR images here
└── outputs/                         ← Generated figures and heatmaps (gitignored)
```

---

## 🚀 Quick Start (Windows)

### 1. First-time setup

Double-click **`setup.bat`** or run from the terminal:
```bat
setup.bat
```
This script will automatically create a Python virtual environment (`.venv/`) and install all required dependencies.

### 2. Run the full pipeline

Place one or more SAR `.tif` images in the `data/` folder, then double-click **`run.bat`** or run:
```bat
run.bat
```
This will automatically:
1. **Calibrate priors** from `data/AIS_Dataset.xlsx` and save to `data/ais_calibration.json`.
2. **Execute HARBOR** on every `*.tif` image found in `data/`, using the calibrated priors.
3. **Save all output figures** to the `outputs/` directory.

---

## 💻 Manual Usage

If you prefer to run the scripts manually, activate the virtual environment first (`.venv\Scripts\activate`).

### Run HARBOR with AIS calibration
```bash
python src/harbor.py \
    --input data/your_sar_image.tif \
    --output-dir outputs \
    --threshold 0.99 \
    --future-minutes 360 \
    --calibration data/ais_calibration.json
```

### Regenerate calibration from AIS data
```bash
python src/calibrate_from_ais.py \
    --input data/AIS_Dataset.xlsx \
    --output data/ais_calibration.json \
    --min-points 5
```

### CLI Arguments Reference

#### `src/harbor.py`
| Argument | Default | Description |
|----------|---------|-------------|
| `--input` | *required* | Path to SAR intensity GeoTIFF |
| `--output-dir` | `outputs` | Folder to store exported figures |
| `--threshold` | `0.99` | Normalized intensity threshold for vessel detection |
| `--future-minutes` | `360` | Projection time horizon (minutes) |
| `--calibration` | *(none)* | Path to AIS calibration JSON; uses hardcoded defaults if omitted |

#### `src/calibrate_from_ais.py`
| Argument | Default | Description |
|----------|---------|-------------|
| `--input` | *required* | Path to AIS dataset (`.xlsx`) |
| `--output` | `data/ais_calibration.json` | Output path for calibration JSON |
| `--min-points` | `5` | Minimum AIS records per vessel to include in statistics |

---

## 📊 AIS-Calibrated Movement Priors

The script `calibrate_from_ais.py` derives empirical speed and angular spread parameters from a real AIS dataset, replacing the original hardcoded estimates. Vessels are classified by **physical length**:

| Category | Length | Sample Count | Speed (calibrated) | Angular Dispersion |
|----------|--------|--------------|-------------------|--------------------|
| **Small** | < 50 m | 2,291 | 4.5 kn | 31.09° |
| **Medium** | 50–200 m | 623 | 10.0 kn | 5.31° |
| **Large** | ≥ 200 m | 387 | 9.6 kn | 2.35° |

> **Key insight:** Large and medium vessels navigate with a much more stable heading than typically assumed. These calibrated values produce significantly tighter and more realistic future-position projections for those classes.

---

## 📑 Generated Outputs

The pipeline generates the following visualizations in the `outputs/` directory:

| File | Description |
|------|-------------|
| `sar_normalized.png` | Normalized SAR input image. |
| `sar_with_directions.png` | Bounding boxes and estimated heading arrows per vessel. Arrows are color-coded by confidence (**Yellow**: High confidence, **Orange**: Low confidence). |
| `sar_with_projection_Xmin.png` | Gaussian heatmap of projected future positions overlaid on the SAR image. |

*Note: Auxiliary scripts located in `scripts/` can be used to generate specific detailed figures (e.g., `scripts/generate_fig4.py` for zoomed sub-regions used in the manuscript).*

---

## 📜 Citation

If you use this code or our methodology in your research, please cite:

```bibtex
@article{dantas2026harbor,
  title  = {HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar},
  author = {Dantas, Joao P. A. and Silva Filho, Paulo F. and Cunha, Jelton A. and Dietzsch, Gabriel},
  year   = {2026},
}
```

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.

---

## 🤝 Contributions

Contributions are welcome! Please open an **Issue** or **Pull Request** to collaborate, improve, or validate the method.
