# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — janela principal PyQt6."""
from __future__ import annotations

import os
import socket
import subprocess
import threading
import time

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)

from . import __version__
from .config import AppConfig, AppEntry, SysProxy, app_dirs
from .i18n import LANGS, lang_label, t
from . import sysprotect
from .torctl import TorThread, TorWorker, wait_port
from .widgets import OnionWidget, SideItem, SparkWidget, ToggleSwitch

DASH_SECTIONS = (
    ("sec_main", ("dashboard", "home")),
    ("sec_net", ("total", "apps", "bridges", "proxy", "dns", "vpn")),
    ("sec_tools", ("scan", "logs", "diag", "update", "about")),
)

DARK_QSS = """
QMainWindow, QWidget#central { background: #0a0a1a; }
QWidget#main { background: #0a0a1a; }
QWidget { color: #f1f2f9; font-size: 13px; font-family: 'Segoe UI', 'Inter', sans-serif; }
/* ── sidebar ── */
QFrame#sidebar { background: #12122b; border-right: 1px solid #26264a; border-radius: 0; }
QFrame#brand { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e1b4b, stop:1 #2e1065); border: 1px solid #3b3670; border-radius: 14px; }
QLabel#brandLogo { background: rgba(139, 92, 246, 0.22); border: 1px solid #6d5bd0; border-radius: 20px; font-size: 22px; }
QLabel#brandName { color: white; font-size: 17px; font-weight: 800; }
QLabel#brandVer { color: #a5b4fc; font-size: 11px; }
QLabel#navsec { color: #b3a6e3; font-size: 10px; font-weight: bold; letter-spacing: 1px; padding: 10px 6px 2px 6px; }
/* ── cards ── */
QFrame#card { background: #151533; border: 1px solid #2b2b55; border-radius: 16px; }
QFrame#inner { background: #0f0f28; border: 1px solid #26264a; border-radius: 12px; }
QFrame#kpi { background: #151533; border: 1px solid #2b2b55; border-radius: 16px; }
QFrame#kpiAccent { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4c1d95, stop:1 #6d28d9); border: 1px solid #7c5ce0; border-radius: 16px; }
QFrame#kpi:hover, QFrame#kpiAccent:hover { border: 1px solid #a78bfa; }
QLabel#kpiTitle { color: #8f8fb0; font-size: 10px; font-weight: bold; letter-spacing: 1px; }
QLabel#kpiValue { color: white; font-size: 21px; font-weight: 800; }
QLabel#kpiSub { color: #9a9ab8; font-size: 11px; }
QLabel#muted { color: #8a8aa3; } QLabel#sec { color: #c2c2da; }
QLabel#title { font-size: 16px; font-weight: 800; }
QLabel#pagetitle { font-size: 19px; font-weight: 800; color: white; }
QLabel#crumb { color: #8a8aa3; font-size: 12px; }
/* ── topbar ── */
QFrame#topbar { background: #101026; border-bottom: 1px solid #23234a; border-radius: 0; }
QLabel#statusPill { font-weight: 800; font-size: 12px; padding: 7px 14px; border-radius: 14px; }
QPushButton { background: #20203e; border: 1px solid #2f2f5c; border-radius: 10px; padding: 8px 13px; color: #e6e6f5; }
QPushButton:hover { background: #2a2a52; border: 1px solid #3d3d75; }
QPushButton:disabled { color: #6a6a8c; }
QPushButton#accent { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8b5cf6, stop:1 #6d28d9); border: 1px solid #a78bfa; color: white; font-weight: 800; border-radius: 11px; }
QPushButton#accent:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a78bfa, stop:1 #7c3aed); }
QPushButton#success { background: #10b981; border: none; color: white; font-weight: bold; border-radius: 10px; }
QPushButton#success:hover { background: #34d399; }
QPushButton#danger { background: #3a1620; border: 1px solid #7f2d3d; color: #fca5a5; font-weight: bold; border-radius: 10px; }
QPushButton#danger:hover { background: #4c1d29; }
QPushButton#side { border: none; border-left: 3px solid transparent; border-radius: 0 10px 10px 0; text-align: left; padding: 10px 10px 10px 12px; font-size: 13px; color: #b9b9d4; background: transparent; }
QPushButton#side:hover { background: #3d2f6b; color: white; }
QPushButton#side:checked { background: #1c1540; color: white; font-weight: 800; border-left: 3px solid #a78bfa; }
QPushButton#row { border: none; border-bottom: 1px solid #26264a; border-radius: 0; text-align: left; padding: 14px 10px; font-size: 14px; background: transparent; }
QPushButton#row:hover { background: #1c1c40; }
QPushButton#row:disabled { color: #55556f; border-bottom: 1px solid #1c1c34; }
QPushButton#quick { background: #1a1a3a; border: 1px solid #2d2d5c; border-radius: 12px; padding: 14px 10px; font-size: 13px; text-align: left; }
QPushButton#quick:hover { background: #23234c; border: 1px solid #4c3a9c; }
QPushButton#burger { background: #1a1a38; border: 1px solid #2d2d5c; border-radius: 10px; font-size: 17px; font-weight: bold; }
QMessageBox { background-color: #151533; }
QMessageBox QLabel { color: #f1f2f9; background: transparent; }
QLabel#heroIcon { background: rgba(255, 255, 255, 0.16); border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 26px; font-size: 24px; color: white; }
QLabel#heroPill { color: white; background: rgba(0, 0, 0, 0.28); border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 10px; padding: 4px 12px; font-weight: 700; font-size: 12px; }
QLabel#heroHint { color: rgba(255, 255, 255, 0.85); font-size: 11px; }
QFrame#addrChip { background: rgba(0, 0, 0, 0.30); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 12px; }
QLabel#addrText { color: white; font-family: monospace; font-size: 15px; font-weight: 700; background: transparent; border: none; }
QPushButton#heroGhost { background: rgba(255, 255, 255, 0.14); border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 9px; color: white; font-size: 15px; }
QPushButton#heroGhost:hover { background: rgba(255, 255, 255, 0.28); }
QPushButton#heroGhost:disabled { color: rgba(255, 255, 255, 0.35); border: 1px solid rgba(255, 255, 255, 0.15); background: transparent; }
QLabel#featIcon { background: rgba(139, 92, 246, 0.16); border: 1px solid #4c3a9c; border-radius: 12px; font-size: 19px; }
QWidget#segbox { background: #0d0d22; border: 1px solid #2a2a52; border-radius: 12px; }
QPushButton#seg { background: transparent; border: none; border-radius: 8px; padding: 11px 8px; color: #b9b9d4; font-weight: 600; }
QPushButton#seg:hover { background: #23234c; color: white; }
QPushButton#seg:checked { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8b5cf6, stop:1 #6d28d9); color: white; font-weight: 800; }
QSpinBox { background: #0d0d22; border: 1px solid #2a2a52; border-radius: 9px; padding: 7px 8px; selection-background-color: #7c3aed; color: #eef; min-width: 90px; }
QSpinBox:focus { border: 1px solid #7c3aed; }
QSpinBox::up-button, QSpinBox::down-button { background: #23234c; border: none; border-radius: 6px; width: 24px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #34346a; }
QLabel#appLbl { font-size: 13px; }
QLabel#mono { font-family: monospace; font-size: 12px; }
QPushButton#miniDanger { background: transparent; border: 1px solid #5b2b35; color: #fca5a5; border-radius: 8px; padding: 4px 8px; font-weight: bold; }
QPushButton#miniDanger:hover { background: #2a1620; }
QScrollArea { border: none; background: transparent; }
QAbstractScrollArea { background: transparent; }
QAbstractScrollArea::viewport { background: transparent; }
QScrollArea#navscroll { background: #2d2350; border: 1px solid #3d3170; border-radius: 12px; }
QWidget#navhost { background: transparent; }
QScrollArea#pagescroll { background: transparent; border: none; }
QFrame#hero { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1e1e42, stop:1 #141430); border: 1px solid #3a3870; border-radius: 18px; }
QFrame#heroDash { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2e1065, stop:0.5 #4c1d95, stop:1 #1e1b4b); border: 1px solid #5b4bc4; border-radius: 18px; }
QLineEdit, QTextEdit, QPlainTextEdit { background: #0d0d22; border: 1px solid #2a2a52; border-radius: 9px; padding: 7px; selection-background-color: #7c3aed; color: #eef; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus { border: 1px solid #7c3aed; }
QProgressBar { border: 1px solid #34346a; border-radius: 7px; background: rgba(0,0,0,0.35); text-align: center; height: 12px; color: white; font-size: 10px; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f59e0b, stop:1 #fbbf24); border-radius: 6px; }
QComboBox { background: #1c1c40; border: 1px solid #2e2e5e; border-radius: 9px; padding: 6px 10px; color: #dedeF5; }
QComboBox QAbstractItemView { background: #1c1c40; color: white; selection-background-color: #7c3aed; border: 1px solid #3a3a6e; }
QComboBox#langTop {
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #23234e, stop:1 #1a1a38);
  border: 1px solid #3d3d75; border-radius: 12px;
  padding: 8px 12px 8px 14px; color: #e6e6f5; font-weight: 600; font-size: 13px;
}
QComboBox#langTop:hover { border: 1px solid #7c3aed; background: #26264f; }
QComboBox#langTop:focus { border: 1px solid #a78bfa; }
QComboBox#langTop::drop-down { border: none; border-left: 1px solid #3d3d75; width: 30px; }
QComboBox#langTop QAbstractItemView {
  background: #1c1c40; color: white; selection-background-color: #7c3aed;
  selection-color: white; border: 1px solid #4c3a9c; border-radius: 8px;
  padding: 4px; outline: 0;
}
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #34346a; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #4c4c92; }
QCheckBox { spacing: 8px; } QCheckBox::indicator { width: 18px; height: 18px; border-radius: 9px; border: 1px solid #4a4870; background: #1e1e3e; }
QCheckBox::indicator:checked { background: #10b981; border: 1px solid #10b981; }
"""

LIGHT_QSS = """
QMainWindow, QWidget#central { background: #edf0f7; }
QWidget#main { background: #edf0f7; }
QWidget { color: #0f172a; font-size: 13px; font-family: 'Segoe UI', 'Inter', sans-serif; }
QFrame#sidebar { background: #ffffff; border-right: 1px solid #dde3ef; border-radius: 0; }
QFrame#brand { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ede9fe, stop:1 #ddd6fe); border: 1px solid #c4b5fd; border-radius: 14px; }
QLabel#brandLogo { background: #ede9fe; border: 1px solid #a78bfa; border-radius: 20px; font-size: 22px; }
QLabel#brandName { color: #1e1b4b; font-size: 17px; font-weight: 800; }
QLabel#brandVer { color: #6d28d9; font-size: 11px; }
QLabel#navsec { color: #94a3b8; font-size: 10px; font-weight: bold; letter-spacing: 1px; padding: 10px 6px 2px 6px; }
QFrame#card { background: #ffffff; border: 1px solid #dbe1ee; border-radius: 16px; }
QFrame#inner { background: #f4f6fb; border: 1px solid #d5dcea; border-radius: 12px; }
QFrame#kpi { background: #ffffff; border: 1px solid #dbe1ee; border-radius: 16px; }
QFrame#kpiAccent { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6d28d9, stop:1 #8b5cf6); border: 1px solid #6d28d9; border-radius: 16px; }
QFrame#kpi:hover, QFrame#kpiAccent:hover { border: 1px solid #7c3aed; }
QLabel#kpiTitle { color: #94a3b8; font-size: 10px; font-weight: bold; letter-spacing: 1px; }
QFrame#kpiAccent QLabel#kpiTitle { color: rgba(255,255,255,0.75); }
QLabel#kpiValue { color: #0f172a; font-size: 21px; font-weight: 800; }
QFrame#kpiAccent QLabel#kpiValue { color: white; }
QLabel#kpiSub { color: #64748b; font-size: 11px; }
QFrame#kpiAccent QLabel#kpiSub { color: rgba(255,255,255,0.85); }
QLabel#muted { color: #94a3b8; } QLabel#sec { color: #475569; }
QLabel#title { font-size: 16px; font-weight: 800; }
QLabel#pagetitle { font-size: 19px; font-weight: 800; color: #0f172a; }
QLabel#crumb { color: #94a3b8; font-size: 12px; }
QFrame#topbar { background: #ffffff; border-bottom: 1px solid #dde3ef; border-radius: 0; }
QLabel#statusPill { font-weight: 800; font-size: 12px; padding: 7px 14px; border-radius: 14px; }
QPushButton { background: #e9edf5; border: 1px solid #d6dbe6; border-radius: 10px; padding: 8px 13px; color: #1e293b; }
QPushButton:hover { background: #dde4f0; }
QPushButton:disabled { color: #94a3b8; }
QPushButton#accent { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8b5cf6, stop:1 #6d28d9); border: 1px solid #6d28d9; color: white; font-weight: 800; border-radius: 11px; }
QPushButton#accent:hover { background: #8b5cf6; }
QPushButton#success { background: #059669; border: none; color: white; font-weight: bold; border-radius: 10px; }
QPushButton#danger { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; font-weight: bold; border-radius: 10px; }
QPushButton#side { border: none; border-left: 3px solid transparent; border-radius: 0 10px 10px 0; text-align: left; padding: 10px 10px 10px 12px; font-size: 13px; color: #475569; background: transparent; }
QPushButton#side:hover { background: #eef2ff; color: #1e1b4b; }
QPushButton#side:checked { background: #ede9fe; color: #4c1d95; font-weight: 800; border-left: 3px solid #7c3aed; }
QPushButton#row { border: none; border-bottom: 1px solid #e2e8f0; border-radius: 0; text-align: left; padding: 14px 10px; font-size: 14px; background: transparent; }
QPushButton#row:hover { background: #f1f5f9; }
QPushButton#row:disabled { color: #94a3b8; border-bottom: 1px solid #eef2f7; }
QPushButton#quick { background: #f1f5f9; border: 1px solid #dbe1ee; border-radius: 12px; padding: 14px 10px; font-size: 13px; text-align: left; color: #1e293b; }
QPushButton#quick:hover { background: #ede9fe; border: 1px solid #a78bfa; }
QPushButton#burger { background: #eef2ff; border: 1px solid #dbe1ee; border-radius: 10px; font-size: 17px; font-weight: bold; }
QMessageBox { background-color: #ffffff; }
QMessageBox QLabel { color: #0f172a; background: transparent; }
QLabel#heroIcon { background: rgba(255, 255, 255, 0.16); border: 1px solid rgba(255, 255, 255, 0.4); border-radius: 26px; font-size: 24px; color: white; }
QLabel#heroPill { color: white; background: rgba(0, 0, 0, 0.28); border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 10px; padding: 4px 12px; font-weight: 700; font-size: 12px; }
QLabel#heroHint { color: rgba(255, 255, 255, 0.85); font-size: 11px; }
QFrame#addrChip { background: rgba(0, 0, 0, 0.30); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 12px; }
QLabel#addrText { color: white; font-family: monospace; font-size: 15px; font-weight: 700; background: transparent; border: none; }
QPushButton#heroGhost { background: rgba(255, 255, 255, 0.14); border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 9px; color: white; font-size: 15px; }
QPushButton#heroGhost:hover { background: rgba(255, 255, 255, 0.28); }
QPushButton#heroGhost:disabled { color: rgba(255, 255, 255, 0.35); border: 1px solid rgba(255, 255, 255, 0.15); background: transparent; }
QLabel#featIcon { background: #ede9fe; border: 1px solid #c4b5fd; border-radius: 12px; font-size: 19px; }
QWidget#segbox { background: #f1f5f9; border: 1px solid #d5dcea; border-radius: 12px; }
QPushButton#seg { background: transparent; border: none; border-radius: 8px; padding: 11px 8px; color: #475569; font-weight: 600; }
QPushButton#seg:hover { background: #e2e8f0; }
QPushButton#seg:checked { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8b5cf6, stop:1 #6d28d9); color: white; font-weight: 800; }
QSpinBox { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 9px; padding: 7px 8px; selection-background-color: #7c3aed; color: #0f172a; min-width: 90px; }
QSpinBox:focus { border: 1px solid #7c3aed; }
QSpinBox::up-button, QSpinBox::down-button { background: #eef2ff; border: none; border-radius: 6px; width: 24px; }
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #dde4f0; }
QLabel#appLbl { font-size: 13px; }
QLabel#mono { font-family: monospace; font-size: 12px; }
QPushButton#miniDanger { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; border-radius: 8px; padding: 4px 8px; font-weight: bold; }
QComboBox#langTop { background: #ffffff; border: 1px solid #c9d2e8; border-radius: 12px; padding: 8px 12px 8px 14px; color: #1e293b; font-weight: 600; font-size: 13px; }
QComboBox#langTop:hover { border: 1px solid #7c3aed; }
QComboBox#langTop:focus { border: 1px solid #6d28d9; }
QComboBox#langTop::drop-down { border: none; border-left: 1px solid #dbe1ee; width: 30px; }
QComboBox#langTop QAbstractItemView { background: white; color: #0f172a; selection-background-color: #7c3aed; selection-color: white; border: 1px solid #a78bfa; border-radius: 8px; padding: 4px; outline: 0; }
QScrollArea { border: none; background: transparent; }
QAbstractScrollArea { background: transparent; }
QAbstractScrollArea::viewport { background: transparent; }
QScrollArea#navscroll { background: transparent; border: none; }
QWidget#navhost { background: transparent; }
QScrollArea#pagescroll { background: transparent; border: none; }
QFrame#hero { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #e9edf6); border: 1px solid #c9d2e8; border-radius: 18px; }
QFrame#heroDash { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4c1d95, stop:0.5 #6d28d9, stop:1 #7c3aed); border: 1px solid #6d28d9; border-radius: 18px; }
QFrame#heroDash QLabel { color: white; }
QLineEdit, QTextEdit, QPlainTextEdit { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 9px; padding: 7px; selection-background-color: #7c3aed; color: #0f172a; }
QProgressBar { border: 1px solid #d6dbe6; border-radius: 7px; background: rgba(255,255,255,0.6); text-align: center; height: 12px; font-size: 10px; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b45309, stop:1 #f59e0b); border-radius: 6px; }
QComboBox { background: #eef2ff; border: 1px solid #d6dbe6; border-radius: 9px; padding: 6px 10px; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 5px; min-height: 30px; }
QCheckBox { spacing: 8px; } QCheckBox::indicator { width: 18px; height: 18px; border-radius: 9px; border: 1px solid #94a3b8; background: #ffffff; }
QCheckBox::indicator:checked { background: #059669; border: 1px solid #059669; }
"""


