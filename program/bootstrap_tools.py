"""Fetch the official, checksum-pinned aria2 Windows build for development."""
import hashlib
import io
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL = 'https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip'
SHA256 = '67d015301eef0b612191212d564c5bb0a14b5b9c4796b76454276a4d28d9b288'


def prepare():
    request = urllib.request.Request(URL, headers={'User-Agent': 'Tekniva-YT-Downloader'})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise RuntimeError('aria2 checksum mismatch; refusing to install')
    tools = ROOT / 'tools'
    tools.mkdir(exist_ok=True)
    licenses = ROOT.parent / 'licenses'
    licenses.mkdir(exist_ok=True)
    names = {'aria2c.exe': tools / 'aria2c.exe', 'COPYING': licenses / 'aria2-GPL-2.0.txt',
             'LICENSE.OpenSSL': licenses / 'aria2-OpenSSL.txt', 'AUTHORS': licenses / 'aria2-AUTHORS.txt'}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name, target in names.items():
            member = next(item for item in archive.infolist() if Path(item.filename).name == name)
            with archive.open(member) as source, target.open('wb') as destination:
                shutil.copyfileobj(source, destination)
    print('Verified aria2 1.37.0 Windows x64 and installed its licenses.')


if __name__ == '__main__':
    prepare()
