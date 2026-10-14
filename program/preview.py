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
    app.speed_mode.set('Otomatik (önerilen)')
    app.engine.set('curl_cffi')
    app.clipboard_watch.set(False)
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
    from PIL import Image, ImageDraw, ImageTk
    for index, entry in enumerate(entries):
        app.entries[entry['id']]['channel'] = 'Tekniva Sessions' if index < 3 else 'Tekniva Studio'
        app.table.set(entry['id'], 'source', app.entries[entry['id']]['channel'])
        image = Image.new('RGB', (54, 32), ('#23666E', '#725387', '#937940', '#42639D', '#28796A', '#944E64')[index])
        draw = ImageDraw.Draw(image)
        draw.ellipse((28, 3, 49, 24), outline='#C1F5E9', width=2)
        draw.line((0, 26, 14, 15, 26, 29, 39, 21, 54, 31), fill='#EAF8F4', width=2)
        app.thumbnail_images[entry['id']] = ImageTk.PhotoImage(image, master=app.root)
        app.table.item(entry['id'], image=app.thumbnail_images[entry['id']])
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
    app.root.geometry('1000x640+60+60')
    app.apply_theme()
    app.root.update()
    if args.settings:
        app.open_settings()
    app.root.mainloop()


if __name__ == '__main__':
    run_gui(test_callback=preview)
