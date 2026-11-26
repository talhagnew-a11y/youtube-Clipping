# YouTube Clipping - portable ShortsFlow updates

Lightweight code updates for the existing **ShortsFlow 0.9.4** portable folder.
This is an update overlay, not the upstream app or a complete installer.

**Roman Urdu:** Ab poora heavy folder dobara copy nahi karna. Models, Python,
Ollama, Node aur videos isi laptop/hard drive par rehte hain. GitHub se sirf
chhoti updated scripts aur Python source files aati hain.

## First update on another laptop: easiest private-repo option

1. Open this private repository while signed into your GitHub account.
2. **Code -> Download ZIP**, then extract it.
3. Double-click **INSTALL-UPDATE.cmd** inside the extracted folder.
4. Choose your existing **shortsflow** folder, wherever the drive is mounted.

The installer validates the base version and every file checksum, makes a
backup, applies the small update, and starts ShortsFlow. Wait for any current
video processing to finish before updating.

## Later updates

Your shortsflow folder now has two update buttons:

- **UPDATE-FROM-ZIP.cmd**: download the latest ZIP in your signed-in browser,
  then select it. No saved GitHub token is needed.
- **UPDATE-SHORTSFLOW.cmd**: download directly from this private repo.
  On the first run on each Windows account/computer, paste a **fine-grained
  GitHub token** with access to only this repository and **Contents: Read-only**.
  Create it at <https://github.com/settings/personal-access-tokens/new>.
  Choose an expiry you are comfortable with. The token is encrypted using
  Windows DPAPI inside .update-auth, separately for each computer/account.
  It is never included in this repository. An expired/revoked token must be
  replaced by running Update-ShortsFlow.ps1 with -RefreshLogin.

No Git, agent, Python installation, or new model download is needed for updates.
The existing folder already contains the required runtime.

## What an update preserves

Models, input/output videos, transcripts, YouTube OAuth files, .env, private
keys, upload preferences, CPU/Intel benchmark profiles and other workspace data
are not update targets. They stay local. GitHub sign-in tokens are not committed.

Backups of replaced code go to update-backups. A failed file installation
attempt rolls back already changed files. Backups contain the replaced code,
not your private account data.

The update refuses to apply while it detects a running video job, or when the
installed upstream ShortsFlow version differs from 0.9.4.

## Included changes

- Portable relative-path launchers and local caches.
- Default 720p fast FFmpeg renderer with simple word captions.
- CPU/Intel comparison and per-laptop measured encoding profiles.
- CPU fallback if Intel encoding fails.
- Small GPU capability test and diagnostic reports.
- Local Ollama context/timeout adjustments.
- Clear missing-audio validation.
- Opt-in YouTube direct auto-publishing for completed shorts.

Updating does not connect YouTube or turn on auto-publishing. Connect and enable
it explicitly in the app when you want that behavior.

## Excluded

No Python/Node/Ollama/FFmpeg binaries, virtual environment dependencies, model
weights, videos, logs, hardware reports, API keys, OAuth tokens or .env files.
The payload/venv folder contains **only the small modified Python source files**.

## Maintaining this repository

Build the approved file list with Build-Update.ps1, then test and push. Example:

    .\Build-Update.ps1 -InstallRoot E:\shortsflow -Version 2026.11.26.2

When changing the portable app, copy only the approved updated scripts/source
files into the corresponding payload locations. Recompute each file's SHA-256
and byte count in update-manifest.json, increment its version, run
tests/Test-Updater.ps1, then commit and push. Do not upgrade packages
and assume these source files are compatible with another upstream version.

Validate a package without changing an installation:

    .\Apply-ShortsFlow-Update.ps1 -InstallRoot E:\shortsflow -CheckOnly

## License and attribution

Upstream: <https://github.com/ghost1412/shortsflow>.
Copied/modified upstream source is MIT licensed; see LICENSE and NOTICE.txt.
This repository is not the upstream ShortsFlow project.

