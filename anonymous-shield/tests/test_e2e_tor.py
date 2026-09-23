# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""E2E real do Tor (lento, rede de verdade). Roda só com ANONSHIELD_E2E=1.

Uma sessão Tor compartilhada: bootstrap 100% + saída IsTor +
Chrome headless via Tor + proxy ida/volta.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from anonshield.config import AppConfig, set_data_dir  # noqa: E402

NEED_E2E = os.environ.get("ANONSHIELD_E2E") == "1"
pytestmark = pytest.mark.skipif(not NEED_E2E, reason="só com ANONSHIELD_E2E=1")

set_data_dir(tempfile.mkdtemp(prefix="e2e_"))
PORT = 9150


@pytest.fixture(scope="module")
def tor():
    from PyQt6.QtCore import QCoreApplication
    from anonshield.torctl import TorThread, TorWorker

    app = QCoreApplication([])
    cfg = AppConfig()
    cfg.bridges_enabled = False
    cfg.upstream_enabled = False
    w = TorWorker(cfg)
    state = {"done": False, "ok": False, "err": ""}
    w.connected.connect(lambda: state.update(done=True, ok=True))
    w.failed.connect(lambda m: state.update(done=True, err=m[:200]))
    th = TorThread(w)
    th.start()
    t0 = time.time()
    while not state["done"] and time.time() - t0 < 240:
        app.processEvents()
        time.sleep(0.5)
    assert state["ok"], f"bootstrap falhou: {state['err']}"
    print(f"\nBOOTSTRAP OK em {time.time()-t0:.0f}s")
    yield {"port": cfg.socks_port}
    w.stop()
    w.kill_tor()
    th.wait(8000)


def test_saida_istor(tor):
    import requests
    p = f"socks5h://127.0.0.1:{tor['port']}"
    j = requests.get("https://check.torproject.org/api/ip",
                     proxies={"http": p, "https": p}, timeout=40).json()
    assert j.get("IsTor") is True, j
    print(f"\nSAIDA IsTor OK: {j.get('IP')}")


def _chrome():
    for c in (shutil.which("chrome"),
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
        if c and os.path.exists(c):
            return c
    return ""


def test_chrome_via_tor(tor):
    ch = _chrome()
    if not ch:
        pytest.skip("sem Chrome")
    prof = os.path.join(tempfile.mkdtemp(), "prof")
    os.makedirs(prof, exist_ok=True)
    r = subprocess.run(
        [ch, "--headless=new", "--no-sandbox", "--disable-gpu",
         f"--proxy-server=socks5://127.0.0.1:{tor['port']}",
         f"--user-data-dir={prof}", "--dump-dom",
         "https://check.torproject.org/api/ip"],
        capture_output=True, text=True, timeout=90)
    assert r.returncode == 0, r.stderr[:300]
    body = r.stdout
    start = body.find("{")
    j = json.loads(body[start:body.find("}", start) + 1])
    assert j.get("IsTor") is True, j
    print(f"\nCHROME IsTor OK: {j.get('IP')}")


def test_proxy_ida_e_volta():
    from anonshield import sysprotect as sp
    prev = sp.get_proxy()
    try:
        sp.set_proxy(9150)
        assert sp.is_our_proxy(9150)
    finally:
        sp.restore_proxy(prev)
    print("\nPROXY roundtrip OK")
