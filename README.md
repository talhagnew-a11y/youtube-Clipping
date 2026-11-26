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


## Project publishing layout and rollback (2026.11.26.4)

The Publish screen now groups videos by project. Select a project, then edit
each video's title, description and tags beside its preview. Each card has
its own Preview upload, Publish now and Schedule buttons and upload status.
Choose platforms, channel and visibility once above the cards. Processing
segments are excluded. The upload queue stays below the cards.

To return to the code before the last update: let active jobs finish, close
ShortsFlow with STOP-SHORTSFLOW.cmd, then run ROLLBACK-SHORTSFLOW.cmd in the
installed folder. It restores the newest code backup and restarts the app.
Models, videos, login and saved schedules are preserved. This restores code;
it cannot undo videos already uploaded to YouTube. Avoid clicking rollback
repeatedly: each restore also saves the version it replaces.

## Full video / Creative Commons and shared hashtag research (2026.11.27.1)

Select **Full video / Creative Commons** for a complete video of up to 15 minutes.
Choose a downloaded local file, title and description. For a CC source, enter
its original creator, source URL and actual license URL. Confirm your intended
editing/upload is permitted. Attribution is saved in the upload description.
Keep start at 0 and end blank to preserve the whole video. Automatic subtitles
use local Whisper; alternatively select an SRT file with the source timings.
Sentence and word captions are supported. Timed explanation notes use
`00:30 | 00:45 | My useful explanation` (times in the edited output).
Optional trim, speed, sound volume/mute, logo and label are available.
Try **Make 15-second preview**, then **Export full video**. **Open Publish page**
selects the latest project so you can upload or schedule it through the normal
YouTube connection. No upload is triggered just by exporting the full video.
Basic re-encoding/subtitles/branding do not guarantee monetization eligibility.

The **Keyword hashtags — for shorts and full videos** box is shared across
screens. Research a topic (for example Minecraft gameplay or GTA 6), review
and edit the chosen tags. Public YouTube search suggestions and matching Google
Trends RSS topics are labeled separately; there is no claimed YouTube hashtag
ranking or search volume. With no network response only the base keyword is
suggested and the source failure is shown. Only the keyword goes online.
Chosen tags are saved before new Shorts auto-upload, including plan-first and
continued runs. Existing short review cards and all Publish video cards have
an apply button. Full-video exports have their own **Use chosen keyword hashtags**
button. Applied tags persist in local metadata and appear in descriptions on
future uploads. They do not edit videos that were already uploaded to YouTube.

The update remains lightweight. Existing models and YouTube sign-in are reused.
Rollback is available with ROLLBACK-SHORTSFLOW.cmd after closing the app.

## OPTIONAL improvements: separate install/update/rollback folder

The normal full-video/hashtag update is still **2026.11.27.1**. Its payload and
update-manifest are unchanged by the optional improvements. Running the normal
updater never enables these tests.

When ready, download/extract a fresh repository ZIP. First install the normal
update using root **INSTALL-UPDATE.cmd** if it has not been installed yet.
Then, only when you want to test, open **improvements/INSTALL-IMPROVEMENTS.cmd**
and select the existing ShortsFlow folder. Let active jobs finish and stop the
app first. Installation does not start test mode automatically.

The installed **shortsflow/improvements/** folder contains:

- **RUN-IMPROVEMENTS.cmd**: launch the optional test mode.
- **STOP-IMPROVEMENTS.cmd**: stop that mode after jobs finish.
- **UPDATE-IMPROVEMENTS.cmd**: update only the optional package from this repo.
- **ROLLBACK-IMPROVEMENTS.cmd**: restore the previous optional code version, or
  disable the first installation. Stable base files are never overwritten.

Normal **RUN-SHORTSFLOW.cmd** always uses stable mode. Do not run both modes on
port 7875 simultaneously. Runtime integration, state and code backups live in
the separate improvements folder. Installation checks the exact tested base.

Optional tools are at the bottom of the test dashboard: automatic upload queue
pause/resume, per-slot upload-limit cooldown, same-session resumable retries,
manual retry after checking Studio; cached subtitle correction to a new export;
bounded sentence-boundary adjustment for new Shorts; local Ollama explanation
drafts that require review. See improvements/HELP.txt for the workflow and limits.
Rollback restores code, not already uploaded videos or intentional saved edits.
Normal mode does not enforce the optional queue cooldowns.
On the first optional installation, its automatic upload queue starts PAUSED. Resume it in the optional dashboard only when ready to upload saved jobs.
