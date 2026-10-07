"""Launch the real UI with fictional, nonpersistent entries for screenshots."""
import argparse
from kanal_indirici import run_gui


def preview(app):
    parser = argparse.ArgumentParser()
    parser.add_argument('--theme', choices=('dark', 'light'), default='dark')
    parser.add_argument('--settings', action='store_true')
    args = parser.parse_args()
    app.settings = {}
    app.language = 'tr'
    app.theme = args.theme
    app.url.set('https://www.youtube.com/@Tekniva')
    app.output.set('D:/Downloads/Tekniva')
    app.channel_subfolders.set(False)
    app.artist_subfolders.set(False)
    app.playlist_subfolders.set(False)
    app.fmt.set('MP3')
    app.quality.set('320 kbps')
    app.scope.set('Videolar + Shorts + yayın kayıtları')
    app.speed_mode.set('Hızlı (8 bağlantı)')
    app.refresh_language()
    entries = [
        {'id': 'demo0000001', 'title': 'Tekniva Sessions - Gece Yolculuğu', 'duration': 242},
        {'id': 'demo0000002', 'title': 'Tekniva Sessions - Yeni Bir Gün', 'duration': 196},
        {'id': 'demo0000003', 'title': 'Akustik Seri - Sahil', 'duration': 218},
        {'id': 'demo0000004', 'title': 'Studio Live - Renkler', 'duration': 263},
        {'id': 'demo0000005', 'title': 'Tekniva Rehberi - İlk Adımlar', 'duration': 387},
        {'id': 'demo0000006', 'title': 'Tekniva Sessions - Yol Arkadaşı', 'duration': 204},
    ]
    app.action = 'list'
    app.handle({'kind': 'list', 'folder': app.output.get(), 'channel': 'Tekniva', 'entries': entries})
    app.action = None
    app.selected_ids = {'demo0000001', 'demo0000002', 'demo0000003'}
    app.states = {'demo0000001': ('completed', 100), 'demo0000002': ('downloading', 64)}
    app.render_selection()
    for video_id in app.states:
        app.render_state(video_id)
    app.apply_search()
    app.status.set('Örnek kuyruk · 3 içerik seçildi')
    app.detail.set('Tanıtım görünümü — örnek içerikler, gerçek indirme yapılmıyor.')
    app.count.set('1 / 3 işlendi · 1 indirildi · 0 hata')
    app.current_bar['value'] = 64
    app.overall_bar['value'] = 33
    app.root.deiconify()
    app.root.protocol('WM_DELETE_WINDOW', app.root.quit)
    app.root.geometry('960x650+60+60')
    app.apply_theme()
    app.root.update()
    if args.settings:
        app.open_settings()
    app.root.mainloop()


if __name__ == '__main__':
    run_gui(test_callback=preview)
