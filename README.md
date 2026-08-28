<p align="center">
  <a href="https://jonschwenk.github.io/cusp/" aria-label="Open the CUSP documentation">
    <img src="docs/assets/branding/cusp-logo-lockup.png" alt="CUSP: CommUnity near-Surface Permafrost dataset" width="620">
  </a>
</p>

# CommUnity near-Surface Permafrost (CUSP)

CUSP brings geolocated near-surface permafrost observations from published
datasets, research groups, collaborators, and our own field work into one
documented table. It includes permafrost presence and absence, active-layer and
thaw-depth measurements, and depth-to-permafrost observations. Each record
retains its source, method, location, date, and relevant quality flags so users
can trace the observation and account for differences among field methods.

The public release is a versioned CSV accompanied by source citations and
release metadata. You can use the table directly or use the repository tools to
aggregate observations, sample environmental features, validate data, rebuild
the synthesis, and generate a BibTeX bibliography for the sources represented
in your analysis.

<p align="center">
  <strong><a href="https://jonschwenk.github.io/cusp/getting-started/release-products/">Download CUSP</a></strong>
  &nbsp;&middot;&nbsp;
  <a href="https://jonschwenk.github.io/cusp/getting-started/using-the-data/">Use the data</a>
  &nbsp;&middot;&nbsp;
  <a href="https://jonschwenk.github.io/cusp/user/data-use-and-attribution/">Cite the data</a>
  &nbsp;&middot;&nbsp;
  <a href="https://jonschwenk.github.io/cusp/contributing/">Contribute data</a>
</p>

## Current Data Release

<!-- CUSP_DATA_TRACKER:START -->
<table>
  <tr>
    <td align="center" width="33%"><strong><a href="https://github.com/jonschwenk/cusp/releases/tag/v1.1">v1.1</a></strong><br><sub>Latest release</sub></td>
    <td align="center" width="33%"><strong>79,389</strong><br><sub>Total observations</sub></td>
    <td align="center" width="33%"><strong>57</strong><br><sub>Included sources</sub></td>
  </tr>
  <tr>
    <td align="center"><strong>62,135</strong><br><sub>Permafrost presence</sub></td>
    <td align="center"><strong>17,254</strong><br><sub>Permafrost absence</sub></td>
    <td align="center"><strong>59,051</strong><br><sub>ALT / thaw-depth measurements</sub></td>
  </tr>
</table>
<p><sub><strong>Note:</strong> ALT / thaw-depth measurements also carry a permafrost state, so this count overlaps the presence/absence counts.</sub></p>
<!-- CUSP_DATA_TRACKER:END -->

## Citation And Source Attribution

Any scientific publication that uses CUSP data should include both of the
following:

1. A citation to CUSP itself. The current repository citation is stored in
   [`CITATION.cff`](CITATION.cff); this will be updated when a CUSP dataset
   paper is available.
2. A citation for every original dataset or publication represented in the
   CUSP rows used in the study.

The [attribution and BibTeX guide](https://jonschwenk.github.io/cusp/user/data-use-and-attribution/)
explains how to generate a source-specific bibliography from a filtered or
aggregated CUSP table. Please run that workflow on the final analysis table so
no contributing data source is omitted.

## Contributing

CUSP grows when people point us to useful public datasets or offer observations
from their own field work. A link, DOI, citation, or short description is enough
to [suggest or add data](https://jonschwenk.github.io/cusp/contributing/); CUSP
maintainers handle evaluation and ingestion. For unpublished or nonpublic data,
contact [cusp.data@gmail.com](mailto:cusp.data@gmail.com).

## License

Copyright 2026 Triad National Security, LLC. All rights reserved.

This program was produced under U.S. Government contract 89233218CNA000001 for
Los Alamos National Laboratory (LANL), which is operated by Triad National
Security, LLC for the U.S. Department of Energy/National Nuclear Security
Administration. All rights in the program are reserved by Triad National
Security, LLC and the U.S. Department of Energy/National Nuclear Security
Administration. The Government is granted for itself and others acting on its
behalf a nonexclusive, paid-up, irrevocable worldwide license in this material
to reproduce, prepare derivative works, distribute copies to the public,
perform publicly and display publicly, and permit others to do so.
