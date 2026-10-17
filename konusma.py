"""Bas-konuş: tuş basılıyken mikrofonu kaydeder, bırakınca Whisper ile yazıya çevirir (internetsiz).

Model: whisper large-v3-turbo (CanYouSpeak ile aynı). modeller/whisper-turbo içinde ya da ayarlar.json'daki
"whisper_klasoru" yolunda aranır; yoksa kurulumda indirilir (~1,6 GB). Ekran kartı yoksa işlemcide 'small'
modele düşer.

Hız: CanYouSpeak'teki ölçüme göre (GTX 1650) Whisper sesi 30 sn'ye tamamlayınca kodlama ~1,75 sn sürüyor.
Kısa sözü 10 sn'lik pencerede kodlamak ~0,4 sn. Burada da CTranslate2 doğrudan kullanılır, dil seçilen
dilde sabittir (dil tespiti yok) ve kısa bir ipucu cümlesi verilir.
"""
import collections
import glob
import logging
import os
import sys
import threading
from pathlib import Path

import numpy as np

KLASOR = Path(__file__).resolve().parent
YEREL_MODEL = KLASOR / "modeller" / "whisper-turbo"
os.environ.setdefault("HF_HOME", str(KLASOR / "modeller" / ".hf"))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

log = logging.getLogger("konusma")


def _cuda_dll_ekle():
    """pip ile gelen NVIDIA kütüphaneleri (cuBLAS, cuDNN) Windows'ta kendiliğinden bulunmuyor."""
    for d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):
        try:
            os.add_dll_directory(d)
        except OSError:
            pass
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")


_cuda_dll_ekle()

import ctranslate2  # noqa: E402
import pyaudiowpatch as pyaudio  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402
from faster_whisper.tokenizer import Tokenizer  # noqa: E402

HIZ = 16000
PARCA = 1600                    # 100 ms
ON_KAYIT = 3                    # tuşa basmadan önceki 300 ms de alınır (ilk hece kesilmesin)
# İpucu sayı içermesin: örnek sayılar sonuca sızabiliyor; ipucusuz ise model sözü tekrarlıyor (2026-10-16 denendi)
IPUCU = {"tr": " Mesafe metre cinsinden.", "en": " Distance in meters."}


def model_yolu(ek_klasor: str = "") -> Path | None:
    """ek_klasor: ayarlar.json'daki "whisper_klasoru" (başka bir programın indirdiği aynı model)."""
    for yol in [YEREL_MODEL] + ([Path(ek_klasor)] if ek_klasor else []):
        if (yol / "model.bin").exists():
            return yol
    return None


def model_hazirla(ek_klasor: str = "") -> bool:
    """Gereken modeli indirir; bir şey indiyse True. Ekran kartı yoksa büyük model inmez
    ('small' model Tanima açılırken kendisi iner, ~480 MB)."""
    if ctranslate2.get_cuda_device_count() > 0 and model_yolu(ek_klasor) is None:
        model_indir()
        return True
    if ctranslate2.get_cuda_device_count() == 0:
        kucuk_model()
    return False


def kucuk_model() -> "WhisperModel":
    """İşlemci modeli. Önce yalnız diskten açılır: indirildikten sonra her açılışta internete sorulmasın
    (2026-10-17 hata.log'da her açılışta Hugging Face istekleri görüldü). Diskte yoksa bir kez indirilir."""
    ayar = dict(device="cpu", compute_type="int8", download_root=str(KLASOR / "modeller" / "whisper-small"),
                revision="536b0662742c02347bc0e980a01041f333bce120")
    try:
        return WhisperModel("Systran/faster-whisper-small", local_files_only=True, **ayar)
    except Exception:  # noqa: BLE001
        return WhisperModel("Systran/faster-whisper-small", **ayar)


def model_indir():
    """Sürüm sabit: depo sonradan değişse bile test edilen dosyalar iner."""
    from huggingface_hub import snapshot_download
    snapshot_download("mobiuslabsgmbh/faster-whisper-large-v3-turbo", local_dir=str(YEREL_MODEL),
                      revision="0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",          # CanYouSpeak ile aynı
                      allow_patterns=["*.json", "*.bin", "*.txt", "README.md"])    # çalıştırılabilir dosya inmesin