def _dark_titlebar(w) -> None:
    """Barra de título escura (Win10 20H1+/Win11) p/ combinar com o tema.

    Mantém os botões nativos (min/max/fechar). Best-effort: falha em silêncio.
    """
    try:
        import ctypes as _ct
        hwnd = int(w.winId() or 0)
        if not hwnd:
            return
        one = _ct.c_int(1)
        _dwm = _ct.windll.dwmapi.DwmSetWindowAttribute
        for _attr in (20, 19):  # USE_IMMERSIVE_DARK_MODE (Win11, Win10)
            try:
                if _dwm(hwnd, _attr, _ct.byref(one), _ct.sizeof(one)) == 0:
                    break
            except Exception:
                continue
        try:  # legenda roxo-escura + texto branco (Win11)
            cap = _ct.c_int(0x4B1B1E)  # BGR de #1e1b4b
            txt = _ct.c_int(0xFFFFFF)
            _dwm(hwnd, 35, _ct.byref(cap), _ct.sizeof(cap))
            _dwm(hwnd, 36, _ct.byref(txt), _ct.sizeof(txt))
        except Exception:
            pass
    except Exception:
        pass


def _card() -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    return f


def _inner() -> QFrame:
    f = QFrame()
    f.setObjectName("inner")
    return f


def _mkbtn(text: str, obj: str = "", min_h: int = 0) -> QPushButton:
    b = QPushButton(text)
    if obj:
        b.setObjectName(obj)
    if min_h:
        b.setMinimumHeight(min_h)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


class PassDialog(QDialog):
    """Diálogo de senha mestra (criar / pedir / trocar) — visual dashboard."""

    def __init__(self, parent, mode: str, lang: str):
        super().__init__(parent)
        title = t(lang, {
            "create": "vault_create_title",
            "ask": "vault_ask_title",
            "change": "vault_change_title",
        }[mode])
        self.setWindowTitle(title)
        self.setObjectName("login")
        self.setMinimumWidth(420)
        self.setMinimumHeight(300)
        # Reusa o visual premium do login (fundo escuro + gradiente).
        try:
            self.setStyleSheet(LOGIN_QSS)
        except NameError:
            pass
        self._lang = lang
        self._mode = mode
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # faixa superior em gradiente
        hero = QFrame()
        hero.setObjectName("hero")
        hero.setFixedHeight(108)
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(24, 16, 24, 14)
        hl.setSpacing(2)
        hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo = QLabel("🔐")
        logo.setObjectName("logo")
        logo.setFixedSize(48, 48)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl = QLabel(title)
        ttl.setObjectName("appname")
        ttl.setStyleSheet("font-size: 17px;")
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl.setWordWrap(True)
        for w in (logo, ttl):
            row = QHBoxLayout()
            row.addStretch(1)
            row.addWidget(w)
            row.addStretch(1)
            hl.addLayout(row)
        root.addWidget(hero)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 18, 24, 20)
        bl.setSpacing(10)
        desc = QLabel(t(lang, {
            "create": "vault_create_text",
            "ask": "vault_ask_text",
            "change": "vault_change_text",
        }[mode]))
        desc.setObjectName("empdesc")
        desc.setWordWrap(True)
        bl.addWidget(desc)

        self.edits: list[QLineEdit] = []
        labels = {"create": ("vault_new", "vault_confirm"), "ask": ("vault_pass",),
                  "change": ("vault_current", "vault_new", "vault_confirm")}[mode]
        for i, key in enumerate(labels):
            fl = QLabel(t(lang, key))
            fl.setObjectName("fld")
            bl.addWidget(fl)
            row = QHBoxLayout()
            row.setSpacing(8)
            ed = QLineEdit()
            ed.setObjectName("pass")
            ed.setEchoMode(QLineEdit.EchoMode.Password)
            ed.setPlaceholderText("••••••••")
            ed.setMinimumHeight(42)
            if i == 0:
                ed.setFocus()
            row.addWidget(ed, 1)
            eye = QPushButton("👁")
            eye.setObjectName("ghost")
            eye.setCheckable(True)
            eye.setFixedSize(46, 42)
            eye.setCursor(Qt.CursorShape.PointingHandCursor)
            eye.toggled.connect(lambda on, e=ed: (e.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)))
            def _eye(on, btn=eye):
                btn.setText("🙈" if on else "👁")
            eye.toggled.connect(_eye)
            row.addWidget(eye)
            bl.addLayout(row)
            self.edits.append(ed)
        if len(self.edits) == 1:
            self.edits[0].returnPressed.connect(self.accept)
        else:
            for e in self.edits:
                e.textChanged.connect(lambda *_: self._live())
            self.edits[-1].returnPressed.connect(self._try_accept)

        self.lbl_warn = QLabel("")
        self.lbl_warn.setObjectName("error")
        self.lbl_warn.setWordWrap(True)
        self.lbl_warn.setVisible(False)
        bl.addWidget(self.lbl_warn)

        brow = QHBoxLayout()
        brow.setSpacing(10)
        btn_cancel = QPushButton(t(lang, "cancel") if t(lang, "cancel") != "cancel" else "Cancelar")
        btn_cancel.setObjectName("ghost")
        btn_cancel.setMinimumHeight(44)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("→  OK")
        btn_ok.setObjectName("primary")
        btn_ok.setMinimumHeight(44)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._try_accept)
        brow.addWidget(btn_cancel)
        brow.addWidget(btn_ok, 1)
        bl.addLayout(brow)

        if mode == "ask":
            hint = QLabel(t(lang, "vault_forgot_hint"))
            hint.setWordWrap(True)
            hint.setObjectName("foot")
            bl.addWidget(hint)
        bl.addStretch(1)
        root.addWidget(body, 1)
        _dark_titlebar(self)

    def _live(self) -> None:
        a = [e.text() for e in self.edits]
        if self._mode == "create" and len(a) == 2:
            if a[1] and a[0] != a[1]:
                self.lbl_warn.setText("✗ " + t(self._lang, "vault_mismatch"))
                self.lbl_warn.setVisible(True)
            elif a[0] and len(a[0]) < 8:
                self.lbl_warn.setText("✗ " + t(self._lang, "vault_short"))
                self.lbl_warn.setVisible(True)
            else:
                self.lbl_warn.setVisible(False)
        elif self._mode == "change" and len(a) == 3:
            _, n, c = a
            if c and n != c:
                self.lbl_warn.setText("✗ " + t(self._lang, "vault_mismatch"))
                self.lbl_warn.setVisible(True)
            elif n and len(n) < 8:
                self.lbl_warn.setText("✗ " + t(self._lang, "vault_short"))
                self.lbl_warn.setVisible(True)
            else:
                self.lbl_warn.setVisible(False)

    def _try_accept(self) -> None:
        vals = [e.text() for e in self.edits]
        if self._mode == "create":
            if len(vals[0]) < 8 or vals[0] != vals[1]:
                self._live()
                self.lbl_warn.setVisible(True)
                if not self.lbl_warn.text():
                    self.lbl_warn.setText("✗ " + t(self._lang, "vault_mismatch"))
                return
        if self._mode == "change":
            if len(vals[1]) < 8 or vals[1] != vals[2]:
                self._live()
                self.lbl_warn.setVisible(True)
                if not self.lbl_warn.text():
                    self.lbl_warn.setText("✗ " + t(self._lang, "vault_mismatch"))
                return
        self.accept()

    def values(self) -> list[str]:
        return [e.text() for e in self.edits]


