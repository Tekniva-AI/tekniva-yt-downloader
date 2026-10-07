import functools
import http.server
import json
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path

import imageio_ffmpeg
import yt_dlp
from kanal_indirici import make_options, normalize_channel, normalize_source, get_entries, run_worker, run_gui, reserve_title, download_with_recovery, metadata_paths, output_folder, aria2_path


class SilentLog:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    reject_once = True
    def log_message(self, *args): pass
    def do_GET(self):
        if '?reject-once' in self.path and type(self).reject_once:
            type(self).reject_once = False
            self.send_error(403)
            return
        super().do_GET()


class ProgramTests(unittest.TestCase):
    def setUp(self):
        self.app_temp = tempfile.TemporaryDirectory()
        self.aria_patch = patch('kanal_indirici.aria2_path', return_value=aria2_path())
        self.aria_patch.start()
        self.app_patch = patch('kanal_indirici.APP_DIR', Path(self.app_temp.name))
        self.app_patch.start()

    def tearDown(self):
        self.app_patch.stop()
        self.aria_patch.stop()
        self.app_temp.cleanup()

    def test_refresh_and_hls_retry_preserves_quality(self):
        attempts, delays = [], []
        class Downloader:
            def __init__(self, options):
                attempts.append(options)
                self.attempt = len(attempts)
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, url, download):
                self.assert_download = download
                return {'id': 'sample', 'height': 2160, 'fps': 60}
            def process_ie_result(self, info, download):
                if self.attempt < 3:
                    raise yt_dlp.utils.DownloadError('HTTP Error 403: Forbidden')
                return info
        with patch.object(yt_dlp, 'YoutubeDL', Downloader):
            result = download_with_recovery('https://youtube.com/watch?v=sample', {'logger': SilentLog()}, lambda *args, **kwargs: None, sleep=delays.append)
        self.assertEqual(result['height'], 2160)
        self.assertEqual(delays, [5, 10])
        self.assertIn('proto:m3u8_native', attempts[-1]['format_sort'])

    def test_permanent_errors_are_not_retried(self):
        with patch.object(yt_dlp, 'YoutubeDL') as mocked:
            mocked.return_value.__enter__.return_value.extract_info.side_effect = yt_dlp.utils.DownloadError('This video is private')
            with self.assertRaises(yt_dlp.utils.DownloadError):
                download_with_recovery('https://youtube.com/watch?v=sample', {'logger': SilentLog()}, lambda *args, **kwargs: None, sleep=lambda n: self.fail('Unexpected retry'))
            self.assertEqual(mocked.call_count, 1)

    def test_recovery_does_not_reduce_resolution(self):
        with patch.object(yt_dlp, 'YoutubeDL') as mocked:
            downloader = mocked.return_value.__enter__.return_value
            downloader.extract_info.side_effect = [{'height': 2160, 'fps': 60}, {'height': 1080, 'fps': 60}]
            downloader.process_ie_result.side_effect = yt_dlp.utils.DownloadError('HTTP Error 403: Forbidden')
            with self.assertRaisesRegex(yt_dlp.utils.DownloadError, 'Kalite düşürülmedi'):
                download_with_recovery('https://youtube.com/watch?v=sample', {'logger': SilentLog()}, lambda *args, **kwargs: None, sleep=lambda n: None)
            self.assertEqual(downloader.process_ie_result.call_count, 1)

    def test_music_sources(self):
        self.assertEqual(normalize_source('https://music.youtube.com/watch?v=SyQi3gH-Ol4&list=RDabc'),
                         ('video', 'https://music.youtube.com/watch?v=SyQi3gH-Ol4'))
        self.assertEqual(normalize_source('https://music.youtube.com/playlist?list=OLAK5uy_test&si=abc'),
                         ('playlist', 'https://music.youtube.com/playlist?list=OLAK5uy_test'))
        self.assertEqual(normalize_source('https://music.youtube.com/browse/MPREb_gTAcphH99wE'),
                         ('playlist', 'https://music.youtube.com/browse/MPREb_gTAcphH99wE'))
        self.assertEqual(normalize_source('https://music.youtube.com/browse/VLPLexample'),
                         ('playlist', 'https://music.youtube.com/playlist?list=PLexample'))
        self.assertEqual(normalize_source('https://music.youtube.com/channel/UCexample')[0], 'channel')
        with self.assertRaises(ValueError):
            normalize_source('https://music.youtube.com/playlist?list=')
        with patch.object(yt_dlp, 'YoutubeDL') as mocked:
            mocked.return_value.__enter__.return_value.extract_info.return_value = {
                'title': 'Album', 'entries': [{'id': 'SyQi3gH-Ol4', 'title': 'Track'}]}
            entries, title, _ = get_entries({'url': 'https://music.youtube.com/playlist?list=OLAK5uy_test',
                                             'action': 'list', 'all_tabs': True}, SilentLog())
            self.assertEqual(len(entries), 1)
            self.assertEqual(title, 'Album')
            self.assertTrue(entries[0]['url'].startswith('https://music.youtube.com/watch'))
            self.assertFalse(mocked.call_args.args[0]['noplaylist'])

    def test_title_only_names_and_collisions(self):
        title = 'Barış Manço - Hal Hal & Sarı Çizmeli Mehmet Ağa - STAR AI 2.5'
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            names = {}
            self.assertEqual(reserve_title(folder, {'id': 'first', 'title': title}, names), title)
            (folder / (title + '.mp4')).touch()
            self.assertEqual(reserve_title(folder, {'id': 'first', 'title': title}, names), title)
            self.assertEqual(reserve_title(folder, {'id': 'second', 'title': title}, names), title + ' (2)')
            self.assertEqual(json.loads(metadata_paths(folder, {'format': 'MP4', 'quality': 'En yüksek'})['names'].read_text(encoding='utf-8'))['first'], title)
            self.assertFalse((folder / '.dosya-adlari.json').exists())

    def test_video_links_do_not_expand_playlists(self):
        expected = ('video', 'https://www.youtube.com/watch?v=SyQi3gH-Ol4')
        for url in ['https://www.youtube.com/watch?v=SyQi3gH-Ol4&list=PLexample&index=3',
                    'https://youtu.be/SyQi3gH-Ol4?si=abc', 'youtube.com/shorts/SyQi3gH-Ol4',
                    'https://www.youtube.com/live/SyQi3gH-Ol4', 'https://www.youtube.com/embed/SyQi3gH-Ol4']:
            self.assertEqual(normalize_source(url), expected)
        self.assertEqual(normalize_source('@UHFklip')[0], 'channel')
        for url in ['https://www.youtube.com/watch?v=abc', 'https://evil.example/watch?v=SyQi3gH-Ol4', 'https://youtu.be/']:
            with self.assertRaises(ValueError):
                normalize_source(url)

    def test_worker_downloads_only_selected_videos(self):
        calls = []
        class FakeDownloader:
            def __init__(self, options): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, url, download):
                return {'id': url.split('v=')[-1]}
            def process_ie_result(self, info, download):
                calls.append(('https://www.youtube.com/watch?v=' + info['id'], download))
                return info
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = {'action': 'download', 'url': 'https://www.youtube.com/@UHFklip', 'all_tabs': True,
                   'selected_entries': [{'id': 'SyQi3gH-Ol4', 'title': 'First'}, {'id': 'Zyvzfn-bYL8', 'title': 'Third'}],
                   'channel_title': 'Test Channel', 'format': 'MP4', 'quality': 'En yüksek', 'output': str(root),
                   'events': str(root / 'events.jsonl'), 'log': str(root / 'log.txt')}
            job_file = root / 'job.json'
            job_file.write_text(json.dumps(job), encoding='utf-8')
            with patch.object(yt_dlp, 'YoutubeDL', FakeDownloader):
                self.assertEqual(run_worker(job_file), 0)
            self.assertEqual(calls, [('https://www.youtube.com/watch?v=SyQi3gH-Ol4', True),
                                     ('https://www.youtube.com/watch?v=Zyvzfn-bYL8', True)])
            events = [json.loads(line) for line in Path(job['events']).read_text(encoding='utf-8').splitlines()]
            self.assertEqual(events[-1]['total'], 2)
            self.assertEqual(events[-1]['completed'], 2)
            with self.assertRaises(ValueError):
                get_entries({**job, 'selected_entries': []}, SilentLog())

    def test_gui_selection_and_stale_list(self):
        def verify(app):
            app.url.set('@UHFklip')
            app.action = 'list'
            entries = [{'id': value, 'title': value, 'duration': 60} for value in ['SyQi3gH-Ol4', 'nUUy8g31HN8', 'Zyvzfn-bYL8']]
            app.handle({'kind': 'list', 'channel': 'UHF', 'folder': 'test', 'entries': entries, 'skipped_live': 0})
            self.assertEqual(len(app.selected_ids), 0)
            self.assertIn('disabled', app.start_btn.state())
            app.toggle('Zyvzfn-bYL8')
            self.assertEqual(app.selected_ids, {'Zyvzfn-bYL8'})
            self.assertNotIn('disabled', app.start_btn.state())
            app.select_all(True)
            self.assertEqual(len(app.selected_ids), 3)
            app.select_all(False)
            self.assertEqual(len(app.selected_ids), 0)
            app.table.selection_set('SyQi3gH-Ol4', 'nUUy8g31HN8')
            app.toggle_highlighted()
            self.assertEqual(len(app.selected_ids), 2)
            app.entries['SyQi3gH-Ol4']['title'] = 'Barış Manço - Sarı Çizmeli'
            app.entries['nUUy8g31HN8']['title'] = 'Kenan Doğulu'
            app.search.set('baris sari')
            self.assertEqual(app.visible_ids, ['SyQi3gH-Ol4'])
            self.assertEqual(len(app.selected_ids), 2)
            app.select_all(False)
            app.select_visible()
            self.assertEqual(app.selected_ids, {'SyQi3gH-Ol4'})
            app.search.set('kenan')
            app.select_visible()
            self.assertEqual(len(app.selected_ids), 2)
            app.search.set('no results')
            self.assertFalse(app.visible_ids)
            app.url.set('https://youtu.be/SyQi3gH-Ol4')
            # Editing a link preserves the queue; fetching replaces it on success.
            self.assertEqual(len(app.entries), 3)
            app.invalidate_list()
            self.assertFalse(app.entries)
            self.assertFalse(app.table.exists('nUUy8g31HN8'))
            self.assertIsNone(app.loaded_key)
            self.assertIn('disabled', app.start_btn.state())
            app.handle({'kind': 'list', 'channel': 'UHF', 'folder': 'test', 'entries': entries[:1], 'skipped_live': 0})
            self.assertEqual(app.selected_ids, {'SyQi3gH-Ol4'})
            app.process = object()
            app.busy(True)
            app.toggle('SyQi3gH-Ol4')
            self.assertEqual(app.selected_ids, {'SyQi3gH-Ol4'})
            self.assertIn('disabled', app.start_btn.state())
            app.process = None
            app.busy(False)
            self.assertNotIn('disabled', app.start_btn.state())
        run_gui(test_callback=verify)

    def test_multilingual_queue_sort_and_progress(self):
        from translations import LANGUAGES, CATALOG, ROWS
        self.assertEqual(len(LANGUAGES), 7)
        for catalog in CATALOG.values():
            self.assertEqual(set(catalog), set(ROWS))
            self.assertTrue(all(catalog.values()))
        def verify(app):
            app.url.set('https://youtu.be/SyQi3gH-Ol4')
            app.action = 'list'
            app.search.set('stale search')
            first = {'id': 'SyQi3gH-Ol4', 'title': 'Zulu', 'duration': 65, 'url': 'https://www.youtube.com/watch?v=SyQi3gH-Ol4'}
            second = {'id': 'Zyvzfn-bYL8', 'title': 'Alpha', 'duration': 3601, 'url': 'https://music.youtube.com/watch?v=Zyvzfn-bYL8'}
            def listing(entries):
                app.handle({'kind': 'list', 'entries': entries, 'channel': 'Test', 'folder': 'test', 'skipped_live': 0})
            listing([first])
            self.assertEqual(app.search.get(), '')
            self.assertEqual(app.table.get_children(), ('SyQi3gH-Ol4',))
            app.url.set(second['url'])
            self.assertEqual(len(app.entries), 1)
            app.append_mode = True
            listing([second])
            listing([second])
            self.assertEqual(len(app.entries), 2)
            self.assertEqual(len(app.selected_ids), 2)
            self.assertTrue(app.entries['Zyvzfn-bYL8']['url'].startswith('https://music.youtube.com'))
            app.sort_by('title')
            self.assertEqual(app.visible_ids, ['Zyvzfn-bYL8', 'SyQi3gH-Ol4'])
            app.sort_by('title')
            self.assertEqual(app.visible_ids, ['SyQi3gH-Ol4', 'Zyvzfn-bYL8'])
            app.sort_by('duration')
            self.assertEqual(app.visible_ids[0], 'SyQi3gH-Ol4')
            app.sort_by('duration')
            self.assertEqual(app.visible_ids[0], 'Zyvzfn-bYL8')
            app.handle({'kind': 'current', 'id': 'SyQi3gH-Ol4', 'title': 'Zulu', 'index': 1, 'total': 2})
            app.handle({'kind': 'progress', 'percent': 47, 'speed': 1048576, 'eta': 30})
            self.assertIn('47%', app.table.set('SyQi3gH-Ol4', 'state'))
            app.handle({'kind': 'status', 'text': 'Görüntü ve ses MP4 olarak birleştiriliyor…'})
            self.assertEqual(app.states['SyQi3gH-Ol4'][0], 'processing')
            app.handle({'kind': 'item', 'id': 'SyQi3gH-Ol4', 'state': 'Tamamlandı'})
            self.assertEqual(app.states['SyQi3gH-Ol4'], ('completed', 100))
            for lang in LANGUAGES:
                app.language = lang
                app.refresh_language()
                for theme in ('light', 'dark'):
                    app.theme = theme
                    app.apply_theme()
                    app.root.update_idletasks()
                self.assertEqual(app.list_btn.cget('text'), CATALOG[lang]['fetch'])
                self.assertEqual(app.table.heading('title')['text'].split(' ▲')[0].split(' ▼')[0], CATALOG[lang]['title'])
                self.assertEqual(app.quality.get(), 'En yüksek')
            app.sort_by('state')
            self.assertEqual(app.visible_ids[0], 'Zyvzfn-bYL8')
            app.select_all(False)
            app.toggle('Zyvzfn-bYL8')
            app.remove_selected()
            self.assertEqual(set(app.entries), {'SyQi3gH-Ol4'})
            # A later fresh scan replaces the queue and resets search.
            app.append_mode = False
            app.search.set('none')
            listing([second])
            self.assertEqual(set(app.entries), {'Zyvzfn-bYL8'})
            self.assertEqual(app.search.get(), '')
        run_gui(test_callback=verify)

    def test_channel_urls(self):
        for link in ['@UHFklip', 'youtube.com/@UHFklip', 'https://www.youtube.com/@UHFklip/videos?view=0']:
            self.assertEqual(normalize_channel(link), 'https://www.youtube.com/@UHFklip')
        self.assertEqual(normalize_channel('https://www.youtube.com/channel/UCexample/streams'), 'https://www.youtube.com/channel/UCexample')
        for link in ['https://evil.example/@channel', 'https://www.youtube.com/watch?v=abc', 'https://youtu.be/abc', 'https://www.youtube.com/@x/unrecognized']:
            with self.assertRaises(ValueError):
                normalize_channel(link)

    def test_real_mp4_mp3_and_archive(self):
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        hooks = {'progress': lambda event: None, 'postprocess': lambda event: None}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / 'sample.mp4'
            from PIL import Image
            Image.new('RGB', (120, 120), '#2563EB').save(root / 'cover.png')
            subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=25',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100', '-t', '1', '-c:v', 'libx264',
                            '-c:a', 'aac', str(fixture)], check=True, capture_output=True)
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=directory))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/sample.mp4'
                for fmt, quality, suffix, stream_codec in [('MP4', 'En yüksek', '.mp4', 'Video: h264'), ('MP3', '320 kbps', '.mp3', 'Audio: mp3')]:
                    output = root / fmt
                    output.mkdir()
                    options = make_options({'format': fmt, 'quality': quality}, output, SilentLog(), hooks)
                    options.update(sleep_interval=0, max_sleep_interval=0)
                    if fmt == 'MP4':
                        download_with_recovery(url, options, lambda *args, **kwargs: None)
                    else:
                        cover_info = {'_type': 'video', 'id': 'sample', 'title': 'sample', 'artist': 'Fixture Artist',
                                      'webpage_url': url, 'url': url, 'ext': 'mp4', 'vcodec': 'h264', 'acodec': 'aac',
                                      'extractor_key': 'Generic', 'thumbnails': [{'url': f'http://127.0.0.1:{server.server_port}/cover.png', 'id': 'cover'}]}
                        with patch.object(yt_dlp.YoutubeDL, 'extract_info', side_effect=lambda *args, **kwargs: dict(cover_info)):
                            download_with_recovery(url, options, lambda *args, **kwargs: None)
                    files = list(output.glob('*' + suffix))
                    self.assertEqual(len(files), 1)
                    self.assertEqual(files[0].name, 'sample' + suffix)
                    probe = subprocess.run([ffmpeg, '-hide_banner', '-i', str(files[0]), '-map', '0', '-c', 'copy', '-f', 'null', '-'], capture_output=True, text=True)
                    self.assertEqual(probe.returncode, 0, probe.stderr)
                    self.assertIn(stream_codec, probe.stderr)
                    if fmt == 'MP3':
                        self.assertIn('320 kb/s', probe.stderr)
                        from mutagen.id3 import ID3
                        tags = ID3(files[0])
                        self.assertEqual(tags.version, (2, 3, 0))
                        pictures = tags.getall('APIC')
                        self.assertEqual(len(pictures), 1)
                        self.assertEqual(pictures[0].mime, 'image/jpeg')
                        self.assertEqual(pictures[0].type, 3)
                        self.assertTrue(pictures[0].data.startswith(b'\xff\xd8'))
                        self.assertEqual(str(tags.get('TPE1')), 'Fixture Artist')
                        self.assertFalse(list(output.glob('*.jpg')) + list(output.glob('*.png')) + list(output.glob('*.webp')))
                    archive = Path(options['download_archive'])
                    self.assertTrue(archive.exists())
                    self.assertFalse(list(output.glob('*.txt')))
                    self.assertFalse(list(output.glob('*.json')))
                    previous_time = files[0].stat().st_mtime_ns
                    with yt_dlp.YoutubeDL(options) as downloader:
                        downloader.download([url])
                    self.assertEqual(files[0].stat().st_mtime_ns, previous_time)
                split_output = root / 'TwoStreams'
                split_output.mkdir()
                options = make_options({'format': 'MP4', 'quality': 'En yüksek'}, split_output, SilentLog(), hooks)
                options.update(sleep_interval=0, max_sleep_interval=0)
                info = {'_type': 'video', 'id': 'twostreams', 'title': 'Two streams', 'extractor_key': 'Generic',
                        'webpage_url': url, 'formats': [
                            {'format_id': 'v', 'url': url + '?video', 'ext': 'mp4', 'vcodec': 'h264', 'acodec': 'none', 'height': 180, 'fps': 25},
                            {'format_id': 'a', 'url': url + '?audio', 'ext': 'm4a', 'vcodec': 'none', 'acodec': 'aac', 'abr': 128}]}
                with patch.object(yt_dlp.YoutubeDL, 'extract_info', return_value=info):
                    download_with_recovery(url, options, lambda *args, **kwargs: None)
                self.assertTrue((split_output / 'Two streams.mp4').exists())
                recovery_output = root / 'Recovery'
                recovery_output.mkdir()
                options = make_options({'format': 'MP4', 'quality': 'En yüksek'}, recovery_output, SilentLog(), hooks)
                options.update(sleep_interval=0, max_sleep_interval=0)
                recovery_info = {'_type': 'video', 'id': 'retry', 'title': 'Recovered', 'extractor_key': 'Generic',
                                 'webpage_url': url, 'url': url + '?reject-once', 'ext': 'mp4', 'vcodec': 'h264', 'acodec': 'aac'}
                with patch.object(yt_dlp.YoutubeDL, 'extract_info', side_effect=lambda *args, **kwargs: dict(recovery_info)):
                    download_with_recovery(url, options, lambda *args, **kwargs: None, sleep=lambda n: None)
                self.assertTrue((recovery_output / 'Recovered.mp4').exists())
            finally:
                server.shutdown()
                server.server_close()

    def test_flat_output_channel_subfolders_and_metadata(self):
        class Downloader:
            def __init__(self, options): self.options = options
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, url, download): return {'id': url.split('v=')[-1]}
            def process_ie_result(self, info, download):
                Path(self.options['outtmpl'].replace('%(ext)s', 'mp4')).write_bytes(b'fixture')
                Path(self.options['download_archive']).write_text('youtube ' + info['id'] + '\n', encoding='utf-8')
                return info
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            job = {'action': 'download', 'url': 'https://www.youtube.com/watch?v=SyQi3gH-Ol4', 'all_tabs': False,
                   'selected_entries': [{'id': 'SyQi3gH-Ol4', 'title': 'First', 'channel': 'Channel A'}, {'id': 'Zyvzfn-bYL8', 'title': 'Second', 'channel': 'Channel B'}],
                   'channel_title': 'Mixed', 'format': 'MP4', 'quality': 'En yüksek', 'output': str(root / 'flat'),
                   'events': str(root / 'events.jsonl'), 'log': str(root / 'log.txt')}
            path = root / 'job.json'
            path.write_text(json.dumps(job), encoding='utf-8')
            with patch.object(yt_dlp, 'YoutubeDL', Downloader):
                self.assertEqual(run_worker(path), 0)
            self.assertEqual({p.name for p in (root / 'flat').iterdir()}, {'First.mp4', 'Second.mp4'})
            paths = metadata_paths(root / 'flat', job)
            self.assertTrue(paths['names'].exists() and paths['report'].exists())
            job.update(output=str(root / 'channels'), channel_subfolders=True)
            path.write_text(json.dumps(job), encoding='utf-8')
            with patch.object(yt_dlp, 'YoutubeDL', Downloader):
                self.assertEqual(run_worker(path), 0)
            self.assertEqual({p.name for p in (root / 'channels').iterdir()}, {'Channel A', 'Channel B'})
            self.assertTrue((root / 'channels' / 'Channel A' / 'First.mp4').exists())
            self.assertTrue((root / 'channels' / 'Channel B' / 'Second.mp4').exists())
            for folder in (root / 'channels').iterdir():
                self.assertFalse(list(folder.glob('*.json')) + list(folder.glob('*.txt')))
            legacy = root / 'legacy'
            legacy.mkdir()
            (legacy / '.tamamlananlar.txt').write_text('youtube SyQi3gH-Ol4\n', encoding='utf-8')
            migrated = metadata_paths(legacy, job)
            self.assertIn('SyQi3gH-Ol4', migrated['archive'].read_text(encoding='utf-8'))
            self.assertFalse((legacy / '.tamamlananlar.txt').exists())

    def test_deleted_archived_media_downloads_again(self):
        downloads = []
        class Downloader:
            def __init__(self, options): self.options = options
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, url, download): return {'id': url.split('v=')[-1]}
            def process_ie_result(self, info, download):
                archive = Path(self.options['download_archive'])
                previous = archive.read_text(encoding='utf-8') if archive.exists() else ''
                if 'youtube ' + info['id'] in previous:
                    raise AssertionError('Stale archive was not repaired before downloading')
                template = self.options['outtmpl']
                template = template['default'] if isinstance(template, dict) else template
                if Path(template.replace('%(ext)s', self.options['test_ext'])).exists():
                    raise AssertionError('An empty final file must be removed before download')
                Path(template.replace('%(ext)s', self.options['test_ext'])).write_bytes(b'media')
                archive.write_text(previous + 'youtube ' + info['id'] + '\n', encoding='utf-8')
                downloads.append(info['id'])
                return info
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for fmt, quality in [('MP4', 'En yüksek'), ('MP3', '320 kbps')]:
                out = root / fmt
                job = {'action': 'download', 'url': 'https://youtu.be/SyQi3gH-Ol4', 'all_tabs': False,
                       'selected_entries': [{'id': 'SyQi3gH-Ol4', 'title': 'Song', 'channel': 'Artist'}],
                       'channel_title': 'Artist', 'format': fmt, 'quality': quality, 'output': str(out),
                       'events': str(root / (fmt + '.events')), 'log': str(root / (fmt + '.log'))}
                job_file = root / 'job.json'
                job_file.write_text(json.dumps(job), encoding='utf-8')
                real_options = make_options
                def options(*args, **kwargs): return {**real_options(*args, **kwargs), 'test_ext': fmt.lower()}
                with patch.object(yt_dlp, 'YoutubeDL', Downloader), patch('kanal_indirici.make_options', side_effect=options):
                    self.assertEqual(run_worker(job_file), 0)
                    count = len(downloads)
                    self.assertEqual(run_worker(job_file), 0)
                    self.assertEqual(len(downloads), count)
                    paths = metadata_paths(out, job)
                    with paths['archive'].open('a', encoding='utf-8') as archive:
                        archive.write('youtube Zyvzfn-bYL8\n')
                    (out / ('Song.' + fmt.lower())).unlink()
                    self.assertEqual(run_worker(job_file), 0)
                    self.assertEqual(len(downloads), count + 1)
                    self.assertTrue((out / ('Song.' + fmt.lower())).exists())
                    self.assertIn('youtube Zyvzfn-bYL8', paths['archive'].read_text(encoding='utf-8'))
                    # An empty final file is also insufficient to skip the download.
                    (out / ('Song.' + fmt.lower())).write_bytes(b'')
                    self.assertEqual(run_worker(job_file), 0)
                    self.assertEqual(len(downloads), count + 2)

    def test_artist_playlist_folder_options_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            entry = {'id': 'SyQi3gH-Ol4', 'title': 'Song', 'channel': 'Channel', 'artist': 'Singer', 'playlist_title': 'My playlist'}
            job = {'output': directory, 'url': 'https://youtube.com/watch?v=SyQi3gH-Ol4', 'action': 'download', 'selected_entries': [entry]}
            selected, _, _ = get_entries(job, SilentLog())
            self.assertEqual(selected[0]['artist'], 'Singer')
            self.assertEqual(selected[0]['playlist_title'], 'My playlist')
            self.assertEqual(output_folder(job, entry), base)
            self.assertEqual(output_folder({**job, 'artist_subfolders': True}, entry), base / 'Singer')
            self.assertEqual(output_folder({**job, 'playlist_subfolders': True}, entry), base / 'My playlist')
            self.assertEqual(output_folder({**job, 'channel_subfolders': True, 'artist_subfolders': True, 'playlist_subfolders': True}, entry), base / 'Channel' / 'Singer' / 'My playlist')
            unknown = {**entry, 'artist': None, 'playlist_title': None}
            self.assertEqual(output_folder({**job, 'artist_subfolders': True, 'playlist_subfolders': True}, unknown), base / 'Channel')
            malicious = {**entry, 'artist': '../outside', 'playlist_title': '../../list'}
            self.assertTrue(output_folder({**job, 'artist_subfolders': True, 'playlist_subfolders': True}, malicious).resolve().is_relative_to(base))


if __name__ == '__main__':
    unittest.main(verbosity=2)
