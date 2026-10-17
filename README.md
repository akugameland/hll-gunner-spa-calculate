# HLL Gunner SPA Calculate

**English** · [Türkçe](#türkçe)

Voice-driven aiming assistant for **self-propelled artillery (SPA)** in *Hell Let Loose*.
Hold a push-to-talk key, say the distance, release. The app reads the gun sight panel on your
screen and shows, as a subtitle, the elevation (MIL) you need to set. When you reach it, it turns
green: **✔ FIRE**.

- Reads the bottom-right gun panel continuously: current **ELEVATION**, the red **tilt MIL** and the
  primary weapon (to detect the tank). Works at any resolution (tested 720p / 1080p / 1440p).
- Speech: "four fifty", "four hundred and fifty", "four five zero", "450 plus 20" (target 20 m higher),
  "300 down 15", "cancel". You can also type the distance.
- The result follows your tank's tilt live: no need to re-enter anything when the hull moves.
- Turkish and English (interface, subtitles and speech).
- The subtitle is always on top, lets mouse clicks pass through and never takes focus.

The math is the formula of [HLL SPA Calculator](https://l1tku.github.io/hll-spa-calculator/) by
**litku** (v2.2.4, HLL Update 21), MIT licensed. It was checked against that site's own code on 3600
cases (6 tanks × 20 distances × 6 tilts × 5 height differences): all identical (`test/test_hesap.py`).

## Privacy

- Everything runs **on your PC**. Speech recognition (Whisper) and screen reading (Windows' built-in
  OCR) are local. Nothing is sent anywhere while the app runs.
- The only internet use is the one-time model download during setup (Hugging Face, pinned version).
- Only a small bottom-right area of the screen is read, in memory. No screenshots are saved.
- Key presses are only used to detect your push-to-talk key. Nothing is logged or saved.
- It does not touch the game's memory or files; it only looks at the screen like you do.
- Settings (`ayarlar.json`) and the error log (`hata.log`) stay local and are not part of the repo.

## Requirements

- Windows 10/11
- Recommended: NVIDIA GPU (4 GB is enough). Without one it runs a smaller model on the CPU.
- Disk: ~1.6 GB model (GPU) or ~0.5 GB (CPU) + ~2 GB Python packages
- Run the game in **Borderless window** mode. In exclusive fullscreen no window can appear on top.

## Install

1. Download the repo (Code → Download ZIP) and extract it.
2. Double-click `BASLAT.bat`. On first start it runs `KURULUM.bat` by itself: installs Python 3.12 if it
   is missing (via winget, no admin rights needed), the packages and the speech model.
3. Next times, `BASLAT.bat` opens the app directly.

If Python can't be installed automatically, install
[Python 3.12.10](https://www.python.org/downloads/release/python-31210/) ("Windows installer (64-bit)",
tick "Add python.exe to PATH") and run `KURULUM.bat` again.

## Use

1. Sit in the SPA gunner seat. The **Read from screen** box should show ELEVATION, red tilt and the tank.
2. Hold the push-to-talk key (default **F9**; click the button to change it, mouse side buttons work too),
   say the distance, release.
3. Raise/lower the gun until the subtitle says **✔ FIRE**.

**Nothing happens when you press the key?** Alt+Tab to the app window: the "Last push-to-talk" line shows
whether the key was detected. If the game runs as administrator a red warning appears: right-click `BASLAT.bat`
→ Run as administrator. "No speech heard" means the wrong microphone is selected. Details are in `hata.log`
(each push-to-talk is logged with its duration, level and the recognized text; never other keys or audio).

Not tested in the real game yet for every tank: only the Sherman 105 HUD ("105MM HOWITZER") was
verified from a screenshot. If the tank is detected wrong, pick it manually in the app.

---

## Türkçe

*Hell Let Loose*'ta **kendinden hareketli top (SPA)** için sesli nişan yardımcısı.
Bas-konuş tuşunu basılı tut, mesafeyi söyle, bırak. Program ekrandaki nişangâh panelini okur ve
namluyu kaç MIL'e getirmen gerektiğini altyazı olarak yazar. Değere gelince yeşil olur: **✔ ATEŞ**.

- Sağ alttaki paneli sürekli okur: şu anki **ELEVATION**, kırmızı **eğim MIL** ve ana silah (tankı bulmak için).
  Her çözünürlükte çalışır (720p / 1080p / 1440p denendi).
- Ses: "dört yüz elli", "dört beş sıfır", "450 artı 20" (hedef 20 m yukarıda), "300 aşağı 15", "iptal".
  Mesafe elle de yazılabilir.
- Tank yatınca sonuç kendiliğinden yeniden hesaplanır.
- Türkçe ve İngilizce (arayüz, altyazı, ses).
- Altyazı hep en öndedir, fare tıklamalarını geçirir, oyunun odağını almaz.

Hesap, **litku**'nun [HLL SPA Calculator](https://l1tku.github.io/hll-spa-calculator/) formülüdür
(v2.2.4, HLL Update 21, MIT lisansı). Sitenin kendi koduyla 3600 durumda karşılaştırıldı, hepsi aynı.

**Gizlilik:** Her şey bilgisayarında çalışır; ses ve ekran hiçbir yere gönderilmez. İnternet yalnız
kurulumda modelin bir kez indirilmesi için kullanılır. Ekranın yalnız sağ alt köşesi bellekte okunur,
görüntü kaydedilmez. Oyunun belleğine ya da dosyalarına dokunmaz.

**Kurulum:** Depoyu indir (Code → Download ZIP), klasöre çıkar, `BASLAT.bat`'a çift tıkla. İlk açılışta
Python 3.12'yi (yoksa), paketleri ve ses modelini kendisi kurar. Oyunu **Kenarlıksız pencere** modunda çalıştır.

Ayrıntılı kullanım: [OKU_BENI.txt](OKU_BENI.txt)

## License

MIT. See [LICENSE](LICENSE) (includes the HLL SPA Calculator notice). Not affiliated with the makers
of Hell Let Loose.
