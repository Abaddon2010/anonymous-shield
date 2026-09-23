# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Sidebar arrastavel: ordem, mover, reset, persistencia."""
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


def test_nav_ordem_padrao():
    app, w = _make_app()
    order = [p for _, p in w._nav_order()]
    assert order == ["dashboard", "home", "total", "apps", "bridges", "proxy",
                     "dns", "vpn", "scan", "logs", "diag", "update", "about"], order
    assert set(w.side_btns) == set(order)


def test_nav_move_e_persiste():
    from anonshield.config import AppConfig as _AC

    app, w = _make_app()
    w._nav_move("vpn", "dashboard")
    order = ["%s:%s" % (s, p) for s, p in w._nav_order()]
    assert order[0] == "sec_main:vpn", order[:3]
    assert w.cfg.sidebar_order[0] == "sec_main:vpn"
    cfg2 = _AC.load("x")
    assert cfg2.sidebar_order[0] == "sec_main:vpn"
    w._nav_reset()
    assert w.cfg.sidebar_order == []
    assert [p for _, p in w._nav_order()][0] == "dashboard"


def test_nav_textos_pt():
    app, w = _make_app()
    assert "Organizar" in w.btn_nav_edit.text()
    assert w.btn_nav_reset.toolTip() == "Restaurar ordem do menu"
