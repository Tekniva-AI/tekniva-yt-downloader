"""Local Windows channel downloader. GUI and isolated, stoppable worker."""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import unicodedata
import socket
import secrets
import hashlib
from pathlib import Path
from urllib.parse import urlparse, parse_qs

APP_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
from dependencies import node_path, node_runtime_options, install_node
PROJECT = APP_DIR.parent
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
VIDEO_QUALITIES = ['En yüksek', '2160p (4K)', '1440p (2K)', '1080p', '720p', '480p', '360p']
AUDIO_QUALITIES = ['320 kbps', '192 kbps', '128 kbps']
SPEED_MODES = ['Hızlı (8 bağlantı)', 'Dengeli (4 bağlantı)', 'Uyumlu (1 bağlantı)']


def search_text(value):
    return ''.join(char for char in unicodedata.normalize('NFKD', value.casefold().replace('ı', 'i')) if not unicodedata.combining(char))


def aria2_path():
    bundled = Path(getattr(sys, '_MEIPASS', APP_DIR)) / 'tools' / 'aria2c.exe'
    return str(bundled) if bundled.exists() else shutil.which('aria2c')


def normalize_source(value):
    value = value.strip()
    if value.startswith('@'):
        return 'channel', normalize_channel(value)
    if '://' not in value:
        value = 'https://' + value
    parsed = urlparse(value)
    if parsed.scheme not in ('https', 'http'):
        raise ValueError('Bir YouTube kanal veya video linki girin.')
    parts = [part for part in parsed.path.split('/') if part]
    video_id = None
    if parsed.hostname in ('youtu.be', 'www.youtu.be'):
        video_id = parts[0] if len(parts) == 1 else ''
    elif parsed.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        query = parse_qs(parsed.query)
        if parts == ['playlist']:
            playlist_id = query.get('list', [''])[0]
            if not re.fullmatch(r'[A-Za-z0-9_-]+', playlist_id):
                raise ValueError('Çalma listesi linki geçersiz.')
            host = 'music.youtube.com' if parsed.hostname == 'music.youtube.com' else 'www.youtube.com'
            return 'playlist', f'https://{host}/playlist?list={playlist_id}'
        if parsed.hostname == 'music.youtube.com' and len(parts) == 2 and parts[0] == 'browse':
            browse_id = parts[1]
            if browse_id.startswith('MPRE') and re.fullmatch(r'[A-Za-z0-9_-]+', browse_id):
                return 'playlist', 'https://music.youtube.com/browse/' + browse_id
            if browse_id.startswith('VL') and re.fullmatch(r'[A-Za-z0-9_-]+', browse_id[2:]):
                return 'playlist', 'https://music.youtube.com/playlist?list=' + browse_id[2:]
            if browse_id.startswith('UC') and re.fullmatch(r'[A-Za-z0-9_-]+', browse_id):
                return 'channel', 'https://www.youtube.com/channel/' + browse_id
            raise ValueError('Desteklenen bir YouTube Music şarkı, albüm veya çalma listesi linki girin.')
        if parts == ['watch']:
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        elif len(parts) == 2 and parts[0] in ('shorts', 'live', 'embed'):
            video_id = parts[1]
    else:
        raise ValueError('Bir YouTube kanal veya video linki girin.')
    if video_id is not None:
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            raise ValueError('Video linkindeki video kimliği geçersiz.')
        # Remove playlist parameters so a video link always means one video.
        host = 'music.youtube.com' if parsed.hostname == 'music.youtube.com' else 'www.youtube.com'
        return 'video', f'https://{host}/watch?v=' + video_id
    if parsed.hostname == 'music.youtube.com':
        value = 'https://www.youtube.com' + parsed.path
    return 'channel', normalize_channel(value)


def normalize_channel(value):
    value = value.strip()
    if value.startswith('@'):
        value = 'https://www.youtube.com/' + value
    if '://' not in value:
        value = 'https://' + value
    parsed = urlparse(value)
    if parsed.scheme not in ('https', 'http') or parsed.hostname not in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        raise ValueError('Bir YouTube kanal linki veya @kanal adı girin.')
    parts = [part for part in parsed.path.split('/') if part]
    if parts and parts[0].startswith('@') and len(parts[0]) > 1:
        base = parts[0]
        tail = parts[1:]
    elif len(parts) >= 2 and parts[0] in ('channel', 'c', 'user'):
        base = '/'.join(parts[:2])
        tail = parts[2:]
    else:
        raise ValueError('Video linki yerine kanal linkini yapıştırın. Örnek: youtube.com/@UHFklip')
    if tail and tail != ['videos'] and tail != ['shorts'] and tail != ['streams'] and tail != ['featured']:
        raise ValueError('Geçerli bir YouTube kanal linki girin.')
    return 'https://www.youtube.com/' + base


