# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — cliente Tor (Orbot-like) em Python + Qt + tor oficial."""
import os
import sys

from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox

from anonshield.config import AppConfig, app_dirs, set_data_dir
from anonshield.gui import LoginDialog, MainWindow
from anonshield.uilogic import UiLogic
from anonshield import users as users_mod
from anonshield import vault as vault_mod


class App(MainWindow, UiLogic):
    pass


def detect_lang() -> str:
    from anonshield.config import detect_lang as _d
    return _d()


def _dialog_lang() -> str:
    lang = detect_lang()
    try:
        if not vault_mod.has_vault(app_dirs()[0]):
            import json as _j
            with open(os.path.join(app_dirs()[0], "config.json"), encoding="utf-8") as f:
                lang = _j.load(f).get("lang", lang)
    except (OSError, ValueError):
        pass
    return lang


def _app_icon() -> "QIcon | None":
    """Ícone caveira-cebola (funciona no fonte e no exe congelado)."""
    try:
        from PyQt6.QtGui import QIcon
        if getattr(sys, "frozen", False):
            here = sys._MEIPASS  # type: ignore[attr-defined]
        else:
            here = os.path.dirname(os.path.abspath(__file__))
        for name in ("icon.ico", "icon.png"):
            icon = os.path.join(here, "assets", name)
            if os.path.exists(icon):
                return QIcon(icon)
    except Exception:
        pass
    return None


def _forensics() -> None:
    """Grava crash/thread-dump em crash.log + error.log na pasta de dados."""
    try:
        import faulthandler as _fh
        import traceback as _tb
        from anonshield.config import app_dirs as _ad
        _, _data = _ad()
        _fh_file = open(os.path.join(_data, "crash.log"), "w")
        _forensics_state["fh"] = _fh_file
        _fh.enable(file=_fh_file)
        try:
            _home = os.path.expanduser("~")
        except Exception:
            _home = ""
        _user = os.environ.get("USERNAME", "") or os.environ.get("USER", "")

        def _scrub(s: str) -> str:
            try:
                if _home and len(_home) > 3:
                    s = s.replace(_home, "~")
                if _user and len(_user) > 2:
                    import re as _re
                    s = _re.sub(r"(?i)(users|home)[/\\]" + _re.escape(_user), r"\1/~", s)
            except Exception:
                pass
            return s

        def _hook(t, v, tb) -> None:
            try:
                with open(os.path.join(_data, "error.log"), "a", encoding="utf-8") as f:
                    f.write(_scrub("".join(_tb.format_exception(t, v, tb))) + "\n")
            except Exception:
                pass
        sys.excepthook = _hook
    except Exception:
        pass


_forensics_state: dict = {}


def _disable_disk_forensics() -> None:
    """Modo never_store_logs: forense só em memória, nada em disco."""
    try:
        import faulthandler as _fh
        try:
            _fh.disable()
        except Exception:
            pass
        try:
            fh = _forensics_state.get("fh")
            if fh is not None:
                fh.close()
        except Exception:
            pass
        _mem: list = []
        _forensics_state["mem"] = _mem

        def _hook(t, v, tb) -> None:
            try:
                import traceback as _tb
                _mem.append("".join(_tb.format_exception(t, v, tb))[-4000:])
                del _mem[:-20]
            except Exception:
                pass
        sys.excepthook = _hook
    except Exception:
        pass


def main() -> int:
    _forensics()
    app = QApplication(sys.argv)
    app.setApplicationName("Anonymous Shield")
    app.setOrganizationName("anonshield")
    _icon = _app_icon()
    if _icon is not None and not _icon.isNull():
        app.setWindowIcon(_icon)

    # Tela inicial: usuário local (opcional) ou sem usuário.
    login = LoginDialog(None, _dialog_lang())
    if _icon is not None and not _icon.isNull():
        login.setWindowIcon(_icon)
    if login.exec() != QDialog.DialogCode.Accepted or not login.result_kind:
        return 0

    if login.result_kind == "user":
        from anonshield.config import set_data_dir as _set
        _set(users_mod.user_dir(login.result_id))
        cfg = AppConfig.load(login.result_pw)
        cfg.current_uid = login.result_id
        if getattr(login, "_lang", "") and login._lang != cfg.lang:
            cfg.lang = login._lang
            cfg.save()
    else:
        # Convidado: entrada direta, sem senha (config em texto neste PC).
        cfg = AppConfig.load_plain()

    if cfg.never_store_logs:
        _disable_disk_forensics()

    w = App(cfg)
    if _icon is not None and not _icon.isNull():
        w.setWindowIcon(_icon)
    if w.another:
        QMessageBox.warning(w, "Anonymous Shield", w.tr("banner_another"))
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
