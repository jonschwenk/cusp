# Zenodo Release Archive

This page defines the archival model for official CUSP dataset releases. It is
written for maintainers preparing or depositing a release.

!!! note "Verified archive status"
    The existing CUSP Zenodo family contains v1.0, v1.1 and v1.2. Its version
    chain was checked on 2026-11-05, and every file inside the deposited v1.2
    ZIP matches the corresponding local archived file byte for byte. The next
    deposit is v1.3, following public map review in the ingestion issue.

## Existing Version Chain

Continue this family using **New version** on its latest published record.

| Dataset version | Version DOI |
| --- | --- |
| v1.0 | [10.5281/zenodo.22802356](https://doi.org/10.5281/zenodo.22802356) |
| v1.1 | [10.5281/zenodo.22802827](https://doi.org/10.5281/zenodo.22802827) |
| v1.2 | [10.5281/zenodo.23171354](https://doi.org/10.5281/zenodo.23171354) |

The concept DOI is
[10.5281/zenodo.22802355](https://doi.org/10.5281/zenodo.22802355).
The v1.2 record uses resource type Dataset and license CC BY 4.0. Preserve the
existing reviewed creator order, affiliations, ORCIDs and contributor metadata
when creating the next draft, subject to any maintainer-approved updates.

The v1.2 deposit contains `v1.2.zip` with the three release files inside a
`v1.2/` directory. Its contents were verified against `exports/archived/v1.2/`.
The public record establishes the existing metadata and archive structure.
Authenticated API access still requires a locally configured Zenodo token.

## Repository Roles

CUSP uses three services for different purposes:

- **Zenodo** is the authoritative archive for immutable, DOI-bearing dataset
  releases.
- **GitHub** hosts development, issue tracking, contributions, reproducibility
  code, and byte-identical release mirrors.
- **ARDAC** provides visualization and convenient access to a named CUSP
  release. ARDAC metadata should display that release's version and
  version-specific Zenodo DOI.

Zenodo creates a DOI for each immutable version and a concept DOI for the
release family. Cite a **version DOI** when data were used in an analysis. Use
the **concept DOI** for links or badges intended to resolve to the latest CUSP
release.

## Deposit CUSP As A Dataset

Create CUSP records manually with the Zenodo resource type **Dataset**. Do not
enable automatic GitHub release archiving for the CUSP repository as the
dataset publication mechanism. That integration is designed around software
source archives, while the citable CUSP object is the flat release bundle
defined in [Versioning and exports](../release/versioning-and-exports.md).

The GitHub repository could be archived separately as software in the future,
but such a record must remain distinct from the official CUSP dataset record
and its DOI.

## Publication Prerequisites

Do not publish a Zenodo draft until all of the following are settled:

1. The release has passed the CUSP release gate and its checksums have been
   reviewed.
2. The dataset creators, order, affiliations, and ORCIDs have been approved.
   Creators are the people or organizations responsible for the CUSP release;
   authors of source datasets remain credited through the release bibliography
   rather than being added automatically as CUSP creators.
3. An institutionally approved open data license has been selected and is
   compatible with the terms or permissions attached to included sources.
   Keep the code copyright notice and the dataset reuse license conceptually
   separate.
4. Source provenance and release clearance are complete, including methods for
   observations not previously described in a public source.
5. At least one backup maintainer has edit or management access to the draft or
   its CUSP Zenodo community.
6. The source tracking issue contains reproducible maps, numeric depth values
   or bounds where interpretable, validation results and explicit maintainer
   approval of the scientific interpretation and public release. Complete this
   public review before creating a Zenodo version draft or uploading its files.

Configure a Zenodo access token locally outside the repository. API automation
can continue the verified record and versioning model using `deposit:write`
and `deposit:actions` scopes. The historical initial-deposit procedure below
documents how the family is established.

## Initial Historical Deposit Procedure

Backfill the existing releases as one Zenodo version chain so that historical
versions do not become unrelated records.

### Publish v1.0

1. Sign in to Zenodo using an account connected to an ORCID.
2. Optionally create a CUSP Zenodo community and add at least one backup
   manager. A suitable institutional community may be used instead.
3. Create a new upload with resource type **Dataset**.
4. Upload the files from `exports/archived/v1.0/` without modifying them:
   `cusp_v1.0.csv`, `cusp_features_v1.0.csv`,
   `cusp_sources_v1.0.bib`, and `RELEASE_INFO.md`.
5. Set the version to `v1.0` and the original public-release date to
   `2026-05-15`.
6. Enter the reviewed metadata described below and compare every local
   SHA-256 value with `RELEASE_INFO.md`.
7. Preview the record and publish only after the creator, rights, and file
   reviews are complete.

### Add v1.1

1. Open the published v1.0 record and choose **New version**. Do not create an
   unrelated upload.
2. Remove files inherited from v1.0 and upload the exact files from
   `exports/archived/v1.1/`: `cusp_v1.1.csv`,
   `cusp_sources_v1.1.bib`, and `RELEASE_INFO.md`.
3. Set the version to `v1.1` and the public-release date to `2026-08-07`.
4. State clearly that v1.1 supersedes v1.0 and summarize the changes already
   recorded in `RELEASE_INFO.md`.
5. Verify the files and metadata, then publish the new version.
6. Record the concept DOI and both version DOIs before changing public links or
   citation metadata in the repository.

## Zenodo Metadata

Use the same reviewed metadata across versions except where the creator list,
description, dates, or relationships genuinely changed.

| Field | CUSP convention |
| --- | --- |
| Resource type | Dataset |
| Title | `CUSP: CommUnity near-Surface Permafrost data synthesis` |
| Version | The matching `vX.Y` release identifier |
| Publication date | Date that version first became public, not the later Zenodo deposit date |
| Creators | Approved CUSP dataset creators, with ORCIDs and ROR-backed affiliations when available |
| Access | Public |
| License | Institutionally approved open data license compatible with source terms |
| Language | English |
| Keywords | permafrost; active layer thickness; thaw depth; depth to permafrost; Arctic; boreal; geospatial observations; data synthesis |
| Related identifiers | GitHub release, repository, documentation, ARDAC record when available, and the Data Descriptor DOI after publication |

The description should identify the release as a synthesis, summarize its
observation types and coverage, list the files, link to the caveats and schema,
and explain the two-part citation expectation: cite the CUSP version DOI and
the original sources represented in the rows used. The version-matched BibTeX
file is part of the deposited bundle for that purpose.

## Future Release Sequence

For v1.3 and later, complete the issue-based scientific and release review
before starting this sequence. The map requirements are described in
[Adding a dataset](adding-data.md#step-8-post-public-spatial-review).

1. Build, validate, and export the final release bundle.
2. Create a **New version** draft from the latest Zenodo CUSP record.
3. Reserve its DOI before finalizing release metadata.
4. Add the concept DOI and reserved version DOI to the release record.
5. Rerun release checks, commit the exact archive, and create the Git tag.
6. Upload the final bundle to the Zenodo draft and verify checksums.
7. Publish Zenodo, then publish the GitHub Release with byte-identical files.
8. Update `CITATION.cff`, README and documentation links, and notify ARDAC of
   the version DOI and checksums.

The v1.3 GitHub Release already exists. Deposit its exact archived files after
the public map review is approved. Record the new Zenodo DOI in current
citation and documentation metadata while retaining the published bundle's
original bytes. Its `RELEASE_INFO.md` describes the hosting status when the
GitHub release was created.

Metadata-only corrections may be made on a published Zenodo record. Any change
to data or deposited files requires a new version; never silently replace an
official release.

## Scientific Data Version Of Record

The Data Descriptor must cite the immutable version DOI for the exact CUSP
snapshot reviewed with the manuscript. Later CUSP releases can continue under
the same concept DOI, but they do not replace the paper's version of record.
After the article receives a DOI, add it to the corresponding Zenodo metadata
as a related publication and retain the version-specific dataset citation in
the manuscript.

## Official Guidance

- [Zenodo: create a new upload](https://help.zenodo.org/docs/deposit/create-new-upload/)
- [Zenodo: manage versions](https://help.zenodo.org/docs/deposit/manage-versions/)
- [Zenodo: licenses and rights](https://help.zenodo.org/docs/deposit/describe-records/licenses/)
- [Zenodo: communities](https://help.zenodo.org/docs/communities/)
- [Scientific Data repository requirements](https://www.nature.com/sdata/policies/repositories)
- [Scientific Data policies for dataset updates](https://www.nature.com/sdata/policies/data-policies#dataset-updates)
