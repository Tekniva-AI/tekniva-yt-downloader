"""Runtime installation tests use local ZIP fixtures, not executable downloads."""
import hashlib
import io
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
import dependencies as dep
import kanal_indirici


class Response(io.BytesIO):
    def __init__(self, data):
        super().__init__(data)
        self.headers = {'Content-Length': str(len(data))}


class DependencyTests(unittest.TestCase):
    def fixture(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            prefix = f'node-v{dep.NODE_VERSION}-win-x64/'
            archive.writestr(prefix + 'node.exe', b'fixture-not-a-real-executable')
            archive.writestr(prefix + 'LICENSE', b'fixture-license')
            archive.writestr(prefix + '../../outside.txt', b'never-extracted')
        return stream.getvalue()

    def test_missing_old_and_app_local_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = root / 'old-node.exe'
            system.write_bytes(b'old')
            local = dep.local_node(root)
            local.parent.mkdir(parents=True)
            local.write_bytes(b'current')
            with patch.object(dep.shutil, 'which', return_value=str(system)), patch.object(dep, 'usable_node', side_effect=lambda p: Path(p) == local):
                self.assertEqual(dep.node_path(root), str(local.resolve()))
                self.assertEqual(dep.node_runtime_options(root), {'node': {'path': str(local.resolve())}})
                local.unlink()
                self.assertIsNone(dep.node_path(root))

    def test_verified_install_extracts_only_runtime_and_license(self):
        data = self.fixture()
        events = []
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(dep.urllib.request, 'urlopen', return_value=Response(data)), \
                patch.object(dep, 'NODE_SHA256', hashlib.sha256(data).hexdigest()), \
                patch.object(dep, 'usable_node', return_value=True):
            path = dep.install_node(directory, lambda *event: events.append(event))
            self.assertEqual(Path(path).read_bytes(), b'fixture-not-a-real-executable')
            files = sorted(p.name for p in Path(directory).rglob('*') if p.is_file())
            self.assertEqual(files, ['LICENSE', 'node.exe'])
            self.assertIn(('verify', 100), events)
            with patch.object(kanal_indirici, 'APP_DIR', Path(directory)):
                options = kanal_indirici.make_options({'format': 'MP4', 'quality': 'En yüksek'}, Path(directory), type('Log', (), {})(), {'progress': lambda event: None, 'postprocess': lambda event: None})
                self.assertEqual(options['js_runtimes'], {'node': {'path': path}})

    def test_bad_hash_never_executes_or_replaces_existing_runtime(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(dep.urllib.request, 'urlopen', return_value=Response(self.fixture())), \
                patch.object(dep, 'usable_node') as execute:
            existing = dep.local_node(directory)
            existing.parent.mkdir(parents=True)
            existing.write_bytes(b'previous')
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                dep.install_node(directory)
            execute.assert_not_called()
            self.assertEqual(existing.read_bytes(), b'previous')
            self.assertFalse(list(Path(directory).glob('tools/.node-install-*')))

    def test_cancel_removes_partial_files(self):
        cancel = threading.Event()
        def progress(phase, percent):
            cancel.set()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(dep.urllib.request, 'urlopen', return_value=Response(self.fixture())):
            with self.assertRaises(dep.InstallCancelled):
                dep.install_node(directory, progress, cancel)
            self.assertFalse(list(Path(directory).rglob('*.zip')))
            self.assertFalse(dep.local_node(directory).exists())

    def test_gui_decline_and_success_resume_same_action(self):
        def verify(app):
            app.url.set('@Tekniva')
            with tempfile.TemporaryDirectory() as directory:
                app.output.set(directory)
                with patch('tekniva_gui.node_path', return_value=None), \
                        patch('tekniva_gui.messagebox.askyesno', return_value=False), \
                        patch('tekniva_gui.subprocess.Popen') as launch:
                    app.start('append')
                    launch.assert_not_called()
                    self.assertFalse(app.installing)
                # The background installer resumes exactly the original queue action.
                with patch('tekniva_gui.node_path', return_value=None), \
                        patch('tekniva_gui.messagebox.askyesno', return_value=True), \
                        patch('tekniva_gui.install_node', return_value='portable-node.exe') as install:
                    app.start('append')
                    self.assertTrue(app.installing)
                    import time
                    deadline = time.monotonic() + 3
                    while app.install_events.empty() and time.monotonic() < deadline:
                        time.sleep(.01)
                    with patch.object(app, 'start') as resume:
                        app.poll_install()
                        app.root.update()
                        resume.assert_called_once_with('append')
                    install.assert_called_once()
                    self.assertFalse(app.installing)
        kanal_indirici.run_gui(test_callback=verify)


if __name__ == '__main__':
    unittest.main(verbosity=2)
