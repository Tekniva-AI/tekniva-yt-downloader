"""Discover and install a checksum-pinned, app-local JavaScript runtime."""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

NODE_VERSION = '22.23.3'
NODE_ARCHIVE = f'node-v{NODE_VERSION}-win-x64.zip'
NODE_URL = f'https://nodejs.org/dist/v{NODE_VERSION}/{NODE_ARCHIVE}'
NODE_SHA256 = '2b0ff57b049cda1bbcea2240eec20467018713c1efe1f7360c2681859b90ed71'
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


class InstallCancelled(Exception):
    pass


def usable_node(path):
    if not path:
        return False
    try:
        result = subprocess.run([str(path), '--version'], capture_output=True, text=True,
                                creationflags=NO_WINDOW, timeout=8, stdin=subprocess.DEVNULL)
        match = re.fullmatch(r'v(\d+)\.\d+\.\d+', result.stdout.strip())
        return result.returncode == 0 and bool(match) and int(match[1]) >= 22
    except (OSError, subprocess.SubprocessError):
        return False


def local_node(app_dir):
    return Path(app_dir) / 'tools' / f'node-v{NODE_VERSION}' / 'node.exe'


def node_path(app_dir):
    candidates = (local_node(app_dir), shutil.which('node'))
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and usable_node(candidate):
            return str(Path(candidate).resolve())
    return None


def node_runtime_options(app_dir):
    path = node_path(app_dir)
    return {'node': {'path': path} if path else {}}


def install_node(app_dir, progress=lambda phase, percent: None, cancel=None):
    """Only call after GUI consent or the explicit --install-node command."""
    def checkpoint():
        if cancel is not None and cancel.is_set():
            raise InstallCancelled()

    checkpoint()
    tools = Path(app_dir) / 'tools'
    tools.mkdir(parents=True, exist_ok=True)
    # Staging stays in the app directory. Neither media nor system folders change.
    with tempfile.TemporaryDirectory(prefix='.node-install-', dir=tools) as temporary:
        staging = Path(temporary)
        archive_path = staging / NODE_ARCHIVE
        request = urllib.request.Request(NODE_URL, headers={'User-Agent': 'Tekniva-YT-Downloader'})
        digest, downloaded, last_percent = hashlib.sha256(), 0, -1
        progress('download', 0)
        with urllib.request.urlopen(request, timeout=25) as response, archive_path.open('wb') as target:
            total = int(response.headers.get('Content-Length', 0))
            if total > 80 * 1024**2:
                raise ValueError('Unexpected Node.js archive size')
            while True:
                checkpoint()
                chunk = response.read1(256 * 1024)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > 80 * 1024**2:
                    raise ValueError('Unexpected Node.js archive size')
                target.write(chunk)
                digest.update(chunk)
                percent = min(99, int(downloaded * 100 / total)) if total else 0
                if percent != last_percent:
                    progress('download', percent)
                    last_percent = percent
        checkpoint()
        progress('verify', 100)
        if digest.hexdigest() != NODE_SHA256:
            raise ValueError('Node.js SHA-256 verification failed')
        # Extract exactly two fixed members; npm and installer scripts are unnecessary.
        prefix = f'node-v{NODE_VERSION}-win-x64/'
        with zipfile.ZipFile(archive_path) as archive:
            for name in ('node.exe', 'LICENSE'):
                checkpoint()
                member = archive.getinfo(prefix + name)
                if member.file_size > 150 * 1024**2:
                    raise ValueError('Unexpected Node.js member size')
                with archive.open(member) as source, (staging / name).open('wb') as target:
                    while chunk := source.read(256 * 1024):
                        checkpoint()
                        target.write(chunk)
        checkpoint()
        if not usable_node(staging / 'node.exe'):
            raise ValueError('Downloaded Node.js runtime could not start')
        checkpoint()
        destination = local_node(app_dir).parent
        destination.mkdir(exist_ok=True)
        os.replace(staging / 'LICENSE', destination / 'LICENSE')
        os.replace(staging / 'node.exe', destination / 'node.exe')
    return str(local_node(app_dir).resolve())
