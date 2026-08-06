# Release Products

CUSP releases are distributed as a small, flat bundle. If you are using CUSP
for analysis, start with the versioned release files rather than the working
files used inside the repository.

## Where To Get Releases

The latest release files are expected to be available in the repository on the
`main` branch:

[Latest CUSP version](https://github.com/jonschwenk/cusp/tree/main/exports/latest){ .md-button .md-button--primary }

For the full suite of public releases, use the repository's GitHub Releases
page:

[All CUSP versions](https://github.com/jonschwenk/cusp/releases){ .md-button }

The detailed export rules are documented in
[Versioning and exports](../release/versioning-and-exports.md).

## Official Bundle

| File | Purpose |
| --- | --- |
| `cusp_vX.Y.csv` | Canonical observation-level dataset |
| `cusp_sources_vX.Y.bib` | BibTeX entries for the included source datasets and publications |
| `RELEASE_INFO.md` | Release metadata, hashes, and build context |

## Which File Should I Use?

Use `cusp_vX.Y.csv` for most analyses. It contains one row per accepted
observation in the stable public schema.

Use `cusp_sources_vX.Y.bib` when preparing citations for a release. If you use
only a subset of sources, the citation helper can write a smaller BibTeX file
for the rows you used.

Environmental feature tables are not canonical release products. They can be
generated from the observation CSV with the optional
[feature-sampling workflow](../user/feature-sampling.md), keyed by
`cusp_obs_id`.

For source-level caveats and citation crosswalks generated inside the working
repository, see [Source metadata](../user/source-metadata.md).
