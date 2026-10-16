import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sayilar  # noqa: E402

DURUMLAR = {
    "tr": {
        "450": (450, 0), "450.": (450, 0), "Dört yüz elli metre.": (450, 0), "bin iki yüz": (1200, 0),
        "1.200 metre": (1200, 0), "1200m": (1200, 0), "450 artı 20": (450, 20), "450 +20": (450, 20),
        "300 aşağı on beş": (300, -15), "300 eksi 15": (300, -15), "Yedi yüz yirmi beş.": (725, 0),
        "Yüz": (100, 0), "İki yüz otuz üç metre": (233, 0), "450 metre, hedef 20 metre aşağıda.": (450, -20),
        "600 metre 30 metre yukarıda": (600, 30), "Altı yüz.": (600, 0), "iptal": "iptal", "Sil.": "iptal",
        "540 540": (540, 0), "1200 1200 1200": (1200, 0), "450 metre. 450 metre, 450 metre metre.": (450, 0),
        "dört beş sıfır": (450, 0), "merhaba": None, "": None, "Doksan beş": (95, 0), "bin": (1000, 0),
        "On bin": None,
    },
    "en": {
        "450": (450, 0), "450 meters.": (450, 0), "Four hundred and fifty.": (450, 0), "four fifty": (450, 0),
        "Four five zero.": (450, 0), "twelve hundred": (1200, 0), "one thousand two hundred": (1200, 0),
        "1,200 meters": (1200, 0), "twelve fifty": (1250, 0), "seven twenty five": (725, 0),
        "450 plus 20": (450, 20), "450, 20 up": (450, 20), "300 minus 15": (300, -15),
        "300 down fifteen": (300, -15), "600 meters, target 30 meters above": (600, 30),
        "Eight hundred ten, 15 below.": (810, -15), "Cancel.": "iptal", "clear": "iptal",
        "hello": None, "ninety five": (95, 0), "one hundred": (100, 0), "four-fifty": (450, 0),
        "450 450": (450, 0),
    },
}
hata = toplam = 0
for dil, durumlar in DURUMLAR.items():
    for metin, beklenen in durumlar.items():
        toplam += 1
        sonuc = sayilar.coz(metin, dil)
        if sonuc != beklenen:
            hata += 1
            print(f"HATA [{dil}] {metin!r}: {sonuc} (beklenen {beklenen})")
print(f"{toplam - hata}/{toplam} doğru")
sys.exit(1 if hata else 0)
