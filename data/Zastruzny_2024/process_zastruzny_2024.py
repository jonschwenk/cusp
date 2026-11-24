"""
metadata_schema_version = 1
source_key = "Zastruzny_2024"
release_clearance = "needs_review"
permission_basis = "public_repository_terms"
original_author = "Codex"
last_substantive_update = "2026-11-16"
source_dataset = '''
Zastruzny, Sebastian; Elberling, Bo; Jensen, Karsten Høgh; Sjöberg, Ylva;
Liu, Yijing (2024): Field data from Disko Island for thermal-hydrological
investigations [dataset]. PANGAEA. https://doi.org/10.1594/PANGAEA.967139
'''
processing_assumptions = [
  "Use only the Disko2015_frost_table event. Retain 68 direct steel-rod readings below 120 cm as detections; the probed frost table is the base of the thawed layer and top of permafrost at this field site. Copy the reported centimetre value to thaw_depth and pf_depth.",
  "Keep all eight exact-120-cm entries in the audit with their original date and coordinates. They recur at the same four positions on both dates and may encode the probe limit. The source does not identify a row-specific refusal or limit, so neither an exact depth nor a bounded non-detection is assigned to these rows.",
  "The remaining 450462 table rows have different or blank event labels and are outside the selected frost-table event. The upstream audit found no frost-depth values in those rows.",
]
temporal_handling = [
  "Use the calendar date of each upstream timestamp, 2015-08-04 or 2015-08-21. Preserve the full upstream timestamp as provenance; retain both visits at every retained position.",
]
spatial_handling = [
  "Preserve the published RTK differential-GPS geographic coordinates in decimal degrees. Assign a consistent position ID from the south-to-north order of the 38 unique coordinate pairs, including the four excluded positions.",
]
manual_steps = [
  "The versioned tab-delimited input is the 76-row event subset of the PANGAEA text export, projected to event, longitude, latitude, timestamp and frost-table depth. Use --upstream with the whole downloaded file to verify the pinned byte checksum, event count and exact subset.",
]
known_limitations = [
  "CUSP's CALM_G3 has four annual observations from 1997-2000 at a location about 2.65 km from the 2015 transect. No point/campaign match was found in the processed-source screen within 4 km. No cross-source or proximity-based exclusions were applied.",
  "The paper cites Pedersen et al. (2022) supplementary material for active-layer calibration. CUSP has no matching source from that study. Treat shared campaign material as a provenance lead if that supplement is proposed later.",
  "The earlier campaign report (https://doi.org/10.5194/tc-2017-97) describes thaw deeper than 120 cm at the site, but does not resolve the exact 120 cm rows in this export.",
]
external_dependencies = ["Python standard library and the checked-in event subset."]
notes = "CC BY 4.0 per the PANGAEA dataset record, retrieved 2026-11-16. CUSP tracking issue #46. Related paper: https://doi.org/10.1029/2023WR036147."
"""

import argparse
import csv
from datetime import datetime
import hashlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = "Zastruzny_2024"
EVENT = "Disko2015_frost_table"
EVENT_SHA256 = "797dab715ffeda547d935659a55fcc787184929df95a52616f86aba0a0f73865"
UPSTREAM_SHA256 = "06382fa79de004dc4de5fe667ddd18b7b1cef4868862dbbdb6f11d614d77191e"
HEADER = (
    "Event",
    "Longitude (Real-time kinematic Different...)",
    "Latitude (Real-time kinematic Different...)",
    "Date/Time",
    "Thaw depth [cm] (Distance to Frost Table, Manu...)",
)
DATES = {"2015-08-04", "2015-08-21"}
CANONICAL_FIELDS = ("site_id", "date", "lon", "lat", "source", "method", "pf_observed",
                    "thaw_depth", "pf_depth", "obs_limit")
