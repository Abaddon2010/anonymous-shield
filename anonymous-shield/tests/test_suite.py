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


def test_linux_nft_script_e_guards():
    from anonshield import sysprotect_linux as _lx
    ok = _lx.set_linux_guards(["1.2.3.4", " 2606:4700:4700::1111 ",
                               "nao-ip", "127.0.0.1", "10.0.0.1", "2001:db8::1",
                               "1.2.3.4; rm -rf /", ""])
    assert ok == ["1.2.3.4", "2606:4700:4700::1111"], ok
    s = _lx.build_nft_script(["1.2.3.4"], ["2606:4700:4700::1111"])
    assert "policy drop" in s and "1.2.3.4" in s and "2606:4700:4700::1111" in s
    assert "meta l4proto tcp" in s  # `tcp` puro é sintaxe inválida no nft
    assert "rm -rf" not in s and "table inet anonshield" in s
    assert "dport 53" not in s  # DNS bloqueado por padrão
    s2 = _lx.build_nft_script([], [])
    assert "255.255.255.254" in s2  # placeholder nunca vazio


def test_linux_proxy_sem_gsettings():
    import shutil
    from anonshield import sysprotect_linux as _lx
    if shutil.which("gsettings"):
        return  # só testa a guarda onde não há GNOME
    try:
        _lx.set_proxy(9150)
        raise AssertionError("deveria falhar sem gsettings")
    except RuntimeError:
        pass


def test_bridge_lines_from():
    from anonshield.uilogic import bridge_lines_from, bridge_valid
    txt = "copie isso\nobfs4 1.2.3.4:443 ABCDEF cert=x iat-mode=0\nlixo\nBridge webtunnel [::1]:443 XYZ\n"
    out = bridge_lines_from(txt)
    assert len(out) == 2 and out[0].startswith("obfs4")
    assert bridge_lines_from("nada aqui") == []
    good = "obfs4 185.177.207.233:11233 88DFC8F45500A56C740175A6604642CB50A83DAA cert=x iat-mode=0"
    assert bridge_valid(good)
    assert bridge_valid("Bridge " + good)
    assert not bridge_valid("obfs4 185.177.207.233:11233 cert=x")
    assert not bridge_valid("cRCX6rtbZvP2yLqf4Vh73epd66bKBetJ7gnNQjfqO6LFg")
    assert not bridge_valid("")


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


def test_i18n_chaves_novas():
    from anonshield.i18n import t
    keys = ["tab_about", "about_sub", "about_licenses", "about_gpl",
            "log_never", "log_never_hint", "log_never_ask",
            "log_br_none", "log_br_invalid", "log_br_tor_off", "log_br_no_pt",
            "upd_sha_required", "mode_stealth", "mode_desc_stealth",
            "mode_need_vpn", "route_bridges",
            "tip_dashboard", "tip_home", "tip_total", "tip_apps",
            "tip_bridges", "tip_proxy", "tip_dns", "tip_vpn", "tip_scan",
            "tip_logs", "tip_diag", "tip_update", "tip_about",
            "net_dns", "net_tcp", "net_http", "net_ok", "net_fail",
            "upd_repo_locked", "upd_repo_tip",
            "mode_stealth", "mode_desc_stealth", "mode_need_vpn",
            "br_mail", "br_tg",
            "duress_btn", "duress_desc", "duress_title", "duress_guest",
            "duress_ok", "duress_cleared", "duress_same", "duress_warn",
            "duress_remove_q",
            "pt_hint_win", "pt_hint_lin",
            "total_rollback"]
    for lang in ("pt-BR", "en", "es"):
        for k in keys:
            v = t(lang, k)
            assert v and v != k, (lang, k)


def test_net_full_structured():
    import os as _os
    import pytest as _pt
    if _os.environ.get("ANONSHIELD_NET") != "1":
        _pt.skip("rede direta só com ANONSHIELD_NET=1")
    from anonshield.sysprotect import test_direct_net_full
    d = test_direct_net_full()
    assert set(d) >= {"dns_ok", "tcp_ok", "http_ok", "text"}
    assert isinstance(d["text"], str) and d["text"]


