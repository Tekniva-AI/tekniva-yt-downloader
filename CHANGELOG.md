# Değişiklik geçmişi / Changelog

Yayımlanan kullanıcı güncellemelerinde sürüm numarası artırılır. Beta sürümleri GitHub'da prerelease olarak işaretlenir.

## [0.1.8-beta](https://github.com/Tekniva-AI/tekniva-yt-downloader/releases/tag/v0.1.8-beta) — 2026-10-14

### Eklendi ve yenilendi

- curl_cffi 0.16.0 varsayılan HTTP/HTTPS bağlantı katmanı oldu; EXE/ZIP paketlerine dahil edildi. Tarayıcı taklidi zorlanmaz.
- Ayarlar → Bağlantı ve kuyruk sekmesinde aria2 motor tercihi, ayrı aktarım modu ve kanal kapsamı.
- MediaHuman’ın kullanım yaklaşımından esinlenen tam genişlikte kuyruk, Tekniva’ya özgü turkuaz renkler, kompakt araç çubuğu ve açık/koyu görünüm.
- Küçük kapak önizlemeleri, kanal/sanatçı sütunu ve başlıkla birlikte kaynak araması.
- Bekleyen, tamamlanan ve hata filtreleri; yeni eklenen içerikler için filtre sıfırlama.
- Panodan ekleme, Enter/Ctrl+V/Space kısayolları, varsayılan kapalı otomatik pano takibi.
- Tamamlanan dosyayı açma, sağ tık kaynak/dosya menüsü ve kuyruk öğesini kaldırma.
- Sekmeli ayarlar, yedi dilde yeni metinler, sertifika hatasında sistem güven deposuyla doğrulanan geri dönüş.
- Gerçek curl HTTP/Range aktarımı ve altı yeni davranış testi; EXE/ZIP testinde curl_cffi yüklenme ve gerçek medya aktarımı kontrolü.

## [0.1.7-beta](https://github.com/Tekniva-AI/tekniva-yt-downloader/releases/tag/v0.1.7-beta) — 2026-10-14

### Düzeltildi ve hızlandırıldı

- YouTube bağlantı bileşeni resmi 2026.10.10 nightly sürümüne sabitlendi; eşleşen EJS kaynakları korunur.
- Temiz bilgisayarlarda Otomatik mod varsayılan oldu: yerleşik HTTP aktarımı, 8 MiB parçalar ve dört akış bağlantısı.
- Hızlı mod hatasında aynı harici aktarımı tekrar tekrar denemek yerine yerleşik indiriciye geçilir; son alternatifte video kalitesi korunur.
- Akış başına 5–10 saniye bekleme kaldırıldı; toplu istek aralığı ve servis sınırında sınırlı bekleme korunur.
- MP4'te yeniden kodlama yapılmadan ek faststart dosya geçişi kaldırıldı.
- MP3 etiket ve kapakları Mutagen/Pillow ile yazılır; üç FFmpeg ses geçişi yerine tek kodlama geçişi.
- RGB JPEG kapak en fazla 600 piksel, ön kapak ve ID3v2.3 olarak korunur.
- Paket FFmpeg'i eski sistem ortam değişkenlerinden önce seçilir. Sertifika verileri pakete dahil edilir; TLS doğrulaması korunur.
- Node.js sürüm kontrolü dosya değişmedikçe aynı süreçte tekrar çalıştırılmaz.

### Eklendi

- Gerçek FFmpeg hazırlama yüzdesi ve geçen süre; uzun işlemlerde artan kayıt dosyası parça parça okunur.
- Erişim, istek sınırı, TLS, bağlantı, disk ve hazırlama hataları için yedi dilde açıklama; kuyruk sonunda hata bilgisi korunur.
- EXE/ZIP için sistem Node/FFmpeg'i olmadan yerel HTTP, MP4, kapaklı MP3 ve eski/yeni geçiş sayısı doğrulaması.
- Gerçek YouTube/YouTube Music örneğinde yerel MP4 ve MP3 indirme doğrulandı; diğer bilgisayardaki özgül hata kaydına erişilemedi.

## [0.1.6-beta](https://github.com/Tekniva-AI/tekniva-yt-downloader/releases/tag/v0.1.6-beta) — 2026-10-09

### Düzeltildi

