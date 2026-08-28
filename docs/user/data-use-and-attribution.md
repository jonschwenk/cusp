# Attribution And BibTeX

Any scientific publication or public research product that uses CUSP data is
expected to cite both CUSP itself and every original data source represented in
the rows used for the study. This applies even when only a small subset of CUSP
is used.

!!! important "Published use requires two kinds of references"

    1. Cite CUSP using the repository's
       [`CITATION.cff`](https://github.com/jonschwenk/cusp/blob/main/CITATION.cff).
    2. Cite every original dataset or publication associated with the source
       keys in your final analysis table.

Permafrost observations are costly to collect. Source-level citation ensures
that the people and organizations who provided those observations receive
credit for the data used in a study.

CUSP provides a citation tool that can export a BibTeX file based on your
particular CUSP dataset after you have filtered, aggregated, or otherwise
downselected from the raw release. This is the simplest way to build the source
bibliography for an analysis.

See the [Caveats](../getting-started/caveats.md) page before using CUSP in an
analysis.

## What To Cite

For a published analysis, include:

1. **CUSP itself.** Use the citation stored in
   [`CITATION.cff`](https://github.com/jonschwenk/cusp/blob/main/CITATION.cff).
   For now, that citation identifies this GitHub repository and the current
   dataset release.
2. **Every original source used.** Run the
   [CUSP citation tool](#export-bibtex-for-your-cusp-subset) on the final table
   to collect the dataset and publication references associated with its
   `source` values.
3. **The exact CUSP release.** Report the version and release URL. Keep
   `RELEASE_INFO.md` with the analysis record because it provides file
   checksums and build details.

When a CUSP dataset paper is published, it will be added to `CITATION.cff` as
the preferred CUSP citation. The requirement to cite the original sources used
in an analysis will remain.

## Export BibTeX For Your CUSP Subset

Once you have finalized your analysis table, use the citation helper to generate
the source bibliography you need:

```bash
python -m cusp.citations \
  --input path/to/your_cusp_table.csv \
  --master-bib exports/latest/cusp_sources_v1.1.bib \
  --output references.bib
```

This works with tables that carry either:

- `source`
- `aggregated_sources`

The helper reads those values, selects matching entries from the versioned
master bibliography, and writes a smaller BibTeX file. It does not modify your
data table. Run it again if the final row or source selection changes.

The helper is included with the repository's [CUSP tools](index.md). If you do
not run the tool, use the version-matched `cusp_sources_vX.Y.bib` file to select
and cite the underlying sources manually.

The public release includes the version-matched bibliography. A repository
build also generates `data/source_reference_crosswalk.csv` for inspecting
provenance, but that crosswalk is not part of the public release bundle.
