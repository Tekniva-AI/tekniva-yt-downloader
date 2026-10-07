# Tekniva YT Downloader

- Her kullanıcıya teslim edilen güncellemede sürüm numarasını artır. Küçük düzeltmelerde patch sürümünü artır; beta etiketi devam etsin.
- Sürümün tek kaynağı `program/translations.py` içindeki `VERSION` değeridir. Arayüz, Windows dosya özellikleri ve kullanım belgesi aynı sürümü göstermelidir.
- `python program/build_release.py` yeni patch sürümü oluşturur. Aynı güncellemenin test veya paket onarımı için `--rebuild` kullan; bu işlem sürümü tekrar artırmaz.
- İndirilen klasörlere yardımcı JSON/TXT dosyası yazma; kayıtlar program klasöründe tutulur.
- İndirme klasörü ve kanal/sanatçı/oynatma listesi alt klasörü tercihleri Ayarlar menüsünde kalmalıdır. Varsayılan kayıt düzeni doğrudan seçilen klasördür.