- Temiz Windows dağıtım testinde kısa TEMP adları ve klasör bağlantıları gerçek dosya yoluna çözülerek karşılaştırılır.
- EXE/ZIP otomatik Node.js kurulumunun GitHub Windows ortamında doğrulanması düzeltildi.

0.1.5'teki onaylı otomatik Node.js kurulumu, yüzde, iptal ve işleme devam özellikleri bu sürümde de bulunur.

## [0.1.5-beta](https://github.com/Tekniva-AI/tekniva-yt-downloader/releases/tag/v0.1.5-beta) — 2026-10-09

### Eklendi

- Eksik/eski Node.js için uygulama içi onaylı, otomatik taşınabilir kurulum.
- Resmi Node.js 22.23.3 Windows x64 arşivinin sabit SHA-256 ile doğrulanması.
- Uygulama klasöründeki yerel Node.js'in listeleme, sanatçı çözümleme ve indirmede kullanılması.
- Kurulum yüzdesi, iptal, hata sonrası tekrar deneme ve tamamlanınca ilk işleme otomatik dönüş.
- Node.js bulunmayan ortamda EXE ve ZIP için gerçek kurulum/açılış doğrulaması.

### Değiştirildi

- Kullanıcının Node.js'i ayrıca edinme zorunluluğu kaldırıldı. Yönetici izni, sistem kurulumu ve PATH değişikliği gerekmez.
- README, kullanım belgesi, lisans bildirimleri ve release notları yeni ilk kullanım akışına uyarlandı.

## [0.1.4-beta](https://github.com/Tekniva-AI/tekniva-yt-downloader/releases/tag/v0.1.4-beta) — 2026-10-07

### Eklendi

- Alt çubukta tıklanabilir Instagram simgesi ve Tekniva bağlantısı; klavyeyle erişim.
- Herkese açık kaynak deposu, ayrıntılı Türkçe/İngilizce README ve uygulama görselleri.
- GPL-3.0-or-later lisansı, üçüncü taraf bildirimleri ve lisans metinleri.
- Katkı rehberi, davranış kuralları, güvenlik bildirim rehberi ve issue/PR şablonları.
- Windows test ve tag tabanlı taslak release iş akışları.
- Sabit checksum ile araç hazırlama; kişisel veriler içermeyen ZIP/EXE dağıtımı ve SHA-256 dosyası.

## 0.1.3-beta — 2026-10-07

### Düzeltildi

- Daha önce indirilip sonradan silinen veya boş kalan dosyaların yeniden indirilebilmesi.
- İndirme geçmişinin dosyanın gerçekten varlığıyla doğrulanması.

### Eklendi

- Sanatçı ve oynatma listesi adına göre isteğe bağlı alt klasörler.
- Birlikte etkinleştirilen klasör seçeneklerinde kanal → sanatçı → oynatma listesi düzeni.

## 0.1.2-beta — 2026-10-07

### Eklendi

- MP3 dosyalarına JPEG ön kapak ve oynatıcı uyumluluğu için ID3v2.3 etiketleme.
- Kapakların indirme klasöründe ayrı görsel dosyası bırakmadan işlenmesi.

## 0.1.1-beta — 2026-10-07

### Değiştirildi

- Koyu/açık tema renkleri; seçim, üzerine gelme ve devre dışı durumlarında okunabilir kontroller.
- Ayarlar ekranında görünümün canlı önizlemesi ve iptal edildiğinde önceki temaya dönüş.
- Kayıt klasörü ve kanal alt klasörü tercihlerinin Ayarlar'da tutulması; varsayılan düz kayıt düzeni.
- Yardımcı dosyaların uygulama klasöründe tutulması; liste araçlarının tek satırda yerleşimi.

## 0.1.0-beta — 2026-10-07

### İlk beta

- Tekniva YT Downloader adı ve kompakt masaüstü arayüzü.
- Türkçe, İngilizce, Almanca, Fransızca, İspanyolca, Arapça ve Hintçe.
- YouTube / YouTube Music bağlantıları; video, kanal ve oynatma listesi desteği.
- MP4/MP3, kalite seçimi, seçili indirme, arama, sıralama ve kalıcı kuyruk.
- İlerleme yüzdeleri; bağlantı modları, aria2 aktarımı ve geçici hatalarda yeniden deneme.

Geçmiş beta sürümleri geliştirme sırasında yerel olarak dağıtılmıştır; ilk GitHub release'i 0.1.4-beta'dır.
