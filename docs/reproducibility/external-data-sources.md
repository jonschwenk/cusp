# External Data Sources

This file tracks oversized or otherwise external raw inputs that are needed to
rebuild some CUSP source products but are not stored in the Git repository.

For CUSP v1, the project decision is that oversized rebuild inputs should be
hosted outside GitHub in a read-only Google Drive, while the repo keeps:

- the processing script
- the processed CUSP output
- the provenance/citation metadata
- the retrieval instructions needed to rebuild locally

Before public release, each external input should have:

- a stable download location
- an expected file size
- a checksum if practical
- clear access notes
- a last-verified date

## Registry

| source | required file | approx size | repo status | external host | access status | local path expected by script | notes |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| `Moore_et_al_2025` | `ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv` | `111 MB` | gitignored; kept local only | read-only Google Drive | read-only shared link: [download/view](https://drive.google.com/file/d/1OI_5sI5T_66fJ9xkCbthuY8PuiLI0PQ4/view?usp=sharing) | `data/Moore_et_al_2025/ABoVE_Soil_ThawDepth_Moisture_Validation_V2.csv` | Local execution audit succeeded once the file was added. File is above GitHub's regular per-file Git limit, so it should remain external unless Git LFS is adopted. |

## Suggested metadata to add later

For each external input, add these fields once the hosting path is finalized:

- direct download URL or shared folder path
- checksum or hash
- source-system version
- maintainer who verified the link
- date last verified