def get_entries(job, logger):
    import yt_dlp
    if job['action'] == 'download':
        requested = job.get('selected_entries')
        if not requested:
            raise ValueError('İndirmek için listeden en az bir video seçin.')
        entries, seen = [], set()
        for item in requested:
            video_id = item.get('id', '')
            if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
                raise ValueError('Seçilen video kimliği geçersiz.')
            if video_id not in seen:
                seen.add(video_id)
                host = 'music.youtube.com' if urlparse(item.get('url') or job['url']).hostname == 'music.youtube.com' else 'www.youtube.com'
                entries.append({'id': video_id, 'title': item.get('title') or video_id,
                                'duration': item.get('duration'), 'channel': item.get('channel') or job.get('channel_title') or 'Kanal',
                                'artist': item.get('artist'), 'playlist_title': item.get('playlist_title'),
                                'url': f'https://{host}/watch?v=' + video_id})
        return entries, job.get('channel_title') or 'Videolar', 0
    source_type, base = normalize_source(job['url'])
    entries, seen = [], set()
    channel_title, skipped_live = '', 0
    with yt_dlp.YoutubeDL({'extract_flat': 'in_playlist', 'skip_download': True, 'noplaylist': source_type != 'playlist',
                          'logger': logger, 'socket_timeout': 25, 'js_runtimes': node_runtime_options(APP_DIR)}) as ydl:
        urls = [base] if source_type != 'channel' else [base + '/' + tab for tab in (['videos', 'shorts', 'streams'] if job['all_tabs'] else ['videos'])]
        for url in urls:
            try:
                info = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as error:
                if source_type == 'channel' and 'does not have a' in str(error) and 'tab' in str(error):
                    continue
                raise
            channel_title = channel_title or (info.get('title') if source_type == 'playlist' else None) or info.get('channel') or info.get('uploader') or re.sub(r' - (Videos|Shorts|Live|Streams)$', '', info.get('title', 'Videolar'))
            for entry in ([info] if source_type == 'video' else info.get('entries', [])):
                if not entry or not entry.get('id') or entry['id'] in seen:
                    continue
                seen.add(entry['id'])
                if entry.get('live_status') in ('is_live', 'is_upcoming'):
                    skipped_live += 1
                    continue
                host = 'music.youtube.com' if urlparse(base).hostname == 'music.youtube.com' else 'www.youtube.com'
                entries.append({'id': entry['id'], 'title': entry.get('title') or entry['id'],
                                'duration': entry.get('duration'), 'channel': entry.get('channel') or entry.get('uploader') or info.get('channel') or info.get('uploader') or channel_title,
                                'artist': entry.get('artist') or ', '.join(entry.get('artists') or []),
                                'playlist_title': info.get('title') if source_type == 'playlist' else None,
                                'url': f'https://{host}/watch?v=' + entry['id']})
    return entries, channel_title, skipped_live


