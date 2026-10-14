"""Low-I/O audio tagging and file-based FFmpeg progress for the worker."""
import io
import threading
import time
from pathlib import Path
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import PostProcessingError


class FastMP3TagsPP(PostProcessor):
    def run(self, info):
        from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TDRC, TRCK, APIC
        from mutagen import MutagenError
        from PIL import Image
        path = info['filepath']
        try:
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()
            fields = [('TIT2', TIT2, info.get('track') or info.get('title')),
                      ('TPE1', TPE1, info.get('artist') or info.get('uploader')),
                      ('TALB', TALB, info.get('album')),
                      ('TDRC', TDRC, info.get('release_date') or info.get('upload_date')),
                      ('TRCK', TRCK, info.get('track_number'))]
            for key, frame, value in fields:
                if value is not None:
                    if key == 'TDRC' and len(str(value)) == 8 and str(value).isdigit():
                        value = f'{str(value)[:4]}-{str(value)[4:6]}-{str(value)[6:8]}'
                    tags.delall(key)
                    tags.add(frame(encoding=1, text=str(value)))
            thumbnails = [Path(t['filepath']) for t in info.get('thumbnails') or []
                          if t.get('filepath') and Path(t['filepath']).is_file()]
            if thumbnails:
                with Image.open(thumbnails[-1]) as image:
                    image = image.convert('RGB')
                    image.thumbnail((600, 600), Image.Resampling.LANCZOS)
                    cover = io.BytesIO()
                    image.save(cover, format='JPEG', quality=90)
                tags.delall('APIC')
                tags.add(APIC(encoding=0, mime='image/jpeg', type=3, desc='Album cover', data=cover.getvalue()))
            tags.save(path, v2_version=3)
            self.to_screen('MP3 title, artist and JPEG front cover saved without another FFmpeg pass')
            return [str(t) for t in thumbnails], info
        except (OSError, ValueError, MutagenError) as error:
            raise PostProcessingError(f'MP3 tags/cover could not be saved: {error}') from error


class ProcessingProgress:
    def __init__(self, path, emit):
        self.path, self.emit = Path(path), emit
        self.stop = threading.Event()
        self.thread = None

    def hook(self, event):
        name = event.get('postprocessor', '')
        if event['status'] == 'started':
            self.close()
            self.path.write_text('', encoding='utf-8')
            self.stop.clear()
            duration = event.get('info_dict', {}).get('duration') or 0
            started = time.monotonic()
            phase = 'cover' if name in ('FastMP3Tags', 'ThumbnailsConvertor', 'EmbedThumbnail') else 'processing'
            self.emit('processing', phase=phase, percent=None, elapsed=0, processor=name)
            def monitor():
                offset, buffer, values = 0, '', {}
                while not self.stop.wait(.5):
                    try:
                        if self.path.stat().st_size < offset:
                            offset, buffer, values = 0, '', {}
                        with self.path.open(encoding='utf-8') as handle:
                            handle.seek(offset)
                            buffer += handle.read()
                            offset = handle.tell()
                        lines = buffer.split('\n')
                        buffer = lines.pop()
                        values.update(line.split('=', 1) for line in lines if '=' in line)
                        timestamp = int(values.get('out_time_us', 0)) / 1_000_000
                        percent = min(99, max(0, timestamp / duration * 100)) if duration and values and phase != 'cover' else None
                        self.emit('processing', phase=phase, percent=percent, elapsed=time.monotonic() - started, processor=name)
                    except (OSError, ValueError):
                        pass
            self.thread = threading.Thread(target=monitor, daemon=True)
            self.thread.start()
        elif event['status'] == 'finished':
            self.close()
            self.emit('processing', phase='cover' if name == 'FastMP3Tags' else 'processing', percent=100, elapsed=0, processor=name)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