class MainWindow(QMainWindow):
    PAGES = ("dashboard", "home", "total", "apps", "bridges", "proxy", "dns", "vpn", "scan", "logs", "diag", "update", "about")
    PAGE_ORDER = ("dashboard", "home", "total", "apps", "bridges", "proxy", "dns", "vpn", "scan", "logs", "diag", "update", "about")
    # Despachante thread-safe p/ UI (emitir de qualquer thread é seguro).
    _ui_call = pyqtSignal(object)

    def __init__(self, cfg: AppConfig):
        super().__init__()
        try:
            self._ui_call.connect(self._run_ui_call)
        except (RuntimeError, TypeError):
            pass
        self.cfg = cfg
        self.connected = False
        self.connecting = False
        self.progress = 0.0
        self.exit_ip = ""
        self.exit_country = ""
        self.exit_is_tor = False
        self.socks_running = False
        self.dns_running = False
        self.dns_addr = ""
        self.pending_protect = False
        self.another = False
        self._lock_sock = None
        self._tor_thread: TorThread | None = None
        self._worker: TorWorker | None = None
        self._tor_log_off = 0
        self._t0 = 0.0
        self._last_change = 0.0
        self._dns_proc = None
        self._log_paused = False
        self._vpn_proc = None
        self.vpn_on = False
        self.vpns: list = []
        self.vpn_exes: list = []
        self._upd_sums: dict = {}
        self._upd_verified: set = set()
        self.upd_src = "gh"
        self._checking = False
        self._status_worker = None
        self._status_line = ""
        self._status_t0 = 0.0
        self._rotate_last = 0.0
        self.circuit = []
        self._circuit_sig = ""
        self._circuit_t0 = 0.0
        try:
            self._lock_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._lock_sock.bind(("127.0.0.1", 51987))
            self._lock_sock.listen(1)
        except OSError:
            self._lock_sock = None
            self.another = True

        self.setWindowTitle(f"Anonymous Shield v{__version__} — Cliente Tor")
        self.resize(1220, 820)
        self.setMinimumSize(1024, 640)
        self._current_page = "dashboard"
        self._build()
        self.apply_theme()
        self._adopt_states()
        self._log("log_started", v=__version__)
        if sysprotect.is_admin():
            threading.Thread(target=self._ensure_fw, daemon=True).start()
        if self.cfg.use_tor and self.cfg.auto_connect:
            self.connect_tor()

        self._ui_timer = QTimer(self)
        self._ui_timer.timeout.connect(self._tick)
        self._ui_timer.start(500)

    # ---------- helpers ----------
    def tr(self, key: str, **kw) -> str:
        s = t(self.cfg.lang, key)
        for k, v in kw.items():
            s = s.replace("{" + k + "}", str(v))
        return s

    def _log(self, key: str, **kw) -> None:
        line = self.tr(key, **kw) if key else ""
        if line:
            self._push_log(line)

    def _push_log(self, line: str) -> None:
        self.log_lines.append(line)
        if len(self.log_lines) > 400:
            del self.log_lines[: len(self.log_lines) - 400]
        try:
            from PyQt6.QtCore import QThread as _QT
            from PyQt6.QtWidgets import QApplication as _QA
            _inst = _QA.instance()
            if _inst is not None and _QT.currentThread() != _inst.thread():
                self._ui_call.emit(self._render_logs_safe)
                return
        except Exception:
            pass
        if self._log_page_ready():
            self._render_logs()

    def _render_logs_safe(self) -> None:
        try:
            if self._log_page_ready():
                self._render_logs()
        except (RuntimeError, AttributeError):
            pass

    def _run_ui_call(self, fn) -> None:
        try:
            fn()
        except (RuntimeError, AttributeError, TypeError):
            pass

    def _on_ui(self, fn) -> None:
        """Roda fn na thread da UI (seguro p/ chamar de worker threads)."""
        try:
            self._ui_call.emit(fn)
        except (RuntimeError, AttributeError, TypeError):
            pass

    def _log_page_ready(self) -> bool:
        return hasattr(self, "log_view")

    # ---------- construção (dashboard) ----------
    def _build(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ===== Sidebar =====
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(262)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(14, 14, 14, 14)
        side.setSpacing(6)

        # marca
        brand = QFrame()
        brand.setObjectName("brand")
        bl_brand = QHBoxLayout(brand)
        bl_brand.setContentsMargins(12, 12, 12, 12)
        bl_brand.setSpacing(10)
        logo = QLabel()
        logo.setObjectName("brandLogo")
        logo.setFixedSize(40, 40)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            import os as _os
            from PyQt6.QtGui import QPixmap as _BPx
            _here = _os.path.dirname(_os.path.abspath(__file__))
            _bicon = None
            for _c in (_os.path.join(_here, "..", "assets", "icon.png"),
                       _os.path.join(_here, "assets", "icon.png"),
                       _os.path.join("assets", "icon.png")):
                if _os.path.exists(_c):
                    _bicon = _c
                    break
            if _bicon:
                logo.setPixmap(_BPx(_bicon).scaled(
                    34, 34, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
            else:
                raise OSError
        except Exception:
            logo.setText("🛡")
        bl_brand.addWidget(logo)
        bt = QVBoxLayout()
        bt.setSpacing(0)
        self.lbl_brand = QLabel("Anonymous Shield")
        self.lbl_brand.setObjectName("brandName")
        self.lbl_brand_ver = QLabel(f"v{__version__} • dashboard")
        self.lbl_brand_ver.setObjectName("brandVer")
        bt.addWidget(self.lbl_brand)
        bt.addWidget(self.lbl_brand_ver)
        bl_brand.addLayout(bt, 1)
        side.addWidget(brand)

        # navegação com seções (scroll, reordenável)
        nav_scroll = QScrollArea()
        nav_scroll.setObjectName("navscroll")
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        nav_scroll.setAutoFillBackground(False)
        nav_scroll.viewport().setAutoFillBackground(False)
        nav_host = QWidget()
        nav_host.setObjectName("navhost")
        self.nav_lay = QVBoxLayout(nav_host)
        self.nav_lay.setContentsMargins(0, 4, 0, 4)
        self.nav_lay.setSpacing(2)
        self.side_group = QButtonGroup(self)
        self.side_group.setExclusive(True)
        self.side_btns: dict[str, QPushButton] = {}
        self.nav_section_labels: dict[str, QLabel] = {}
        self._nav_edit = False
        self._rebuild_nav()
        nav_scroll.setWidget(nav_host)
        side.addWidget(nav_scroll, 1)

        navrow = QHBoxLayout()
        navrow.setSpacing(6)
        self.btn_nav_edit = _mkbtn("", "side")
        self.btn_nav_edit.setCheckable(True)
        self.btn_nav_edit.clicked.connect(self._nav_toggle_edit)
        navrow.addWidget(self.btn_nav_edit, 1)
        self.btn_nav_reset = _mkbtn("↺", "side")
        self.btn_nav_reset.setFixedWidth(44)
        self.btn_nav_reset.clicked.connect(self._nav_reset)
        navrow.addWidget(self.btn_nav_reset)
        side.addLayout(navrow)

        self.btn_theme = _mkbtn("", "side")
        self.btn_theme.clicked.connect(self._toggle_theme)
        side.addWidget(self.btn_theme)
        self.btn_quit = _mkbtn("", "danger")
        self.btn_quit.clicked.connect(self.close)
        side.addWidget(self.btn_quit)
        root.addWidget(self.sidebar)

        # ===== Coluna principal =====
        main = QWidget()
        main.setObjectName("main")
        mlay = QVBoxLayout(main)
        mlay.setContentsMargins(0, 0, 0, 0)
        mlay.setSpacing(0)

        # topbar
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(72)
        top = QHBoxLayout(topbar)
        top.setContentsMargins(16, 10, 16, 10)
        top.setSpacing(12)
        self.btn_burger = _mkbtn("☰", "burger")
        self.btn_burger.setFixedSize(42, 42)
        self.btn_burger.clicked.connect(self._toggle_sidebar)
        top.addWidget(self.btn_burger)
        title = QVBoxLayout()
        title.setSpacing(0)
        self.lbl_title = QLabel("Anonymous Shield")
        self.lbl_title.setObjectName("pagetitle")
        self.lbl_sub = QLabel()
        self.lbl_sub.setObjectName("crumb")
        title.addWidget(self.lbl_title)
        title.addWidget(self.lbl_sub)
        top.addLayout(title, 1)
        self.combo_lang = QComboBox()
        self.combo_lang.setObjectName("langTop")
        for code, label in LANGS:
            self.combo_lang.addItem(label, code)
        try:
            codes = [c for c, _ in LANGS]
            self.combo_lang.setCurrentIndex(max(0, codes.index(self.cfg.lang)))
        except ValueError:
            self.combo_lang.setCurrentIndex(0)
        self.combo_lang.setMinimumHeight(40)
        self.combo_lang.setMaxVisibleItems(20)
        self.combo_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_lang.setToolTip("Idioma / Language / Idioma")
        self.combo_lang.currentIndexChanged.connect(self._lang_changed)
        top.addWidget(self.combo_lang)
        self.lbl_status = QLabel()
        self.lbl_status.setObjectName("statusPill")
        top.addWidget(self.lbl_status)
        mlay.addWidget(topbar)

        # área de conteúdo: páginas em pilha (cada página já é scrollável)
        content = QWidget()
        content.setObjectName("main")
        clay = QVBoxLayout(content)
        clay.setContentsMargins(18, 18, 18, 18)
        clay.setSpacing(0)
        self.stack = QStackedWidget()
        clay.addWidget(self.stack, 1)
        mlay.addWidget(content, 1)

        root.addWidget(main, 1)

        self._page_idx: dict[str, int] = {}
        for pid in self.PAGES:
            build = getattr(self, f"_page_{pid}")
            w = build()
            scr = QScrollArea()
            scr.setObjectName("pagescroll")
            scr.setWidgetResizable(True)
            scr.setFrameShape(QFrame.Shape.NoFrame)
            scr.setAutoFillBackground(False)
            scr.viewport().setAutoFillBackground(False)
            scr.setWidget(w)
            self._page_idx[pid] = self.stack.addWidget(scr)

        self.log_lines: list[str] = []
        self.refresh_texts()
        self._goto("dashboard")
        self._refresh_status()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        _dark_titlebar(self)
        try:
            self.refresh_texts()
        except (RuntimeError, AttributeError):
            pass

    # ---------- navegação/textos/tema ----------
    def _toggle_sidebar(self) -> None:
        self.sidebar.setVisible(self.sidebar.isHidden())
        self.refresh_texts()

    def _nav_order(self) -> list[tuple[str, str]]:
        """[(sec, pid)] efetiva: salva + novas páginas no fim da sua seção."""
        known = {pid: sec for sec, pids in DASH_SECTIONS for pid in pids}
        saved = [s for s in (self.cfg.sidebar_order or []) if isinstance(s, str)]
        seen: set[str] = set()
        out: list[tuple[str, str]] = []
        for s in saved:
            if ":" in s:
                sec, pid = s.split(":", 1)
                if pid in known and pid not in seen:
                    seen.add(pid)
                    out.append((sec if sec.startswith("sec_") else known[pid], pid))
        for sec, pids in DASH_SECTIONS:
            for pid in pids:
                if pid not in seen:
                    seen.add(pid)
                    out.append((sec, pid))
        return out

    def _rebuild_nav(self) -> None:
        """Reconstrói os botões da sidebar na ordem salva."""
        lay = self.nav_lay
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.side_btns = {}
        self.nav_section_labels = {}
        cur_sec = None
        for sec, pid in self._nav_order():
            if sec != cur_sec:
                cur_sec = sec
                sec_lbl = QLabel(sec)
                sec_lbl.setObjectName("navsec")
                self.nav_section_labels[sec] = sec_lbl
                lay.addWidget(sec_lbl)
            b = SideItem(pid)
            b.setObjectName("side")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.set_draggable(self._nav_edit)
            b.clicked.connect(lambda _=False, p=pid: self._goto(p))
            b.moved.connect(self._nav_move)
            self.side_group.addButton(b)
            self.side_btns[pid] = b
            lay.addWidget(b)
        lay.addStretch(1)

    def _nav_toggle_edit(self) -> None:
        self._nav_edit = not self._nav_edit
        for b in self.side_btns.values():
            if isinstance(b, SideItem):
                b.set_draggable(self._nav_edit)
        self.refresh_texts()

    def _nav_move(self, src: str, target: str) -> None:
        order = [f"{s}:{p}" for s, p in self._nav_order()]
        si = next((i for i, e in enumerate(order) if e.endswith(f":{src}")), None)
        ti = next((i for i, e in enumerate(order) if e.endswith(f":{target}")), None)
        if si is None or ti is None:
            return
        # solta ANTES do alvo, herdando a seção do alvo
        tgt_sec = order[ti].split(":", 1)[0]
        item = order.pop(si)
        pid = item.split(":", 1)[1]
        ti2 = next((i for i, e in enumerate(order) if e.endswith(f":{target}")), len(order))
        order.insert(ti2, f"{tgt_sec}:{pid}")
        self.cfg.sidebar_order = order
        self.cfg.save()
        self._rebuild_nav()
        self.refresh_texts()

    def _nav_reset(self) -> None:
        self.cfg.sidebar_order = []
        self.cfg.save()
        self._rebuild_nav()
        self.refresh_texts()

    def _refresh_status(self) -> None:
        if self.connected:
            txt, col = self.tr("st_connected"), "#10b981"
        elif self.connecting:
            txt, col = self.tr("st_connecting"), "#f59e0b"
        else:
            txt, col = self.tr("st_off"), "#78788a"
        dot = "●" if self.connected else ("◐" if self.connecting else "○")
        self.lbl_status.setText(f"{dot} {txt}")
        self.lbl_status.setStyleSheet(
            f"padding: 6px 12px; border-radius: 12px; font-weight: bold; color: {col}; border: 1px solid {col};")

    # ---------- páginas ----------
    def _kpi_card(self, accent: bool = False) -> tuple[QFrame, QLabel, QLabel, QLabel]:
        from .widgets import KpiCard
        f = KpiCard()
        f.setObjectName("kpiAccent" if accent else "kpi")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(2)
        t = QLabel()
        t.setObjectName("kpiTitle")
        v = QLabel("—")
        v.setObjectName("kpiValue")
        s = QLabel("")
        s.setObjectName("kpiSub")
        s.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(v)
        lay.addWidget(s)
        return f, t, v, s

    def _page_dashboard(self) -> QWidget:
        lay = QVBoxLayout()
        lay.setSpacing(14)

        # Hero principal
        hero = QFrame()
        hero.setObjectName("heroDash")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(22, 20, 22, 20)
        hl.setSpacing(18)
        left = QVBoxLayout()
        left.setSpacing(6)
        self.lbl_dash_kicker = QLabel()
        self.lbl_dash_kicker.setObjectName("crumb")
        self.lbl_dash_kicker.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        self.lbl_dash_title = QLabel("Anonymous Shield")
        self.lbl_dash_title.setStyleSheet("color: white; font-size: 26px; font-weight: 800;")
        self.lbl_dash_sub = QLabel()
        self.lbl_dash_sub.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 13px;")
        self.lbl_dash_sub.setWordWrap(True)
        self.lbl_dash_route = QLabel()
        self.lbl_dash_route.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; font-family: monospace;")
        self.lbl_dash_route.setWordWrap(True)
        left.addWidget(self.lbl_dash_kicker)
        left.addWidget(self.lbl_dash_title)
        left.addWidget(self.lbl_dash_sub)
        left.addWidget(self.lbl_dash_route)
        left.addStretch(1)
        prow = QHBoxLayout()
        prow.setSpacing(10)
        self.dash_power = _mkbtn("", "accent")
        self.dash_power.setMinimumSize(200, 46)
        self.dash_power.clicked.connect(self._onion_clicked)
        self.dash_cancel = _mkbtn("✕", "")
        self.dash_cancel.setFixedSize(46, 46)
        self.dash_cancel.clicked.connect(self._cancel_connect)
        self.dash_cancel.setStyleSheet("background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.3); border-radius: 11px; font-weight: bold;")
        prow.addWidget(self.dash_power)
        self.dash_identity = _mkbtn("🔄", "heroGhost")
        self.dash_identity.setFixedSize(46, 46)
        self.dash_identity.clicked.connect(self._new_identity)
        prow.addWidget(self.dash_identity)
        self.dash_check = _mkbtn("⟳", "heroGhost")
        self.dash_check.setFixedSize(46, 46)
        self.dash_check.clicked.connect(self._check_status)
        prow.addWidget(self.dash_check)
        prow.addWidget(self.dash_cancel)
        prow.addStretch(1)
        left.addLayout(prow)
        hl.addLayout(left, 1)
        right = QVBoxLayout()
        right.setSpacing(6)
        self.dash_big = QLabel("OFF")
        self.dash_big.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dash_big.setStyleSheet("color: white; font-size: 40px; font-weight: 800;")
        self.dash_bar = QProgressBar()
        self.dash_bar.setRange(0, 100)
        self.dash_bar.setFixedWidth(220)
        self.dash_phase = QLabel("")
        self.dash_phase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dash_phase.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        self.dash_phase.setWordWrap(True)
        right.addWidget(self.dash_big)
        right.addWidget(self.dash_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.dash_phase)
        hl.addLayout(right)
        lay.addWidget(hero)

        # KPIs
        krow = QHBoxLayout()
        krow.setSpacing(12)
        c1, self.kpi_tor_t, self.kpi_tor_v, self.kpi_tor_s = self._kpi_card(accent=True)
        c2, self.kpi_socks_t, self.kpi_socks_v, self.kpi_socks_s = self._kpi_card()
        c3, self.kpi_prot_t, self.kpi_prot_v, self.kpi_prot_s = self._kpi_card()
        c4, self.kpi_dns_t, self.kpi_dns_v, self.kpi_dns_s = self._kpi_card()
        for c in (c1, c2, c3, c4):
            c.setMinimumHeight(108)
            krow.addWidget(c, 1)
        self.kpi_card_tor, self.kpi_card_socks = c1, c2
        self.kpi_card_prot, self.kpi_card_dns = c3, c4
        c1.clicked.connect(lambda: self._goto("home"))
        c2.clicked.connect(lambda: self._goto("proxy"))
        c3.clicked.connect(self._toggle_total)
        c4.clicked.connect(lambda: self._goto("dns"))
        lay.addLayout(krow)

        # Ações rápidas + atividade
        brow = QHBoxLayout()
        brow.setSpacing(12)
        qcard = _card()
        ql = QVBoxLayout(qcard)
        ql.setContentsMargins(16, 14, 16, 14)
        self.lbl_quick_title = QLabel()
        self.lbl_quick_title.setObjectName("title")
        ql.addWidget(self.lbl_quick_title)
        qgrid = QGridLayout()
        qgrid.setSpacing(10)
        self.dash_quicks: list[QPushButton] = []
        for i, pid in enumerate(("home", "bridges", "proxy", "dns", "scan", "logs")):
            b = _mkbtn("", "quick")
            b.setMinimumHeight(52)
            b.clicked.connect(lambda _=False, p=pid: self._goto(p))
            self.dash_quicks.append(b)
            setattr(self, f"dash_quick_{pid}", b)
            qgrid.addWidget(b, i // 2, i % 2)
        ql.addLayout(qgrid)
        brow.addWidget(qcard, 1)

        acard = _card()
        al = QVBoxLayout(acard)
        al.setContentsMargins(16, 14, 16, 14)
        self.lbl_act_title = QLabel()
        self.lbl_act_title.setObjectName("title")
        al.addWidget(self.lbl_act_title)
        self.dash_exit = QLabel()
        self.dash_exit.setStyleSheet("font-size: 20px; font-weight: 800; font-family: monospace;")
        self.dash_exit.setWordWrap(True)
        al.addWidget(self.dash_exit)
        self.dash_logs = QLabel()
        self.dash_logs.setObjectName("muted")
        self.dash_logs.setWordWrap(True)
        self.dash_logs.setAlignment(Qt.AlignmentFlag.AlignTop)
        al.addWidget(self.dash_logs, 1)
        self.dash_view_logs = _mkbtn("", "")
        self.dash_view_logs.clicked.connect(lambda: self._goto("logs"))
        al.addWidget(self.dash_view_logs)
        brow.addWidget(acard, 1)
        lay.addLayout(brow)

        # Tráfego ao vivo
        bwcard = _card()
        bwl = QVBoxLayout(bwcard)
        bwl.setContentsMargins(16, 14, 16, 14)
        bwl.setSpacing(8)
        self.lbl_bw_title = QLabel()
        self.lbl_bw_title.setObjectName("title")
        bwl.addWidget(self.lbl_bw_title)
        self.spark = SparkWidget()
        bwl.addWidget(self.spark)
        lay.addWidget(bwcard)

        # Circuito Tor (relays)
        ccard = _card()
        cl2 = QVBoxLayout(ccard)
        cl2.setContentsMargins(16, 14, 16, 14)
        cl2.setSpacing(8)
        chead = QHBoxLayout()
        chead.setSpacing(10)
        self.lbl_circuit_title = QLabel()
        self.lbl_circuit_title.setObjectName("title")
        chead.addWidget(self.lbl_circuit_title, 1)
        self.btn_circuit_new = _mkbtn("", "")
        self.btn_circuit_new.setMinimumHeight(40)
        self.btn_circuit_new.clicked.connect(self._new_identity)
        chead.addWidget(self.btn_circuit_new)
        cl2.addLayout(chead)
        self.circuit_rows = QVBoxLayout()
        self.circuit_rows.setSpacing(4)
        cl2.addLayout(self.circuit_rows)
        dnsrow = QHBoxLayout()
        dnsrow.setSpacing(10)
        self.lbl_dns_now_t = QLabel()
        self.lbl_dns_now_t.setObjectName("sec")
        self.lbl_dns_now = QLabel()
        self.lbl_dns_now.setObjectName("muted")
        self.lbl_dns_now.setStyleSheet("font-family: monospace;")
        self.lbl_dns_now.setWordWrap(True)
        dnsrow.addWidget(self.lbl_dns_now_t)
        dnsrow.addWidget(self.lbl_dns_now, 1)
        cl2.addLayout(dnsrow)
        lay.addWidget(ccard)

        return self._wrap(lay)

    def _wrap(self, layout) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(8)
        lay.addLayout(layout)
        lay.addStretch(1)
        return w

    def _page_home(self) -> QWidget:
        lay = QVBoxLayout()
        card = _card()
        card.setObjectName("hero")
        cl = QVBoxLayout(card)
        self.lbl_hero_sub = QLabel()
        self.lbl_hero_sub.setObjectName("sec")
        self.lbl_hero_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hero_route = QLabel()
        self.lbl_hero_route.setObjectName("muted")
        self.lbl_hero_route.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.lbl_hero_sub)
        cl.addWidget(self.lbl_hero_route)
        self.lbl_banner = QLabel()
        self.lbl_banner.setWordWrap(True)
        self.lbl_banner.setStyleSheet("color:#b45309; background:#fef3c7; border-radius:8px; padding:6px;")
        self.lbl_banner.setVisible(False)
        cl.addWidget(self.lbl_banner)
        self.btn_onion = OnionWidget()
        self.btn_onion.setToolTip(self.tr("onion_tip"))
        self.btn_onion.clicked.connect(self._onion_clicked)
        hc = QHBoxLayout()
        hc.addStretch(1)
        hc.addWidget(self.btn_onion)
        hc.addStretch(1)
        cl.addLayout(hc)
        # Palavra de status gigante (estilo Orbot)
        self.lbl_bigstatus = QLabel()
        self.lbl_bigstatus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_bigstatus.setStyleSheet("font-size: 30px; font-weight: bold;")
        cl.addWidget(self.lbl_bigstatus)
        # Botão liga/desliga explícito
        pc = QHBoxLayout()
        pc.addStretch(1)
        self.btn_power = _mkbtn("", "accent")
        self.btn_power.setMinimumSize(240, 44)
        self.btn_power.clicked.connect(self._onion_clicked)
        pc.addWidget(self.btn_power)
        pc.addStretch(1)
        cl.addLayout(pc)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        cl.addWidget(self.bar)
        self.lbl_phase = QLabel()
        self.lbl_phase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.lbl_phase)
        # Cancelar conexão
        crow = QHBoxLayout()
        crow.addStretch(1)
        self.btn_cancel = _mkbtn("")
        self.btn_cancel.setFixedWidth(200)
        self.btn_cancel.clicked.connect(self._cancel_connect)
        crow.addWidget(self.btn_cancel)
        crow.addStretch(1)
        cl.addLayout(crow)
        self.lbl_detail = QLabel()
        self.lbl_detail.setObjectName("muted")
        self.lbl_detail.setWordWrap(True)
        self.lbl_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self.lbl_detail)
        self.box_block = _inner()
        bl = QVBoxLayout(self.box_block)
        self.lbl_block = QLabel()
        self.lbl_block.setWordWrap(True)
        bl.addWidget(self.lbl_block)
        brow = QHBoxLayout()
        self.btn_gobridges = _mkbtn("", "accent")
        self.btn_gobridges.clicked.connect(lambda: self._goto("bridges"))
        self.btn_retry = _mkbtn("")
        self.btn_retry.clicked.connect(lambda: self.connect_tor())
        brow.addWidget(self.btn_gobridges)
        brow.addWidget(self.btn_retry)
        bl.addLayout(brow)
        self.box_block.setVisible(False)
        cl.addWidget(self.box_block)
        self.card_exit = _inner()
        el = QHBoxLayout(self.card_exit)
        ev = QVBoxLayout()
        self.lbl_exit_title = QLabel()
        self.lbl_exit_ip = QLabel()
        self.lbl_exit_ip.setStyleSheet("font-size: 24px; font-weight: bold; font-family: monospace;")
        self.lbl_exit_country = QLabel()
        self.lbl_exit_country.setObjectName("sec")
        ev.addWidget(self.lbl_exit_title)
        ev.addWidget(self.lbl_exit_ip)
        ev.addWidget(self.lbl_exit_country)
        el.addLayout(ev)
        el.addStretch(1)
        ev2 = QVBoxLayout()
        self.lbl_exit_badge = QLabel("✓")
        self.lbl_exit_badge.setStyleSheet("font-size: 22px; font-weight: bold; color: #10b981;")
        self.btn_exit_copy = _mkbtn("⎙")
        self.btn_exit_copy.setFixedSize(40, 40)
        self.btn_exit_copy.clicked.connect(self._copy_ip)
        ev2.addWidget(self.lbl_exit_badge, alignment=Qt.AlignmentFlag.AlignCenter)
        ev2.addWidget(self.btn_exit_copy)
        el.addLayout(ev2)
        self.card_exit.setVisible(False)
        cl.addWidget(self.card_exit)
        # Evitar 5/9/14 Olhos (saída fora desses países)
        avoid = _inner()
        av = QVBoxLayout(avoid)
        self.lbl_exit_avoid = QLabel()
        self.lbl_exit_avoid.setObjectName("sec")
        av.addWidget(self.lbl_exit_avoid)
        ar = QHBoxLayout()
        ar.setSpacing(8)
        self.exit_group = QButtonGroup(self)
        self.exit_btns: dict[str, QPushButton] = {}
        for mode in ("all", "five", "nine", "fourteen"):
            b = _mkbtn(mode)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, m=mode: self._exit_mode(m))
            self.exit_group.addButton(b)
            self.exit_btns[mode] = b
            ar.addWidget(b)
        av.addLayout(ar)
        self.lbl_exit_note = QLabel()
        self.lbl_exit_note.setObjectName("muted")
        self.lbl_exit_note.setWordWrap(True)
        av.addWidget(self.lbl_exit_note)
        cl.addWidget(avoid)
        lay.addWidget(card)

        # Modos prontos
        modes = _card()
        ml = QVBoxLayout(modes)
        ml.setContentsMargins(16, 14, 16, 14)
        ml.setSpacing(10)
        self.lbl_mode_title = QLabel()
        self.lbl_mode_title.setObjectName("title")
        ml.addWidget(self.lbl_mode_title)
        segbox = QWidget()
        segbox.setObjectName("segbox")
        mrow = QHBoxLayout(segbox)
        mrow.setContentsMargins(4, 4, 4, 4)
        mrow.setSpacing(4)
        self.mode_btns: dict[str, QPushButton] = {}
        for mode in ("rapido", "anonimo", "censura"):
            b = _mkbtn(mode, "seg")
            b.clicked.connect(lambda _=False, m=mode: self._apply_preset(m))
            self.mode_btns[mode] = b
            mrow.addWidget(b)
        ml.addWidget(segbox)
        self.lbl_mode_cur = QLabel()
        self.lbl_mode_cur.setObjectName("muted")
        ml.addWidget(self.lbl_mode_cur)
        self.lbl_mode_desc = QLabel()
        self.lbl_mode_desc.setObjectName("muted")
        self.lbl_mode_desc.setWordWrap(True)
        ml.addWidget(self.lbl_mode_desc)
        lay.addWidget(modes)

        # Rotação automática de IP
        rot = _card()
        rl2 = QVBoxLayout(rot)
        rl2.setContentsMargins(16, 14, 16, 14)
        rl2.setSpacing(10)
        rhead = QHBoxLayout()
        rhead.setSpacing(10)
        rico = QLabel("🔄")
        rico.setObjectName("featIcon")
        rico.setFixedSize(40, 40)
        rico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rhead.addWidget(rico)
        self.lbl_rotate_title = QLabel()
        self.lbl_rotate_title.setObjectName("title")
        rhead.addWidget(self.lbl_rotate_title, 1)
        self.chk_rotate = ToggleSwitch()
        self.chk_rotate.toggled.connect(self._rotate_toggled)
        rhead.addWidget(self.chk_rotate, alignment=Qt.AlignmentFlag.AlignCenter)
        rl2.addLayout(rhead)
        rrow = QHBoxLayout()
        rrow.setSpacing(10)
        self.lbl_rotate_every = QLabel()
        self.lbl_rotate_every.setObjectName("sec")
        from PyQt6.QtWidgets import QSpinBox as _SB2
        self.spin_rotate = _SB2()
        self.spin_rotate.setRange(1, 1440)
        self.spin_rotate.setMinimumHeight(38)
        self.spin_rotate.valueChanged.connect(lambda *_: self._rotate_changed())
        self.combo_rotate_unit = QComboBox()
        self.combo_rotate_unit.setMinimumHeight(38)
        self.combo_rotate_unit.currentIndexChanged.connect(lambda *_: self._rotate_changed())
        rrow.addWidget(self.lbl_rotate_every)
        rrow.addWidget(self.spin_rotate)
        rrow.addWidget(self.combo_rotate_unit, 1)
        rl2.addLayout(rrow)
        self.lbl_rotate_count = QLabel()
        self.lbl_rotate_count.setObjectName("muted")
        rl2.addWidget(self.lbl_rotate_count)
        lay.addWidget(rot)

        # Agendador
        sch = _card()
        shl = QVBoxLayout(sch)
        shl.setContentsMargins(16, 14, 16, 14)
        shl.setSpacing(10)
        shead = QHBoxLayout()
        shead.setSpacing(10)
        sico = QLabel("⏰")
        sico.setObjectName("featIcon")
        sico.setFixedSize(40, 40)
        sico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shead.addWidget(sico)
        self.lbl_sched_title = QLabel()
        self.lbl_sched_title.setObjectName("title")
        shead.addWidget(self.lbl_sched_title, 1)
        self.chk_sched = ToggleSwitch()
        self.chk_sched.toggled.connect(self._sched_toggled)
        shead.addWidget(self.chk_sched, alignment=Qt.AlignmentFlag.AlignCenter)
        shl.addLayout(shead)
        srow1 = QHBoxLayout()
        srow1.setSpacing(10)
        self.lbl_sched_on = QLabel()
        self.lbl_sched_on.setObjectName("sec")
        self.edit_sched_on = QLineEdit()
        self.edit_sched_on.setMinimumHeight(40)
        self.edit_sched_on.setPlaceholderText("08:00")
        self.edit_sched_on.editingFinished.connect(lambda *_: self._sched_changed())
        self.lbl_sched_off = QLabel()
        self.lbl_sched_off.setObjectName("sec")
        self.edit_sched_off = QLineEdit()
        self.edit_sched_off.setMinimumHeight(40)
        self.edit_sched_off.setPlaceholderText("23:00")
        self.edit_sched_off.editingFinished.connect(lambda *_: self._sched_changed())
        srow1.addWidget(self.lbl_sched_on)
        srow1.addWidget(self.edit_sched_on, 1)
        srow1.addWidget(self.lbl_sched_off)
        srow1.addWidget(self.edit_sched_off, 1)
        shl.addLayout(srow1)
        srow2 = QHBoxLayout()
        srow2.setSpacing(10)
        self.lbl_sched_rot = QLabel()
        self.lbl_sched_rot.setObjectName("sec")
        self.edit_sched_rot = QLineEdit()
        self.edit_sched_rot.setMinimumHeight(40)
        self.edit_sched_rot.setPlaceholderText("09:00, 13:00, 18:00")
        self.edit_sched_rot.editingFinished.connect(lambda *_: self._sched_changed())
        srow2.addWidget(self.lbl_sched_rot)
        srow2.addWidget(self.edit_sched_rot, 1)
        shl.addLayout(srow2)
        self.lbl_sched_next = QLabel()
        self.lbl_sched_next.setObjectName("muted")
        shl.addWidget(self.lbl_sched_next)
        lay.addWidget(sch)

        # Linhas de ação (estilo Orbot)
        rows = _card()
        rl = QVBoxLayout(rows)
        rl.setSpacing(0)
        rl.setContentsMargins(6, 2, 6, 2)
        self.row_identity = _mkbtn("")
        self.row_identity.setObjectName("row")
        self.row_identity.clicked.connect(self._new_identity)
        self.row_check = _mkbtn("")
        self.row_check.setObjectName("row")
        self.row_check.clicked.connect(self._check_exit)
        self.row_total = _mkbtn("")
        self.row_total.setObjectName("row")
        self.row_total.clicked.connect(lambda: self._goto("total"))
        self.row_copyip = _mkbtn("")
        self.row_copyip.setObjectName("row")
        self.row_copyip.clicked.connect(self._copy_ip)
        self.row_browser = _mkbtn("")
        self.row_browser.setObjectName("row")
        self.row_browser.clicked.connect(self._browser_open)
        for b in (self.row_identity, self.row_check, self.row_total, self.row_copyip,
                  self.row_browser):
            rl.addWidget(b)
        lay.addWidget(rows)
        return self._wrap(lay)

    def _page_bridges(self) -> QWidget:
        lay = QVBoxLayout()
        card = _card()
        cl = QVBoxLayout(card)
        self.lbl_br_title = QLabel()
        self.lbl_br_title.setObjectName("title")
        cl.addWidget(self.lbl_br_title)
        self.lbl_br_tags = QLabel()
        self.lbl_br_tags.setObjectName("muted")
        cl.addWidget(self.lbl_br_tags)
        inner = _inner()
        il = QVBoxLayout(inner)
        self.lbl_br_enable = QLabel()
        erow = QHBoxLayout()
        erow.addWidget(self.lbl_br_enable)
        erow.addStretch(1)
        self.chk_bridges = QCheckBox()
        self.chk_bridges.toggled.connect(self._bridges_toggled)
        erow.addWidget(self.chk_bridges)
        il.addLayout(erow)
        self.lbl_br_desc = QLabel()
        self.lbl_br_desc.setObjectName("muted")
        self.lbl_br_desc.setWordWrap(True)
        il.addWidget(self.lbl_br_desc)
        cl.addWidget(inner)
        self.lbl_transport = QLabel()
        self.lbl_transport.setObjectName("sec")
        cl.addWidget(self.lbl_transport)
        prow = QHBoxLayout()
        self.preset_group = QButtonGroup(self)
        self.preset_btns: dict[str, QPushButton] = {}
        for p in ("direto", "auto", "obfs4", "conjure", "snowflake", "webtunnel", "custom"):
            b = _mkbtn(p)
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, q=p: self._preset(q))
            self.preset_group.addButton(b)
            self.preset_btns[p] = b
            prow.addWidget(b)
        cl.addLayout(prow)
        self.lbl_direct_info = QLabel()
        self.lbl_direct_info.setWordWrap(True)
        self.lbl_direct_info.setObjectName("sec")
        cl.addWidget(self.lbl_direct_info)
        self.lbl_pt = QLabel()
        self.lbl_pt.setObjectName("sec")
        cl.addWidget(self.lbl_pt)
        self.edit_pt = QLineEdit()
        self.edit_pt.editingFinished.connect(lambda: self._save_cfg())
        cl.addWidget(self.edit_pt)
        self.lbl_br_lines = QLabel()
        self.lbl_br_lines.setObjectName("sec")
        cl.addWidget(self.lbl_br_lines)
        from PyQt6.QtWidgets import QTextEdit
        self.edit_bridges = QTextEdit()
        self.edit_bridges.setMinimumHeight(110)
        self.edit_bridges.setFontFamily("monospace")
        cl.addWidget(self.edit_bridges)
        brow = QHBoxLayout()
        self.btn_paste = _mkbtn("")
        self.btn_paste.clicked.connect(self._paste_bridges)
        self.btn_apply_br = _mkbtn("", "accent")
        self.btn_apply_br.clicked.connect(self._apply_bridges)
        self.btn_clear_br = _mkbtn("")
        self.btn_clear_br.clicked.connect(lambda: self.edit_bridges.clear())
        self.lbl_br_count = QLabel()
        self.lbl_br_count.setObjectName("muted")
        brow.addWidget(self.btn_paste)
        brow.addWidget(self.btn_apply_br)
        brow.addWidget(self.btn_clear_br)
        brow.addWidget(self.lbl_br_count)
        cl.addLayout(brow)
        self.lbl_br_tip = QLabel()
        self.lbl_br_tip.setObjectName("sec")
        self.lbl_br_tip.setWordWrap(True)
        cl.addWidget(self.lbl_br_tip)
        self.btn_br_open = _mkbtn("")
        self.btn_br_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://bridges.torproject.org/")))
        cl.addWidget(self.btn_br_open)
        self.lbl_br_captcha = QLabel()
        self.lbl_br_captcha.setObjectName("muted")
        self.lbl_br_captcha.setWordWrap(True)
        cl.addWidget(self.lbl_br_captcha)
        self.lbl_br_web = QLabel()
        self.lbl_br_web.setWordWrap(True)
        self.lbl_br_web.setObjectName("muted")
        cl.addWidget(self.lbl_br_web)
        self.lbl_br_web = QLabel()
        self.lbl_br_web.setWordWrap(True)
        self.lbl_br_web.setObjectName("muted")
        cl.addWidget(self.lbl_br_web)
        lay.addWidget(card)
        return self._wrap(lay)

    def _feat_row(self, icon: str, title_lbl: QLabel, desc_lbl: QLabel,
                    switch: QWidget) -> QWidget:
        """Linha de recurso: selo + título/descrição + interruptor."""
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(10, 10, 10, 10)
        rl.setSpacing(12)
        ic = QLabel(icon)
        ic.setObjectName("featIcon")
        ic.setFixedSize(40, 40)
        ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(ic)
        tx = QVBoxLayout()
        tx.setSpacing(2)
        title_lbl.setStyleSheet("font-weight: 700;")
        tx.addWidget(title_lbl)
        desc_lbl.setObjectName("muted")
        desc_lbl.setWordWrap(True)
        tx.addWidget(desc_lbl)
        rl.addLayout(tx, 1)
        rl.addWidget(switch, alignment=Qt.AlignmentFlag.AlignCenter)
        return row

    def _page_proxy(self) -> QWidget:
        lay = QVBoxLayout()
        lay.setSpacing(14)

        # ---- hero: estado + endereço ----
        hero = QFrame()
        hero.setObjectName("heroDash")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(20, 18, 20, 18)
        hl.setSpacing(14)
        pic = QLabel("⇄")
        pic.setObjectName("heroIcon")
        pic.setFixedSize(52, 52)
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(pic)
        hleft = QVBoxLayout()
        hleft.setSpacing(6)
        self.lbl_local_title = QLabel()
        self.lbl_local_title.setObjectName("title")
        self.lbl_proxy_state = QLabel()
        self.lbl_proxy_state.setObjectName("heroPill")
        hleft.addWidget(self.lbl_local_title)
        hleft.addWidget(self.lbl_proxy_state, alignment=Qt.AlignmentFlag.AlignLeft)
        hl.addLayout(hleft, 1)
        hright = QVBoxLayout()
        hright.setSpacing(6)
        chip = QFrame()
        chip.setObjectName("addrChip")
        chipl = QHBoxLayout(chip)
        chipl.setContentsMargins(12, 6, 6, 6)
        chipl.setSpacing(8)
        self.lbl_socks_addr = QLabel("127.0.0.1:9150")
        self.lbl_socks_addr.setObjectName("addrText")
        chipl.addWidget(self.lbl_socks_addr)
        btn_copy = _mkbtn("⎙", "heroGhost")
        btn_copy.setFixedSize(36, 36)
        btn_copy.setToolTip("⎙")
        btn_copy.clicked.connect(lambda: (
            QApplication.clipboard().setText(f"127.0.0.1:{self.cfg.socks_port}"),
            self._push_log(self.tr("log_proxy_copied"))))
        chipl.addWidget(btn_copy)
        hright.addWidget(chip)
        self.lbl_proxy_hint = QLabel()
        self.lbl_proxy_hint.setObjectName("heroHint")
        self.lbl_proxy_hint.setWordWrap(True)
        hright.addWidget(self.lbl_proxy_hint)
        hl.addLayout(hright)
        lay.addWidget(hero)

        # ---- recursos (interruptores) ----
        feat = _card()
        fl = QVBoxLayout(feat)
        fl.setContentsMargins(8, 8, 8, 8)
        fl.setSpacing(2)
        self.lbl_local_enable = QLabel()
        self.lbl_local_desc = QLabel()
        self.chk_socks = ToggleSwitch()
        self.chk_socks.toggled.connect(lambda v: (setattr(self.cfg, "socks_enabled", bool(v)), self.cfg.save()))
        fl.addWidget(self._feat_row("⇄", self.lbl_local_enable, self.lbl_local_desc, self.chk_socks))
        self.lbl_kill = QLabel()
        self.lbl_kill_desc = QLabel()
        self.chk_kill = ToggleSwitch()
        self.chk_kill.toggled.connect(self._kill_toggled)
        fl.addWidget(self._feat_row("⛔", self.lbl_kill, self.lbl_kill_desc, self.chk_kill))
        self.lbl_autocon = QLabel()
        self.lbl_autocon_desc = QLabel("")
        self.chk_autocon = ToggleSwitch()
        self.chk_autocon.toggled.connect(self._autocon_toggled)
        fl.addWidget(self._feat_row("🔌", self.lbl_autocon, self.lbl_autocon_desc, self.chk_autocon))
        lay.addWidget(feat)

        # ---- porta + ações ----
        act = _card()
        al = QVBoxLayout(act)
        al.setContentsMargins(16, 14, 16, 14)
        al.setSpacing(10)
        prow = QHBoxLayout()
        prow.setSpacing(10)
        self.lbl_port = QLabel()
        self.lbl_port.setObjectName("sec")
        from PyQt6.QtWidgets import QSpinBox
        self.spin_port = QSpinBox()
        self.spin_port.setRange(1024, 65535)
        self.spin_port.setMinimumHeight(38)
        self.spin_port.valueChanged.connect(lambda v: (setattr(self.cfg, "socks_port", int(v)), self.cfg.save(), self._push_log(self.tr("log_port", p=v))))
        prow.addWidget(self.lbl_port)
        prow.addWidget(self.spin_port)
        prow.addStretch(1)
        al.addLayout(prow)
        srow = QHBoxLayout()
        srow.setSpacing(10)
        self.btn_socks_start = _mkbtn("", "success")
        self.btn_socks_start.setMinimumHeight(44)
        self.btn_socks_start.clicked.connect(lambda: self._tor_op("start_socks"))
        self.btn_socks_stop = _mkbtn("")
        self.btn_socks_stop.setMinimumHeight(44)
        self.btn_socks_stop.clicked.connect(lambda: self._tor_op("stop_socks"))
        srow.addWidget(self.btn_socks_start)
        srow.addWidget(self.btn_socks_stop)
        al.addLayout(srow)
        lay.addWidget(act)

        # ---- upstream ----
        up = _card()
        ul = QVBoxLayout(up)
        ul.setContentsMargins(16, 14, 16, 14)
        ul.setSpacing(10)
        uhead = QHBoxLayout()
        uhead.setSpacing(10)
        uico = QLabel("🌐")
        uico.setObjectName("featIcon")
        uico.setFixedSize(40, 40)
        uico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        uhead.addWidget(uico)
        self.lbl_up_title = QLabel()
        self.lbl_up_title.setObjectName("title")
        uhead.addWidget(self.lbl_up_title, 1)
        self.chk_upstream = ToggleSwitch()
        self.chk_upstream.toggled.connect(self._upstream_toggled)
        uhead.addWidget(self.chk_upstream, alignment=Qt.AlignmentFlag.AlignCenter)
        ul.addLayout(uhead)
        self.lbl_up_enable = QLabel()
        self.lbl_up_enable.setObjectName("sec")
        ul.addWidget(self.lbl_up_enable)
        self.lbl_up_desc = QLabel()
        self.lbl_up_desc.setObjectName("muted")
        self.lbl_up_desc.setWordWrap(True)
        ul.addWidget(self.lbl_up_desc)
        self.lbl_quick = QLabel()
        self.lbl_quick.setObjectName("sec")
        ul.addWidget(self.lbl_quick)
        segbox = QWidget()
        segbox.setObjectName("segbox")
        qrow = QHBoxLayout(segbox)
        qrow.setContentsMargins(4, 4, 4, 4)
        qrow.setSpacing(4)
        self.up_btns: dict[str, QPushButton] = {}
        for key, url in (("direct", ""), ("SOCKS5", "socks5://127.0.0.1:1080"), ("HTTP", "http://127.0.0.1:8080")):
            b = _mkbtn(key, "seg")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key, u=url: self._upstream_quick(k, u))
            self.up_btns[key] = b
            qrow.addWidget(b)
        ul.addWidget(segbox)
        self.lbl_up_url = QLabel()
        self.lbl_up_url.setObjectName("sec")
        ul.addWidget(self.lbl_up_url)
        self.edit_upstream = QLineEdit()
        self.edit_upstream.editingFinished.connect(lambda: (setattr(self.cfg, "upstream_proxy_url", self.edit_upstream.text().strip()), self.cfg.save()))
        ul.addWidget(self.edit_upstream)
        self.lbl_up_formats = QLabel()
        self.lbl_up_formats.setObjectName("sec")
        self.lbl_up_formats.setWordWrap(True)
        ul.addWidget(self.lbl_up_formats)
        arow2 = QHBoxLayout()
        arow2.setSpacing(10)
        self.btn_up_apply = _mkbtn("", "accent")
        self.btn_up_apply.setMinimumHeight(44)
        self.btn_up_apply.clicked.connect(self._upstream_apply)
        self.btn_up_test = _mkbtn("")
        self.btn_up_test.setMinimumHeight(44)
        self.btn_up_test.clicked.connect(self._upstream_testfmt)
        arow2.addWidget(self.btn_up_apply)
        arow2.addWidget(self.btn_up_test)
        ul.addLayout(arow2)
        lay.addWidget(up)
        return self._wrap(lay)

    def _page_dns(self) -> QWidget:
        lay = QVBoxLayout()
        lay.setSpacing(14)

        # ---- hero: estado + escuta ----
        hero = QFrame()
        hero.setObjectName("heroDash")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(20, 18, 20, 18)
        hl.setSpacing(14)
        pic = QLabel("🛡")
        pic.setObjectName("heroIcon")
        pic.setFixedSize(52, 52)
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(pic)
        hleft = QVBoxLayout()
        hleft.setSpacing(6)
        self.lbl_dns_title = QLabel()
        self.lbl_dns_title.setObjectName("title")
        self.lbl_dns_state = QLabel()
        self.lbl_dns_state.setObjectName("heroPill")
        hleft.addWidget(self.lbl_dns_title)
        hleft.addWidget(self.lbl_dns_state, alignment=Qt.AlignmentFlag.AlignLeft)
        hl.addLayout(hleft, 1)
        self.dns_chip = QFrame()
        self.dns_chip.setObjectName("addrChip")
        chipl = QHBoxLayout(self.dns_chip)
        chipl.setContentsMargins(12, 8, 12, 8)
        self.lbl_dns_listen = QLabel()
        self.lbl_dns_listen.setObjectName("addrText")
        chipl.addWidget(self.lbl_dns_listen)
        hl.addWidget(self.dns_chip, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hero)

        # ---- ativar ----
        feat = _card()
        fl = QVBoxLayout(feat)
        fl.setContentsMargins(8, 8, 8, 8)
        self.lbl_dns_enable = QLabel()
        self.lbl_dns_desc = QLabel()
        self.chk_dns = ToggleSwitch()
        self.chk_dns.toggled.connect(self._dns_toggled)
        fl.addWidget(self._feat_row("🛡", self.lbl_dns_enable, self.lbl_dns_desc, self.chk_dns))
        lay.addWidget(feat)

        # ---- modo segmentado ----
        modecard = _card()
        ml = QVBoxLayout(modecard)
        ml.setContentsMargins(16, 14, 16, 14)
        ml.setSpacing(10)
        self.lbl_mode = QLabel()
        self.lbl_mode.setObjectName("sec")
        ml.addWidget(self.lbl_mode)
        segbox = QWidget()
        segbox.setObjectName("segbox")
        mrow = QHBoxLayout(segbox)
        mrow.setContentsMargins(4, 4, 4, 4)
        mrow.setSpacing(4)
        self.btn_dns_tor = _mkbtn("tor", "seg")
        self.btn_dns_tor.setCheckable(True)
        self.btn_dns_tor.clicked.connect(lambda: self._dns_mode("tor"))
        self.btn_dns_local = _mkbtn("local", "seg")
        self.btn_dns_local.setCheckable(True)
        self.btn_dns_local.clicked.connect(lambda: self._dns_mode("local"))
        self.btn_dns_combo = _mkbtn("combo", "seg")
        self.btn_dns_combo.setCheckable(True)
        self.btn_dns_combo.clicked.connect(lambda: self._dns_mode("combined"))
        mrow.addWidget(self.btn_dns_tor)
        mrow.addWidget(self.btn_dns_local)
        mrow.addWidget(self.btn_dns_combo)
        ml.addWidget(segbox)
        self.lbl_dns_info = QLabel()
        self.lbl_dns_info.setObjectName("muted")
        self.lbl_dns_info.setWordWrap(True)
        ml.addWidget(self.lbl_dns_info)
        lay.addWidget(modecard)

        # ---- stub local ----
        self.dns_local_box = QWidget()
        dl = QVBoxLayout(self.dns_local_box)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(14)
        bincard = _card()
        bl = QVBoxLayout(bincard)
        bl.setContentsMargins(16, 14, 16, 14)
        bl.setSpacing(10)
        self.lbl_dns_bin = QLabel()
        self.lbl_dns_bin.setObjectName("sec")
        bl.addWidget(self.lbl_dns_bin)
        brow = QHBoxLayout()
        brow.setSpacing(10)
        self.edit_dns_bin = QLineEdit()
        self.edit_dns_bin.setMinimumHeight(42)
        self.edit_dns_bin.editingFinished.connect(lambda: (setattr(self.cfg, "dnscrypt_bin", self.edit_dns_bin.text().strip()), self.cfg.save()))
        self.btn_dns_browse = _mkbtn("…", "")
        self.btn_dns_browse.setFixedSize(52, 42)
        self.btn_dns_browse.clicked.connect(self._dns_browse)
        brow.addWidget(self.edit_dns_bin, 1)
        brow.addWidget(self.btn_dns_browse)
        bl.addLayout(brow)
        self.btn_dns_get = _mkbtn("")
        self.btn_dns_get.setMinimumHeight(42)
        self.btn_dns_get.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/DNSCrypt/dnscrypt-proxy/releases")))
        bl.addWidget(self.btn_dns_get)
        self.lbl_dns_port = QLabel()
        self.lbl_dns_port.setObjectName("sec")
        bl.addWidget(self.lbl_dns_port)
        from PyQt6.QtWidgets import QSpinBox as _SB
        self.spin_dns_port = _SB()
        self.spin_dns_port.setRange(1025, 65535)
        self.spin_dns_port.setMinimumHeight(38)
        self.spin_dns_port.valueChanged.connect(lambda v: (setattr(self.cfg, "dnscrypt_port", int(v)), self.cfg.save()))
        bl.addWidget(self.spin_dns_port)
        self.lbl_dns_toml = QLabel()
        self.lbl_dns_toml.setObjectName("sec")
        bl.addWidget(self.lbl_dns_toml)
        self.edit_dns_toml = QLineEdit()
        self.edit_dns_toml.setMinimumHeight(42)
        self.edit_dns_toml.editingFinished.connect(lambda: (setattr(self.cfg, "dnscrypt_config", self.edit_dns_toml.text().strip()), self.cfg.save()))
        bl.addWidget(self.edit_dns_toml)
        srow = QHBoxLayout()
        srow.setSpacing(10)
        self.btn_dns_start = _mkbtn("", "success")
        self.btn_dns_start.setMinimumHeight(44)
        self.btn_dns_start.clicked.connect(lambda: self._tor_op("dns_start"))
        self.btn_dns_stop = _mkbtn("")
        self.btn_dns_stop.setMinimumHeight(44)
        self.btn_dns_stop.clicked.connect(lambda: self._tor_op("dns_stop"))
        srow.addWidget(self.btn_dns_start)
        srow.addWidget(self.btn_dns_stop)
        bl.addLayout(srow)
        dl.addWidget(bincard)
        tcard = _inner()
        tl = QVBoxLayout(tcard)
        self.lbl_dns_test = QLabel()
        self.lbl_dns_test.setObjectName("sec")
        tl.addWidget(self.lbl_dns_test)
        trow = QHBoxLayout()
        trow.setSpacing(10)
        self.edit_dns_host = QLineEdit()
        self.edit_dns_host.setMinimumHeight(42)
        self.edit_dns_host.editingFinished.connect(lambda: (setattr(self.cfg, "dnscrypt_host", self.edit_dns_host.text().strip() or "example.com"), self.cfg.save()))
        self.btn_dns_test = _mkbtn("", "accent")
        self.btn_dns_test.setMinimumHeight(42)
        self.btn_dns_test.clicked.connect(self._dns_test)
        trow.addWidget(self.edit_dns_host, 1)
        trow.addWidget(self.btn_dns_test)
        tl.addLayout(trow)
        self.lbl_dns_result = QLabel()
        self.lbl_dns_result.setObjectName("mono")
        self.lbl_dns_result.setWordWrap(True)
        tl.addWidget(self.lbl_dns_result)
        dl.addWidget(tcard)
        lay.addWidget(self.dns_local_box)
        return self._wrap(lay)

    def _page_total(self) -> QWidget:
        lay = QVBoxLayout()
        card = _card()
        cl = QVBoxLayout(card)
        self.lbl_total_title = QLabel()
        self.lbl_total_title.setObjectName("title")
        cl.addWidget(self.lbl_total_title)
        lrow = QHBoxLayout()
        self.lay_labels: dict[str, QLabel] = {}
        for key in ("lay_tor", "lay_socks", "lay_sys", "lay_fw"):
            inner = _inner()
            il = QVBoxLayout(inner)
            t = QLabel()
            t.setObjectName("muted")
            v = QLabel()
            v.setStyleSheet("font-weight: bold;")
            il.addWidget(t)
            il.addWidget(v)
            lrow.addWidget(inner)
            self.lay_labels[key] = v
            setattr(self, f"_lay_t_{key}", t)
        cl.addLayout(lrow)
        inner = _inner()
        il = QVBoxLayout(inner)
        self.lbl_total_enable = QLabel()
        mrow = QHBoxLayout()
        mrow.addWidget(self.lbl_total_enable)
        mrow.addStretch(1)
        self.chk_total = ToggleSwitch()
        self.chk_total.toggled.connect(self._total_toggled)
        mrow.addWidget(self.chk_total)
        il.addLayout(mrow)
        self.lbl_total_desc = QLabel()
        self.lbl_total_desc.setObjectName("muted")
        self.lbl_total_desc.setWordWrap(True)
        il.addWidget(self.lbl_total_desc)
        cl.addWidget(inner)
        fw = _inner()
        fl = QVBoxLayout(fw)
        self.lbl_fw_title = QLabel()
        frow = QHBoxLayout()
        frow.addWidget(self.lbl_fw_title)
        frow.addStretch(1)
        self.chk_fw = ToggleSwitch()
        self.chk_fw.toggled.connect(self._fw_toggled)
        frow.addWidget(self.chk_fw)
        fl.addLayout(frow)
        self.lbl_fw_desc = QLabel()
        self.lbl_fw_desc.setObjectName("muted")
        self.lbl_fw_desc.setWordWrap(True)
        fl.addWidget(self.lbl_fw_desc)
        self.lbl_fw_admin = QLabel()
        fl.addWidget(self.lbl_fw_admin)
        cl.addWidget(fw)
        emg = _inner()
        el = QVBoxLayout(emg)
        self.lbl_total_restore = QLabel()
        self.lbl_total_restore.setObjectName("muted")
        self.lbl_total_restore.setWordWrap(True)
        el.addWidget(self.lbl_total_restore)
        self.btn_total_restore = _mkbtn("", "")
        self.btn_total_restore.setStyleSheet("background:#b91c1c; color:white; font-weight:bold;")
        self.btn_total_restore.clicked.connect(self.restore_internet)
        el.addWidget(self.btn_total_restore)
        cl.addWidget(emg)
        lay.addWidget(card)
        return self._wrap(lay)

    def _page_apps(self) -> QWidget:
        lay = QVBoxLayout()
        lay.setSpacing(14)

        # ---- hero ----
        hero = QFrame()
        hero.setObjectName("heroDash")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(20, 18, 20, 18)
        hl.setSpacing(14)
        pic = QLabel("🗂")
        pic.setObjectName("heroIcon")
        pic.setFixedSize(52, 52)
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(pic)
        hleft = QVBoxLayout()
        hleft.setSpacing(6)
        self.lbl_apps_title = QLabel()
        self.lbl_apps_title.setObjectName("title")
        self.lbl_apps_count = QLabel()
        self.lbl_apps_count.setObjectName("heroPill")
        hleft.addWidget(self.lbl_apps_title)
        hleft.addWidget(self.lbl_apps_count, alignment=Qt.AlignmentFlag.AlignLeft)
        hl.addLayout(hleft, 1)
        self.lbl_apps_sub = QLabel()
        self.lbl_apps_sub.setObjectName("heroHint")
        self.lbl_apps_sub.setWordWrap(True)
        hl.addWidget(self.lbl_apps_sub, 1)
        lay.addWidget(hero)

        # ---- lista ----
        apps = _card()
        al = QVBoxLayout(apps)
        al.setContentsMargins(16, 14, 16, 14)
        al.setSpacing(10)
        self.apps_box = QGridLayout()
        self.apps_box.setColumnStretch(1, 1)
        self.apps_box.setHorizontalSpacing(8)
        self.apps_box.setVerticalSpacing(6)
        al.addLayout(self.apps_box)
        self.lbl_apps_empty = QLabel()
        self.lbl_apps_empty.setObjectName("muted")
        self.lbl_apps_empty.setWordWrap(True)
        al.addWidget(self.lbl_apps_empty)
        lay.addWidget(apps)

        # ---- adicionar ----
        add = _card()
        adl = QVBoxLayout(add)
        adl.setContentsMargins(16, 14, 16, 14)
        adl.setSpacing(10)
        arow = QHBoxLayout()
        arow.setSpacing(10)
        self.edit_app_path = QLineEdit()
        self.edit_app_path.setMinimumHeight(44)
        self.edit_app_path.textChanged.connect(lambda *_: self.lbl_apps_msg.setVisible(False))
        self.edit_app_path.returnPressed.connect(self._app_add)
        self.btn_app_browse = _mkbtn("…", "")
        self.btn_app_browse.setFixedSize(52, 44)
        self.btn_app_browse.clicked.connect(self._app_browse)
        self.btn_app_add = _mkbtn("", "accent")
        self.btn_app_add.setMinimumHeight(44)
        self.btn_app_add.clicked.connect(self._app_add)
        arow.addWidget(self.edit_app_path, 1)
        arow.addWidget(self.btn_app_browse)
        arow.addWidget(self.btn_app_add)
        adl.addLayout(arow)
        self.lbl_apps_msg = QLabel("")
        self.lbl_apps_msg.setWordWrap(True)
        self.lbl_apps_msg.setVisible(False)
        adl.addWidget(self.lbl_apps_msg)
        self.lbl_apps_ff = QLabel()
        self.lbl_apps_ff.setObjectName("muted")
        self.lbl_apps_ff.setWordWrap(True)
        adl.addWidget(self.lbl_apps_ff)
        self.btn_leak_test = _mkbtn("", "")
        self.btn_leak_test.setMinimumHeight(44)
        self.btn_leak_test.clicked.connect(self._leak_test)
        adl.addWidget(self.btn_leak_test)
        lay.addWidget(add)
        return self._wrap(lay)

    def _page_vpn(self) -> QWidget:
        lay = QVBoxLayout()
        lay.setSpacing(14)

        # ---- hero ----
        hero = QFrame()
        hero.setObjectName("heroDash")
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(20, 18, 20, 18)
        hl.setSpacing(14)
        pic = QLabel("🔒")
        pic.setObjectName("heroIcon")
        pic.setFixedSize(52, 52)
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(pic)
        hleft = QVBoxLayout()
        hleft.setSpacing(6)
        self.lbl_vpn_title = QLabel()
        self.lbl_vpn_title.setObjectName("title")
        self.lbl_vpn_state = QLabel()
        self.lbl_vpn_state.setObjectName("heroPill")
        hleft.addWidget(self.lbl_vpn_title)
        hleft.addWidget(self.lbl_vpn_state, alignment=Qt.AlignmentFlag.AlignLeft)
        hl.addLayout(hleft, 1)
        self.lbl_vpn_hint = QLabel()
        self.lbl_vpn_hint.setObjectName("heroHint")
        self.lbl_vpn_hint.setWordWrap(True)
        hl.addWidget(self.lbl_vpn_hint, 1)
        lay.addWidget(hero)

        # ---- VPNs detectadas ----
        det = _card()
        dl = QVBoxLayout(det)
        dl.setContentsMargins(16, 14, 16, 14)
        dl.setSpacing(10)
        dhead = QHBoxLayout()
        dhead.setSpacing(10)
        dico = QLabel("🔍")
        dico.setObjectName("featIcon")
        dico.setFixedSize(40, 40)
        dico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dhead.addWidget(dico)
        self.lbl_vpn_det_title = QLabel()
        self.lbl_vpn_det_title.setObjectName("title")
        dhead.addWidget(self.lbl_vpn_det_title, 1)
        self.btn_vpn_refresh = _mkbtn("⟳", "")
        self.btn_vpn_refresh.setMinimumHeight(40)
        self.btn_vpn_refresh.clicked.connect(self._vpn_refresh)
        dhead.addWidget(self.btn_vpn_refresh)
        dl.addLayout(dhead)
        self.lbl_vpn_list = QLabel()
        self.lbl_vpn_list.setObjectName("sec")
        self.lbl_vpn_list.setWordWrap(True)
        dl.addWidget(self.lbl_vpn_list)
        self.lbl_vpn_det_note = QLabel()
        self.lbl_vpn_det_note.setObjectName("muted")
        self.lbl_vpn_det_note.setWordWrap(True)
        dl.addWidget(self.lbl_vpn_det_note)
        lay.addWidget(det)

        # ---- OpenVPN própria ----
        ov = _card()
        ol = QVBoxLayout(ov)
        ol.setContentsMargins(16, 14, 16, 14)
        ol.setSpacing(10)
        ohead = QHBoxLayout()
        ohead.setSpacing(10)
        oico = QLabel("⚙")
        oico.setObjectName("featIcon")
        oico.setFixedSize(40, 40)
        oico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ohead.addWidget(oico)
        self.lbl_vpn_ovpn_title = QLabel()
        self.lbl_vpn_ovpn_title.setObjectName("title")
        ohead.addWidget(self.lbl_vpn_ovpn_title, 1)
        ol.addLayout(ohead)
        self.lbl_vpn_bin = QLabel()
        self.lbl_vpn_bin.setObjectName("sec")
        ol.addWidget(self.lbl_vpn_bin)
        brow = QHBoxLayout()
        brow.setSpacing(10)
        self.edit_vpn_bin = QLineEdit()
        self.edit_vpn_bin.setMinimumHeight(42)
        self.btn_vpn_bin_browse = _mkbtn("…", "")
        self.btn_vpn_bin_browse.setFixedSize(52, 42)
        self.btn_vpn_bin_browse.clicked.connect(lambda: self._vpn_browse("bin"))
        brow.addWidget(self.edit_vpn_bin, 1)
        brow.addWidget(self.btn_vpn_bin_browse)
        ol.addLayout(brow)
        self.lbl_vpn_cfg = QLabel()
        self.lbl_vpn_cfg.setObjectName("sec")
        ol.addWidget(self.lbl_vpn_cfg)
        crow = QHBoxLayout()
        crow.setSpacing(10)
        self.edit_vpn_config = QLineEdit()
        self.edit_vpn_config.setMinimumHeight(42)
        self.btn_vpn_cfg_browse = _mkbtn("…", "")
        self.btn_vpn_cfg_browse.setFixedSize(52, 42)
        self.btn_vpn_cfg_browse.clicked.connect(lambda: self._vpn_browse("cfg"))
        crow.addWidget(self.edit_vpn_config, 1)
        crow.addWidget(self.btn_vpn_cfg_browse)
        ol.addLayout(crow)
        urow = QHBoxLayout()
        urow.setSpacing(10)
        self.lbl_vpn_user = QLabel()
        self.lbl_vpn_user.setObjectName("sec")
        self.edit_vpn_user = QLineEdit()
        self.edit_vpn_user.setMinimumHeight(42)
        self.lbl_vpn_pass = QLabel()
        self.lbl_vpn_pass.setObjectName("sec")
        self.edit_vpn_pass = QLineEdit()
        self.edit_vpn_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_vpn_pass.setMinimumHeight(42)
        urow.addWidget(self.lbl_vpn_user)
        urow.addWidget(self.edit_vpn_user, 1)
        urow.addWidget(self.lbl_vpn_pass)
        urow.addWidget(self.edit_vpn_pass, 1)
        ol.addLayout(urow)
        orow = QHBoxLayout()
        orow.setSpacing(10)
        self.btn_vpn_connect = _mkbtn("", "success")
        self.btn_vpn_connect.setMinimumHeight(44)
        self.btn_vpn_connect.clicked.connect(self._vpn_connect)
        self.btn_vpn_disc = _mkbtn("", "")
        self.btn_vpn_disc.setMinimumHeight(44)
        self.btn_vpn_disc.clicked.connect(self._vpn_disconnect)
        self.btn_vpn_log = _mkbtn("", "")
        self.btn_vpn_log.setMinimumHeight(44)
        self.btn_vpn_log.clicked.connect(self._vpn_show_log)
        orow.addWidget(self.btn_vpn_connect)
        orow.addWidget(self.btn_vpn_disc)
        orow.addWidget(self.btn_vpn_log)
        ol.addLayout(orow)
        self.lbl_vpn_log = QLabel()
        self.lbl_vpn_log.setObjectName("muted")
        self.lbl_vpn_log.setWordWrap(True)
        self.lbl_vpn_log.setStyleSheet("font-family: monospace;")
        self.lbl_vpn_log.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        ol.addWidget(self.lbl_vpn_log)
        lay.addWidget(ov)
        return self._wrap(lay)

    def _page_logs(self) -> QWidget:
        lay = QVBoxLayout()
        card = _card()
        cl = QVBoxLayout(card)
        self.lbl_logs_title = QLabel()
        self.lbl_logs_title.setObjectName("title")
        cl.addWidget(self.lbl_logs_title)
        self.lbl_logs_info = QLabel()
        self.lbl_logs_info.setObjectName("muted")
        self.lbl_logs_info.setWordWrap(True)
        cl.addWidget(self.lbl_logs_info)
        frow = QHBoxLayout()
        self.lbl_filter = QLabel()
        self.lbl_filter.setObjectName("muted")
        self.edit_filter = QLineEdit()
        self.edit_filter.textChanged.connect(lambda: self._render_logs())
        frow.addWidget(self.lbl_filter)
        frow.addWidget(self.edit_filter, 1)
        cl.addLayout(frow)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-family: monospace; font-size: 11px;")
        self.log_view.setMinimumHeight(380)
        cl.addWidget(self.log_view)
        brow = QHBoxLayout()
        self.btn_pause = _mkbtn("")
        self.btn_pause.setCheckable(True)
        self.btn_pause.toggled.connect(lambda v: setattr(self, "_log_paused", bool(v)) or self.refresh_texts())
        self.btn_copylog = _mkbtn("")
        self.btn_copylog.clicked.connect(self._copy_log)
        self.btn_clearlog = _mkbtn("")
        self.btn_clearlog.clicked.connect(self._clear_log)
        self.btn_nolog = _mkbtn("")
        self.btn_nolog.setCheckable(True)
        self.btn_nolog.toggled.connect(self._nolog_toggled)
        brow.addWidget(self.btn_pause)
        brow.addWidget(self.btn_copylog)
        brow.addWidget(self.btn_clearlog)
        brow.addWidget(self.btn_nolog)
        cl.addLayout(brow)
        self.lbl_nolog_hint = QLabel()
        self.lbl_nolog_hint.setObjectName("muted")
        self.lbl_nolog_hint.setWordWrap(True)
        cl.addWidget(self.lbl_nolog_hint)
        lay.addWidget(card)
        return self._wrap(lay)

    def _page_scan(self) -> QWidget:
        lay = QVBoxLayout()
        lay.setSpacing(14)
        card = _card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(10)
        self.lbl_scan_title = QLabel()
        self.lbl_scan_title.setObjectName("title")
        cl.addWidget(self.lbl_scan_title)
        self.lbl_scan_engine = QLabel()
        self.lbl_scan_engine.setObjectName("sec")
        cl.addWidget(self.lbl_scan_engine)
        self.lbl_scan_admin = QLabel()
        self.lbl_scan_admin.setWordWrap(True)
        self.lbl_scan_admin.setVisible(False)
        cl.addWidget(self.lbl_scan_admin)
        trow = QHBoxLayout()
        trow.setSpacing(10)
        self.lbl_scan_target = QLabel()
        self.lbl_scan_target.setObjectName("muted")
        self.edit_scan_target = QLineEdit()
        self.edit_scan_target.setMinimumHeight(42)
        self.edit_scan_target.setPlaceholderText("127.0.0.1 / scanme.nmap.org")
        self.edit_scan_target.textChanged.connect(lambda *_: self._scan_preview())
        trow.addWidget(self.lbl_scan_target)
        trow.addWidget(self.edit_scan_target, 1)
        cl.addLayout(trow)
        prow = QHBoxLayout()
        prow.setSpacing(10)
        self.lbl_scan_profile = QLabel()
        self.lbl_scan_profile.setObjectName("muted")
        self.combo_scan = QComboBox()
        self.combo_scan.setMinimumHeight(40)
        self.combo_scan.currentIndexChanged.connect(self._scan_preset)
        prow.addWidget(self.lbl_scan_profile)
        prow.addWidget(self.combo_scan, 1)
        self.btn_scan_adv = _mkbtn("", "")
        self.btn_scan_adv.setCheckable(True)
        self.btn_scan_adv.setMinimumHeight(40)
        self.btn_scan_adv.toggled.connect(lambda v: self.scan_advbox.setVisible(bool(v)))
        prow.addWidget(self.btn_scan_adv)
        cl.addLayout(prow)

        # ---- painel avançado ----
        self.scan_advbox = QWidget()
        self.scan_advbox.setVisible(False)
        adv = QVBoxLayout(self.scan_advbox)
        adv.setContentsMargins(0, 0, 0, 0)
        adv.setSpacing(10)
        advcard = _inner()
        al = QVBoxLayout(advcard)
        al.setSpacing(10)
        # tipo + portas
        tyrow = QHBoxLayout()
        tyrow.setSpacing(10)
        self.lbl_scan_type = QLabel()
        self.lbl_scan_type.setObjectName("sec")
        self.combo_scan_type = QComboBox()
        self.combo_scan_type.setMinimumHeight(40)
        tyrow.addWidget(self.lbl_scan_type)
        tyrow.addWidget(self.combo_scan_type, 1)
        self.lbl_scan_ports = QLabel()
        self.lbl_scan_ports.setObjectName("sec")
        self.edit_scan_ports = QLineEdit()
        self.edit_scan_ports.setMinimumHeight(40)
        tyrow.addWidget(self.lbl_scan_ports)
        tyrow.addWidget(self.edit_scan_ports, 1)
        al.addLayout(tyrow)
        # descoberta + timing
        dtrow = QHBoxLayout()
        dtrow.setSpacing(10)
        self.lbl_scan_disc = QLabel()
        self.lbl_scan_disc.setObjectName("sec")
        self.combo_scan_disc = QComboBox()
        self.combo_scan_disc.setMinimumHeight(40)
        dtrow.addWidget(self.lbl_scan_disc)
        dtrow.addWidget(self.combo_scan_disc, 1)
        self.lbl_scan_timing = QLabel()
        self.lbl_scan_timing.setObjectName("sec")
        self.combo_scan_timing = QComboBox()
        self.combo_scan_timing.setMinimumHeight(40)
        dtrow.addWidget(self.lbl_scan_timing)
        dtrow.addWidget(self.combo_scan_timing, 1)
        al.addLayout(dtrow)
        # flags
        frow = QHBoxLayout()
        frow.setSpacing(12)
        self.chk_scan_sv = QCheckBox()
        self.chk_scan_os = QCheckBox()
        self.chk_scan_aggr = QCheckBox()
        self.chk_scan_reason = QCheckBox()
        self.chk_scan_frag = QCheckBox()
        for c in (self.chk_scan_sv, self.chk_scan_os, self.chk_scan_aggr,
                  self.chk_scan_reason, self.chk_scan_frag):
            frow.addWidget(c)
        frow.addStretch(1)
        al.addLayout(frow)
        # decoy
        drow = QHBoxLayout()
        drow.setSpacing(10)
        self.lbl_scan_decoy = QLabel()
        self.lbl_scan_decoy.setObjectName("sec")
        self.edit_scan_decoy = QLineEdit()
        self.edit_scan_decoy.setMinimumHeight(40)
        drow.addWidget(self.lbl_scan_decoy)
        drow.addWidget(self.edit_scan_decoy, 1)
        al.addLayout(drow)
        # NSE
        nrow = QHBoxLayout()
        nrow.setSpacing(10)
        self.lbl_scan_scripts = QLabel()
        self.lbl_scan_scripts.setObjectName("sec")
        self.edit_scan_scripts = QLineEdit()
        self.edit_scan_scripts.setMinimumHeight(40)
        nrow.addWidget(self.lbl_scan_scripts)
        nrow.addWidget(self.edit_scan_scripts, 1)
        al.addLayout(nrow)
        arow2 = QHBoxLayout()
        arow2.setSpacing(10)
        self.lbl_scan_script_args = QLabel()
        self.lbl_scan_script_args.setObjectName("sec")
        self.edit_scan_script_args = QLineEdit()
        self.edit_scan_script_args.setMinimumHeight(40)
        arow2.addWidget(self.lbl_scan_script_args)
        arow2.addWidget(self.edit_scan_script_args, 1)
        al.addLayout(arow2)
        # saída extra
        orow2 = QHBoxLayout()
        orow2.setSpacing(10)
        self.lbl_scan_outfmt = QLabel()
        self.lbl_scan_outfmt.setObjectName("sec")
        self.combo_scan_out = QComboBox()
        self.combo_scan_out.setMinimumHeight(40)
        orow2.addWidget(self.lbl_scan_outfmt)
        orow2.addWidget(self.combo_scan_out, 1)
        al.addLayout(orow2)
        adv.addWidget(advcard)
        cl.addWidget(self.scan_advbox)

        # args extras livres
        self.lbl_scan_extra = QLabel()
        self.lbl_scan_extra.setObjectName("sec")
        cl.addWidget(self.lbl_scan_extra)
        self.edit_scan_args = QLineEdit()
        self.edit_scan_args.setMinimumHeight(40)
        self.edit_scan_args.setPlaceholderText("-sV -p 1-1000 --open")
        self.edit_scan_args.textChanged.connect(lambda *_: self._scan_preview())
        cl.addWidget(self.edit_scan_args)
        # preview do comando
        prev = _inner()
        pl = QVBoxLayout(prev)
        self.lbl_scan_cmd_title = QLabel()
        self.lbl_scan_cmd_title.setObjectName("sec")
        pl.addWidget(self.lbl_scan_cmd_title)
        self.lbl_scan_cmd = QLabel()
        self.lbl_scan_cmd.setObjectName("mono")
        self.lbl_scan_cmd.setWordWrap(True)
        self.lbl_scan_cmd.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        pl.addWidget(self.lbl_scan_cmd)
        cl.addWidget(prev)
        for c in (self.combo_scan_type, self.combo_scan_disc, self.combo_scan_timing,
                  self.combo_scan_out):
            c.currentIndexChanged.connect(lambda *_: self._scan_preview())
        for c in (self.chk_scan_sv, self.chk_scan_os, self.chk_scan_aggr,
                  self.chk_scan_reason, self.chk_scan_frag):
            c.toggled.connect(lambda *_: self._scan_preview())
        for e in (self.edit_scan_ports, self.edit_scan_decoy,
                  self.edit_scan_scripts, self.edit_scan_script_args):
            e.textChanged.connect(lambda *_: self._scan_preview())

        orow = QHBoxLayout()
        orow.setSpacing(10)
        self.chk_scan_tor = QCheckBox()
        self.chk_scan_open = QCheckBox()
        self.chk_scan_noping = QCheckBox()
        orow.addWidget(self.chk_scan_tor)
        orow.addWidget(self.chk_scan_open)
        orow.addWidget(self.chk_scan_noping)
        cl.addLayout(orow)
        self.chk_scan_tor.toggled.connect(lambda *_: self._scan_preview())
        self.chk_scan_open.toggled.connect(lambda *_: self._scan_preview())
        self.chk_scan_noping.toggled.connect(lambda *_: self._scan_preview())
        brow = QHBoxLayout()
        brow.setSpacing(10)
        self.btn_scan_run = _mkbtn("", "accent")
        self.btn_scan_run.setMinimumHeight(44)
        self.btn_scan_run.clicked.connect(self._scan_run)
        self.btn_scan_stop = _mkbtn("")
        self.btn_scan_stop.setMinimumHeight(44)
        self.btn_scan_stop.clicked.connect(self._scan_stop)
        self.btn_scan_save = _mkbtn("")
        self.btn_scan_save.setMinimumHeight(44)
        self.btn_scan_save.clicked.connect(self._scan_save)
        brow.addWidget(self.btn_scan_run)
        brow.addWidget(self.btn_scan_stop)
        brow.addWidget(self.btn_scan_save)
        cl.addLayout(brow)
        self.scan_out = QPlainTextEdit()
        self.scan_out.setReadOnly(True)
        self.scan_out.setStyleSheet("font-family: monospace; font-size: 11px;")
        self.scan_out.setMinimumHeight(300)
        cl.addWidget(self.scan_out)
        self.lbl_scan_warn = QLabel()
        self.lbl_scan_warn.setObjectName("muted")
        self.lbl_scan_warn.setWordWrap(True)
        cl.addWidget(self.lbl_scan_warn)
        lay.addWidget(card)
        return self._wrap(lay)

    def _page_diag(self) -> QWidget:
        lay = QVBoxLayout()
        card = _card()
        cl = QVBoxLayout(card)
        self.lbl_diag_title = QLabel()
        self.lbl_diag_title.setObjectName("title")
        cl.addWidget(self.lbl_diag_title)
        inner = _inner()
        il = QVBoxLayout(inner)
        self.lbl_diag_tor = QLabel()
        il.addWidget(self.lbl_diag_tor)
        trow = QHBoxLayout()
        self.lbl_target = QLabel()
        self.lbl_target.setObjectName("muted")
        self.edit_target = QLineEdit()
        self.edit_target.editingFinished.connect(lambda: (setattr(self.cfg, "test_target", self.edit_target.text().strip() or "check.torproject.org:80"), self.cfg.save()))
        self.btn_test = _mkbtn("", "accent")
        self.btn_test.clicked.connect(self._test_tor)
        trow.addWidget(self.lbl_target)
        trow.addWidget(self.edit_target, 1)
        trow.addWidget(self.btn_test)
        il.addLayout(trow)
        cl.addWidget(inner)
        net = _inner()
        nl = QVBoxLayout(net)
        self.lbl_net_title = QLabel()
        nl.addWidget(self.lbl_net_title)
        self.lbl_net_desc = QLabel()
        self.lbl_net_desc.setObjectName("muted")
        self.lbl_net_desc.setWordWrap(True)
        nl.addWidget(self.lbl_net_desc)
        self.btn_net = _mkbtn("", "accent")
        self.btn_net.setStyleSheet("background:#0891b2; color:white; font-weight:bold;")
        self.btn_net.clicked.connect(self._test_net)
        nl.addWidget(self.btn_net)
        self.btn_e2e = _mkbtn("", "success")
        self.btn_e2e.setMinimumHeight(44)
        self.btn_e2e.clicked.connect(self._e2e_run)
        nl.addWidget(self.btn_e2e)
        cl.addWidget(net)
        # Emergência: sem internet após proteção total/crash
        emg = _inner()
        el = QVBoxLayout(emg)
        self.lbl_restore_title = QLabel()
        self.lbl_restore_title.setObjectName("title")
        el.addWidget(self.lbl_restore_title)
        self.lbl_restore_desc = QLabel()
        self.lbl_restore_desc.setObjectName("muted")
        self.lbl_restore_desc.setWordWrap(True)
        el.addWidget(self.lbl_restore_desc)
        self.btn_net_restore = _mkbtn("", "accent")
        self.btn_net_restore.setStyleSheet("background:#b91c1c; color:white; font-weight:bold;")
        self.btn_net_restore.clicked.connect(self.restore_internet)
        el.addWidget(self.btn_net_restore)
        cl.addWidget(emg)
        wipe = _inner()
        wl = QVBoxLayout(wipe)
        self.lbl_wipe_title = QLabel()
        wl.addWidget(self.lbl_wipe_title)
        self.lbl_wipe_desc = QLabel()
        self.lbl_wipe_desc.setObjectName("muted")
        self.lbl_wipe_desc.setWordWrap(True)
        wl.addWidget(self.lbl_wipe_desc)
        self.btn_wipe = _mkbtn("")
        self.btn_wipe.setStyleSheet("background:#b45309; color:white; font-weight:bold;")
        self.btn_wipe.clicked.connect(self._wipe)
        wl.addWidget(self.btn_wipe)
        cl.addWidget(wipe)
        self.lbl_result = QLabel()
        self.lbl_result.setWordWrap(True)
        self.lbl_result.setStyleSheet("font-family: monospace;")
        self.lbl_result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cl.addWidget(self.lbl_result)
        # Cofre AES-256
        sec = _inner()
        sl = QVBoxLayout(sec)
        self.lbl_vault_title = QLabel()
        sl.addWidget(self.lbl_vault_title)
        self.lbl_vault_desc = QLabel()
        self.lbl_vault_desc.setObjectName("muted")
        self.lbl_vault_desc.setWordWrap(True)
        sl.addWidget(self.lbl_vault_desc)
        self.btn_vault = _mkbtn("")
        self.btn_vault.clicked.connect(self._change_password)
        sl.addWidget(self.btn_vault)
        cl.addWidget(sec)
        # Dados: abrir pasta + restaurar padrão (paridade com menu Rust)
        drow = QHBoxLayout()
        self.btn_data = _mkbtn("")
        self.btn_data.clicked.connect(self.open_data_folder)
        self.btn_reset = _mkbtn("")
        self.btn_reset.clicked.connect(self.reset_config)
        drow.addWidget(self.btn_data)
        drow.addWidget(self.btn_reset)
        cl.addLayout(drow)
        # Backup do perfil: exportar/importar cofre
        brow = QHBoxLayout()
        self.btn_backup_exp = _mkbtn("", "accent")
        self.btn_backup_exp.clicked.connect(self.backup_export)
        self.btn_backup_imp = _mkbtn("")
        self.btn_backup_imp.clicked.connect(self.backup_import)
        brow.addWidget(self.btn_backup_exp)
        brow.addWidget(self.btn_backup_imp)
        cl.addLayout(brow)
        lay.addWidget(card)
        return self._wrap(lay)

    def _page_update(self) -> QWidget:
        lay = QVBoxLayout()
        card = _card()
        cl = QVBoxLayout(card)
        self.lbl_upd_title = QLabel()
        self.lbl_upd_title.setObjectName("title")
        cl.addWidget(self.lbl_upd_title)
        self.lbl_tor_ver = QLabel()
        self.lbl_tor_ver.setObjectName("muted")
        cl.addWidget(self.lbl_tor_ver)
        self.lbl_upd_note = QLabel()
        self.lbl_upd_note.setObjectName("muted")
        self.lbl_upd_note.setWordWrap(True)
        cl.addWidget(self.lbl_upd_note)
        self.lbl_upd_src = QLabel()
        self.lbl_upd_src.setObjectName("sec")
        cl.addWidget(self.lbl_upd_src)
        segbox = QWidget()
        segbox.setObjectName("segbox")
        srow = QHBoxLayout(segbox)
        srow.setContentsMargins(4, 4, 4, 4)
        srow.setSpacing(4)
        self.btn_upd_src_gh = _mkbtn("GitHub", "seg")
        self.btn_upd_src_gh.setCheckable(True)
        self.btn_upd_src_gh.clicked.connect(lambda: self._upd_src_set("gh"))
        self.btn_upd_src_url = _mkbtn("URL", "seg")
        self.btn_upd_src_url.setCheckable(True)
        self.btn_upd_src_url.clicked.connect(lambda: self._upd_src_set("url"))
        srow.addWidget(self.btn_upd_src_gh)
        srow.addWidget(self.btn_upd_src_url)
        cl.addWidget(segbox)
        self.gh_box = QWidget()
        gl = QVBoxLayout(self.gh_box)
        gl.setContentsMargins(0, 0, 0, 0)
        rrow = QHBoxLayout()
        self.lbl_upd_repo = QLabel()
        self.lbl_upd_repo.setObjectName("muted")
        self.edit_repo = QLineEdit()
        self.edit_repo.editingFinished.connect(lambda: (setattr(self.cfg, "update_repo", self.edit_repo.text().strip()), self.cfg.save()))
        self.btn_upd_check = _mkbtn("", "accent")
        self.btn_upd_check.clicked.connect(self._upd_check)
        rrow.addWidget(self.lbl_upd_repo)
        rrow.addWidget(self.edit_repo, 1)
        rrow.addWidget(self.btn_upd_check)
        gl.addLayout(rrow)
        cl.addWidget(self.gh_box)
        self.url_box = QWidget()
        ul = QVBoxLayout(self.url_box)
        ul.setContentsMargins(0, 0, 0, 0)
        ul.setSpacing(10)
        self.lbl_upd_url = QLabel()
        self.lbl_upd_url.setObjectName("sec")
        ul.addWidget(self.lbl_upd_url)
        self.edit_upd_url = QLineEdit()
        self.edit_upd_url.setMinimumHeight(42)
        ul.addWidget(self.edit_upd_url)
        self.lbl_upd_sha = QLabel()
        self.lbl_upd_sha.setObjectName("sec")
        ul.addWidget(self.lbl_upd_sha)
        self.edit_upd_sha = QLineEdit()
        self.edit_upd_sha.setMinimumHeight(42)
        ul.addWidget(self.edit_upd_sha)
        self.btn_upd_dl_url = _mkbtn("", "accent")
        self.btn_upd_dl_url.setMinimumHeight(44)
        self.btn_upd_dl_url.clicked.connect(self._upd_dl_url)
        ul.addWidget(self.btn_upd_dl_url)
        cl.addWidget(self.url_box)
        self.lbl_upd_status = QLabel()
        self.lbl_upd_status.setWordWrap(True)
        cl.addWidget(self.lbl_upd_status)
        self.upd_assets = QVBoxLayout()
        cl.addLayout(self.upd_assets)
        self.btn_upd_open = _mkbtn("")
        self.btn_upd_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(f"https://github.com/{self.cfg.update_repo}/releases")) if self.cfg.update_repo else None)
        cl.addWidget(self.btn_upd_open)
        lay.addWidget(card)

        # Sobre / Licenças (atribuição exigida pelas licenças BSD/Apache)
        about = _card()
        al = QVBoxLayout(about)
        self.lbl_about_title = QLabel()
        self.lbl_about_title.setObjectName("title")
        al.addWidget(self.lbl_about_title)
        self.lbl_about_text = QLabel()
        self.lbl_about_text.setObjectName("muted")
        self.lbl_about_text.setWordWrap(True)
        self.lbl_about_text.setOpenExternalLinks(True)
        al.addWidget(self.lbl_about_text)
        self.btn_licenses = _mkbtn("")
        self.btn_licenses.clicked.connect(self._show_licenses)
        al.addWidget(self.btn_licenses)
        lay.addWidget(about)
        return self._wrap(lay)

    def _page_about(self) -> QWidget:
        """Página Sobre: atribuição + licenças embutidas (sem diálogo)."""
        from PyQt6.QtWidgets import QComboBox, QPlainTextEdit
        lay = QVBoxLayout()
        hero = _card()
        hl = QVBoxLayout(hero)
        self.lbl_about2_title = QLabel()
        self.lbl_about2_title.setObjectName("title")
        hl.addWidget(self.lbl_about2_title)
        self.lbl_about2_ver = QLabel()
        self.lbl_about2_ver.setObjectName("muted")
        hl.addWidget(self.lbl_about2_ver)
        self.lbl_about2_text = QLabel()
        self.lbl_about2_text.setObjectName("muted")
        self.lbl_about2_text.setWordWrap(True)
        self.lbl_about2_text.setOpenExternalLinks(True)
        hl.addWidget(self.lbl_about2_text)
        lay.addWidget(hero)
        lic = _card()
        ll = QVBoxLayout(lic)
        self.lbl_about2_lic = QLabel()
        self.lbl_about2_lic.setObjectName("sec")
        ll.addWidget(self.lbl_about2_lic)
        self.combo_lic = QComboBox()
        ll.addWidget(self.combo_lic)
        self.view_lic = QPlainTextEdit()
        self.view_lic.setReadOnly(True)
        self.view_lic.setStyleSheet("font-family: monospace; font-size: 11px;")
        self.view_lic.setMinimumHeight(260)
        ll.addWidget(self.view_lic, 1)
        self.combo_lic.currentIndexChanged.connect(self._lic_load)
        self.lbl_about2_gpl = QLabel()
        self.lbl_about2_gpl.setObjectName("muted")
        self.lbl_about2_gpl.setWordWrap(True)
        ll.addWidget(self.lbl_about2_gpl)
        lay.addWidget(lic, 1)
        return self._wrap(lay)