def make_options(job, folder, logger, hooks):
    import imageio_ffmpeg
    options = {
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
        'js_runtimes': node_runtime_options(APP_DIR),
        'outtmpl': str(folder / '%(title).180B.%(ext)s'),
        'windowsfilenames': True,
        'download_archive': str(metadata_paths(folder, job)['archive']),
        'continuedl': True, 'overwrites': False,
        'retries': 8, 'fragment_retries': 8, 'extractor_retries': 3,
        'retry_sleep_functions': {'http': lambda n: min(2 ** n, 20), 'fragment': lambda n: min(2 ** n, 20)},
        'skip_unavailable_fragments': False,
        'concurrent_fragment_downloads': 8 if job.get('speed', SPEED_MODES[0]) == SPEED_MODES[0] else (4 if job.get('speed') == SPEED_MODES[1] else 1),
        'socket_timeout': 25,
        'noplaylist': True,
        'sleep_interval': 5, 'max_sleep_interval': 10, 'sleep_interval_requests': 0.5,
        'noprogress': True, 'logger': logger,
        'progress_hooks': [hooks['progress']],
        'postprocessor_hooks': [hooks['postprocess']],
    }
    if job['format'] == 'MP3':
        cover_folder = metadata_paths(folder, job)['root'] / 'kapaklar'
        options.update(format='bestaudio/best', writethumbnail=True,
                       outtmpl={'default': options['outtmpl'], 'thumbnail': str(cover_folder / '%(id)s.%(ext)s')},
                       postprocessors=[
                           {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg', 'when': 'before_dl'},
                           {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': job['quality'].split()[0]},
                           {'key': 'FFmpegMetadata', 'add_metadata': True, 'add_chapters': False, 'add_infojson': False},
                           {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
                       ])
    else:
        cap = re.match(r'(\d+)p', job['quality'])
        selector = f'bv*[height<={cap[1]}]+ba/b[height<={cap[1]}]' if cap else 'bv*+ba/b'
        options.update(format=selector, format_sort=['res', 'fps'],
                       merge_output_format='mp4', postprocessors=[{
                           'key': 'FFmpegVideoRemuxer', 'preferedformat': 'mp4',
                       }])
    return options


def retryable_error(error):
    text = str(error).casefold()
    return any(fragment in text for fragment in ('403', 'forbidden', '429', 'too many requests', 'timed out', 'timeout',
                                                  'connection reset', '500', '502', '503', '504', 'aria2c exited', 'try again later'))


def download_with_recovery(url, options, emit, sleep=time.sleep):
    import yt_dlp
    from urllib.request import Request, build_opener, ProxyHandler
    reference = None
    for attempt in range(3):
        current = dict(options)
        stop_monitor = threading.Event()
        monitor = None
        if attempt < 2 and current.get('concurrent_fragment_downloads', 1) > 1 and aria2_path():
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            token = secrets.token_hex(16)
            connections = current['concurrent_fragment_downloads']
            current['external_downloader'] = {'http': aria2_path(), 'https': aria2_path()}
            current['external_downloader_args'] = {'aria2c': [f'-x{connections}', f'-s{connections}', '-j1', '-k1M',
                '--max-tries=3', '--retry-wait=2', '--connect-timeout=15', '--timeout=30', '--enable-rpc=true',
                '--rpc-listen-all=false', f'--rpc-listen-port={port}', f'--rpc-secret={token}']}

            def rpc_progress():
                opener = build_opener(ProxyHandler({}))
                shutdown_session = None
                def rpc(method, params):
                    payload = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': ['token:' + token, *params]}).encode()
                    with opener.open(Request(f'http://127.0.0.1:{port}/jsonrpc', data=payload,
                                             headers={'Content-Type': 'application/json'}), timeout=0.4) as response:
                        return json.loads(response.read()).get('result', [])
                while not stop_monitor.wait(0.5):
                    try:
                        tasks = rpc('aria2.tellActive', [['completedLength', 'totalLength', 'downloadSpeed']])
                        total = sum(int(task.get('totalLength', 0)) for task in tasks)
                        complete = sum(int(task.get('completedLength', 0)) for task in tasks)
                        speed = sum(int(task.get('downloadSpeed', 0)) for task in tasks)
                        if total:
                            emit('progress', percent=min(100, complete / total * 100), speed=speed,
                                 eta=(total - complete) / speed if speed else None, stage='downloading')
                        elif not tasks and rpc('aria2.tellStopped', [0, 1, ['status']]):
                            session = rpc('aria2.getSessionInfo', []).get('sessionId')
                            if session != shutdown_session:
                                rpc('aria2.shutdown', [])
                                shutdown_session = session
                    except Exception:
                        pass
            monitor = threading.Thread(target=rpc_progress, daemon=True)
            monitor.start()
        if attempt == 2:
            # Prefer segmented HLS only after comparing resolution and frame rate.
            current['extractor_args'] = {'youtube': {'player_client': ['default', 'web_safari']}}
            current['format_sort'] = ['res', 'fps', 'proto:m3u8_native']
            selector = current.get('format', 'bv*+ba/b')
            if selector == 'bestaudio/best':
                current['format'] = 'bestaudio[protocol^=m3u8]/best[protocol^=m3u8]'
            else:
                current['format'] = selector.replace('bv*', 'bv*[protocol^=m3u8]').replace('+ba', '+ba[protocol^=m3u8]').replace('/b', '/b[protocol^=m3u8]')
            current['concurrent_fragment_downloads'] = min(4, current.get('concurrent_fragment_downloads', 1))
        try:
            with yt_dlp.YoutubeDL(current) as downloader:
                info = downloader.extract_info(url, download=False)
                if not info:
                    raise yt_dlp.utils.DownloadError('Video bilgisi alınamadı.')
                if not reference:
                    reference = (info.get('height') or 0, info.get('fps') or 0)
                elif reference[0] and ((info.get('height') or 0) < reference[0] or
                                       ((info.get('height') or 0) == reference[0] and (info.get('fps') or 0) < reference[1])):
                    raise yt_dlp.utils.DownloadError('Alternatif bağlantı daha düşük kalite sunuyor. Kalite düşürülmedi; daha sonra tekrar deneyin.')
                return downloader.process_ie_result(info, download=True)
        except yt_dlp.utils.DownloadError as error:
            if attempt == 2 or not retryable_error(error):
                raise
            limited = any(term in str(error).casefold() for term in ('429', 'too many requests', 'try again later'))
            delay = (30 if attempt == 0 else 90) if limited else (5 if attempt == 0 else 10)
            emit('status', text=f'Geçici bağlantı hatası. {delay} sn sonra yeniden deneniyor ({attempt + 2}/3)…')
            options['logger'].warning(f'Fresh URL retry {attempt + 2}/3: {error}')
            sleep(delay)
        finally:
            stop_monitor.set()
            if monitor:
                monitor.join(timeout=1)


def output_folder(job, entry=None, channel_title='Kanal'):
    from yt_dlp.utils import sanitize_filename
    base = Path(job['output']).expanduser().resolve()
    item = entry or {}
    channel = item.get('channel') or channel_title
    components = []
    if job.get('channel_subfolders', False):
        components.append(channel)
    if job.get('artist_subfolders', False):
        components.append(item.get('artist') or channel)
    if job.get('playlist_subfolders', False) and item.get('playlist_title'):
        components.append(item['playlist_title'])
    for component in components:
        safe = sanitize_filename(str(component), restricted=False).strip(' .') or 'Kanal'
        safe = safe.replace('/', '_').replace('\\', '_')
        safe = safe.encode('utf-8')[:120].decode('utf-8', errors='ignore').rstrip(' .')
        if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', safe, re.I):
            safe = '_' + safe
        base = base / safe
    return base


def archived_file_exists(folder, entry, names, fmt):
    stem = names.get(entry['id'])
    if not stem:
        return False
    # State names must identify one file inside its destination directory.
    candidate = Path(folder) / (stem + '.' + fmt.lower())
    if candidate.resolve().parent != Path(folder).resolve():
        return False
    try:
        return candidate.is_file() and candidate.stat().st_size > 0
    except OSError:
        return False


def forget_archived_id(archive, video_id):
    lines = archive.read_text(encoding='utf-8').splitlines()
    kept = [line for line in lines if not line.strip() or line.split()[-1] != video_id]
    temp = archive.with_suffix('.tmp')
    temp.write_text('\n'.join(kept) + ('\n' if kept else ''), encoding='utf-8')
    temp.replace(archive)


def metadata_paths(folder, job):
    """State belongs to the app, isolated by destination and export settings."""
    key = hashlib.sha256(os.path.normcase(str(Path(folder).resolve())).encode('utf-8')).hexdigest()[:24]
    state = APP_DIR / 'veri' / 'indirmeler' / key
    state.mkdir(parents=True, exist_ok=True)
    variant = hashlib.sha256((job['format'] + '|' + job['quality']).encode('utf-8')).hexdigest()[:16]
    paths = {'root': state, 'archive': state / ('tamamlananlar-' + variant + '.txt'),
             'names': state / 'dosya-adlari.json', 'list': state / 'video-listesi.json', 'report': state / 'sonuc.json'}
    (state / 'konum.json').write_text(json.dumps({'folder': str(Path(folder).resolve())}, ensure_ascii=False), encoding='utf-8')
    # Preserve resume data from previous versions without leaving it beside media.
    for old, key in [('.tamamlananlar.txt', 'archive'), ('.dosya-adlari.json', 'names'), ('video-listesi.json', 'list'), ('sonuc.json', 'report')]:
        source = Path(folder) / old
        if source.is_file():
            if not paths[key].exists():
                source.replace(paths[key])
            else:
                if key == 'archive':
                    lines = list(dict.fromkeys(paths[key].read_text(encoding='utf-8').splitlines() + source.read_text(encoding='utf-8').splitlines()))
                    paths[key].write_text('\n'.join(lines) + '\n', encoding='utf-8')
                elif key == 'names':
                    old_names = json.loads(source.read_text(encoding='utf-8'))
                    old_names.update(json.loads(paths[key].read_text(encoding='utf-8')))
                    paths[key].write_text(json.dumps(old_names, ensure_ascii=False, indent=2), encoding='utf-8')
                backup = state / 'onceki-kayitlar'
                backup.mkdir(exist_ok=True)
                source.replace(backup / (uuid.uuid4().hex[:8] + '-' + old.lstrip('.')))
    return paths


def reserve_title(folder, entry, names, names_file=None):
    from yt_dlp.utils import sanitize_filename
    video_id = entry['id']
    if video_id in names:
        return names[video_id]
    title = sanitize_filename(entry['title'], restricted=False, is_id=False).strip(' .') or 'Video'
    title = title.encode('utf-8')[:180].decode('utf-8', errors='ignore').rstrip(' .')
    if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', title, re.I):
        title = '_' + title
    stem, number = title, 1
    taken = {name.casefold() for name in names.values()}
    existing = {path.stem.casefold() for path in folder.iterdir() if path.suffix.lower() in ('.mp4', '.mp3')}
    while stem.casefold() in taken or stem.casefold() in existing:
        number += 1
        stem = f'{title} ({number})'
    names[video_id] = stem
    destination = names_file or metadata_paths(folder, {'format': 'MP4', 'quality': 'En yüksek'})['names']
    Path(destination).write_text(json.dumps(names, ensure_ascii=False, indent=2), encoding='utf-8')
    return stem


def run_worker(job_path):
    import yt_dlp
    from yt_dlp.utils import sanitize_filename
    job = json.loads(Path(job_path).read_text(encoding='utf-8'))
    events_path = Path(job['events'])
    lock = threading.Lock()
    log_path = Path(job['log'])

    def emit(kind, **data):
        line = json.dumps({'kind': kind, **data}, ensure_ascii=False)
        with lock:
            with events_path.open('a', encoding='utf-8') as handle:
                handle.write(line + '\n')

    class Logger:
        def debug(self, message):
            self.write(message)
        def write(self, message):
            with lock:
                with log_path.open('a', encoding='utf-8') as handle:
                    handle.write(message + '\n')
        def warning(self, message):
            self.write('WARNING: ' + message)
        def error(self, message):
            self.write('ERROR: ' + message)

    logger = Logger()
    try:
        emit('status', text='Video listesi alınıyor…' if job['action'] == 'list' else 'Seçilen videolar hazırlanıyor…')
        entries, channel_title, skipped_live = get_entries(job, logger)
        folder = output_folder(job, entries[0] if entries else None, channel_title)
        emit('list', entries=entries, channel=channel_title, folder=str(folder), skipped_live=skipped_live)
        if job['action'] == 'list':
            emit('done', text=f'{len(entries)} video bulundu.', completed=0, skipped=0, failed=0)
            return 0
        if not entries:
            raise RuntimeError('Bu kanalda seçilen kapsamda indirilebilir video bulunamadı.')
        folder.mkdir(parents=True, exist_ok=True)
        completed = skipped = failed = 0
        last_progress = [0.0]

        def progress(event):
            if time.monotonic() - last_progress[0] < 0.4 and event['status'] != 'finished':
                return
            last_progress[0] = time.monotonic()
            if shutil.disk_usage(folder).free < 3 * 1024**3:
                raise RuntimeError('Diskte 3 GB altında boş alan kaldı. Kayıt klasörünü değiştirin.')
            total = event.get('total_bytes') or event.get('total_bytes_estimate') or 0
            emit('progress', percent=min(100, event.get('downloaded_bytes', 0) / total * 100) if total else 0,
                 speed=event.get('speed'), eta=event.get('eta'), stage=event['status'])

        def postprocess(event):
            cover = job['format'] == 'MP3' and event.get('postprocessor') in ('EmbedThumbnail', 'ThumbnailsConvertor')
            emit('status', text='Kapak görseli ekleniyor…' if cover else 'Ses hazırlanıyor…' if job['format'] == 'MP3' else 'Görüntü ve ses MP4 olarak birleştiriliyor…', code='cover' if cover else 'processing')

        for index, entry in enumerate(entries, 1):
            if job.get('artist_subfolders') and not entry.get('artist'):
                # Flat channel/playlist listings may omit music metadata.
                with yt_dlp.YoutubeDL({'skip_download': True, 'noplaylist': True, 'logger': logger,
                                      'socket_timeout': 25, 'js_runtimes': node_runtime_options(APP_DIR)}) as resolver:
                    try:
                        details = resolver.extract_info(entry['url'], download=False) or {}
                        entry['artist'] = details.get('artist') or ', '.join(details.get('artists') or [])
                        entry['channel'] = details.get('channel') or entry['channel']
                    except yt_dlp.utils.DownloadError as error:
                        logger.warning('Sanatçı bilgisi alınamadı; kanal adı kullanılacak: ' + str(error))
            folder = output_folder(job, entry, channel_title)
            folder.mkdir(parents=True, exist_ok=True)
            paths = metadata_paths(folder, job)
            paths['list'].write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
            options = make_options(job, folder, logger, {'progress': progress, 'postprocess': postprocess})
            archive = paths['archive']
            archived_ids = {line.split()[-1] for line in archive.read_text(encoding='utf-8').splitlines() if line.strip()} if archive.exists() else set()
            names_file = paths['names']
            names = json.loads(names_file.read_text(encoding='utf-8')) if names_file.exists() else {}
            emit('current', id=entry['id'], title=entry['title'], index=index, total=len(entries), folder=str(folder))
            if entry['id'] in archived_ids and archived_file_exists(folder, entry, names, job['format']):
                skipped += 1
                emit('item', id=entry['id'], state='Zaten indirildi')
            else:
                try:
                    if entry['id'] in archived_ids:
                        forget_archived_id(archive, entry['id'])
                    if shutil.disk_usage(folder).free < 3 * 1024**3:
                        raise RuntimeError('Diskte yeterli boş alan yok. İndirme durduruldu.')
                    stem = reserve_title(folder, entry, names, names_file)
                    empty_media = folder / (stem + '.' + job['format'].lower())
                    if empty_media.resolve().parent == folder.resolve() and empty_media.is_file() and empty_media.stat().st_size == 0:
                        # yt-dlp's no-overwrite mode otherwise preserves an empty final file.
                        empty_media.unlink()
                    template = str(folder / (stem.replace('%', '%%') + '.%(ext)s'))
                    entry_template = {**options['outtmpl'], 'default': template} if isinstance(options['outtmpl'], dict) else template
                    entry_options = {**options, 'outtmpl': entry_template}
                    result = download_with_recovery(entry['url'], entry_options, emit)
                    if not result:
                        raise yt_dlp.utils.DownloadError('Video indirilemedi; ayrıntılar kayıt dosyasında.')
                    completed += 1
                    emit('item', id=entry['id'], state='Tamamlandı')
                except yt_dlp.utils.DownloadError as error:
                    failed += 1
                    emit('item', id=entry['id'], state='Hata', error=str(error))
            emit('overall', processed=index, total=len(entries), completed=completed, skipped=skipped, failed=failed)
        report = {'completed': completed, 'skipped': skipped, 'failed': failed, 'total': len(entries)}
        for target in {output_folder(job, entry, channel_title) for entry in entries}:
            metadata_paths(target, job)['report'].write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        emit('done', text=f'Bitti: {completed} indirildi, {skipped} zaten vardı, {failed} hata.', **report)
        return 0 if not failed else 1
    except BaseException as error:
        logger.error(str(error))
        emit('fatal', text=str(error))
        return 1


def run_gui(test_callback=None):
    from tekniva_gui import run_gui as gui
    return gui(test_callback)


if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--worker':
        sys.exit(run_worker(sys.argv[2]))
    elif len(sys.argv) >= 3 and sys.argv[1] == '--install-node':
        try:
            installed = install_node(APP_DIR)
            result = {'ok': True, 'node_path': installed}
        except Exception as error:
            result = {'ok': False, 'error': str(error)}
        Path(sys.argv[2]).write_text(json.dumps(result), encoding='utf-8')
        sys.exit(0 if result['ok'] else 1)
    elif len(sys.argv) >= 3 and sys.argv[1] == '--check':
        import imageio_ffmpeg
        import yt_dlp
        import yt_dlp_ejs
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        check = subprocess.run([ffmpeg, '-version'], capture_output=True, creationflags=NO_WINDOW)
        runtime = node_path(APP_DIR)
        Path(sys.argv[2]).write_text(json.dumps({'ffmpeg': check.returncode == 0, 'node': bool(runtime), 'node_path': runtime,
                                                'aria2': bool(aria2_path()), 'yt_dlp': yt_dlp.version.__version__,
                                                'ejs': str(yt_dlp_ejs.__file__)}, indent=2), encoding='utf-8')
    else:
        run_gui()
