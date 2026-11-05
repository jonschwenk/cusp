"""Prevent public review maps from confusing measured depths and bounds."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "data/Yukon_Permafrost_Database/plot_ingestion_review.py"
SPEC = importlib.util.spec_from_file_location("yukon_review", SCRIPT)
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


@pytest.fixture(scope="module")
def rows():
    return review.prepare_review_rows(pd.read_csv(review.RELEASE), pd.read_csv(review.PROCESSED))


def test_review_keeps_all_release_observations_and_quantities(rows):
    assert len(rows) == 973
    assert rows.cusp_obs_id.is_unique
    assert rows.review_quantity.value_counts().to_dict() == {
        "presence_upper_bound": 923,
        "measured_thaw_depth": 46,
        "non_detection_observed_reach": 4,
    }
    bounds = rows[rows.review_quantity.eq("presence_upper_bound")]
    assert bounds[["thaw_depth", "pf_depth"]].isna().all().all()
    assert bounds.review_depth_cm.equals(bounds.obs_limit)
    measured = rows[rows.review_quantity.eq("measured_thaw_depth")]
    assert measured.review_depth_cm.equals(measured.thaw_depth)


def test_thermal_symbols_are_existing_latest_qualifying_observations(rows):
    thermal = rows[rows.ingestion_tier.eq("two_year_temperature_bound")]
    selected = thermal[thermal.depth_panel_selected]
    assert len(thermal) == 170
    assert len(selected) == 28
    assert selected.site_id.is_unique
    latest = thermal.groupby("site_id").thermal_year.max().sort_index()
    actual = selected.set_index("site_id").thermal_year.sort_index()
    pd.testing.assert_series_equal(actual, latest)
    assert actual.min() == 2012
    assert actual.max() == 2020
    assert rows.loc[~rows.index.isin(thermal.index), "depth_panel_selected"].all()


def test_review_rejects_source_release_depth_disagreement():
    processed = pd.read_csv(review.PROCESSED)
    processed.loc[0, "obs_limit"] += 1
    with pytest.raises(AssertionError, match="Source/release mismatch"):
        review.prepare_review_rows(pd.read_csv(review.RELEASE), processed)
