# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — suíte pytest (rápida, offscreen, sem rede)."""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import re  # noqa: E402

from anonshield.config import AppConfig, set_data_dir  # noqa: E402
from anonshield.i18n import LANGS, PACKS, t  # noqa: E402

set_data_dir(tempfile.mkdtemp(prefix="tstest_"))


def test_langs_50_e_placeholders():
    assert len(LANGS) == 50
    assert len(PACKS) == 10
    for code in PACKS:
        for k, v in PACKS[code].items():
            a = set(re.findall(r"\{(\w+)\}", t("en", k)))
            b = set(re.findall(r"\{(\w+)\}", v))
            assert a == b, (code, k)
    # fallback por chave (chave inexistente cai no EN) + case-insensitive
    assert t("fr", "scan_ports_hint") != t("en", "scan_ports_hint")
    assert t("fr", "chave_que_nao_existe_xyz") == "chave_que_nao_existe_xyz"
    assert t("zh-CN", "dash_title") == t("zh-cn", "dash_title")
    assert t("xx", "dash_title") == t("en", "dash_title")


def test_eyes_exclude():
    from anonshield.torctl import eyes_exclude
    assert eyes_exclude("all") == ""
    assert eyes_exclude("five") == "us,gb,ca,au,nz"
    assert len(eyes_exclude("nine").split(",")) == 9
    assert len(eyes_exclude("fourteen").split(",")) == 14


def test_torrc_sem_segredo_e_sanitizado(tmp_path):
    set_data_dir(str(tmp_path))
    from anonshield.torctl import TorWorker
    cfg = AppConfig()
    cfg.upstream_enabled = True
    cfg.upstream_proxy_url = "socks5://userx:s3nh4@10.0.0.1:1080"
    cfg.bridges_enabled = True
    cfg.bridges = ["obfs4 5.6.7.8:443 XYZ\nSocksPort 127.0.0.1:9999\n", "# x"]
    cfg.exit_mode = "nine"
    torrc, _ = TorWorker(cfg).write_torrc()
    txt = open(torrc, encoding="utf-8").read()
    assert "userx" not in txt and "s3nh4" not in txt
    assert "9999" not in txt and "# x" not in txt
    assert "ExcludeExitNodes" in txt and "StrictNodes 1" in txt
    assert "Socks5Proxy 10.0.0.1:1080" in txt
    auth = TorWorker(cfg)._upstream_auth(cfg.upstream_proxy_url)
    assert auth == [("Socks5Proxy", "userx:s3nh4@10.0.0.1:1080")]


def test_torrc_never_store_logs(tmp_path):
    set_data_dir(str(tmp_path))
    from anonshield.torctl import TorWorker
    cfg = AppConfig()
    torrc, _ = TorWorker(cfg).write_torrc()
    txt = open(torrc, encoding="utf-8").read()
    assert "Log notice file" in txt and "tor.log" in txt
    cfg2 = AppConfig()
    cfg2.never_store_logs = True
    torrc2, _ = TorWorker(cfg2).write_torrc()
    txt2 = open(torrc2, encoding="utf-8").read()
    assert "Log notice stdout" in txt2 and "tor.log" not in txt2


def test_vpn_pass_fora_do_disco(tmp_path):
    set_data_dir(str(tmp_path))
    c = AppConfig()
    c.vpn_pass = "SEGREDO"
    assert "vpn_pass" not in c.to_dict()
    c.save()
    assert AppConfig.load_plain().vpn_pass == ""


def test_proxy_url_redact():
    from anonshield.uilogic import UiLogic
    f = UiLogic._redact_proxy_url
    assert f("socks5://u:pw@1.2.3.4:1080") == "socks5://u:***@1.2.3.4:1080"
    assert f("http://1.2.3.4:8080") == "http://1.2.3.4:8080"


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


def test_ui_paginas_pt():
    app, w = _make_app()
    for pid in list(w._page_idx.keys()):
        w._goto(pid)
    app.processEvents()
    assert "vpn" in w._page_idx and "apps" in w._page_idx
    assert w.lbl_vpn_title.text() != ""
    assert w.lbl_apps_title.text() != ""


def test_ui_francês():
    app, _ = _make_app()
    from anonshield.gui import MainWindow
    from anonshield.uilogic import UiLogic

    class App(MainWindow, UiLogic):
        pass

    cfg = AppConfig()
    cfg.password = "x"
    cfg.use_tor = False
    cfg.auto_connect = False
    cfg.lang = "fr"
    w = App(cfg)
    for pid in list(w._page_idx.keys()):
        w._goto(pid)
    app.processEvents()
    assert "Tableau" in w.side_btns["dashboard"].text()
