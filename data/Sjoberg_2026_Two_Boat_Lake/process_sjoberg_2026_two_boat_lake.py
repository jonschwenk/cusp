"""
metadata_schema_version = 1
source_key = "Sjoberg_2026_Two_Boat_Lake"
release_clearance = "needs_review"
permission_basis = "public_repository_terms"
original_author = "Codex"
last_substantive_update = "2026-11-16"
source_dataset = '''
Sjöberg, Ylva; Rydberg, Johan; Lindborg, Emma (2026): Thaw depth measurements
along transects A and B near Kangerlussuaq, West Greenland (May 2017).
PANGAEA. A: https://doi.org/10.1594/PANGAEA.989941
B: https://doi.org/10.1594/PANGAEA.989942
'''
processing_assumptions = [
  "Retain all 1225 positive manual steel-rod thaw depths in centimetres. These are the depths of seasonal thaw during snowmelt. Leave pf_depth and obs_limit blank.",
  "Assign pf_observed = 1 based on the documented continuous permafrost under the terrestrial catchment (Rydberg et al. 2026, section 2.1). Flag every retained row pf_state_assumed because the spring probe reached the seasonal thaw front rather than confirming the top of permafrost.",
  "Keep all 189 blank thaw measurements unresolved in the audit. The PANGAEA records note that an unsuccessful measurement was most often due to rock, without a row-specific reason or numeric limit. Water-table values, including zero and the 25 water-only rows, stay in the audit as upstream provenance.",
]
temporal_handling = [
  "Use the seven exact table dates from 2017-05-19 through 2017-05-31. The companion paper describes an intensive monitoring period beginning May 18. Use the individual field dates from the data deposit and retain all repeat visits.",
]
spatial_handling = [
  "Use a WGS84 geodesic between each pair of PANGAEA event endpoints. Place stations at their nominal offset divided by 50 m along that geodesic and flag coord_lookup_or_interpolated. The companion workbook confirms the four endpoints. The geodesic spans are 51.73 m for A and 48.90 m for B. No station-level GPS or surveyed path geometry is supplied.",
]
manual_steps = []
known_limitations = [
  "Each site ID pairs the transect label with the zero-based half-metre station index. Coordinates convey approximate position along the endpoint chord. Preserve the reported offset for spacing or along-transect analysis.",
  "Petrone_etal_2016 overlaps spatially in the same catchment. Its 76 retained steel-rod and 590 GPR observations date to August 2011, whereas the added steel-rod surveys date to May 2017. Retain both campaigns and all seven spring dates. No cross-source deletions, spatial thinning or aggregation are applied by this processor.",
]
external_dependencies = ["pyproj (WGS84 geodesic); pinned PANGAEA text exports in pangaea_transects.zip."]
notes = "Both child datasets are CC BY 4.0. Retrieved 2026-11-16. CUSP issue #47. Related methods: https://doi.org/10.5194/tc-20-47-2026."
"""

from collections import Counter
import csv
import hashlib
import io
import math
from pathlib import Path
import re
from zipfile import ZipFile

from pyproj import Geod


HERE = Path(__file__).resolve().parent
SOURCE = "Sjoberg_2026_Two_Boat_Lake"
FILES = {
    "A": ("989941", "5479c02ac33f986cedde6b290bf234c9ef9486350d01a90d7c5356897a6e61f4"),
    "B": ("989942", "8153f391c905eb89a8a3d2eb9cae1f90e2ebdf64834f9ac16f21fe6cc2f55243"),
}
DATES = [f"2017-05-{day}" for day in range(19, 32, 2)]
EXPECTED = {"A": (85, 193, 8), "B": (90, 182, 17)}
HEADER = ["Dist [m]", "Date/Time", "Thaw depth [cm]", "WTD [cm]"]
AUDIT_FIELDS = ("site_id", "date", "lon", "lat", "upstream_transect", "upstream_offset_m",
                "upstream_doi", "upstream_thaw_depth_cm", "upstream_water_table_cm", "decision")
PROCESSED_FIELDS = (
    "site_id", "date", "lon", "lat", "source", "method", "pf_observed", "thaw_depth",
    "pf_depth", "obs_limit", "quality_flag_coord_lookup_or_interpolated",
    "quality_flag_pf_state_assumed", *AUDIT_FIELDS[4:8],
)


