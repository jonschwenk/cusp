# Contribute Data To CUSP

CUSP grows when people point us to useful public data or offer observations
from their own field work. A dataset does not need to be formatted for CUSP or
ready for ingestion before it is worth sharing with us.

You do not need to write processing code, investigate duplication, determine
licensing, or know whether a source meets every CUSP requirement. CUSP
maintainers handle evaluation and ingestion. Original datasets remain
individually identified in CUSP so users can find and cite the source work.

!!! tip "A link is enough"
    For public data, a repository page, DOI, paper, project page, or download
    link is enough to start the review.

## Publicly Available Data

Open the short data-intake issue and paste the best link or citation you have.
Please link to the canonical repository or source rather than uploading a copy
to the issue.

[Suggest or add data to CUSP](https://github.com/jonschwenk/cusp/issues/new?template=dataset_candidate.yml){ .md-button .md-button--primary }

If you do not use GitHub, email the link or description to
[cusp.data@gmail.com](mailto:cusp.data@gmail.com). A maintainer can record the
suggestion in the issue tracker.

## Unpublished Or Nonpublic Data

The GitHub issue is public, so do not attach unpublished or restricted files or
post private contact information. Open an issue with a public-safe description,
select **Unpublished or not publicly available**, and then email
[cusp.data@gmail.com](mailto:cusp.data@gmail.com) with the issue number. We will
coordinate communications and data sharing by email.

If even a brief public description would be inappropriate, email us first. A
CUSP maintainer can help determine what information can be recorded in the
tracking issue.

## What CUSP Can Use

CUSP focuses on geolocated, direct observations relevant to near-surface
permafrost, including:

- permafrost presence or absence
- active-layer thickness, thaw depth, or frost-table depth
- depth to permafrost
- soil-pit, core, auger, probe, or related field observations
- field geophysics such as GPR or ERT when the measurements can be represented
  appropriately

Coordinates, dates, methods, citation information, and permission for public
reuse will eventually be needed, but you do not need to investigate all of
those before contacting us. If you are unsure whether data fit, please submit
them for consideration.

## What Happens Next

1. A CUSP maintainer reviews the tracking issue and investigates the source.
2. We check scope, access, spatial and temporal information, permissions, and
   possible overlap with data already in CUSP.
3. We follow up in the issue or through `cusp.data@gmail.com` when we need help
   from the person suggesting or providing the data.
4. The CUSP team handles processing, quality flags, deduplication, and release
   integration.
5. The issue records the outcome and, for accepted data, links the source to
   the corresponding CUSP update.

Developers who want to extend the optional environmental-feature workflow can
also see [Adding new GEE features](adding-gee-features.md).
