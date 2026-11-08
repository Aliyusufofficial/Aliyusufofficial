#!/usr/bin/env python3
"""Senaryo JSON'undan dikey video kurgular (CapCut'sız).

Her sahne için:
  - Görsel/video:  assets/gorseller/<senaryo>/<id>.mp4 | .png | .jpg  (yoksa taslak kart)
  - Ses:           assets/sesler/<senaryo>/<id>.mp3 | .wav            (yoksa sessizlik)
  - Altyazı, BİİİP sesi ve ekran yazıları otomatik eklenir.

Kullanım:
  python3 pipeline/render.py senaryolar/001-patronun-arabasi.json
Çıktı: cikti/<senaryo>.mp4
"""
import json
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


def sahne_render(s, ad, tmp: Path) -> Path:
    sid, sure = s["id"], float(s["sure"])
    gorsel = bul(ROOT / "assets/gorseller" / ad, sid, [".mp4", ".png", ".jpg"])
    ses = bul(ROOT / "assets/sesler" / ad, sid, [".mp3", ".wav"])
    out = tmp / f"sahne_{sid:03d}.mp4"

    # --- girdiler
    cmd = ["ffmpeg", "-y"]
    if gorsel is None:
        renk = RENKLER.get(s["konusan"], "0x222222")
        cmd += ["-f", "lavfi", "-i", f"color=c={renk}:s={W}x{H}:r={FPS}:d={sure}"]
    elif gorsel.suffix == ".mp4":
        cmd += ["-stream_loop", "-1", "-i", str(gorsel)]
    else:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-i", str(gorsel)]
    if ses:
        cmd += ["-i", str(ses)]
    else:
        cmd += ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={sure}"]

    # --- görüntü filtreleri
    v = [f"scale={W}:{H}:force_original_aspect_ratio=increase", f"crop={W}:{H}", f"fps={FPS}"]
    if gorsel is not None and gorsel.suffix != ".mp4":
        # durağan görsele hafif yakınlaşma (Ken Burns)
        v.append(f"zoompan=z='min(zoom+0.0008,1.08)':d=1:s={W}x{H}:fps={FPS}")
    if gorsel is None:
        # taslak kart: konuşan + kamera notu
        v.append(f"drawtext=fontfile={FONT}:textfile='{yaz(tmp, f'k{sid}.txt', s['konusan'])}':"
                 f"fontsize=110:fontcolor=white@0.9:x=(w-tw)/2:y=360")
        not_ = textwrap.fill("[" + s.get("kamera", "") + "]", 30)
        v.append(f"drawtext=fontfile={FONT}:textfile='{yaz(tmp, f'n{sid}.txt', not_)}':"
                 f"fontsize=40:fontcolor=white@0.6:line_spacing=12:x=(w-tw)/2:y=540")
    if s.get("ekran"):
        v.append(f"drawbox=x=90:y=760:w={W-180}:h=330:color=black@0.85:t=fill")
        v.append(f"drawtext=fontfile={MONO}:textfile='{yaz(tmp, f'e{sid}.txt', s['ekran'])}':"
                 f"fontsize=52:fontcolor=0x7CFC9A:line_spacing=18:x=140:y=810")
    if s.get("metin"):
        alt = textwrap.fill(s["metin"], 26)
        v.append(f"drawtext=fontfile={FONT}:textfile='{yaz(tmp, f'a{sid}.txt', alt)}':"
                 f"fontsize=62:fontcolor=white:borderw=6:bordercolor=black:line_spacing=14:"
                 f"box=1:boxcolor=black@0.45:boxborderw=24:x=(w-tw)/2:y=h*0.70")
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
    senaryo = Path(sys.argv[1])
    ad = senaryo.stem
    veri = json.loads(senaryo.read_text(encoding="utf-8"))
    (ROOT / "cikti").mkdir(exist_ok=True)
    hedef = ROOT / "cikti" / f"{ad}.mp4"

    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        parcalar = []
        for s in veri["sahneler"]:
            print(f"  sahne {s['id']:>2} — {s['konusan']}: {s.get('metin', '')[:40]}")
            parcalar.append(sahne_render(s, ad, tmp))
        liste = tmp / "liste.txt"
        liste.write_text("".join(f"file '{p}'\n" for p in parcalar))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
             "-c", "copy", str(hedef)])
    print(f"\nHazır: {hedef}")


if __name__ == "__main__":
    main()
