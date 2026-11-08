#!/usr/bin/env python3
"""Senaryo JSON'undan dikey video kurgular (CapCut'sız).

Her sahne için:
  - Görsel/video:  assets/gorseller/<senaryo>/<id>.mp4 | .png | .jpg  (yoksa taslak kart)
  - Ses:           assets/sesler/<senaryo>/<id>.mp3 | .wav            (yoksa sessizlik)
  - Altyazı, BİİİP sesi ve ekran yazıları otomatik eklenir.

Kullanım:
  python3 pipeline/render.py senaryolar/001-patronun-arabasi.json [--altyazisiz]
Çıktı: cikti/<senaryo>.mp4
"""
import json
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
RENKLER = {"USTA": "0x2b3a55", "ROBO": "0x8a4b12", "EKRAN": "0x0d0f14"}


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def bul(klasor: Path, sid: int, uzantilar):
    for u in uzantilar:
        p = klasor / f"{sid}{u}"
        if p.exists():
            return p
    return None


def yaz(tmp: Path, ad: str, metin: str) -> str:
    p = tmp / ad
    p.write_text(metin, encoding="utf-8")
    return str(p)


def sessizlikleri_kes(klip: Path, hedef: Path, hiz: float = 1.1, esik="-35dB",
                      min_bosluk=0.35, pay=0.12) -> float:
    """Klipteki konuşmayı bulur; baştaki/sondaki beklemeyi ve aradaki uzun
    duraklamaları keser, hafifçe hızlandırır. Yeni süreyi döndürür."""
    sure = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(klip)],
        capture_output=True, text=True).stdout.strip())
    log = subprocess.run(["ffmpeg", "-i", str(klip), "-af",
                          f"silencedetect=n={esik}:d={min_bosluk}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    bas = [float(x.split("silence_start: ")[1].split()[0]) for x in log.splitlines() if "silence_start" in x]
    bit = [float(x.split("silence_end: ")[1].split()[0]) for x in log.splitlines() if "silence_end" in x]
    sessiz = list(zip(bas, bit + [sure] * (len(bas) - len(bit))))
    # konuşma aralıkları = sessizliklerin tersi
    konusma, t = [], 0.0
    for a, b in sessiz:
        if a - t > 0.05:
            konusma.append([max(0, t - pay), min(sure, a + pay)])
        t = b
    if sure - t > 0.05:
        konusma.append([max(0, t - pay), sure])
    if not konusma:
        konusma = [[0, sure]]
    # çakışanları birleştir
    birlesik = [konusma[0]]
    for a, b in konusma[1:]:
        if a <= birlesik[-1][1]:
            birlesik[-1][1] = b
        else:
            birlesik.append([a, b])
    fc, etiket = [], ""
    for i, (a, b) in enumerate(birlesik):
        fc.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}]")
        etiket += f"[v{i}][a{i}]"
    fc.append(f"{etiket}concat=n={len(birlesik)}:v=1:a=1[v][a];[v]setpts=PTS/{hiz}[vo];[a]atempo={hiz}[ao]")
    run(["ffmpeg", "-y", "-i", str(klip), "-filter_complex", ";".join(fc), "-map", "[vo]", "-map", "[ao]",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-c:a", "aac", str(hedef)])
    return sum(b - a for a, b in birlesik) / hiz


def sahne_render(s, ad, tmp: Path, onceki=None, altyazi=True) -> Path:
    sid, sure = s["id"], float(s.get("sure", 0))
    gorsel = bul(ROOT / "assets/gorseller" / ad, sid, [".mp4", ".png", ".jpg"])
    ses = bul(ROOT / "assets/sesler" / ad, sid, [".mp3", ".wav"])
    out = tmp / f"sahne_{sid}.mp4"
    klip_sesi = False
    if "kaynak" in s:
        # elle kurgu: kaynak klipten seçilen aralıklar + punch-in zoom + sonda bekleme
        kaynak = ROOT / "assets/gorseller" / ad / f"{s['kaynak']}.mp4"
        araliklar = s.get("araliklar") or [s["aralik"]]
        hiz, z, bekle = float(s.get("hiz", 1.08)), float(s.get("zoom", 1.0)), float(s.get("bekleme", 0))
        fc, et = [], ""
        for i, (a, b) in enumerate(araliklar):
            fc.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}]")
            et += f"[v{i}][a{i}]"
        zoom = f",crop=iw/{z}:ih/{z}:(iw-iw/{z})/2:(ih-ih/{z})/2.6,scale=720:1280" if z != 1.0 else ""
        pad_v = f",tpad=stop_mode=clone:stop_duration={bekle}" if bekle else ""
        pad_a = f",apad=pad_dur={bekle}" if bekle else ""
        fc.append(f"{et}concat=n={len(araliklar)}:v=1:a=1[vc][ac];"
                  f"[vc]setpts=PTS/{hiz}{zoom}{pad_v}[vo];[ac]atempo={hiz}{pad_a}[ao]")
        kesik = tmp / f"kurgu_{sid}.mp4"
        run(["ffmpeg", "-y", "-i", str(kaynak), "-filter_complex", ";".join(fc), "-map", "[vo]", "-map", "[ao]",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-c:a", "aac", str(kesik)])
        sure = sum(b - a for a, b in araliklar) / hiz + bekle
        gorsel, klip_sesi = kesik, True
    elif gorsel is not None and gorsel.suffix == ".mp4" and ses is None:
        # Veo/Flow klibi: kendi sesi var → boşlukları kes, süreyi klibe göre ayarla
        kesik = tmp / f"kesik_{sid}.mp4"
        sure = sessizlikleri_kes(gorsel, kesik, hiz=float(s.get("hiz", 1.1)))
        gorsel, klip_sesi = kesik, True

    arka_plan = False
    if gorsel is None and s["konusan"] == "EKRAN" and onceki is not None:
        # ekran sahnesi: önceki sahnenin son karesini bulanık arka plan yap (siyah ekran olmasın)
        kare = tmp / f"son_{sid}.png"
        run(["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(onceki), "-frames:v", "1", "-update", "1", str(kare)])
        gorsel, arka_plan = kare, True

    # --- girdiler
    cmd = ["ffmpeg", "-y"]
    if gorsel is None:
        renk = RENKLER.get(s["konusan"], "0x222222")
        cmd += ["-f", "lavfi", "-i", f"color=c={renk}:s={W}x{H}:r={FPS}:d={sure}"]
    elif klip_sesi:
        cmd += ["-i", str(gorsel)]
    elif gorsel.suffix == ".mp4":
        cmd += ["-stream_loop", "-1", "-i", str(gorsel)]
    else:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-i", str(gorsel)]
    if klip_sesi:
        cmd += ["-i", str(gorsel)]
    elif ses:
        cmd += ["-i", str(ses)]
    else:
        cmd += ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={sure}"]

    # --- görüntü filtreleri
    v = [f"scale={W}:{H}:force_original_aspect_ratio=increase", f"crop={W}:{H}", f"fps={FPS}"]
    if arka_plan:
        v += ["boxblur=18:2", "eq=brightness=-0.18"]
    if gorsel is not None and gorsel.suffix != ".mp4":
        # durağan görsele hafif yakınlaşma (Ken Burns)
        v.append(f"zoompan=z='min(zoom+0.0008,1.08)':d=1:s={W}x{H}:fps={FPS}")
    if gorsel is None and s["konusan"] != "EKRAN":
        # taslak kart: konuşan + kamera notu
        v.append(f"drawtext=fontfile={FONT}:textfile='{yaz(tmp, f'k{sid}.txt', s['konusan'])}':"
                 f"fontsize=110:fontcolor=white@0.9:x=(w-tw)/2:y=360")
        not_ = textwrap.fill("[" + s.get("kamera", "") + "]", 30)
        v.append(f"drawtext=fontfile={FONT}:textfile='{yaz(tmp, f'n{sid}.txt', not_)}':"
                 f"fontsize=40:fontcolor=white@0.6:line_spacing=12:x=(w-tw)/2:y=540")
    if s.get("ekran"):
        satir = s["ekran"].count("\n") + 1
        kh = 110 + satir * 78
        ky = (H - kh) // 2
        v.append(f"drawbox=x=70:y={ky}:w={W-140}:h={kh}:color=0x0b0e14@0.92:t=fill")
        v.append(f"drawbox=x=70:y={ky}:w={W-140}:h={kh}:color=0x3fb950@0.9:t=4")
        v.append(f"drawtext=fontfile={MONO}:textfile='{yaz(tmp, f'e{sid}.txt', s['ekran'])}':"
                 f"fontsize=54:fontcolor=0x7CFC9A:line_spacing=24:x=120:y={ky + 60}")
    for x, y, bw, bh, t0, t1 in s.get("bulaniklastir", []):
        # Flow'un kendi eklediği yazıyı gizle (çıktı koordinatlarında)
        v.append(f"delogo=x={x}:y={y}:w={bw}:h={bh}:enable='between(t,{t0},{t1})'")
    if s.get("metin") and altyazi:
        # cümlelere böl, her cümleyi uzunluğuyla orantılı süre boyunca sırayla göster
        cumleler = [c.strip() for c in re.split(r"(?<=[.!?])\s+|\s/\s", s["metin"]) if c.strip()]
        toplam = sum(len(c) for c in cumleler)
        t = 0.0
        for j, c in enumerate(cumleler):
            uz = sure * len(c) / toplam
            alt = textwrap.fill(c, 24)
            v.append(f"drawtext=fontfile={FONT}:textfile='{yaz(tmp, f'a{sid}_{j}.txt', alt)}':"
                     f"fontsize=58:fontcolor=white:borderw=5:bordercolor=black:line_spacing=12:"
                     f"box=1:boxcolor=black@0.45:boxborderw=20:x=(w-tw)/2:y=h*0.72:"
                     f"enable='between(t,{t:.2f},{t + uz:.2f})'")
            t += uz
    vf = ",".join(v)

    # --- ses: BİİİP'ler
    bipler = s.get("bip", [])
    if bipler:
        parca = ["[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a0]"]
        etiketler = ["[a0]"]
        for i, (bas, uz) in enumerate(bipler):
            ms = int(bas * 1000)
            parca.append(f"sine=f=1000:d={uz}:sample_rate=44100,volume=0.35,"
                         f"aformat=channel_layouts=stereo,adelay={ms}|{ms}[b{i}]")
            etiketler.append(f"[b{i}]")
        parca.append("".join(etiketler) + f"amix=inputs={len(etiketler)}:normalize=0[a]")
        fc = f"[0:v]{vf}[v];" + ";".join(parca)
    else:
        fc = f"[0:v]{vf}[v];[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a]"

    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", str(sure),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast",
            "-c:a", "aac", "-ar", "44100", str(out)]
    run(cmd)
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    altyazi = "--altyazisiz" not in sys.argv
    senaryo = Path([a for a in sys.argv[1:] if not a.startswith("--")][0])
    veri0 = json.loads(senaryo.read_text(encoding="utf-8"))
    ad = veri0.get("klasor", senaryo.stem)
    veri = json.loads(senaryo.read_text(encoding="utf-8"))
    (ROOT / "cikti").mkdir(exist_ok=True)
    hedef = ROOT / "cikti" / f"{senaryo.stem}.mp4"

    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        parcalar = []
        for s in veri["sahneler"]:
            print(f"  sahne {str(s['id']):>3} — {s['konusan']}: {s.get('metin', '')[:40]}")
            onceki = parcalar[-1] if parcalar else None
            parcalar.append(sahne_render(s, ad, tmp, onceki, altyazi))
        liste = tmp / "liste.txt"
        liste.write_text("".join(f"file '{p}'\n" for p in parcalar))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
             "-c", "copy", str(hedef)])
    print(f"\nHazır: {hedef}")


if __name__ == "__main__":
    main()
