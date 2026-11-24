"""
metadata_schema_version = 1
source_key = "MyThaw_2026"
release_clearance = "needs_review"
permission_basis = "public_repository_terms"
original_author = "Codex"
last_substantive_update = "2026-11-24"
source_dataset = '''
Boike et al. (2024), Circumarctic seasonal measurements of permafrost parameters.
PANGAEA collection https://doi.org/10.1594/PANGAEA.971787.
Annual releases by Martin et al. (2023), Boike et al. (2024),
Hammar et al. (2025, 2026): 10.1594/PANGAEA.956039 (2021),
10.1594/PANGAEA.971586 (2022), 10.1594/PANGAEA.974461 (2023),
10.1594/PANGAEA.997035 (2024). All four child records are CC BY 4.0.
'''
processing_assumptions = [
  "Keep dated seasonal steel-rod thaw depths in centimetres. Set contextual permafrost presence with PA, leave pf_depth blank, and preserve the supplied error and comments. The metadata identifies these as permafrost monitoring sites, but seasonal frozen ground reached during a visit need not be the top of permafrost.",
  "The 21 Bayelva entries at 150 cm explicitly described as rod-limited in 2021 and 2022 become bounded non-detections with obs_limit=150 cm and LB. Blank and zero thaw entries remain unresolved in the audit.",
  "Exclude source-identified stone stops, questionable over-hammered values, measurements explicitly inconsistent with unfrozen ground beneath a surface crust, and four uncertain 2023 Bayelva near-limit values. The 182 cm 2024 Bayelva reading exceeds the metadata's stated 1-1.5 m rod length and its note describes a difficult single measurement without documenting a longer rod. Hold that reading for clarification. Other points on the same visits are retained.",
  "Remove 29 copied 2024 thaw entries under protocol IDs 3253009, 3253004, and 4846957 after comparing complete site/date/point depth/error vectors to 3231467, 3253000, and 4846950. Only protocol IDs and measurement-day image names differ in the copied raw rows.",
]
temporal_handling = [
  "Retain exact source dates and repeated visits. Correct Bayelva points 0-3 in the 2023-07-31 protocol to 2023-07-28 using its explicit note. Three of these are held for uncertain depth, leaving one retained date correction. Keep the original date in provenance.",
]
spatial_handling = [
  "Use published transect coordinates for 2021, 2023 and 2024, repeated at all transect points and flagged CS. For 2022 use the precise site-description coordinates because the transect fields are rounded to whole degrees; preserve both raw coordinate fields.",
]
manual_steps = []
known_limitations = [
  "Coordinates locate transects rather than individual stations. Site/transect/point IDs identify within-transect observations without fabricating station GPS positions.",
  "CALM annual summaries share monitoring programmes at Toolik, Zackenberg and Samoylov. Retain the dated individual visits and flag DO for these sites. CUSP CALM dates are assigned annual dates and cannot establish identical field visits. Native-source annual summaries and seasonal point measurements have dependent support.",
  "ALLena Samoylov observations were compared by year, date, coordinates and provenance. Same-day observations within 1 km are recorded in overlap_review.csv; this is a candidate screen rather than a proximity deduplication rule. No established republished ALLena observations are removed.",
  "Source notes sometimes apply to specific points within a whole protocol. Unmeasured points described as completely thawed lack a numeric observation limit and remain unresolved.",
]
external_dependencies = ["Python standard library; pinned raw source archive; existing CALM and Veremeeva_etal_2025 processed files for overlap review."]
notes = "Issue #44. All four public annual files retrieved 2026-11-24. The 2024 child record was published on 2026-11-09 and is now publicly downloadable. Individual annual and provider citations remain in the raw metadata and per-row accession."
"""

from collections import Counter
import csv
from datetime import date
import hashlib
import io
import math
from pathlib import Path
import re
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = "MyThaw_2026"
FILES = {
    2021: ("956039", "b7b9da5712e34ff2a4f224e15fa567fac796cc92dbdf1f4e2937819ad500fafb", 1824),
    2022: ("971586", "75fbaeffac5c36ad8065d6a4a2068843391e9e8fafb115e2e55274ea7d51aeec", 3655),
    2023: ("974461", "266508d4c37ae33f5ff4079debf68b6a3ba2a542bb722b73cf0c5440a711428f", 2867),
    2024: ("997035", "ee026063d0a937fb0c0a22d38ef069159a79bbe1024f7473276227ea3cd3c94a", 3077),
}
COPIED_PROTOCOLS = {"3253009": "3231467", "3253004": "3253000", "4846957": "4846950"}
POINT = "ID (ID of transect point)"
DEPTH = "Thaw depth [cm]"
ERROR = "Thaw depth e [cm]"
COMMENT = "Comment (on thaw depth measurements)"
CALM_SHARED = {"Toolik Field Station", "Samoylov", "Zackenberg CALM wet transect",
               "Zackenberg CALM dry transect"}


