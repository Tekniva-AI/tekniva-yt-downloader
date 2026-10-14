"""Compact multilingual desktop interface for the isolated downloader worker."""
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
import webbrowser
import threading
import queue
import io
from urllib.parse import urlparse
from dependencies import node_path, install_node, InstallCancelled
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from translations import LANGUAGES, VERSION, translate


def run_gui(test_callback=None):
    # Importing here also works when the downloader is running as __main__.
    from kanal_indirici import APP_DIR, PROJECT, NO_WINDOW, normalize_source, search_text, VIDEO_QUALITIES, AUDIO_QUALITIES, SPEED_MODES

    class App:
        def __init__(self, root):
            self.root = root
            self.process = self.events_file = self.log_file = self.actual_folder = None
            self.installing = False
            self.install_events = queue.SimpleQueue()
            self.install_cancel = threading.Event()
            self.install_dialog = None
            self.last_error_hint = None
            self.event_offset = 0
            self.event_buffer = ''
            self.got_final = self.stopping = False
            self.entries = {}
            self.thumbnail_jobs = queue.SimpleQueue()
            self.thumbnail_results = queue.SimpleQueue()
            self.thumbnail_images = {}
            self.thumbnail_requested = set()
            self.selected_ids = set()
            self.visible_ids = []
            self.states = {}
            self.loaded_key = None
            self.channel_title = ''
            self.action = None
            self.append_mode = False
            self.current_id = None
            self.sort_column = None
            self.sort_reverse = False
            self.config_file = APP_DIR / 'ayarlar.json'
            self.queue_file = APP_DIR / 'kuyruk.json'
            self.persistence_enabled = test_callback is None
            try:
                self.settings = json.loads(self.config_file.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                self.settings = {}
            self.language = self.settings.get('language', 'tr')
            if self.language not in LANGUAGES:
                self.language = 'tr'
            self.theme = self.settings.get('theme', 'light')
            self.text_widgets = []
            self.root.title('Tekniva YT Downloader')
            # Logical dimensions: Windows scales this automatically for high DPI screens.
            self.root.geometry('1000x640')
            self.root.minsize(920, 600)
            icon = Path(getattr(sys, '_MEIPASS', APP_DIR)) / 'app.ico'
            if icon.exists():
                root.iconbitmap(str(icon))
            self.style = ttk.Style(root)
            self.style.theme_use('clam')
            self.url = tk.StringVar(value=self.settings.get('url', ''))
            self.output = tk.StringVar(value=self.settings.get('output', str(PROJECT / 'Indirmeler')))
            self.channel_subfolders = tk.BooleanVar(value=self.settings.get('channel_subfolders', False))
            self.artist_subfolders = tk.BooleanVar(value=self.settings.get('artist_subfolders', False))
            self.playlist_subfolders = tk.BooleanVar(value=self.settings.get('playlist_subfolders', False))
            self.fmt = tk.StringVar(value=self.settings.get('format', 'MP4'))
            self.quality = tk.StringVar(value=self.settings.get('quality', VIDEO_QUALITIES[0]))
            self.scope = tk.StringVar(value=self.settings.get('scope', 'Videolar + Shorts + yayın kayıtları'))
            self.speed_mode = tk.StringVar(value=self.settings.get('speed', SPEED_MODES[0]))
            self.quality_display = tk.StringVar()
            self.scope_display = tk.StringVar()
            self.speed_display = tk.StringVar()
            self.engine = tk.StringVar(value=self.settings.get('engine', 'curl_cffi') if self.settings.get('engine') in ('curl_cffi', 'aria2') else 'curl_cffi')
            self.clipboard_watch = tk.BooleanVar(value=self.settings.get('clipboard_watch', False))
            self.last_clipboard = None
            self.filter_mode = tk.StringVar(value='all')
            self.search = tk.StringVar()
            self.selection_text = tk.StringVar()
            self.status = tk.StringVar(value=self.t('ready'))
            self.detail = tk.StringVar(value=self.t('instructions'))
            self.count = tk.StringVar(value=self.t('empty'))

            header = ttk.Frame(root, padding=(16, 8), style='Header.TFrame')
            header.pack(fill='x')
            ttk.Label(header, text='TEKNIVA', font=('Segoe UI', 17, 'bold'), style='Brand.TLabel').pack(side='left')
            ttk.Label(header, text='YT Downloader', font=('Segoe UI', 12), style='Header.TLabel').pack(side='left', padx=(12, 0))
            self.settings_btn = self.button(header, 'settings', self.open_settings, style='Header.TButton')
            self.settings_btn.pack(side='right')
            source = ttk.Frame(root, padding=(16, 6))
            source.pack(fill='x')
            row = ttk.Frame(source)
            row.pack(fill='x')
            self.paste_btn = self.button(row, 'paste', self.paste_link)
            self.paste_btn.pack(side='left', padx=(0, 8))
            self.url_entry = ttk.Entry(row, textvariable=self.url)
            self.url_entry.pack(side='left', fill='x', expand=True)
            self.url_entry.bind('<Return>', lambda event: self.start('append'))
            self.list_btn = self.button(row, 'fetch', lambda: self.start('list'))
            self.list_btn.pack(side='left', padx=(8, 4))
            self.add_btn = self.button(row, 'add', lambda: self.start('append'), style='Accent.TButton')
            self.add_btn.pack(side='left')

            toolbar = ttk.Frame(root, padding=(16, 6), style='Panel.TFrame')
            toolbar.pack(fill='x')
            self.label(toolbar, 'format').pack(side='left', padx=(0, 6))
            self.format_box = ttk.Combobox(toolbar, textvariable=self.fmt, values=['MP4', 'MP3'], state='readonly', width=6)
            self.format_box.pack(side='left')
            self.label(toolbar, 'quality').pack(side='left', padx=(14, 6))
            self.quality_box = ttk.Combobox(toolbar, textvariable=self.quality_display, state='readonly', width=14)
            self.quality_box.pack(side='left')
            self.format_box.bind('<<ComboboxSelected>>', self.format_changed)
            self.quality_box.bind('<<ComboboxSelected>>', lambda e: self.quality.set(self.quality_values[self.quality_box.current()]))
            self.start_btn = self.button(toolbar, 'download', lambda: self.start('download'), style='Primary.TButton')
            self.start_btn.pack(side='left', padx=(16, 6))
            self.stop_btn = self.button(toolbar, 'stop', self.stop, state='disabled')
            self.stop_btn.pack(side='left')
            self.button(toolbar, 'open', self.open_folder).pack(side='right')
            self.button(toolbar, 'log', self.open_log).pack(side='right', padx=(4, 6))

            body = ttk.Frame(root, padding=(16, 8))
            body.pack(fill='both', expand=True)
            library = ttk.Frame(body, padding=10, style='Panel.TFrame')
            library.pack(fill='both', expand=True)
            library.columnconfigure(0, weight=1)
            library.rowconfigure(3, weight=1)
            caption = ttk.Frame(library, style='Panel.TFrame')
            caption.grid(row=0, column=0, sticky='ew')
            self.label(caption, 'queue', font=('Segoe UI', 12, 'bold')).pack(side='left')
            ttk.Label(caption, textvariable=self.selection_text, style='Muted.TLabel').pack(side='right')
            searchrow = ttk.Frame(library, style='Panel.TFrame')
            searchrow.grid(row=1, column=0, sticky='ew', pady=(10, 8))
            self.filter_buttons = []
            for value in ('all', 'waiting', 'completed', 'failed'):
                widget = ttk.Radiobutton(searchrow, text=self.t('queue_' + value), value=value, variable=self.filter_mode,
                                         style='Filter.TRadiobutton', command=self.apply_search)
                self.text_widgets.append((widget, 'queue_' + value))
                widget.pack(side='left', padx=(0, 4))
                self.filter_buttons.append(widget)
            self.button(searchrow, 'clear', lambda: self.search.set(''), style='Toolbar.TButton').pack(side='right')
            self.search_entry = ttk.Entry(searchrow, textvariable=self.search, width=19)
            self.search_entry.pack(side='right', padx=(6, 6), fill='x', expand=True)
            self.label(searchrow, 'search').pack(side='right', padx=(16, 0))
            selection = ttk.Frame(library, style='Panel.TFrame')
            selection.grid(row=2, column=0, sticky='ew', pady=(0, 8))
            self.all_btn = self.button(selection, 'select_all_short', lambda: self.select_all(True), style='Toolbar.TButton')
            self.all_btn.pack(side='left')
            self.results_btn = self.button(selection, 'select_results_short', self.select_visible, style='Toolbar.TButton')
            self.results_btn.pack(side='left', padx=4)
            self.clear_btn = self.button(selection, 'clear_selection_short', lambda: self.select_all(False), style='Toolbar.TButton')
            self.clear_btn.pack(side='left')
            self.failed_btn = self.button(selection, 'failed_selection_short', self.select_failed, style='Toolbar.TButton')
            self.failed_btn.pack(side='left', padx=(4, 0))
            self.remove_btn = self.button(selection, 'remove_short', self.remove_selected, style='Toolbar.TButton')
            self.remove_btn.pack(side='left', padx=4)
            tableframe = ttk.Frame(library, style='Panel.TFrame')
            tableframe.grid(row=3, column=0, sticky='nsew')
            tableframe.columnconfigure(0, weight=1)
            tableframe.rowconfigure(0, weight=1)
            self.table = ttk.Treeview(tableframe, columns=('selected', 'title', 'source', 'duration', 'state'), show='tree headings', selectmode='extended')
            self.table.column('#0', width=66, minwidth=66, stretch=False)
            for col, width in [('selected', 42), ('title', 340), ('source', 130), ('duration', 60), ('state', 210)]:
                self.table.column(col, width=width, minwidth=40 if col != 'title' else 180, stretch=col == 'title')
            self.table.grid(row=0, column=0, sticky='nsew')
            self.table_scroll = ttk.Scrollbar(tableframe, command=self.table.yview)
            self.table_scroll.grid(row=0, column=1, sticky='ns')
            self.table.configure(yscrollcommand=self.table_scrolled)
            self.table.bind('<Button-1>', self.table_click)
            self.table.bind('<Double-1>', self.table_double_click)
            self.table.bind('<space>', self.toggle_highlighted)
            self.table.bind('<Button-3>', self.show_context_menu)
            self.table.bind('<Return>', lambda event: self.open_item())
            self.root.bind('<Control-v>', self.paste_shortcut)
            self.root.bind('<Control-V>', self.paste_shortcut)
            self.empty_label = ttk.Label(tableframe, text=self.t('empty_queue'), style='Muted.TLabel', justify='center')
            progress = ttk.Frame(library, style='Panel.TFrame')
            progress.grid(row=4, column=0, sticky='ew', pady=(6, 0))
            progress.columnconfigure(0, weight=1)
            ttk.Label(progress, textvariable=self.status, style='Panel.TLabel', wraplength=830).grid(row=0, column=0, sticky='w')
            ttk.Label(progress, textvariable=self.detail, style='Muted.TLabel', wraplength=830).grid(row=1, column=0, sticky='w', pady=(3, 5))
            self.current_bar = ttk.Progressbar(progress, maximum=100, style='Slim.Horizontal.TProgressbar')
            self.current_bar.grid(row=2, column=0, sticky='ew')
            ttk.Label(progress, textvariable=self.count, style='Muted.TLabel', wraplength=830).grid(row=3, column=0, sticky='w', pady=(5, 4))
            self.overall_bar = ttk.Progressbar(progress, maximum=100, style='Slim.Horizontal.TProgressbar')
            self.overall_bar.grid(row=4, column=0, sticky='ew')
            footer = ttk.Frame(root, padding=(16, 4))
            # Reserve the footer before the expanding body, including small windows.
            footer.pack(side='bottom', fill='x', before=body)
            self.version_label = ttk.Label(footer, text='Tekniva YT Downloader  ·  ' + VERSION, font=('Segoe UI', 8), style='Footer.TLabel')
            self.version_label.pack(side='left')
            self.instagram_icon = tk.Canvas(footer, width=24, height=24, highlightthickness=0, cursor='hand2', takefocus=True)
            self.instagram_icon.pack(side='left', padx=(10, 0))
            self.instagram_icon.create_line(7, 3, 17, 3, 21, 7, 21, 17, 17, 21, 7, 21, 3, 17, 3, 7, 7, 3,
                                            smooth=True, width=2, fill='#E1306C', tags='logo')
            self.instagram_icon.create_oval(7, 7, 17, 17, outline='#E1306C', width=2, tags='logo')
            self.instagram_icon.create_oval(16, 5, 18, 7, fill='#E1306C', outline='', tags='logo')
            self.instagram_link = ttk.Label(footer, text='Instagram', style='Footer.TLabel', cursor='hand2')
            self.instagram_link.pack(side='left', padx=(4, 0))
            for widget in (self.instagram_icon, self.instagram_link):
                widget.bind('<Button-1>', self.open_instagram)
            self.instagram_icon.bind('<Return>', self.open_instagram)
            self.instagram_icon.bind('<space>', self.open_instagram)
            self.instagram_icon.bind('<FocusIn>', lambda event: self.instagram_icon.configure(highlightthickness=1, highlightbackground='#E1306C'))
            self.instagram_icon.bind('<FocusOut>', lambda event: self.instagram_icon.configure(highlightthickness=0))
            self.search.trace_add('write', self.apply_search)
            self.refresh_language()
            self.apply_theme()
            self.update_selection()
            self.apply_search()
            if self.persistence_enabled:
                self.restore_queue()
            root.protocol('WM_DELETE_WINDOW', self.close)
            root.after(200, self.poll)
            if not test_callback:
                for _ in range(2):
                    threading.Thread(target=self.thumbnail_worker, daemon=True, name='Cover-preview').start()
            self.url_entry.focus_set()
            if test_callback:
                root.withdraw()
                try:
                    test_callback(self)
                finally:
                    root.destroy()
            elif '--gui-smoke' in sys.argv:
                root.after(800, root.destroy)

        def t(self, key, **values):
            return translate(self.language, key, **values)

        def open_instagram(self, event=None):
            webbrowser.open('https://www.instagram.com/tekniva.com.tr/')
            return 'break'

        def label(self, parent, key, **kwargs):
            kwargs.setdefault('style', 'Panel.TLabel')
            widget = ttk.Label(parent, text=self.t(key), **kwargs)
            self.text_widgets.append((widget, key))
            return widget

        def button(self, parent, key, command, **kwargs):
            widget = ttk.Button(parent, text=self.t(key), command=command, **kwargs)
            self.text_widgets.append((widget, key))
            return widget

        def refresh_language(self):
            for widget, key in self.text_widgets:
                widget.configure(text=self.t(key))
            for col in ('selected', 'title', 'source', 'duration', 'state'):
                arrow = (' ▼' if self.sort_reverse else ' ▲') if col == self.sort_column else ''
                self.table.heading(col, text=self.t(col) + arrow, command=lambda c=col: self.sort_by(c))
            self.format_changed()
            for video_id in self.entries:
                self.render_state(video_id)
            self.empty_label.configure(text=self.t('no_results' if self.entries else 'empty_queue'))
            self.status.set(self.t('ready') if not self.entries else self.t('loaded', n=len(self.entries)))
            self.detail.set(self.t('instructions'))
            self.count.set(self.t('empty') if not self.entries else self.t('queue'))
            self.update_selection()
            # Right alignment preserves the natural reading direction for Arabic.
            rtl = self.language == 'ar'
            self.url_entry.configure(justify='right' if rtl else 'left')
            self.search_entry.configure(justify='right' if rtl else 'left')
            self.table.column('title', anchor='e' if rtl else 'w')

        def apply_theme(self):
            dark = self.theme == 'dark'
            bg, panel, fg, muted, field, border = ('#101820', '#1A2632', '#F1F5F9', '#B9C8D7', '#111C27', '#344859') if dark else ('#EDF3F5', '#FFFFFF', '#182E3D', '#536B7A', '#F8FAFC', '#D6E2E8')
            hover = '#263A54' if dark else '#E5EEFA'
            self.root.configure(bg=bg)
            self.instagram_icon.configure(bg=bg)
            s = self.style
            s.configure('.', font=('Nirmala UI' if self.language == 'hi' else 'Segoe UI', 9), background=bg, foreground=fg)
            s.configure('TFrame', background=bg)
            s.configure('Panel.TFrame', background=panel)
            s.configure('TLabel', background=bg, foreground=fg)
            s.configure('Source.TLabel', background=bg, foreground=fg)
            s.configure('SourceMuted.TLabel', background=bg, foreground=muted)
            s.configure('Panel.TLabel', background=panel, foreground=fg)
            s.configure('Muted.TLabel', background=panel, foreground=muted)
            s.configure('Footer.TLabel', background=bg, foreground=muted)
            s.configure('Header.TFrame', background='#102B3B')
            s.configure('Header.TLabel', background='#102B3B', foreground='white')
            s.configure('Brand.TLabel', background='#102B3B', foreground='#59DEC3')
            s.configure('Header.TButton', background='#23495D', foreground='white')
            s.map('Header.TButton', background=[('active', '#315E72')], foreground=[('active', 'white')])
            s.configure('Accent.TButton', background='#D8F4ED' if not dark else '#214D4A', foreground=fg)
            s.configure('TNotebook', background=bg, borderwidth=0, bordercolor=border, lightcolor=border, darkcolor=border)
            s.configure('TNotebook.Tab', padding=(14, 8), background=border, foreground=fg, bordercolor=border, lightcolor=border, darkcolor=border)
            s.map('TNotebook.Tab', background=[('selected', panel)], foreground=[('selected', fg)])
            s.configure('Filter.TRadiobutton', padding=(9, 6), background=panel, foreground=fg)
            s.layout('Filter.TRadiobutton', [('Radiobutton.padding', {'children': [('Radiobutton.label', {'sticky': 'nswe'})], 'sticky': 'nswe'})])
            s.map('Filter.TRadiobutton', background=[('selected', '#237E73'), ('active', hover)], foreground=[('selected', 'white')])
            s.configure('TButton', padding=(7, 6), background=border, foreground=fg, borderwidth=0)
            s.configure('Toolbar.TButton', padding=(5, 6), font=('Nirmala UI' if self.language == 'hi' else 'Segoe UI', 9))
            s.map('TButton', background=[('disabled', panel), ('pressed', '#3B5270' if dark else '#C7DAF5'), ('active', hover)], foreground=[('disabled', '#8C9BAF' if dark else '#64748B'), ('active', fg)])
            s.configure('Primary.TButton', background='#147D70', foreground='white', padding=(12, 8))
            s.map('Primary.TButton', background=[('active', '#11665D'), ('disabled', border)], foreground=[('disabled', muted)])
            s.configure('TEntry', padding=7, fieldbackground=field, foreground=fg, bordercolor=border, lightcolor=border, darkcolor=border, insertcolor=fg)
            s.map('TEntry', bordercolor=[('focus', '#60A5FA')], fieldbackground=[('disabled', panel)], foreground=[('disabled', muted)])
            s.configure('TCombobox', padding=5, fieldbackground=field, background=border, foreground=fg, arrowcolor=fg, bordercolor=border, lightcolor=border, darkcolor=border)
            s.map('TCombobox', fieldbackground=[('disabled', panel), ('readonly', field)], foreground=[('disabled', muted), ('readonly', fg)], background=[('active', hover), ('readonly', border)], arrowcolor=[('disabled', muted), ('active', fg)], bordercolor=[('focus', '#60A5FA')])
            # Clam has light hover/selected defaults: override all indicator states.
            for control in ('TCheckbutton', 'TRadiobutton', 'Mode.TRadiobutton'):
                s.configure(control, background=panel, foreground=fg, padding=(2, 6), indicatorbackground=field, indicatorforeground=fg, bordercolor=border, lightcolor=border, darkcolor=border)
                s.map(control, background=[('disabled', panel), ('active', hover), ('selected', panel)], foreground=[('disabled', muted), ('active', fg), ('selected', fg)], indicatorbackground=[('disabled', border), ('selected', '#2563EB'), ('active', hover)], indicatorforeground=[('disabled', muted), ('selected', '#FFFFFF')])
            s.configure('Mode.TRadiobutton', padding=(10, 9))
            self.root.option_add('*TCombobox*Listbox.background', field)
            self.root.option_add('*TCombobox*Listbox.foreground', fg)
            self.root.option_add('*TCombobox*Listbox.selectBackground', '#2563EB')
            self.root.option_add('*TCombobox*Listbox.selectForeground', '#FFFFFF')
            s.configure('Treeview', rowheight=36, background=panel, fieldbackground=panel, foreground=fg, borderwidth=0,
                        bordercolor=panel, lightcolor=panel, darkcolor=panel)
            s.layout('Treeview.Item', [('Treeitem.padding', {'sticky': 'nswe', 'children': [('Treeitem.image', {'side': 'left', 'sticky': ''}), ('Treeitem.text', {'side': 'left', 'sticky': ''})]})])
            s.configure('Treeview.Heading', padding=6, background=border, foreground=fg, relief='flat',
                        bordercolor=border, lightcolor=border, darkcolor=border)
            s.map('Treeview.Heading', background=[('active', hover)], foreground=[('active', fg)])
            s.map('Treeview', background=[('selected', '#1D4ED8')], foreground=[('selected', '#FFFFFF')])
            s.configure('TProgressbar', background='#1CA995', troughcolor=border, thickness=5)
            s.configure('Slim.Horizontal.TProgressbar', background='#1CA995', troughcolor=border, thickness=5,
                        borderwidth=0, bordercolor=panel, lightcolor=panel, darkcolor=panel)
            self.table.tag_configure('even', background='#203240' if dark else '#F3F8FA')
            self.table.tag_configure('error', foreground='#FDA4AF' if dark else '#BE123C')
            self.table.tag_configure('completed', foreground='#75DEC2' if dark else '#08745C')
            self.dark_titlebar(self.root, dark)
            for window in self.root.winfo_children():
                if isinstance(window, tk.Toplevel):
                    window.configure(bg=bg)
                    self.dark_titlebar(window, dark)

        def dark_titlebar(self, window, enabled):
            if sys.platform != 'win32':
                return
            try:
                import ctypes
                window.update_idletasks()
                handle = ctypes.windll.user32.GetParent(window.winfo_id())
                value = ctypes.c_int(int(enabled))
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 20, ctypes.byref(value), ctypes.sizeof(value))
                if result:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(handle, 19, ctypes.byref(value), ctypes.sizeof(value))
            except (OSError, AttributeError):
                pass

        def open_settings(self):
            if self.process:
                return
            dialog = tk.Toplevel(self.root)
            dialog.title(self.t('settings'))
            dialog.transient(self.root)
            dialog.resizable(False, False)
            icon = Path(getattr(sys, '_MEIPASS', APP_DIR)) / 'app.ico'
            if icon.exists():
                dialog.iconbitmap(str(icon))
            frame = ttk.Frame(dialog, padding=18)
            frame.pack(fill='both', expand=True)
            ttk.Label(frame, text=self.t('settings'), font=('Segoe UI', 16, 'bold')).pack(anchor='w')
            ttk.Label(frame, text=self.t('settings_hint'), wraplength=430).pack(anchor='w', pady=(4, 16))
            tabs = ttk.Notebook(frame)
            tabs.pack(fill='both', expand=True)
            appearance = ttk.Frame(tabs, padding=16, style='Panel.TFrame')
            network = ttk.Frame(tabs, padding=16, style='Panel.TFrame')
            storage = ttk.Frame(tabs, padding=16, style='Panel.TFrame')
            tabs.add(appearance, text=self.t('preferences'))
            tabs.add(network, text=self.t('transfer_settings'))
            tabs.add(storage, text=self.t('storage'))
            ttk.Label(appearance, text=self.t('language'), style='Panel.TLabel').pack(anchor='w')
            language = ttk.Combobox(appearance, values=list(LANGUAGES.values()), state='readonly', width=35)
            language.current(list(LANGUAGES).index(self.language))
            language.pack(fill='x', pady=(5, 18))
            ttk.Label(appearance, text=self.t('theme'), style='Panel.TLabel').pack(anchor='w')
            original_theme = self.theme
            theme = tk.StringVar(value=self.theme)
            modes = ttk.Frame(appearance, style='Panel.TFrame')
            modes.pack(fill='x', pady=(5, 0))
            def preview():
                self.theme = theme.get()
                self.apply_theme()
            self.light_mode_btn = ttk.Radiobutton(modes, text=self.t('light'), value='light', variable=theme, command=preview, style='Mode.TRadiobutton')
            self.dark_mode_btn = ttk.Radiobutton(modes, text=self.t('dark'), value='dark', variable=theme, command=preview, style='Mode.TRadiobutton')
            self.light_mode_btn.pack(side='left', fill='x', expand=True, padx=(0, 6))
            self.dark_mode_btn.pack(side='left', fill='x', expand=True)
            ttk.Label(network, text=self.t('engine'), style='Panel.TLabel').pack(anchor='w')
            self.engine_box = ttk.Combobox(network, values=[self.t('engine_default'), 'aria2'], state='readonly')
            self.engine_box.current(0 if self.engine.get() == 'curl_cffi' else 1)
            self.engine_box.pack(fill='x', pady=(5, 6))
            ttk.Label(network, text=self.t('engine_hint'), style='Muted.TLabel', wraplength=430).pack(anchor='w', pady=(0, 12))
            ttk.Label(network, text=self.t('speed'), style='Panel.TLabel').pack(anchor='w')
            self.speed_box = ttk.Combobox(network, values=[self.t(k) for k in ('automatic', 'fast', 'balanced', 'compatible')], state='readonly')
            self.speed_box.current(SPEED_MODES.index(self.speed_mode.get()) if self.speed_mode.get() in SPEED_MODES else 0)
            self.speed_box.pack(fill='x', pady=(5, 12))
            ttk.Label(network, text=self.t('scope'), style='Panel.TLabel').pack(anchor='w')
            self.scope_box = ttk.Combobox(network, values=[self.t('videos'), self.t('all_tabs')], state='readonly')
            self.scope_box.current(0 if self.scope.get() == 'Yalnızca Videolar sekmesi' else 1)
            self.scope_box.pack(fill='x', pady=(5, 12))
            watch = tk.BooleanVar(value=self.clipboard_watch.get())
            ttk.Checkbutton(network, text=self.t('clipboard_watch'), variable=watch).pack(anchor='w')
            ttk.Label(network, text=self.t('clipboard_hint'), style='Muted.TLabel', wraplength=430).pack(anchor='w', pady=(5, 0))
            ttk.Label(storage, text=self.t('storage'), font=('Segoe UI', 11, 'bold'), style='Panel.TLabel').pack(anchor='w', pady=(0, 12))
            ttk.Label(storage, text=self.t('folder'), style='Panel.TLabel').pack(anchor='w')
            folder = tk.StringVar(value=self.output.get())
            folder_row = ttk.Frame(storage, style='Panel.TFrame')
            folder_row.pack(fill='x', pady=(5, 6))
            self.settings_folder_entry = ttk.Entry(folder_row, textvariable=folder, width=34)
            self.settings_folder_entry.pack(side='left', fill='x', expand=True)
            def choose():
                selected = filedialog.askdirectory(parent=dialog, title=self.t('choose'), initialdir=folder.get() if Path(folder.get()).exists() else str(PROJECT))
                if selected:
                    folder.set(selected)
            ttk.Button(folder_row, text=self.t('choose'), command=choose).pack(side='left', padx=(6, 0))
            subfolders = tk.BooleanVar(value=self.channel_subfolders.get())
            self.settings_subfolder_check = ttk.Checkbutton(storage, text=self.t('channel_subfolders'), variable=subfolders)
            self.settings_subfolder_check.pack(anchor='w', pady=(8, 4))
            artist_folders = tk.BooleanVar(value=self.artist_subfolders.get())
            playlist_folders = tk.BooleanVar(value=self.playlist_subfolders.get())
            self.settings_artist_check = ttk.Checkbutton(storage, text=self.t('artist_subfolders'), variable=artist_folders)
            self.settings_artist_check.pack(anchor='w', pady=(0, 4))
            self.settings_playlist_check = ttk.Checkbutton(storage, text=self.t('playlist_subfolders'), variable=playlist_folders)
            self.settings_playlist_check.pack(anchor='w', pady=(0, 4))
            ttk.Label(storage, text=self.t('folder_order'), style='Muted.TLabel', wraplength=410).pack(anchor='w', pady=(0, 6))
            ttk.Label(storage, text=self.t('folder_hint'), style='Muted.TLabel', wraplength=410).pack(anchor='w', pady=(0, 2))
            def save():
                if not folder.get().strip():
                    messagebox.showerror(self.t('error'), self.t('need_folder'), parent=dialog)
                    return
                self.language = list(LANGUAGES)[language.current()]
                self.theme = theme.get()
                self.output.set(str(Path(folder.get()).expanduser().resolve()))
                self.channel_subfolders.set(subfolders.get())
                self.artist_subfolders.set(artist_folders.get())
                self.playlist_subfolders.set(playlist_folders.get())
                self.engine.set(('curl_cffi', 'aria2')[self.engine_box.current()])
                self.speed_mode.set(SPEED_MODES[self.speed_box.current()])
                self.scope.set(['Yalnızca Videolar sekmesi', 'Videolar + Shorts + yayın kayıtları'][self.scope_box.current()])
                self.clipboard_watch.set(watch.get())
                self.actual_folder = None
                self.save_settings()
                self.refresh_language()
                self.apply_theme()
                dialog.destroy()
            def cancel():
                self.theme = original_theme
                self.apply_theme()
                dialog.destroy()
            actions = ttk.Frame(frame)
            actions.pack(fill='x', pady=(16, 0))
            self.settings_save_btn = ttk.Button(actions, text=self.t('save'), command=save, style='Primary.TButton')
            self.settings_save_btn.pack(side='right', padx=(6, 0))
            self.settings_cancel_btn = ttk.Button(actions, text=self.t('cancel'), command=cancel)
            self.settings_cancel_btn.pack(side='right')
            dialog.protocol('WM_DELETE_WINDOW', cancel)
            dialog.bind('<Escape>', lambda event: cancel())
            self.apply_theme()
            dialog.update_idletasks()
            x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dialog.winfo_reqwidth()) // 2)
            y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dialog.winfo_reqheight()) // 2)
            dialog.geometry(f'+{x}+{y}')
            dialog.grab_set()
            return dialog

        def clipboard_link(self):
            try:
                raw = self.root.clipboard_get().strip()
                _, url = normalize_source(raw)
                return raw, url
            except (tk.TclError, ValueError):
                return None

        def thumbnail_worker(self):
            from PIL import Image, ImageOps
            from curl_cffi import requests
            while True:
                job = self.thumbnail_jobs.get()
                if job is None:
                    return
                video_id, url = job
                try:
                    # Preview requests only use thumbnail hosts supplied by YouTube.
                    parsed = urlparse(url)
                    host = parsed.hostname or ''
                    if parsed.scheme != 'https' or not (host in ('i.ytimg.com', 'img.youtube.com') or host.endswith('.googleusercontent.com')):
                        continue
                    with requests.get(url, stream=True, timeout=5) as response:
                        response.raise_for_status()
                        data = bytearray()
                        for chunk in response.iter_content():
                            data.extend(chunk)
                            if len(data) > 3 * 1024**2:
                                raise ValueError('Preview too large')
                    with Image.open(io.BytesIO(data)) as image:
                        preview = ImageOps.fit(image.convert('RGB'), (54, 32))
                    self.thumbnail_results.put((video_id, preview))
                except Exception:
                    # A missing cover never interrupts listing or downloading.
                    pass

        def table_scrolled(self, first, last):
            self.table_scroll.set(first, last)
            self.request_previews(int(float(first) * len(self.visible_ids)))

        def request_previews(self, start=0):
            if not self.persistence_enabled:
                return
            for video_id in self.visible_ids[start:start + 30]:
                if video_id not in self.thumbnail_requested:
                    entry = self.entries[video_id]
                    url = entry.get('thumbnail') or f'https://i.ytimg.com/vi/{video_id}/mqdefault.jpg'
                    self.thumbnail_requested.add(video_id)
                    self.thumbnail_jobs.put((video_id, url))

        def poll_previews(self):
            from PIL import ImageTk
            while not self.thumbnail_results.empty():
                video_id, preview = self.thumbnail_results.get()
                if video_id in self.entries and self.table.exists(video_id):
                    image = ImageTk.PhotoImage(preview, master=self.root)
                    self.thumbnail_images[video_id] = image
                    self.table.item(video_id, image=image)

        def paste_link(self, event=None):
            if self.process or self.installing:
                return 'break'
            value = self.clipboard_link()
            if not value:
                self.status.set(self.t('clipboard_empty'))
                return 'break'
            self.last_clipboard = value[0]
            self.url.set(value[1])
            self.start('append')
            return 'break'

        def paste_shortcut(self, event):
            # Entry widgets retain normal text-paste behavior.
            if event.widget in (self.url_entry, self.search_entry) or isinstance(event.widget, (ttk.Entry, ttk.Combobox)):
                return None
            return self.paste_link()

        def poll_clipboard(self):
            if not self.clipboard_watch.get() or self.process or self.installing:
                return
            now = time.monotonic()
            if now - getattr(self, 'clipboard_checked', 0) < 2:
                return
            self.clipboard_checked = now
            value = self.clipboard_link()
            if value and value[0] != self.last_clipboard:
                self.last_clipboard = value[0]
                self.url.set(value[1])
                self.start('append')

        def open_item(self, video_id=None):
            selected = self.table.selection()
            video_id = video_id or (selected[0] if selected else None)
            if video_id not in self.entries:
                return
            filename = self.entries[video_id].get('filepath')
            if filename and Path(filename).is_file():
                os.startfile(filename)
            else:
                self.status.set(self.t('file_missing'))

        def show_context_menu(self, event):
            video_id = self.table.identify_row(event.y)
            if not video_id:
                return
            self.table.selection_set(video_id)
            if getattr(self, 'context_menu', None):
                self.context_menu.destroy()
            menu = self.context_menu = tk.Menu(self.root, tearoff=False,
                           background='#1A2632' if self.theme == 'dark' else '#FFFFFF',
                           foreground='#F1F5F9' if self.theme == 'dark' else '#182E3D',
                           activebackground='#147D70', activeforeground='white')
            menu.add_command(label=self.t('open_file'), command=lambda: self.open_item(video_id),
                             state='normal' if self.entries[video_id].get('filepath') else 'disabled')
            def open_source():
                try:
                    _, url = normalize_source(self.entries[video_id]['url'])
                    webbrowser.open(url)
                except (KeyError, ValueError):
                    pass
            menu.add_command(label=self.t('open_source'), command=open_source)
            menu.add_separator()
            def remove():
                self.selected_ids = {video_id}
                self.remove_selected()
            menu.add_command(label=self.t('remove_short'), command=remove, state='disabled' if self.process else 'normal')
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        def save_settings(self):
            self.settings = {'url': self.url.get(), 'output': self.output.get(), 'channel_subfolders': self.channel_subfolders.get(), 'artist_subfolders': self.artist_subfolders.get(), 'playlist_subfolders': self.playlist_subfolders.get(), 'format': self.fmt.get(), 'quality': self.quality.get(), 'scope': self.scope.get(), 'speed': self.speed_mode.get(), 'engine': self.engine.get(), 'clipboard_watch': self.clipboard_watch.get(), 'language': self.language, 'theme': self.theme}
            if not self.persistence_enabled:
                return
            self.config_file.write_text(json.dumps(self.settings, ensure_ascii=False, indent=2), encoding='utf-8')

        def save_queue(self):
            if not self.persistence_enabled:
                return
            data = {'entries': list(self.entries.values()), 'selected': list(self.selected_ids), 'states': self.states, 'channel': self.channel_title}
            temporary = self.queue_file.with_suffix('.tmp')
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(self.queue_file)

        def restore_queue(self):
            try:
                data = json.loads(self.queue_file.read_text(encoding='utf-8'))
                restored = []
                for entry in data['entries']:
                    kind, url = normalize_source(entry['url'])
                    if kind != 'video' or url.split('v=')[-1] != entry['id']:
                        continue
                    restored.append({**entry, 'url': url})
                self.action = 'restore'
                self.handle({'kind': 'list', 'entries': restored, 'channel': data.get('channel', ''), 'folder': self.output.get(), 'skipped_live': 0})
                self.channel_title = data.get('channel', '')
                self.selected_ids = set(data.get('selected', [])) & set(self.entries)
                for i in self.entries:
                    state, percent = data.get('states', {}).get(i, ['waiting', 0])
                    self.set_state(i, state if state in ('completed', 'skipped', 'failed', 'stopped') else 'waiting', percent)
                self.render_selection()
                self.status.set(self.t('loaded', n=len(self.entries)))
                self.action = None
            except (OSError, ValueError, KeyError, TypeError):
                pass

        def source_key(self):
            source_type, url = normalize_source(self.url.get())
            return url, self.scope.get() if source_type == 'channel' else 'video'

        def invalidate_list(self, *args):
            # Explicit reset only: typing the next link must preserve the queue.
            if self.process:
                return
            self.table.delete(*(i for i in self.entries if self.table.exists(i)))
            self.entries.clear()
            self.thumbnail_images.clear()
            self.thumbnail_requested.clear()
            self.states.clear()
            self.selected_ids.clear()
            self.visible_ids.clear()
            self.loaded_key = None
            self.actual_folder = None
            self.update_selection()

        def update_selection(self):
            self.selection_text.set(self.t('summary', total=len(self.entries), visible=len(self.visible_ids), selected=len(self.selected_ids)))
            self.start_btn.configure(state='normal' if self.entries and self.selected_ids and not self.process and not self.installing else 'disabled')
            for widget in (self.all_btn, self.clear_btn, self.results_btn, self.remove_btn):
                widget.configure(state='normal' if self.entries and not self.process and not self.installing else 'disabled')
            self.failed_btn.configure(state='normal' if any(s[0] == 'failed' for s in self.states.values()) and not self.process and not self.installing else 'disabled')

        def apply_search(self, *args):
            words = search_text(self.search.get()).split()
            self.visible_ids = []
            for video_id, entry in self.entries.items():
                if not self.table.exists(video_id):
                    continue
                state = self.states.get(video_id, ('waiting', 0))[0]
                group = self.filter_mode.get()
                matches = group == 'all' or (group == 'waiting' and state in ('waiting', 'stopped', 'preparing', 'downloading', 'processing')) or (group == 'completed' and state in ('completed', 'skipped')) or (group == 'failed' and state == 'failed')
                haystack = search_text(entry['title'] + ' ' + (entry.get('artist') or entry.get('channel') or ''))
                if matches and all(word in haystack for word in words):
                    self.table.move(video_id, '', 'end')
                    self.visible_ids.append(video_id)
                else:
                    self.table.detach(video_id)
            self.reorder()
            self.request_previews()
            self.empty_label.configure(text=self.t('no_results' if self.entries else 'empty_queue'))
            if not self.visible_ids:
                self.empty_label.place(relx=.5, rely=.45, anchor='center')
            else:
                self.empty_label.place_forget()
            self.update_selection()

        def sort_by(self, column):
            self.sort_reverse = not self.sort_reverse if column == self.sort_column else False
            self.sort_column = column
            self.reorder()
            for col in ('selected', 'title', 'source', 'duration', 'state'):
                arrow = (' ▼' if self.sort_reverse else ' ▲') if col == self.sort_column else ''
                self.table.heading(col, text=self.t(col) + arrow)

        def reorder(self):
            if not self.sort_column:
                return
            col = self.sort_column
            def key(i):
                if col == 'duration':
                    return self.entries[i].get('duration') or 0
                if col == 'selected':
                    return i in self.selected_ids
                if col == 'state':
                    state, percent = self.states.get(i, ('waiting', 0))
                    return (['waiting', 'preparing', 'downloading', 'processing', 'completed', 'skipped', 'stopped', 'failed'].index(state), percent)
                return search_text((self.entries[i].get('artist') or self.entries[i].get('channel') or '') if col == 'source' else self.entries[i]['title'])
            self.visible_ids.sort(key=key, reverse=self.sort_reverse)
            for i in self.visible_ids:
                self.table.move(i, '', 'end')

        def select_visible(self):
            if not self.process:
                self.selected_ids.update(self.visible_ids)
                self.render_selection()

        def select_failed(self):
            if not self.process:
                self.selected_ids = {i for i, state in self.states.items() if state[0] == 'failed'}
                self.render_selection()

        def select_all(self, selected):
            if not self.process:
                self.selected_ids = set(self.entries) if selected else set()
                self.render_selection()

        def render_selection(self):
            for i in self.entries:
                self.table.set(i, 'selected', '☑' if i in self.selected_ids else '☐')
            self.reorder()
            self.update_selection()
            self.save_queue()

        def toggle(self, video_id):
            if self.process or video_id not in self.entries:
                return
            self.selected_ids.symmetric_difference_update({video_id})
            self.render_selection()

        def table_click(self, event):
            if self.table.identify_region(event.x, event.y) == 'cell' and self.table.identify_column(event.x) == '#1':
                self.toggle(self.table.identify_row(event.y))
                return 'break'

        def table_double_click(self, event):
            if self.table.identify_region(event.x, event.y) == 'cell':
                if self.table.identify_column(event.x) != '#1':
                    video_id = self.table.identify_row(event.y)
                    if self.states.get(video_id, ('waiting', 0))[0] in ('completed', 'skipped'):
                        self.open_item(video_id)
                    else:
                        self.toggle(video_id)
                return 'break'

        def toggle_highlighted(self, event=None):
            for i in self.table.selection():
                self.toggle(i)
            return 'break'

        def remove_selected(self):
            if self.process:
                return
            for i in list(self.selected_ids):
                self.table.delete(i)
                self.entries.pop(i, None)
                self.thumbnail_images.pop(i, None)
                self.thumbnail_requested.discard(i)
                self.states.pop(i, None)
            self.selected_ids.clear()
            self.apply_search()
            self.save_queue()

        def format_changed(self, event=None):
            self.quality_values = AUDIO_QUALITIES if self.fmt.get() == 'MP3' else VIDEO_QUALITIES
            if self.quality.get() not in self.quality_values:
                self.quality.set(self.quality_values[0])
            self.quality_box.configure(values=[self.t('best') if q == 'En yüksek' else q for q in self.quality_values])
            self.quality_box.current(self.quality_values.index(self.quality.get()))

        def choose_folder(self):
            path = filedialog.askdirectory(title=self.t('choose'), initialdir=self.output.get() if Path(self.output.get()).exists() else str(PROJECT))
            if path:
                self.output.set(path)

        def busy(self, active):
            for widget in (self.list_btn, self.add_btn, self.paste_btn, self.url_entry, self.settings_btn):
                widget.configure(state='disabled' if active else 'normal')
            for widget in (self.format_box, self.quality_box):
                widget.configure(state='disabled' if active else 'readonly')
            self.stop_btn.configure(state='normal' if active else 'disabled')
            self.update_selection()

        def offer_node_install(self, action):
            if not messagebox.askyesno(self.t('dependencies'), self.t('node_install_question'), parent=self.root):
                self.status.set(self.t('node_install_declined'))
                return
            self.installing = True
            self.install_action = action
            self.install_cancel.clear()
            self.busy(True)
            self.stop_btn.configure(state='disabled')
            dialog = tk.Toplevel(self.root)
            self.install_dialog = dialog
            dialog.title(self.t('dependencies'))
            dialog.transient(self.root)
            dialog.resizable(False, False)
            frame = ttk.Frame(dialog, padding=20)
            frame.pack(fill='both', expand=True)
            ttk.Label(frame, text='Node.js', font=('Segoe UI', 14, 'bold')).pack(anchor='w')
            self.install_label = ttk.Label(frame, text=self.t('node_install_downloading', percent=0), wraplength=380)
            self.install_label.pack(anchor='w', pady=(10, 8))
            self.install_bar = ttk.Progressbar(frame, maximum=100, length=380)
            self.install_bar.pack(fill='x')
            self.install_cancel_btn = ttk.Button(frame, text=self.t('cancel'), command=self.cancel_node_install)
            self.install_cancel_btn.pack(anchor='e', pady=(12, 0))
            dialog.protocol('WM_DELETE_WINDOW', self.cancel_node_install)
            dialog.bind('<Escape>', lambda event: self.cancel_node_install())
            self.apply_theme()
            dialog.grab_set()
            self.status.set(self.t('node_install_downloading', percent=0))

            def worker():
                try:
                    install_node(APP_DIR, lambda phase, percent: self.install_events.put(('progress', phase, percent)), self.install_cancel)
                    self.install_events.put(('done',))
                except InstallCancelled:
                    self.install_events.put(('cancelled',))
                except Exception as error:
                    self.install_events.put(('failed', str(error)))
            threading.Thread(target=worker, name='Node-runtime-install', daemon=True).start()

        def cancel_node_install(self):
            self.install_cancel.set()
            self.install_cancel_btn.configure(state='disabled')
            self.install_label.configure(text=self.t('stopping'))

        def poll_install(self):
            while not self.install_events.empty():
                event = self.install_events.get()
                if event[0] == 'progress':
                    if not self.install_cancel.is_set():
                        text = self.t('node_install_verifying') if event[1] == 'verify' else self.t('node_install_downloading', percent=f'{event[2]:.0f}')
                        self.install_label.configure(text=text)
                        self.install_bar['value'] = event[2]
                        self.status.set(text)
                    continue
                self.installing = False
                if self.install_dialog:
                    self.install_dialog.grab_release()
                    self.install_dialog.destroy()
                    self.install_dialog = None
                self.busy(False)
                if event[0] == 'done' and not self.install_cancel.is_set():
                    self.root.after(0, lambda action=self.install_action: self.start(action))
                elif event[0] == 'failed':
                    self.status.set(self.t('error'))
                    messagebox.showerror(self.t('dependencies'), self.t('node_install_failed', error=event[1]), parent=self.root)
                else:
                    self.status.set(self.t('stopped'))

        def start(self, action):
            if self.process or self.installing:
                return
            try:
                selected_entries = []
                if action == 'download':
                    selected_entries = [entry for i, entry in self.entries.items() if i in self.selected_ids]
                    if not selected_entries:
                        raise ValueError(self.t('need_selection'))
                    url = selected_entries[0]['url']
                else:
                    try:
                        _, url = normalize_source(self.url.get())
                    except ValueError:
                        raise ValueError(self.t('invalid_link'))
                if not self.output.get().strip():
                    raise ValueError(self.t('need_folder'))
                folder = Path(self.output.get()).expanduser().resolve()
                folder.mkdir(parents=True, exist_ok=True)
                if action == 'download' and shutil.disk_usage(folder).free < 3 * 1024**3:
                    raise ValueError(self.t('disk'))
                if not node_path(APP_DIR):
                    self.offer_node_install(action)
                    return
                self.save_settings()
                job_dir = APP_DIR / 'islem-kayitlari'
                job_dir.mkdir(exist_ok=True)
                token = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6]
                events_file = job_dir / (token + '.events.jsonl')
                log_file = job_dir / (token + '.log')
                job_path = job_dir / (token + '.json')
                job = {**self.settings, 'url': url, 'output': str(folder), 'action': 'download' if action == 'download' else 'list', 'all_tabs': self.scope.get() != 'Yalnızca Videolar sekmesi', 'events': str(events_file), 'log': str(log_file)}
                if action == 'download':
                    job.update(selected_entries=selected_entries, channel_title=self.channel_title or self.t('queue'))
                job_path.write_text(json.dumps(job, ensure_ascii=False), encoding='utf-8')
                command = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, str(APP_DIR / 'kanal_indirici.py')]
                self.process = subprocess.Popen(command + ['--worker', str(job_path)], creationflags=NO_WINDOW, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.events_file, self.log_file = events_file, log_file
            except (OSError, ValueError) as error:
                messagebox.showerror(self.t('error'), str(error))
                return
            self.append_mode = action == 'append'
            self.action = 'list' if action in ('list', 'append') else 'download'
            self.event_offset = 0
            self.event_buffer = ''
            self.got_final = self.stopping = False
            self.last_error_hint = None
            self.current_id = None
            if self.action == 'list':
                # Clear stale search immediately; old queue survives failed extraction.
                self.search.set('')
            self.current_bar['value'] = self.overall_bar['value'] = 0
            self.status.set(self.t('loading') if self.action == 'list' else self.t('preparing'))
            self.detail.set(self.t('instructions'))
            self.count.set(self.t('queue'))
            self.busy(True)

        def set_state(self, video_id, state, percent=0):
            if video_id in self.entries:
                self.states[video_id] = (state, percent)
                self.render_state(video_id)
                if self.filter_mode.get() != 'all':
                    self.apply_search()
                elif self.sort_column == 'state':
                    self.reorder()

        def render_state(self, video_id):
            if self.table.exists(video_id):
                state, percent = self.states.get(video_id, ('waiting', 0))
                self.table.set(video_id, 'state', self.t('processing_percent' if state == 'processing' and percent else state, percent=f'{percent:.0f}'))
                if state == 'failed':
                    self.table.item(video_id, tags=('error',))
                else:
                    index = list(self.entries).index(video_id)
                    self.table.item(video_id, tags=(('even',) if index % 2 == 0 else ()) + (('completed',) if state in ('completed', 'skipped') else ()))

        def handle(self, event):
            kind = event['kind']
            if kind == 'list':
                self.actual_folder = event['folder']
                if self.action == 'list':
                    self.filter_mode.set('all')
                    self.search.set('')
                    if not self.append_mode:
                        self.table.delete(*(i for i in self.entries if self.table.exists(i)))
                        self.entries.clear()
                        self.thumbnail_images.clear()
                        self.thumbnail_requested.clear()
                        self.states.clear()
                        self.selected_ids.clear()
                        self.visible_ids.clear()
                    self.loaded_key = self.source_key()
                    self.channel_title = self.t('queue') if self.append_mode else event['channel']
                for item in event['entries']:
                    i = item['id']
                    if 'url' not in item:
                        host = 'music.youtube.com' if 'music.youtube.com' in self.url.get() else 'www.youtube.com'
                        item = {**item, 'url': f'https://{host}/watch?v={i}'}
                    if i not in self.entries:
                        self.entries[i] = item
                        duration = int(item.get('duration') or 0)
                        duration_text = f'{duration//3600}:{duration//60%60:02}:{duration%60:02}' if duration >= 3600 else f'{duration//60}:{duration%60:02}' if duration else '—'
                        self.table.insert('', 'end', iid=i, values=('☐', item['title'], item.get('artist') or item.get('channel') or '', duration_text, ''))
                        self.set_state(i, 'waiting')
                    if self.action == 'list' and (self.append_mode or normalize_source(self.url.get())[0] == 'video'):
                        self.selected_ids.add(i)
                    if self.action == 'download':
                        self.set_state(i, 'waiting')
                self.render_selection()
                self.apply_search()
                self.count.set(self.t('loaded', n=len(self.entries)))
            elif kind == 'status':
                text = event.get('text', '')
                if event.get('code') == 'cover':
                    self.status.set(self.t('cover'))
                    self.set_state(self.current_id, 'processing')
                elif event.get('code') == 'queue_pause':
                    self.status.set(self.t('queue_pause'))
                elif 'birleştir' in text or 'Ses hazırlan' in text:
                    self.status.set(self.t('processing'))
                    self.set_state(self.current_id, 'processing')
                elif 'yeniden' in text:
                    self.status.set(self.t('retry'))
                    self.set_state(self.current_id, 'preparing')
                else:
                    self.status.set(self.t('loading') if self.action == 'list' else self.t('preparing'))
            elif kind == 'current':
                if event.get('folder'):
                    self.actual_folder = event['folder']
                self.current_id = event['id']
                self.status.set(event['title'])
                self.detail.set(self.t('preparing'))
                self.current_bar['value'] = 0
                self.set_state(self.current_id, 'preparing')
                if self.current_id in self.visible_ids:
                    self.table.see(self.current_id)
            elif kind == 'processing':
                percent = event.get('percent')
                self.current_bar['value'] = percent or 0
                self.set_state(self.current_id, 'processing', percent or 0)
                self.status.set(self.t('cover') if event.get('phase') == 'cover' else self.t('processing'))
                self.detail.set(self.t('processing_progress', percent=f'{percent:.0f}', seconds=int(event.get('elapsed') or 0))
                                if percent is not None else self.t('processing_elapsed', seconds=int(event.get('elapsed') or 0)))
            elif kind == 'progress':
                percent = event['percent']
                self.current_bar['value'] = percent
                self.set_state(self.current_id, 'downloading', percent)
                eta = event.get('eta')
                remaining = f'{int(eta)//60}:{int(eta)%60:02}' if eta is not None else '—'
                self.detail.set(self.t('progress', percent=f'{percent:.0f}', speed=f"{(event.get('speed') or 0)/1024**2:.1f}", eta=remaining))
            elif kind == 'item':
                state = {'Tamamlandı': 'completed', 'Zaten indirildi': 'skipped', 'Hata': 'failed'}[event['state']]
                if event.get('filepath') and event['id'] in self.entries:
                    self.entries[event['id']]['filepath'] = event['filepath']
                self.set_state(event['id'], state, 100 if state in ('completed', 'skipped') else 0)
                if event.get('error'):
                    self.last_error_hint = self.t('error_' + event.get('error_code', 'network'))
                    self.detail.set(self.last_error_hint)
            elif kind == 'overall':
                self.overall_bar['value'] = event['processed'] / event['total'] * 100 if event['total'] else 0
                self.count.set(self.t('overall', **{k: event[k] for k in ('processed', 'total', 'completed', 'skipped', 'failed')}))
            elif kind in ('done', 'fatal'):
                self.got_final = True
                self.status.set(self.t('loaded', n=len(self.entries)) if kind == 'done' and self.action == 'list' else self.t('done_with_errors', n=event['failed']) if kind == 'done' and event.get('failed') else self.t('done') if kind == 'done' else self.t('error'))
                self.detail.set(self.last_error_hint or self.t('instructions') if kind == 'done' else self.t('error_' + event.get('error_code', 'network')))
                if kind == 'done' and self.action == 'download':
                    self.current_id = None
                self.save_queue()

        def poll(self):
            self.poll_install()
            self.poll_previews()
            self.poll_clipboard()
            if self.events_file and self.events_file.exists():
                with self.events_file.open('r', encoding='utf-8') as handle:
                    handle.seek(self.event_offset)
                    self.event_buffer += handle.read()
                    self.event_offset = handle.tell()
                lines = self.event_buffer.split('\n')
                self.event_buffer = lines.pop()
                for line in lines:
                    if line:
                        try:
                            self.handle(json.loads(line))
                        except (ValueError, KeyError):
                            self.status.set(self.t('error'))
                            self.detail.set(self.t('details_log'))
            if self.process and self.process.poll() is not None:
                # A worker can finish between the event read and process check. Drain next tick.
                if not self.got_final and not self.stopping:
                    if not getattr(self, 'exit_pending', False):
                        self.exit_pending = True
                        self.root.after(100, self.poll)
                        return
                    self.status.set(self.t('error'))
                    self.detail.set(self.t('details_log'))
                if self.stopping:
                    self.status.set(self.t('stopped'))
                    for i, (state, percent) in list(self.states.items()):
                        if state in ('preparing', 'downloading', 'processing'):
                            self.set_state(i, 'stopped', percent)
                self.exit_pending = False
                self.process = None
                self.busy(False)
            self.root.after(200, self.poll)

        def stop(self):
            if self.process and self.process.poll() is None:
                self.stopping = True
                self.stop_btn.configure(state='disabled')
                self.status.set(self.t('stopping'))
                subprocess.Popen(['taskkill', '/PID', str(self.process.pid), '/T', '/F'], creationflags=NO_WINDOW, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        def open_folder(self):
            folder = Path(self.actual_folder or self.output.get())
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))

        def open_log(self):
            if self.log_file and self.log_file.exists():
                os.startfile(str(self.log_file))
            else:
                messagebox.showinfo(self.t('log'), self.t('no_log'))

        def close(self):
            if self.installing:
                self.cancel_node_install()
                return
            if self.process and self.process.poll() is None:
                if not messagebox.askyesno(self.t('close'), self.t('close_question')):
                    return
                subprocess.run(['taskkill', '/PID', str(self.process.pid), '/T', '/F'], creationflags=NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                self.save_settings()
                self.save_queue()
            except OSError:
                pass
            self.root.destroy()
            for _ in range(2):
                self.thumbnail_jobs.put(None)

    root = tk.Tk()
    App(root)
    if not test_callback:
        root.mainloop()