def test_duress_ciclo(tmp_path, monkeypatch):
    import anonshield.config as _cfg
    import anonshield.users as _u
    monkeypatch.setattr(_cfg, "set_data_dir", lambda p: None)
    monkeypatch.setattr(_cfg, "app_dirs",
                        lambda: (str(tmp_path), str(tmp_path)))
    uid = _u.create_user("vitima", "senha-real-123")
    assert not _u.has_duress(uid)
    assert not _u.check_duress(uid, "qualquer-coisa")
    try:
        _u.set_duress(uid, "senha-real-123")
        raise AssertionError("igual à real deveria falhar")
    except ValueError:
        pass
    try:
        _u.set_duress(uid, "curta")
        raise AssertionError("curta deveria falhar")
    except ValueError:
        pass
    _u.set_duress(uid, "coacao-falsa-456")
    assert _u.has_duress(uid)
    assert _u.check_duress(uid, "coacao-falsa-456")
    assert not _u.check_duress(uid, "senha-real-123")
    assert _u.verify_user(uid, "senha-real-123")  # real intacta
    assert _u.duress_wipe(uid) is True
    assert _u.list_users() == []
    assert not os.path.exists(_u.user_dir(uid))
    assert _u.duress_wipe(uid) is False


def test_torrc_rejeita_bridge_invalida(tmp_path):
    set_data_dir(str(tmp_path))
    from anonshield.config import AppConfig as _AC
    from anonshield.torctl import TorWorker
    cfg = _AC()
    cfg.bridges_enabled = True
    cfg.bridges = ["obfs4 1.2.3.4:443 " + "B" * 40,
                   "obfs4 1.2.3.4:443 incompleta",
                   "lixo total"]
    torrc, _ = TorWorker(cfg).write_torrc()
    txt = open(torrc, encoding="utf-8").read()
    assert "UseBridges 1" in txt and "B" * 40 in txt
    assert "incompleta" not in txt and "lixo total" not in txt


def test_tor_pin_sha256(tmp_path):
    set_data_dir(str(tmp_path))
    from anonshield.config import AppConfig as _AC
    from anonshield import torctl as _tc
    from anonshield.torctl import TorWorker
    w = TorWorker(_AC())
    exe = _tc.tor_bin()
    assert os.path.exists(exe)
    assert w._verify_bundled_tor(exe) is True
    f1 = os.path.join(str(tmp_path), "a.bin")
    f2 = os.path.join(str(tmp_path), "b.bin")
    open(f1, "wb").write(b"conteudo-igual")
    open(f2, "wb").write(b"conteudo-igual")
    open(os.path.join(str(tmp_path), "c.bin"), "wb").write(b"adulterado!")
    import hashlib
    h = hashlib.sha256(b"conteudo-igual").hexdigest()
    assert _tc._tor_file_matches(f1, h) is True
    assert _tc._tor_file_matches(f2, h.upper()) is True
    assert _tc._tor_file_matches(os.path.join(str(tmp_path), "c.bin"), h) is False
    assert _tc._tor_file_matches(os.path.join(str(tmp_path), "nope.bin"), h) is False


def test_ovpn_mgmt_handshake():
    import socket
    from anonshield.sysprotect import _ovpn_mgmt_handshake
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    script = []

    def fake_server():
        c, _ = srv.accept()
        f = c.makefile("rwb", buffering=0)
        f.write(b">INFO:fake\n>PASSWORD:Need 'Auth' username/password\n")
        got = [f.readline(256) for _ in range(2)]
        script.extend(got)
        f.write(b">HOLD:Waiting for hold release\n")
        got2 = f.readline(256)
        script.append(got2)
        f.write(b"SUCCESS: hold release succeeded\n")
        f.close()
        c.close()
        srv.close()

    import threading
    t = threading.Thread(target=fake_server, daemon=True)
    t.start()
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    _ovpn_mgmt_handshake(s, "userx", "s3nh4")
    s.close()
    t.join(timeout=10)
    blob = b"".join(script)
    assert b'username "Auth" "userx"' in blob and b'password "Auth" "s3nh4"' in blob
    assert blob.strip().endswith(b"hold release")


def test_multiplataforma_nomes_e_paths():
    from anonshield import sysprotect as _sp
    assert "firefox" in _sp._FIREFOX_EXES and "firefox.exe" in _sp._FIREFOX_EXES
    assert "google-chrome" in _sp._CHROMIUM_EXES and "chrome.exe" in _sp._CHROMIUM_EXES
    apps = _sp.detect_apps()
    assert isinstance(apps, list)
    for a in apps:
        assert os.path.exists(_sp.expand(a["path"]))
