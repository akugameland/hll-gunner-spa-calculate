"""Kurulumda ses modelini indirir (KURULUM.bat çağırır). / Downloads the speech model during setup.

Ekran kartı (NVIDIA) varsa whisper large-v3-turbo (~1,6 GB), yoksa whisper small (~480 MB).
Sürümler sabittir; yalnız model ağırlıkları ve json/txt dosyaları iner, çalıştırılabilir kod inmez.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import konusma  # noqa: E402

try:
    ek = json.loads((Path(__file__).parent / "ayarlar.json").read_text(encoding="utf-8")).get("whisper_klasoru", "")
except (OSError, ValueError):
    ek = ""
print("Ses modeli hazirlaniyor / Preparing speech model...")
konusma.model_hazirla(ek)
print("Ses modeli hazir / Speech model ready.")
