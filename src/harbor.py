"""
HARBOR: Heading Analysis and Reconstruction from Behavioral Observation and Radar

This script loads a SAR intensity image, detects vessel-like objects, estimates
their heading using skeletonization, and generates a probabilistic heatmap of
future vessel positions along the estimated direction of motion.

Pipeline overview:
1. Load SAR image from a GeoTIFF file.
2. Normalize the intensity values.
3. Threshold and apply morphological operations to isolate bright targets.
4. Label connected components and classify them into size categories.
5. Extract skeletons for each vessel and estimate a main axis from the longest
   pair of endpoints.
6. Use local intensity to distinguish bow and stern.
7. Draw bounding boxes and direction arrows on top of the SAR image.
8. Create a global heatmap of future vessel locations based on a simple
   probabilistic motion model.

This script is provided as reference code for a scientific article.
"""

import argparse
import math
import os

import cv2
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import rasterio
from scipy.ndimage import label
from skimage.measure import regionprops
from skimage.morphology import skeletonize
from tqdm import tqdm


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Estimate vessel heading and future-position heatmaps from a SAR image."
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to the SAR intensity GeoTIFF image.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="plots",
        help="Directory where output plots will be saved (default: plots).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.99,
        help="Normalized intensity threshold for vessel detection (default: 0.99).",
    )
    parser.add_argument(
        "--future-minutes",
        type=int,
        default=360,
        help=(
            "Time horizon in minutes used to build the future-position "
            "heatmap (default: 360)."
        ),
    )
    return parser.parse_args()


def ensure_output_dir(output_dir: str) -> None:
    """Create the output directory if it does not exist."""
    os.makedirs(output_dir, exist_ok=True)


def load_sar_image(tif_path: str) -> np.ndarray:
    """
    Load the SAR intensity image (first band) from a GeoTIFF file.

    Parameters
    ----------
    tif_path : str
        Path to the input GeoTIFF image.

    Returns
    -------
    np.ndarray
        2D array with SAR intensity values.
    """
    print(f"[1/8] Loading SAR image from: {tif_path}")
    try:
        with rasterio.open(tif_path) as dataset:
            sar_image = dataset.read(1)
    except Exception as e:
        raise RuntimeError(
            f"Failed to read SAR image from '{tif_path}'. "
            "Please check if the file is a valid, non-corrupted TIFF."
        ) from e

    print(f"      Loaded image with shape {sar_image.shape}, dtype={sar_image.dtype}")
    return sar_image


def normalize_image(image: np.ndarray) -> np.ndarray:
    """
    Normalize the input image to the [0, 1] range.

    Parameters
    ----------
    image : np.ndarray
        Input image.

    Returns
    -------
    np.ndarray
        Normalized image with values in [0, 1].
    """
    print("[2/8] Normalizing SAR image to [0, 1]")
    image_min = image.min()
    image_max = image.max()
    print(f"      Intensity range before normalization: min={image_min}, max={image_max}")

    if image_max == image_min:
        # Avoid division by zero in degenerate cases
        print("      Warning: image has constant intensity. Returning zeros.")
        return np.zeros_like(image, dtype=float)

    sar_norm = (image - image_min) / (image_max - image_min)
    print("      Normalization completed.")
    return sar_norm


def get_local_intensity(image: np.ndarray, row: int, col: int, radius: int = 2) -> float:
    """
    Compute the mean intensity in a local neighborhood around a pixel.

    Parameters
    ----------
    image : np.ndarray
        Normalized SAR image.
    row : int
        Row index of the central pixel.
    col : int
        Column index of the central pixel.
    radius : int, optional
        Radius of the square neighborhood (default: 2).

    Returns
    -------
    float
        Mean intensity in the local window.
    """
    rmin = max(0, row - radius)
    rmax = min(image.shape[0], row + radius + 1)
    cmin = max(0, col - radius)
    cmax = min(image.shape[1], col + radius + 1)
    return float(np.mean(image[rmin:rmax, cmin:cmax]))


