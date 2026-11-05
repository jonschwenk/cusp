"""Render public spatial review of the Yukon observations in CUSP v1.3.

Run from the repository root in the CUSP environment. The checked boundary
subset makes rendering offline. All release observations remain in the review
CSV. Only the thermal depth panel selects one historical observation per site.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = "Yukon_Permafrost_Database"
RELEASE = ROOT / "exports/archived/v1.3/cusp_v1.3.csv"
PROCESSED = HERE / "processed_yukon_permafrost_database.csv"
BASEMAP = HERE / "review/basemap.geojson"
MAP_CRS = "EPSG:3578"
EXTENT = (-143.0, 59.6, -128.0, 69.1)
TIERS = {
    "direct_thaw": ("Measured thaw depth", "o", "#077f83", 46),
    "source_permafrost_bound": ("Source-labelled permafrost bound", "v", "#5052a3", 129),
    "late_summer_frozen_bound": ("Late-summer frozen-ground bound", "s", "#cd8534", 624),
    "two_year_temperature_bound": ("Temperature-derived bound", "D", "#bf437d", 170),
    "explicit_profile_non_detection": ("Bounded non-detection", "X", "#222222", 1),
    "continuous_unfrozen_profile_non_detection": ("Bounded non-detection", "X", "#222222", 3),
}


def prepare_review_rows(release: pd.DataFrame, processed: pd.DataFrame) -> pd.DataFrame:
    """Link immutable release rows to source evidence without changing values."""
    release = release.loc[release["source"].eq(SOURCE)].copy()
    keys = ["site_id", "date"]
    comparison = release.merge(processed, on=keys, validate="one_to_one", suffixes=("", "_source"))
    if len(comparison) != len(release) or len(release) != len(processed):
        raise ValueError("Release and processor rows must match one to one.")
    for column in ("lat", "lon", "pf_observed", "thaw_depth", "pf_depth", "obs_limit"):
        np.testing.assert_allclose(
            comparison[column], comparison[f"{column}_source"], rtol=0, atol=1e-10,
            equal_nan=True, err_msg=f"Source/release mismatch in {column}",
        )
    extra = ["ingestion_tier", "thermal_prior_year", "thermal_year"]
    rows = release.merge(processed[keys + extra], on=keys, validate="one_to_one")
    counts = rows["ingestion_tier"].value_counts().to_dict()
    expected = {tier: spec[3] for tier, spec in TIERS.items()}
    if counts != expected:
        raise ValueError(f"Review requires the pinned v1.3 counts, received {counts}.")

    direct = rows["ingestion_tier"].eq("direct_thaw")
    thermal = rows["ingestion_tier"].eq("two_year_temperature_bound")
    absent = rows["pf_observed"].eq(0)
    rows["review_quantity"] = "presence_upper_bound"
    rows.loc[direct, "review_quantity"] = "measured_thaw_depth"
    rows.loc[absent, "review_quantity"] = "non_detection_observed_reach"
    rows["review_depth_cm"] = rows["obs_limit"].where(~direct, rows["thaw_depth"])
    rows["depth_panel_selected"] = ~thermal
    latest = rows.loc[thermal].sort_values(["thermal_year", "cusp_obs_id"]).groupby("site_id").tail(1)
    rows.loc[latest.index, "depth_panel_selected"] = True
    if rows["review_depth_cm"].isna().any():
        raise ValueError("Every review row must have an interpretable numeric quantity.")
    return rows.sort_values(["ingestion_tier", "site_id", "date"]).reset_index(drop=True)


def project_rows(rows: pd.DataFrame, crs: str = MAP_CRS) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        rows.copy(), geometry=gpd.points_from_xy(rows["lon"], rows["lat"]), crs="EPSG:4326"
    ).to_crs(crs)


def context_map(ax, boundaries: gpd.GeoDataFrame, extent=EXTENT) -> None:
    from matplotlib.ticker import FuncFormatter

    boundaries.plot(ax=ax, facecolor="#f3f1e9", edgecolor="#a1a8ad", linewidth=0.6, zorder=0)
    boundaries.loc[boundaries["name"].eq("Yukon")].boundary.plot(
        ax=ax, color="#5d6972", linewidth=1.1, zorder=1
    )
    transform = Transformer.from_crs("EPSG:4326", MAP_CRS, always_xy=True)
    west, south, east, north = extent
    edge_lon = np.concatenate([np.linspace(west, east, 100)] * 2 + [np.full(100, west), np.full(100, east)])
    edge_lat = np.concatenate([np.full(100, south), np.full(100, north)] + [np.linspace(south, north, 100)] * 2)
    x, y = transform.transform(edge_lon, edge_lat)
    ax.set_xlim(min(x), max(x))
    ax.set_ylim(min(y), max(y))
    for lon in np.arange(-170, -99, 5):
        xx, yy = transform.transform(np.full(100, lon), np.linspace(south, north, 100))
        ax.plot(xx, yy, color="#d1d8dc", linewidth=0.45, zorder=1)
    for lat in np.arange(45, 80, 2):
        xx, yy = transform.transform(np.linspace(west, east, 100), np.full(100, lat))
        ax.plot(xx, yy, color="#d1d8dc", linewidth=0.45, zorder=1)
    for label, lon, lat in (("YUKON", -136, 65.7), ("ALASKA", -142, 65.4), ("N.W.T.", -129.5, 66), ("B.C.", -133, 59.8)):
        xx, yy = transform.transform(lon, lat)
        ax.text(xx, yy, label, fontsize=9, color="#64717c", ha="center", clip_on=True, zorder=2)
    ax.set_facecolor("#eaf3f7")
    ax.set_aspect("equal")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.0f}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.0f}"))
    ax.set_xlabel("Yukon Albers easting (km)", fontsize=9)
    ax.set_ylabel("Yukon Albers northing (km)", fontsize=9)
    ax.tick_params(labelsize=8)


def depth_points(ax, points, marker, norm, size=30):
    return ax.scatter(
        points.geometry.x, points.geometry.y, c=points["review_depth_cm"],
        cmap="viridis", norm=norm, s=size, marker=marker, linewidths=0.45,
        edgecolors="#222222", zorder=4,
    )


def render_maps(rows: pd.DataFrame, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    from matplotlib.ticker import FuncFormatter

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.titleweight": "bold"})
    basemap = gpd.read_file(BASEMAP).to_crs(MAP_CRS)
    points = project_rows(rows)
    fig, ax = plt.subplots(figsize=(10.5, 11))
    fig.subplots_adjust(top=0.89, bottom=0.30, left=0.11, right=0.96)
    context_map(ax, basemap)
    handles = []
    for tier, (label, marker, color, count) in TIERS.items():
        selected = points.loc[points["ingestion_tier"].eq(tier)]
        ax.scatter(selected.geometry.x, selected.geometry.y, s=28, marker=marker,
                   color=color, edgecolors="white", linewidths=0.35, zorder=4)
        if tier == "continuous_unfrozen_profile_non_detection":
            continue
        count_label = 4 if tier == "explicit_profile_non_detection" else count
        handles.append(Line2D([], [], marker=marker, linestyle="", color=color,
                              markersize=7, label=f"{label}  ({count_label})"))
    direct = points.loc[points["ingestion_tier"].eq("direct_thaw")]
    ax.annotate("46 thaw measurements\nclose-up in the depth figure", xy=(direct.geometry.x.mean(), direct.geometry.y.mean()),
                xytext=(24, -8), textcoords="offset points", fontsize=9,
                arrowprops={"arrowstyle": "-", "color": "#34434e"}, zorder=6)
    locator = ax.inset_axes([0.02, 0.69, 0.28, 0.29])
    context_map(locator, basemap, extent=(-165, 45, -105, 77))
    for label in locator.texts:
        label.set_visible(False)
    locator.set_xlabel("")
    locator.set_ylabel("")
    locator.set_xticks([])
    locator.set_yticks([])
    locator.add_patch(Rectangle((ax.get_xlim()[0], ax.get_ylim()[0]),
                                np.diff(ax.get_xlim())[0], np.diff(ax.get_ylim())[0],
                                fill=False, edgecolor="#b34835", linewidth=1.6, zorder=4))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.09), frameon=False, ncol=2, fontsize=9)
    fig.suptitle("Yukon Permafrost Database\nNew CUSP v1.3 observation locations", fontsize=18, y=0.97)
    fig.text(0.5, 0.905, "973 observations  •  831 site IDs  •  827 coordinate pairs  •  1972–2023", ha="center", fontsize=11)
    fig.text(0.07, 0.075,
             "All 973 observations are drawn at their recorded coordinates. Repeated station-years and coincident sites overlap.\n"
             "Symbol size is fixed. This figure shows sampling coverage across dates.\n"
             "Coordinates are WGS84. Projection is Yukon Albers (EPSG 3578). Boundaries are Natural Earth 5.1.2, public domain.\n"
             "Data credit — Yukon Geological Survey, Open Government Licence – Yukon. Review data and code accompany these maps.",
             fontsize=9, va="bottom", linespacing=1.6)
    fig.savefig(output / "sampling_locations.png", dpi=180, facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(14, 17))
    fig.subplots_adjust(top=0.90, bottom=0.24, hspace=0.48, wspace=0.32, left=0.07, right=0.95)
    fig.suptitle("Yukon thaw measurements and depth bounds", fontsize=20, y=0.97)
    fig.text(0.5, 0.935, "Depths below ground surface in centimetres", ha="center", fontsize=12)

    ax = axes[0, 0]
    closeup = project_rows(rows.loc[rows["ingestion_tier"].eq("direct_thaw")], "EPSG:32607")
    artist = depth_points(ax, closeup, "o", Normalize(40, 240), size=58)
    ax.set_aspect("equal")
    x_mid = (closeup.geometry.x.min() + closeup.geometry.x.max()) / 2
    y_mid = (closeup.geometry.y.min() + closeup.geometry.y.max()) / 2
    width = np.ptp(closeup.geometry.x) * 1.24
    ax.set_xlim(x_mid - width / 2, x_mid + width / 2)
    ax.set_ylim(y_mid - width * 0.66, y_mid + width * 0.66)
    ax.grid(color="#d8dee3", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.set_title("A  Measured thaw depth\n46 observations, August–September 2005", fontsize=12, pad=12)
    ax.set_xlabel("UTM zone 7N easting (km)", fontsize=9)
    ax.set_ylabel("UTM zone 7N northing (km)", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.1f}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.1f}"))
    fig.colorbar(artist, ax=ax, fraction=0.045, pad=0.025).set_label("Measured thaw depth (cm)", fontsize=9)
    ax.text(0.02, 0.02, "Near 67.57°N, 139.84°W\nDate-specific thaw boundaries", transform=ax.transAxes,
            fontsize=9, bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9})

    ax = axes[0, 1]
    context_map(ax, basemap)
    norm = Normalize(0, 1000)
    for tier in ("source_permafrost_bound", "late_summer_frozen_bound"):
        selected = points.loc[points["ingestion_tier"].eq(tier)]
        artist = depth_points(ax, selected, TIERS[tier][1], norm, size=19)
    ax.set_title("B  Geotechnical presence upper bounds\n753 investigations, 1972–2023", fontsize=12, pad=12)
    fig.colorbar(artist, ax=ax, fraction=0.045, pad=0.025).set_label("Permafrost-top upper bound (cm)", fontsize=9)
    ax.legend(handles=[Line2D([], [], marker="v", linestyle="", color="#555555", label="129 source-labelled"),
                       Line2D([], [], marker="s", linestyle="", color="#555555", label="624 late-summer assumed (PA)")],
              loc="upper center", bbox_to_anchor=(0.5, -0.18), fontsize=8, frameon=False)

    ax = axes[1, 0]
    context_map(ax, basemap)
    selected = points.loc[points["ingestion_tier"].eq("two_year_temperature_bound") & points["depth_panel_selected"]]
    artist = depth_points(ax, selected, "D", norm, size=44)
    ax.set_title("C  Temperature-based upper bounds\nLatest qualifying evidence at 28 stations", fontsize=12, pad=12)
    fig.colorbar(artist, ax=ax, fraction=0.045, pad=0.025).set_label("Permafrost-top upper bound (cm)", fontsize=9)
    cluster = selected.loc[selected["site_id"].str.contains("Shakwak|BeaverCreek")].to_crs("EPSG:32607")
    detail = ax.inset_axes([0.49, 0.43, 0.48, 0.46])
    depth_points(detail, cluster, "D", norm, size=16)
    detail.set_aspect("equal")
    detail.margins(0.12)
    detail.set_title(f"{len(cluster)} Beaver Creek stations", fontsize=7, pad=5)
    detail.tick_params(labelsize=6)
    detail.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.1f}"))
    detail.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.1f}"))
    detail.set_xlabel("UTM 7N easting (km)", fontsize=6)
    detail.set_ylabel("Northing (km)", fontsize=6)
    detail.grid(color="#d8dee3", linewidth=0.4)
    detail.set_axisbelow(True)
    ax.text(0.5, -0.20, "Latest qualifying endpoints vary 2012–2020\n170 station-year rows retained in the table",
            transform=ax.transAxes, fontsize=8, ha="center", va="top")

    ax = axes[1, 1]
    context_map(ax, basemap)
    selected = points.loc[points["pf_observed"].eq(0)]
    ax.scatter(selected.geometry.x, selected.geometry.y, marker="X", color="#b34835", s=65, zorder=4)
    for _, row in selected.iterrows():
        offset = (8, 4)
        if row["site_id"] == "YGS_BC_Brown":
            offset = (10, 24)
        if row["site_id"] == "YGS_BC_Hwys":
            offset = (10, -20)
        ax.annotate(f"{row['review_depth_cm']:.0f} cm", (row.geometry.x, row.geometry.y),
                    xytext=offset, textcoords="offset points", fontsize=9,
                    arrowprops={"arrowstyle": "-", "color": "#b34835", "linewidth": 0.7},
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9})
    ax.set_title("D  Bounded non-detections\n4 investigations, 2009 and 2023", fontsize=12, pad=12)
    ax.text(0.5, -0.20, "Labels give observed reach\nNo permafrost detected within that reach",
            transform=ax.transAxes, fontsize=8, ha="center", va="top")

    fig.text(0.06, 0.045,
             "A  The measured depths span 40–240 cm. Annual maximum active-layer thickness is unavailable. All 46 rows carry coordinate flag CF.\n"
             "B  Upper bounds span 40–1000 cm. Interval bottoms delimit the bounds. Seasonal frozen-ground interpretation carries PA.\n"
             "C  Each symbol is an existing retained observation. Selected bounds span 100–950 cm. September 1 is an assigned annual label.\n"
             "     Thermal evidence uses consecutive-year pairs, which share support. The displayed station endpoints have different years.\n"
             "D  Observed reaches are 200, 1100, 1550 and 1580 cm. Site-specific profile support is documented in the source audit.\n"
             "All observations are in the linked review CSV. Fixed-size symbols overlap at coincident positions. Panel A has a local map scale.\n"
             "WGS84 input coordinates. Regional projection EPSG 3578, close-up EPSG 32607. Natural Earth 5.1.2 boundaries, public domain.\n"
             "Data credit — Yukon Geological Survey, Open Government Licence – Yukon.",
             fontsize=9, linespacing=1.5, va="bottom")
    fig.savefig(output / "depth_review.png", dpi=180, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE / "review")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = prepare_review_rows(pd.read_csv(RELEASE), pd.read_csv(PROCESSED))
    rows.to_csv(args.output_dir / "review_observations.csv", index=False, lineterminator="\n")
    render_maps(rows, args.output_dir)
    summary = {
        "dataset_version": "v1.3", "rows": len(rows), "sites": int(rows["site_id"].nunique()),
        "coordinate_pairs": len(rows[["lon", "lat"]].drop_duplicates()),
        "date_min": rows["date"].min(), "date_max": rows["date"].max(),
        "tier_counts": rows["ingestion_tier"].value_counts().sort_index().to_dict(),
        "thermal_depth_panel_selection": "Latest retained thermal_year per site, endpoints 2012–2020",
        "thermal_rows": 170, "thermal_depth_panel_symbols": 28,
        "input_sha256_lf": {
            path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for path in (RELEASE, PROCESSED, BASEMAP)
        },
        "outputs_sha256": {name: hashlib.sha256((args.output_dir / name).read_bytes()).hexdigest()
                           for name in ("sampling_locations.png", "depth_review.png", "review_observations.csv")},
    }
    (args.output_dir / "review_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