class Tanima:
    PENCERE_EN_AZ = 1000        # mel karesi (10 ms): en az 10 sn
    PAY = 300                   # sözün ardına 3 sn sessizlik

    def __init__(self, dil: str = "tr", ek_klasor: str = ""):
        self.cihaz = None
        yol = model_yolu(ek_klasor)
        if yol and ctranslate2.get_cuda_device_count() > 0:
            try:
                self.model = WhisperModel(str(yol), device="cuda", compute_type="int8_float16")
                self.cihaz = "gpu"
            except Exception:  # noqa: BLE001
                log.exception("whisper cuda açılamadı, işlemciye düşülüyor")
        if self.cihaz is None:
            self.model = kucuk_model()
            self.cihaz = "cpu"
        self.dil_ayarla(dil)

    def dil_ayarla(self, dil: str):
        tk = Tokenizer(self.model.hf_tokenizer, True, task="transcribe", language=dil)
        self._tk = tk
        self._bas = ([tk.sot_prev] + tk.encode(IPUCU.get(dil, IPUCU["en"])) + list(tk.sot_sequence)
                     + [tk.no_timestamps])

    def yaziya(self, pcm: np.ndarray) -> str:
        """pcm: 16 kHz mono float32."""
        m = self.model
        ozellik = m.feature_extractor(pcm)
        n = min(3000, max(self.PENCERE_EN_AZ, int(np.ceil((ozellik.shape[1] + self.PAY) / 100) * 100)))
        girdi = np.zeros((ozellik.shape[0], n), np.float32)
        girdi[:, :min(n, ozellik.shape[1])] = ozellik[:, :n]
        kod = m.model.encode(ctranslate2.StorageView.from_array(girdi[None]), to_cpu=False)
        r = m.model.generate(kod, [self._bas], beam_size=3, return_no_speech_prob=True, suppress_blank=True,
                             no_repeat_ngram_size=3, max_length=64)[0]
        if r.no_speech_prob > 0.7:
            return ""
        return self._tk.decode([t for t in r.sequences_ids[0] if t < self._tk.eot]).strip()


class Mikrofon:
    """Hep açık durur; tuşa basılınca toplanmaya başlar (önceki 300 ms dahil)."""

    def __init__(self, ad_parcasi: str = ""):
        self._pa = pyaudio.PyAudio()
        idx = None
        if ad_parcasi:
            mme = self._pa.get_host_api_info_by_type(pyaudio.paMME)["index"]
            for i in range(self._pa.get_device_count()):
                d = self._pa.get_device_info_by_index(i)
                if d["hostApi"] == mme and d["maxInputChannels"] > 0 and ad_parcasi.lower()[:31] in d["name"].lower():
                    idx = i
                    break
        self.ad = (self._pa.get_device_info_by_index(idx) if idx is not None
                   else self._pa.get_default_input_device_info())["name"]
        self._kilit = threading.Lock()
        self._once = collections.deque(maxlen=ON_KAYIT)
        self._kayit: list[bytes] | None = None
        self._akis = self._pa.open(format=pyaudio.paInt16, channels=1, rate=HIZ, input=True,
                                   input_device_index=idx, frames_per_buffer=PARCA,
                                   stream_callback=self._geri)

    def _geri(self, veri, kare, zaman, durum):
        with self._kilit:
            if self._kayit is not None:
                self._kayit.append(veri)
            else:
                self._once.append(veri)
        return None, pyaudio.paContinue

    def basla(self):
        with self._kilit:
            self._kayit = list(self._once)

    def bitir(self) -> np.ndarray:
        with self._kilit:
            parcalar, self._kayit = self._kayit or [], None
        return np.frombuffer(b"".join(parcalar), np.int16).astype(np.float32) / 32768.0

    def kapat(self):
        try:
            self._akis.stop_stream()
            self._akis.close()
            self._pa.terminate()
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def liste() -> list[str]:
        pa = pyaudio.PyAudio()
        try:
            mme = pa.get_host_api_info_by_type(pyaudio.paMME)["index"]
            return sorted({pa.get_device_info_by_index(i)["name"] for i in range(pa.get_device_count())
                           if pa.get_device_info_by_index(i)["hostApi"] == mme
                           and pa.get_device_info_by_index(i)["maxInputChannels"] > 0})
        finally:
            pa.terminate()


EN_KISA_SN = 0.35
EN_DUSUK_SEVIYE = 0.004


def seviye(pcm: np.ndarray) -> float:
    return float(np.sqrt(np.mean(pcm * pcm))) if len(pcm) else 0.0


def ses_var_mi(pcm: np.ndarray) -> bool:
    """Çok kısa ya da sessiz kayıt Whisper'a gitmesin (sessizlikte söz uyduruyor)."""
    return len(pcm) >= HIZ * EN_KISA_SN and seviye(pcm) > EN_DUSUK_SEVIYE