def find_skeleton_endpoints(skel: np.ndarray) -> list[tuple[int, int]]:
    """
    Find endpoints in a skeleton image.

    An endpoint is a pixel with value 1 that has exactly one neighbor with value 1
    in its 3x3 neighborhood.

    Parameters
    ----------
    skel : np.ndarray
        Binary skeleton image.

    Returns
    -------
    list of (int, int)
        List of (row, col) coordinates of skeleton endpoints.
    """
    endpoints: list[tuple[int, int]] = []

    # Skip the border to avoid boundary issues.
    for r in range(1, skel.shape[0] - 1):
        for c in range(1, skel.shape[1] - 1):
            if skel[r, c]:
                neighborhood = skel[r - 1 : r + 2, c - 1 : c + 2]
                if np.sum(neighborhood) == 2:
                    endpoints.append((r, c))

    return endpoints


def main() -> None:
    args = parse_args()

    print("==========================================")
    print(" HARBOR: Heading Analysis from SAR Imagery ")
    print("==========================================")
    print(f"Input image   : {args.input}")
    print(f"Output dir    : {args.output_dir}")
    print(f"Threshold     : {args.threshold}")
    print(f"Future minutes: {args.future_minutes}")
    print("")

    # -------------------------------------------------------------------------
    # 0. Prepare output directory
    # -------------------------------------------------------------------------
    print("[0/8] Ensuring output directory exists")
    ensure_output_dir(args.output_dir)

    # -------------------------------------------------------------------------
    # 1–2. Load and normalize SAR image
    # -------------------------------------------------------------------------
    sar_image = load_sar_image(args.input)
    sar_norm = normalize_image(sar_image)

    # Save the normalized SAR image for reference
    print("[3/8] Saving normalized SAR image")
    plt.figure(figsize=(8, 8))
    plt.imshow(sar_norm, cmap="gray")
    plt.axis("off")
    plt.tight_layout()
    norm_path = os.path.join(args.output_dir, "sar_normalized.png")
    plt.savefig(norm_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"      Normalized image saved to: {norm_path}")

    # -------------------------------------------------------------------------
    # 3. Thresholding and morphological operations to detect vessels
    # -------------------------------------------------------------------------
    print("[4/8] Thresholding and morphological filtering")
    threshold_value = args.threshold
    binary_mask = (sar_norm > threshold_value).astype(np.uint8)

    # Morphological opening removes small noise; closing fills small gaps.
    binary_mask = cv2.morphologyEx(
        binary_mask,
        cv2.MORPH_OPEN,
        np.ones((3, 3), np.uint8),
    )
    binary_mask = cv2.morphologyEx(
        binary_mask,
        cv2.MORPH_CLOSE,
        np.ones((15, 15), np.uint8),
    )
    print("      Morphological operations completed.")

    # -------------------------------------------------------------------------
    # 4. Label connected components and compute region properties
    # -------------------------------------------------------------------------
    print("[5/8] Labeling connected components")
    labeled_mask, num_objects = label(binary_mask, structure=np.ones((3, 3)))
    props = regionprops(labeled_mask)
    print(f"      Found {num_objects} labeled objects (before filtering).")

    # Filter out very small regions (likely noise)
    candidate_props = [p for p in props if p.area >= 60]
    print(f"      Number of candidate vessel regions (area >= 60 px): {len(candidate_props)}")

    # -------------------------------------------------------------------------
    # 5. Prepare plot for vessel bounding boxes and direction arrows
    # -------------------------------------------------------------------------
    print("[6/8] Initializing figure for vessel directions")
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(sar_norm, cmap="gray")

    # Vessel size categories and corresponding colors
    colors = {
        "Small": "blue",
        "Medium": "green",
        "Large": "red",
    }

    # Global heatmap aggregating all vessels
    global_heatmap = np.zeros_like(sar_norm, dtype=float)

    # Time horizon for projection (in minutes)
    future_minutes = args.future_minutes

    # -------------------------------------------------------------------------
    # 6. Process each detected vessel-like region
    # -------------------------------------------------------------------------
    print("[7/8] Processing vessel candidates and building heatmap")

    for prop in tqdm(candidate_props, desc="Vessels", unit="obj"):
        # Skip very small regions (already filtered, but keep for safety)
        if prop.area < 60:
            continue

        minr, minc, maxr, maxc = prop.bbox
        bbox_height = maxr - minr
        bbox_width = maxc - minc
        bbox_area = bbox_height * bbox_width

        # Simple size-based classification (in pixels)
        if bbox_area < 1000:
            size_category = "Small"
        elif bbox_area < 5000:
            size_category = "Medium"
        else:
            size_category = "Large"

        # Draw bounding box for the detected vessel
        rect = mpatches.Rectangle(
            (minc, minr),
            bbox_width,
            bbox_height,
            edgecolor=colors[size_category],
            linewidth=2,
            fill=False,
        )
        ax.add_patch(rect)

        # Extract binary region for this vessel and compute its skeleton
        sub_bin = (labeled_mask[minr:maxr, minc:maxc] == prop.label).astype(np.uint8)
        sub_skel = skeletonize(sub_bin)
        endpoints = find_skeleton_endpoints(sub_skel)

        # We need at least two endpoints to estimate a main axis
        if len(endpoints) < 2:
            # No clear skeleton axis
            continue

        # ---------------------------------------------------------------------
        # 6.1. Find the pair of endpoints with maximum distance (main axis)
        # ---------------------------------------------------------------------
        max_dist = 0.0
        best_pair: tuple[tuple[int, int], tuple[int, int]] | None = None

        for i in range(len(endpoints)):
            for j in range(i + 1, len(endpoints)):
                r1, c1 = endpoints[i]
                r2, c2 = endpoints[j]
                dist = (r1 - r2) ** 2 + (c1 - c2) ** 2
                if dist > max_dist:
                    max_dist = dist
                    best_pair = ((r1, c1), (r2, c2))

        if best_pair is None:
            # Degenerate case
            continue

        # Convert local (sub-image) coordinates to global coordinates
        (rA, cA), (rB, cB) = best_pair
        A_row, A_col = rA + minr, cA + minc
        B_row, B_col = rB + minr, cB + minc

        # ---------------------------------------------------------------------
        # 6.2. Estimate bow vs. stern using local intensity statistics
        # ---------------------------------------------------------------------
        intA = get_local_intensity(sar_norm, A_row, A_col)
        intB = get_local_intensity(sar_norm, B_row, B_col)

        # Heuristic: assume the brighter endpoint corresponds to the bow.
        # Adjust this rule if your dataset shows the opposite behavior.
        if intA > intB:
            bow_row, bow_col = A_row, A_col
            stern_row, stern_col = B_row, B_col
        else:
            bow_row, bow_col = B_row, B_col
            stern_row, stern_col = A_row, A_col

        # Vector from bow to stern (direction of motion)
        dx = stern_col - bow_col
        dy = stern_row - bow_row
        norm = math.hypot(dx, dy)

        if norm == 0:
            # Degenerate case: skip if bow and stern are the same point
            continue

        dx_unit = dx / norm
        dy_unit = dy / norm

        # ---------------------------------------------------------------------
        # 6.3. Draw direction arrow from bow in the estimated heading
        # ---------------------------------------------------------------------
        arrow_length = 200  # in pixels
        dx_fixed = dx_unit * arrow_length
        dy_fixed = dy_unit * arrow_length

        # Small lateral offset so the arrow does not overlap the skeleton
        offset = 5  # pixels
        offset_dx = -dy_unit * offset
        offset_dy = dx_unit * offset

        start_x = bow_col + offset_dx
        start_y = bow_row + offset_dy

        ax.arrow(
            start_x,
            start_y,
            dx_fixed,
            dy_fixed,
            width=2.5,
            head_width=14,
            head_length=14,
            length_includes_head=True,
            color="yellow",
        )

        # ---------------------------------------------------------------------
        # 6.4. Generate local future-position heatmap for this vessel
        # ---------------------------------------------------------------------
        # Approximate vessel speeds (in knots) by size category
        speed_knots = {"Small": 6, "Medium": 10, "Large": 15}
        # Angular spread (degrees) around the estimated heading
        spread_deg = {"Small": 30, "Medium": 25, "Large": 20}

        # Convert speed to pixels per minute (scale factor is dataset-specific)
        speed_pix_per_min = speed_knots[size_category] * 0.5
        spread_rad = math.radians(spread_deg[size_category])

        max_radius = int(speed_pix_per_min * future_minutes)
        heatmap_size = 2 * max_radius
        if heatmap_size <= 0:
            # Nothing meaningful to project
            continue

        local_heatmap = np.zeros((heatmap_size, heatmap_size), dtype=float)
        center = heatmap_size // 2

        # Heading angle in image coordinates
        angle_center = math.atan2(dy_unit, dx_unit)

        # Inner loop with tqdm over rows for progress feedback
        for y in tqdm(
            range(heatmap_size),
            desc=f"  Heatmap ({size_category})",
            unit="row",
            leave=False,
        ):
            for x in range(heatmap_size):
                dx_local = x - center
                dy_local = y - center
                distance = math.hypot(dx_local, dy_local)

                # Ignore pixels outside the maximum radius or at the center
                if distance > max_radius or distance == 0:
                    continue

                angle = math.atan2(dy_local, dx_local)
                # Shortest signed angle difference between angle and angle_center
                angle_diff = abs(
                    math.atan2(
                        math.sin(angle - angle_center),
                        math.cos(angle - angle_center),
                    )
                )

                if angle_diff <= spread_rad / 2:
                    # Distance term: Gaussian decay with distance
                    dist_term = math.exp(-(distance**2) / (2 * (max_radius / 2) ** 2))
                    # Angular term: Gaussian decay with angular deviation
                    angle_term = math.exp(-(angle_diff**2) / (2 * (spread_rad / 3) ** 2))
                    prob = dist_term * angle_term
                    local_heatmap[y, x] = prob

        # Normalize local heatmap to [0, 1] if non-zero
        max_local = local_heatmap.max()
        if max_local > 0:
            local_heatmap /= max_local

        # ---------------------------------------------------------------------
        # 6.5. Add local heatmap into the global heatmap (bow-centered)
        # ---------------------------------------------------------------------
        row_center = int(bow_row)
        col_center = int(bow_col)
        r_start = row_center - center
        c_start = col_center - center

        for y in range(heatmap_size):
            for x in range(heatmap_size):
                ry = r_start + y
                cx = c_start + x
                if 0 <= ry < sar_norm.shape[0] and 0 <= cx < sar_norm.shape[1]:
                    global_heatmap[ry, cx] += local_heatmap[y, x]

    # -------------------------------------------------------------------------
    # 7. Add legend and save vessel-direction plot
    # -------------------------------------------------------------------------
    print("[8/8] Saving direction plot and projection heatmap")

    legend_patches = [mpatches.Patch(color=colors[k], label=k) for k in colors]
    ax.legend(handles=legend_patches, loc="upper right")
    ax.axis("off")

    directions_path = os.path.join(args.output_dir, "sar_with_directions.png")
    plt.tight_layout()
    plt.savefig(directions_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"      Vessel direction image saved to: {directions_path}")

    # -------------------------------------------------------------------------
    # 8. Normalize and save the global future-position heatmap
    # -------------------------------------------------------------------------
    if np.max(global_heatmap) > 0:
        norm_heatmap = global_heatmap / np.max(global_heatmap)
    else:
        norm_heatmap = global_heatmap

    plt.figure(figsize=(10, 10))
    plt.imshow(sar_norm, cmap="gray", origin="upper")
    # Use a square-root transform to enhance low probabilities visually
    plt.imshow(norm_heatmap**0.5, cmap="hot", alpha=0.6)
    plt.axis("off")
    plt.tight_layout()

    projection_path = os.path.join(
        args.output_dir,
        f"sar_with_projection_{future_minutes}min.png",
    )
    plt.savefig(projection_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"      Projection heatmap saved to: {projection_path}")
    print("")
    print("Done. HARBOR pipeline finished successfully.")


if __name__ == "__main__":
    main()
