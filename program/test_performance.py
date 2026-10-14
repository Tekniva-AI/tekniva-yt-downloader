"""Behavioral checks for fewer media passes, recovery and actual FFmpeg progress."""
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yt_dlp
from dependencies import ffmpeg_path
from kanal_indirici import download_with_recovery, make_options, error_code, run_gui
from media_processing import FastMP3TagsPP, ProcessingProgress


class Log:
    def debug(self, message): pass
    def warning(self, message): pass
    def error(self, message): pass


class PerformanceTests(unittest.TestCase):
    def test_mp3_tagging_preserves_encoded_audio_and_car_cover(self):
        from PIL import Image
        from mutagen.id3 import ID3
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'song.mp3'
            subprocess.run([ffmpeg_path(), '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440',
                            '-t', '0.25', '-c:a', 'libmp3lame', '-b:a', '320k', str(path)], check=True, capture_output=True)
            before = hashlib.sha256(path.read_bytes()[ID3(path).size:]).hexdigest()
            cover = root / 'cover.webp'
            Image.new('RGB', (1600, 900), '#2563EB').save(cover)
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                processor = FastMP3TagsPP(ydl)
                deleted, _ = processor.run({'filepath': str(path), 'ext': 'mp3', 'title': 'Şarkı', 'artist': 'Sanatçı',
                                           'album': 'Album', 'upload_date': '20261014', 'thumbnails': [{'filepath': str(cover)}]})
            tags = ID3(path)
            self.assertEqual(tags.version, (2, 3, 0))
            self.assertEqual(str(tags['TPE1']), 'Sanatçı')
            picture = tags.getall('APIC')[0]
            self.assertEqual((picture.mime, picture.type), ('image/jpeg', 3))
            import io
            with Image.open(io.BytesIO(picture.data)) as image:
                self.assertLessEqual(max(image.size), 600)
            self.assertEqual(before, hashlib.sha256(path.read_bytes()[tags.size:]).hexdigest())
            self.assertEqual(deleted, [str(cover)])

    def test_fast_transfer_failure_switches_to_native_without_quality_loss(self):
        attempts = []
        class Downloader:
            def __init__(self, options):
                attempts.append(options)
                self.number = len(attempts)
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, *args, **kwargs): return {'height': 2160, 'fps': 60}
            def process_ie_result(self, info, download):
                if self.number == 1:
                    raise yt_dlp.utils.DownloadError('aria2c exited with code 1')
                return info
        with patch('kanal_indirici.create_downloader', Downloader), patch('kanal_indirici.aria2_path', return_value='aria2c'):
            result = download_with_recovery('https://youtube.com/watch?v=sample',
                       {'logger': Log(), 'tekniva_transfer': 'Hızlı (8 bağlantı)', 'tekniva_engine': 'aria2', 'concurrent_fragment_downloads': 8},
                       lambda *args, **kwargs: None, sleep=lambda seconds: None)
        self.assertIn('external_downloader', attempts[0])
        self.assertNotIn('external_downloader', attempts[1])
        self.assertEqual(result['height'], 2160)

    def test_real_ffmpeg_processing_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = []
            monitor = ProcessingProgress(root / 'progress.txt', lambda kind, **data: events.append(data))
            monitor.hook({'status': 'started', 'postprocessor': 'ExtractAudio', 'info_dict': {'duration': 1.4}})
            try:
                subprocess.run([ffmpeg_path(), '-v', 'error', '-re', '-f', 'lavfi', '-i', 'sine=frequency=440',
                                '-t', '1.4', '-progress', str(root / 'progress.txt'), '-stats_period', '0.1',
                                str(root / 'audio.mp3')], check=True, capture_output=True)
                monitor.hook({'status': 'finished', 'postprocessor': 'ExtractAudio'})
            finally:
                monitor.close()
            self.assertTrue(any(e['percent'] is not None and 0 < e['percent'] < 100 for e in events), events)
            self.assertEqual(events[-1]['percent'], 100)

    def test_gui_reports_processing_and_preserves_actionable_error(self):
        def verify(app):
            app.handle({'kind': 'list', 'folder': 'test', 'channel': 'Test', 'entries': [{'id': 'sample00001', 'title': 'Test'}]})
            app.current_id = 'sample00001'
            app.action = 'download'
            app.handle({'kind': 'processing', 'phase': 'processing', 'percent': 71, 'elapsed': 4})
            self.assertIn('71', app.table.set('sample00001', 'state'))
            app.handle({'kind': 'item', 'id': 'sample00001', 'state': 'Hata', 'error': '403', 'error_code': 'access'})
            app.handle({'kind': 'done', 'failed': 1})
            self.assertIn('YouTube', app.detail.get())
            self.assertIn('1', app.status.get())
        run_gui(test_callback=verify)

    def test_default_has_no_per_stream_pause_or_external_tool_requirement(self):
        with tempfile.TemporaryDirectory() as directory:
            import kanal_indirici
            with patch.object(kanal_indirici, 'APP_DIR', Path(directory)):
                options = make_options({'format': 'MP3', 'quality': '320 kbps'}, Path(directory), Log(),
                                       {'progress': lambda event: None, 'postprocess': lambda event: None})
            self.assertEqual(options['sleep_interval'], 0)
            self.assertNotIn('external_downloader', options)
            self.assertEqual(len(options['postprocessors']), 1)
            self.assertEqual(error_code('HTTP 429'), 'rate_limit')
            self.assertEqual(error_code('CERTIFICATE_VERIFY_FAILED'), 'tls')
