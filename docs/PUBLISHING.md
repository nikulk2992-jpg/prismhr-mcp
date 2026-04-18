# Publishing prismhr-mcp

Releases go to PyPI via **trusted publishing** — GitHub Actions authenticates
to PyPI over OIDC. No API tokens are ever stored in GitHub Secrets.

## One-time PyPI configuration

Do this once, before the first release.

1. Sign in to [pypi.org](https://pypi.org). If `prismhr-mcp` does not yet
   exist on PyPI, go to:
   <https://pypi.org/manage/account/publishing/>
   and fill in the **"Add a new pending publisher"** form:

   | Field           | Value               |
   |-----------------|---------------------|
   | PyPI Project    | `prismhr-mcp`       |
   | Owner           | `nikulk2992-jpg`    |
   | Repository name | `prismhr-mcp`       |
   | Workflow name   | `publish.yml`       |
   | Environment     | `release` (recommended) |

2. In GitHub, create an environment named `release`:
   `Settings → Environments → New environment → release`.
   Optionally add required reviewers so tag pushes prompt for approval
   before the package actually hits PyPI.

That's it. GitHub's OIDC token is now trusted by PyPI for this project.

## Cutting a release

1. Bump `version` in `pyproject.toml`. Examples:
   - Name reservation: `0.1.0.dev0`
   - Stable: `0.1.0`, `0.2.0`, `1.0.0`
2. Commit: `git commit -am "release: vX.Y.Z"`
3. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
4. Push: `git push origin main --tags`

The `publish.yml` workflow will:
- Verify the git tag matches `pyproject.toml`'s `version`.
- Run the full pytest suite against Python 3.11 / 3.12 / 3.13.
- Build the sdist + wheel.
- Upload to PyPI via OIDC. If an environment was set up, this step is
  blocked until an approver clicks "Approve".

## Emergency yanks

`uv` + `twine` have no API for yanking. Use the PyPI web UI:
<https://pypi.org/manage/project/prismhr-mcp/releases/>

Yanks hide a release from `pip install prismhr-mcp` (users get the prior
version) while preserving it for anyone who pinned it explicitly. Yanking
is preferable to deletion; deletion permanently burns the version number.
