# Third-party notices

Tekniva YT Downloader source: Copyright © 2026 Tekniva, GPL-3.0-or-later. Bundled components retain their own licenses. These unmodified components are used to download, tag and process media; no ownership of their work is claimed.

| Component | Packaged version | License | Upstream / source |
|---|---|---|---|
| Python | Build host 3.13 | PSF and included notices | https://www.python.org/downloads/source/ |
| Tcl/Tk | Python Windows runtime | Tcl/Tk BSD-style terms | https://www.tcl-lang.org/software/tcltk/download.html |
| yt-dlp | 2026.8.19 | Unlicense | https://github.com/yt-dlp/yt-dlp/tree/2026.08.19 |
| yt-dlp-ejs | 0.8.0 | Unlicense, MIT, ISC | https://github.com/yt-dlp/ejs/tree/0.8.0 |
| imageio-ffmpeg Python wrapper | 0.6.0 | BSD-2-Clause | https://github.com/imageio/imageio-ffmpeg/tree/v0.6.0 |
| FFmpeg executable | 7.1 essentials, gyan.dev | GPL-3.0-or-later (GPL/version3 build) | https://www.gyan.dev/ffmpeg/builds/ ; https://github.com/FFmpeg/FFmpeg/tree/n7.1 |
| aria2 executable | 1.37.0 win-64bit-build1 | GPL-2.0-or-later; included OpenSSL notices | https://github.com/aria2/aria2/releases/tag/release-1.37.0 |
| Mutagen | 1.48.1 | GPL-2.0-or-later | https://github.com/quodlibet/mutagen |
| PyInstaller bootloader | 6.22.3 | GPL-2.0-or-later with bootloader exception | https://github.com/pyinstaller/pyinstaller |

Runtime license texts are supplied in `licenses/`. The full GPLv3 text is also in the top-level `LICENSE`. Python package notices can be reproduced from the pinned distributions using `program/collect_licenses.py`. Development dependencies (including Pillow) are specified in `requirements-dev.txt`; they retain their respective licenses.

## Binary provenance and source access

- aria2 Windows binary is taken directly from [this official ZIP](https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip). Its SHA-256 is `67d015301eef0b612191212d564c5bb0a14b5b9c4796b76454276a4d28d9b288`. The corresponding [aria2 1.37.0 source archive](https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0.tar.xz) and Windows build instructions are available upstream. `licenses/aria2-*` are copied unchanged from the binary ZIP.
- FFmpeg comes unchanged from the imageio-ffmpeg 0.6.0 Windows wheel: `ffmpeg-win-x86_64-v7.1.exe`, identifying itself as `7.1-essentials_build-www.gyan.dev`. The original build provider documents the GPLv3 license and enabled libraries at [gyan.dev](https://www.gyan.dev/ffmpeg/builds/). FFmpeg's matching core source is [n7.1](https://github.com/FFmpeg/FFmpeg/archive/refs/tags/n7.1.tar.gz). Build configuration is recorded in `licenses/FFmpeg-build.txt`; upstream codec/library projects and their licenses remain applicable. FFmpeg is invoked as a separate executable.
- Source distributions of the pinned Python dependencies can be downloaded with `python -m pip download --no-binary=:all: -r requirements.txt`. Their metadata contains the upstream copyright/license notices; these are copied without modification into `licenses/`.
- Node.js is a user-installed prerequisite, not bundled in this release. See https://github.com/nodejs/node/blob/main/LICENSE for its license.

## Branding

The application footer includes a simple camera-outline link to Tekniva's Instagram profile. Instagram and YouTube are trademarks of their respective owners. The project is independent and is not endorsed by Instagram, Google or YouTube.
