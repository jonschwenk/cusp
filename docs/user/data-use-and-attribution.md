# Data Use And Attribution

Proper attribution is important. Permafrost observations are costly in time and
money, and we want to ensure that contributors to CUSP receive attribution that
acknowledges this cost in the form of citations.

**As a CUSP user, it is your responsibility to make sure you are citing all the
sources from which you have used data.**

CUSP provides a citation tool that can export a BibTeX file based on your
particular CUSP dataset after you have filtered, aggregated, or otherwise
downselected from the raw release.

See the [Caveats](../getting-started/caveats.md) page before using CUSP in an
analysis.

## What To Cite

**You must cite:**

1. The original datasets/publications behind the records used. Use the
   [CUSP citation tool](#export-bibtex-for-your-cusp-subset).
2. The CUSP code repository:
   `Schwenk, J. CUSP: CommUnity near-Surface Permafrost data synthesis.
   https://github.com/jonschwenk/cusp`
3. The CUSP dataset paper: `[placeholder: CUSP dataset paper citation]`

## Export BibTeX For Your CUSP Subset

Once you have finalized your own version of CUSP, use this tool to generate the
list of citations you need to include:

```bash
python -m cusp.citations --input path/to/your_cusp_table.csv --output references.bib
```

This works with tables that carry either:

- `source`
- `aggregated_sources`

The release also includes bibliography and source-reference files if you want
to inspect provenance manually.
