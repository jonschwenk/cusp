"""
metadata_schema_version = 1
source_key = "Sannel_2020"
release_clearance = "needs_review"
permission_basis = "public_repository_terms"
original_author = "Codex"
last_substantive_update = "2026-11-24"
source_dataset = '''
Sannel, Britta (2020): Ground temperature, thaw depth and snow depth in a
permafrost peatland in Tavvavuoma, northern Sweden. Version 1. Bolin Centre
Database. https://doi.org/10.17043/sannel-2020-temperature-1
'''
processing_assumptions = [
  "Retain nine source-reported station/date mean thaw depths with summary_statistic and their three original readings as provenance. Retain 13 explicit >100 cm outcomes as bounded non-detections with obs_limit = 100, pf_observed = 0, lower_bound_absence and blank canonical depths.",
  "The 100 cm non-detection means permafrost was not reached within the probe depth. It does not imply that deeper permafrost is absent. Exclude five cells stating No data (in water), preserving them in the audit.",
  "Retain the two exact-date installation thaw depths explicitly recorded in workbook footnotes: T1 on 2005-09-23 (75 cm) and T4 on 2006-09-04 (115 cm). No replicate count or observation limit is assigned to these readings.",
]
temporal_handling = [
  "Preserve 2010-09-02, 2011-09-03 and 2012-08-23 from workbook serial dates. The T4 footnote specifies September 2006; the paper discussion refers to installation in 2005. Follow the pinned workbook and flag date_source_approximate for this conflicting installation date pending review.",
]
spatial_handling = [
  "Convert station degrees and decimal minutes in the Read me worksheet to WGS84 decimal degrees. The workbook does not explicitly state a datum. Treat supplied geographic coordinates as WGS84 with coord_source_flagged; flag coord_site_level because probes were within 25 cm of the cable.",
]
manual_steps = [
  "Extract sannel-2020-tavvavuoma-snow-and-thaw-depth.xlsx unchanged from https://bolin.su.se/data/uploads/sannel-2020.zip; the processor pins its SHA-256.",
]
known_limitations = [
  "These are late-season thaw depths, measured before the regional maximum thaw season, and preserve source-reported means without recalculation from rounded replicates.",
  "Processed-source screening found no existing observations within 4 km of the station complex; no cross-source rows are removed. All repeated dates are retained.",
]
external_dependencies = ["Python standard library; pinned XLSX workbook."]
notes = "CC BY 4.0 per Bolin Centre record, checked 2026-11-24. Related methods https://doi.org/10.1002/ppp.2045. CUSP issue #45."
"""

from collections import Counter
import csv
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
SOURCE = "Sannel_2020"
SHA256 = "e1c08de02374092892b968dece6fcf90f7eb939691d3f85ae40a2da8639a7734"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def worksheet(archive: ZipFile, number: int, strings: list[str]) -> dict[str, str]:
    root = ET.fromstring(archive.read(f"xl/worksheets/sheet{number}.xml"))
    result = {}
    for cell in root.findall(f".//{NS}c"):
        value = cell.find(f"{NS}v")
        if value is not None:
            result[cell.attrib["r"]] = strings[int(value.text)] if cell.get("t") == "s" else value.text
    return result


def coordinate(text: str) -> float:
    degrees, minutes = map(float, re.findall(r"\d+(?:\.\d+)?", text))
    return round(degrees + minutes / 60, 9)


def main() -> None:
    path = HERE / "tavvavuoma_snow_and_thaw.xlsx"
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
        raise ValueError("The Tavvavuoma workbook changed.")
    with ZipFile(path) as archive:
        strings = ["".join(element.itertext()) for element in
                   ET.fromstring(archive.read("xl/sharedStrings.xml"))]
        sites = worksheet(archive, 1, strings)
        thaw = worksheet(archive, 3, strings)
    audit = []
    for row in range(2, 5):
        date = (datetime(1899, 12, 30) + timedelta(days=int(thaw[f"B{row}"]))).date().isoformat()
        for station in range(1, 10):
            raw = thaw[f"{chr(66 + station)}{row}"].strip()
            audit.append(make_record(station, date, raw, sites, installation=False))
    for cell, station in [("A6", 1), ("A7", 4)]:
        date, depth = re.search(r"(\d{4}-\d{2}-\d{2}): (\d+) cm", thaw[cell]).groups()
        audit.append(make_record(station, date, depth, sites, installation=True))
    counts = Counter(row["decision"] for row in audit)
    if counts != {"retained_mean": 9, "retained_bound": 13, "excluded_in_water": 5,
                  "retained_installation": 2}:
        raise ValueError(f"Unexpected source accounting: {counts}")
    retained = [row for row in audit if row["decision"] != "excluded_in_water"]
    if len({(row["site_id"], row["date"]) for row in retained}) != 24:
        raise ValueError("Station/date observations must be unique.")
    fields = list(audit[0])
    for name, rows in [("processing_audit.csv", audit), ("processed_sannel_2020.csv", retained)]:
        with (HERE / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    print(f"{SOURCE}: {len(retained)} records; {dict(counts)}")


def make_record(station: int, date: str, raw: str, sites: dict, installation: bool) -> dict:
    bounded = raw.startswith(">100")
    missing = raw == "No data (in water)"
    if installation:
        value, decision = float(raw), "retained_installation"
    elif missing:
        value, decision = None, "excluded_in_water"
    elif bounded:
        if raw != ">100 (>100, >100, >100)":
            raise ValueError(f"Unexpected bound {raw}")
        value, decision = None, "retained_bound"
    else:
        match = re.fullmatch(r"(\d+) \((\d+), (\d+), (\d+)\)", raw)
        if not match:
            raise ValueError(f"Unrecognized thaw cell {raw}")
        value, decision = float(match[1]), "retained_mean"
    return dict(
        source=SOURCE, site_id=f"T{station}", date=date,
        lon=coordinate(sites[f"C{station + 7}"]), lat=coordinate(sites[f"B{station + 7}"]),
        method="tp", pf_observed=None if missing else int(not bounded),
        thaw_depth=value, pf_depth=value, obs_limit=100 if bounded else None,
        quality_flag_lower_bound_absence=bounded,
        quality_flag_summary_statistic=decision == "retained_mean",
        quality_flag_coord_site_level=True, quality_flag_coord_source_flagged=True,
        quality_flag_date_source_approximate=installation and station == 4,
        upstream_measurement=raw, upstream_landscape_unit=sites[f"D{station + 7}"],
        decision=decision,
    )


if __name__ == "__main__":
    main()
