"""HLL SPA (kendinden hareketli top) yükseliş hesabı.

Kaynak: litku'nun HLL SPA Calculator v2.2.4 (HLL Update 21, istatistikler 2026-10-11),
https://github.com/l1tku/hll-spa-calculator  dist/main.js  "SPA SOLVE ENGINE" ve calculate().
Formül birebir aktarıldı. Doğrulama: test/spa_referans.json, sitenin kendi JS koduyla
üretilen 3600 durum (6 tank × 20 mesafe × 6 eğim × 5 yükseklik). test_hesap.py hepsini karşılaştırır.

Oyundaki nişangâh tablosu (600M | 366 MIL ...) yaklaşık bir referanstır. Site ölçülmüş satırları
ve kuyruk yasasını kullanır; burası da onları kullanır.

Sonuç = HUD_yuvarla( yuvarla( taban(mesafe) + yükseklik_düzeltmesi - kırmızı_MIL ) )
  kırmızı MIL: tankın eğimi (oyunda ELEVATION satırındaki kırmızı sayı).
  sonuç: beyaz ELEVATION değerini getirmen gereken sayı.
"""
import math

# ── tanklar ────────────────────────────────────────────────────────────────
# rows: [dünya MIL, metre] ölçümleri; tail: son satırdan sonrası için kuyruk yasası
SPA_SOLVE = {
    "US (Sherman M4A3 105)": dict(
        rows=[[-89, 23], [-50, 35], [-16, 55], [5, 75], [25, 101], [40, 122], [55, 145], [70, 168], [85, 194],
              [100, 221], [116, 241], [166, 311], [233, 406], [300, 507], [366, 598],
              [400, 644], [424, 676], [448, 702], [466, 719]],
        tail=dict(maxM=600, capDeg=20.6), hmM=1.46),
    "Soviet Union (KV-2)": dict(
        rows=[[-89, 22], [-50, 35], [-16, 55], [5, 75], [25, 99], [40, 122], [55, 143], [70, 168], [85, 191],
              [99, 217], [116, 241], [166, 311], [233, 406], [300, 507], [367, 601],
              [403, 648], [426, 676], [451, 703], [466, 720]],
        tail=dict(maxM=600, capDeg=20.6), hmM=1.34),
    "Germany (Sturmpanzer IV Brummbär)": dict(
        rows=[[-89, 18], [-50, 29], [-16, 48], [5, 67], [25, 92], [40, 115], [55, 139], [70, 164], [85, 190],
              [100, 218], [117, 237], [188, 311], [260, 387], [331, 466], [364, 500], [366, 508],
              [398, 535], [422, 557], [446, 585], [464, 600]],
        tail=dict(maxM=500, capDeg=20.6), hmM=1.52),
    "DAK (Panzer III Ausf.N)": dict(
        rows=[[-87, 18], [-49, 28], [-14, 48], [7, 68], [25, 92], [41, 114], [51, 131], [58, 142], [66, 153],
              [74, 168], [82, 181], [90, 196], [98, 211], [106, 222], [113, 228], [120, 237], [129, 242],
              [137, 251], [146, 264], [153, 272], [163, 282], [170, 289], [203, 324], [252, 377],
              [302, 430], [353, 486], [403, 539], [453, 591], [469, 605]],
        tail=dict(maxM=500, capDeg=20.6), hmM=1.04),
    "British (Churchill AVRE)": dict(
        rows=[[-89, 17], [-20, 35], [10, 48], [82, 98], [100, 114], [110, 124], [120, 132], [131, 142],
              [141, 150], [152, 161], [162, 171], [173, 179], [183, 189], [194, 197], [204, 206], [215, 217],
              [225, 225], [235, 234], [246, 245], [256, 255], [281, 274], [301, 293], [330, 315], [345, 326],
              [356, 334]],
        tail=dict(maxM=250, capDeg=14.42), hmM=0.94),
    "British (Bishop SP)": dict(
        rows=[[-89, 19], [-50, 32], [-16, 61], [5, 100], [25, 148], [40, 194], [50, 232], [58, 278], [65, 304],
              [73, 338], [81, 381], [89, 424], [97, 459], [105, 500], [112, 535], [120, 573], [128, 611],
              [136, 655], [144, 695], [151, 730], [159, 769], [167, 810], [200, 955], [267, 1238]],
        tail=dict(maxM=800, capDeg=9.4), hmM=1.64),
}

