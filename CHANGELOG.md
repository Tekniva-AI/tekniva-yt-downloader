# Değişiklik geçmişi / Changelog

Yayımlanan kullanıcı güncellemelerinde sürüm numarası artırılır. Beta sürümleri GitHub'da prerelease olarak işaretlenir.

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
