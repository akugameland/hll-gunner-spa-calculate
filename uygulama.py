"""HLL Gunner SPA Calculate (hll-gunner-spa-calculate): Hell Let Loose SPA nişan yardımcısı. Türkçe / English.

Bas-konuş tuşuna basılı tutup mesafeyi söyle ("dört yüz elli" / "four fifty", "450 artı 20" / "450 plus 20").
Program sağ alttaki nişangâh panelini sürekli okur (namlu ELEVATION + kırmızı eğim MIL + tank)
ve namluyu kaç MIL'e getirmen gerektiğini altyazı olarak yazar. Değere gelince yeşil "ATEŞ" / "FIRE" der.
Hesap: litku'nun HLL SPA Calculator v2.2.4 formülü (hesap.py, MIT).
"""
import ctypes
import json
import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import keyboard

# Çift tıklamayla (pythonw) açılınca konsol yok: sys.stdout/stderr None olur ve bir şey yazmaya çalışan her
# kütüphane çöker. Model indirirken ilerleme çubuğu (tqdm) "'NoneType' object has no attribute 'write'"
# veriyordu (2026-10-17, kurulumu yarım kalan başka bir bilgisayarda görüldü). Çıktıyı boşluğa yönlendir.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

KLASOR = Path(__file__).resolve().parent
AYAR_DOSYASI = KLASOR / "ayarlar.json"
logging.basicConfig(filename=KLASOR / "hata.log", level=logging.INFO, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
for _gurultu in ("httpx", "httpx2", "httpcore", "huggingface_hub"):        # her HTTP isteğini kayda yazmasın
    logging.getLogger(_gurultu).setLevel(logging.WARNING)

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)     # ekran yakalama doğru bölgeyi alsın, yazı bulanık olmasın
except Exception:  # noqa: BLE001
    pass

# Sıra önemli: konusma (ctranslate2) ekran'dan (winrt) ÖNCE yüklenmeli. winrt paketi kendi eski
# msvcp140.dll'ini getiriyor; önce o yüklenince Whisper modeli açılırken çöküyor (2026-10-16 ölçüldü).
try:
    import konusma  # noqa: E402
    KONUSMA_HATA = None
except Exception as _h:  # noqa: BLE001
    konusma, KONUSMA_HATA = None, _h
import altyazi  # noqa: E402
import ekran  # noqa: E402
import hesap  # noqa: E402
import sayilar  # noqa: E402
import yetki  # noqa: E402
from fare import DUGMELER, FareDinleyici  # noqa: E402
from metinler import DIL_ADLARI, t, varsayilan_dil  # noqa: E402

VARSAYILAN = {"dil": "", "tank": "otomatik", "ptt_tusu": "f9", "mikrofon": "", "monitor": 1,
              "boyut": 30, "alt_bosluk": 18, "tarama_ms": 250,
              "whisper_klasoru": ""}     # isteğe bağlı: aynı Whisper modeli başka klasörde varsa (indirmeden)
OKUMA_GECERLI_SN = 1.2          # son okuma bu kadar eskiyse nişangâh görünmüyor say
DUYULAN_SN = 5

SARI, YESIL, BEYAZ, GRI, KIRMIZI, MAVI = "#ffd84a", "#4dff6a", "#ffffff", "#bdbdbd", "#ff5a5a", "#8fd0ff"
ARKA, ON, KUTU = "#1e1f24", "#e8e8e8", "#2b2d34"


def ayar_yukle() -> dict:
    a = dict(VARSAYILAN)
    try:
        a.update({k: v for k, v in json.loads(AYAR_DOSYASI.read_text(encoding="utf-8")).items() if k in VARSAYILAN})
    except (OSError, ValueError):
        pass
    if a["dil"] not in DIL_ADLARI:
        a["dil"] = varsayilan_dil()
    return a


