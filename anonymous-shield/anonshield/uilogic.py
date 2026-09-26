# Copyright (C) 2026 Abaddon2010
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# Licenca dupla: Apache-2.0 OU GPL-3.0-ou-posterior, a sua escolha. Ver LICENSE-APACHE e LICENSE na raiz.

"""Anonymous Shield — lógica da janela (mixin de MainWindow)."""
from __future__ import annotations

import os
import threading
import time

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import __version__
from . import sysprotect
from .config import AppEntry, SysProxy
from .torctl import TorThread, TorWorker


def tor_reachable_host(host: str) -> bool:
    """Tor só alcança IPs/hosts globais: loopback, rede local e nomes
    locais são rejeitados pelos exits (vira enxurrada de 'malformed
    hostname' no tor.log)."""
    h = (host or "").strip().strip("[]").lower().split("/")[0]
    if h in ("localhost",):
        return False
    try:
        import ipaddress as _ip
        return _ip.ip_address(h).is_global
    except ValueError:
        pass
    if h.endswith((".local", ".localhost", ".lan", ".home", ".internal")):
        return False
    return True


from .sysprotect import bridge_lines_from, bridge_valid


def probe_host(host: str, port: int, via_tor: bool, socks_port: int) -> tuple[int, bool, str]:
    """Probe único (usado no ping sweep). Retorna (porta, aberta, banner)."""
    import socket as _s
    if via_tor and not tor_reachable_host(host):
        return port, False, ""
    try:
        if via_tor:
            import socks as _socks
            s = _socks.socksocket()
            s.set_proxy(_socks.SOCKS5, "127.0.0.1", socks_port, True)
        else:
            s = _s.socket(_s.AF_INET, _s.SOCK_STREAM)
        s.settimeout(2.5)
        s.connect((host, port))
        try:
            s.settimeout(2.0)
            banner = s.recv(256).decode("utf-8", "replace").strip().split("\n")[0][:80]
        except OSError:
            banner = ""
        s.close()
        return port, True, banner
    except OSError:
        return port, False, ""


