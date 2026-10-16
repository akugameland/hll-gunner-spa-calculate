"""ekran.py'yi kayıtlı oyun görüntüleriyle dener: python test/test_ekran.py [görüntü ...]"""
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ekran  # noqa: E402

okuyucu = ekran.EkranOkuyucu()
dosyalar = sys.argv[1:] or [str(Path(__file__).parent / "ornek_1080p.webp")]
for yol in dosyalar:
    im = Image.open(yol).convert("RGBA")
    for boyut in (None, (1280, 720), (2560, 1440)):
        r = im if boyut is None else im.resize(boyut, Image.LANCZOS)
        a = np.asarray(r)
        h, w = a.shape[:2]
        bolge = a[int(h * (1 - ekran.BOLGE_ALT)):, int(w * (1 - ekran.BOLGE_SAG)):]
        t = time.perf_counter()
        o = okuyucu.oku(bolge)
        print(f"{Path(yol).name} {w}x{h}: panel={o.panel} yukselis={o.yukselis} kirmizi={o.kirmizi} "
              f"silah={o.silah!r} tank={o.tank} ({time.perf_counter() - t:.3f} sn)")
