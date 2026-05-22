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
import sqlite3
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parent
GPKG_PATH = SOURCE_DIR / "ncss_labdata.gpkg"
RAW_OUTPUT = SOURCE_DIR / "raw_ncss_permafrost_domain_pedons.csv"
ABSENCE_LATITUDE_THRESHOLD = 55.0


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
           AND (
             lower(coalesce(l.hzn_desgn, '')) LIKE '%f%'
             OR lower(coalesce(l.hzn_desgn_old, '')) LIKE '%f%'
           )
          THEN l.hzn_top END) AS pf_depth_cm,
        MAX(l.hzn_bot) AS obs_limit_cm,
        GROUP_CONCAT(CASE
          WHEN lower(coalesce(l.hzn_desgn, '')) LIKE '%f%'
            OR lower(coalesce(l.hzn_desgn_old, '')) LIKE '%f%'
          THEN coalesce(l.hzn_desgn, l.hzn_desgn_old) END, '|') AS frozen_horizons,
        GROUP_CONCAT(coalesce(l.hzn_desgn, l.hzn_desgn_old), '|') AS all_horizons,
        COUNT(CASE
          WHEN lower(coalesce(l.hzn_desgn, '')) LIKE '%f%'
            OR lower(coalesce(l.hzn_desgn_old, '')) LIKE '%f%'
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
