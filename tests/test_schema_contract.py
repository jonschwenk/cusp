from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

from cusp.schema_contract import (
    CANONICAL_COLUMNS,
    OBS_ID_COMPONENT_COLUMNS,
    SCHEMA_CONTRACT,
    build_cusp_obs_id,
    quality_flag_vocabulary_matches,
    validate_canonical_dataframe,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
V11_PATH = REPO_ROOT / "exports" / "archived" / "v1.1" / "cusp_v1.1.csv"
V10_PATH = REPO_ROOT / "exports" / "archived" / "v1.0" / "cusp_v1.0.csv"
EXPECTED_COLUMNS = (
    "cusp_obs_id",
    "source",
    "site_id",
    "lat",
    "lon",
    "date",
    "pf_observed",
    "thaw_depth",
    "pf_depth",
    "obs_limit",
    "method",
    "quality_flags",
)


def valid_observation() -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "source": ["Daanen_2017"],
            "site_id": ["A1"],
            "lat": [65.0],
            "lon": [-147.0],
            "date": ["2020-08-01"],
            "pf_observed": [1],
            "thaw_depth": [40.0],
            "pf_depth": [40.0],
            "obs_limit": [120.0],
            "method": ["tp"],
            "quality_flags": [""],
        }
    )
    frame.insert(0, "cusp_obs_id", build_cusp_obs_id(frame))
    return frame


class CanonicalSchemaContractTests(unittest.TestCase):
    def test_v11_contract_shape_is_frozen(self) -> None:
        self.assertEqual(SCHEMA_CONTRACT["established_in_dataset_version"], "v1.1")
        self.assertEqual(CANONICAL_COLUMNS, EXPECTED_COLUMNS)
        self.assertEqual(
            OBS_ID_COMPONENT_COLUMNS,
            tuple(column for column in EXPECTED_COLUMNS if column not in {"cusp_obs_id", "quality_flags"}),
        )

    def test_observation_id_algorithm_is_frozen(self) -> None:
        components = pd.DataFrame(
            {
                "source": ["Example_A"],
                "site_id": ["A1"],
                "lat": [65.0],
                "lon": [-147.0],
                "date": ["2020-08-01"],
                "pf_observed": [1],
                "thaw_depth": [40.0],
                "pf_depth": [40.0],
                "obs_limit": [120.0],
                "method": ["tp"],
            }
        )
        self.assertEqual(build_cusp_obs_id(components).iloc[0], "obs_9b584bc6e0a660b9")

    def test_v11_release_conforms_to_contract(self) -> None:
        result = validate_canonical_dataframe(pd.read_csv(V11_PATH, low_memory=False))
        self.assertTrue(result.ok, result.details_frame().to_string(index=False))

    def test_v10_predates_quality_flag_contract(self) -> None:
        result = validate_canonical_dataframe(pd.read_csv(V10_PATH, low_memory=False))
        self.assertEqual(result.counts["column_mismatch"], 1)

    def test_quality_flag_registry_matches_contract(self) -> None:
        self.assertTrue(
            quality_flag_vocabulary_matches(REPO_ROOT / "data" / "quality_flag_definitions.csv")
        )

    def test_column_changes_are_rejected(self) -> None:
        frame = valid_observation()
        reordered = frame.loc[:, list(reversed(frame.columns))]
        extra = frame.assign(new_column="not allowed")
        self.assertEqual(validate_canonical_dataframe(reordered).counts["column_mismatch"], 1)
        self.assertEqual(validate_canonical_dataframe(extra).counts["column_mismatch"], 1)

    def test_types_vocabularies_and_ids_are_enforced(self) -> None:
        invalid_type = valid_observation()
        invalid_type["site_id"] = invalid_type["site_id"].astype(object)
        invalid_type.loc[0, "site_id"] = 123
        self.assertGreater(validate_canonical_dataframe(invalid_type).counts["invalid_type"], 0)

        invalid_source = valid_observation()
        invalid_source.loc[0, "source"] = "Unregistered_Source"
        invalid_source["cusp_obs_id"] = build_cusp_obs_id(invalid_source)
        self.assertGreater(validate_canonical_dataframe(invalid_source).counts["invalid_vocabulary"], 0)

        invalid_flag = valid_observation()
        invalid_flag.loc[0, "quality_flags"] = "ZZ"
        self.assertGreater(validate_canonical_dataframe(invalid_flag).counts["invalid_vocabulary"], 0)

        invalid_id = valid_observation()
        invalid_id.loc[0, "cusp_obs_id"] = "obs_0000000000000000"
        self.assertGreater(validate_canonical_dataframe(invalid_id).counts["identifier_mismatch"], 0)

    def test_row_semantics_are_enforced(self) -> None:
        absence_with_depth = valid_observation()
        absence_with_depth.loc[0, "pf_observed"] = 0
        absence_with_depth["cusp_obs_id"] = build_cusp_obs_id(absence_with_depth)
        self.assertGreater(
            validate_canonical_dataframe(absence_with_depth).counts["invalid_relationship"],
            0,
        )

        duplicate = pd.concat([valid_observation(), valid_observation()], ignore_index=True)
        self.assertGreater(validate_canonical_dataframe(duplicate).counts["identifier_mismatch"], 0)


if __name__ == "__main__":
    unittest.main()
