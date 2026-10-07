"""Create release assets using an explicit allowlist, never local app data."""
import hashlib
import shutil
import zipfile
from pathlib import Path
from translations import VERSION

ROOT = Path(__file__).resolve().parent.parent


def package():
    number = VERSION.removeprefix('beta ')
    destination = ROOT / 'release' / number
    destination.mkdir(parents=True, exist_ok=True)
    stem = f'Tekniva-YT-Downloader-{number}-Windows-x64'
    executable = ROOT / 'program' / 'Tekniva YT Downloader.exe'
    if not executable.is_file():
        raise FileNotFoundError('Build the executable first with build_release.py')
    standalone = destination / (stem + '.exe')
    shutil.copy2(executable, standalone)
    files = {'Tekniva YT Downloader.exe': executable,
             'KULLANIM.txt': ROOT / 'program' / 'KULLANIM.txt',
             'README.md': ROOT / 'README.md', 'LICENSE': ROOT / 'LICENSE',
             'THIRD_PARTY_NOTICES.md': ROOT / 'THIRD_PARTY_NOTICES.md',
             'CHANGELOG.md': ROOT / 'CHANGELOG.md'}
    for license_file in sorted((ROOT / 'licenses').rglob('*')):
        if license_file.is_file():
            files[license_file.relative_to(ROOT).as_posix()] = license_file
    for screenshot in sorted((ROOT / 'docs' / 'images').glob('*.png')):
        files[screenshot.relative_to(ROOT).as_posix()] = screenshot
    archive = destination / (stem + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for name, path in files.items():
            bundle.write(path, stem + '/' + name)
    checksums = destination / 'SHA256SUMS.txt'
    checksums.write_text(''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n'
                                for path in (archive, standalone)), encoding='utf-8')
    print(f'Clean release assets: {destination}')


if __name__ == '__main__':
    package()
