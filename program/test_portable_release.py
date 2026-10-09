"""Opt-in release check: real Node download in isolated EXE and ZIP directories."""
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from translations import VERSION


def verify():
    number = VERSION.removeprefix('beta ')
    release = Path(__file__).resolve().parent.parent / 'release' / number
    stem = f'Tekniva-YT-Downloader-{number}-Windows-x64'
    environment = dict(os.environ)
    environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
    with tempfile.TemporaryDirectory(prefix='tekniva-portable-') as directory:
        root = Path(directory)
        standalone = root / 'Standalone EXE'
        standalone.mkdir()
        import shutil
        executable = standalone / (stem + '.exe')
        shutil.copy2(release / executable.name, executable)
        zip_root = root / 'ZIP distribution'
        with zipfile.ZipFile(release / (stem + '.zip')) as archive:
            archive.extractall(zip_root)
        zipped = zip_root / stem / 'Tekniva YT Downloader.exe'
        for label, app in (('EXE', executable), ('ZIP', zipped)):
            report = app.parent / 'check.json'
            def run(*arguments):
                subprocess.run([str(app), *map(str, arguments)], check=True, timeout=240, env=environment,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            run('--check', report)
            assert not json.loads(report.read_text())['node'], 'Test environment unexpectedly provides Node.js'
            run('--install-node', report)
            installed = json.loads(report.read_text())
            assert installed['ok'], installed
            node = Path(installed['node_path'])
            assert node.is_relative_to(app.parent) and node.is_file()
            assert (node.parent / 'LICENSE').is_file()
            run('--check', report)
            dependencies = json.loads(report.read_text())
            assert dependencies['node'] and dependencies['ffmpeg'] and dependencies['aria2'], dependencies
            run('--gui-smoke')
            print(label + ': no system Node, official download, local runtime, FFmpeg/aria2 and GUI verified.', flush=True)


if __name__ == '__main__':
    verify()