# Ekranda gösterilen kısa ad, taret sınırları (site: tables[..].minMil/maxMil) ve en kısa test edilen mesafe
TANKLAR = {
    "US (Sherman M4A3 105)": dict(ad={"tr": "Sherman 105 (ABD)", "en": "Sherman 105 (US)"},
                                  min_mil=-89, max_mil=466, en_kisa=23),
    "Soviet Union (KV-2)": dict(ad={"tr": "KV-2 (Sovyet)", "en": "KV-2 (Soviet)"},
                                min_mil=-89, max_mil=466, en_kisa=22),
    "Germany (Sturmpanzer IV Brummbär)": dict(ad={"tr": "Brummbär (Alman)", "en": "Brummbär (German)"},
                                              min_mil=-89, max_mil=466, en_kisa=18),
    "DAK (Panzer III Ausf.N)": dict(ad={"tr": "Panzer III N (DAK)", "en": "Panzer III N (DAK)"},
                                    min_mil=-89, max_mil=466, en_kisa=18),
    "British (Churchill AVRE)": dict(ad={"tr": "Churchill AVRE", "en": "Churchill AVRE"},
                                     min_mil=-89, max_mil=356, en_kisa=17),
    "British (Bishop SP)": dict(ad={"tr": "Bishop (İngiliz)", "en": "Bishop (British)"},
                                min_mil=-89, max_mil=267, en_kisa=19),
}

SPA_G = 9.8
SPA_MIL_DEG = 0.05625
MILS_PER_DEG = 17.777779
SPA_V0_MPS = 112.5


def js_round(x: float) -> int:
    """JavaScript Math.round: .5 yukarı (Python round bankacı yuvarlaması yapar)."""
    return math.floor(x + 0.5)


def _round_unreal(x: float) -> int:
    return math.floor(x + 0.5) if x >= 0 else math.ceil(x - 0.5)


def hud_yuvarla(mils: float) -> int:
    """Oyunun HUD'u MIL'i böyle yuvarlıyor (site: hudQuantizeMil). >> 1 = aşağı tam bölme."""
    return _round_unreal(mils * 2.0 + 0.5) >> 1


# ── ileri / ters çözüm ─────────────────────────────────────────────────────
def ileri_metre(anahtar: str, mil: float) -> float:
    d = SPA_SOLVE[anahtar]
    rows = d["rows"]
    if mil <= rows[0][0]:
        return rows[0][1]
    son = rows[-1]
    if mil <= son[0]:
        for (m1, r1), (m2, r2) in zip(rows, rows[1:]):
            if mil <= m2:
                return r1 + (mil - m1) / (m2 - m1) * (r2 - r1)
    th = math.radians(mil * SPA_MIL_DEG)
    th_ust = math.radians(son[0] * SPA_MIL_DEG)
    th_cap = math.radians(d["tail"]["capDeg"])
    c = (d["tail"]["maxM"] - 5 * math.cos(th_cap)) / (1.005 * math.sin(2 * th_cap))
    i = lambda t: 5 * math.cos(t) + c * math.sin(2 * t)  # noqa: E731
    return son[1] + i(th) - i(th_ust)


def yukseklik_metre_farki(anahtar: str, mil: float, yukseklik: float) -> float:
    """yukseklik: hedefin toptan kaç metre yukarıda olduğu."""
    if not yukseklik:
        return 0.0
    d = SPA_SOLVE[anahtar]
    r = ileri_metre(anahtar, mil)
    th_deg = mil * SPA_MIL_DEG
    sin_f, cos_f = math.sin(math.radians(th_deg)), math.cos(math.radians(th_deg))
    if abs(sin_f) < 1e-4 or abs(cos_f) < 1e-4:
        return 0.0
    th_hiz = math.radians(max(th_deg, 2.8))
    r_cikis = max(r - 5 * cos_f, 1)
    v2 = SPA_G * r_cikis / (2.01 * math.sin(th_hiz) * math.cos(th_hiz))
    if not v2 > 0:
        return 0.0
    v = math.sqrt(v2)
    vx, vy0 = v * cos_f, v * sin_f

    def dus(dh):
        dd = d["hmM"] + 5 * sin_f - dh
        disc = max(0.0, vy0 * vy0 + 2 * SPA_G * dd)
        return 5 * cos_f + vx * (vy0 + math.sqrt(disc)) / SPA_G

    return dus(yukseklik) - dus(0)