def decision(row: dict, year: int) -> str:
    raw = row[DEPTH]
    if not raw:
        return "excluded_no_thaw_measurement"
    depth = float(raw)
    if not math.isfinite(depth) or depth < 0:
        raise ValueError("Unexpected non-finite or negative thaw depth.")
    if depth == 0:
        return "excluded_unresolved_zero"
    point = int(float(row[POINT])) if row[POINT] else None
    note = row[COMMENT].lower()
    if row["Protocol ID"] in COPIED_PROTOCOLS:
        return "excluded_copied_protocol"
    if "recommended to discard" in note:
        return "excluded_source_stone_stop"
    if row["Site"] == "Bayelva":
        if year == 2022 and "maxed out" in note:
            return "retained_lower_bound" if depth == 150 else "excluded_source_stone_stop"
        if year == 2022 and "indicates the depth is more than" in note:
            if point == 4:
                return "excluded_source_stone_stop"
            if depth == 150:
                return "retained_lower_bound"
        if year == 2021 and "could not measure more than 150" in note and depth == 150:
            return "retained_lower_bound"
        if year == 2023 and "cannot be captured" in note and point in {0, 1, 3, 7}:
            return "excluded_uncertain_probe_limit"
        if year == 2024 and "hammered too much" in note and point in {0, 1, 2}:
            return "excluded_questionable_probe"
        if year == 2024 and depth > 150 and "very difficult to measure" in note:
            return "excluded_protocol_length_conflict"
    if "point 0 - rock" in note or note == "0. rock":
        if point == 0:
            return "excluded_source_stone_stop"
    if "point 5 probably inhibited by rock" in note and point == 5:
        return "excluded_source_stone_stop"
    if "not frozen underneath" in note or "not underneath" in note:
        return "excluded_surface_refreezing"
    if "points 28 & 29 underground surface of pond ice" in note and point in {28, 29}:
        return "excluded_pond_ice_reference"
    return "retained_seasonal_thaw"


def rows_from_archive() -> list[dict]:
    result = []
    with ZipFile(HERE / "pangaea_annual_exports.zip") as archive:
        for year, (accession, checksum, count) in FILES.items():
            content = archive.read(f"PANGAEA.{accession}.tab")
            if hashlib.sha256(content).hexdigest() != checksum:
                raise ValueError(f"Changed upstream snapshot for {year}.")
            metadata, table = content.decode("utf-8-sig").split("*/", 1)
            if "CC-BY-4.0" not in metadata:
                raise ValueError(f"Missing expected child license for {year}.")
            rows = list(csv.DictReader(io.StringIO(table.lstrip("\r\n")), delimiter="\t"))
            if len(rows) != count:
                raise ValueError(f"Changed raw row count for {year}.")
            for number, row in enumerate(rows, 1):
                row["_year"], row["_accession"], row["_row"] = year, accession, number
            result.extend(rows)
    return result


def verify_protocol_copies(rows: list[dict]) -> None:
    for copied, original in COPIED_PROTOCOLS.items():
        first = [r for r in rows if r["Protocol ID"] == original]
        second = [r for r in rows if r["Protocol ID"] == copied]
        ignored = {"Protocol ID", "IMAGE earth surf (transect on measurement day)", "_row"}
        projected = lambda group: [{k: v for k, v in r.items() if k not in ignored} for r in group]
        if not first or projected(first) != projected(second):
            raise ValueError(f"Repeated protocol {copied} differs from {original}; review required.")


