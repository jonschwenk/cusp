# CommUnity near-Surface Permafrost (CUSP)

CUSP is the CommUnity near-Surface Permafrost data synthesis. It brings
near-surface permafrost observations from many source datasets into a shared,
documented table with source citations and reproducible processing tools.

## Documentation

The best starting point is the documentation site:

- [CUSP documentation](https://jonschwenk.github.io/cusp/)
- [Release products](docs/getting-started/release-products.md)
- [Caveats](docs/getting-started/caveats.md)
- [Data schema](docs/user/data-schema.md)
- [Data use and attribution](docs/user/data-use-and-attribution.md)

## Core CUSP Data

CUSP release bundles use flat, versioned filenames:

| File | What it is for |
| --- | --- |
| `cusp_vX.Y.csv` | Main CUSP table with one row per accepted observation |
| `cusp_features_vX.Y.csv` | Environmental features sampled with Google Earth Engine and joined by `cusp_obs_id`, when included |
| `cusp_sources_vX.Y.bib` | BibTeX entries for included source datasets and publications |
| `RELEASE_INFO.md` | Release metadata, hashes, and build context |

The latest release files are expected under:

- [`exports/latest/`](exports/latest)

Archived public versions are distributed through GitHub Releases.

## Using The Tools

You do not need to install CUSP to use the dataset. Download the release files
directly if that is all you need.

CUSP cannot be downloaded from conda or pip. To use the repository tools, clone
the repo and create the included conda environment:

```bash
git clone https://github.com/jonschwenk/cusp.git
cd cusp
conda env create -f environment.yml
conda activate cusp
```

Common commands:

```bash
python -m cusp.build
python -m cusp.qc validate-combined
python -m cusp.aggregate
python -m cusp.qc validate-aggregated
python -m cusp.citations --input path/to/your_cusp_table.csv --output references.bib
```

Feature sampling uses your own Google Earth Engine account and project:

```bash
earthengine authenticate
python -m cusp.features \
  --input exports/latest/cusp_v1.0.csv \
  --output runs/examples/cusp_v1.0_features.csv \
  --manifest runs/examples/cusp_v1.0_features_manifest.json \
  --gee-project <your-earth-engine-project> \
  --resume
```

## Contributing

CUSP grows through community contributions. You can suggest a dataset even if it
is not ready for ingestion, including unpublished data you are willing to share.

- [Suggest a dataset](docs/contributing/suggest-dataset.md)
- [Adding data](docs/contributing/adding-data.md)
- [Adding new GEE features](docs/contributing/adding-gee-features.md)
- [Process script header guidelines](docs/contributing/process-script-header-guidelines.md)

## Attribution

Permafrost observations are costly in time and money. If you use CUSP, cite the
CUSP release and the original datasets or publications behind the records you
used.

Use the citation helper to export BibTeX entries for a filtered or aggregated
CUSP table:

```bash
python -m cusp.citations --input path/to/your_cusp_table.csv --output references.bib
```

See [Data use and attribution](docs/user/data-use-and-attribution.md).

## Maintainers

Release process notes, validation records, and source-clearance guidance are in
the [For Maintainers](docs/maintainers/index.md) section.

## License

The current repo-wide license is in [LICENSE.txt](LICENSE.txt).
