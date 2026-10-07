"""Build a versioned release; --rebuild retains the current release number."""
import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
from collect_licenses import collect
collect()
parser = argparse.ArgumentParser()
parser.add_argument('--rebuild', action='store_true', help='Repackage the current release without incrementing it')
args = parser.parse_args()
catalog = root / 'translations.py'
source = catalog.read_text(encoding='utf-8')
match = re.search(r"^VERSION = (.+)$", source, re.M)
version = ast.literal_eval(match[1])
numbers = [int(n) for n in re.search(r'(\d+)\.(\d+)\.(\d+)', version).groups()]
if not args.rebuild:
    numbers[2] += 1
    version = 'beta ' + '.'.join(map(str, numbers))
    source = source[:match.start()] + 'VERSION = ' + repr(version) + source[match.end():]
    catalog.write_text(source, encoding='utf-8')
number = '.'.join(map(str, numbers))
version_file = root / 'version_info.txt'
info = version_file.read_text(encoding='utf-8')
info = re.sub(r'filevers=\([^)]*\)', 'filevers=' + repr(tuple(numbers + [0])), info)
info = re.sub(r'prodvers=\([^)]*\)', 'prodvers=' + repr(tuple(numbers + [0])), info)
info = re.sub(r"StringStruct\('FileVersion', '[^']*'\)", f"StringStruct('FileVersion', '{number} beta')", info)
info = re.sub(r"StringStruct\('ProductVersion', '[^']*'\)", f"StringStruct('ProductVersion', '{version}')", info)
version_file.write_text(info, encoding='utf-8')
manual = root / 'KULLANIM.txt'
text = manual.read_text(encoding='utf-8')
manual.write_text('TEKNIVA YT DOWNLOADER — ' + version + '\n' + text.split('\n', 1)[1], encoding='utf-8')
command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed', '--name', 'Tekniva YT Downloader',
           '--distpath', str(root), '--workpath', str(root / 'build'), '--specpath', str(root),
           '--version-file', str(version_file), '--icon', str(root / 'app.ico'), '--add-data', str(root / 'app.ico') + ';.',
           '--add-data', str(root.parent / 'licenses') + ';licenses',
           '--add-data', str(root.parent / 'LICENSE') + ';licenses',
           '--add-data', str(root.parent / 'THIRD_PARTY_NOTICES.md') + ';licenses',
           '--add-binary', str(root / 'tools' / 'aria2c.exe') + ';tools', '--collect-all', 'yt_dlp',
           '--collect-all', 'yt_dlp_ejs', '--collect-all', 'imageio_ffmpeg', str(root / 'kanal_indirici.py')]
with (root / ('paketleme-' + number + '.log')).open('w', encoding='utf-8') as log:
    subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
print('Built Tekniva YT Downloader ' + version)
