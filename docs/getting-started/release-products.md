# Download CUSP

CUSP releases are distributed as a small, flat bundle. If you are using CUSP
for analysis, start with the versioned release files rather than the working
files used inside the repository.

## Current Release

The current public release is **CUSP v1.1**. Download the observation table and
keep its source bibliography and release metadata with your analysis.

<div class="cusp-button-row" markdown="1">

[Download the v1.1 CSV](https://github.com/jonschwenk/cusp/releases/download/v1.1/cusp_v1.1.csv){ .md-button .md-button--primary }
[Download the source BibTeX](https://github.com/jonschwenk/cusp/releases/download/v1.1/cusp_sources_v1.1.bib){ .md-button }
[Download release metadata](https://github.com/jonschwenk/cusp/releases/download/v1.1/RELEASE_INFO.md){ .md-button }

</div>

[View v1.1 release notes and checksums](https://github.com/jonschwenk/cusp/releases/tag/v1.1)

## Other Versions And Repository Copy

For the full suite of public releases, use the repository's GitHub Releases
page:

[All CUSP versions](https://github.com/jonschwenk/cusp/releases){ .md-button }

The latest files are also mirrored on the `main` branch for repository-based
workflows:

[Browse `exports/latest`](https://github.com/jonschwenk/cusp/tree/main/exports/latest){ .md-button }

The detailed export rules are documented in
[Versioning and exports](../release/versioning-and-exports.md).

!!! important "Before using the table"

    Read [Caveats and limits](caveats.md), then use the
    [introductory data guide](using-the-data.md) to interpret rows and quality
    flags. Plan for [attribution and BibTeX](../user/data-use-and-attribution.md)
    before downselecting columns or sources.

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

[Generate BibTeX for a CUSP subset](../user/data-use-and-attribution.md#export-bibtex-for-your-cusp-subset){ .md-button }

Environmental feature tables are not canonical release products. They can be
generated from the observation CSV with the optional
[feature-sampling workflow](../user/feature-sampling.md), keyed by
`cusp_obs_id`.

For source-level caveats and citation crosswalks generated inside the working
repository, see [Source metadata](../user/source-metadata.md).
