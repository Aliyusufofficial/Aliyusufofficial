# Usta & Robo — Otomatik Komik Video Sistemi

Usta (sinirli kaynakçı) ile Robo'nun (aşırı sakin yapay zekâ asistanı) yer aldığı komik dikey videoları (Reels / Shorts) üretmek için hazırlanan sistem. Kurgu CapCut'ta değil, kodla yapılıyor.

## Klasörler
| Klasör | İçerik |
|---|---|
| `karakterler/` | Karakter kişilikleri, görsel promptları, sabit sahne |
| `senaryolar/` | Sahne sahne senaryolar (JSON) |
| `.claude/skills/komik-senaryo/` | Yeni senaryo yazan Claude skill'i |
| `pipeline/render.py` | Senaryodan video kurgulayan motor |
| `assets/gorseller/<senaryo>/` | Sahne görselleri veya klipleri: `1.mp4`, `2.png`... |
| `assets/sesler/<senaryo>/` | Sahne sesleri: `1.mp3`, `2.mp3`... |
| `cikti/` | Hazır videolar (git'e eklenmez) |

## Nasıl çalışır?
1. **Senaryo:** Claude'a "yeni bir Usta ve Robo senaryosu yaz" de. `komik-senaryo` skill'i devreye girer.
2. **Taslak video:** `python3 pipeline/render.py senaryolar/001-patronun-arabasi.json`
   Görsel ve ses yoksa renkli taslak kartlarla bir **animatik** çıkar. Böylece zamanlamayı ve espriyi kontrol edersin.
3. **Gerçek görseller ve sesler:** Her sahnenin görselini/klibini ve sesini `assets/` altına sahne numarasıyla koy, sonra aynı komutu tekrar çalıştır. Motor bunları otomatik kullanır. Altyazı, bip sesleri ve ekran yazıları otomatik eklenir.

## Gereksinimler
Python 3 ve ffmpeg.