class Uygulama:
    def __init__(self):
        self.ayar = ayar_yukle()
        self.olaylar: queue.Queue = queue.Queue()
        self.kok = tk.Tk()
        self.kok.geometry("580x680")
        self.kok.configure(bg=ARKA)
        self.kok.protocol("WM_DELETE_WINDOW", self.kapat)
        self.kok.report_callback_exception = lambda *a: logging.error("arayüz hatası", exc_info=a)
        stil = ttk.Style()
        stil.theme_use("clam")
        stil.configure("TCombobox", fieldbackground=KUTU, background=KUTU, foreground=ON)

        self.hedef: tuple[int, int] | None = None       # (mesafe, yükseklik farkı)
        self.okuma = ekran.Okuma()
        self.okuma_zamani = 0.0
        self.son_kirmizi: tuple[int, float] | None = None
        self.son_tank: str | None = None
        self.duyulan: tuple[str, float, str] | None = None   # (metin, zaman, renk)
        self.dinliyor = False
        self.cozuluyor = False
        self._tus_basili = False
        self._atama_bekliyor = False
        self._calisiyor = True
        self.tanima = None
        self.mikrofon = None
        self.son_bas = 0.0
        self.son_kayit: tuple[str, float, float] | None = None
        self._engel = False                                # oyun yönetici, biz değiliz: tuşlar gelmez
        self._engel_zamani = 0.0
        self._durum = ("yukleniyor", {}, GRI)               # dil değişince yeniden yazılabilsin
        self._mikrofonlar: list[str] = []
        self._gecmis: list[str] = []
        self.govde = None

        self._arayuz()
        self.altyazi = altyazi.Altyazi(self.kok, self.ayar["boyut"], self.ayar["alt_bosluk"])
        self._altyazi_konumla()
        self.fare = FareDinleyici(self._fare_olayi)
        self._tus_bagla()
        threading.Thread(target=self._ekran_dongusu, daemon=True, name="ekran").start()
        threading.Thread(target=self._ses_hazirla, daemon=True, name="ses").start()
        self.kok.after(100, self._tik)

    def m(self, anahtar: str, **kw) -> str:
        return t(self.ayar["dil"], anahtar, **kw)

    def tus_adi(self, tus: str) -> str:
        return self.m(tus) if tus in DUGMELER else tus.upper()

    def tank_adi(self, anahtar: str) -> str:
        return hesap.TANKLAR[anahtar]["ad"][self.ayar["dil"]]

    # ── arayüz ───────────────────────────────────────────────────────────────
    def _arayuz(self):
        """Dil değişince baştan kurulur."""
        if self.govde is not None:
            self.govde.destroy()
        self.kok.title(self.m("baslik").split(":")[0])
        k = self.govde = tk.Frame(self.kok, bg=ARKA)
        k.pack(fill="both", expand=True)
        tk.Label(k, text=self.m("baslik"), bg=ARKA, fg=SARI, font=("Segoe UI", 15, "bold")).pack(pady=(12, 2))
        self.durum = tk.Label(k, bg=ARKA, fg=GRI, font=("Segoe UI", 10), wraplength=540)
        self.durum.pack()
        self._durum_yaz()

        cerceve = tk.Frame(k, bg=ARKA)
        cerceve.pack(fill="x", padx=16, pady=10)
        cerceve.columnconfigure(1, weight=1)

        def etiket(yazi, satir):
            tk.Label(cerceve, text=yazi, bg=ARKA, fg=ON, font=("Segoe UI", 10)).grid(row=satir, column=0,
                                                                                    sticky="w", pady=4, padx=(0, 8))

        etiket(self.m("dil"), 0)
        self.dil_kutu = ttk.Combobox(cerceve, values=list(DIL_ADLARI.values()), state="readonly")
        self.dil_kutu.set(DIL_ADLARI[self.ayar["dil"]])
        self.dil_kutu.grid(row=0, column=1, sticky="ew")
        self.dil_kutu.bind("<<ComboboxSelected>>", self._dil_secildi)

        etiket(self.m("tank"), 1)
        self.tank_kutu = ttk.Combobox(cerceve, values=[self.m("otomatik")] + [self.tank_adi(a) for a in hesap.TANKLAR],
                                      state="readonly")
        self.tank_kutu.set(self.tank_adi(self.ayar["tank"]) if self.ayar["tank"] in hesap.TANKLAR
                           else self.m("otomatik"))
        self.tank_kutu.grid(row=1, column=1, sticky="ew")
        self.tank_kutu.bind("<<ComboboxSelected>>", self._tank_secildi)

        etiket(self.m("bas_konus"), 2)
        self.tus_dugme = tk.Button(cerceve, command=self._tus_degistir, bg=KUTU, fg=ON, relief="flat",
                                   activebackground="#3a3d46", activeforeground=ON,
                                   text=self.m("tus_degistir", tus=self.tus_adi(self.ayar["ptt_tusu"])))
        self.tus_dugme.grid(row=2, column=1, sticky="ew")

        etiket(self.m("mikrofon"), 3)
        self.mik_kutu = ttk.Combobox(cerceve, state="readonly", values=[self.m("varsayilan_mik")] + self._mikrofonlar)
        self.mik_kutu.set(self.ayar["mikrofon"] or self.m("varsayilan_mik"))
        self.mik_kutu.grid(row=3, column=1, sticky="ew")
        self.mik_kutu.bind("<<ComboboxSelected>>", self._mikrofon_secildi)

        etiket(self.m("elle"), 4)
        elle = tk.Frame(cerceve, bg=ARKA)
        elle.grid(row=4, column=1, sticky="ew")
        self.elle = tk.Entry(elle, bg=KUTU, fg=ON, insertbackground=ON, relief="flat", font=("Segoe UI", 11))
        self.elle.pack(side="left", fill="x", expand=True)
        self.elle.bind("<Return>", lambda e: self._elle_gir())
        tk.Button(elle, text=self.m("hesapla"), command=self._elle_gir, bg=KUTU, fg=ON,
                  relief="flat").pack(side="left", padx=(6, 0))
        tk.Label(cerceve, text=self.m("elle_ornek"), bg=ARKA, fg=GRI, font=("Segoe UI", 8)).grid(row=5, column=1,
                                                                                               sticky="w")

        etiket(self.m("boyut"), 6)
        boyut = tk.Scale(cerceve, from_=14, to=70, orient="horizontal", bg=ARKA, fg=ON, highlightthickness=0,
                         troughcolor=KUTU)
        boyut.set(self.ayar["boyut"])
        boyut.config(command=lambda v: self._altyazi_ayar("boyut", int(v)))
        boyut.grid(row=6, column=1, sticky="ew")
        etiket(self.m("konum"), 7)
        konum = tk.Scale(cerceve, from_=0, to=60, orient="horizontal", bg=ARKA, fg=ON, highlightthickness=0,
                         troughcolor=KUTU)
        konum.set(self.ayar["alt_bosluk"])
        konum.config(command=lambda v: self._altyazi_ayar("alt_bosluk", int(v)))
        konum.grid(row=7, column=1, sticky="ew")
        etiket(self.m("ekran_no"), 8)
        self.mon = tk.Spinbox(cerceve, from_=1, to=4, width=4, bg=KUTU, fg=ON, relief="flat",
                              command=lambda: self._altyazi_ayar("monitor", int(self.mon.get())))
        self.mon.delete(0, "end")
        self.mon.insert(0, str(self.ayar["monitor"]))
        self.mon.grid(row=8, column=1, sticky="w")

        tk.Label(k, text=self.m("okunan"), bg=ARKA, fg=MAVI, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16)
        self.okunan = tk.Label(k, text="—", bg=KUTU, fg=ON, font=("Consolas", 10), justify="left", anchor="w")
        self.okunan.pack(fill="x", padx=16, pady=(2, 8), ipady=6, ipadx=6)
        tk.Label(k, text=self.m("gecmis"), bg=ARKA, fg=MAVI, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=16)
        self.gecmis = tk.Listbox(k, bg=KUTU, fg=ON, relief="flat", height=8, font=("Segoe UI", 9),
                                 highlightthickness=0)
        self.gecmis.pack(fill="both", expand=True, padx=16, pady=(2, 12))
        for satir in self._gecmis:
            self.gecmis.insert("end", satir)

    def _durum_yaz(self):
        anahtar, kw, renk = self._durum
        self.durum.config(text=self.m(anahtar, **kw), fg=renk)

    def _durum_ayarla(self, anahtar: str, kw: dict, renk: str):
        self._durum = (anahtar, kw, renk)
        self._durum_yaz()

    def _hazir_durumu(self):
        if self.tanima and self.mikrofon:
            self._durum_ayarla("hazir", dict(tus=self.tus_adi(self.ayar["ptt_tusu"]), cihaz=self.m(self.tanima.cihaz),
                                             mik=self.mikrofon.ad), YESIL)

    def _kaydet(self):
        try:
            AYAR_DOSYASI.write_text(json.dumps(self.ayar, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            logging.exception("ayar kaydı")

    def _gecmise(self, metin: str):
        satir = time.strftime("%H:%M:%S  ") + metin
        self._gecmis = [satir] + self._gecmis[:199]
        self.gecmis.insert(0, satir)
        self.gecmis.delete(200, "end")

    def _dil_secildi(self, _=None):
        dil = next(k for k, v in DIL_ADLARI.items() if v == self.dil_kutu.get())
        if dil == self.ayar["dil"]:
            return
        self.ayar["dil"] = dil
        self._kaydet()
        if self.tanima:
            self.tanima.dil_ayarla(dil)
            self._hazir_durumu()
        self._arayuz()

    def _tank_secildi(self, _=None):
        ad = self.tank_kutu.get()
        self.ayar["tank"] = next((k for k in hesap.TANKLAR if self.tank_adi(k) == ad), "otomatik")
        self._kaydet()

    def _altyazi_ayar(self, anahtar, deger):
        if self.ayar.get(anahtar) == deger:
            return
        self.ayar[anahtar] = deger
        self._kaydet()
        if hasattr(self, "altyazi"):
            self._altyazi_konumla()

    def _altyazi_konumla(self):
        try:
            import mss
            with mss.MSS() as m:
                mon = m.monitors[min(int(self.ayar["monitor"]), len(m.monitors) - 1)]
        except Exception:  # noqa: BLE001
            mon = None
        self.altyazi.ayarla(self.ayar["boyut"], self.ayar["alt_bosluk"], mon)

    # ── ses ──────────────────────────────────────────────────────────────────
    def _ses_hazirla(self):
        try:
            if konusma is None:
                raise RuntimeError(KONUSMA_HATA)
            self._konusma = konusma
            self.olaylar.put(("mikrofonlar", konusma.Mikrofon.liste()))
            if konusma.ctranslate2.get_cuda_device_count() > 0 and konusma.model_yolu(self.ayar["whisper_klasoru"]) is None:
                self.olaylar.put(("durum", "indiriliyor", {}, GRI))     # kurulum indirmediyse (normalde indirir)
                konusma.model_indir()
            self.mikrofon = konusma.Mikrofon(self.ayar["mikrofon"])
            self.tanima = konusma.Tanima(self.ayar["dil"], self.ayar["whisper_klasoru"])
            self.tanima.yaziya(__import__("numpy").zeros(8000, "float32"))     # ilk çağrı yavaş: ısıt
            self.olaylar.put(("hazir",))
        except Exception as h:  # noqa: BLE001
            logging.exception("ses hazırlığı")
            self.olaylar.put(("durum", "ses_yok", {"hata": f"{type(h).__name__}: {h}"}, KIRMIZI))

    def _mikrofon_secildi(self, _=None):
        ad = self.mik_kutu.get()
        self.ayar["mikrofon"] = "" if ad == self.m("varsayilan_mik") else ad
        self._kaydet()
        if self.mikrofon:
            eski = self.mikrofon
            try:
                self.mikrofon = self._konusma.Mikrofon(self.ayar["mikrofon"])
                eski.kapat()
                self._gecmise(self.m("mik_degisti", ad=self.mikrofon.ad))
                self._hazir_durumu()
            except Exception:  # noqa: BLE001
                logging.exception("mikrofon değişimi")
                self._gecmise(self.m("mik_acilmadi"))

    def _tus(self, basili: bool):
        """Klavye/fare iş parçacığından çağrılır: kısa tut."""
        if basili == self._tus_basili:
            return
        self._tus_basili = basili
        self.olaylar.put(("tus_durum", basili))

    def _tus_isle(self, basili: bool):
        """Hiçbir durum sessiz geçmez (2026-10-17 kullanıcı "tuşa basıyorum bir şey olmuyor" dedi):
        model hazır değilse, ses çok kısa ya da sessizse altyazıda kırmızı uyarı çıkar ve kayda yazılır."""
        if basili:
            self.son_bas = time.time()
        if not self.mikrofon or not self.tanima:
            if basili:
                logging.info("bas-konuş basıldı ama ses hazır değil: %s", self.durum.cget("text"))
                self.duyulan = (self.m("hazir_degil", durum=self.durum.cget("text")), time.time(), KIRMIZI)
            return
        if basili:
            self.dinliyor = True
            self.mikrofon.basla()
            return
        self.dinliyor = False
        pcm = self.mikrofon.bitir()
        sure, sev = len(pcm) / self._konusma.HIZ, self._konusma.seviye(pcm)
        self.son_kayit = (time.strftime("%H:%M:%S"), sure, sev)
        logging.info("bas-konuş: %.2f sn, ses seviyesi %.4f, mikrofon %s", sure, sev, self.mikrofon.ad)
        if not self._konusma.ses_var_mi(pcm):
            anahtar = "cok_kisa" if sure < self._konusma.EN_KISA_SN else "ses_duyulmadi"
            self.duyulan = (self.m(anahtar, sure=sure, mik=self.mikrofon.ad), time.time(), KIRMIZI)
            self._gecmise(self.m(anahtar, sure=sure, mik=self.mikrofon.ad))
            return
        self.cozuluyor = True

        def coz():
            try:
                metin = self.tanima.yaziya(pcm)
            except Exception:  # noqa: BLE001
                logging.exception("whisper")
                metin = ""
            logging.info("duyulan: %r", metin)
            self.olaylar.put(("duyulan", metin))
        threading.Thread(target=coz, daemon=True).start()

    def _soz_isle(self, metin: str, kaynak: str):
        self.cozuluyor = False
        sonuc = sayilar.coz(metin, self.ayar["dil"]) if metin else None
        if sonuc == "iptal":
            self.hedef = None
            self.duyulan = (self.m("hedef_silindi", kaynak=kaynak, metin=metin), time.time(), GRI)
            self._gecmise(self.m("hedef_silindi", kaynak=kaynak, metin=repr(metin)))
        elif sonuc:
            self.hedef = sonuc
            yuks = self.m("yuks_gecmis", y=sonuc[1]) if sonuc[1] else ""
            self.duyulan = (f"{kaynak}: {metin}", time.time(), GRI)
            self._gecmise(self.m("gecmis_hedef", kaynak=kaynak, metin=metin, mesafe=sonuc[0], yuks=yuks))
        else:
            self.duyulan = (self.m("anlasilmadi", metin=metin or self.m("ses_bos")), time.time(), KIRMIZI)
            self._gecmise(self.m("anlasilmadi", metin=repr(metin)))

    def _elle_gir(self):
        metin = self.elle.get().strip()
        if metin:
            self._soz_isle(metin, self.m("elle_kaynak"))
            self.elle.delete(0, "end")

    # ── bas-konuş tuşu (CanYouSpeak'ten) ─────────────────────────────────────
    def _tus_bagla(self):
        self._atama_bekliyor = False
        keyboard.unhook_all()
        tus = self.ayar["ptt_tusu"]
        if tus in DUGMELER:
            self.fare.dinle(True)
        else:
            self.fare.dinle(False)
            aranan = tus.lower()       # tuş ADIYLA eşleşir: makro yazılımları tarama kodu göndermeyebiliyor

            def klavye(olay):
                if (olay.name or "").lower() == aranan:
                    self._tus(olay.event_type == keyboard.KEY_DOWN)
            keyboard.hook(klavye)
        self.tus_dugme.config(text=self.m("tus_degistir", tus=self.tus_adi(tus)))
        self._hazir_durumu()

    def _fare_olayi(self, dugme: str, basili: bool):
        if self._atama_bekliyor:
            if basili:
                self._atama_bekliyor = False
                self.olaylar.put(("tus_ata", dugme))
        elif dugme == self.ayar["ptt_tusu"]:
            self._tus(basili)

    def _tus_degistir(self):
        if self._tus_basili:
            return
        self.tus_dugme.config(text=self.m("tus_bekle"))
        keyboard.unhook_all()
        self._atama_bekliyor = True
        self.fare.dinle(True)

        def klavye(olay):
            if self._atama_bekliyor and olay.event_type == keyboard.KEY_DOWN and olay.name:
                self._atama_bekliyor = False
                self.olaylar.put(("tus_ata", None if olay.name == "esc" else olay.name))
        keyboard.hook(klavye)

    # ── ekran ────────────────────────────────────────────────────────────────
    def _ekran_dongusu(self):
        okuyucu = None
        while self._calisiyor:
            bas = time.perf_counter()
            try:
                if okuyucu is None or okuyucu.monitor_no != int(self.ayar["monitor"]):
                    okuyucu = ekran.EkranOkuyucu(int(self.ayar["monitor"]))
                self.olaylar.put(("okuma", okuyucu.oku()))
            except Exception:  # noqa: BLE001
                logging.exception("ekran okuma")
                time.sleep(2)
            # hedef yokken seyrek oku (işlemciyi boşuna yorma)
            aralik = self.ayar["tarama_ms"] / 1000 if self.hedef else 1.0
            time.sleep(max(0.05, aralik - (time.perf_counter() - bas)))

    # ── ana döngü ────────────────────────────────────────────────────────────
    def _tik(self):
        try:
            for _ in range(200):
                tur, *veri = self.olaylar.get_nowait()
                if tur == "okuma":
                    o = veri[0]
                    if o.panel:
                        self.okuma, self.okuma_zamani = o, time.time()
                        if o.kirmizi is not None:
                            self.son_kirmizi = (o.kirmizi, time.time())
                        if o.tank:
                            self.son_tank = o.tank
                elif tur == "tus_durum":
                    self._tus_isle(veri[0])
                elif tur == "duyulan":
                    self._soz_isle(veri[0], self.m("duyulan"))
                elif tur == "durum":
                    self._durum_ayarla(*veri)
                elif tur == "hazir":
                    self._hazir_durumu()
                elif tur == "mikrofonlar":
                    self._mikrofonlar = veri[0]
                    self.mik_kutu.config(values=[self.m("varsayilan_mik")] + veri[0])
                elif tur == "tus_ata":
                    if veri[0]:
                        self.ayar["ptt_tusu"] = veri[0]
                        self._kaydet()
                    self._tus_bagla()
        except queue.Empty:
            pass
        except Exception:  # noqa: BLE001
            logging.exception("olay işleme")
        try:
            self._goster()
        except Exception:  # noqa: BLE001
            logging.exception("gösterim")
        if self._calisiyor:
            self.kok.after(100, self._tik)

    def _goster(self):
        simdi = time.time()
        gorunuyor = simdi - self.okuma_zamani < OKUMA_GECERLI_SN
        o = self.okuma
        tank = self.ayar["tank"] if self.ayar["tank"] in hesap.TANKLAR else self.son_tank
        self.okunan.config(text="\n".join((
            self.m("nisangah", durum=self.m("gorunuyor" if gorunuyor else "gorunmuyor")),
            self.m("okunan_satir", elev=o.yukselis if gorunuyor else "—",
                   kirmizi=o.kirmizi if gorunuyor and o.kirmizi is not None else "—"),
            self.m("silah_satir", silah=o.silah or "—", tank=self.tank_adi(tank) if tank else self.m("bulunamadi")),
            self.m("son_bas_satir", saat=self.son_kayit[0], sure=self.son_kayit[1], sev=self.son_kayit[2])
            if self.son_kayit else self.m("son_bas_yok"))))
        if simdi - self._engel_zamani > 1.0:
            self._engel_zamani = simdi
            engel = yetki.tuslar_engelli_mi()
            if engel and not self._engel:
                logging.warning("öndeki pencere yönetici olarak çalışıyor, program değil: bas-konuş tuşu görünmez")
            self._engel = engel

        satirlar = []
        if self._engel:
            satirlar.append((self.m("yonetici_uyari"), KIRMIZI, 0.5, True))
        if self.duyulan and simdi - self.duyulan[1] < DUYULAN_SN:
            satirlar.append((self.duyulan[0], self.duyulan[2], 0.5, False))
        if self.dinliyor:
            satirlar.append((self.m("dinliyorum"), MAVI, 0.6, True))
        elif self.cozuluyor:
            satirlar.append(("…", MAVI, 0.6, True))

        if self.hedef:
            mesafe, yukseklik = self.hedef
            yuks = self.m("yuks_bilgi", y=yukseklik) if yukseklik else ""
            if not tank:
                satirlar.append((self.m("tank_yok", mesafe=mesafe, yuks=yuks), KIRMIZI, 0.55, True))
            else:
                if gorunuyor and o.kirmizi is not None:
                    kirmizi, egim_notu = o.kirmizi, ""
                elif not gorunuyor and self.son_kirmizi:
                    kirmizi, egim_notu = self.son_kirmizi[0], self.m("egim_son")
                else:
                    kirmizi, egim_notu = 0, self.m("egim_okunamadi")
                r = hesap.hesapla(tank, mesafe, kirmizi, yukseklik)
                bilgi = self.m("bilgi", mesafe=mesafe, yuks=yuks, tank=self.tank_adi(tank), kirmizi=kirmizi,
                               not_=egim_notu)
                if gorunuyor and o.yukselis is not None:
                    fark = r["mil"] - o.yukselis
                    if fark == 0:
                        satirlar += [(bilgi, BEYAZ, 0.5, False), (self.m("atesle", mil=r["mil"]), YESIL, 1.0, True)]
                    else:
                        yon = self.m("yukari", n=fark) if fark > 0 else self.m("asagi", n=-fark)
                        satirlar += [(bilgi, BEYAZ, 0.5, False), (f"{r['mil']} MIL", SARI, 1.0, True),
                                     (yon + self.m("su_an", deger=o.yukselis), BEYAZ, 0.55, True)]
                else:
                    satirlar += [(bilgi + self.m("gorunmuyor_ek"), GRI, 0.5, False),
                                 (f"{r['mil']} MIL", GRI, 0.8, True)]
                if r["uyari"]:
                    kod, n = r["uyari"]
                    satirlar.append((self.m(kod, n=n), KIRMIZI, 0.5, True))
        self.altyazi.yaz(satirlar)

    def kapat(self):
        self._calisiyor = False
        try:
            keyboard.unhook_all()
            self.fare.kapat()
            if self.mikrofon:
                self.mikrofon.kapat()
        finally:
            self.kok.destroy()

    def calis(self):
        self.kok.mainloop()


if __name__ == "__main__":
    try:
        Uygulama().calis()
    except Exception:  # noqa: BLE001
        logging.exception("çöküş")
        raise