def event_positions(metadata: str, transect: str) -> list[tuple[str, str]]:
    event = re.search(rf"^Event\(s\):\s+Kangerl_WGreenl_Transect{transect} "
                      r"\* LATITUDE START: ([\d.]+) \* LONGITUDE START: (-[\d.]+) "
                      r"\* LATITUDE END: ([\d.]+) \* LONGITUDE END: (-[\d.]+)",
                      metadata, re.MULTILINE)
    if not event:
        raise ValueError(f"Missing PANGAEA endpoints for transect {transect}.")
    lat0, lon0, lat1, lon1 = map(float, event.groups())
    geod = Geod(ellps="WGS84")
    azimuth, _, span = geod.inv(lon0, lat0, lon1, lat1)
    # Distances in the input are nominal station offsets on a 50 m field transect.
    coords = [(lon0, lat0)]
    coords.extend(geod.fwd(lon0, lat0, azimuth, span * i / 100)[:2] for i in range(1, 100))
    coords.append((lon1, lat1))
    return [(f"{lon:.8f}", f"{lat:.8f}") for lon, lat in coords]


def read_transect(raw: bytes, transect: str) -> list[dict]:
    accession, checksum = FILES[transect]
    if hashlib.sha256(raw).hexdigest() != checksum:
        raise ValueError(f"The PANGAEA.{accession} snapshot changed.")
    metadata, table = raw.decode("utf-8-sig").split("*/", 1)
    locations = event_positions(metadata, transect)
    stream = csv.reader(io.StringIO(table.lstrip("\r\n")), delimiter="\t")
    if next(stream) != HEADER:
        raise ValueError(f"Unexpected PANGAEA.{accession} column names.")

    audit = []
    for offset, date, depth, water in stream:
        half_metres = 2 * float(offset)
        if not (0 <= half_metres <= 100 and half_metres.is_integer()):
            raise ValueError(f"Invalid offset in PANGAEA.{accession}: {offset}")
        if depth and not (math.isfinite(float(depth)) and float(depth) > 0):
            raise ValueError(f"Invalid thaw depth in PANGAEA.{accession}: {depth}")
        station = int(half_metres)
        lon, lat = locations[station]
        audit.append(dict(
            site_id=f"{transect}_{station:03d}", date=date, lon=lon, lat=lat,
            upstream_transect=transect, upstream_offset_m=offset,
            upstream_doi=f"10.1594/PANGAEA.{accession}", upstream_thaw_depth_cm=depth,
            upstream_water_table_cm=water,
            decision="retained_spring_thaw_depth" if depth else "excluded_unresolved_thaw_depth",
        ))

    expected_visits = {(date, f"{transect}_{station:03d}") for date in DATES for station in range(101)}
    visits = {(row["date"], row["site_id"]) for row in audit}
    reported = [row for row in audit if row["upstream_thaw_depth_cm"]]
    measured = Counter(row["date"] for row in reported)
    measured_stations = {row["site_id"] for row in reported}
    water = sum(bool(row["upstream_water_table_cm"]) for row in audit)
    water_only = water - sum(bool(row["upstream_water_table_cm"]) for row in reported)
    n, expected_water, expected_water_only = EXPECTED[transect]
    if (len(audit) != len(expected_visits) or visits != expected_visits or
            measured != dict.fromkeys(DATES, n) or len(measured_stations) != n or
            (water, water_only) != (expected_water, expected_water_only)):
        raise ValueError(f"Unexpected campaign accounting for transect {transect}.")
    return audit


def write_rows(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    audit = []
    with ZipFile(HERE / "pangaea_transects.zip") as archive:
        for transect, (accession, _) in FILES.items():
            audit.extend(read_transect(archive.read(f"PANGAEA.{accession}.tab"), transect))
    measured = [
        dict(row, source=SOURCE, method="tp", pf_observed=1, thaw_depth=row["upstream_thaw_depth_cm"],
             pf_depth=None, obs_limit=None, quality_flag_coord_lookup_or_interpolated=True,
             quality_flag_pf_state_assumed=True)
        for row in audit if row["upstream_thaw_depth_cm"]
    ]
    write_rows(HERE / "processing_audit.csv", AUDIT_FIELDS, audit)
    write_rows(HERE / "processed_sjoberg_2026_two_boat_lake.csv", PROCESSED_FIELDS, measured)
    print(f"{SOURCE}: {len(measured)} thaw depths, {len(audit) - len(measured)} unresolved blanks.")


if __name__ == "__main__":
    main()
