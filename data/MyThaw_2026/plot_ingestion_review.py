"""Show myThaw site locations and date-specific transect medians."""

from collections import defaultdict
import csv
from datetime import date
from pathlib import Path
from statistics import median

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize


HERE = Path(__file__).resolve().parent


def main() -> None:
    with (HERE / "processed_mythaw_2026.csv").open(encoding="utf-8", newline="") as stream:
        observations = list(csv.DictReader(stream))
    groups = defaultdict(list)
    for row in observations:
        groups[row["upstream_year"], row["upstream_site"], row["date"]].append(row)
    plotted = []
    for (year, site, day), rows in sorted(groups.items()):
        depths = [float(row["thaw_depth"]) for row in rows if row["thaw_depth"]]
        bounded = sum(row["pf_observed"] == "0" for row in rows)
        plotted.append(dict(year=year, site=site, date=day, lon=rows[0]["lon"], lat=rows[0]["lat"],
                            n_measured=len(depths), n_bounded=bounded,
                            median_measured_thaw_cm=median(depths) if depths else "",
                            non_detection_limit_cm=150 if bounded else ""))
    with (HERE / "review_plot_data.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(plotted[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(plotted)

    sites = sorted({row["site"] for row in plotted})
    positions = {site: index for index, site in enumerate(sites)}
    fig = plt.figure(figsize=(13.5, 11), layout="constrained")
    grid = fig.add_gridspec(3, 2, height_ratios=[0.85, 1, 1])
    fig.suptitle("myThaw seasonal probe observations · 2021–2024", fontsize=18)
    map_ax = fig.add_subplot(grid[0, :])
    unique = {(row["site"], row["lon"], row["lat"]) for row in plotted}
    offsets = {"Bayelva": (3, -12), "CNR@Bayelva": (3, 12),
               "Kevo Vaisejaeggi": (3, -12), "Iskoras": (3, 10),
               "Zackenberg CALM wet transect": (3, -12),
               "Zackenberg CALM dry transect": (3, 10),
               "NRC Lake Transect": (3, -12), "Siksik Creek (TVC)": (3, 10)}
    labelled = set()
    for site, lon, lat in sorted(unique):
        map_ax.scatter(float(lon), float(lat), s=28, color="#176c8b")
        if site not in labelled:
            map_ax.annotate(site, (float(lon), float(lat)), xytext=offsets.get(site, (3, 3)),
                            textcoords="offset points", fontsize=7.5)
            labelled.add(site)
    map_ax.set(xlim=(-165, 155), ylim=(65, 82), xlabel="Longitude (° E)", ylabel="Latitude (° N)")
    map_ax.set_title("Published site or transect coordinates shared by individual probe stations",
                     loc="left", fontsize=10)
    map_ax.grid(alpha=0.22)

    axes = []
    colors = Normalize(vmin=0, vmax=150)
    for year in range(2021, 2025):
        ax = fig.add_subplot(grid[1 + (year - 2021) // 2, (year - 2021) % 2])
        axes.append(ax)
        records = [row for row in plotted if row["year"] == str(year)]
        measured = [row for row in records if row["n_measured"]]
        dots = ax.scatter([date.fromisoformat(row["date"]) for row in measured],
                          [positions[row["site"]] for row in measured],
                          c=[row["median_measured_thaw_cm"] for row in measured],
                          s=23, cmap="viridis", norm=colors, edgecolors="none")
        limits = [row for row in records if row["n_bounded"]]
        ax.scatter([date.fromisoformat(row["date"]) for row in limits],
                   [positions[row["site"]] for row in limits], facecolors="none",
                   edgecolors="#b14424", marker="s", s=55, linewidths=1.2)
        ax.set_yticks(range(len(sites)), sites, fontsize=7.5)
        ax.set(xlim=(date(year, 1, 1), date(year, 12, 31)), ylim=(-1, len(sites)))
        ax.set_title(str(year), loc="left", fontsize=12)
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        ax.grid(alpha=0.15)
        ax.set_axisbelow(True)
    fig.colorbar(dots, ax=axes, label="Median measured seasonal thaw per site/date (cm)", shrink=0.78)
    fig.supxlabel("Each dot summarizes only the retained measured depths at one site/date.\n"
                  "Open red squares mark visits containing non-detections to 150 cm.",
                  fontsize=10)
    fig.savefig(HERE / "mythaw_review.png", dpi=170, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