class UiLogic:
    # ---------- navegação/textos/tema ----------
    def _goto(self, pid: str) -> None:
        if pid not in getattr(self, "_page_idx", {}):
            return
        self._current_page = pid
        self.stack.setCurrentIndex(self._page_idx[pid])
        for k, b in self.side_btns.items():
            b.setChecked(k == pid)
        if pid == "vpn":
            try:
                self._vpn_refresh()
            except (RuntimeError, AttributeError):
                pass
        self.refresh_texts()

    def _lang_changed(self, idx: int) -> None:
        code = self.combo_lang.itemData(idx)
        if code and code != self.cfg.lang:
            self.cfg.lang = code
            self.cfg.save()
            from .i18n import lang_label as _ll
            self._push_log(f"→ {_ll(code)}")
            if self._worker:
                self._worker.lang = code
            self.refresh_texts()

    def _toggle_theme(self) -> None:
        self.cfg.theme = "light" if self.cfg.theme != "light" else "dark"
        self.cfg.save()
        self.apply_theme()
        self.refresh_texts()
        self._push_log(self.tr("log_theme", t=self.tr("theme_light" if self.cfg.theme == "light" else "theme_dark")))

    def apply_theme(self) -> None:
        from .gui import DARK_QSS, LIGHT_QSS
        self.setStyleSheet(LIGHT_QSS if self.cfg.theme == "light" else DARK_QSS)

    def refresh_texts(self) -> None:
        T = self.tr
        collapsed = self.sidebar.isHidden()
        icons = {"dashboard": "▦", "home": "🌐", "total": "🛡", "apps": "🗂",
                 "bridges": "⬡", "proxy": "⇄", "dns": "🛡", "vpn": "🔒",
                 "scan": "◉", "logs": "🖥", "diag": "⟡", "update": "⟳", "about": "ⓘ"}
        names = {"dashboard": "dash_nav", "home": "tab_local", "total": "tab_total",
                 "apps": "tab_apps", "bridges": "tab_bridges", "proxy": "tab_upstream",
                 "dns": "tab_dns", "vpn": "tab_vpn", "scan": "tab_scan",
                 "logs": "tab_logs", "diag": "tab_diag", "update": "tab_update",
                 "about": "tab_about"}
        for pid, btn in self.side_btns.items():
            key = names.get(pid, pid)
            nm = T(key)
            if pid == "home":
                nm = "Tor"
            ico = icons.get(pid, "•")
            # i18n já pode trazer o emoji (ex. "🛡 Total"): não duplicar.
            txt = nm if nm.startswith(ico) else f"{ico}  {nm}"
            btn.setText(ico if collapsed else txt)
            tip = T(f"tip_{pid}")
            if tip != f"tip_{pid}":
                btn.setToolTip(tip)
        # títulos das seções da sidebar
        secs = {"sec_main": "sec_main", "sec_net": "sec_net", "sec_tools": "sec_tools"}
        for raw, key in secs.items():
            lbl = getattr(self, "nav_section_labels", {}).get(raw)
            if lbl is not None:
                lbl.setText(T(key).upper() if T(key) != key else raw.replace("sec_", "").upper())
        self.btn_theme.setText(
            ("☀" if collapsed else f"☀  {T('theme_light')}") if self.cfg.theme != "light"
            else ("🌙" if collapsed else f"🌙  {T('theme_dark')}"))
        self.btn_quit.setText("⏻" if collapsed else T("menu_quit"))
        try:
            self.btn_nav_edit.setChecked(self._nav_edit)
            self.btn_nav_edit.setText("✎" if collapsed else f"✎  {T('nav_organize')}")
            self.btn_nav_reset.setToolTip(T("nav_reset"))
        except (RuntimeError, AttributeError):
            pass
        self._refresh_status()
        for meth in ("_rt_top", "_rt_dashboard", "_rt_home", "_rt_bridges", "_rt_proxy", "_rt_dns",
                     "_rt_vpn", "_rt_scan", "_rt_total", "_rt_apps", "_rt_logs", "_rt_diag", "_rt_update",
                     "_rt_about"):
            fn = getattr(self, meth, None)
            if fn:
                try:
                    fn()
                except (RuntimeError, AttributeError):
                    pass

    def _rt_top(self) -> None:
        T = self.tr
        titles = {
            "dashboard": ("dash_title", "dash_sub"),
            "home": ("tab_local", "hero_off"),
            "total": ("total_title", "total_desc"),
            "apps": ("apps_title", "apps_sub"),
            "bridges": ("br_title", "br_tags"),
            "proxy": ("local_title", "local_desc"),
            "dns": ("dns_title", "dns_desc"),
            "vpn": ("vpn_title", "vpn_sub"),
            "scan": ("scan_title", "scan_warn"),
            "logs": ("logs_title", "logs_info"),
            "diag": ("diag_title", "diag_net_desc"),
            "update": ("upd_title", "upd_repo"),
            "about": ("about_title", "about_sub"),
        }
        cur = getattr(self, "_current_page", "dashboard")
        tk, sk = titles.get(cur, ("dash_title", "dash_sub"))
        try:
            self.lbl_title.setText("Anonymous Shield")
            page, desc = T(tk), T(sk)
            self.lbl_sub.setText(f"{page}  •  {desc}" if page != "Anonymous Shield" else desc)
        except (RuntimeError, AttributeError):
            pass

    def _rt_dashboard(self) -> None:
        T = self.tr
        if not hasattr(self, "lbl_dash_title"):
            return
        self.lbl_dash_kicker.setText(T("dash_kicker").upper())
        self.lbl_dash_title.setText(T("dash_title"))
        sub = T("hero_on") if self.connected else (T("hero_ing") if self.connecting else T("hero_off"))
        self.lbl_dash_sub.setText(sub)
        self.lbl_dash_route.setText(f"{T('route')}: {self.describe_route()}")
        # botão principal espelha o power da home
        if self.connected or self.connecting:
            self.dash_power.setText(T("power_off"))
            self.dash_power.setStyleSheet(
                "background: #b91c1c; color: white; font-weight: 800; border-radius: 11px; border: 1px solid #ef4444;")
        else:
            self.dash_power.setText(T("power_on"))
            self.dash_power.setStyleSheet("")
        self.dash_cancel.setVisible(bool(self.connecting and not self.connected))
        self.dash_check.setToolTip(T("check_tip"))
        self.dash_check.setEnabled(bool(self.connected and not getattr(self, "_checking", False)))
        self.dash_identity.setToolTip(T("new_identity"))
        self.dash_identity.setEnabled(bool(self.connected))
        self.kpi_card_tor.setToolTip("Tor  ›")
        self.kpi_card_socks.setToolTip(T("local_title"))
        self.kpi_card_prot.setToolTip(T("total_enable"))
        self.kpi_card_dns.setToolTip(T("dns_title"))
        # KPIs
        self.kpi_tor_t.setText(T("kpi_tor"))
        self.kpi_socks_t.setText(T("kpi_socks"))
        self.kpi_prot_t.setText(T("kpi_protect"))
        self.kpi_dns_t.setText(T("kpi_dns"))
        if self.connected:
            self.kpi_tor_v.setText(T("st_connected"))
            self.kpi_tor_s.setText(self.exit_ip or T("checking_ip"))
        elif self.connecting:
            self.kpi_tor_v.setText(f"{int(self.progress * 100)}%")
            self.kpi_tor_s.setText(T("st_connecting"))
        else:
            self.kpi_tor_v.setText(T("st_off"))
            self.kpi_tor_s.setText(T("off_tap"))
        self.kpi_socks_v.setText(T("on") if self.socks_running else T("off"))
        self.kpi_socks_s.setText(f"127.0.0.1:{self.cfg.socks_port}")
        prot = T("prot_full") if self.cfg.protect_total else (T("prot_kill") if self.cfg.kill_switch else T("prot_off"))
        self.kpi_prot_v.setText(prot)
        self.kpi_prot_s.setText(T("total_enable"))
        self.kpi_dns_v.setText(T("on") if self.dns_running else T("off"))
        self.kpi_dns_s.setText(self.dash_dns_sub() if hasattr(self, "dash_dns_sub") else self.cfg.dnscrypt_mode)
        self.lbl_bw_title.setText(T("bw_title"))
        self.lbl_circuit_title.setText(T("circuit_title"))
        self.btn_circuit_new.setText(T("circuit_new"))
        self.lbl_dns_now_t.setText(T("dns_now"))
        self.lbl_dns_now.setText(self._current_dns())
        self._render_circuit()
        # ações rápidas
        self.lbl_quick_title.setText(T("dash_quick"))
        quick_names = {"home": "Tor", "bridges": "tab_bridges", "proxy": "tab_upstream",
                       "dns": "tab_dns", "scan": "tab_scan", "logs": "tab_logs"}
        for pid in ("home", "bridges", "proxy", "dns", "scan", "logs"):
            b = getattr(self, f"dash_quick_{pid}", None)
            if b is not None:
                key = quick_names[pid]
                nm = "Tor" if pid == "home" else T(key)
                b.setText(f"{nm}  ›")
        # atividade
        self.lbl_act_title.setText(T("dash_activity"))
        if self.exit_ip:
            self.dash_exit.setText(f"🌐 {self.exit_ip}  •  {self.exit_country}")
        else:
            self.dash_exit.setText(T("dash_no_ip"))
        tail = (self.log_lines[-3:] if getattr(self, "log_lines", None) else [])
        self.dash_logs.setText("\n".join(tail) if tail else T("logs_empty"))
        self.dash_view_logs.setText(f"{T('logs_title')}  →")

    def dash_dns_sub(self) -> str:
        return {"tor": self.tr("dns_tor"), "local": self.tr("dns_local"),
                "combined": self.tr("dns_combined")}.get(self.cfg.dnscrypt_mode, self.cfg.dnscrypt_mode)

    def _rt_home(self) -> None:
        T = self.tr
        sub = T("hero_on") if self.connected else (T("hero_ing") if self.connecting else T("hero_off"))
        self.lbl_hero_sub.setText(sub)
        route = f"{T('route')}: {self.describe_route()}"
        self.lbl_hero_route.setText(route)
        self.lbl_banner.setVisible(self.another)
        if self.another:
            self.lbl_banner.setText(T("banner_another"))
        self.btn_onion.setToolTip(T("onion_tip"))
        self._power_text()
        self.btn_gobridges.setText(T("go_bridges"))
        self.btn_retry.setText(T("retry"))
        # Palavra gigante + linhas estilo Orbot
        big = T("st_connected") if self.connected else (f"{int(self.progress*100)}%" if self.connecting else T("st_off"))
        col = "#10b981" if self.connected else ("#f59e0b" if self.connecting else ("#64748b" if self.cfg.theme == "light" else "#78788a"))
        self.lbl_bigstatus.setText(big)
        self.lbl_bigstatus.setStyleSheet(f"font-size: 30px; font-weight: bold; color: {col};")
        self.row_identity.setText(f"{T('new_identity')}  ›")
        self.row_check.setText(f"◎  {T('check_ip')}  ›")
        self.row_total.setText(f"{T('row_total')}  ›")
        self.row_copyip.setText(f"⎙  {T('copy_ip')}  ›")
        self.row_browser.setText(f"{T('row_browser')}  ›")
        self.row_identity.setEnabled(self.connected)
        self.row_check.setEnabled(self.connected)
        self.lbl_exit_title.setText(T("exit_title"))
        self.btn_cancel.setText(T("cancel"))
        self.lbl_exit_avoid.setText(T("exit_avoid"))
        _modes = {"all": "exit_all", "five": "exit_5",
                  "nine": "exit_9", "fourteen": "exit_14"}
        for _m, _b in self.exit_btns.items():
            _b.setText(T(_modes[_m]))
            _b.setChecked(self.cfg.exit_mode == _m)
        self.lbl_exit_note.setText(T("exit_note"))
        self.lbl_mode_title.setText(T("mode_title"))
        _cur = self._detect_preset()
        _names = {"rapido": "mode_fast", "anonimo": "mode_anon",
                  "censura": "mode_censor", "furtivo": "mode_stealth",
                  "custom": "mode_custom"}
        for _m, _b in self.mode_btns.items():
            _b.setText(T(_names[_m]))
            _b.setChecked(_m == _cur)
        self.lbl_mode_cur.setText(f"{T('mode_cur')}: {T(_names[_cur])}")
        _desc = {"rapido": "mode_desc_fast", "anonimo": "mode_desc_anon",
                 "censura": "mode_desc_censor", "furtivo": "mode_desc_stealth",
                 "custom": "mode_desc_custom"}[_cur]
        self.lbl_mode_desc.setText(T(_desc))
        self.lbl_rotate_title.setText(T("rotate_title"))
        self.lbl_rotate_every.setText(T("rotate_every"))
        cur_u = self.combo_rotate_unit.currentIndex()
        self.combo_rotate_unit.blockSignals(True)
        self.combo_rotate_unit.clear()
        self.combo_rotate_unit.addItem(T("rotate_sec"))
        self.combo_rotate_unit.addItem(T("rotate_min"))
        self.combo_rotate_unit.setCurrentIndex(cur_u if cur_u in (0, 1) else 0)
        self.combo_rotate_unit.blockSignals(False)
        secs = max(60, int(self.cfg.rotate_secs or 600))
        if secs >= 120 and secs % 60 == 0:
            unit, val = 1, secs // 60
        else:
            unit, val = 0, min(secs, 1440)
        self.combo_rotate_unit.blockSignals(True)
        self.combo_rotate_unit.setCurrentIndex(unit)
        self.combo_rotate_unit.blockSignals(False)
        self.spin_rotate.blockSignals(True)
        self.spin_rotate.setValue(max(1, min(1440, val)))
        self.spin_rotate.blockSignals(False)
        self.lbl_rotate_count.setText(self._rotate_count_text())
        self.chk_rotate.blockSignals(True)
        self.chk_rotate.setChecked(bool(self.cfg.auto_rotate))
        self.chk_rotate.blockSignals(False)
        self.lbl_sched_title.setText(T("sched_title"))
        self.lbl_sched_on.setText(T("sched_on_lbl"))
        self.lbl_sched_off.setText(T("sched_off_lbl"))
        self.lbl_sched_rot.setText(T("sched_rot_lbl"))
        for _ed, _v in ((self.edit_sched_on, self.cfg.sched_on),
                        (self.edit_sched_off, self.cfg.sched_off),
                        (self.edit_sched_rot, self.cfg.sched_rotate)):
            try:
                if _ed.text() != (_v or ""):
                    _ed.setText(_v or "")
            except (RuntimeError, AttributeError):
                pass
        self.lbl_sched_next.setText(self._sched_next_text())
        self.chk_sched.blockSignals(True)
        self.chk_sched.setChecked(bool(self.cfg.sched_enabled))
        self.chk_sched.blockSignals(False)

    def _rotate_toggled(self, v: bool) -> None:
        self.cfg.auto_rotate = bool(v)
        self.cfg.save()
        self._rotate_last = time.time()
        self._push_log(self.tr("rotate_on" if v else "rotate_off"))
        self.refresh_texts()

    def _rotate_changed(self) -> None:
        try:
            val = max(1, int(self.spin_rotate.value()))
            mult = 60 if self.combo_rotate_unit.currentIndex() == 1 else 1
            self.cfg.rotate_secs = max(60, min(86400, val * mult))
            self.cfg.save()
            self._rotate_last = time.time()
        except (RuntimeError, AttributeError, ValueError):
            pass
        self.refresh_texts()

    def _rotate_count_text(self) -> str:
        if not (self.connected and self.cfg.auto_rotate):
            return ""
        interval = max(60, int(self.cfg.rotate_secs or 600))
        remain = max(0, int(interval - (time.time() - getattr(self, "_rotate_last", 0.0))))
        mm, ss = divmod(remain, 60)
        return self.tr("rotate_in", t=f"{mm:02d}:{ss:02d}")

    def _detect_preset(self) -> str:
        c = self.cfg
        if (c.bridges_enabled and c.never_store_logs
                and c.bridge_preset in ("obfs4", "auto")):
            return "furtivo"
        if (c.bridges_enabled and c.bridge_preset not in ("direto", "auto")):
            return "censura"
        if (c.exit_mode == "fourteen" and c.auto_rotate and c.kill_switch
                and not c.bridges_enabled):
            return "anonimo"
        if (not c.bridges_enabled and c.exit_mode == "all"
                and not c.upstream_enabled and not c.auto_rotate
                and not c.kill_switch):
            return "rapido"
        return "custom"

    def _apply_preset(self, mode: str) -> None:
        c = self.cfg
        if mode == "rapido":
            c.bridges_enabled = False
            c.bridge_preset = "direto"
            c.exit_mode = "all"
            c.upstream_enabled = False
            c.auto_rotate = False
            c.kill_switch = False
        elif mode == "anonimo":
            c.exit_mode = "fourteen"
            c.auto_rotate = True
            if not c.rotate_secs or c.rotate_secs < 60:
                c.rotate_secs = 600
            c.kill_switch = True
            c.socks_enabled = True
        elif mode == "censura":
            best = self._best_transport()
            if best:
                c.bridge_preset = best
                c.bridges_enabled = True
            else:
                c.bridges_enabled = True
                if c.bridge_preset == "direto":
                    c.bridge_preset = "obfs4"
                self._push_log(self.tr("mode_need_bridges"))
        elif mode == "furtivo":
            # VPN + obfs4 + nunca-armazenar-logs contra a provedora.
            c.bridges_enabled = True
            if c.bridge_preset == "direto":
                c.bridge_preset = "obfs4"
            if not (c.bridges or []):
                self._push_log(self.tr("mode_need_bridges"))
            c.never_store_logs = True
            vb = (c.vpn_bin or "").strip()
            vc = (c.vpn_config or "").strip()
            if (vb and vc and os.path.exists(vb) and os.path.exists(vc)
                    and not self.vpn_on):
                try:
                    if hasattr(self, "edit_vpn_bin"):
                        if not self.edit_vpn_bin.text().strip():
                            self.edit_vpn_bin.setText(vb)
                        if not self.edit_vpn_config.text().strip():
                            self.edit_vpn_config.setText(vc)
                    self._vpn_connect()
                except (RuntimeError, AttributeError):
                    self._push_log(self.tr("mode_need_vpn"))
            elif not self.vpn_on:
                self._push_log(self.tr("mode_need_vpn"))
        else:
            return
        c.save()
        _mn = {"rapido": "mode_fast", "anonimo": "mode_anon",
               "censura": "mode_censor", "furtivo": "mode_stealth"}.get(mode, "mode_custom")
        self._push_log(self.tr("mode_applied", m=self.tr(_mn)))
        if self.connected and self._worker and mode in ("rapido", "censura", "furtivo"):
            self.disconnect_tor(silent=True)
            self.connect_tor()
        elif self.connected and self._worker and mode == "anonimo":
            threading.Thread(target=self._worker.apply_exit_mode, daemon=True).start()
        self._rotate_last = time.time()
        self.refresh_texts()

    def _best_transport(self) -> str:
        """Melhor transporte pelas bridges salvas (que realmente funciona)."""
        lines = [str(b).strip().lower() for b in (self.cfg.bridges or []) if str(b).strip()]
        if any(l.startswith("obfs4") for l in lines):
            return "obfs4"
        if any(l.startswith("conjure") for l in lines):
            return "conjure"
        for l in lines:
            if l.startswith("snowflake"):
                return "snowflake"
            if l.startswith("webtunnel"):
                return "webtunnel"
        return ""

    def _sched_toggled(self, v: bool) -> None:
        self.cfg.sched_enabled = bool(v)
        self.cfg.save()
        self._push_log(self.tr("sched_on" if v else "sched_off_log"))
        self.refresh_texts()

    @staticmethod
    def _sched_parse_hm(s: str) -> str:
        import re as _re
        m = _re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", s or "")
        if not m:
            return ""
        h, mi = int(m.group(1)), int(m.group(2))
        return f"{h:02d}:{mi:02d}" if 0 <= h <= 23 and 0 <= mi <= 59 else ""

    def _sched_changed(self) -> None:
        try:
            self.cfg.sched_on = self._sched_parse_hm(self.edit_sched_on.text())
            self.cfg.sched_off = self._sched_parse_hm(self.edit_sched_off.text())
            rots = []
            for tok in (self.edit_sched_rot.text() or "").replace(";", ",").split(","):
                hm = self._sched_parse_hm(tok)
                if hm and hm not in rots:
                    rots.append(hm)
            self.cfg.sched_rotate = ",".join(rots)
            self.cfg.save()
        except (RuntimeError, AttributeError, ValueError):
            pass
        self.refresh_texts()

    def _sched_check(self) -> None:
        if not self.cfg.sched_enabled:
            return
        import datetime as _dt
        now = _dt.datetime.now().strftime("%H:%M")
        today = _dt.date.today().isoformat()
        fired = getattr(self, "_sched_fired", set())
        key = (today, now)
        if getattr(self, "_sched_last", "") == now:
            return
        self._sched_last = now
        if self.cfg.sched_on == now and ("on",) + key not in fired:
            fired.add(("on",) + key)
            if not self.connected and not self.connecting:
                self._push_log(self.tr("sched_fire_on", t=now))
                self.connect_tor()
        if self.cfg.sched_off == now and ("off",) + key not in fired:
            fired.add(("off",) + key)
            if self.connected or self.connecting:
                self._push_log(self.tr("sched_fire_off", t=now))
                self.disconnect_tor()
                try:
                    self.restore_internet()
                except Exception:
                    pass
        rots = [r for r in (self.cfg.sched_rotate or "").split(",") if r]
        if now in rots and ("rot",) + key not in fired:
            fired.add(("rot",) + key)
            if self.connected and self._worker:
                self._push_log(self.tr("sched_fire_rot", t=now))
                self._new_identity()
        self._sched_fired = fired

    def _sched_next_text(self) -> str:
        if not self.cfg.sched_enabled:
            return ""
        import datetime as _dt
        now = _dt.datetime.now().strftime("%H:%M")
        cands = []
        if self.cfg.sched_on:
            cands.append((self.cfg.sched_on, self.tr("power_on")))
        if self.cfg.sched_off:
            cands.append((self.cfg.sched_off, self.tr("power_off")))
        for r in (self.cfg.sched_rotate or "").split(","):
            if r:
                cands.append((r, self.tr("new_identity")))
        future = sorted([c for c in cands if c[0] >= now] or cands)
        if not future:
            return ""
        return self.tr("sched_next", t=future[0][0], a=future[0][1])

    def _exit_mode(self, mode: str) -> None:
        """Escolha do usuário: sai por qualquer país ou fora dos Olhos."""
        self.cfg.exit_mode = mode if mode in ("all", "five", "nine", "fourteen") else "all"
        self.cfg.save()
        if self.connected and self._worker:
            threading.Thread(target=self._worker.apply_exit_mode, daemon=True).start()
        self.refresh_texts()

    def _rt_bridges(self) -> None:
        T = self.tr
        self.lbl_br_title.setText(T("br_title"))
        self.lbl_br_tags.setText(T("br_tags"))
        self.lbl_br_enable.setText(T("br_enable"))
        self.lbl_br_desc.setText(T("br_desc"))
        self.lbl_transport.setText(T("transport"))
        for p, b in self.preset_btns.items():
            b.setText(T("preset_direto") if p == "direto" else p)
            b.setChecked(self.cfg.bridge_preset == p)
        self.lbl_direct_info.setText(T("br_direct_info"))
        self.lbl_direct_info.setVisible(self.cfg.bridge_preset == "direto")
        self.lbl_pt.setText(T("pt_path"))
        self.edit_pt.setPlaceholderText(
            T("pt_hint_win") if os.name == "nt" else T("pt_hint_lin"))
        self.lbl_br_lines.setText(T("br_lines"))
        self.edit_bridges.setPlaceholderText(T("br_hint"))
        self.btn_paste.setText(T("paste"))
        self.btn_apply_br.setText(T("apply_reconnect"))
        self.btn_clear_br.setText(T("clear"))
        self.lbl_br_count.setText(T("br_count", n=len(self.cfg.bridges)))
        self.lbl_br_tip.setText(T("br_tip"))
        self.btn_br_open.setText(T("br_open"))
        self.btn_br_mail.setText(T("br_mail"))
        self.btn_br_tg.setText(T("br_tg"))
        self.lbl_br_captcha.setText(T("br_captcha"))
        self.lbl_br_web.setText(T("br_webtunnel"))
        self.lbl_br_web.setVisible(self.cfg.bridge_preset in ("snowflake", "webtunnel"))
        self.lbl_br_web.setText(T("br_webtunnel"))

    def _rt_proxy(self) -> None:
        T = self.tr
        self.lbl_local_title.setText(T("local_title"))
        self.lbl_proxy_state.setText(T("on") if self.socks_running else T("off"))
        self.lbl_local_enable.setText(T("local_enable"))
        self.lbl_local_desc.setText(T("local_desc"))
        self.lbl_kill.setText(T("kill_title"))
        self.lbl_kill_desc.setText(T("kill_desc"))
        self.lbl_autocon.setText(T("autoconnect"))
        self.lbl_port.setText(T("port"))
        self.btn_socks_start.setText(T("start_proxy"))
        self.btn_socks_stop.setText(T("stop"))
        self.lbl_socks_addr.setText(f"127.0.0.1:{self.cfg.socks_port}")
        self.lbl_proxy_hint.setText(T("proxy_running") if self.socks_running else T("proxy_stopped"))
        self.lbl_up_title.setText(T("up_title"))
        self.lbl_up_enable.setText(T("up_enable"))
        self.lbl_up_desc.setText(T("up_desc"))
        self.lbl_quick.setText(T("quick_type"))
        for key, b in self.up_btns.items():
            nm = T("direct") if key == "direct" else key
            b.setText(nm)
            b.setChecked((key == "direct" and not self.cfg.upstream_enabled)
                         or (key != "direct" and self.cfg.upstream_enabled
                             and self.cfg.upstream_proxy_url.startswith(key.lower() + "://")))
        self.lbl_up_url.setText(T("up_url"))
        self.edit_upstream.setPlaceholderText(T("up_hint"))
        self.lbl_up_formats.setText(T("up_formats"))
        self.btn_up_apply.setText(T("apply_reconnect"))
        self.btn_up_test.setText(T("test_format"))
        self.chk_socks.blockSignals(True)
        self.chk_socks.setChecked(self.cfg.socks_enabled)
        self.chk_socks.blockSignals(False)
        self.chk_kill.blockSignals(True)
        self.chk_kill.setChecked(self.cfg.kill_switch)
        self.chk_kill.blockSignals(False)
        self.chk_autocon.blockSignals(True)
        self.chk_autocon.setChecked(self.cfg.auto_connect)
        self.chk_autocon.blockSignals(False)
        self.chk_upstream.blockSignals(True)
        self.chk_upstream.setChecked(self.cfg.upstream_enabled)
        self.chk_upstream.blockSignals(False)
        if self.spin_port.value() != self.cfg.socks_port:
            self.spin_port.blockSignals(True)
            self.spin_port.setValue(self.cfg.socks_port)
            self.spin_port.blockSignals(False)

    def _rt_dns(self) -> None:
        T = self.tr
        self.lbl_dns_title.setText(T("dns_title"))
        st = T("on") if self.dns_running else (T("dns_armed") if self.cfg.dnscrypt_enabled else T("off"))
        self.lbl_dns_state.setText(st)
        self.lbl_dns_enable.setText(T("dns_enable"))
        self.lbl_dns_desc.setText(T("dns_desc"))
        self.lbl_mode.setText(T("mode"))
        self.btn_dns_tor.setText(T("dns_tor"))
        self.btn_dns_tor.setChecked(self.cfg.dnscrypt_mode == "tor")
        self.btn_dns_local.setText(T("dns_local"))
        self.btn_dns_local.setChecked(self.cfg.dnscrypt_mode == "local")
        self.btn_dns_combo.setText(T("dns_combined"))
        self.btn_dns_combo.setToolTip(T("dns_combined_hint"))
        self.btn_dns_combo.setChecked(self.cfg.dnscrypt_mode == "combined")
        self.lbl_dns_info.setText(T("dns_info"))
        self.dns_local_box.setVisible(self.cfg.dnscrypt_mode in ("local", "combined"))
        self.lbl_dns_bin.setText(T("dns_bin"))
        self.edit_dns_bin.setPlaceholderText(T("dns_bin_hint"))
        self.btn_dns_get.setText(T("dns_get"))
        self.lbl_dns_port.setText(T("dns_port"))
        self.lbl_dns_toml.setText(T("dns_toml"))
        self.edit_dns_toml.setPlaceholderText(T("dns_toml_hint"))
        self.btn_dns_start.setText(T("dns_start"))
        self.btn_dns_stop.setText(T("stop"))
        self.lbl_dns_listen.setText(T("dns_listening", a=self.dns_addr) if self.dns_running else "")
        try:
            self.dns_chip.setVisible(bool(self.lbl_dns_listen.text()))
        except (RuntimeError, AttributeError):
            pass
        self.lbl_dns_test.setText(T("dns_test_title"))
        self.btn_dns_test.setText(T("test"))
        self.chk_dns.blockSignals(True)
        self.chk_dns.setChecked(self.cfg.dnscrypt_enabled)
        self.chk_dns.blockSignals(False)

    SCAN_TYPES = ["", "-sS", "-sT", "-sU", "-sN", "-sF", "-sX", "-sA"]
    SCAN_DISC = ["", "-Pn", "-sn", "-PS", "-PA", "-PU"]
    SCAN_TEMPO = ["", "0", "1", "2", "3", "4", "5"]
    SCAN_OUT = ["none", "oN", "oX", "oG"]

    def _fill_combo(self, combo, keys: tuple) -> None:
        T = self.tr
        cur = combo.currentIndex()
        combo.blockSignals(True)
        combo.clear()
        for key in keys:
            combo.addItem(T(key))
        combo.setCurrentIndex(cur if 0 <= cur < len(keys) else 0)
        combo.blockSignals(False)

    def _rt_scan(self) -> None:
        T = self.tr
        self.lbl_scan_title.setText(T("scan_title"))
        self.lbl_scan_engine.setText(T("scan_engine", e=self._scan_engine()[1]))
        self.lbl_scan_target.setText(T("scan_target"))
        self.lbl_scan_profile.setText(T("scan_profile"))
        self._fill_combo(self.combo_scan, ("scan_p_quick", "scan_p_services",
                                           "scan_p_full", "scan_p_os",
                                           "scan_p_ping", "scan_p_custom"))
        self.btn_scan_adv.setText(T("scan_adv"))
        self.lbl_scan_type.setText(T("scan_type"))
        self._fill_combo(self.combo_scan_type, ("scan_st_auto", "scan_st_syn",
                                                "scan_st_con", "scan_st_udp",
                                                "scan_st_null", "scan_st_fin",
                                                "scan_st_xmas", "scan_st_ack"))
        self.lbl_scan_ports.setText(T("scan_ports"))
        self.edit_scan_ports.setPlaceholderText(T("scan_ports_hint"))
        self.lbl_scan_disc.setText(T("scan_disc"))
        self._fill_combo(self.combo_scan_disc, ("scan_sd_auto", "scan_sd_noping",
                                                "scan_sd_sweep", "scan_sd_syn",
                                                "scan_sd_ack", "scan_sd_udp"))
        self.chk_scan_sv.setText(T("scan_sv"))
        self.chk_scan_os.setText(T("scan_os"))
        self.chk_scan_aggr.setText(T("scan_aggr"))
        self.chk_scan_reason.setText(T("scan_reason"))
        self.chk_scan_frag.setText(T("scan_frag"))
        self.lbl_scan_timing.setText(T("scan_timing"))
        self._fill_combo(self.combo_scan_timing, ("scan_tm_def", "scan_tm_0",
                                                  "scan_tm_1", "scan_tm_2",
                                                  "scan_tm_3", "scan_tm_4",
                                                  "scan_tm_5"))
        self.lbl_scan_decoy.setText(T("scan_decoy"))
        self.edit_scan_decoy.setPlaceholderText(T("scan_decoy_hint"))
        self.lbl_scan_scripts.setText(T("scan_scripts"))
        self.edit_scan_scripts.setPlaceholderText(T("scan_scripts_hint"))
        self.lbl_scan_script_args.setText(T("scan_script_args"))
        self.lbl_scan_outfmt.setText(T("scan_outfmt"))
        self._fill_combo(self.combo_scan_out, ("scan_of_screen", "scan_of_normal",
                                               "scan_of_xml", "scan_of_grep"))
        self.lbl_scan_extra.setText(T("scan_extra"))
        self.lbl_scan_cmd_title.setText(T("scan_cmd"))
        self.chk_scan_tor.setText(T("scan_via_tor"))
        self.chk_scan_open.setText(T("scan_open"))
        self.chk_scan_noping.setText(T("scan_noping"))
        self.btn_scan_run.setText(T("scan_run"))
        self.btn_scan_stop.setText(T("stop"))
        self.btn_scan_save.setText(T("scan_save"))
        self.lbl_scan_warn.setText(T("scan_warn"))
        self._scan_preview()

    def _scan_preset(self, i: int) -> None:
        """Perfil rápido preenche os controles avançados."""
        if i == 5:
            self._scan_preview()
            return
        P = {
            0: dict(ty=0, ports="", disc=0, sv=False, os=False, ag=False, tm=0,
                    frag=False, scr="", out=0),
            1: dict(ty=0, ports="", disc=0, sv=True, os=False, ag=False, tm=0,
                    frag=False, scr="", out=0),
            2: dict(ty=0, ports="all", disc=0, sv=False, os=False, ag=False,
                    tm=5, frag=False, scr="", out=0),
            3: dict(ty=0, ports="", disc=0, sv=True, os=True, ag=False, tm=0,
                    frag=False, scr="", out=0),
            4: dict(ty=0, ports="", disc=2, sv=False, os=False, ag=False, tm=0,
                    frag=False, scr="", out=0),
        }.get(i)
        if not P:
            return
        self.combo_scan_type.setCurrentIndex(P["ty"])
        self.edit_scan_ports.setText(P["ports"])
        self.combo_scan_disc.setCurrentIndex(P["disc"])
        self.chk_scan_sv.setChecked(P["sv"])
        self.chk_scan_os.setChecked(P["os"])
        self.chk_scan_aggr.setChecked(P["ag"])
        self.combo_scan_timing.setCurrentIndex(P["tm"])
        self.chk_scan_frag.setChecked(P["frag"])
        self.edit_scan_scripts.setText(P["scr"])
        self.combo_scan_out.setCurrentIndex(P["out"])
        self._scan_preview()

    def _rt_total(self) -> None:
        T = self.tr
        self.lbl_total_title.setText(T("total_title"))
        vals = {
            "lay_tor": (T("on") if self.connected else T("off"), self.connected),
            "lay_socks": (T("on") if self.socks_running else T("off"), self.socks_running),
            "lay_sys": (T("on") if self.cfg.protect_total else T("off"), self.cfg.protect_total),
            "lay_fw": (T("on") if self.cfg.firewall_on else T("off"), self.cfg.firewall_on),
        }
        for key, lbl in self.lay_labels.items():
            v, ok = vals[key]
            lbl.setText(v)
            lbl.setStyleSheet(f"font-weight: bold; color: {'#10b981' if ok else '#78788a'};")
        for key, t in (("lay_tor", "TOR"), ("lay_socks", "SOCKS"), ("lay_sys", "SIST"), ("lay_fw", "FW")):
            getattr(self, f"_lay_t_{key}").setText(T(key))
        self.lbl_total_enable.setText(T("total_enable"))
        self.lbl_total_desc.setText(T("total_desc"))
        self.lbl_fw_title.setText(T("fw_title"))
        self.lbl_fw_desc.setText(T("fw_desc"))
        admin = sysprotect.is_admin()
        self.lbl_fw_admin.setText(T("fw_admin") if admin else T("fw_noadmin"))
        self.chk_total.blockSignals(True)
        self.chk_total.setChecked(self.cfg.protect_total)
        self.chk_total.blockSignals(False)
        self.chk_fw.blockSignals(True)
        self.chk_fw.setChecked(self.cfg.firewall_on)
        self.chk_fw.blockSignals(False)
        self.lbl_total_restore.setText(T("net_restore_desc"))
        self.btn_total_restore.setText(T("net_restore_btn"))

    def _rt_apps(self) -> None:
        T = self.tr
        if not hasattr(self, "apps_box"):
            return
        self.lbl_apps_title.setText(T("apps_title"))
        n = len(self.cfg.apps)
        self.lbl_apps_count.setText(T("apps_count", n=n))
        self.lbl_apps_sub.setText(T("apps_sub"))
        self.edit_app_path.setPlaceholderText(T("apps_path_hint"))
        self.btn_app_add.setText(T("apps_add"))
        self.lbl_apps_ff.setText(T("apps_ff", p=self.cfg.socks_port))
        self.btn_leak_test.setText(T("leak_test"))
        self.lbl_apps_empty.setText(T("apps_empty"))
        self.lbl_apps_empty.setVisible(n == 0)
        self._render_apps()

    def _app_browse(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("apps_title"), "", "Apps (*.exe);;All (*)")
        if path:
            self.edit_app_path.setText(path)

    def _leak_test(self) -> None:
        """Abre ipleak.net no navegador via Tor p/ conferir vazamentos."""
        if not self.connected or not self.socks_running:
            self._push_log(self.tr("leak_need"))
            return
        browser = ""
        for d in sysprotect.detect_apps():
            if os.path.basename(sysprotect.expand(d["path"])).lower() in (
                    "chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"):
                p = sysprotect.expand(d["path"])
                if os.path.exists(p):
                    browser = p
                    break
        if not browser:
            self._push_log(self.tr("leak_nobrowser"))
            return
        try:
            how = sysprotect.launch_with_proxy(
                browser, self.cfg.socks_port, "https://ipleak.net")
            name = os.path.splitext(os.path.basename(browser))[0]
            self._push_log(self.tr("log_leak_open", n=name, m=how))
        except Exception as e:  # noqa: BLE001
            self._push_log(f"✗ {e}"[:300])

    def _rt_logs(self) -> None:
        T = self.tr
        self.lbl_logs_title.setText(T("logs_title"))
        self.lbl_logs_info.setText(T("logs_info"))
        self.lbl_filter.setText(T("log_filter"))
        self.edit_filter.setPlaceholderText("consensus, guard...")
        self.btn_pause.setText(T("log_resume") if self._log_paused else T("log_pause"))
        self.btn_copylog.setText(T("copy_log"))
        self.btn_clearlog.setText(T("clear"))
        self.btn_nolog.setText(T("log_never"))
        self.btn_nolog.setChecked(bool(self.cfg.never_store_logs))
        self.lbl_nolog_hint.setText(T("log_never_hint"))
        self.lbl_nolog_hint.setVisible(bool(self.cfg.never_store_logs))
        self._render_logs()

    def _rt_diag(self) -> None:
        T = self.tr
        self.lbl_diag_title.setText(T("diag_title"))
        self.lbl_diag_tor.setText(T("diag_tor"))
        self.lbl_target.setText(T("target"))
        self.btn_test.setText(T("test"))
        self.lbl_net_title.setText(T("diag_net"))
        self.lbl_net_desc.setText(T("diag_net_desc"))
        self.btn_net.setText(T("diag_net_btn"))
        self.btn_e2e.setText(T("e2e_btn"))
        try:
            _titles = {"dns": T("net_dns"), "tcp": T("net_tcp"), "http": T("net_http")}
            for _cid, (_t, _v, _s) in self.net_cards.items():
                _t.setText(_titles[_cid])
        except (RuntimeError, AttributeError):
            pass
        self.lbl_wipe_title.setText(T("diag_wipe"))
        self.lbl_wipe_desc.setText(T("diag_wipe_desc"))
        self.btn_wipe.setText(T("diag_wipe_btn"))
        self.btn_data.setText(T("open_data"))
        self.btn_reset.setText(T("reset"))
        self.btn_backup_exp.setText(T("backup_export"))
        self.btn_backup_imp.setText(T("backup_import"))
        self.lbl_restore_title.setText(T("net_restore_title"))
        self.lbl_restore_desc.setText(T("net_restore_desc"))
        self.btn_net_restore.setText(T("net_restore_btn"))
        self.lbl_vault_title.setText(T("vault_title"))
        self.lbl_vault_desc.setText(T("vault_desc"))
        self.btn_vault.setText(T("vault_change_btn"))
        self.btn_duress.setText(T("duress_btn"))
        self.lbl_duress.setText(T("duress_desc"))

    def _change_password(self) -> None:
        from PyQt6.QtWidgets import QDialog, QMessageBox
        from .gui import PassDialog
        d = PassDialog(self, "change", self.cfg.lang)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        cur, new, conf = d.values()
        from . import vault as _v
        try:
            _v.decrypt_obj(cur, self._cfg_dir())
        except _v.BadPassword:
            QMessageBox.warning(self, "Anonymous Shield", self.tr("vault_wrong"))
            return
        except _v.VaultError as e:
            QMessageBox.warning(self, "Anonymous Shield", f"✗ {e}")
            return
        if len(new) < 8:
            QMessageBox.warning(self, "Anonymous Shield", self.tr("vault_short"))
            return
        if new != conf:
            QMessageBox.warning(self, "Anonymous Shield", self.tr("vault_mismatch"))
            return
        self.cfg.password = new
        self.cfg.save()
        self._push_log(self.tr("vault_changed"))

    def _duress_dialog(self) -> None:
        """Define/remove a senha de coação (apaga o perfil se digitada no login)."""
        from PyQt6.QtWidgets import QDialog, QMessageBox
        from . import users as _users
        from .gui import PassDialog
        uid = (getattr(self.cfg, "current_uid", "") or "").strip()
        if not uid:
            QMessageBox.information(
                self, "Anonymous Shield", self.tr("duress_guest"))
            return
        if _users.has_duress(uid):
            ans = QMessageBox.question(
                self, "Anonymous Shield", self.tr("duress_remove_q"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ans == QMessageBox.StandardButton.Yes:
                _users.clear_duress(uid)
                self._push_log(self.tr("duress_cleared"))
                self.refresh_texts()
                return
        d = PassDialog(self, "change", self.cfg.lang)
        try:
            d.setWindowTitle(self.tr("duress_title"))
        except (RuntimeError, AttributeError):
            pass
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        cur, new, conf = d.values()
        if not _users.verify_user(uid, cur):
            QMessageBox.warning(self, "Anonymous Shield", self.tr("vault_wrong"))
            return
        if len(new) < 8 or new != conf:
            QMessageBox.warning(self, "Anonymous Shield", self.tr("vault_mismatch"))
            return
        try:
            _users.set_duress(uid, new)
        except ValueError:
            QMessageBox.warning(self, "Anonymous Shield", self.tr("duress_same"))
            return
        QMessageBox.warning(self, "Anonymous Shield", self.tr("duress_warn"))
        self._push_log(self.tr("duress_ok"))
        self.refresh_texts()

    def _cfg_dir(self) -> str:
        from .config import app_dirs
        cfg_dir, _ = app_dirs()
        return cfg_dir

    def _upd_src_set(self, which: str) -> None:
        self.upd_src = "url" if which == "url" else "gh"
        self.refresh_texts()

    def _rt_update(self) -> None:
        T = self.tr
        self.lbl_upd_title.setText(T("upd_title"))
        try:
            self.lbl_tor_ver.setText(T("tor_ver", v=sysprotect.tor_version()))
        except (RuntimeError, AttributeError):
            pass
        self.lbl_upd_note.setText(T("upd_note"))
        self.lbl_upd_src.setText(T("upd_src"))
        self.btn_upd_src_gh.setText("GitHub")
        self.btn_upd_src_url.setText(T("upd_src_url"))
        src = getattr(self, "upd_src", "gh")
        self.btn_upd_src_gh.setChecked(src == "gh")
        self.btn_upd_src_url.setChecked(src == "url")
        self.gh_box.setVisible(src == "gh")
        self.url_box.setVisible(src == "url")
        self.lbl_upd_repo.setText(T("upd_repo"))
        self.edit_repo.setText(self.cfg.update_repo or "")
        self.edit_repo.setToolTip(T("upd_repo_tip"))
        self.btn_upd_check.setText(T("upd_check"))
        self.lbl_upd_url.setText(T("upd_url"))
        self.edit_upd_url.setPlaceholderText(T("upd_url_hint"))
        self.lbl_upd_sha.setText(T("upd_sha"))
        self.edit_upd_sha.setPlaceholderText(T("upd_sha_hint"))
        self.btn_upd_dl_url.setText(T("upd_download"))
        self.btn_upd_open.setText(T("upd_open"))
        self.lbl_about_title.setText(T("about_title"))
        self.lbl_about_text.setText(T("about_text", v=__version__,
                                      t=sysprotect.tor_version()))
        self.btn_licenses.setText(T("about_view"))

    # ---------- tor ----------
    def describe_route(self) -> str:
        if self.cfg.bridges_enabled and self.cfg.bridges:
            # Com pontes não há rota "direta": ou pontes ou direto.
            base = (f"{self.tr('route_bridges')}: {len(self.cfg.bridges)} "
                    f"bridge(s) [{self.cfg.bridge_preset}]")
            if self.cfg.upstream_enabled:
                base = f"{self.tr('route_via')} + {base}"
        else:
            base = self.tr("route_via") if self.cfg.upstream_enabled else self.tr("route_direct")
        if getattr(self, "vpns", None):
            base = f"{base} + via VPN ({', '.join(self.vpns)})"
        if self.cfg.exit_mode in ("five", "nine", "fourteen"):
            base = f"{base} [−{self.cfg.exit_mode}]"
        return base

    # ---------- VPN externa ----------
    def _vpn_refresh(self) -> None:
        def job() -> None:
            try:
                found = sysprotect.vpn_running()
            except Exception:
                found = []
            self.vpns = [f["name"] for f in found]
            self.vpn_exes = [f["exe"] for f in found if f.get("exe")]
            self._on_ui(self.refresh_texts)
        threading.Thread(target=job, daemon=True).start()

    def _vpn_connect(self) -> None:
        exe = (self.edit_vpn_bin.text().strip() or sysprotect.find_openvpn()).strip()
        cfg = self.edit_vpn_config.text().strip()
        if not exe or not os.path.exists(exe):
            self._push_log(self.tr("vpn_nobin"))
            return
        if not cfg or not os.path.exists(cfg):
            self._push_log(self.tr("vpn_nocfg"))
            return
        self.cfg.vpn_bin, self.cfg.vpn_config = exe, cfg
        self.cfg.vpn_user = self.edit_vpn_user.text()
        self.cfg.vpn_pass = self.edit_vpn_pass.text()
        self.cfg.save()
        try:
            self._vpn_proc = sysprotect.ovpn_start(exe, cfg, self.cfg.vpn_user, self.cfg.vpn_pass)
        except Exception as e:  # noqa: BLE001
            sysprotect.ovpn_shred_auth()
            self._push_log(f"✗ {e}"[:300])
            return
        self.vpn_on = True
        self._push_log(self.tr("vpn_started"))
        self.refresh_texts()
        # openvpn lê o auth no arranque: tritura 25s depois, sem travar a UI.
        def _shred_later() -> None:
            time.sleep(25)
            try:
                if self.vpn_on:
                    sysprotect.ovpn_shred_auth()
            except Exception:
                pass
        threading.Thread(target=_shred_later, daemon=True).start()

    def _vpn_disconnect(self) -> None:
        try:
            if getattr(self, "_vpn_proc", None):
                proc = self._vpn_proc
                self._vpn_proc = None
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=6)
                    except Exception:
                        proc.kill()
        except Exception:
            pass
        finally:
            sysprotect.ovpn_shred_auth()
        if self.vpn_on:
            self._push_log(self.tr("vpn_stopped"))
        self.vpn_on = False
        self.refresh_texts()

    def _vpn_poll(self) -> None:
        proc = getattr(self, "_vpn_proc", None)
        if proc and proc.poll() is not None:
            self._vpn_proc = None
            self.vpn_on = False
            self._push_log(self.tr("vpn_died", rc=proc.returncode))
            try:
                with open(sysprotect.ovpn_log_path(), encoding="utf-8", errors="replace") as f:
                    tail = f.read().splitlines()[-8:]
                for line in tail:
                    self._push_log(f"[ovpn] {line.strip()[-200:]}")
            except OSError:
                pass
            self.refresh_texts()

    def _vpn_show_log(self) -> None:
        target = getattr(self, "lbl_vpn_log", getattr(self, "lbl_result", None))
        if target is None:
            return
        try:
            with open(sysprotect.ovpn_log_path(), encoding="utf-8", errors="replace") as f:
                tail = f.read().splitlines()[-25:]
            target.setText("openvpn.log:\n" + "\n".join(tail))
        except OSError as e:
            target.setText(f"✗ {e}")

    def _vpn_browse(self, what: str) -> None:
        from PyQt6.QtWidgets import QFileDialog
        if what == "bin":
            path, _ = QFileDialog.getOpenFileName(
                self, self.tr("vpn_bin"), self.edit_vpn_bin.text().strip(),
                "Exe (openvpn*.exe);;All (*)")
            if path:
                self.edit_vpn_bin.setText(path)
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, self.tr("vpn_cfg"), self.edit_vpn_config.text().strip(),
                "OpenVPN (*.ovpn);;All (*)")
            if path:
                self.edit_vpn_config.setText(path)

    def _rt_vpn(self) -> None:
        T = self.tr
        if not hasattr(self, "edit_vpn_bin"):
            return
        self.lbl_vpn_title.setText(T("vpn_title"))
        if self.vpn_on:
            self.lbl_vpn_state.setText(T("vpn_state_on"))
            self.lbl_vpn_hint.setText(T("vpn_via_ovpn"))
        elif getattr(self, "vpns", None):
            self.lbl_vpn_state.setText("● " + ", ".join(self.vpns))
            self.lbl_vpn_hint.setText(f"{T('route')}: {self.describe_route()}")
        else:
            self.lbl_vpn_state.setText(T("vpn_state_off"))
            self.lbl_vpn_hint.setText(T("vpn_direct"))
        self.lbl_vpn_det_title.setText(T("vpn_det_title"))
        self.btn_vpn_refresh.setText(T("vpn_refresh"))
        vpns = getattr(self, "vpns", []) or []
        self.lbl_vpn_list.setText(
            "\n".join(f"● {n}" for n in vpns) if vpns else T("vpn_det_none"))
        self.lbl_vpn_det_note.setText(T("vpn_det_note"))
        self.lbl_vpn_ovpn_title.setText(T("vpn_ovpn_title"))
        self.lbl_vpn_bin.setText(T("vpn_bin"))
        if not self.edit_vpn_bin.text().strip():
            self.edit_vpn_bin.setText(self.cfg.vpn_bin or sysprotect.find_openvpn())
        self.edit_vpn_bin.setPlaceholderText(T("vpn_bin_hint"))
        self.lbl_vpn_cfg.setText(T("vpn_cfg"))
        if not self.edit_vpn_config.text().strip() and self.cfg.vpn_config:
            self.edit_vpn_config.setText(self.cfg.vpn_config)
        self.edit_vpn_config.setPlaceholderText(T("vpn_cfg_hint"))
        self.lbl_vpn_user.setText(T("vpn_user"))
        if not self.edit_vpn_user.text() and self.cfg.vpn_user:
            self.edit_vpn_user.setText(self.cfg.vpn_user)
        self.lbl_vpn_pass.setText(T("vpn_pass"))
        self.edit_vpn_pass.setPlaceholderText(T("vpn_pass_hint"))
        self.btn_vpn_connect.setText(T("vpn_connect"))
        self.btn_vpn_disc.setText(T("vpn_disconnect"))
        self.btn_vpn_log.setText(T("vpn_log"))

    def _adopt_states(self) -> None:
        if sysprotect.is_our_proxy(self.cfg.socks_port):
            self.socks_running = True
        else:
            self.socks_running = False
            if self.cfg.protect_total:
                self.cfg.protect_total = False
        fw = sysprotect.firewall_active()
        if fw and not (self.cfg.firewall_on
                       or (self.cfg.protect_total and self.cfg.use_tor)):
            # Sobrou bloqueio de sessão morta (crash): reverte sozinho.
            for key, arg in sysprotect.net_rescue():
                self._push_log(f"🛟 {self.tr(key, d=arg)}")
            self.cfg.firewall_on = False
            self.cfg.save()
            fw = False
        if fw != self.cfg.firewall_on:
            self.cfg.firewall_on = fw
        # mescla apps (migra paths antigos absolutos p/ forma %VAR%)
        for a in self.cfg.apps:
            if isinstance(a, dict) and a.get("path"):
                a["path"] = sysprotect.portable(a["path"])
        for d in sysprotect.detect_apps():
            if not any(a["path"] == d["path"] for a in self.cfg.apps):
                self.cfg.apps.append(d)
        self.cfg.apps = [a for a in self.cfg.apps
                         if (isinstance(a, dict) and (a.get("custom") or os.path.exists(sysprotect.expand(a.get("path", "")))))]
        self.cfg.save()

    def _ensure_fw(self) -> None:
        try:
            ok = sysprotect.ensure_allowed_app()
        except Exception:
            ok = False
        if ok:
            self._push_log(self.tr("w_fw_allowed"))

    def connect_tor(self) -> None:
        if self.another:
            msg = self.tr("err_another")
            self._push_log(msg)
            self._show_error(msg)
            return
        if self.connected or self.connecting:
            return
        self.cfg.use_tor = True
        self.cfg.save()
        self.connecting = True
        self.progress = 0.0
        self._t0 = time.time()
        self._last_change = self._t0
        self._push_log(self.tr("log_connecting", m=self.describe_route()))
        self._worker = TorWorker(self.cfg)
        w = self._worker
        w.progress.connect(self._on_progress)
        w.connected.connect(self._on_connected)
        w.failed.connect(self._on_failed)
        w.log_line.connect(self._push_log)
        w.exit_info.connect(self._on_exit_info)
        w.circuit_result.connect(self._on_circuit_result)
        w.identity_done.connect(lambda: self._push_log(self.tr("log_identity")))
        w.test_result.connect(self._on_test_result)
        self._tor_thread = TorThread(w)
        self._tor_thread.finished.connect(self._tor_thread.deleteLater)
        self._tor_thread.start()
        self._refresh_status()
        self.refresh_texts()

    def disconnect_tor(self, silent: bool = False) -> None:
        self.connecting = False
        w = self._worker
        if w is not None:
            # worker velho não pode mais falar com a UI (sinais tardios
            # ressuscitavam "conectando" e derrubavam o app).
            for _sig in ("progress", "connected", "failed", "log_line",
                         "exit_info", "identity_done", "test_result",
                         "circuit_result", "status_result"):
                try:
                    getattr(w, _sig).disconnect()
                except (TypeError, RuntimeError):
                    pass
            w.stop()
            w.kill_tor()
        # Sem wait(): o wait(3000) congelava a UI e o thread órfão com
        # wait em outra thread corria risco de use-after-free. Sinais já
        # desligados acima; finished→deleteLater recolhe sozinho.
        self._tor_thread = None
        self._worker = None
        was = self.connected
        self.connected = False
        self.socks_running = False
        self.exit_ip = ""
        if not silent or was:
            self._push_log(self.tr("log_disconnected"))
        self._refresh_status()
        self.refresh_texts()

    def _onion_clicked(self) -> None:
        if self.connected or self.connecting:
            self.cfg.use_tor = False
            self.cfg.save()
            self.disconnect_tor()
            # Parar o Tor com proteção total = internet de volta ao padrão.
            try:
                self.restore_internet()
            except Exception:
                pass
        else:
            self.connect_tor()

    def _on_progress(self, frac: float, tag: str, summary: str) -> None:
        if self.connected or self._worker is None:
            return
        self.connecting = True
        if frac > self.progress:
            self.progress = frac
        if abs(frac - getattr(self, "_pf", -1)) > 0.001:
            self._pf = frac
            self._last_change = time.time()

    def _on_connected(self) -> None:
        self.connected = True
        self.connecting = False
        self.progress = 1.0
        self._rotate_last = time.time()
        if self.cfg.socks_enabled:
            self.socks_running = True
        self._push_log(self.tr("log_connected"))
        if self.pending_protect:
            self.pending_protect = False
            self._sysproxy_on()
        if getattr(self, "pending_fw", False):
            self.pending_fw = False
            if self.cfg.protect_total and not self.cfg.firewall_on:
                self._fw_toggled(True)
        # DNSCrypt local/combinado sobe junto com o Tor.
        if (self.cfg.dnscrypt_enabled
                and self.cfg.dnscrypt_mode in ("local", "combined")
                and not self.dns_running):
            from PyQt6.QtCore import QTimer as _QTimer
            _QTimer.singleShot(1500, self._dns_start)
        self._refresh_status()
        self.refresh_texts()

    def _on_failed(self, msg: str) -> None:
        if self._worker is None:
            return
        self.connecting = False
        self._show_error(msg)
        self._push_log(msg if msg[:1] in "✗✓→●○⚠" else "✗ " + msg)
        if self.cfg.protect_total or self.cfg.firewall_on:
            # Tor não subiu com proteção total: sem isso o PC ficava sem
            # rede (proxy morto + firewall bloqueando). Devolve tudo.
            try:
                self.restore_internet()
            except Exception:
                pass
            self._push_log(self.tr("total_auto_off"))
        self._refresh_status()
        self.refresh_texts()

    def _on_exit_info(self, ip: str, is_tor: bool, country: str) -> None:
        if self._worker is None:
            return
        self.exit_ip, self.exit_is_tor, self.exit_country = ip, is_tor, country
        self.refresh_texts()

    @staticmethod
    def _flag(cc: str) -> str:
        cc = (cc or "").lower()
        if len(cc) != 2 or not cc.isalpha():
            return "🏳"
        return chr(0x1F1E6 + ord(cc[0]) - 97) + chr(0x1F1E6 + ord(cc[1]) - 97)

    def _circuit_job(self) -> None:
        try:
            w = self._worker
            if w is not None:
                w.fetch_circuit()
        except Exception:
            pass
        finally:
            try:
                self._circuit_busy = False
            except (RuntimeError, AttributeError):
                pass

    def _on_circuit_result(self, info: list) -> None:
        self._circuit_busy = False
        self.circuit = info or []
        try:
            if os.name != "nt":
                guards = [h.get("ip", "") for c in (info or [])
                          for h in (c.get("path") or [])[:1]]
                sysprotect.set_linux_guards(guards)
                if sysprotect.firewall_active():
                    sysprotect.refresh_linux_guards()
        except Exception:
            pass
        self._render_circuit()

    def _current_dns(self) -> str:
        """DNS em uso agora (cache 30s): stub, saída Tor ou sistema."""
        try:
            if (time.time() - getattr(self, "_dns_t0", 0.0) < 30
                    and getattr(self, "_dns_now", "")):
                return self._dns_now
            if self.cfg.dnscrypt_enabled and self.dns_running and self.dns_addr:
                val = f"{self.dns_addr} (stub)"
            elif self.connected:
                val = self.tr("dns_via_exit")
            else:
                val = sysprotect.system_dns() or "?"
            self._dns_now, self._dns_t0 = val, time.time()
            return val
        except (RuntimeError, AttributeError):
            return "?"

    def _render_circuit(self) -> None:
        try:
            T = self.tr
            sig = repr(getattr(self, "circuit", [])) + "|" + self.cfg.lang
            if sig == getattr(self, "_circuit_sig", ""):
                return
            self._circuit_sig = sig
            lay = self.circuit_rows
            while lay.count():
                item = lay.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
            roles = [T("circuit_this"), T("relay_guard"), T("relay_middle"), T("relay_exit")]

            def _row(left: str, right: str) -> None:
                h = QHBoxLayout()
                h.setSpacing(10)
                a = QLabel(left)
                a.setWordWrap(True)
                b = QLabel(right)
                b.setObjectName("muted")
                b.setStyleSheet("font-family: monospace;")
                b.setWordWrap(True)
                h.addWidget(a, 1)
                h.addWidget(b, 1)
                box = QWidget()
                box.setLayout(h)
                lay.addWidget(box)

            circs = getattr(self, "circuit", []) or []
            if self.connected and circs and circs[0].get("path"):
                path = circs[0]["path"]
                _row(f"○  {roles[0]}", "")
                for i, r in enumerate(path[:3]):
                    role = roles[min(i + 1, 3)]
                    nm = f"{self._flag(r.get('cc'))}  {role}"
                    if r.get("cc"):
                        nm += f" ({r['cc'].upper()})"
                    _row(nm, r.get("ip", "?"))
                if self.exit_ip:
                    _row(f"🌐  {self.exit_ip}", self.exit_country)
            else:
                _row(T("circuit_none"), "")
        except (RuntimeError, AttributeError):
            pass

    def _on_test_result(self, target: str, result: str) -> None:
        if target == "wipe-tor-data":
            self.lbl_result.setText(result)
            if self.cfg.use_tor:
                self.connect_tor()
        else:
            self.lbl_result.setText(f"{target}\n{result}")

    def _show_error(self, msg: str) -> None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Anonymous Shield", msg[:800])

    def _new_identity(self) -> None:
        if not self.connected or not self._worker:
            return
        threading.Thread(target=self._worker.new_identity, daemon=True).start()

    def _check_exit(self) -> None:
        if not self.connected or not self._worker:
            return
        threading.Thread(target=self._worker._fetch_exit, daemon=True).start()

    def _check_status(self) -> None:
        """Check manual: bootstrap (controle) + saída IsTor, com resultado no hero."""
        if not self.connected:
            self._push_log(self.tr("check_off"))
            return
        if getattr(self, "_checking", False):
            return
        self._checking = True
        self._status_line = ""
        try:
            self.dash_phase.setText(self.tr("testing"))
        except (RuntimeError, AttributeError):
            pass
        self.refresh_texts()

        def _job() -> None:
            from .torctl import TorWorker as _TW
            w = _TW(self.cfg)
            self._status_worker = w
            try:
                w.status_result.connect(self._on_status_result)
            except RuntimeError:
                return
            w.status_check()

        threading.Thread(target=_job, daemon=True).start()

    def _on_status_result(self, info: dict) -> None:
        self._status_worker = None
        self._checking = False
        if info.get("ok"):
            try:
                dns = self.dash_dns_sub()
            except (RuntimeError, AttributeError):
                dns = self.cfg.dnscrypt_mode
            line = self.tr("tor_ok", phase=info.get("phase", "?"),
                           ip=info.get("ip", "?"), dns=dns)
        else:
            line = self.tr("tor_bad", e=info.get("err") or info.get("phase", "?"))
            if info.get("ip"):
                self.exit_ip = info["ip"]
        self._status_line = line
        self._status_t0 = time.time()
        self._push_log(line)
        self.refresh_texts()

    def _copy_ip(self) -> None:
        if self.exit_ip:
            QApplication.clipboard().setText(self.exit_ip)
            self._push_log(self.tr("log_ip_copied", ip=self.exit_ip))

    def _browser_open(self) -> None:
        """Abre o Tor Browser (anonimato real) ou aponta p/ download."""
        import subprocess as _sp
        cands = []
        if (self.cfg.tor_browser_path or "").strip():
            cands.append(self.cfg.tor_browser_path.strip())
        for base in (os.path.join(os.environ.get("PROGRAMFILES", ""), "Tor Browser"),
                     os.path.join(os.environ.get("LOCALAPPDATA", ""),
                                  "Tor Browser"),
                     os.path.join(os.path.expanduser("~"), "Desktop", "Tor Browser")):
            cands.append(os.path.join(base, "Browser", "firefox.exe"))
        for c in cands:
            if c and os.path.exists(c):
                self.cfg.tor_browser_path = c
                self.cfg.save()
                try:
                    _sp.Popen([c], close_fds=False,
                              creationflags=getattr(_sp, "DETACHED_PROCESS", 0))
                    self._push_log(self.tr("log_browser_open"))
                except OSError as e:
                    self._push_log(f"✗ {e}"[:300])
                return
        self._push_log(self.tr("browser_nobin"))
        QDesktopServices.openUrl(QUrl("https://www.torproject.org/download/"))

    def _power_text(self) -> None:
        if self.connected or self.connecting:
            self.btn_power.setText(self.tr("power_off"))
            self.btn_power.setStyleSheet(
                "background:#b91c1c; color:white; font-weight:bold;"
                "border-radius:10px; padding:10px;")
        else:
            self.btn_power.setText(self.tr("power_on"))
            self.btn_power.setStyleSheet("")

    def _cancel_connect(self) -> None:
        self.cfg.use_tor = False
        self.cfg.save()
        self._push_log(self.tr("log_cancelled"))
        self.disconnect_tor(silent=True)
        try:
            self.restore_internet()
        except Exception:
            pass
        self.refresh_texts()

    # ---------- tick (fases, stall, tor.log) ----------
    def _sync_dashboard_tick(self, pct: int, phase_text: str = "") -> None:
        try:
            if not hasattr(self, "dash_bar"):
                return
            self.dash_bar.setValue(pct if (self.connecting or self.connected) else 0)
            big = self.tr("st_connected") if self.connected else (f"{pct}%" if self.connecting else self.tr("st_off"))
            self.dash_big.setText(big)
            if self.connected and self.exit_ip:
                self.dash_phase.setText(f"{self.exit_ip}  •  {self.exit_country}")
            elif self.connected:
                self.dash_phase.setText(self.tr("checking_ip"))
            elif self.connecting:
                self.dash_phase.setText(phase_text or f"Bootstrap {pct}%")
            else:
                self.dash_phase.setText(self.tr("off_tap"))
            self.dash_cancel.setVisible(bool(self.connecting and not self.connected))
            try:
                if (getattr(self, "_status_line", "")
                        and time.time() - getattr(self, "_status_t0", 0) < 12):
                    self.dash_phase.setText(self._status_line)
            except (RuntimeError, AttributeError):
                pass
            # atualiza KPIs/atividade sem reconstruir tudo (barato a cada 500ms)
            self._rt_dashboard()
        except (RuntimeError, AttributeError):
            pass

    def _tick(self) -> None:
        pct = int(self.progress * 100)
        self._power_text()
        try:
            self.btn_onion.set_state(
                "on" if self.connected else ("ing" if self.connecting else "off"),
                self.progress,
            )
        except (RuntimeError, AttributeError):
            pass
        big = self.tr("st_connected") if self.connected else (f"{pct}%" if self.connecting else self.tr("st_off"))
        col = "#10b981" if self.connected else ("#f59e0b" if self.connecting else ("#64748b" if self.cfg.theme == "light" else "#78788a"))
        if getattr(self, "_tick_big", None) != (big, col):
            self._tick_big = (big, col)
            self.lbl_bigstatus.setText(big)
            self.lbl_bigstatus.setStyleSheet(f"font-size: 30px; font-weight: bold; color: {col};")
        self.btn_cancel.setVisible(self.connecting and not self.connected)
        if self.connecting:
            pct = int(self.progress * 100)
            if pct <= 9:
                ph = self.tr("ph_start")
            elif pct <= 25:
                ph = self.tr("ph_guards")
            elif pct <= 55:
                ph = self.tr("ph_consensus")
            elif pct <= 85:
                ph = self.tr("ph_circuits")
            else:
                ph = self.tr("ph_final")
            el = int(time.time() - self._t0) if self._t0 else 0
            self.bar.setValue(pct)
            self.lbl_phase.setText(f"Bootstrap {pct}% ({el}s)  •  {ph}")
            self._sync_dashboard_tick(pct, f"Bootstrap {pct}% ({el}s)  •  {ph}")
            stall = int(time.time() - self._last_change)
            if stall > 60 and pct < 99:
                self.lbl_detail.setText(self.tr("stuck_title", s=stall))
                self.box_block.setVisible(True)
                self.lbl_block.setText(self.tr("stuck_title", s=stall))
            else:
                self.box_block.setVisible(False)
        else:
            self.bar.setValue(100 if self.connected else 0)
            if self.connected and self.exit_ip:
                self.lbl_phase.setText(f"{self.exit_ip}  •  {self.exit_country}")
                self.card_exit.setVisible(True)
                self.lbl_exit_ip.setText(self.exit_ip)
                self.lbl_exit_country.setText(self.exit_country)
                self.btn_exit_copy.setVisible(True)
                self._sync_dashboard_tick(100)
            elif self.connected:
                self.lbl_phase.setText(self.tr("checking_ip"))
                self.card_exit.setVisible(True)
                self.lbl_exit_ip.setText("…")
                self.lbl_exit_country.setText("")
                self.btn_exit_copy.setVisible(False)
                self._sync_dashboard_tick(100)
            else:
                self.lbl_phase.setText(self.tr("off_tap"))
                self.card_exit.setVisible(False)
                self.box_block.setVisible(False)
                self._sync_dashboard_tick(0)
        # circuito (a cada ~6s, só conectado)
        try:
            if self.connected and self._worker:
                if time.time() - getattr(self, "_circuit_t0", 0.0) > 6:
                    self._circuit_t0 = time.time()
                    if not getattr(self, "_circuit_busy", False):
                        self._circuit_busy = True
                        threading.Thread(target=self._circuit_job, daemon=True).start()
        except (RuntimeError, AttributeError):
            pass
        # vigia o openvpn próprio (morreu? avisa no log)
        try:
            self._vpn_poll()
        except (RuntimeError, AttributeError):
            pass
        # banda ao vivo (a cada ~2s, só conectado)
        try:
            self._bw_n = getattr(self, "_bw_n", 0) + 1
            if self.connected and self._bw_n % 4 == 0:
                from .torctl import HAVE_STEM
                if HAVE_STEM:
                    from stem.control import Controller as _Ctl
                    _ctl_port = getattr(getattr(self, "_worker", None), "_ctl_port", 9151)
                    with _Ctl.from_port(port=_ctl_port) as _ctl:
                        _ctl.authenticate()
                        _r = int(_ctl.get_info("traffic/read") or 0)
                        _wr = int(_ctl.get_info("traffic/written") or 0)
                    _prev = getattr(self, "_bw_prev", None)
                    if _prev:
                        self.spark.push(max(0, (_r - _prev[0]) / 2.0),
                                        max(0, (_wr - _prev[1]) / 2.0))
                    self._bw_prev = (_r, _wr)
        except Exception:
            pass
        # rotação automática de IP
        try:
            if self.connected and self.cfg.auto_rotate and self._worker:
                interval = max(60, int(self.cfg.rotate_secs or 600))
                if time.time() - getattr(self, "_rotate_last", 0.0) >= interval:
                    self._rotate_last = time.time()
                    self._push_log(self.tr("rotate_done"))
                    self._new_identity()
            if hasattr(self, "lbl_rotate_count"):
                self.lbl_rotate_count.setText(self._rotate_count_text())
            if hasattr(self, "lbl_sched_next"):
                self.lbl_sched_next.setText(self._sched_next_text())
        except (RuntimeError, AttributeError):
            pass
        try:
            self._sched_check()
        except (RuntimeError, AttributeError):
            pass
        # cauda do tor.log (ou buffer volátil no modo never_store_logs)
        if self._worker:
            if self.cfg.never_store_logs:
                try:
                    for line in self._worker.drain_stdout_lines():
                        line = line.strip()
                        if line:
                            self._push_log(f"[tor] {line[-380:]}")
                except (RuntimeError, AttributeError):
                    pass
            else:
                path = self._worker.tor_log_path()
                if path and os.path.exists(path):
                    try:
                        size = os.path.getsize(path)
                        if size > self._tor_log_off:
                            with open(path, "rb") as f:
                                f.seek(self._tor_log_off)
                                chunk = f.read(min(size - self._tor_log_off, 65536))
                            self._tor_log_off = size
                            for line in chunk.decode("utf-8", "replace").splitlines():
                                line = line.strip()
                                if line:
                                    self._push_log(f"[tor] {line[-380:]}")
                    except OSError:
                        pass
        # auto-cola: bridge nova no clipboard entra sozinha na página Pontes
        try:
            if getattr(self, "_current_page", "") == "bridges" and hasattr(self, "edit_bridges"):
                clip = QApplication.clipboard().text() or ""
                if clip != getattr(self, "_clip_seen", None):
                    self._clip_seen = clip
                    novas = [l for l in bridge_lines_from(clip)
                             if l not in self.edit_bridges.toPlainText()]
                    if novas:
                        cur = self.edit_bridges.toPlainText()
                        if cur and not cur.endswith("\n"):
                            cur += "\n"
                        self.edit_bridges.setPlainText(cur + "\n".join(novas))
                        self._push_log(self.tr("log_pasted", n=len(novas)))
        except (RuntimeError, AttributeError):
            pass
        # drena saída do scanner
        q = getattr(self, "_scan_q", None)
        if q is not None and hasattr(self, "scan_out"):
            try:
                while True:
                    item = q.get_nowait()
                    if item is None:
                        self._scan_q = None
                        if hasattr(self, "_scan_t0"):
                            self._push_log(self.tr("scan_done", s=f"{time.time()-self._scan_t0:.1f}"))
                        break
                    self.scan_out.appendPlainText(item.rstrip("\n"))
            except Exception:
                pass

    # ---------- ações das páginas ----------
    def _save_cfg(self) -> None:
        self.cfg.save()

    def _bridges_toggled(self, v: bool) -> None:
        self.cfg.bridges_enabled = bool(v)
        self.cfg.save()

    def _preset(self, p: str) -> None:
        self.cfg.bridge_preset = p
        if p == "direto":
            self.cfg.bridges_enabled = False
            self.cfg.save()
            self._push_log(self.tr("log_direct"))
            if self.cfg.use_tor:
                self.disconnect_tor(silent=True)
                self.connect_tor()
        else:
            self.cfg.save()
        self.refresh_texts()

    def _paste_bridges(self) -> None:
        txt = QApplication.clipboard().text() or ""
        lines = [l for l in (ln.strip() for ln in txt.splitlines()) if l]
        if not lines:
            self._push_log(self.tr("log_paste_empty"))
            return
        cur = self.edit_bridges.toPlainText()
        if cur and not cur.endswith("\n"):
            cur += "\n"
        self.edit_bridges.setPlainText(cur + "\n".join(lines))
        self._push_log(self.tr("log_pasted", n=len(lines)))

    def _apply_bridges(self) -> None:
        lines = [l.strip() for l in self.edit_bridges.toPlainText().splitlines() if l.strip()]
        if not lines:
            self._push_log(self.tr("log_br_empty"))
            return
        valid = [l for l in lines if bridge_valid(l)]
        if not valid:
            self._push_log(self.tr("log_br_none"))
            return
        if len(valid) != len(lines):
            self._push_log(self.tr("log_br_invalid", n=len(lines) - len(valid)))
        if self.cfg.bridge_preset in ("snowflake", "webtunnel"):
            try:
                from .torctl import TorWorker as _TW
                _w = self._worker or _TW(self.cfg)
                has_pt = bool(_w._pt_line())
            except Exception:
                has_pt = False
            if not has_pt:
                self._push_log(self.tr("log_br_no_pt", p=self.cfg.bridge_preset))
                return
        self.cfg.bridges = valid
        if not self.cfg.bridges_enabled:
            self.cfg.bridges_enabled = True
            self._push_log(self.tr("log_br_auto"))
        self.cfg.save()
        self._push_log(self.tr("log_bridges", n=len(valid), p=self.cfg.bridge_preset))
        self.lbl_br_count.setText(self.tr("br_count", n=len(valid)))
        if self.cfg.use_tor:
            self.disconnect_tor(silent=True)
            self.connect_tor()
        else:
            self._push_log(self.tr("log_br_tor_off"))

    def _kill_toggled(self, v: bool) -> None:
        self.cfg.kill_switch = bool(v)
        self.cfg.save()

    def _autocon_toggled(self, v: bool) -> None:
        self.cfg.auto_connect = bool(v)
        self.cfg.auto_connect_explicit = True
        self.cfg.use_tor = bool(v)
        self.cfg.save()

    def _tor_op(self, what: str) -> None:
        if what == "start_socks":
            self.cfg.socks_enabled = True
            self.cfg.save()
            if self.connected:
                self.socks_running = True
                self._push_log(self.tr("log_socks_on", p=self.cfg.socks_port))
            else:
                self._push_log(self.tr("proxy_stopped"))
        elif what == "stop_socks":
            self.socks_running = False
            self._push_log(self.tr("log_socks_off"))
        elif what == "dns_start":
            self._dns_start()
        elif what == "dns_stop":
            self._dns_stop()
        self.refresh_texts()

    def _upstream_toggled(self, v: bool) -> None:
        self.cfg.upstream_enabled = bool(v)
        self.cfg.save()

    def _upstream_quick(self, key: str, url: str) -> None:
        if key == "direct":
            self.cfg.upstream_enabled = False
        else:
            self.cfg.upstream_enabled = True
            self.cfg.upstream_proxy_url = url
        self.cfg.save()
        self.refresh_texts()

    @staticmethod
    def _redact_proxy_url(url: str) -> str:
        import re as _re
        return _re.sub(r"://([^/@:]+):([^@]*)@", r"://\1:***@", url or "")

    def _upstream_apply(self) -> None:
        self.cfg.upstream_proxy_url = self.edit_upstream.text().strip()
        url = self.cfg.upstream_proxy_url
        if self.cfg.upstream_enabled:
            self._push_log(self.tr("log_up_applied", u=self._redact_proxy_url(url)))
        else:
            self._push_log(self.tr("log_up_applied_direct"))
        self.cfg.save()
        if self.cfg.use_tor:
            self.disconnect_tor(silent=True)
            self.connect_tor()

    def _upstream_testfmt(self) -> None:
        url = self.edit_upstream.text().strip()
        if not url or not (url.startswith("socks4://") or url.startswith("socks5://") or url.startswith("http://")):
            self._push_log(self.tr("log_fmt_bad"))
        elif ":" not in url.split("://", 1)[-1]:
            self._push_log(self.tr("log_fmt_noport"))
        else:
            self._push_log(self.tr("log_fmt_ok", u=self._redact_proxy_url(url)))

    # ---------- DNSCrypt ----------
    def _dns_toggled(self, v: bool) -> None:
        self.cfg.dnscrypt_enabled = bool(v)
        self.cfg.save()
        if not v:
            self._dns_stop()
        elif self.cfg.dnscrypt_mode in ("local", "combined") and (
            self.cfg.dnscrypt_mode == "local" or self.connected
        ):
            self._dns_start()
        self.refresh_texts()

    def _dns_mode(self, mode: str) -> None:
        self.cfg.dnscrypt_mode = mode
        self.cfg.save()
        self.refresh_texts()

    def _dns_browse(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "dnscrypt-proxy", "", "Exe (*.exe);;All (*)")
        if path:
            self.edit_dns_bin.setText(path)
            self.cfg.dnscrypt_bin = path
            self.cfg.save()

    def _dns_toml(self) -> str:
        from .config import app_dirs
        _, data = app_dirs()
        if self.cfg.dnscrypt_config.strip() and os.path.exists(self.cfg.dnscrypt_config.strip()):
            return self.cfg.dnscrypt_config.strip()
        cache = os.path.join(data, "public-resolvers.md").replace("\\", "/")
        toml = f"""server_names = ['cloudflare']
listen_addresses = ['127.0.0.1:{self.cfg.dnscrypt_port}']
max_clients = 50
ipv4_servers = true
ipv6_servers = false
dnscrypt_servers = true
doh_servers = false
require_nolog = true
require_nofilter = true
timeout = 5000
log_level = 2
cert_refresh_delay = 240
[sources]
  [sources.'public-resolvers']
  urls = ['https://raw.githubusercontent.com/DNSCrypt/dnscrypt-resolvers/master/v3/public-resolvers.md']
  minisign_key = 'RWQf6LRCGA9i53mlYecO4IzT51TGPpvWucNSChRY0Q7xn7xBAgzKgerSg'
  cache_file = '{cache}'
  refresh_delay = 72
  prefix = ''
"""
        path = os.path.join(data, "dnscrypt-proxy.toml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(toml)
        return path

    def _dns_start(self) -> None:
        if self.cfg.dnscrypt_mode not in ("local", "combined"):
            self.dns_running = False
            return
        if self.cfg.dnscrypt_mode == "combined" and not self.connected:
            # Combinado exige Tor: conecta primeiro, o stub sobe ao conectar.
            if not self.connecting:
                self.connect_tor()
            return
        exe = self.cfg.dnscrypt_bin.strip()
        import shutil as _sh
        found = exe if exe and os.path.exists(exe) else _sh.which("dnscrypt-proxy")
        if not found:
            self._push_log("✗ dnscrypt-proxy: " + self.tr("dns_bin"))
            return
        try:
            toml = self._dns_toml()
        except OSError as e:
            self._push_log(f"✗ {e}")
            return
        try:
            self._dns_proc = subprocess.Popen(
                [found, "-config", toml], stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as e:
            self._push_log(f"✗ {e}")
            return
        time.sleep(1.0)
        import socket as _s
        ok = False
        for _ in range(10):
            try:
                c = _s.create_connection(("127.0.0.1", self.cfg.dnscrypt_port), timeout=1)
                c.close()
                ok = True
                break
            except OSError:
                time.sleep(0.5)
        if ok:
            self.dns_running = True
            self.dns_addr = f"127.0.0.1:{self.cfg.dnscrypt_port}"
            self._push_log(self.tr("log_dns_on2", a=self.dns_addr))
        else:
            self._dns_stop()
        self.refresh_texts()

    def _dns_stop(self) -> None:
        try:
            if self._dns_proc and self._dns_proc.poll() is None:
                self._dns_proc.terminate()
        except Exception:
            pass
        self._dns_proc = None
        if self.dns_running:
            self._push_log(self.tr("log_dns_off2"))
        self.dns_running = False
        self.dns_addr = ""
        self.refresh_texts()

    def _dns_test(self) -> None:
        if not self.dns_running:
            return
        host = (self.edit_dns_host.text() or "example.com").strip()
        port = self.cfg.dnscrypt_port
        self.lbl_dns_result.setText(self.tr("resolving"))

        def job() -> None:
            try:
                ips = sysprotect.dns_via_stub(host, port)
                self._on_ui(lambda: self.lbl_dns_result.setText(f"✓ {host}: {', '.join(ips)}"))
            except Exception as e:  # noqa: BLE001
                self._on_ui(lambda: self.lbl_dns_result.setText(f"✗ {e}"))
        threading.Thread(target=job, daemon=True).start()

    # ---------- proteção total ----------
    def _toggle_total(self) -> None:
        """Alterna a proteção total (usado pelo KPI clicável)."""
        self._total_toggled(not self.cfg.protect_total)

    def _total_toggled(self, v: bool) -> None:
        if v:
            self.cfg.protect_total = True
            self.cfg.socks_enabled = True
            self.cfg.save()
            if self.connected and self.socks_running:
                self._sysproxy_on()
            else:
                self.pending_protect = True
                if not self.connected:
                    self.connect_tor()
                elif not self.socks_running:
                    self.socks_running = True
                    self._push_log(self.tr("log_socks_on", p=self.cfg.socks_port))
                    self._sysproxy_on()
            # Tudo pelo Tor ou sem internet: bloqueia o resto no firewall.
            if not self.cfg.firewall_on and self.cfg.protect_total:
                if os.name != "nt" and not self.connected:
                    # Linux: sem guardas conhecidos o nft travaria o bootstrap;
                    # aplica após conectar (ver _on_connected).
                    self.pending_fw = True
                else:
                    self._fw_toggled(True)
        else:
            self.cfg.protect_total = False
            self.pending_protect = False
            self.cfg.save()
            prev = self.cfg.prev_proxy
            if isinstance(prev, dict):
                from .config import SysProxy as _SP
                prev = _SP(**prev)
            sysprotect.restore_proxy(prev) if prev else sysprotect.restore_proxy(sysprotect.SysProxy())
            if self.cfg.firewall_on:
                try:
                    sysprotect.firewall_unblock()
                except Exception:
                    pass
                self.cfg.firewall_on = False
                self.cfg.save()
        self.refresh_texts()

    def _sysproxy_on(self) -> None:
        try:
            prev = sysprotect.set_proxy(self.cfg.socks_port)
            self.cfg.prev_proxy = {"enabled": prev.enabled, "server": prev.server, "bypass": prev.bypass}
            self.cfg.save()
            self._push_log(self.tr("w_fw_allowed") if False else f"✓ socks=127.0.0.1:{self.cfg.socks_port}")
        except Exception as e:  # noqa: BLE001
            self._push_log(f"✗ {e}")
            # Rollback total: sem proxy não há proteção total — desliga
            # também o firewall p/ não travar a net com flag apagado.
            self.cfg.protect_total = False
            try:
                sysprotect.firewall_unblock()
            except Exception:
                pass
            self.cfg.firewall_on = False
            self.cfg.save()
            self._push_log(self.tr("total_rollback"))
        self.refresh_texts()

    def _fw_tor_exes(self) -> list:
        """Bins que o kill-switch sempre libera (senão o próprio Tor morre)."""
        out = []
        try:
            from .torctl import tor_bin as _tb, pt_bin as _pb
            cands = [_tb(), _pb("lyrebird"), _pb("conjure")]
            pt = (self.cfg.pt_path or "").split("\n")[0].split("\r")[0].strip().split()
            if pt:
                cands.append(pt[-1])
            for p in cands:
                if p and os.path.exists(p) and p not in out:
                    out.append(p)
        except Exception:
            pass
        return out

    def _fw_toggled(self, v: bool) -> None:
        extras_base = self._fw_tor_exes()
        if self.dns_running and self.cfg.dnscrypt_bin.strip():
            extras_base.append(self.cfg.dnscrypt_bin.strip())
        extras_base += [e for e in getattr(self, "vpn_exes", []) if e.strip()]

        def job(on: bool, extras: list) -> None:
            outcome = {"ok": True, "kind": "ok", "detail": ""}
            try:
                if on:
                    sysprotect.firewall_block(";".join(extras))
                    sysprotect.firewall_block(";".join(extras))
                    outcome.update(ok=True, kind="on", detail=str(len(extras)))
                else:
                    sysprotect.firewall_unblock()
                    outcome.update(ok=True, kind="off")
            except PermissionError:
                outcome.update(ok=False, kind="noadmin")
            except Exception as e:  # noqa: BLE001
                outcome.update(ok=False, kind="err", detail=f"✗ {e}"[:300])

            def _apply() -> None:
                try:
                    if outcome["kind"] == "on":
                        if not self.cfg.protect_total:
                            # Usuário desligou (ou rollback) enquanto o job rodava:
                            # desfaz em vez de deixar meio-ligado.
                            try:
                                sysprotect.firewall_unblock()
                            except Exception:
                                pass
                            self.cfg.firewall_on = False
                        else:
                            self.cfg.firewall_on = True
                            if outcome["detail"] not in ("", "0"):
                                self._push_log(self.tr("fw_vpn_extra", n=outcome["detail"]))
                    elif outcome["kind"] == "off":
                        self.cfg.firewall_on = False
                    elif outcome["kind"] == "noadmin":
                        self._push_log(self.tr("fw_noadmin"))
                        self.cfg.firewall_on = False
                    else:
                        self._push_log(outcome["detail"])
                    self.cfg.save()
                    self.refresh_texts()
                except (RuntimeError, AttributeError):
                    pass
                    self._on_ui(_apply)
        threading.Thread(target=job, args=(bool(v), list(extras_base)), daemon=True).start()

    def _render_apps(self) -> None:
        from .widgets import ToggleSwitch
        lay = self.apps_box
        # limpa tudo (widgets)
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        for i, a in enumerate(self.cfg.apps):
            name = a["name"] if isinstance(a, dict) else a.name
            path = a["path"] if isinstance(a, dict) else a.path
            en = a["enabled"] if isinstance(a, dict) else a.enabled
            custom = a["custom"] if isinstance(a, dict) else a.custom
            tgl = ToggleSwitch()
            tgl.setChecked(bool(en))
            tgl.toggled.connect(lambda v, idx=i: self._app_enabled(idx, v))
            lay.addWidget(tgl, i, 0)
            lab = QLabel(f"<b>{name}</b><br><small>{path[-60:]}</small><br>"
                         f"<small>⇄ SOCKS 127.0.0.1:{sysprotect.app_socks_port(i)}</small>")
            lab.setObjectName("appLbl")
            lab.setToolTip(sysprotect.expand(path))
            lay.addWidget(lab, i, 1)
            if custom:
                btnx = QPushButton("✕")
                btnx.setObjectName("miniDanger")
                btnx.setFixedWidth(32)
                btnx.setCursor(Qt.CursorShape.PointingHandCursor)
                btnx.clicked.connect(lambda _=False, idx=i: self._app_del(idx))
                lay.addWidget(btnx, i, 3)
            btno = QPushButton(self.tr("apps_open"))
            btno.clicked.connect(lambda _=False, idx=i: self._app_open_idx(idx))
            btno.setEnabled(self.socks_running and bool(en))
            btno.setMinimumWidth(120)
            lay.addWidget(btno, i, 2)

    def _app_enabled(self, i: int, v: bool) -> None:
        try:
            a = self.cfg.apps[i]
            if isinstance(a, dict):
                a["enabled"] = bool(v)
            else:
                a.enabled = bool(v)
            self.cfg.save()
        except IndexError:
            pass

    def _app_del(self, i: int) -> None:
        try:
            del self.cfg.apps[i]
            self.cfg.save()
            self._render_apps()
        except IndexError:
            pass

    def _app_open(self, path: str) -> None:
        try:
            how = sysprotect.launch_with_proxy(path, self.cfg.socks_port)
            name = os.path.splitext(os.path.basename(sysprotect.expand(path)))[0]
            self._push_log(self.tr("log_app_how", n=name, m=how))
        except Exception as e:  # noqa: BLE001
            self._push_log(f"✗ {e}"[:300])

    def _app_open_idx(self, i: int) -> None:
        """Abre o app na sua porta SOCKS dedicada (circuito próprio)."""
        try:
            a = self.cfg.apps[i]
        except IndexError:
            return
        en = a.get("enabled", True) if isinstance(a, dict) else getattr(a, "enabled", True)
        path = a.get("path", "") if isinstance(a, dict) else getattr(a, "path", "")
        name = a.get("name", "?") if isinstance(a, dict) else getattr(a, "name", "?")
        if not en:
            self._push_log(self.tr("app_disabled", n=name))
            return
        try:
            how = sysprotect.launch_with_proxy(
                path, sysprotect.app_socks_port(i))
            self._push_log(self.tr("log_app_how", n=f"{name} (:{sysprotect.app_socks_port(i)})", m=how))
        except Exception as e:  # noqa: BLE001
            self._push_log(f"✗ {e}"[:300])

    def _apps_msg(self, key: str, ok: bool = False) -> None:
        self.lbl_apps_msg.setText(("✓ " if ok else "✗ ") + self.tr(key))
        self.lbl_apps_msg.setStyleSheet(
            "color:#047857; background:#ecfdf5; border:1px solid #a7f3d0; "
            "border-radius:8px; padding:7px 10px;" if ok else
            "color:#b91c1c; background:#fef2f2; border:1px solid #fecaca; "
            "border-radius:8px; padding:7px 10px;")
        self.lbl_apps_msg.setVisible(True)

    def _app_add(self) -> None:
        raw = self.edit_app_path.text().strip().strip('"').strip("'")
        if not raw:
            self._apps_msg("apps_err_empty")
            return
        real = os.path.abspath(os.path.expanduser(os.path.expandvars(raw)))
        if not os.path.isfile(real):
            self._apps_msg("apps_err_notfound")
            return
        p = sysprotect.portable(real)
        if any((a["path"] if isinstance(a, dict) else a.path) == p for a in self.cfg.apps):
            self.edit_app_path.clear()
            self._apps_msg("apps_dup")
            return
        name = os.path.splitext(os.path.basename(real))[0]
        self.cfg.apps.append({"name": name, "path": p, "enabled": True, "custom": True})
        self.cfg.save()
        self._push_log(self.tr("log_app_added", p=p))
        self.edit_app_path.clear()
        self._apps_msg("apps_ok_added", ok=True)
        self.refresh_texts()

    # ---------- logs ----------
    def _render_logs(self) -> None:
        if not hasattr(self, "log_view"):
            return
        f = self.edit_filter.text().lower() if hasattr(self, "edit_filter") else ""
        lines = self.log_lines if not f else [l for l in self.log_lines if f in l.lower()]
        self.log_view.setPlainText("\n".join(lines[-400:]))
        if not self._log_paused:
            sb = self.log_view.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _copy_log(self) -> None:
        QApplication.clipboard().setText("\n".join(self.log_lines))
        self._push_log(self.tr("log_copied"))

    def _clear_log(self) -> None:
        self.log_lines.clear()
        self._push_log(self.tr("log_cleared"))

    def _nolog_toggled(self, v: bool) -> None:
        """Liga/desliga 'Nunca armazenar logs' (vale na próxima conexão)."""
        self.cfg.never_store_logs = bool(v)
        self.cfg.save()
        if v:
            try:
                path = self._worker.tor_log_path() if self._worker else ""
            except (RuntimeError, AttributeError):
                path = ""
            if path and os.path.exists(path) and not self.connected:
                from PyQt6.QtWidgets import QMessageBox
                ans = QMessageBox.question(
                    self, "Anonymous Shield", self.tr("log_never_ask"),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ans == QMessageBox.StandardButton.Yes:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        try:
            self.refresh_texts()
        except (RuntimeError, AttributeError):
            pass

    # ---------- diagnóstico ----------
    def _test_tor(self) -> None:
        if not self.connected or not self._worker:
            return
        tgt = self.edit_target.text().strip() or "check.torproject.org:80"
        tgt = tgt[:253]
        self.lbl_result.setText(self.tr("testing"))
        threading.Thread(target=self._worker.test_target, args=(tgt,), daemon=True).start()

    def _e2e_run(self) -> None:
        """Teste ponta a ponta no app: saída IsTor + DNS + proxy."""
        if not self.connected:
            self.lbl_result.setText(self.tr("e2e_need"))
            return
        self.lbl_result.setText(self.tr("e2e_run"))
        port = self.cfg.socks_port

        def job() -> None:
            lines = []
            try:
                import requests
                p = f"socks5h://127.0.0.1:{port}"
                j = requests.get("https://check.torproject.org/api/ip",
                                 proxies={"http": p, "https": p},
                                 timeout=40).json()
                ok = bool(j.get("IsTor", False))
                lines.append(("✓ " if ok else "✗ ")
                             + self.tr("e2e_exit", ip=j.get("IP", "?")))
            except Exception as e:  # noqa: BLE001
                lines.append("✗ " + self.tr("e2e_exit_fail"))
                lines.append(f"✗ {e}"[:160])
            try:
                if self.cfg.protect_total:
                    lines.append(("✓ " if sysprotect.is_our_proxy(port)
                                  else "✗ ") + self.tr("e2e_proxy"))
            except Exception:
                pass
            try:
                if self.dns_running and self.dns_addr:
                    lines.append("✓ " + self.tr("e2e_dns", a=self.dns_addr))
            except Exception:
                pass
            txt = "\n".join(lines)
            self._push_log(txt)
            self._on_ui(lambda: self.lbl_result.setText(txt))
        threading.Thread(target=job, daemon=True).start()

    def _test_net(self) -> None:
        self.lbl_result.setText(self.tr("testing_net"))
        try:
            for _t, _v, _s in self.net_cards.values():
                _v.setText("…")
                _s.setText("")
                _v.setStyleSheet("font-size: 15px;")
        except (RuntimeError, AttributeError):
            pass

        def job() -> None:
            try:
                d = sysprotect.test_direct_net_full()
            except Exception as e:  # noqa: BLE001
                d = {"text": f"✗ {e}"[:300]}
            self._on_ui(lambda: self._paint_net(d))
        threading.Thread(target=job, daemon=True).start()

    def _paint_net(self, d: dict) -> None:
        """Pinta os 3 cards (DNS/TCP/HTTP) + texto técnico abaixo."""
        try:
            T = self.tr
            titles = {"dns": T("net_dns"), "tcp": T("net_tcp"), "http": T("net_http")}
            vals = {
                "dns": (d.get("dns_ok", False), d.get("dns_ip", "") or "",
                        d.get("dns_ms")),
                "tcp": (d.get("tcp_ok", False), "443",
                        d.get("tcp_ms")),
                "http": (d.get("http_ok", False),
                         f"HTTP {d.get('http_code', '')}".strip(),
                         d.get("http_ms")),
            }
            for cid, (_t, _v, _s) in self.net_cards.items():
                ok, sub, ms = vals[cid]
                _t.setText(titles[cid])
                _v.setText(T("net_ok") if ok else T("net_fail"))
                _v.setStyleSheet("font-size: 15px; font-weight: 800; color: %s;"
                                 % ("#10b981" if ok else "#ef4444"))
                tail = []
                if sub:
                    tail.append(str(sub))
                if isinstance(ms, (int, float)):
                    tail.append(f"{ms:.0f} ms")
                _s.setText(" · ".join(tail))
            self.lbl_result.setText(d.get("text", ""))
        except (RuntimeError, AttributeError):
            pass

    def _wipe(self) -> None:
        self.lbl_result.setText(self.tr("wiping"))
        self.cfg.use_tor = True
        self.cfg.save()
        self.disconnect_tor(silent=True)

        def job() -> None:
            if self._worker:
                msg = self._worker.wipe_data()
            else:
                w = TorWorker(self.cfg)
                msg = w.wipe_data()

            def _done() -> None:
                try:
                    self.lbl_result.setText(msg)
                except (RuntimeError, AttributeError):
                    pass
                if self.cfg.use_tor:
                    self.connect_tor()
            self._on_ui(_done)
        threading.Thread(target=job, daemon=True).start()

    # ---------- update ----------
    def _show_licenses(self) -> None:
        from PyQt6.QtWidgets import QComboBox, QDialog, QPlainTextEdit, QVBoxLayout
        files = sysprotect.license_files()
        d = QDialog(self)
        d.setWindowTitle(self.tr("about_title"))
        d.resize(640, 480)
        lay = QVBoxLayout(d)
        combo = QComboBox()
        for label, path in files:
            combo.addItem(label, path)
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setStyleSheet("font-family: monospace; font-size: 11px;")

        def _load(i: int) -> None:
            try:
                view.setPlainText(sysprotect.read_license(combo.itemData(i)))
            except (RuntimeError, AttributeError):
                pass

        combo.currentIndexChanged.connect(_load)
        lay.addWidget(combo)
        lay.addWidget(view, 1)
        _load(0)
        d.exec()

    def _lic_load(self, i: int = 0) -> None:
        """Carrega o texto da licença selecionada na página Sobre."""
        try:
            self.view_lic.setPlainText(sysprotect.read_license(self.combo_lic.itemData(i)))
        except (RuntimeError, AttributeError):
            pass

    def _rt_about(self) -> None:
        if not hasattr(self, "combo_lic"):
            return
        T = self.tr
        ver, tv = __version__, sysprotect.tor_version()
        self.lbl_about2_title.setText(T("about_title"))
        self.lbl_about2_ver.setText(f"Anonymous Shield v{ver} · Tor {tv}")
        self.lbl_about2_text.setText(T("about_text", v=ver, t=tv))
        self.lbl_about2_lic.setText(T("about_licenses"))
        self.lbl_about2_gpl.setText(T("about_gpl"))
        cur = self.combo_lic.currentIndex()
        self.combo_lic.blockSignals(True)
        self.combo_lic.clear()
        for label, path in sysprotect.license_files():
            self.combo_lic.addItem(label, path)
        self.combo_lic.blockSignals(False)
        self.combo_lic.setCurrentIndex(cur if cur >= 0 else 0)
        self._lic_load(self.combo_lic.currentIndex())

    def _upd_check(self) -> None:
        import re as _re
        from .config import UPDATE_REPO_OFFICIAL as _OFF
        repo = _re.sub(r"[^A-Za-z0-9_.\-/]", "", self.edit_repo.text().strip()
                       or self.cfg.update_repo.strip())
        if repo.lower() != _OFF.lower():
            # Campo travado: qualquer divergência (edição manual do config)
            # volta sozinha p/ o oficial, com aviso.
            self.cfg.update_repo = _OFF
            self.cfg.save()
            try:
                self.edit_repo.setText(_OFF)
            except (RuntimeError, AttributeError):
                pass
            self._push_log(self.tr("upd_repo_locked"))
        repo = _OFF
        old = self.cfg.update_repo.strip()
        if old and repo.lower() != old.lower():
            # Repositório trocado: confirmação explícita (anti-redirecionamento).
            from PyQt6.QtWidgets import QMessageBox
            ans = QMessageBox.question(
                self, "Anonymous Shield",
                self.tr("upd_repo_changed", a=old, b=repo),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ans != QMessageBox.StandardButton.Yes:
                self.edit_repo.setText(old)
                return
        self.cfg.update_repo = repo
        self.cfg.save()
        if not _re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo or ""):
            self.lbl_upd_status.setText(self.tr("upd_none"))
            return
        self.lbl_upd_status.setText(self.tr("testing"))
        threading.Thread(target=self._upd_job, args=(repo,), daemon=True).start()

    def _upd_proxies(self) -> dict | None:
        if self.connected:
            p = f"socks5h://127.0.0.1:{self.cfg.socks_port}"
            return {"http": p, "https": p}
        return None

    def _upd_job(self, repo: str) -> None:
        import requests
        try:
            proxies = self._upd_proxies()
            r = requests.get(f"https://api.github.com/repos/{repo}/releases/latest",
                             headers={"User-Agent": f"AnonymousShield/{__version__}", "Accept": "application/vnd.github+json"},
                             proxies=proxies, timeout=25)
            if r.status_code != 200:
                self._on_ui(lambda: self.lbl_upd_status.setText(self.tr("upd_none")))
                return
            j = r.json()
            payload = {
                "tag": str(j.get("tag_name", "?")),
                "notes": str(j.get("body", ""))[:600],
                "assets": [(str(a.get("name", "?")), str(a.get("browser_download_url", "")))
                           for a in (j.get("assets") or [])[:8]
                           if isinstance(a, dict)],
            }
            payload["sums"] = self._upd_fetch_sums(j.get("assets") or [])
        except Exception as e:  # noqa: BLE001
            err = f"✗ {e}"[:300]
            self._on_ui(lambda: self.lbl_upd_status.setText(err))
            return

        def _apply() -> None:
            try:
                tag, notes = payload["tag"], payload["notes"]
                cur = [int(x) for x in __version__.split(".")]
                lat = [int("".join(c for c in x if c.isdigit()) or 0) for x in tag.lstrip("v").split(".")]
                self.lbl_upd_status.setText(
                    self.tr("upd_current", cur=__version__, lat=tag) + "\n" + self.tr("upd_notes") + "\n" + notes)
                for i in reversed(range(self.upd_assets.count())):
                    w = self.upd_assets.takeAt(i).widget()
                    if w:
                        w.deleteLater()
                self._upd_sums = payload["sums"]
                for name, url in payload["assets"]:
                    row = QHBoxLayout()
                    lab = QLabel(name)
                    lab.setStyleSheet("font-family: monospace;")
                    btn = QPushButton(self.tr("upd_download"))
                    btn.setObjectName("accent")
                    btn.clicked.connect(lambda _=False, n=name, u=url: self._upd_dl(n, u))
                    row.addWidget(lab, 1)
                    row.addWidget(btn)
                    if name.lower().endswith(".exe"):
                        ap = QPushButton(self.tr("upd_apply"))
                        ap.setObjectName("success")
                        ap.clicked.connect(lambda _=False, n=name: self._upd_apply(n))
                        row.addWidget(ap)
                    self.upd_assets.addLayout(row)
                if tag.lstrip("v") != __version__ and lat > cur:
                    self.lbl_upd_status.setText("⬆ " + self.lbl_upd_status.text())
                else:
                    self._push_log(self.tr("upd_uptodate"))
            except (RuntimeError, AttributeError):
                pass
        self._on_ui(_apply)

    def _upd_dl(self, name: str, url: str) -> None:
        import requests
        if os.name != "nt" and not (getattr(self, "_upd_sums", {}) or {}).get(os.path.basename(name), ""):
            # Linux não tem Authenticode: sem checksum publicado, nem baixa.
            self.lbl_upd_status.setText(self.tr("upd_sha_required"))
            self._push_log(self.tr("upd_sha_required"))
            return
        threading.Thread(target=self._upd_dl_job, args=(name, url, None), daemon=True).start()

    def _upd_apply(self, name: str) -> None:
        """Troca o exe em uso pelo baixado+verificado e reinicia (só frozen)."""
        import subprocess as _sp
        import sys as _sys
        if not getattr(_sys, "frozen", False):
            self.lbl_upd_status.setText(self.tr("upd_nofrozen"))
            return
        base = os.path.basename(name)
        if base not in getattr(self, "_upd_verified", set()):
            self.lbl_upd_status.setText(self.tr("upd_unverified"))
            return
        try:
            from .config import app_dirs
            _, data = app_dirs()
            src = os.path.join(data, base)
            if not os.path.exists(src):
                self.lbl_upd_status.setText(self.tr("upd_noupdate"))
                return
            dst = os.path.abspath(_sys.argv[0])
            bat = os.path.join(data, "update-apply.bat")
            with open(bat, "w", encoding="utf-8") as f:
                f.write("@echo off\n"
                        "set PID=%~1\nset SRC=%~2\nset DST=%~3\n"
                        ":wait\n"
                        'tasklist /FI "PID eq %PID%" 2>nul | find "%PID%" >nul\n'
                        "if %errorlevel%==0 (timeout /t 1 /nobreak >nul & goto wait)\n"
                        'move /Y "%SRC%" "%DST%" >nul\n'
                        'start "" "%DST%"\n'
                        'del "%~f0"\n')
            sig = sysprotect.authenticode(src)
            if sig == "bad":
                self.lbl_upd_status.setText(self.tr("upd_sig_bad"))
                return
            pid = str(os.getpid())
            _sp.Popen([os.environ.get("COMSPEC", "cmd.exe"), "/c", bat, pid, src, dst],
                      close_fds=False,
                      creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0)
                      | getattr(_sp, "DETACHED_PROCESS", 0))
            self.lbl_upd_status.setText(self.tr("upd_applying"))
            self._push_log(self.tr("upd_applying"))
            QApplication.instance().quit()
        except Exception as e:  # noqa: BLE001
            self.lbl_upd_status.setText(f"✗ {e}"[:300])

    def _upd_dl_url(self) -> None:
        import re as _re
        url = self.edit_upd_url.text().strip()
        if not url.lower().startswith(("http://", "https://")):
            self.lbl_upd_status.setText(self.tr("upd_bad_url"))
            return
        sha = _re.sub(r"\s+", "", self.edit_upd_sha.text().strip()).lower()
        if not _re.fullmatch(r"[0-9a-f]{64}", sha or ""):
            self.lbl_upd_status.setText(self.tr("upd_bad_sha"))
            return
        name = url.split("?")[0].rstrip("/").rsplit("/", 1)[-1] or "download.bin"
        self.lbl_upd_status.setText(self.tr("testing"))
        threading.Thread(target=self._upd_dl_job, args=(name, url, sha or None),
                         daemon=True).start()

    def _upd_fetch_sums(self, assets: list) -> dict:
        """Baixa asset de checksum (se publicado) → {arquivo: sha256hex}."""
        import re as _re

        sums: dict[str, str] = {}
        cands = [a for a in assets
                 if isinstance(a, dict)
                 and _re.search(r"sha-?256|sums?|checksum", str(a.get("name", "")), _re.I)
                 and a.get("browser_download_url")]
        if not cands:
            return sums
        import requests
        try:
            r = requests.get(cands[0]["browser_download_url"], timeout=25,
                             proxies=self._upd_proxies(),
                             headers={"User-Agent": f"AnonymousShield/{__version__}"})
            r.raise_for_status()
            for line in r.text.splitlines():
                m = _re.match(r"\s*([0-9a-fA-F]{64})\s+\*?(\S+)\s*$", line)
                if m:
                    sums[m.group(2).strip()] = m.group(1).lower()
        except Exception:
            pass
        return sums

    def _upd_dl_job(self, name: str, url: str, expect_sha: str | None = None) -> None:
        import hashlib as _hl
        import requests
        try:
            from .config import app_dirs
            _, data = app_dirs()
            dest = os.path.join(data, os.path.basename(name))
            with requests.get(url, stream=True, timeout=60,
                              headers={"User-Agent": f"AnonymousShield/{__version__}"}) as r:
                r.raise_for_status()
                h = _hl.sha256()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(1024 * 256):
                        f.write(chunk)
                        h.update(chunk)
            digest = h.hexdigest()
            expect = expect_sha or (getattr(self, "_upd_sums", {}) or {}).get(os.path.basename(name), "")
            if expect and digest.lower() != expect.lower():
                try:
                    os.remove(dest)
                except OSError:
                    pass

                def _bad() -> None:
                    try:
                        self.lbl_upd_status.setText(self.tr("upd_bad_hash"))
                    except (RuntimeError, AttributeError):
                        pass
                self._push_log(self.tr("upd_bad_hash"))
                self._on_ui(_bad)
                return
            if expect:
                try:
                    self._upd_verified.add(os.path.basename(name))
                except (RuntimeError, AttributeError):
                    pass
            tail = "\n" + (self.tr("upd_verified") if expect else self.tr("upd_nosums"))
            sig = sysprotect.authenticode(dest)
            if sig == "valid":
                tail += "\n" + self.tr("upd_sig_valid")
            elif sig == "bad":
                tail += "\n" + self.tr("upd_sig_bad")
            elif sig == "none":
                tail += "\n" + self.tr("upd_sig_none")
            final = self.tr("upd_downloaded", p=dest) + tail

            def _ok() -> None:
                try:
                    self.lbl_upd_status.setText(final)
                except (RuntimeError, AttributeError):
                    pass
            self._on_ui(_ok)
        except Exception as e:  # noqa: BLE001
            err = f"✗ {e}"[:300]

            def _fail() -> None:
                try:
                    self.lbl_upd_status.setText(err)
                except (RuntimeError, AttributeError):
                    pass
            self._on_ui(_fail)

    # ---------- scanner ----------
    def _scan_engine(self) -> tuple[str, str]:
        import shutil
        for cand in (shutil.which("nmap"),
                     r"C:\Program Files (x86)\Nmap\nmap.exe",
                     r"C:\Program Files\Nmap\nmap.exe"):
            if cand and os.path.exists(cand):
                return cand, f"nmap ({cand})"
        return "", self.tr("scan_no_nmap")

    @staticmethod
    def _scan_clean(s: str, keep: str = "", limit: int = 500) -> str:
        s = (s or "").replace("\n", " ").replace("\r", " ").strip()[:limit]
        if keep:
            s = "".join(c for c in s if c.isalnum() or c in keep)
        return s

    def _scan_ports_flag(self) -> list:
        spec = (self.edit_scan_ports.text() or "").strip().lower()
        if not spec:
            return ["-F"]
        if spec in ("all", "-p-", "tudo", "todas", "todo"):
            return ["-p-"]
        clean = self._scan_clean(spec, keep="0123456789TU,:-. ")
        return ["-p", clean] if clean else ["-F"]

    def _scan_build_cmd(self, target: str) -> tuple:
        """Monta o comando nmap a partir dos controles. Retorna (cmd, outpath)."""
        import re as _re
        nmap, _ = self._scan_engine()
        if not nmap:
            return None, None
        via_tor = self.chk_scan_tor.isChecked()
        if via_tor:
            return None, None
        cmd = [nmap]
        ty = self.SCAN_TYPES[self.combo_scan_type.currentIndex()]
        if ty:
            cmd.append(ty)
        cmd += self._scan_ports_flag()
        disc = self.SCAN_DISC[self.combo_scan_disc.currentIndex()]
        if self.chk_scan_noping.isChecked():
            disc = "-Pn"
        if disc:
            cmd.append(disc)
        if self.chk_scan_aggr.isChecked():
            cmd.append("-A")
        else:
            if self.chk_scan_sv.isChecked():
                cmd.append("-sV")
            if self.chk_scan_os.isChecked():
                cmd.append("-O")
            if self.chk_scan_reason.isChecked():
                cmd.append("--reason")
        tm = self.SCAN_TEMPO[self.combo_scan_timing.currentIndex()]
        if tm:
            cmd.append("-T" + tm)
        if self.chk_scan_frag.isChecked():
            cmd.append("-f")
        decoy = self._scan_clean(self.edit_scan_decoy.text(), keep="0123456789., RNDrnd")
        if decoy:
            cmd += ["-D", decoy]
        scripts = self._scan_clean(self.edit_scan_scripts.text())
        if scripts:
            cmd.append("--script=" + scripts)
        sargs = self._scan_clean(self.edit_scan_script_args.text())
        if sargs:
            cmd.append("--script-args=" + sargs)
        if self.chk_scan_open.isChecked() and disc != "-sn":
            cmd.append("--open")
        if ":" in target and not target.startswith("["):
            cmd.append("-6")
        outpath = None
        outfmt = self.SCAN_OUT[self.combo_scan_out.currentIndex()]
        if outfmt != "none":
            from .config import app_dirs as _ad
            _, data = _ad()
            ext = {"oN": "nmap", "oX": "xml", "oG": "gnmap"}[outfmt]
            safe = _re.sub(r"[^A-Za-z0-9_.-]", "_", target)[:60] or "alvo"
            outpath = os.path.join(
                data, f"scan-{safe}-{time.strftime('%Y%m%d-%H%M%S')}.{ext}")
            cmd.append(f"-{outfmt}")
            cmd.append(outpath)
        extra = self.edit_scan_args.text().strip()
        if extra:
            import re as _re2
            toks = self._scan_clean(extra).split()
            bad = {"-oN", "-oX", "-oG", "-oA", "--script", "-iL", "-iR", "--datadir"}
            if not any(t.split("=")[0] in bad for t in toks):
                cmd += toks
        cmd.append(target)
        return cmd, outpath

    def _scan_preview(self) -> None:
        try:
            target = (self.edit_scan_target.text() or "").strip() or "<alvo>"
            cmd, _ = self._scan_build_cmd(target)
            if cmd is None:
                if self.chk_scan_tor.isChecked():
                    self.lbl_scan_cmd.setText(self.tr("scan_preview_tor"))
                else:
                    self.lbl_scan_cmd.setText(self.tr("scan_preview_builtin"))
            else:
                self.lbl_scan_cmd.setText("$ " + " ".join(cmd))
            # aviso de admin p/ SYN/UDP/OS
            need_root = (self.combo_scan_type.currentIndex() in (1, 3)
                         or self.chk_scan_os.isChecked()
                         or self.chk_scan_aggr.isChecked())
            show = bool(need_root and not sysprotect.is_admin())
            self.lbl_scan_admin.setVisible(show)
            if show:
                self.lbl_scan_admin.setText(self.tr("scan_admin_note"))
                self.lbl_scan_admin.setStyleSheet(
                    "color:#b45309; background:#fef3c7; border-radius:8px; padding:6px;")
        except (RuntimeError, AttributeError):
            pass

    def _scan_run(self) -> None:
        target = self.edit_scan_target.text().strip()
        if not target:
            return
        target = target[:253]
        self._scan_stop_proc()
        import queue
        self._scan_q = queue.Queue()
        self.scan_out.clear()
        self._scan_t0 = time.time()
        self._push_log(self.tr("scan_running", t=target))
        prof = self.combo_scan.currentIndex()
        via_tor = self.chk_scan_tor.isChecked()
        nmap, _ = self._scan_engine()
        if nmap and not via_tor:
            cmd, outpath = self._scan_build_cmd(target)
            if cmd is None:
                return
            self._scan_q.put("$ " + " ".join(cmd) + "\n")
            if outpath:
                self._scan_q.put(self.tr("scan_outfile", p=outpath) + "\n")
            threading.Thread(target=self._scan_nmap_job, args=(cmd,), daemon=True).start()
        else:
            if via_tor and not self.connected:
                self._scan_q.put("✗ Tor off\n")
                return
            ports_text = self.edit_scan_ports.text().strip()
            args = self.edit_scan_args.text().strip()
            threading.Thread(
                target=self._scan_builtin_job,
                args=(target, prof, via_tor, ports_text, args), daemon=True).start()

    def _scan_nmap_job(self, cmd: list) -> None:
        import subprocess as _sp
        try:
            self._scan_proc = _sp.Popen(
                cmd, stdout=_sp.PIPE, stderr=_sp.STDOUT, text=True,
                creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0))
            if self._scan_proc.stdout is None:
                return
            for line in self._scan_proc.stdout:
                if hasattr(self, "_scan_q"):
                    self._scan_q.put(line)
            self._scan_proc.wait()
        except Exception as e:  # noqa: BLE001
            if hasattr(self, "_scan_q"):
                self._scan_q.put(f"✗ {e}\n")
        finally:
            self._scan_proc = None
            if hasattr(self, "_scan_q"):
                self._scan_q.put(None)

    TOP_PORTS = (21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
                 993, 995, 1723, 3306, 3389, 5900, 8080, 8443, 8000, 8888,
                 1433, 1521, 5432, 6379, 27017, 631, 515, 1720, 5060, 5061,
                 119, 563, 587, 465, 993, 995, 1080, 3128, 8008, 8081, 8888,
                 9000, 9090, 10000, 5000, 7000, 47808, 7547, 2323, 23, 69,
                 123, 161, 162, 389, 636, 2049, 111, 2049, 33060, 5985, 5986,
                 47001, 49152, 62078, 8082, 8181, 8444, 8880, 9001, 9030, 9050,
                 9150, 9051, 9151, 1080, 9050, 1080)

    def _scan_builtin_job(self, target: str, prof: int, via_tor: bool,
                            ports_text: str = "", args: str = "") -> None:
        import socket as _s
        q = self._scan_q
        host = target.split("/")[0].strip("[]")
        try:
            rhost = _s.gethostbyaddr(host)[0]
        except OSError:
            rhost = "?"
        q.put(f"# {host} ({rhost}) via={'Tor' if via_tor else 'direto'}\n")
        if via_tor and not tor_reachable_host(host):
            q.put(self.tr("scan_tor_local") + "\n")
            q.put(None)
            return
        if prof == 4:
            # ping sweep simplificado: tenta 80/443 no /24
            base = ".".join(host.split(".")[:3]) if host[0].isdigit() else None
            addrs = [f"{base}.{i}" for i in (1, 254)] if base else [host]
        elif (ports_text or "").strip().lower() in ("all", "-p-", "tudo", "todas", "todo"):
            ports = list(range(1, 1025))
        elif (ports_text or "").strip():
            ports = self._parse_ports(ports_text)
        elif prof == 2:
            ports = list(range(1, 1025))
        elif args and prof == 5:
            ports = self._parse_ports(args)
        else:
            ports = list(dict.fromkeys(self.TOP_PORTS))
        t0 = time.time()
        open_n = 0

        def probe(port: int):
            try:
                if via_tor:
                    import socks as _socks
                    s = _socks.socksocket()
                    s.set_proxy(_socks.SOCKS5, "127.0.0.1", self.cfg.socks_port, True)
                else:
                    s = _s.socket(_s.AF_INET, _s.SOCK_STREAM)
                s.settimeout(2.5)
                s.connect((host, port))
                try:
                    s.settimeout(2.0)
                    banner = s.recv(256).decode("utf-8", "replace").strip().split("\n")[0][:80]
                except OSError:
                    banner = ""
                s.close()
                return port, True, banner
            except OSError:
                return port, False, ""

        from concurrent.futures import ThreadPoolExecutor
        total = len(ports) if prof != 4 else len(addrs)
        if prof == 4:
            for a in addrs:
                ok = False
                for p in (80, 443):
                    _, is_open, _ = probe_host(a, p, via_tor, self.cfg.socks_port)
                    if is_open:
                        ok = True
                        break
                q.put(f"{'🟢' if ok else '🔴'} {a}\n")
            q.put(None)
            return
        done = 0
        with ThreadPoolExecutor(max_workers=60) as ex:
            for port, is_open, banner in ex.map(probe, ports):
                done += 1
                if is_open:
                    open_n += 1
                    svc = self._svc_name(port)
                    q.put(f"🟢 {port}/tcp  {svc}  {banner}\n".rstrip() + "\n")
                if done % 200 == 0:
                    q.put(f"… {done}/{total}\n")
        q.put(f"\n# {open_n} aberta(s) em {time.time()-t0:.1f}s\n")
        q.put(None)

    @staticmethod
    def _parse_ports(args: str) -> list:
        ports: set = set()
        for tok in args.replace(",", " ").split():
            if tok.startswith("-p"):
                tok = tok[2:]
            if "-" in tok and tok[0].isdigit():
                a, _, b = tok.partition("-")
                try:
                    ports.update(range(max(1, int(a)), min(65535, int(b)) + 1))
                except ValueError:
                    pass
            else:
                try:
                    ports.add(int(tok))
                except ValueError:
                    pass
        return sorted(ports)[:2000] or [80, 443]

    @staticmethod
    def _svc_name(port: int) -> str:
        try:
            return socket.getservbyport(port, "tcp")
        except OSError:
            return "?"

    def _scan_stop_proc(self) -> None:
        proc = getattr(self, "_scan_proc", None)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        self._scan_proc = None

    def _scan_stop(self) -> None:
        self._scan_stop_proc()
        if hasattr(self, "_scan_q"):
            self._scan_q.put(self.tr("scan_stopped") + "\n")
            self._scan_q.put(None)

    def _scan_save(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "scan", "scan.txt", "Text (*.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.scan_out.toPlainText())
                self._push_log(self.tr("scan_saved", p=path))
            except OSError as e:
                self._push_log(f"✗ {e}")

    # ---------- menu/geral ----------
    def _save_cfg(self) -> None:
        self.cfg.save()

    def open_data_folder(self) -> None:
        from .config import app_dirs
        _, data = app_dirs()
        QDesktopServices.openUrl(QUrl.fromLocalFile(data))
        self._push_log(self.tr("log_data_opened", p=data))

    def restore_internet(self) -> None:
        """Botão de emergência: volta a internet ao padrão (pré-Anonymous Shield).

        Restaura o proxy anterior (ou desliga o proxy local 127.0.0.1),
        apaga as regras AnonShield-BlockAll/Allow e limpa os flags
        protect_total/firewall_on/kill_switch. Não mexe em idioma/tema.
        """
        prev = self.cfg.prev_proxy
        try:
            res = sysprotect.emergency_restore(prev)
        except Exception as e:  # noqa: BLE001
            res = {"proxy": f"falha: {e}"[:120], "firewall": "?"}
        self.cfg.protect_total = False
        if hasattr(self.cfg, "pending_protect"):
            self.cfg.pending_protect = False
        try:
            self.pending_protect = False
        except (RuntimeError, AttributeError):
            pass
        self.cfg.firewall_on = False
        self.cfg.kill_switch = False
        self.cfg.prev_proxy = None
        try:
            self.cfg.save()
        except Exception:
            pass
        for chk in ("chk_total", "chk_fw", "chk_kill"):
            try:
                w = getattr(self, chk, None)
                if w is not None:
                    w.blockSignals(True)
                    w.setChecked(False)
                    w.blockSignals(False)
            except (RuntimeError, AttributeError):
                pass
        p, f = res.get("proxy", "?"), res.get("firewall", "?")
        bad = str(p).startswith("falha") or str(f).startswith("falha")
        msg = self.tr("net_restore_fail" if bad else "net_restore_ok", p=p, f=f)
        try:
            self.lbl_result.setText(msg)
        except (RuntimeError, AttributeError):
            pass
        self._push_log(msg)
        self.refresh_texts()

    def reset_config(self) -> None:
        from .config import AppConfig as _AC
        # Primeiro devolve a internet (proxy + firewall), senão o "padrão"
        # deixaria o PC sem rede mesmo com config limpa.
        try:
            self.restore_internet()
        except Exception:
            pass
        lang, theme, pw = self.cfg.lang, self.cfg.theme, self.cfg.password
        self.cfg = _AC()
        self.cfg.lang, self.cfg.theme, self.cfg.password = lang, theme, pw
        self.cfg.save()
        self.edit_bridges.setPlainText("")
        self.apply_theme()
        self.refresh_texts()
        self._push_log(self.tr("log_reset"))

    def _profile_files(self) -> tuple[str, list[str]]:
        """(pasta do perfil, arquivos do cofre). Convidado = cfg global."""
        from .config import app_dirs as _ad
        cfg_dir, _ = _ad()
        names = ["config.enc", "vault.meta", "config.json", "users.meta"]
        return cfg_dir, [n for n in names
                         if os.path.exists(os.path.join(cfg_dir, n))]

    def backup_export(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        cfg_dir, files = self._profile_files()
        if not files:
            self._push_log(self.tr("backup_empty"))
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, self.tr("backup_title"), "anonshield-backup.zip",
            "ZIP (*.zip)")
        if not dest:
            return
        try:
            import zipfile as _zf
            with _zf.ZipFile(dest, "w", _zf.ZIP_DEFLATED) as z:
                for n in files:
                    z.write(os.path.join(cfg_dir, n), n)
            self._push_log(self.tr("backup_done", p=dest))
        except OSError as e:
            self._push_log(f"✗ {e}"[:300])

    def backup_import(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("backup_title"), "", "ZIP (*.zip)")
        if not path:
            return
        ans = QMessageBox.question(
            self, "Anonymous Shield", self.tr("backup_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            import zipfile as _zf
            cfg_dir, _ = self._profile_files()
            with _zf.ZipFile(path) as z:
                bad = [n for n in z.namelist()
                       if "/" in n or "\\" in n or n.startswith(".")
                       or n not in ("config.enc", "vault.meta", "config.json",
                                    "users.meta")]
                if bad or not z.namelist():
                    self._push_log(self.tr("backup_bad"))
                    return
                z.extractall(cfg_dir)
            self._push_log(self.tr("backup_restored"))
        except Exception as e:  # noqa: BLE001
            self._push_log(f"✗ {e}"[:300])

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            # Sempre devolve a internet ao sair (mesmo se os flags já
            # estiverem falsos por crash anterior): proxy + firewall.
            sysprotect.emergency_restore(getattr(self.cfg, "prev_proxy", None))
        except Exception:
            pass
        try:
            if self._worker:
                self._worker.stop()
                self._worker.kill_tor()
            self._dns_stop()
        except Exception:
            pass
        try:  # não deixa o openvpn órfão ao sair (silencioso, sem refresh)
            proc = getattr(self, "_vpn_proc", None)
            self._vpn_proc = None
            self.vpn_on = False
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except Exception:
                    proc.kill()
        except Exception:
            pass
        super().closeEvent(event)
