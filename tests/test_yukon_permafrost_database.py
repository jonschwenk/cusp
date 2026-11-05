"""Focused tests for Yukon source interpretation and inference safeguards."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


PROCESSOR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "Yukon_Permafrost_Database"
    / "process_yukon_permafrost_database.py"
)
SPEC = importlib.util.spec_from_file_location("yukon_processor", PROCESSOR)
yukon = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(yukon)


def profile(**overrides):
    row = {
        "PERMAFROST_DESC": "Permafrost encountered",
        "COMMENTS": "",
        "TOP_DEPTH": "0",
        "BOT_DEPTH": "2",
        "SURFACE_THAW": "",
        "ICE_CODE": "F",
        "ID": "1",
        "SITE_ID": "site-1",
    }
    row.update(overrides)
    return row


def thermal_row(location, depth, year, **overrides):
    row = {
        "location_id": location,
        "depth_m": str(depth),
        "year": str(year),
        "accuracy": "0.1",
        "coverage": "0.96",
        "maxgap": "7",
        "max_temp": "-0.11",
        "methods": "thermistor",
        "who": "provider-a",
        "comments": "",
    }
    row.update(overrides)
    return row


def station(name="station", permafrost="Yes"):
    return {
        "NAME": name,
        "PERMAFROST": permafrost,
        "LATITUDE": "65.0",
        "LONGITUDE": "-135.0",
    }


def test_explicit_permafrost_required_even_with_thaw_value():
    assert yukon.explicit_permafrost(profile(PERMAFROST_DESC="Permafrost present"))
    assert not yukon.explicit_permafrost(
        profile(PERMAFROST_DESC="Unfrozen", SURFACE_THAW="1.2")
    )
    assert not yukon.explicit_permafrost(
        profile(PERMAFROST_DESC="No permafrost observed")
    )


@pytest.mark.parametrize(
    "top,bottom,hole,expected",
    [
        ("0", "0", 1, True),
        ("0", "1", 1, True),
        ("1", "1", 1, True),
        ("-0.01", "1", 1, False),
        ("0", "1.01", 1, False),
        ("1", "0", 1, False),
        ("", "1", 1, False),
        ("0", "NaN", 1, False),
    ],
)
def test_interval_bounds_and_inversions(top, bottom, hole, expected):
    assert yukon.valid_interval(
        profile(TOP_DEPTH=top, BOT_DEPTH=bottom), hole
    ) is expected


@pytest.mark.parametrize(
    "description,comments",
    [
        ("No permafrost encountered", ""),
        ("Non-permafrost deposit", ""),
        ("Permafrost not observed", ""),
        ("Permafrost present", "Possibly seasonal"),
        ("Possible permafrost", ""),
        ("Permafrost", "Likely present"),
    ],
)
def test_negative_or_uncertain_permafrost_words_do_not_qualify(description, comments):
    assert not yukon.explicit_permafrost(
        profile(PERMAFROST_DESC=description, COMMENTS=comments)
    )


def _geotech_location(site_id, date_text, transformer):
    east, north = 500000, 7200000
    lon, lat = transformer.transform(east, north)
    return {
        "SITE_ID": site_id,
        "START_DATE": date_text,
        "END_DATE": date_text,
        "HOLE_DEPTH": "3",
        "UTMZONE": "8",
        "EASTING": str(east),
        "NORTHING": str(north),
        "LATITUDE": str(lat),
        "LONGITUDE": str(lon),
        "COORD_ACQ": "UTM",
        "EQUIPMENT": "auger",
        "HOLE_TYPE": "B",
    }


def test_late_summer_frozen_interval_can_qualify_but_winter_does_not():
    pyproj = pytest.importorskip("pyproj")
    transformer = pyproj.Transformer.from_crs(26908, 4326, always_xy=True)
    summer = _geotech_location("summer", "15-Aug-20", transformer)
    winter = _geotech_location("winter", "15-Jan-20", transformer)
    records, audit = yukon.geotech_records(
        [summer, winter],
        {
            # Frozen interval codes alone are only accepted in late summer;
            # neither row explicitly names permafrost.
            "summer": [profile(PERMAFROST_DESC="Frozen ground")],
            "winter": [profile(SITE_ID="winter", PERMAFROST_DESC="Frozen ground")],
        },
    )

    assert [record["site_id"] for record in records] == ["summer"]
    assert records[0]["ingestion_tier"] == "late_summer_frozen_bound"
    assert records[0]["quality_flag_pf_state_assumed"] is True
    decisions = {row["site_id"]: row["decision"] for row in audit}
    assert decisions["winter"] == "no_supported_permafrost_evidence"


def test_interval_bound_is_not_emitted_as_an_exact_depth():
    pyproj = pytest.importorskip("pyproj")
    transformer = pyproj.Transformer.from_crs(26908, 4326, always_xy=True)
    location = _geotech_location("bound", "15-Jun-20", transformer)
    interval = profile(TOP_DEPTH="1", BOT_DEPTH="2")
    records, _ = yukon.geotech_records([location], {"bound": [interval]})

    assert len(records) == 1
    record = records[0]
    assert record["ingestion_tier"] == "source_permafrost_bound"
    assert record["obs_limit"] == 200
    assert record["quality_flag_upper_bound_presence"] is True
    assert record["pf_depth"] is None
    assert record["thaw_depth"] is None


def test_thermal_year_requires_known_accuracy_and_all_quality_thresholds():
    baseline = thermal_row("s", 1, 2020)
    assert yukon.year_qualifies(baseline)
    assert not yukon.year_qualifies({**baseline, "accuracy": ""})
    assert not yukon.year_qualifies({**baseline, "coverage": "0.9499"})
    assert not yukon.year_qualifies({**baseline, "maxgap": "8"})
    # The warmest raw extreme must be strictly colder than the documented margin.
    assert not yukon.year_qualifies({**baseline, "max_temp": "-0.1"})
    assert not yukon.year_qualifies({**baseline, "max_temp": "0"})


def test_thermal_requires_same_method_provider_and_consecutive_qualifying_years():
    annual = [
        thermal_row("good", 0.5, 2020),
        thermal_row("good", 0.5, 2021),
        thermal_row("method-change", 0.5, 2020),
        thermal_row("method-change", 0.5, 2021, methods="logger"),
        thermal_row("provider-change", 0.5, 2020),
        thermal_row("provider-change", 0.5, 2021, who="provider-b"),
        thermal_row("metadata-no", 0.5, 2020),
        thermal_row("metadata-no", 0.5, 2021),
        thermal_row("unknown-accuracy", 0.5, 2020, accuracy=""),
        thermal_row("unknown-accuracy", 0.5, 2021, accuracy=""),
        thermal_row("gap", 0.5, 2020),
        thermal_row("gap", 0.5, 2022),
    ]
    locations = {
        "good": station("good"),
        "method-change": station("method-change"),
        "provider-change": station("provider-change"),
        "metadata-no": station("metadata-no", permafrost="No"),
        "unknown-accuracy": station("unknown-accuracy"),
        "gap": station("gap"),
    }

    records, audit = yukon.thermal_records(annual, locations)

    # Each two-year pair supports a dated summary for its later year.
    assert [(r["site_id"], r["thermal_year"]) for r in records] == [("good", 2021)]
    decisions = {(r["site_id"], r.get("depth_m")): r["decision"] for r in audit}
    assert decisions[("metadata-no", 0.5)] == "hold_station_metadata_no"
    assert decisions[("unknown-accuracy", 0.5)] == "hold_unknown_instrument_accuracy"
    assert decisions[("gap", 0.5)] == "hold_insufficient_two_year_cold_evidence"
    assert decisions[("method-change", 0.5)] == "hold_sensor_provider_change_or_comments"
    assert decisions[("provider-change", 0.5)] == "hold_sensor_provider_change_or_comments"


def test_thermal_selects_shallowest_qualifying_depth_per_station_year():
    annual = [
        thermal_row("s", 1.0, year) for year in (2020, 2021)
    ] + [thermal_row("s", 0.5, year) for year in (2020, 2021)]

    records, _ = yukon.thermal_records(annual, {"s": station("s")})

    assert len(records) == 1
    assert [record["thermal_year"] for record in records] == [2021]
    assert all(record["obs_limit"] == 50 for record in records)
    assert all(record["pf_depth"] is None for record in records)
    assert all(record["thaw_depth"] is None for record in records)


def test_unfrozen_profile_requires_contiguous_evidence_and_never_uses_unlogged_hole_bottom():
    location = {
        'SITE_ID': 'gps', 'START_DATE': '13-Oct-23', 'END_DATE': '13-Oct-23',
        'HOLE_DEPTH': '4', 'UTMZONE': '', 'EASTING': '', 'NORTHING': '',
        'LATITUDE': '62.38855', 'LONGITUDE': '-140.8816', 'COORD_ACQ': 'Avenza',
        'EQUIPMENT': 'Sonic Drill', 'HOLE_TYPE': 'B',
    }
    intervals = [profile(PERMAFROST_DESC='Not frozen',ICE_CODE='',TOP_DEPTH='0',BOT_DEPTH='1'),
                 profile(PERMAFROST_DESC='Not frozen',ICE_CODE='',ID='2',TOP_DEPTH='1',BOT_DEPTH='2'),
                 profile(PERMAFROST_DESC='Not frozen',ICE_CODE='',ID='3',TOP_DEPTH='3',BOT_DEPTH='4')]
    records,_ = yukon.geotech_records([location], {'gps': intervals})
    assert len(records)==1
    assert records[0]['pf_observed']==0
    assert records[0]['obs_limit']==200  # Gap 2-3 m prevents a 4 m claim.
    assert records[0]['pf_depth'] is None and records[0]['thaw_depth'] is None
    assert records[0]['quality_flag_coord_source_flagged'] is True
    assert records[0]['quality_flag_obs_limit_profile_bottom'] is True


def test_pinned_staged_snapshot_counts_and_bounds():
    import csv
    import collections
    rows=list(csv.DictReader((PROCESSOR.parent/'processed_yukon_permafrost_database.csv').open(encoding='utf-8')))
    assert len(rows)==973
    assert collections.Counter(r['ingestion_tier'] for r in rows)=={
        'direct_thaw':46,'late_summer_frozen_bound':624,'source_permafrost_bound':129,
        'two_year_temperature_bound':170,'explicit_profile_non_detection':1,
        'continuous_unfrozen_profile_non_detection':3,
    }
    assert len({(r['site_id'],r['date']) for r in rows})==len(rows)
    for row in rows:
        if row['ingestion_tier']!='direct_thaw':
            assert row['pf_depth']==row['thaw_depth']==''
            assert float(row['obs_limit'])>0


def test_frozen_code_cannot_override_negative_or_seasonal_description():
    assert not yukon.frozen(profile(PERMAFROST_DESC='Not frozen',ICE_CODE='F'))
    assert not yukon.frozen(profile(PERMAFROST_DESC='Seasonal frost',ICE_CODE='N'))
    assert not yukon.frozen(profile(PERMAFROST_DESC='No permafrost encountered',ICE_CODE='F'))


def test_csv_column_order_is_independent_of_dictionary_insertion(tmp_path):
    first=tmp_path/'one.csv';second=tmp_path/'two.csv'
    yukon.write_csv(first,[{'lon':-135,'site_id':'s','quality_flag_upper_bound_presence':True,'quality_flag_pf_state_assumed':True}])
    yukon.write_csv(second,[{'quality_flag_pf_state_assumed':True,'site_id':'s','quality_flag_upper_bound_presence':True,'lon':-135}])
    assert first.read_bytes()==second.read_bytes()
