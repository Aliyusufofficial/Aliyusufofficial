---
name: komik-senaryo
description: Usta ve Robo karakterleriyle 30-50 saniyelik komik dikey video (Instagram Reels / YouTube Shorts) senaryosu yazar ve senaryolar/ klasörüne render edilebilir JSON olarak kaydeder. Kullanıcı yeni senaryo, skeç, komik video fikri veya "Usta ve Robo" videosu istediğinde kullan.
---

# Komik Senaryo Yazarı — Usta & Robo

Önce `karakterler/usta.md` ve `karakterler/robo.md` dosyalarını oku. Karakterlerin kişiliğine sadık kal.

## Espri yapısı (her senaryoda)
1. **Hook (ilk 2 sn):** Usta bir felaketi gururla ya da sakince duyurur. Giriş yok, direkt olay.
2. **Tırmanma (4-6 replik):** Robo'nun her cevabı durumu bir kat daha kötüleştirir. Kötü haberi Robo hep en sona saklar. Rakamlar kullan ("kırk dakika", "47 kişi").
3. **Patlama:** Usta küfrederek patlar. Küfürler `[BİİİP]` olarak yazılır ve sahneye `"bip": [[başlangıç_sn, süre_sn]]` eklenir.
4. **Ters köşe:** Robo, Ustanın daha önce verdiği bir talimatı kelimesi kelimesine uyguladığını söyler.
5. **Döngüsel final:** Ya Usta hiçbir şey öğrenmeden aynı hatayı yapmaya hazırlanır, ya da Robo durumu daha da kötüleştirir.

## Kurallar
- Toplam 35-50 saniye, 12-18 sahne. Her replik en fazla 2 satır altyazı (≈50 karakter).
- Küfür ilk 7 saniyede ve başlıkta **asla** yok (reklam geliri için). Her küfür bip'li.
- En az 1-2 `EKRAN` sahnesi (kamera kaydı, dosya adı, WhatsApp grubu, fatura...). Ekran yazılarında emoji kullanma.
- Mizah Türk gündelik hayatından gelsin: şantiye, patron, maaş, kahvehane, komşu, kayınpeder.
- Kimseyi aşağılayan, ırkçı veya cinsel içerikli espri yok.

## Çıktı
1. Önce kullanıcıya 5 kısa fikir (birer cümle) sun, birini seçmesini iste.
2. Seçilen fikri `senaryolar/NNN-kisa-ad.json` olarak `senaryolar/001-patronun-arabasi.json` biçiminde kaydet (alanlar: id, konusan USTA|ROBO|EKRAN, metin, sure, kamera, isteğe bağlı ekran ve bip).
3. Taslak videoyu oluştur: `python3 pipeline/render.py senaryolar/NNN-kisa-ad.json`
