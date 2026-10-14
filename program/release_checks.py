"""Packaged end-to-end media checks using only generated local fixtures."""
import functools
import http.server
import json
import subprocess
import tempfile
import threading
import time
from pathlib import Path


def verify_media(report_path):
    import yt_dlp
    from PIL import Image
    from mutagen.id3 import ID3
    from kanal_indirici import APP_DIR, NO_WINDOW, make_options, download_with_recovery
    from dependencies import ffmpeg_path
    from media_processing import FastMP3TagsPP, ProcessingProgress
    from transfer import create_downloader
    state = APP_DIR / 'veri'
    state.mkdir(exist_ok=True)
    results = []
    class Logger:
        def __init__(self): self.messages = []
        def debug(self, message): self.messages.append(message)
        def warning(self, message): self.messages.append(message)
        def error(self, message): self.messages.append(message)
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    try:
        with tempfile.TemporaryDirectory(prefix='media-check-', dir=state) as directory:
            root = Path(directory)
            source = root / 'fixture.mp4'
            subprocess.run([ffmpeg_path(), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=25',
                            '-f', 'lavfi', '-i', 'sine=frequency=440', '-t', '1.4', '-c:v', 'libx264', '-c:a', 'aac', str(source)],
                           check=True, capture_output=True, creationflags=NO_WINDOW)
            Image.new('RGB', (1280, 720), '#2563EB').save(root / 'cover.png')
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=directory))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/fixture.mp4'
                for label, fmt in [('curl_cffi MP4', 'MP4'), ('aria2 MP4', 'MP4'), ('MP3', 'MP3'), ('Baseline MP3', 'MP3')]:
                    output = root / label
                    output.mkdir()
                    logger = Logger()
                    job = {'format': fmt, 'quality': '320 kbps' if fmt == 'MP3' else 'En yüksek',
                           'engine': 'aria2' if label == 'aria2 MP4' else 'curl_cffi',
                           'speed': 'Hızlı (8 bağlantı)' if label == 'aria2 MP4' else 'Otomatik (önerilen)'}
                    events = []
                    monitor = ProcessingProgress(state / 'check-progress.txt', lambda kind, **data: events.append(data))
                    options = make_options(job, output, logger, {'progress': lambda event: None, 'postprocess': monitor.hook})
                    options['verbose'] = True
                    options['outtmpl'] = {'default': str(output / 'Fixture.%(ext)s'), 'thumbnail': str(state / 'check-cover.%(ext)s')}
                    info = {'id': label, 'title': 'Fixture', 'artist': 'Test Artist', 'duration': 1.4, 'webpage_url': url,
                            'extractor_key': 'Generic', 'url': url, 'ext': 'mp4', 'vcodec': 'h264', 'acodec': 'aac',
                            'thumbnails': [{'url': f'http://127.0.0.1:{server.server_port}/cover.png', 'id': 'cover'}]}
                    started = time.monotonic()
                    try:
                        if label == 'aria2 MP4':
                            download_with_recovery(url, options, lambda *args, **kwargs: None)
                        else:
                            if label == 'Baseline MP3':
                                options['postprocessors'] = [
                                    {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg', 'when': 'before_dl'},
                                    *options['postprocessors'],
                                    {'key': 'FFmpegMetadata', 'add_metadata': True, 'add_chapters': False, 'add_infojson': False},
                                    {'key': 'EmbedThumbnail', 'already_have_thumbnail': False}]
                            with create_downloader(options) as ydl:
                                if label == 'MP3':
                                    ydl.add_post_processor(FastMP3TagsPP(ydl))
                                ydl.process_ie_result(info, download=True)
                    finally:
                        monitor.close()
                    files = list(output.glob('*.' + fmt.lower()))
                    assert len(files) == 1, (label, [p.name for p in output.iterdir()])
                    probe = subprocess.run([ffmpeg_path(), '-v', 'error', '-i', str(files[0]), '-map', '0', '-c', 'copy', '-f', 'null', '-'],
                                           capture_output=True, creationflags=NO_WINDOW)
                    assert probe.returncode == 0, probe.stderr.decode(errors='replace')
                    if fmt == 'MP3':
                        tags = ID3(files[0])
                        assert tags.version == (2, 3, 0) and tags.getall('APIC')[0].mime == 'image/jpeg'
                        assert str(tags['TPE1']) == 'Test Artist'
                    assert not list(output.glob('*.json')) + list(output.glob('*.txt')) + list(output.glob('*.png')) + list(output.glob('*.jpg'))
                    passes = sum('ffmpeg command line:' in message and '.mp3' in message for message in logger.messages)
                    results.append({'case': label, 'engine': job['engine'], 'seconds': round(time.monotonic() - started, 3), 'mp3_ffmpeg_passes': passes,
                                    'retries': [m for m in logger.messages if 'Fresh URL retry' in m]})
                optimized = next(item for item in results if item['case'] == 'MP3')
                baseline = next(item for item in results if item['case'] == 'Baseline MP3')
                assert optimized['mp3_ffmpeg_passes'] == 1, results
                assert baseline['mp3_ffmpeg_passes'] >= 3, results
                report = {'ok': True, 'cases': results}
            finally:
                server.shutdown()
                server.server_close()
    except Exception as error:
        report = {'ok': False, 'error': str(error), 'cases': results}
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report['ok']
