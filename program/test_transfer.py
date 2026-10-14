"""Exercise the selected HTTP handler, fallback and queue controls."""
import http.server
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from yt_dlp.networking import Request
from yt_dlp.networking._curlcffi import CurlCFFIRH
from transfer import create_downloader
from kanal_indirici import run_gui, make_options, download_with_recovery


class Logger:
    def debug(self, text): pass
    def warning(self, text): pass
    def error(self, text): pass


class TransferTests(unittest.TestCase):
    def test_default_really_sends_range_and_headers_through_curl(self):
        received, calls = [], []
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                received.append((self.headers.get('Range'), self.headers.get('X-Test')))
                self.send_response(206)
                self.send_header('Content-Length', '5')
                self.send_header('Content-Range', 'bytes 5-9/10')
                self.end_headers()
                self.wfile.write(b'56789')
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        original = CurlCFFIRH._send
        def tracked(handler, request):
            calls.append(request.url)
            return original(handler, request)
        try:
            with create_downloader({'quiet': True}) as downloader, patch.object(CurlCFFIRH, '_send', tracked):
                with downloader.urlopen(Request(f'http://127.0.0.1:{server.server_port}/media',
                                                headers={'Range': 'bytes=5-9', 'X-Test': 'preserved'})) as response:
                    self.assertEqual(response.read(), b'56789')
                self.assertIsNone(downloader.params.get('impersonate'))
            self.assertEqual(len(calls), 1)
            self.assertEqual(received, [('bytes=5-9', 'preserved')])
        finally:
            server.shutdown()
            server.server_close()

    def test_missing_curl_is_reported_instead_of_silently_claiming_it(self):
        import yt_dlp
        original = yt_dlp.YoutubeDL.build_request_director
        def without_curl(instance, *args, **kwargs):
            director = original(instance, *args, **kwargs)
            director.handlers.pop('CurlCFFI', None)
            return director
        with patch.object(yt_dlp.YoutubeDL, 'build_request_director', without_curl):
            with self.assertRaisesRegex(RuntimeError, 'curl_cffi component is missing'):
                create_downloader({'quiet': True})

    def test_curl_failure_refreshes_using_native_same_quality(self):
        import yt_dlp
        attempts = []
        class Downloader:
            def __init__(self, options): attempts.append(options)
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def extract_info(self, *args, **kwargs): return {'height': 2160, 'fps': 60}
            def process_ie_result(self, info, download):
                if len(attempts) == 1:
                    raise yt_dlp.utils.DownloadError('HTTP 403 Forbidden')
                return info
        with patch('kanal_indirici.create_downloader', Downloader):
            result = download_with_recovery('https://youtube.com/watch?v=sample',
                     {'tekniva_engine': 'curl_cffi', 'logger': Logger()}, lambda *args, **kwargs: None, sleep=lambda delay: None)
        self.assertEqual([o['tekniva_engine'] for o in attempts], ['curl_cffi', 'native'])
        self.assertEqual(result['height'], 2160)
        self.assertFalse(any(o.get('nocheckcertificate') for o in attempts))

    def test_engine_setting_is_independent_from_connection_count(self):
        with tempfile.TemporaryDirectory() as directory, patch('kanal_indirici.APP_DIR', Path(directory)):
            for engine in ('curl_cffi', 'aria2'):
                options = make_options({'format': 'MP4', 'quality': 'En yüksek', 'engine': engine, 'speed': 'Dengeli (4 bağlantı)'},
                                       Path(directory), Logger(), {'progress': lambda event: None, 'postprocess': lambda event: None})
                self.assertEqual(options['tekniva_engine'], engine)
                self.assertEqual(options['concurrent_fragment_downloads'], 4)

    def test_queue_filters_source_search_and_completed_file_open(self):
        def verify(app):
            app.action = 'restore'
            app.handle({'kind': 'list', 'folder': '.', 'channel': 'Test', 'entries': [
                {'id': 'sample00001', 'title': 'Song', 'channel': 'Artist A'},
                {'id': 'sample00002', 'title': 'Concert', 'channel': 'Artist B'}]})
            app.set_state('sample00001', 'completed', 100)
            app.filter_mode.set('completed')
            app.apply_search()
            self.assertEqual(app.visible_ids, ['sample00001'])
            app.filter_mode.set('waiting')
            app.apply_search()
            self.assertEqual(app.visible_ids, ['sample00002'])
            app.search.set('Artist B')
            self.assertEqual(app.visible_ids, ['sample00002'])
            app.set_state('sample00002', 'failed')
            self.assertEqual(app.visible_ids, [])
            app.filter_mode.set('failed')
            app.apply_search()
            self.assertEqual(app.visible_ids, ['sample00002'])
            with tempfile.NamedTemporaryFile(suffix='.mp3') as file, patch('tekniva_gui.os.startfile') as opened:
                app.entries['sample00001']['filepath'] = file.name
                app.open_item('sample00001')
                opened.assert_called_once_with(file.name)
            app.open_item('sample00001')
            self.assertEqual(app.status.get(), app.t('file_missing'))
        run_gui(test_callback=verify)

    def test_settings_cancel_save_engine_and_clipboard_opt_in(self):
        def verify(app):
            app.engine.set('curl_cffi')
            app.clipboard_watch.set(False)
            with patch.object(app, 'clipboard_link') as read:
                app.poll_clipboard()
                read.assert_not_called()
            app.open_settings()
            app.engine_box.current(1)
            app.settings_cancel_btn.invoke()
            self.assertEqual(app.engine.get(), 'curl_cffi')
            app.open_settings()
            app.engine_box.current(1)
            app.settings_save_btn.invoke()
            self.assertEqual(app.engine.get(), 'aria2')
            with (patch.object(app, 'clipboard_link', return_value=('https://youtu.be/SyQi3gH-Ol4', 'https://www.youtube.com/watch?v=SyQi3gH-Ol4')),
                  patch.object(app, 'start') as start):
                app.paste_link()
                start.assert_called_once_with('append')
                self.assertIn('SyQi3gH-Ol4', app.url.get())
        run_gui(test_callback=verify)


if __name__ == '__main__':
    unittest.main(verbosity=2)
