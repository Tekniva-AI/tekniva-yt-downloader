"""Copy installed dependency license texts into the redistribution directory."""
import importlib.metadata
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ('yt-dlp', 'yt-dlp-ejs', 'imageio-ffmpeg', 'mutagen', 'pyinstaller',
            'altgraph', 'packaging', 'pefile', 'pywin32-ctypes', 'setuptools',
            'pyinstaller-hooks-contrib', 'Pillow')


def collect():
    target = ROOT / 'licenses'
    target.mkdir(exist_ok=True)
    for name in PACKAGES:
        distribution = importlib.metadata.distribution(name)
        for item in distribution.files or ():
            path = Path(item)
            if ('license' in path.name.lower() or path.name.lower().startswith(('copying', 'notice'))):
                source = Path(distribution.locate_file(item))
                if source.is_file():
                    destination = target / name / path.name
                    destination.parent.mkdir(exist_ok=True)
                    shutil.copy2(source, destination)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.is_file():
        shutil.copy2(python_license, target / 'Python-LICENSE.txt')
    for name in ('tcl8.6', 'tk8.6'):
        tcl_license = Path(sys.base_prefix) / 'tcl' / name / 'license.terms'
        if tcl_license.is_file():
            shutil.copy2(tcl_license, target / (name + '-license.terms'))
    import imageio_ffmpeg
    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-version'], capture_output=True, text=True, check=True)
    (target / 'FFmpeg-build.txt').write_text(result.stdout, encoding='utf-8')
    print('Collected dependency license texts.')


if __name__ == '__main__':
    collect()
