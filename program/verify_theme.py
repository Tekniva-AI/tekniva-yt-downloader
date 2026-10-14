"""Exercise theme states, live preview/cancel, saved preferences and localized dialogs."""
import json
import tempfile
import time
from pathlib import Path
from kanal_indirici import run_gui
from translations import LANGUAGES, VERSION


def contrast(first, second):
    def luminance(color):
        rgb = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
        rgb = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        return sum(v*w for v, w in zip(rgb, (.2126, .7152, .0722)))
    bright, dim = sorted((luminance(first), luminance(second)), reverse=True)
    return (bright+.05)/(dim+.05)


def verify(app):
    with tempfile.TemporaryDirectory() as directory:
        app.config_file = Path(directory) / 'settings.json'
        app.queue_file = Path(directory) / 'queue.json'
        app.persistence_enabled = True
        app.output.set(directory)
        app.root.deiconify()
        app.root.update()
        checked = 0
        for language in LANGUAGES:
            app.language = language
            app.refresh_language()
            for theme in ('light', 'dark'):
                app.theme = theme
                app.apply_theme()
                dialog = app.open_settings()
                app.root.update()
                for state in ((), ('active',), ('selected',), ('active', 'selected')):
                    fg = app.style.lookup('TCheckbutton', 'foreground', state)
                    bg = app.style.lookup('TCheckbutton', 'background', state)
                    assert contrast(fg, bg) >= 4.5, (language, theme, state, fg, bg)
                assert app.style.lookup('TCombobox', 'fieldbackground', ('readonly',)) != '#FFFFFF' if theme == 'dark' else True
                app.settings_subfolder_check.invoke()
                app.settings_subfolder_check.event_generate('<Enter>')
                app.root.update()
                assert dialog.winfo_height() < app.root.winfo_screenheight() - 60
                dialog.destroy()
                checked += 1
        app.language = 'tr'
        app.theme = 'dark'
        app.refresh_language()
        app.apply_theme()
        dialog = app.open_settings()
        app.light_mode_btn.invoke()
        assert app.theme == 'light'
        app.settings_cancel_btn.invoke()
        assert app.theme == 'dark'
        assert not app.config_file.exists()
        dialog = app.open_settings()
        app.light_mode_btn.invoke()
        app.settings_save_btn.invoke()
        assert json.loads(app.config_file.read_text(encoding='utf-8'))['theme'] == 'light'
        assert VERSION in app.version_label.cget('text')
        app.theme = 'dark'
        app.apply_theme()
        dialog = app.open_settings()
        dialog.attributes('-topmost', True)
        dialog.lift()
        app.settings_subfolder_check.event_generate('<Enter>')
        app.root.update()
        app.settings_cancel_btn.invoke()
        print(json.dumps({'localized_theme_dialogs': checked, 'text_contrast': '>=4.5', 'live_preview_cancel': True, 'saved_theme': True, 'version': VERSION}))


if __name__ == '__main__':
    run_gui(test_callback=verify)
