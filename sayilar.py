"""Söylenen sözden mesafe (ve isteğe bağlı yükseklik farkı) çıkarır. Türkçe ve İngilizce.

Türkçe:
    "450"                   -> (450, 0)
    "Dört yüz elli metre."  -> (450, 0)
    "dört beş sıfır"        -> (450, 0)     rakam rakam
    "bin iki yüz"           -> (1200, 0)
    "1.200 metre"           -> (1200, 0)
    "450 artı 20"           -> (450, 20)    hedef 20 m yukarıda
    "300 aşağı on beş"      -> (300, -15)   hedef 15 m aşağıda
    "iptal" / "sil"         -> "iptal"
İngilizce:
    "four hundred and fifty" / "four fifty" / "four five zero" -> (450, 0)
    "twelve hundred"        -> (1200, 0)
    "450 plus 20" / "450, 20 up"   -> (450, 20)
    "300 minus 15" / "300 down 15" -> (300, -15)
    "cancel" / "clear"      -> "iptal"
"""
import re

DILLER = {
    "tr": dict(
        birler={"sıfır": 0, "bir": 1, "iki": 2, "üç": 3, "dört": 4, "beş": 5, "altı": 6, "yedi": 7,
                "sekiz": 8, "dokuz": 9},
        onlu={},
        onlar={"on": 10, "yirmi": 20, "otuz": 30, "kırk": 40, "elli": 50, "altmış": 60, "yetmiş": 70,
               "seksen": 80, "doksan": 90},
        yuz="yüz", bin="bin", ve=(),
        yukari=("artı", "yukarı", "yukarıda", "yüksek", "yüksekte"),
        asagi=("eksi", "aşağı", "aşağıda", "alçak", "alçakta"),
        iptal=("iptal", "sil", "temizle", "vazgeç"),
        km=("km", "kilometre"),
    ),
    "en": dict(
        birler={"zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9},
        onlu={"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
              "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19},
        onlar={"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60,
               "seventy": 70, "eighty": 80, "ninety": 90},
        yuz="hundred", bin="thousand", ve=("and",),
        yukari=("plus", "up", "above", "higher", "high"),
        asagi=("minus", "down", "below", "lower", "low"),
        iptal=("cancel", "clear", "delete", "reset", "abort"),
        km=("km", "kilometer", "kilometers", "kilometre", "kilometres"),
    ),
}
_HARF = "a-zçğıöşü"


def _kucuk(metin: str, dil: str) -> str:
    if dil == "tr":
        metin = metin.replace("İ", "i").replace("I", "ı")
    return metin.lower()


def _grup_sayi(kelimeler: list[str], d: dict) -> int:
    birler, onlu, onlar = d["birler"], d["onlu"], d["onlar"]
    # Rakam rakam: "dört beş sıfır" / "four five zero" -> 450
    if len(kelimeler) >= 2 and all(k in birler for k in kelimeler):
        return int("".join(str(birler[k]) for k in kelimeler))
    # İngilizce kısa söyleyiş: "four fifty" -> 450, "twelve fifty" -> 1250, "seven twenty five" -> 725
    if (len(kelimeler) >= 2 and d["yuz"] not in kelimeler and d["bin"] not in kelimeler
            and (kelimeler[0] in birler or kelimeler[0] in onlu) and (kelimeler[1] in onlar or kelimeler[1] in onlu)):
        ilk = birler.get(kelimeler[0], onlu.get(kelimeler[0], 0))
        return ilk * 100 + _grup_sayi(kelimeler[1:], d)
    toplam, simdi = 0, 0
    for k in kelimeler:
        if k in birler:
            simdi += birler[k]
        elif k in onlu:
            simdi += onlu[k]
        elif k in onlar:
            simdi += onlar[k]
        elif k == d["yuz"]:
            simdi = (simdi or 1) * 100
        elif k == d["bin"]:
            toplam += (simdi or 1) * 1000
            simdi = 0
    return toplam + simdi


def _jetonlar(metin: str, d: dict, dil: str) -> list[str]:
    """Sayı sözcüklerini rakama çevirir; diğer kelimeleri olduğu gibi bırakır."""
    m = _kucuk(metin, dil)
    # 1.200 / 1,200 / 1 200 -> 1200. İlk grup en çok 2 hane: Whisper "540 540" diye tekrar yazınca 540540 olmasın
    m = re.sub(r"(?<!\d)(\d{1,2})[.,\s](\d{3})(?!\d)", r"\1\2", m)
    m = re.sub(r"(\d+)\s*(m|mt|metre|meter|metres|meters|metro)\b", r"\1", m)
    m = re.sub(rf"(\d)(?=[{_HARF}])", r"\1 ", m)                # 450m -> 450 m
    m = re.sub(rf"(?<=[{_HARF}])-(?=[{_HARF}])", " ", m)        # "four-fifty", "twenty-five"
    parcalar = re.findall(rf"[+-]?\d+|[{_HARF}]+|[+-]", m)
    sayi_sozu = set(d["birler"]) | set(d["onlu"]) | set(d["onlar"]) | {d["yuz"], d["bin"]}
    cikti, grup = [], []
    for i, p in enumerate(parcalar):
        if p in sayi_sozu:
            grup.append(p)
            continue
        # "four hundred and fifty": iki sayı sözcüğü arasındaki "and" grubu bölmesin
        if p in d["ve"] and grup and i + 1 < len(parcalar) and parcalar[i + 1] in sayi_sozu:
            continue
        if grup:
            cikti.append(str(_grup_sayi(grup, d)))
            grup = []
        cikti.append(p)
    if grup:
        cikti.append(str(_grup_sayi(grup, d)))
    return cikti


def coz(metin: str, dil: str = "tr"):
    """(mesafe, yukseklik) ya da 'iptal' ya da None."""
    d = DILLER.get(dil, DILLER["tr"])
    j = _jetonlar(metin, d, dil)
    if not j:
        return None
    if any(k in d["iptal"] for k in j):
        return "iptal"
    yukari, asagi = d["yukari"], d["asagi"]
    sayilar = [(i, int(k)) for i, k in enumerate(j) if re.fullmatch(r"[+-]?\d+", k)]
    if not sayilar:
        return None
    i0, mesafe = sayilar[0]
    mesafe = abs(mesafe)
    if any(k in d["km"] for k in j[i0 + 1:i0 + 2]):
        mesafe *= 1000
    yukseklik = 0
    for i, deger in sayilar[1:]:
        once = j[max(i0 + 1, i - 2):i]
        if any(k in asagi or k == "-" for k in once):
            yukseklik = -abs(deger)
        elif any(k in yukari or k == "+" for k in once) or j[i].startswith("+"):
            yukseklik = abs(deger)
        elif j[i].startswith("-"):
            yukseklik = -abs(deger)
        else:
            continue
        if any(k in asagi for k in j[i + 1:i + 3]):              # "20 metre aşağıda": yön sonradan
            yukseklik = -abs(deger)
        break
    else:
        # "450 metre, hedef 20 metre aşağıda" / "450, 20 up": yön sözcüğü sayıdan sonra
        for i, deger in sayilar[1:]:
            sonra = j[i + 1:i + 3]
            if any(k in asagi for k in sonra):
                yukseklik = -abs(deger)
                break
            if any(k in yukari for k in sonra):
                yukseklik = abs(deger)
                break
    if not 1 <= mesafe <= 3000:
        return None
    return mesafe, yukseklik
