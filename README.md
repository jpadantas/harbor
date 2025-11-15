# HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar

HARBOR is a reference implementation for estimating **ship heading** and generating **future-location projection heatmaps** using a **single Synthetic Aperture Radar (SAR)** intensity image. The method is based on morphological processing, skeleton-based shape interpretation, local intensity heuristics, and probabilistic behavioral modeling.

This repository provides supplementary and reproducible material for the article:

> **HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar**  
> *João Paulo A. Dantas, et al., 2025 – Under Review*

---

## Overview

Traditional trajectory estimation approaches require multiple sequential satellite captures or AIS (Automatic Identification System) telemetry, which is often unavailable, incomplete, corrupted, or intentionally disabled.

**HARBOR** addresses the single-image inference case by:

1. Detecting vessel-like bright targets in SAR amplitude data.
2. Skeletonizing detected structures.
3. Extracting endpoints and identifying the longest geodesic pair.
4. Inferring **bow vs. stern** using local intensity comparison.
5. Assigning a **size-based behavioral movement prior**.
6. Projecting future vessel positions over a time horizon using probabilistic heatmaps.

---

## Features

- SAR normalization and visualization
- Morphology-based vessel extraction
- Skeleton endpoint analysis for directional inference
- Local intensity–based bow/stern disambiguation
- Vessel size classification (Small, Medium, Large)
- Simulated forward-trajectory Gaussian heatmap projection
- Exported visual overlays ready for publication

---

## Repository Structure

```text
harbor/
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── src/
│   └── harbor.py
├── data/
│   └── .gitkeep
└── plots/
    └── .gitkeep
```

- **`data/`** — Place input `*.tif` SAR images here  
- **`plots/`** — Output figures automatically saved here  
- **`src/harbor.py`** — Main pipeline implementation  

---

## Installation

It is recommended to use a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

---

## Usage

Place your SAR `.tif` image into the `data/` directory, then run:

```bash
python src/harbor.py     --input data/your_sar_image.tif     --output-dir plots     --threshold 0.99     --future-minutes 360
```

### Optional Parameters

| Argument | Default | Description |
|----------|----------|-------------|
| `--input` | *required* | Path to SAR intensity GeoTIFF |
| `--output-dir` | `plots` | Folder to store exported figures |
| `--threshold` | `0.99` | Normalized intensity threshold |
| `--future-minutes` | `360` | Projection horizon |

### Generated Output Files

| File | Description |
|------|-------------|
| `sar_normalized.png` | Normalized SAR input image |
| `sar_with_directions.png` | Bounding boxes + heading arrows |
| `sar_with_projection_Xmin.png` | Heatmap-projected future positions |

---

## Methodological Assumptions

- SAR input contains clear bright scatterers for vessel detection  
- Skeleton endpoints approximate vessel extremities  
- Higher local intensity corresponds to bow (heuristic; scene-dependent)  
- Movement is forward along inferred heading with Gaussian spread  
- Vessel speed prior correlates with bounding-box area proxy  

Default speed priors (in knots):

| Class | Bounding Box Area | Speed (knots) |
|--------|------------------------|----------------|
| Small  | `< 1000 px²` | ~6 |
| Medium | `< 5000 px²` | ~10 |
| Large  | `>= 5000 px²` | ~15 |

---

## Potential Extensions

- AIS-based calibration or Bayesian fusion  
- Deep-learning skeleton endpoint refinement  
- Real georeferencing and nautical unit projection  
- Dynamic tuning based on wind, sea state, SAR incidence angle  

---

## Citation

Please cite as:

```bibtex
@article{dantas2025harbor,
  title     = {HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar},
  author    = {Dantas, Joao P. A.},
  year      = {2025},
}
```

---

## License

This project is distributed under the **MIT License**.  
See the `LICENSE` file for more details.

---

## Contributions

Contributions are welcome!  
Please open an **Issue** or **Pull Request** if you want to collaborate, improve, or validate the method.