def transformed(row: dict) -> dict:
    year = row["_year"]
    original_date = row["Date/Time"][:10]
    date.fromisoformat(original_date)
    point = int(float(row[POINT])) if row[POINT] else None
    site = row["Site"]
    transect = row.get("Transect", row.get("Transect no", "")) or "1"
    transect = str(int(float(transect)))
    suffix = f"P{point:03d}" if point is not None else "no_point"
    site_id = f"{re.sub(r'[^A-Za-z0-9]+', '_', site).strip('_')}_T{transect}_{suffix}"
    lat_key = next(k for k in row if k.startswith("Latitude descr (latitude of site"))
    lon_key = next(k for k in row if k.startswith("Longitude descr (longitude of site"))
    lon = row[lon_key] if year == 2022 else row["Longitude (of transect)"]
    lat = row[lat_key] if year == 2022 else row["Latitude (of transect)"]
    if not (-180 <= float(lon) <= 180 and -90 <= float(lat) <= 90):
        raise ValueError("Invalid site coordinate.")
    measurement_date = original_date
    if year == 2023 and site == "Bayelva" and "28.7.2023" in row[COMMENT] and point is not None and point <= 3:
        measurement_date = "2023-07-28"
    result = dict(
        site_id=site_id, source=SOURCE, lon=lon, lat=lat, date=measurement_date,
        upstream_year=year, upstream_accession=f"10.1594/PANGAEA.{row['_accession']}",
        upstream_row=row["_row"], upstream_protocol=row["Protocol ID"], upstream_site=site,
        upstream_transect=transect, upstream_point=row[POINT], upstream_date=row["Date/Time"],
        upstream_thaw_depth_cm=row[DEPTH], upstream_thaw_error_cm=row[ERROR],
        upstream_thaw_comment=row[COMMENT], upstream_site_lat=row[lat_key],
        upstream_site_lon=row[lon_key], upstream_transect_lat=row["Latitude (of transect)"],
        upstream_transect_lon=row["Longitude (of transect)"], decision=decision(row, year),
    )
    return result


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def overlap_review(processed: list[dict]) -> list[dict]:
    with (ROOT / "data/Veremeeva_etal_2025/processed_veremeeva_etal_2025.csv").open(
            encoding="utf-8", newline="") as stream:
        allena = list(csv.DictReader(stream))
    checks = []
    for year in (2021, 2022):
        current = [r for r in processed if r["upstream_site"] == "Samoylov" and r["upstream_year"] == year]
        dates = {r["date"] for r in current}
        lat, lon = float(current[0]["lat"]), float(current[0]["lon"])
        candidates = [r for r in allena if r["date"][:4] == str(year) and
                      111195 * math.hypot(float(r["lat"]) - lat,
                                         (float(r["lon"]) - lon) * math.cos(math.radians(lat))) <= 1000]
        matches = sum(r["date"] in dates for r in candidates)
        if matches:
            raise ValueError("New same-day ALLena overlap requires provenance review.")
        checks.append(dict(compared_source="Veremeeva_etal_2025", site="Samoylov", year=year,
                           candidate_count=len(candidates), same_day_candidates=matches,
                           rows_removed=0, interpretation="Different field dates within shared study area"))
    return checks


def main() -> None:
    raw = rows_from_archive()
    verify_protocol_copies(raw)
    audit = [transformed(row) for row in raw]
    processed = []
    for row in audit:
        if not row["decision"].startswith("retained"):
            continue
        bound = row["decision"] == "retained_lower_bound"
        result = dict(row)
        result.pop("decision")
        result.update(method="tp", pf_observed=0 if bound else 1, pf_depth=None,
                      thaw_depth=None if bound else float(row["upstream_thaw_depth_cm"]),
                      obs_limit=150 if bound else None,
                      quality_flag_coord_site_level=True, quality_flag_pf_state_assumed=not bound,
                      quality_flag_lower_bound_absence=bound,
                      quality_flag_possible_duplicate_or_overlap=row["upstream_site"] in CALM_SHARED,
                      quality_flag_refusal_or_obstruction_note=any(
                          word in row["upstream_thaw_comment"].lower() for word in ("rock", "tussock")),
                      quality_flag_summary_statistic="three measurements per point" in
                          row["upstream_thaw_comment"].lower())
        processed.append(result)
    counts = Counter(row["decision"] for row in audit)
    if (counts["retained_lower_bound"] != 21 or counts["excluded_copied_protocol"] != 29 or
            counts["excluded_unresolved_zero"] != 492 or len(processed) != 4399):
        raise ValueError(f"Changed semantic accounting: {counts}")
    keys = [(r["site_id"], r["date"]) for r in processed]
    if len(keys) != len(set(keys)):
        raise ValueError("Repeated site/date key remains after source-level copy removal.")
    write_csv(HERE / "processing_audit.csv", audit)
    write_csv(HERE / "processed_mythaw_2026.csv", processed)
    write_csv(HERE / "overlap_review.csv", overlap_review(processed))
    print(f"{SOURCE}: {len(processed)} retained observations from {len(raw)} rows.")
    print(dict(counts))


if __name__ == "__main__":
    main()
