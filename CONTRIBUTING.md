# Katkı rehberi / Contributing

Kod, çeviri, dokümantasyon, test ve hata bildirimleriyle katkıda bulunabilirsiniz.

## Hata ve fikir bildirimi

Önce mevcut Issues ve Discussions konularını arayın. Hata için uygulama sürümünü, Windows sürümünü, yeniden oluşturma adımlarını, beklenen/gerçek davranışı belirtin. İşlem kayıtlarını paylaşmadan önce kişisel klasör yollarını, hesap bilgilerini ve özel içerik bağlantılarını temizleyin. Büyük medya dosyaları göndermeyin.

Özellik önerilerini Issues, soruları ve tasarım fikirlerini Discussions üzerinden paylaşın. Güvenlik açıklarını herkese açık issue olarak göndermek yerine SECURITY.md yolunu izleyin.

## Kod katkısı

1. Depoyu fork edin ve kendi kopyanızı klonlayın.
2. `git switch -c fix/aciklayici-ad` ile branch oluşturun.
3. README'deki Python 3.13 / Node.js 22+ ortamını hazırlayın.
4. Değişikliği dar kapsamlı tutun; mevcut davranışı ve yedi dilin anahtar bütünlüğünü koruyun.
5. `python program/test_program.py` çalıştırın. Arayüz değişikliği yaptıysanız iki temada, küçük pencere boyutunda ve ilgili dillerde kontrol edin.
6. Commit yapıp fork'unuza push edin, ana depoya pull request açın.

Doğrudan ana depoya yazma yetkisi gerekmez. Herkes kendi fork'unda commit yapabilir ve pull request gönderebilir; maintainer inceleyerek birleştirir. Windows CI kontrolü PR'larda otomatik çalışır.

## Proje kuralları

- İndirmeler, geçmiş, ayarlar, işlem kayıtları, token'lar ve kullanıcı dosyalarını commit etmeyin.
- Yalnızca seçilen içerikleri indirme davranışını koruyun.
- Yardımcı JSON/TXT dosyaları uygulama klasöründe kalmalı; indirilen klasör temiz tutulmalı.
- Ağ hatalarında sınırlı yeniden deneme uygulayın; sınırsız döngüler veya erişim kısıtlarını aşma iddiaları eklemeyin.
- Ağdan içerik indiren yeni testler yerine yerel sentetik medya kullanın.
- Son kullanıcı güncellemesi yayımlanırken VERSION patch numarası artırılır. Aynı sürümü test için paketlerken `--rebuild` kullanılır. Birden çok PR'ın sürüm artışı release hazırlığında maintainer tarafından birleştirilebilir.
- Yeni arayüz metinlerini `translations.py` içinde yedi dile ekleyin.
- Çeviri katkılarında anlamı, kısaltmaların butonlara sığmasını ve Unicode desteğini kontrol edin.

PR açıklamasında değişiklik, gerekçe ve doğrulama adımlarını belirtin. Katkılar GPL-3.0-or-later altında kabul edilir. Büyük değişiklikleri önce bir issue veya discussion ile tartışın.

## English

Fork the repository, create a focused branch, install the documented development dependencies, run the local test suite and submit a pull request. Do not commit downloads, settings, private paths, logs or credentials. Keep all seven translations complete and verify light/dark themes when changing the UI. Maintainers coordinate the version bump for each delivered update. Contributions are accepted under GPL-3.0-or-later.