def ters_mil(anahtar: str, metre: float, yukseklik: float = 0.0) -> float:
    f = lambda mil: ileri_metre(anahtar, mil) + yukseklik_metre_farki(anahtar, mil, yukseklik) - metre  # noqa: E731
    lo, hi = -89.0, 800.0
    if f(lo) >= 0:
        return lo
    if f(hi) <= 0:
        return hi
    for _ in range(60):
        orta = (lo + hi) * 0.5
        if f(orta) < 0:
            lo = orta
        else:
            hi = orta
        if hi - lo < 1e-4:
            break
    return (lo + hi) * 0.5


# ── yükseklik düzeltmesi (site: computeHeightDiffMils + balistik yedek) ────
def _balistik_acilar(x, y, v0):
    v2 = v0 * v0
    d = v2 * v2 - SPA_G * (SPA_G * x * x + 2.0 * y * v2)
    if not d >= 0:
        return None
    k = math.sqrt(d)
    return math.atan((v2 + k) / (SPA_G * x)), math.atan((v2 - k) / (SPA_G * x))


def _balistik_mil_farki(taban_mil: float, x: float, y: float) -> float:
    if not x > 0:
        return 0.0
    taban_rad = math.radians(abs(taban_mil / MILS_PER_DEG))
    v0 = SPA_V0_MPS
    if taban_rad > 0 and math.sin(2.0 * taban_rad) > 1e-6:
        v0 = math.sqrt(x * SPA_G / math.sin(2.0 * taban_rad))
    cozum = _balistik_acilar(x, y, v0)
    if not cozum:
        return math.degrees(math.atan2(y, x)) * MILS_PER_DEG
    secilen = cozum[0] if abs(cozum[0] - taban_rad) <= abs(cozum[1] - taban_rad) else cozum[1]
    return math.degrees(secilen - taban_rad) * MILS_PER_DEG


def yukseklik_mil_farki(anahtar: str, taban_mil: float, metre: float, yukseklik: float) -> float:
    dunya = ters_mil(anahtar, metre, yukseklik)
    duz = ters_mil(anahtar, metre, 0)
    # Düşük açıda model doyuma ulaşıyor (yükseklik değişse de sonuç değişmiyor): o zaman balistik yedek
    deneme = 1 if yukseklik == 0 else yukseklik
    test = max(yukseklik + 50, 100) if yukseklik >= 0 else min(yukseklik - 50, -100)
    doymus = abs(yukseklik_metre_farki(anahtar, dunya, test) - yukseklik_metre_farki(anahtar, dunya, deneme)) < 0.5
    if not doymus:
        return dunya - duz
    return _balistik_mil_farki(taban_mil, metre, yukseklik)


# ── dışa açık hesap ───────────────────────────────────────────────────────
def hesapla(anahtar: str, metre: float, kirmizi_mil: float = 0.0, yukseklik: float = 0.0) -> dict:
    """Dönen sözlük: mil (beyaz ELEVATION'ın getirileceği değer), uyari ((kod, sayı) ya da None; metni arayüz kendi dilinde yazar)."""
    tank = TANKLAR[anahtar]
    taban = ters_mil(anahtar, metre, 0)
    fark = yukseklik_mil_farki(anahtar, taban, metre, yukseklik)
    if not math.isfinite(fark):
        fark = _balistik_mil_farki(taban, metre, yukseklik)
    ham = js_round(taban + fark - kirmizi_mil)
    rows = SPA_SOLVE[anahtar]["rows"]
    en_uzak = max(ileri_metre(anahtar, 800), rows[-1][1])
    uyari = None
    if ham > tank["max_mil"]:
        uyari = ("cok_yuksek", tank["max_mil"])
    elif metre < tank["en_kisa"]:
        uyari = ("cok_yakin", tank["en_kisa"])
    elif ham < tank["min_mil"]:
        uyari = ("cok_alcak", tank["min_mil"])
    elif metre > en_uzak:
        uyari = ("menzil_disi", round(en_uzak))
    return dict(mil=hud_yuvarla(ham), uyari=uyari)