LOGIN_QSS = """
QDialog#login { background: #08081a; }
QFrame#hero {
  background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 #a78bfa, stop:0.35 #7c3aed, stop:0.7 #5b21b6, stop:1 #1e1b4b);
  border: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.18);
}
QLabel#logoRing {
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 38px;
}
QLabel#logo { background: transparent; border: none; font-size: 34px; }
QLabel#appname { color: white; font-size: 27px; font-weight: 800; letter-spacing: 0.5px; }
QFrame#sidePanel {
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
    stop:0 #8b5cf6, stop:0.45 #6d28d9, stop:1 #1e1b4b);
  border: none;
}
QLabel#sideTitle { color: white; font-size: 15px; font-weight: 800; letter-spacing: 0px; }
QLabel#sideFeat {
  color: white; background: rgba(0, 0, 0, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.25); border-radius: 10px;
  padding: 9px 12px; font-size: 12px; font-weight: 600;
}
QLabel#formTitle { color: #e9e8ff; font-size: 20px; font-weight: 800; }
QLabel#capswarn { color: #fbbf24; font-size: 11px; font-weight: 700; }
QLabel#verPill {
  color: #ede9fe; background: rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.35); border-radius: 10px;
  padding: 3px 10px; font-size: 11px; font-weight: 700;
}
QLabel#appsub { color: rgba(255, 255, 255, 0.88); font-size: 12px; }
QLabel#featPill {
  color: white; background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.28); border-radius: 11px;
  padding: 5px 11px; font-size: 11px; font-weight: 600;
}
QLabel#sect { color: #c4b5fd; font-size: 11px; font-weight: bold; }
QLabel#count {
  color: #a5b4fc; background: rgba(124, 58, 237, 0.18);
  border: 1px solid #4c3a8c; border-radius: 9px; padding: 2px 9px; font-size: 11px;
}
QListWidget#users {
  background: #141428; border: 1px solid #2a2a4d; border-radius: 13px;
  padding: 6px; outline: 0; font-size: 13px;
}
QListWidget#users::item { background: transparent; border: 1px solid transparent; border-radius: 10px; margin: 2px; }
QListWidget#users::item:selected { background: #251d4d; border: 1px solid #7c3aed; }
QListWidget#users::item:hover:!selected { background: #1c1c38; }
QLabel#avatar { border-radius: 18px; font-weight: 800; font-size: 15px; color: white; }
QLabel#uname { color: #f1f0ff; font-size: 14px; font-weight: 600; }
QLabel#usub { color: #8b8ba3; font-size: 11px; }
QLabel#go { color: #8b8ba3; font-size: 16px; font-weight: bold; }
QLabel#fld { color: #b9b9d0; font-size: 12px; font-weight: 600; }
QLineEdit#pass, QLineEdit#field {
  background: #141428; border: 1px solid #2e2e5c; border-radius: 11px;
  padding: 11px 12px; color: #ffffff; font-size: 14px; selection-background-color: #7c3aed;
}
QLineEdit#pass:focus, QLineEdit#field:focus { border: 1px solid #7c3aed; background: #171730; }
QPushButton#eye {
  background: transparent; border: none; color: #8b8ba3; font-size: 16px;
  padding: 4px 8px;
}
QPushButton#eye:hover { color: white; }
QPushButton#primary {
  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8b5cf6, stop:1 #6d28d9);
  border: 1px solid #a78bfa; border-radius: 11px; padding: 12px;
  color: white; font-weight: 800; font-size: 14px;
}
QPushButton#primary:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a78bfa, stop:1 #7c3aed); }
QPushButton#primary:disabled { background: #2a2a45; border: 1px solid #34345a; color: #71718c; }
QPushButton#ghost {
  background: #1a1a33; border: 1px solid #33335f; border-radius: 10px;
  padding: 9px; color: #d6d3f5; font-size: 13px;
}
QPushButton#ghost:hover { background: #232344; border: 1px solid #4c4c8c; }
QPushButton#dangerGhost {
  background: transparent; border: 1px solid #5b2b35; color: #fca5a5;
  border-radius: 10px; padding: 9px; font-size: 13px;
}
QPushButton#dangerGhost:hover { background: #2a1620; }
QPushButton#guestBtn {
  background: transparent; border: 1px dashed #4c4c7a; border-radius: 10px;
  padding: 10px; color: #a5b4fc; font-size: 13px;
}
QPushButton#guestBtn:hover { background: #171730; border: 1px dashed #7c3aed; color: white; }
QComboBox#langBox {
  background: #141428; border: 1px solid #2e2e5c; border-radius: 9px;
  padding: 5px 8px; color: #d6d3f5; font-size: 12px;
}
QComboBox#langBox QAbstractItemView {
  background: #1c1c40; color: white; selection-background-color: #7c3aed;
  border: 1px solid #3a3a6e;
}
QLabel#error {
  color: #fca5a5; background: #2a1620; border: 1px solid #5b2b35;
  border-radius: 8px; padding: 7px 10px; font-size: 12px;
}
QLabel#okmsg {
  color: #6ee7b7; background: #0c2b22; border: 1px solid #14532d;
  border-radius: 8px; padding: 7px 10px; font-size: 12px;
}
QLabel#foot { color: #63637c; font-size: 11px; }
QLabel#div { color: #4c4c6e; font-size: 11px; }
QLabel#emptitle { color: #e9e8ff; font-size: 14px; font-weight: 700; }
QLabel#empdesc { color: #8b8ba3; font-size: 12px; }
QFrame#emptyBox { background: #141428; border: 1px dashed #3a3a63; border-radius: 13px; }
"""


