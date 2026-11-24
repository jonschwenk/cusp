"""Plot approximate station locations and the seven spring probe rounds."""

import csv
from math import cos, radians
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent


def main() -> None:
    with (HERE / "processing_audit.csv").open(encoding="utf-8", newline="") as stream:
        points = list(csv.DictReader(stream))
    dates = sorted({row["date"] for row in points})
    date_index = {date: index for index, date in enumerate(dates)}
    start = next(row for row in points if row["site_id"] == "A_000")
    lon0, lat0 = float(start["lon"]), float(start["lat"])
    degrees_to_m = 111_195
    lon_to_m = degrees_to_m * cos(radians(lat0))

    fig = plt.figure(figsize=(11, 6.4), layout="constrained")
    grid = fig.add_gridspec(2, 2, width_ratios=[1, 2.45])
    fig.suptitle("Two-Boat Lake spring thaw depths · 19–31 May 2017", fontsize=17)
    station_map = fig.add_subplot(grid[:, 0])
    depth_axes = [fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, 1])]
    missing_color = "#d5d9de"
    cmap = plt.colormaps["viridis"].with_extremes(bad=missing_color)

    for transect, color, ax in zip("AB", ("#167a8b", "#ad4b24"), depth_axes, strict=True):
        visit_rows = [row for row in points if row["upstream_transect"] == transect]
        day_by_station = np.full((len(dates), 101), np.nan)
        for row in visit_rows:
            raw_depth = row["upstream_thaw_depth_cm"]
            if raw_depth:
                station = int(2 * float(row["upstream_offset_m"]))
                day_by_station[date_index[row["date"]], station] = float(raw_depth)
        image = ax.imshow(day_by_station, cmap=cmap, vmin=0, vmax=50, aspect="auto",
                          interpolation="none", origin="upper",
                          extent=(-0.25, 50.25, len(dates) - 0.5, -0.5))
        ax.set_title(f"Transect {transect} · {np.isfinite(day_by_station).sum()} measured depths",
                     color=color, loc="left", fontsize=11)
        ax.set_yticks(range(len(dates)), [f"May {date[-2:]}" for date in dates])
        ax.set_xticks(range(0, 51, 10))

        stations = sorted((row for row in visit_rows if row["date"] == dates[0]),
                          key=lambda row: float(row["upstream_offset_m"]))
        east = [(float(row["lon"]) - lon0) * lon_to_m for row in stations]
        north = [(float(row["lat"]) - lat0) * degrees_to_m for row in stations]
        station_map.plot(east, north, color=color, alpha=0.65, linewidth=0.8)
        station_map.scatter(east, north, s=9, linewidths=0,
                            c=[color if row["upstream_thaw_depth_cm"] else missing_color
                               for row in stations], zorder=3)
        station_map.text(east[0], north[0] + 5, f"{transect} · 0 m", color=color, fontsize=9)
        station_map.text(east[-1], north[-1] + 5, "50 m", color=color, ha="right", fontsize=9)

    station_map.set_title("Interpolated station locations", fontsize=11)
    station_map.set(xlabel="Easting from A start (m)", ylabel="Northing from A start (m)",
                    xlim=(-12, 64), ylim=(-7, 118), aspect="equal")
    station_map.grid(alpha=0.22)
    station_map.set_axisbelow(True)
    station_map.text(0.5, -0.13, f"A start  {lat0:.5f}° N, {abs(lon0):.5f}° W",
                     ha="center", transform=station_map.transAxes, fontsize=8)
    depth_axes[0].tick_params(labelbottom=False)
    depth_axes[1].set_xlabel("Reported offset along transect (m)")
    fig.colorbar(image, ax=depth_axes, label="Spring thaw depth (cm)", shrink=0.90)
    depth_axes[1].text(0, -0.28, "Gray marks unresolved thaw measurements",
                       transform=depth_axes[1].transAxes, fontsize=9, color="#4b525a")
    fig.savefig(HERE / "two_boat_lake_review.png", dpi=170, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
