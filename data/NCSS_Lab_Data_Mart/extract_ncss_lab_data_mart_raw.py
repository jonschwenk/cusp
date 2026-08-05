#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create the compact versioned NCSS raw extract from the local GeoPackage.

The full NCSS Lab Data Mart GeoPackage is too large to keep in the repository.
This script reads the ignored local `ncss_labdata.gpkg` file and writes a
pedon-level subset that is small enough to version and sufficient for the CUSP
processor.
"""

from __future__ import annotations

import csv
import re
import sqlite3
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parent
GPKG_PATH = SOURCE_DIR / "ncss_labdata.gpkg"
RAW_OUTPUT = SOURCE_DIR / "raw_ncss_permafrost_domain_pedons.csv"
ABSENCE_LATITUDE_THRESHOLD = 55.0
HORIZON_MASTER_SYMBOLS = frozenset("OAEBCRLMW")


RAW_COLUMNS = [
    "candidate_type",
    "absence_latitude_threshold_abs_ge",
    "pedon_key",
    "site_key",
    "pedlabsampnum",
    "upedonid",
    "usiteid",
    "site_obsdate",
    "lat",
    "lon",
    "country_key",
    "state_key",
    "county_key",
    "mlra_key",
    "ssa_key",
    "corr_classification_name",
    "corr_taxorder",
    "corr_taxsuborder",
    "corr_taxgrtgroup",
    "corr_taxsubgrp",
    "samp_classification_name",
    "samp_taxorder",
    "samp_taxsuborder",
    "samp_taxgrtgroup",
    "samp_taxsubgrp",
    "SSL_classification_name",
    "SSL_taxorder",
    "SSL_taxsuborder",
    "SSL_taxgrtgroup",
    "SSL_taxsubgrp",
    "pf_depth_cm",
    "obs_limit_cm",
    "frozen_horizons",
    "all_horizons",
    "n_frozen_layers",
    "n_layers",
]


def is_frozen_horizon_designation(value: object) -> int:
    """Return 1 when an NCSS horizon has a valid ``f`` or ``ff`` suffix.

    NCSS ``hzn_desgn`` values may contain lithologic prefixes, vertical
    subdivisions, transitional horizons, and slash-separated components.
    The parser intentionally rejects prose and parenthetical texture labels.
    Uppercase ``F`` is accepted in otherwise valid legacy-style symbols, but
    ``hzn_desgn_old`` is not classified because that field also contains
    free-form labels such as ``DUFF`` and ``CLAY FILMS``.
    """

    if value is None:
        return 0

    for raw_component in str(value).strip().split("/"):
        component = (
            raw_component.strip()
            .replace("\N{RIGHT SINGLE QUOTATION MARK}", "'")
            .replace("\N{PRIME}", "'")
        )
        if not component or re.search(r"\s|[()&]", component):
            continue

        component = component.lstrip("^")
        component = re.sub(r"^\d+", "", component)

        # Lowercase w is used for ice-wedge components in some NCSS records.
        if re.fullmatch(r"w[fF]{1,2}\d*", component):
            return 1
        if component.startswith("w"):
            component = component[1:]

        master_end = 0
        while (
            master_end < len(component)
            and component[master_end] in HORIZON_MASTER_SYMBOLS
        ):
            master_end += 1
        if master_end == 0:
            continue

        suffix = component[master_end:].replace("'", "")
        suffix = re.sub(r"\d", "", suffix)
        if (
            suffix
            and re.fullmatch(r"[a-zF]+", suffix)
            and ("f" in suffix or "F" in suffix)
        ):
            return 1

    return 0


def main() -> None:
    if not GPKG_PATH.exists():
        raise FileNotFoundError(
            f"{GPKG_PATH} not found. Download/extract the NCSS Lab Data Mart "
            "GeoPackage locally before regenerating the compact raw extract."
        )

    query = """
    WITH pedons AS (
      SELECT
        c.pedon_key,
        c.site_key,
        c.pedlabsampnum,
        c.upedonid,
        c.usiteid,
        c.site_obsdate,
        c.latitude_decimal_degrees AS lat,
        c.longitude_decimal_degrees AS lon,
        c.country_key,
        c.state_key,
        c.county_key,
        c.mlra_key,
        c.ssa_key,
        c.corr_classification_name,
        c.corr_taxorder,
        c.corr_taxsuborder,
        c.corr_taxgrtgroup,
        c.corr_taxsubgrp,
        c.samp_classification_name,
        c.samp_taxorder,
        c.samp_taxsuborder,
        c.samp_taxgrtgroup,
        c.samp_taxsubgrp,
        c.SSL_classification_name,
        c.SSL_taxorder,
        c.SSL_taxsuborder,
        c.SSL_taxgrtgroup,
        c.SSL_taxsubgrp,
        MIN(CASE
          WHEN l.hzn_top IS NOT NULL
           AND is_frozen_horizon(l.hzn_desgn) = 1
          THEN l.hzn_top END) AS pf_depth_cm,
        MAX(l.hzn_bot) AS obs_limit_cm,
        GROUP_CONCAT(CASE
          WHEN is_frozen_horizon(l.hzn_desgn) = 1
          THEN l.hzn_desgn END, '|') AS frozen_horizons,
        GROUP_CONCAT(coalesce(l.hzn_desgn, l.hzn_desgn_old), '|') AS all_horizons,
        COUNT(CASE
          WHEN is_frozen_horizon(l.hzn_desgn) = 1
          THEN 1 END) AS n_frozen_layers,
        COUNT(*) AS n_layers
      FROM lab_combine_nasis_ncss AS c
      JOIN lab_layer AS l USING (pedon_key)
      WHERE c.latitude_decimal_degrees IS NOT NULL
        AND c.longitude_decimal_degrees IS NOT NULL
        AND c.site_obsdate IS NOT NULL
      GROUP BY c.pedon_key
    )
    SELECT
      CASE
        WHEN pf_depth_cm IS NOT NULL THEN 'presence'
        ELSE 'absence'
      END AS candidate_type,
      CASE
        WHEN pf_depth_cm IS NULL THEN ? ELSE NULL
      END AS absence_latitude_threshold_abs_ge,
      *
    FROM pedons
    WHERE pf_depth_cm IS NOT NULL
       OR (
         pf_depth_cm IS NULL
         AND obs_limit_cm IS NOT NULL
         AND obs_limit_cm > 0
         AND abs(lat) >= ?
       )
    ORDER BY candidate_type DESC, country_key, state_key, pedlabsampnum
    """

    con = sqlite3.connect(GPKG_PATH)
    con.create_function(
        "is_frozen_horizon",
        1,
        is_frozen_horizon_designation,
        deterministic=True,
    )
    con.row_factory = sqlite3.Row
    rows = [dict(row) for row in con.execute(query, (ABSENCE_LATITUDE_THRESHOLD, ABSENCE_LATITUDE_THRESHOLD))]
    con.close()

    with RAW_OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    presence = sum(row["candidate_type"] == "presence" for row in rows)
    absence = sum(row["candidate_type"] == "absence" for row in rows)
    print(
        f"Wrote {RAW_OUTPUT} with {len(rows)} rows "
        f"({presence} presence, {absence} absence)."
    )


if __name__ == "__main__":
    main()
