# LANL GitHub Mirror

[lanl/cusp](https://github.com/lanl/cusp) is an automated, one-way mirror of
[jonschwenk/cusp](https://github.com/jonschwenk/cusp). Make contributions and
maintainer changes in the upstream repository, not in the mirror.

## Synchronization

The upstream `.github/workflows/mirror.yml` runs when branches or tags are
pushed, created, or deleted, including creation through GitHub's interface. It
copies all branches, tags, and their Git history, including
tracked data and archived exports. Deleted upstream branches/tags are pruned
from the mirror, and upstream ref changes replace mirror-only changes.

The workflow uses a fresh bare repository and atomic pushes. Failures are
reported by GitHub Actions rather than suppressed. It does not depend on a
local workstation, an expiring personal access token, or a scheduled workflow.
No routine manual synchronization is required while the key and repository
permissions remain valid.

GitHub issues, pull requests, release descriptions/assets, and Pages settings
are not Git refs and are not copied. The original repository remains the home
for contributions and release downloads; the existing documentation and planned
Zenodo archive retain their roles. This mirror does not publish a new dataset
release or alter the hold on depositing v1.2 to Zenodo.

GitHub Actions is disabled in the LANL mirror to prevent duplicate CI or Pages
deployments. The mirror job also checks the repository identity so it cannot
recursively run from a copied workflow.

The workflow requires an upstream `main` branch before it changes the mirror.
If that branch is renamed, update the workflow guard and the destination's
default-branch setting deliberately. The guard prevents an unexpected empty or
misconfigured source from deleting mirror refs.

## Credentials

The dedicated write-enabled deploy key is attached only to `lanl/cusp`. Its
private key is stored only as the upstream Actions secret
`LANL_CUSP_MIRROR_SSH_KEY`. Public upstream data is fetched over HTTPS, so no
second credential is needed. The key is not attached to a personal account and
has no automatic expiry. GitHub host keys are obtained from GitHub's HTTPS API,
and SSH host verification stays enabled.

Upstream users with direct push access must also be trusted with control of the
LANL mirror: branch workflows can access the repository secret. Fork pull
requests do not trigger this workflow. Review write access accordingly and
rotate the mirror credential when that trust changes.

Never commit the private key or paste it into an issue. Repository/organization
permission changes or key revocation can still require administrator attention;
this is automatic synchronization, not a guarantee against future service or
policy changes.

## Check Or Recover

Check the upstream **Actions > Mirror to LANL** run. Its **Run workflow** button
can synchronize the current upstream refs again without creating a commit.
Address a failed run before retrying; do not hide push errors or enable direct
development in the mirror.

GitHub suppresses ordinary follow-on workflow events for changes made with
`GITHUB_TOKEN` and can suppress events for bulk ref creation. If introducing
such automation or creating tags in bulk, explicitly run this workflow as part
of that operation; a subsequent normal upstream update also reconciles all refs.
The event-driven setup intentionally avoids scheduled jobs that GitHub can
disable after prolonged repository inactivity.

To compare both repositories from a machine with Git installed:

```bash
git ls-remote --heads --tags https://github.com/jonschwenk/cusp.git
git ls-remote --heads --tags https://github.com/lanl/cusp.git
```

Matching ref names and object IDs confirm the same branches/tags and history.
For key rotation, replace both the mirror deploy key and the upstream secret,
then run and verify synchronization. Follow organizational credential policies.
