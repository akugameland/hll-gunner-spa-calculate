"""Kurulum denetimi: her parçayı kontrol eder, hazır olanı atlar, eksik ya da yarım olanı tamamlar.
KURULUM.bat çağırır. Elle de çalıştırılabilir: .venv\\Scripts\\python.exe kurulum_denetim.py

    --paketler   yalnız Python paketlerini requirements.txt'ye göre denetle (internet kullanmaz).
                 Çıkış kodu 0: hepsi doğru sürümde kurulu, 1: eksik/yanlış var (pip çalıştırılmalı).
    (argümansız) tam denetim: paketler, ekran kartı, ses modeli (gerekirse indirir), yazı tanıma, mikrofon.
                 Çıkış kodu 0: program çalışabilir, 1: çalışamaz.

2026-10-17 kullanıcı: "sürekli silip kurulum yapıyorum, mevcut şeyleri tekrar tekrar yüklediği için hata
veriyor olmasın". Bu yüzden: model program klasörü dışında (konusma.VERI) durur ve bütünlüğü boyut kaydıyla
denetlenir; paketler sürümleriyle denetlenir, doğruysa pip hiç çalışmaz.
"""
import json
import re
import sys
from importlib import metadata
from pathlib import Path

KLASOR = Path(__file__).resolve().parent
TAMAM, UYARI, HATA = "[TAMAM]", "[UYARI]", "[HATA] "


def yaz(etiket: str, tr: str, en: str = ""):
    print(f"{etiket} {tr}" + (f"  /  {en}" if en else ""), flush=True)


def paketleri_denetle(sessiz: bool = False) -> list[str]:
    """requirements.txt'deki her 'ad==sürüm' kurulu mu? Eksik/yanlış olanları döndürür."""
    eksik = []
    for satir in (KLASOR / "requirements.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_.\-]+)==([^\s#]+)", satir)
        if not m:
            continue
        ad, surum = m.groups()
        try:
            kurulu = metadata.version(ad)
        except metadata.PackageNotFoundError:
            kurulu = None
        if kurulu != surum:
            eksik.append(f"{ad} (gerekli {surum}, kurulu {kurulu or 'yok'})")
    if not sessiz:
        if eksik:
            yaz(UYARI, "Eksik ya da farklı sürüm paketler: " + ", ".join(eksik))
        else:
            yaz(TAMAM, "Python paketleri doğru sürümde kurulu", "Python packages OK")
    return eksik


def main() -> int:
    if "--paketler" in sys.argv:
        return 1 if paketleri_denetle(sessiz=True) else 0

    tamam = True
    yaz(TAMAM if sys.version_info[:2] == (3, 12) else UYARI, f"Python {sys.version.split()[0]}")
    if paketleri_denetle():
        return 1

    try:
        ayar = json.loads((KLASOR / "ayarlar.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ayar = {}
    ek = ayar.get("whisper_klasoru", "")

    # Sıra önemli: konusma (ctranslate2) winrt'den önce yüklenmeli (bkz. uygulama.py)
    import konusma

    gerekli = konusma.gereken_model()
    if gerekli == "turbo":
        yaz(TAMAM, "NVIDIA ekran kartı bulundu: büyük ses modeli kullanılacak", "NVIDIA GPU found")
    else:
        yaz(UYARI, "NVIDIA ekran kartı yok: işlemcide küçük model kullanılacak (biraz daha yavaş)",
            "No NVIDIA GPU: small CPU model")

    m = konusma.MODELLER[gerekli]
    yol = konusma.model_yolu(ek) if gerekli == "turbo" else (
        konusma.model_klasoru("small") if konusma.model_tam_mi(konusma.model_klasoru("small")) else None)
    if yol:
        yaz(TAMAM, f"Ses modeli hazır, indirilmeyecek: {yol}", "Speech model ready")
    else:
        hedef = konusma.model_klasoru(gerekli)
        yarim = hedef.exists() and any(hedef.iterdir())
        yaz(UYARI, ("Ses modeli yarım kalmış, kaldığı yerden tamamlanıyor" if yarim else
                    f"Ses modeli indiriliyor ({m['boyut']}, bir kez)") + f": {hedef}",
            "Resuming speech model download" if yarim else "Downloading speech model (once)")
        try:
            konusma.model_indir(gerekli)
            yaz(TAMAM, "Ses modeli indirildi ve doğrulandı", "Speech model downloaded and verified")
        except Exception as h:  # noqa: BLE001
            yaz(HATA, f"Ses modeli indirilemedi: {h}. İnternet bağlantısını kontrol edip KURULUM.bat'ı "
                      "yeniden çalıştırın; indirme kaldığı yerden sürer.",
                "Model download failed; run KURULUM.bat again, it resumes")
            tamam = False

    try:
        from winrt.windows.media.ocr import OcrEngine
        diller = [d.language_tag for d in OcrEngine.available_recognizer_languages]
        if diller:
            yaz(TAMAM, f"Windows yazı tanıma hazır ({', '.join(diller)})", "Windows OCR ready")
        else:
            yaz(HATA, "Windows yazı tanıma dili yok: Ayarlar → Saat ve dil → Dil → bir dil paketi ekleyin",
                "No Windows OCR language installed")
            tamam = False
    except Exception as h:  # noqa: BLE001
        yaz(HATA, f"Windows yazı tanıma açılamadı: {h}", "Windows OCR unavailable")
        tamam = False

    try:
        mikrofonlar = konusma.Mikrofon.liste()
        if mikrofonlar:
            yaz(TAMAM, f"{len(mikrofonlar)} mikrofon bulundu: {', '.join(mikrofonlar)}", "Microphones found")
        else:
            yaz(UYARI, "Mikrofon bulunamadı. Mesafe programa elle de yazılabilir.", "No microphone found")
    except Exception as h:  # noqa: BLE001
        yaz(UYARI, f"Mikrofonlar listelenemedi: {h}", "Could not list microphones")

    yaz(TAMAM if tamam else HATA, "Kurulum denetimi bitti" if tamam else "Kurulumda eksik var (yukarıya bakın)",
        "Setup check passed" if tamam else "Setup incomplete (see above)")
    return 0 if tamam else 1


if __name__ == "__main__":
    sys.exit(main())
