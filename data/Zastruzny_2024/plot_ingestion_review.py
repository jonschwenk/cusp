"""Map the audited Disko GPS positions on each survey date."""

import csv
from math import cos, radians
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import Normalize


HERE = Path(__file__).resolve().parent


def main():
    with (HERE / "processing_audit.csv").open(encoding="utf-8", newline="") as stream:
        points = list(csv.DictReader(stream))

    origin = points[0]
    lat0, lon0 = float(origin["lat"]), float(origin["lon"])
    for point in points:
        point["east_m"] = (float(point["lon"]) - lon0) * cos(radians(lat0)) * 111_195
        point["north_m"] = (float(point["lat"]) - lat0) * 111_195

    dates = sorted({point["date"] for point in points})
    fig, axes = plt.subplots(1, len(dates), figsize=(8, 5.4), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.15, right=0.79, top=0.79, bottom=0.21, wspace=0.24)
    fig.suptitle("Disko Island frost-table probes", x=0.08, y=0.95, ha="left", fontsize=17)
    fig.text(0.08, 0.875, f"West Greenland  |  South endpoint {lat0:.5f}° N, {abs(lon0):.5f}° W",
             fontsize=10, color="#414854")
    scale = Normalize(vmin=20, vmax=60)

    for date, ax in zip(dates, axes, strict=True):
        visit = [point for point in points if point["date"] == date]
        measured = [point for point in visit if point["decision"] == "retained_direct_probe"]
        unresolved = [point for point in visit if point["decision"] != "retained_direct_probe"]
        dots = ax.scatter([p["east_m"] for p in measured], [p["north_m"] for p in measured],
                          c=[float(p["upstream_frost_depth_cm"]) for p in measured],
                          cmap="viridis", norm=scale, s=39, edgecolors="white",
                          linewidths=0.35, zorder=3)
        excluded = ax.scatter([p["east_m"] for p in unresolved], [p["north_m"] for p in unresolved],
                              marker="x", color="#9c3d22", s=24, linewidths=1, zorder=3)
        ax.set_title(f"{date}\n{len(measured)} retained · {len(unresolved)} unresolved", fontsize=10)
        ax.set(xlim=(-19, 10), ylim=(-5, 85), aspect="equal", xticks=[-15, -5, 5],
               xlabel="Easting (m)")
        ax.grid(alpha=0.25)
        ax.set_axisbelow(True)

    axes[0].set_ylabel("Northing (m)")
    bar_ax = fig.add_axes([0.79, 0.30, 0.028, 0.43])
    fig.colorbar(dots, cax=bar_ax, label="Measured frost-table depth (cm)")
    fig.legend([excluded], ["Exact 120 cm entry excluded pending interpretation"],
               loc="lower left", bbox_to_anchor=(0.064, 0.043), frameon=False, fontsize=9)
    fig.savefig(HERE / "disko_frost_table_review.png", dpi=180, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
