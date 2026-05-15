<section class="cusp-hero" markdown="1">

# CUSP

The CommUnity near-Surface Permafrost dataset is a data synthesis for
near-surface permafrost, active-layer, thaw-depth, and related field
observations.

CUSP brings many published and field datasets into one documented table, with
source citations and tools that make the synthesis easier to check, rebuild,
and extend.

[Start with the data](getting-started/release-products.md){ .md-button .md-button--primary }
[Suggest a dataset](contributing/suggest-dataset.md){ .md-button }

</section>

<div class="cusp-card-grid" markdown="1">

<div class="cusp-card" markdown="1">
### Use CUSP

Find the release files, understand the columns, and cite the dataset and
underlying sources correctly.

[Release products](getting-started/release-products.md)
</div>

<div class="cusp-card" markdown="1">
### Work With The Data

Use the CUSP tools to rebuild the data, check the files, create spatial
summaries, or add environmental information from Google Earth Engine.

[Rebuild and process CUSP](user/cli-examples.md)
</div>

<div class="cusp-card" markdown="1">
### Contribute Data

Suggest a dataset, prepare a new dataset, or add an environmental layer to the
feature sampler.

[Contributing guide](contributing/index.md)
</div>

<div class="cusp-card" markdown="1">
### See How CUSP Is Built

Review the source inputs, rebuild steps, and known limitations behind the
current release.

[Build and source notes](reproducibility/index.md)
</div>

</div>

## First Steps

| If you want to... | Start here |
| --- | --- |
| Understand what CUSP is and is not | [What CUSP is](getting-started/what-is-cusp.md) |
| Use the released data | [Release products](getting-started/release-products.md) |
| Read the public columns | [Data schema](user/data-schema.md) |
| Rebuild or process CUSP on your computer | [Command examples](user/cli-examples.md) |
| Add or suggest a source dataset | [Suggest a dataset](contributing/suggest-dataset.md) |
| Rebuild the current release artifacts | [Rebuild CUSP](reproducibility/rebuild-cusp.md) |

## Core CUSP Data

Each CUSP release is meant to be small enough to understand and specific enough
to cite.

| File | What it is for |
| --- | --- |
| `cusp_vX.Y.csv` | Main CUSP table with one row per accepted observation |
| `cusp_features_vX.Y.csv` | Environmental features sampled with Google Earth Engine and joined by `cusp_obs_id`, when included |
| `cusp_sources_vX.Y.bib` | BibTeX entries for included source datasets and publications |
| `RELEASE_INFO.md` | Release metadata, hashes, and build context |
