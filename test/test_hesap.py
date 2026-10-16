"""hesap.py'yi sitenin kendi JS koduyla üretilmiş 3600 durumla karşılaştırır."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import hesap  # noqa: E402

veri = json.loads((Path(__file__).parent / "spa_referans.json").read_text(encoding="utf-8"))
hata = [(t, d, r, h, b, hesap.hesapla(t, d, r, h)["mil"]) for t, d, r, h, b in veri
        if hesap.hesapla(t, d, r, h)["mil"] != b]
print(f"{len(veri) - len(hata)}/{len(veri)} durum site ile aynı")
for x in hata[:20]:
    print("  FARK", x)
sys.exit(1 if hata else 0)