def _login_tr(lang: str, key: str, fallback: str) -> str:
    s = t(lang, key)
    return fallback if s == key else s


_AVATAR_COLORS = ("#7c3aed", "#059669", "#0284c7", "#ea580c", "#db2777", "#4f46e5")


def _avatar_color(name: str) -> str:
    return _AVATAR_COLORS[(abs(hash(name)) % len(_AVATAR_COLORS))]


class LoginDialog(QDialog):
    """Tela inicial moderna: perfis locais, senha, criar/excluir ou convidado."""

    def __init__(self, parent, lang: str):
        super().__init__(parent)
        self._lang = lang
        self.result_kind: str | None = None  # user | guest
        self.result_id = ""
        self.result_pw = ""
        self._users: list[dict] = []
        self.setWindowTitle(t(lang, "user_title"))
        self.setObjectName("login")
        self.setMinimumSize(720, 560)
        self.resize(760, 600)
        self.setStyleSheet(LOGIN_QSS)

        from PyQt6.QtWidgets import QListWidget

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- painel lateral (marca) ----
        side = QFrame()
        side.setObjectName("sidePanel")
        side.setFixedWidth(300)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(28, 30, 28, 28)
        sl.setSpacing(8)
        # Sem alinhamento global: labels de texto esticam na largura útil
        # (244px) e quebram linha; só o anel do logo é centralizado.
        # anel do logo (usa o ícone real se existir, senão emoji)
        ring = QLabel()
        ring.setObjectName("logoRing")
        ring.setFixedSize(88, 88)
        ring.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo = QLabel(ring)
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            import os as _os
            from PyQt6.QtGui import QPixmap as _Px
            _here = _os.path.dirname(_os.path.abspath(__file__))
            _icon = None
            for _c in (_os.path.join(_here, "..", "assets", "icon.png"),
                       _os.path.join(_here, "assets", "icon.png"),
                       _os.path.join("assets", "icon.png")):
                if _os.path.exists(_c):
                    _icon = _c
                    break
            if _icon:
                _px = _Px(_icon).scaled(
                    76, 76, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                logo.setPixmap(_px)
                logo.resize(76, 76)
                logo.move(6, 6)
            else:
                raise OSError
        except Exception:
            logo.setText("🛡")
            logo.setStyleSheet("background: transparent; border: none; font-size: 38px;")
            logo.setFixedSize(88, 88)
        # Linha única reduzida (15px, QSS): cabe nos ~244px úteis do
        # painel sem cortar o "A" inicial nem o "D" final. wordWrap fica
        # como rede de segurança (quebra em 2 linhas em vez de cortar).
        name = QLabel("Anonymous Shield")
        name.setObjectName("sideTitle")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setWordWrap(True)
        try:
            from . import __version__ as _v
            ver = QLabel(f"v{_v}")
        except Exception:
            ver = QLabel("")
        ver.setObjectName("verPill")
        sub = QLabel(_login_tr(lang, "motto", "Privacidade • Liberdade • Anonimato"))
        sub.setObjectName("appsub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        self.hero_sub = sub
        sl.addWidget(ring, alignment=Qt.AlignmentFlag.AlignHCenter)
        sl.addWidget(name)
        if ver.text():
            _vrow = QHBoxLayout()
            _vrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _vrow.addWidget(ver)
            sl.addLayout(_vrow)
        sl.addWidget(sub)
        sl.addStretch(1)
        self.hero_feats = []
        for _ic, _key, _fb in (("🔐", "user_feat_vault", "Cofre AES-256 por perfil"),
                               ("💻", "user_feat_local", "100% local, nada sai do PC"),
                               ("🛡", "user_feat_tor", "Rede Tor integrada")):
            _fl = QLabel(f"{_ic}  {_login_tr(lang, _key, _fb)}")
            _fl.setObjectName("sideFeat")
            _fl.setWordWrap(True)
            sl.addWidget(_fl)
            self.hero_feats.append((_fl, _ic, _key, _fb))
        root.addWidget(side)

        # ---- formulário ----
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 24, 28, 22)
        bl.setSpacing(10)
        self.lbl_formtitle = QLabel(_login_tr(lang, "user_welcome", "Bem-vindo de volta"))
        self.lbl_formtitle.setObjectName("formTitle")
        bl.addWidget(self.lbl_formtitle)

        # cabeçalho da seção + contador + idioma
        secrow = QHBoxLayout()
        secrow.setSpacing(8)
        self.sect = QLabel(t(lang, "user_pick"))
        self.sect.setObjectName("sect")
        self.lbl_count = QLabel("0")
        self.lbl_count.setObjectName("count")
        secrow.addWidget(self.sect)
        secrow.addWidget(self.lbl_count)
        secrow.addStretch(1)
        globe = QLabel("🌐")
        globe.setObjectName("fld")
        secrow.addWidget(globe)
        self.combo_lang = QComboBox()
        self.combo_lang.setObjectName("langBox")
        for code, label in LANGS:
            self.combo_lang.addItem(label, code)
        try:
            self.combo_lang.setCurrentIndex(
                max(0, [c for c, _ in LANGS].index(lang)))
        except ValueError:
            self.combo_lang.setCurrentIndex(0)
        self.combo_lang.setToolTip("Idioma / Language / Idioma")
        self.combo_lang.setMaxVisibleItems(20)
        self.combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        secrow.addWidget(self.combo_lang)
        bl.addLayout(secrow)

        # lista de perfis
        self.names = QListWidget()
        self.names.setObjectName("users")
        self.names.setMinimumHeight(120)
        self.names.setMaximumHeight(190)
        self.names.setSpacing(2)
        self.names.itemClicked.connect(lambda *_: self._on_select())
        self.names.itemDoubleClicked.connect(lambda *_: self._do_login())
        self.names.currentRowChanged.connect(lambda *_: self._on_select())
        bl.addWidget(self.names)

        # estado vazio
        self.empty_box = QFrame()
        self.empty_box.setObjectName("emptyBox")
        el = QVBoxLayout(self.empty_box)
        el.setContentsMargins(16, 16, 16, 16)
        el.setSpacing(4)
        self.lbl_empty_title = QLabel("👤  " + _login_tr(lang, "user_empty_title", "Nenhum perfil ainda"))
        self.lbl_empty_title.setObjectName("emptitle")
        self.lbl_empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_desc = QLabel(_login_tr(lang, "user_empty_desc",
                                               "Crie seu primeiro perfil — cada um tem um cofre AES-256 separado."))
        self.lbl_empty_desc.setObjectName("empdesc")
        self.lbl_empty_desc.setWordWrap(True)
        self.lbl_empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(self.lbl_empty_title)
        el.addWidget(self.lbl_empty_desc)
        bl.addWidget(self.empty_box)

        # senha
        passhead = QHBoxLayout()
        passhead.setSpacing(8)
        self.lbl_pass = QLabel(t(lang, "user_pass"))
        self.lbl_pass.setObjectName("fld")
        passhead.addWidget(self.lbl_pass)
        passhead.addStretch(1)
        self.lbl_caps = QLabel("⇪ " + _login_tr(lang, "user_caps", "Caps Lock ativo"))
        self.lbl_caps.setObjectName("capswarn")
        self.lbl_caps.setVisible(False)
        passhead.addWidget(self.lbl_caps)
        bl.addLayout(passhead)
        passrow = QHBoxLayout()
        passrow.setSpacing(8)
        self.ed_pass = QLineEdit()
        self.ed_pass.setObjectName("pass")
        self.ed_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_pass.setMinimumHeight(48)
        self.ed_pass.setPlaceholderText("••••••••")
        self.ed_pass.returnPressed.connect(self._do_login)
        self.ed_pass.textChanged.connect(lambda *_: (self._hide_msg(), self._check_caps()))
        self.btn_eye = QPushButton("👁")
        self.btn_eye.setObjectName("ghost")
        self.btn_eye.setCheckable(True)
        self.btn_eye.setToolTip(_login_tr(lang, "user_show", "Mostrar / ocultar senha"))
        self.btn_eye.setFixedSize(48, 48)
        self.btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eye.toggled.connect(self._toggle_eye)
        passrow.addWidget(self.ed_pass, 1)
        passrow.addWidget(self.btn_eye)
        bl.addLayout(passrow)

        # mensagens inline
        self.lbl_msg = QLabel("")
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setVisible(False)
        bl.addWidget(self.lbl_msg)

        # botão principal
        self.btn_login = QPushButton("→  " + t(lang, "user_login"))
        self.btn_login.setObjectName("primary")
        self.btn_login.setMinimumHeight(50)
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.clicked.connect(self._do_login)
        bl.addWidget(self.btn_login)

        # criar / excluir
        row2 = QHBoxLayout()
        row2.setSpacing(10)
        self.btn_create = QPushButton("＋  " + t(lang, "user_create"))
        self.btn_create.setObjectName("ghost")
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.clicked.connect(self._do_create)
        self.btn_delete = QPushButton("🗑  " + t(lang, "user_delete"))
        self.btn_delete.setObjectName("dangerGhost")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.clicked.connect(self._do_delete)
        row2.addWidget(self.btn_create)
        row2.addWidget(self.btn_delete)
        bl.addLayout(row2)

        # divisor
        divrow = QHBoxLayout()
        divrow.setSpacing(10)
        l1 = QLabel("────────")
        l1.setObjectName("div")
        self.div_mid = QLabel(_login_tr(lang, "user_or", "ou"))
        self.div_mid.setObjectName("div")
        l2 = QLabel("────────")
        l2.setObjectName("div")
        divrow.addStretch(1)
        divrow.addWidget(l1)
        divrow.addWidget(self.div_mid)
        divrow.addWidget(l2)
        divrow.addStretch(1)
        bl.addLayout(divrow)

        # convidado
        self.btn_guest = QPushButton(t(lang, "user_guest") + "  →")
        self.btn_guest.setObjectName("guestBtn")
        self.btn_guest.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_guest.setToolTip(_login_tr(
            lang, "user_guest_hint", "Entrar sem perfil — sem senha, config salva neste PC"))
        self.btn_guest.clicked.connect(self._do_guest)
        bl.addWidget(self.btn_guest)

        self.foot = QLabel("🔐 " + _login_tr(
            lang, "user_footer",
            "Perfis locais • cofre AES-256 • nada sai deste PC"))
        self.foot.setObjectName("foot")
        self.foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.foot.setWordWrap(True)
        bl.addWidget(self.foot)

        bl.addStretch(1)
        root.addWidget(body, 1)
        self.refresh_names()
        _dark_titlebar(self)

    def _on_lang_changed(self, idx: int) -> None:
        code = self.combo_lang.itemData(idx)
        if not code or code == self._lang:
            return
        self._lang = code
        try:
            import json as _j
            import os as _os
            from .config import app_dirs as _ad
            _cfg, _ = _ad()
            _p = _os.path.join(_cfg, "config.json")
            _raw: dict = {}
            try:
                with open(_p, encoding="utf-8") as _f:
                    _raw = _j.load(_f)
            except (OSError, ValueError):
                _raw = {}
            _raw["lang"] = code
            with open(_p, "w", encoding="utf-8") as _f:
                _j.dump(_raw, _f, ensure_ascii=False, indent=2)
        except OSError:
            pass
        self._retranslate()

    def _retranslate(self) -> None:
        lang = self._lang
        self.setWindowTitle(t(lang, "user_title"))
        if hasattr(self, "hero_sub"):
            self.hero_sub.setText(_login_tr(lang, "motto", "Privacidade • Liberdade • Anonimato"))
        for _fl, _ic, _key, _fb in getattr(self, "hero_feats", []):
            try:
                _fl.setText(f"{_ic}  {_login_tr(lang, _key, _fb)}")
            except (RuntimeError, AttributeError):
                pass
        self.lbl_formtitle.setText(_login_tr(lang, "user_welcome", "Bem-vindo de volta"))
        self.lbl_caps.setText("⇪ " + _login_tr(lang, "user_caps", "Caps Lock ativo"))
        self.sect.setText(t(lang, "user_pick"))
        self.lbl_empty_title.setText("👤  " + _login_tr(lang, "user_empty_title", "Nenhum perfil ainda"))
        self.lbl_empty_desc.setText(_login_tr(lang, "user_empty_desc",
                                              "Crie seu primeiro perfil — cada um tem um cofre AES-256 separado."))
        self.lbl_pass.setText(t(lang, "user_pass"))
        self.btn_eye.setToolTip(_login_tr(lang, "user_show", "Mostrar / ocultar senha"))
        self.btn_create.setText("＋  " + t(lang, "user_create"))
        self.btn_delete.setText("🗑  " + t(lang, "user_delete"))
        self.div_mid.setText(_login_tr(lang, "user_or", "ou"))
        self.btn_guest.setText(t(lang, "user_guest") + "  →")
        self.btn_guest.setToolTip(_login_tr(
            lang, "user_guest_hint", "Entrar sem perfil — sem senha, config salva neste PC"))
        self.foot.setText("🔐 " + _login_tr(
            lang, "user_footer",
            "Perfis locais • cofre AES-256 • nada sai deste PC"))
        cur = self._selected()
        self.refresh_names(select_id=cur["id"] if cur else "")

    # ---------- lista ----------
    def refresh_names(self, select_id: str = "") -> None:
        from PyQt6.QtWidgets import QListWidgetItem
        from PyQt6.QtCore import QSize
        from . import users as _users
        self._users = _users.list_users()
        self.names.clear()
        for u in self._users:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 54))
            self.names.addItem(item)
            row = QWidget()
            hl = QHBoxLayout(row)
            hl.setContentsMargins(8, 4, 8, 4)
            hl.setSpacing(10)
            av = QLabel(u["name"][:1].upper() or "?")
            av.setObjectName("avatar")
            av.setFixedSize(36, 36)
            av.setAlignment(Qt.AlignmentFlag.AlignCenter)
            av.setStyleSheet(
                f"QLabel#avatar {{ background: {_avatar_color(u['name'])}; }}")
            txt = QVBoxLayout()
            txt.setSpacing(0)
            nm = QLabel(u["name"])
            nm.setObjectName("uname")
            sb = QLabel(_login_tr(self._lang, "user_vault_tag", "cofre local • AES-256"))
            sb.setObjectName("usub")
            txt.addWidget(nm)
            txt.addWidget(sb)
            go = QLabel("›")
            go.setObjectName("go")
            hl.addWidget(av)
            hl.addLayout(txt, 1)
            hl.addWidget(go)
            self.names.setItemWidget(item, row)
        n = len(self._users)
        _pkey = "user_profile_one" if n == 1 else "user_profile_many"
        self.lbl_count.setText(f"{n} " + t(self._lang, _pkey))
        self.names.setVisible(n > 0)
        self.empty_box.setVisible(n == 0)
        self.ed_pass.setEnabled(n > 0)
        self.btn_login.setEnabled(n > 0)
        self.btn_delete.setEnabled(n > 0)
        if n:
            pick = 0
            if select_id:
                for i, u in enumerate(self._users):
                    if u["id"] == select_id:
                        pick = i
                        break
            self.names.setCurrentRow(pick)
        self._update_login_text()

    def _on_select(self) -> None:
        self._hide_msg()
        self._update_login_text()
        try:
            self.ed_pass.setFocus()
        except RuntimeError:
            pass

    def _update_login_text(self) -> None:
        u = self._selected()
        base = t(self._lang, "user_login")
        self.btn_login.setText(f"→  {base}" + (f"  •  {u['name']}" if u else ""))

    def _selected(self):
        row = self.names.currentRow()
        if 0 <= row < len(self._users):
            return self._users[row]
        return None

    # ---------- mensagens ----------
    def _hide_msg(self) -> None:
        self.lbl_msg.setVisible(False)

    def _show_msg(self, text: str, ok: bool = False) -> None:
        self.lbl_msg.setText(text)
        self.lbl_msg.setObjectName("okmsg" if ok else "error")
        self.lbl_msg.setStyleSheet("")  # força reaplicar o QSS pelo objectName
        self.lbl_msg.setVisible(True)

    def _toggle_eye(self, on: bool) -> None:
        self.ed_pass.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)
        self.btn_eye.setText("🙈" if on else "👁")

    def _check_caps(self) -> None:
        on = False
        try:
            import ctypes as _ct
            on = bool(_ct.windll.user32.GetKeyState(0x14) & 1)
        except Exception:
            pass
        try:
            self.lbl_caps.setVisible(on)
        except (RuntimeError, AttributeError):
            pass

    # ---------- ações ----------
    def _do_login(self) -> None:
        from . import users as _users
        u = self._selected()
        if not u:
            self._show_msg(t(self._lang, "user_need_select"))
            return
        if _users.verify_user(u["id"], self.ed_pass.text()):
            _users.reset_fails(u["id"])
            self.result_kind, self.result_id, self.result_pw = "user", u["id"], self.ed_pass.text()
            self.accept()
        else:
            wiped, left = _users.register_fail(u["id"])
            if wiped:
                # Legado: register_fail não apaga mais (só bloqueia);
                # ramo mantido por compatibilidade.
                self.ed_pass.clear()
                self.refresh_names()
                self._show_msg(t(self._lang, "user_wiped").replace("{n}", u["name"]))
            elif left <= 0 or _users.is_locked(u["id"]) > 0:
                self.ed_pass.clear()
                self._show_msg(t(self._lang, "user_locked").replace("{n}", u["name"]))
            else:
                self._show_msg(t(self._lang, "user_attempts").replace("{n}", str(left)))
                self.ed_pass.selectAll()
                self.ed_pass.setFocus()

    def _do_guest(self) -> None:
        self.result_kind = "guest"
        self.accept()

    def _do_create(self) -> None:
        from . import users as _users
        d = CreateDialog(self, self._lang)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        name, a, b = d.values()
        if not name.strip():
            self._show_msg("✗ " + t(self._lang, "user_empty"))
            return
        if len(a) < 8:
            self._show_msg("✗ " + t(self._lang, "vault_short"))
            return
        if a != b:
            self._show_msg("✗ " + t(self._lang, "vault_mismatch"))
            return
        try:
            uid = _users.create_user(name.strip(), a)
        except ValueError as e:
            key = {"exists": "user_exists", "short": "vault_short",
                   "empty": "user_empty"}.get(str(e), "user_exists")
            self._show_msg("✗ " + t(self._lang, key))
            return
        self.refresh_names(select_id=uid)
        self.ed_pass.clear()
        self.ed_pass.setFocus()
        self._show_msg("✓ " + t(self._lang, "user_created"), ok=True)

    def _do_delete(self) -> None:
        from . import users as _users
        u = self._selected()
        if not u:
            self._show_msg("✗ " + t(self._lang, "user_need_select"))
            return
        ask = t(self._lang, "user_confirm_del")
        if ask == "user_confirm_del":
            ask = "Excluir '{n}' e seu cofre?"
        ask = ask.replace("{n}", u["name"])
        r = QMessageBox.question(
            self, "Anonymous Shield", ask,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        if _users.delete_user(u["id"], self.ed_pass.text()):
            self.ed_pass.clear()
            self.refresh_names()
            self._show_msg("✓ " + t(self._lang, "user_deleted"), ok=True)
        else:
            self._show_msg("✗ " + t(self._lang, "user_wrong"))


class CreateDialog(QDialog):
    """Criar usuário local (moderno): nome + senha + confirmação."""

    def __init__(self, parent, lang: str):
        super().__init__(parent)
        self._lang = lang
        self.setWindowTitle(t(lang, "user_create_title"))
        self.setObjectName("login")
        self.setMinimumWidth(380)
        self.setStyleSheet(LOGIN_QSS)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(10)

        title = QLabel(t(lang, "user_create_title"))
        title.setObjectName("emptitle")
        title.setStyleSheet("font-size: 17px;")
        lay.addWidget(title)
        hint = QLabel(_login_tr(
            lang, "user_create_hint",
            "Um perfil = um cofre criptografado separado neste PC."))
        hint.setObjectName("empdesc")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.ed_name = QLineEdit()
        self.ed_name.setObjectName("field")
        self.ed_name.setPlaceholderText("Ex.: julio")
        self.ed_a = QLineEdit()
        self.ed_a.setObjectName("field")
        self.ed_b = QLineEdit()
        self.ed_b.setObjectName("field")
        for w in (self.ed_a, self.ed_b):
            w.setEchoMode(QLineEdit.EchoMode.Password)
        self.ed_a.setPlaceholderText("••••••••")
        self.ed_b.setPlaceholderText("••••••••")

        ln = QLabel(t(lang, "user_name"))
        ln.setObjectName("fld")
        lay.addWidget(ln)
        lay.addWidget(self.ed_name)
        la = QLabel(t(lang, "vault_new"))
        la.setObjectName("fld")
        lay.addWidget(la)
        lay.addWidget(self.ed_a)
        lb = QLabel(t(lang, "vault_confirm"))
        lb.setObjectName("fld")
        lay.addWidget(lb)
        lay.addWidget(self.ed_b)

        self.lbl_warn = QLabel("")
        self.lbl_warn.setObjectName("error")
        self.lbl_warn.setWordWrap(True)
        self.lbl_warn.setVisible(False)
        lay.addWidget(self.lbl_warn)
        for w in (self.ed_a, self.ed_b):
            w.textChanged.connect(self._live_check)

        row = QHBoxLayout()
        row.setSpacing(10)
        btn_cancel = QPushButton(t(lang, "cancel") if t(lang, "cancel") != "cancel" else "Cancelar")
        btn_cancel.setObjectName("ghost")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("＋  " + t(lang, "user_create"))
        btn_ok.setObjectName("primary")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._on_ok)
        row.addWidget(btn_cancel)
        row.addWidget(btn_ok, 1)
        lay.addLayout(row)
        self.ed_name.setFocus()
        _dark_titlebar(self)

    def _live_check(self) -> None:
        a, b = self.ed_a.text(), self.ed_b.text()
        if b and a != b:
            self.lbl_warn.setText("✗ " + t(self._lang, "vault_mismatch"))
            self.lbl_warn.setVisible(True)
        elif a and len(a) < 8:
            self.lbl_warn.setText("✗ " + t(self._lang, "vault_short"))
            self.lbl_warn.setVisible(True)
        else:
            self.lbl_warn.setVisible(False)

    def _on_ok(self) -> None:
        if not self.ed_name.text().strip():
            self.lbl_warn.setText("✗ " + t(self._lang, "user_empty"))
            self.lbl_warn.setVisible(True)
            return
        if len(self.ed_a.text()) < 8:
            self.lbl_warn.setText("✗ " + t(self._lang, "vault_short"))
            self.lbl_warn.setVisible(True)
            return
        if self.ed_a.text() != self.ed_b.text():
            self.lbl_warn.setText("✗ " + t(self._lang, "vault_mismatch"))
            self.lbl_warn.setVisible(True)
            return
        self.accept()

    def values(self) -> tuple[str, str, str]:
        return self.ed_name.text(), self.ed_a.text(), self.ed_b.text()
