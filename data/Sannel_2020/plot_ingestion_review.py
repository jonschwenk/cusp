"""Plot each dated Tavvavuoma measurement and explicit probe bound."""

import csv
from math import cos, radians
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

HERE = Path(__file__).resolve().parent


def main() -> None:
    with (HERE / "processing_audit.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    dates = sorted({row["date"] for row in rows})
    lat0, lon0 = 68.462, 20.902
    scale = Normalize(40, 120)
    fig, axes = plt.subplots(1, len(dates), figsize=(13, 4.5), sharex=True, sharey=True)
    fig.subplots_adjust(left=0.055, right=0.90, bottom=0.23, top=0.79, wspace=0.1)
    fig.suptitle("Tavvavuoma thaw depths and probe bounds", y=0.97, fontsize=17)
    fig.text(0.055, 0.86, "Site reference 68.462° N, 20.902° E · Coordinates at thermistor stations", fontsize=10)
    for date, ax in zip(dates, axes, strict=True):
        for row in [r for r in rows if r["date"] == date]:
            x = (float(row["lon"]) - lon0) * cos(radians(lat0)) * 111195
            y = (float(row["lat"]) - lat0) * 111195
            if row["decision"] == "excluded_in_water":
                ax.scatter(x, y, marker="x", color="#a3a8ae", s=25)
            elif row["decision"] == "retained_bound":
                ax.scatter(x, y, marker="s", facecolors="none", edgecolors="#a24626", s=55)
            else:
                dots = ax.scatter(x, y, c=[float(row["thaw_depth"])], cmap="viridis", norm=scale,
                                  s=55, edgecolors="black", linewidths=0.3)
            offset = (-14, -10) if row["site_id"] == "T6" else (3, 4)
            ax.annotate(row["site_id"], (x, y), xytext=offset, textcoords="offset points", fontsize=7)
        ax.set(title=date, xlabel="East (m)", xlim=(-30, 33), ylim=(-10, 50), aspect="equal")
        ax.grid(alpha=0.2)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("North (m)")
    cax = fig.add_axes([0.92, 0.25, 0.013, 0.53])
    fig.colorbar(dots, cax=cax, label="Measured thaw / frost-table depth (cm)")
    fig.text(0.055, 0.07, "Open squares  permafrost not reached within 100 cm     ×  unsampled in water", fontsize=10)
    fig.savefig(HERE / "sannel_review.png", dpi=170, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