AUDIT_FIELDS = ("site_id", "date", "lon", "lat", "upstream_event", "upstream_timestamp",
                "upstream_frost_depth_cm", "decision")


def verify_upstream(path: Path, snapshot: list[tuple[str, ...]]) -> None:
    if hashlib.sha256(path.read_bytes()).hexdigest() != UPSTREAM_SHA256:
        raise ValueError("The PANGAEA export differs from the pinned snapshot.")

    with path.open(encoding="utf-8-sig", newline="") as stream:
        for line in stream:
            if line.strip() == "*/":
                break
        reader = csv.reader(stream, delimiter="\t")
        header = next(reader)
        indices = [header.index(field) for field in HEADER]
        projected = [tuple(row[i] for i in indices) for row in reader
                     if row[0] == EVENT or row[indices[-1]]]
    if projected != snapshot:
        raise ValueError("PANGAEA frost-depth rows differ from the checked-in event subset.")


def write_rows(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process Disko Island's 2015 frost-table probes.")
    parser.add_argument("--upstream", type=Path, help="Verify against the pinned full PANGAEA export.")
    args = parser.parse_args()

    path = HERE / f"{EVENT}.tab"
    # Normalize checkout line endings for the portable subset checksum.
    snapshot = path.read_text(encoding="utf-8")
    if hashlib.sha256(snapshot.encode("utf-8")).hexdigest() != EVENT_SHA256:
        raise ValueError("The Disko event subset differs from the pinned snapshot.")
    header, *rows = [tuple(row) for row in csv.reader(snapshot.splitlines(), delimiter="\t")]
    if header != HEADER:
        raise ValueError("Unexpected Disko frost-table header.")
    if args.upstream:
        verify_upstream(args.upstream, rows)

    positions = sorted({(lat, lon) for _, lon, lat, _, _ in rows},
                       key=lambda pair: tuple(map(float, pair)))
    position_ids = {position: f"{EVENT}_{i:02d}" for i, position in enumerate(positions, 1)}
    audit = []
    processed = []
    for event, lon, lat, timestamp, raw_depth in rows:
        date = datetime.fromisoformat(timestamp).date().isoformat()
        depth = int(raw_depth)
        if not (event == EVENT and 0 < depth <= 120 and
                -180 <= float(lon) <= 180 and -90 <= float(lat) <= 90):
            raise ValueError("Unexpected event, depth, or coordinate in the Disko subset.")
        point = {"site_id": position_ids[lat, lon], "date": date, "lon": lon, "lat": lat}
        provenance = dict(upstream_event=event, upstream_timestamp=timestamp,
                          upstream_frost_depth_cm=raw_depth)
        decision = "excluded_ambiguous_120_cm" if depth == 120 else "retained_direct_probe"
        audit.append(dict(point, **provenance, decision=decision))
        if depth < 120:
            processed.append(dict(point, **provenance, source=SOURCE, method="tp", pf_observed=1,
                                  thaw_depth=depth, pf_depth=depth, obs_limit=None))

    visits = {(row["date"], row["site_id"]) for row in audit}
    capped = {(row["date"], row["site_id"]) for row in audit if row["decision"] != "retained_direct_probe"}
    expected = {(date, site) for date in DATES for site in position_ids.values()}
    expected_capped = {(date, f"{EVENT}_{i:02d}") for date in DATES for i in range(35, 39)}
    if (len(positions) != 38 or len(audit) != 76 or visits != expected or
            capped != expected_capped or len(processed) != 68):
        raise ValueError("Disko campaign or exclusion counts changed.")

    write_rows(HERE / "processed_zastruzny_2024.csv", (*CANONICAL_FIELDS, *AUDIT_FIELDS[4:-1]), processed)
    write_rows(HERE / "processing_audit.csv", AUDIT_FIELDS, audit)
    print(f"{SOURCE}: {len(processed)} retained probes, {len(capped)} ambiguous rows audited.")


if __name__ == "__main__":
    main()
