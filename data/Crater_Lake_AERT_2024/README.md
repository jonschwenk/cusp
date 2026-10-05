# Crater Lake Direct Probes

Tracking: [issue #41](https://github.com/jonschwenk/cusp/issues/41).
Working ingestion prepared on 2026-10-05; `release_clearance = "needs_review"`.
No official release has been changed.

## Source And Reproduction

Source: [Herring et al. (2024), Zenodo v1.0](https://doi.org/10.5281/zenodo.13754727),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The archived
`data_AERT/probing_data.txt` is preserved unchanged.
`input_manifest.json` records archive/member checksums, retrieval, unit evidence,
and the published representative site coordinate; `zenodo_metadata.json` preserves
the archived attribution and license. The record credits Farzamian, Vieira, and
de Pablo for the data and Herring for the notebook.

The [Farzamian et al. (2024) paper](https://doi.org/10.5194/tc-18-4197-2024)
describes the field measurements at Crater Lake, Deception Island, Antarctica.
Only its **manual probing**, not ERT inversion results, is ingested here.

Run offline from the repository root:

```powershell
python data/Crater_Lake_AERT_2024/process_crater_lake_aert_2024.py
```

## Accounting And Representation

The source table has five dated rows, two probe columns (`[3,2]`, `[3,3]`), and
one derived mean column. The processor retains **10 measurements**, excludes the
**5 non-independent mean cells**, and records all 15 decisions in
`processing_audit.csv`. Probe depths range from 26 to 35 cm. All reported dates
are retained: 2009-02-15, 2010-01-30, 2011-02-10, 2019-02-04, and 2020-02-15.
The archived notebook divides probing values by 100 before plotting metres,
confirming centimetres in the input file. No depth conversion or assigned date
is needed. At this monitored permafrost site, positive probed thaw depths become
`pf_observed = 1` and `pf_depth = thaw_depth`, with `method = "tp"`.

Both labelled nodes use the **published representative site location**, not
individual GPS coordinates: 62 degrees 59 minutes 06.7 seconds S,
60 degrees 40 minutes 44.8 seconds W (paper, section 2.1).
Every observation is flagged `CS`. Node labels are preserved, but their axis
order, grid orientation, and precise positions are not reconstructed. The
separate 50 cm sensor GIS archive is not used to invent a coordinate crosswalk.

## Overlap And Limitations

`CALM_South` already has 20 annual A16 summaries (2006-2025), including all five
probe years. Its corresponding annual values are 34, 31, 28, 29, and 36 cm;
the two-node means here are 33.5, 31.5, 27.8, 29.5, and 34.5 cm. These are
different spatial summaries, not interchangeable measurements. Keep the direct
dated probes and the annual grid summaries, without importing the five derived
means or rewriting existing annual depths/dates. All new probes have `DO` to
surface their component-to-summary overlap; they must not be counted as
statistically independent evidence of the same site's annual conditions.
No proximity-based deletion or temporal thinning is applied.

Raw ERT, resistivity models, climate data, temperature series, and newly
interpreted thaw interfaces remain excluded. ERT-derived depth requires
threshold and sensitivity choices; revisit that component only with a reviewed
depth interpretation, georeferencing, and overlap plan. Site-level coordinates
are adequate for this limited import, but not for grid-node spatial analysis.
