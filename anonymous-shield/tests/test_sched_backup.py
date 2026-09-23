# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Agendador (parse/disparo) + backup (roundtrip zip)."""
import datetime as _dt
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from anonshield.config import AppConfig, set_data_dir  # noqa: E402

set_data_dir(tempfile.mkdtemp(prefix="tstest_"))


def _make_app():
    from PyQt6.QtWidgets import QApplication
    from anonshield.gui import MainWindow
    from anonshield.uilogic import UiLogic

    app = QApplication.instance() or QApplication([])
    cfg = AppConfig()
    cfg.password = "x"
    cfg.use_tor = False
    cfg.auto_connect = False

    class App(MainWindow, UiLogic):
        pass

    return app, App(cfg)


def test_sched_parse():
    from anonshield.uilogic import UiLogic

    p = UiLogic._sched_parse_hm
    assert p("08:00") == "08:00"
    assert p("8:00") == "08:00"
    assert p(" 23:59 ") == "23:59"
    assert p("24:00") == ""
    assert p("abc") == ""
    assert p("") == ""


def test_sched_dispara_on_uma_vez():
    app, w = _make_app()
    now = _dt.datetime.now().strftime("%H:%M")
    w.cfg.sched_enabled = True
    w.cfg.sched_on = now
    calls = []
    w.connect_tor = lambda: calls.append("on")
    w._sched_check()
    w._sched_check()  # segundo tick no mesmo minuto: nao repete
    assert calls == ["on"], calls


def test_sched_off_restaura():
    app, w = _make_app()
    now = _dt.datetime.now().strftime("%H:%M")
    w.cfg.sched_enabled = True
    w.cfg.sched_off = now
    w.connected = True
    w.disconnect_tor = lambda silent=False: calls.append("off")
    import anonshield.uilogic as _u
    calls = []
    w.disconnect_tor = lambda silent=False: calls.append("off")
    w.restore_internet = lambda: calls.append("net")
    w._sched_check()
    assert calls == ["off", "net"], calls


def test_sched_desligado_nao_faz_nada():
    app, w = _make_app()
    w.cfg.sched_enabled = False
    w.cfg.sched_on = _dt.datetime.now().strftime("%H:%M")
    w.connect_tor = lambda: (_ for _ in ()).throw(AssertionError("nao devia"))
    w._sched_check()


def test_backup_roundtrip():
    import zipfile as _zf

    app, w = _make_app()
    w.cfg.apps.append({"name": "t", "path": "C:\\t.exe",
                       "enabled": True, "custom": True})
    w.cfg.save()
    cfg_dir, files = w._profile_files()
    assert files, "sem arquivos de perfil"
    dest = os.path.join(tempfile.mkdtemp(), "bk.zip")
    with _zf.ZipFile(dest, "w", _zf.ZIP_DEFLATED) as z:
        for n in files:
            z.write(os.path.join(cfg_dir, n), n)
    names = _zf.ZipFile(dest).namelist()
    assert names and all("/" not in n and "\\" not in n for n in names)
    bad = [n for n in names if n not in ("config.enc", "vault.meta",
                                         "config.json", "users.meta")]
    assert not bad, bad
