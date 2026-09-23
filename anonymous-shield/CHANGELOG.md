# Changelog — Anonymous Shield

## [1.8.0] — 2026-09-21 — Renamed to Anonymous Shield

### Changed (brand)
- Name/brand swapped everywhere (code, UI, installer, firewall,
  data folders with automatic migration from the old folder, User-Agent).
  Reason: the Tor Project's trademark policy forbids "Tor" in third-party
  product names without written authorization.
- Single intentional leftover: internal cryptographic pepper (changing it
  would invalidate existing profiles).
- Old firewall rules (TorShield-*) are cleaned up on revert.
- About → text with Tor™ + credit + "unaffiliated" + licenses.

## [1.7.2] — Scheduler + profile backup

### Added
- ⏰ Scheduler (Tor page): turn on/off and rotate IP on schedule
  (HH:MM, fires 1x per minute, shows the next one).
- ⬆⬇ Profile backup (Diagnostics): exports/imports the vault as ZIP
  (validates contents, asks for confirmation, backup password on entry).

## [1.7.1] — Draggable sidebar

### Added
- ✎ Organize button on the sidebar: drag items to reorder (including
  across sections); ↺ restores the default. Order saved per profile.

## [1.7.0] — Full translation (10 languages × 476 keys) — 2026-09-20 — Real Tor E2E

### Added
- `tests/test_e2e_tor.py` (TORSHIELD_E2E=1): bootstrap + IsTor + headless
  Chrome via Tor + round-trip proxy. Proven: 3 passed.
- "End-to-end test" button on Diagnostics (exit/DNS/proxy).

## [1.6.3] — 2026-09-20 — No auto-connect + translated login

### Changed
- Tor only connects on click (auto-connect off by default;
  whoever deliberately enabled it keeps it via toggle).
- Login strings translated in all 10 packs (feats, welcome,
  Caps Lock, footer, empty, guest hint).

## [1.6.2] — 2026-09-20 — Always-visible circuit

### Fixed
- Circuit card stuck on "No circuit" forever: missing
  `_circuit_job`, signal connection and busy reset. Now shows
  guard→middle→exit with flags + fallback to any circuit.

## [1.6.1] — 2026-09-20 — Tor circuit + current DNS + mode names

### Added
- Tor Circuit card on the Dashboard (guard→middle→exit with flags + IP,
  new circuit button, self-updating).
- "Current DNS" line (local stub, Tor exit or system DNS).
- Ready-made description of each mode + correct names on buttons.

## [1.6.0] — 2026-09-20 — Modes, bandwidth, per-app SOCKS, conjure

### Added
- Ready modes (Tor): ⚡ Fast, 🥷 Anonymous, 🧱 Anti-censorship
  (detects the current one; censorship uses best transport from saved bridges).
- Live traffic on the Dashboard (↓/↑ per second via control port).
- Dedicated SOCKS per app (9160+i in torrc; opening uses the app's port;
  the switch now actually works).
- conjure-client as a transport (already shipped in the bundle).

## [1.5.3] — 2026-09-20 — Dark title bar

### Changed
- Window titles dark to match (purple #1e1b4b on Win11),
  keeping native buttons. Applies to login, passwords and app.

## [1.5.2] — 2026-09-20 — Two-panel login

### Changed
- Redesigned login: brand side panel (logo, version, features)
  + form (profiles, 48px password, aligned eye, Caps Lock, 50px sign-in).

## [1.5.1] — 2026-09-20 — Standard DNS + 115 translated keys

### Added
- Redesigned DNS page (hero, segmented control, listen chip).
- +40 keys in the 10 language packs (115 total per language).
- Inno Setup installer (`installer.iss`), self-applying updater with
  restart, Tor Browser button, DNS in Check Status, pytest + git.

## [1.5.0] — 2026-09-20 — Identified Tor window

### Changed
- "Open with Tor" opens purple home page "TorShield — Tor window":
  impossible to confuse with normal/anonymous Chrome.

## [1.4.9] — 2026-09-20 — Audit: threads + credential leak

### Security/Fixes
- No `shell=True`, 0.0.0.0 binds, eval or pickle; everything via arg
  lists; SOCKS/control/DNS on 127.0.0.1 only.
- Widgets never touched from worker threads (`_ui_call` + `_push_log`
  thread-safe; firewall/DNS/updater reorganized).
- Upstream proxy password masked in logs (`user:***`).
- Sanitized updater repo; update metadata via Tor when connected.
- `program="..."` quoted in firewall rules (paths with spaces).

## [1.4.8] — 2026-09-20 — Update = project, via GitHub or URL

### Changed
- Update page makes it clear: it updates TorShield (the app), not Tor
  (the bundled Tor ships along). Sources: GitHub release or direct URL with
  optional expected SHA-256 (actually verified when provided).

## [1.4.7] — 2026-09-20 — 10 languages truly translated

### Added
- Hand translation of the main screens into FR/DE/IT/ZH/JA/RU/NL/TR/AR/HI
  (per-key fallback to EN for the rest; other 37 remain selectable).
  Fixed case-insensitive lookup (`zh-CN`).

## [1.4.6] — 2026-09-20 — Credential off disk + honest updater

### Security
- torrc NEVER carries the upstream password again: host:port only; the
  credential is applied at runtime via SETCONF on the control port.
- Updater: explicit confirmation if the repository changes + Authenticode
  status (valid/missing/invalid) of each download. Honest limit:
  a release's own checksum doesn't prove origin against a hijacked account.

## [1.4.5] — 2026-09-20 — Automatic IP rotation

### Added
- Tor page: on/off + interval in seconds/minutes (min. 60s),
  countdown and automatic (new identity) rotation on schedule.

## [1.4.4] — 2026-09-20 — Change IP button on Dashboard

### Added
- 🔄 button on the Dashboard hero: new Tor identity (new exit IP).
  Only active while connected.

## [1.4.3] — 2026-09-20 — Avoid 5/9/14 Eyes + atomic torrc

### Added
- Exits outside 5/9/14 Eyes (your choice): All|−5|−9|−14 on the exit
  card; applies live (control port) or in the next connect's torrc.

### Fixed
- Atomic torrc writes (temp+replace) + 6 retries with backoff +
  single fallback: 20/20 stress OK even with a filter locking the file.

## [1.4.2] — 2026-09-20 — Hang-free shutdown + crash forensics

### Fixed
- Turning off no longer freezes the UI (blocking `wait(3000)` removed) nor
  kills the window (proven with real Tor + 60s of UI after shutdown).
- Forensics: `crash.log`/`error.log` in the data folder on fatal events.

## [1.4.1] — 2026-09-20 — Shutdown/failure restores internet alone

### Fixed
- Turning Tor off or cancelling it (and connection failure under total
  protection) automatically restores proxy + firewall — no more dead internet.
- Tor picks on its own where it can write (default→Local→Temp) and
  logs the location.

## [1.4.0] — 2026-09-20 — Restore internet button (no-network after total protection)

### Fixed
- "No internet for 1h after adding stuff": v1.3.9 made total protection =
  Windows proxy + firewall blocking everything outside Tor. If the
  app crashed/closed before undoing it ("Turn off kills the app" bug still
  open), the PC was left with dead proxy `socks=127.0.0.1:9150` + rules
  `TorShield-BlockAll/Allow` — no network even with the app closed.
- `↺ Restore default` did NOT touch proxy/firewall (it only zeroed the config),
  so it didn't help.

### Added
- Red **🌐 Restore internet (default)** button on Diagnostics and on
  Total Protection: restores the previous proxy (or turns the local proxy off),
  deletes the BlockAll/Allow rules and clears `protect_total/firewall_on/
  kill_switch`. Preserves third-party proxies and language/theme.
- `sysprotect.emergency_restore()`: same reusable logic.
- `reset_config` now restores before zeroing; `closeEvent`
  always restores on exit (best-effort).
- `Restaurar-Internet.bat`: rescue without the app (offline PC) — run as
  administrator on the affected PC.

## [1.3.9] — 2026-09-20 — Real apps on Tor + total blocks the rest

### Fixed
- "Open with Tor" now works: Chromium via `--proxy-server` + dedicated
  profile with anti-WebRTC; Firefox via `user.js` profile (WebRTC off,
  no DoH); others via `ALL_PROXY`. Chrome used to ignore the variable.
- Total protection is now = Tor + Windows proxy + firewall blocking the
  rest (tor.exe/lyrebird always allowed): everything goes through Tor or
  stays offline, not just the app list.

### Added
- "Leak test" button (ipleak.net in the browser via Tor) on the
  Applications page + log of the method used to open each app.
- Turning Tor off/cancelling under total protection restores everything
  to default (previous proxy, clean firewall, flags off) + automatic
  rollback on launch if a dead session left a block behind.

## [1.3.8] — 2026-09-20 — Hero stuck at 95% + clickable KPIs

### Fixed
- Dashboard hero froze on the last bootstrap frame (95%):
  `_tick` didn't sync the hero when connected. Now shows
  CONNECTED 100% + exit IP.
- KPIs became buttons: Protection toggles total protection;
  Tor/SOCKS/DNS navigate to their pages.

## [1.3.7] — 2026-09-20 — Turn-off doesn't quit + status check

### Fixed
- Turning Tor off no longer quits the app: stale worker signals are
  disconnected on `disconnect` (they used to resurrect "connecting"
  and kill the window); late progress/error/exit ignored.
- Bar stuck at 95% with CONNECTED status: same cause (late signal);
  regressing after connected is now impossible.

### Added
- ⟳ **Check Status** button on the Dashboard hero: queries bootstrap
  phase (control port) + IsTor exit and shows the result on the hero and log.

## [1.3.6] — 2026-09-20 — Lock-proof torrc

### Fixed
- `write_torrc` with fallback: if the main `torrc` is locked
  (DENY, another process's lock), uses `torrc-<pid>` and carries on; orphans
  older than 7 days are cleaned. Proven against a poisoned file.
- Root cause of Error 13 mapped: file with denied writes despite
  `<user>:(F)` (lock external to the DACL); folder and ACLs verified healthy.

## [1.3.5] — 2026-09-20 — Null ACE + readable dialogs

### Fixed
- Error 13 root cause: empty inherited ACE `<user>:(I)` with no permissions on torrc.
  Repair is now `icacls /reset` + explicit additive `/grant`
  (`acl_repair`, never removes anything); `tor-data` folder with explicit F.
- Error dialogs (QMessageBox) themed: dark background + light text
  in dark mode, white background + dark text in light mode.

## [1.3.4] — 2026-09-20 — Scanner-via-Tor + Error 13 diagnostics

### Fixed
- "Via Tor" scanner on localhost/local network is now blocked with a clear
  warning (it used to flood tor.log with "malformed hostname" rejected
  by exits — correct Tor behavior, our target was invalid).
- Error 13 on torrc: `icacls /reset` on the `data` folder too + ACL
  diagnostics attached to the message when everything fails.
- Log without duplicated "✗ ✗" on Tor failures.

## [1.3.3] — 2026-09-20 — Error 13 fix on torrc (admin)

### Fixed
- `lock_private` no longer touches ACL inheritance (`icacls /inheritance:r`
  locked torrc with Permission denied, fallout from v1.3.1 when running as
  administrator). The profile folder already restricts to SYSTEM/Admin/owner.
- `write_torrc` with self-repair: `icacls /reset` on file/folder and a new
  attempt before failing (heals files locked by v1.3.1).

## [1.3.2] — 2026-09-20 — Full nmap panel

### Added
- Scanner with all functions: types (-sS/-sT/-sU/-sN/-sF/-sX/-sA),
  ports (`-F`/`-p-`/ranges), discovery (-Pn/-sn/-PS/-PA/-PU), -sV/-O/-A,
  --reason, timing T0–T5, fragmentation (-f), decoys (-D), NSE
  (--script/--script-args), -oN/-oX/-oG outputs, live command preview
  and warning when administrator is required. Quick profiles fill the panel.

## [1.3.2] — 2026-09-20 — Error 13 fix on torrc (admin)

### Fixed
- `lock_private` no longer touches ACL inheritance (`icacls /inheritance:r`
  locked torrc with Permission denied, fallout from v1.3.1 when running as
  administrator). The profile folder already restricts to SYSTEM/Admin/owner.
- `write_torrc` with self-repair: `icacls /reset` on file/folder and a new
  attempt before failing (heals files locked by v1.3.1).

## [1.3.1] — 2026-09-20 — Security audit (8 items)

### Security (all verified with automated test `sec_verify.py`)
- **Traceless VPN**: `vpn_pass` in memory only (`to_dict` strips it, `load`
  purges legacy); `ovpn-auth.txt` with restricted ACL (`lock_private`) and
  shredded 25s after connecting + on disconnect/failure; UI hint.
- **SHA-256 updater**: downloads the release's published checksum and
  compares; mismatched hash = file deleted + alert; no checksum =
  explicit warning.
- **Shielded torrc**: bridges/PT/upstream sanitized (1 line each, no
  CR/LF); file with user-only ACL (`lock_private`).
- **8-char minimum password** (was 4) on create/change/user; old passwords
  keep working.
- Bundled Tor **0.4.9.12 = latest security release** (verified
  2026-09-20); version shown on the Update page (`tor_ver`).
- Hygiene: `SESSAO.md` free of personal paths; exe verified with
  0 username occurrences. `_device_secret` documented as
  obfuscation (future DPAPI).

## [Unreleased] — dashboard era (2026-09-20, already in the desktop exe)

### Added
- **Dashboard**: home page with hero, 4 KPIs (Tor/SOCKS/protection/DNS),
  quick actions and recent activity; sidebar with sections.
- **🗂 Applications page**: per-app switch (only enabled ones use Tor),
  "Open with Tor", add by path/`…`/Enter,
  auto-detection (Chrome/Edge/Discord...).
- **🔒 VPN page**: detected external VPNs + own OpenVPN
  (Tor-over-VPN), kill-switch allows VPN exes, embedded log.
- **50 languages** on login and topbar (PT/EN/ES complete, rest via EN),
  automatic system detection.
- **Skull-onion icon** (new `assets/icon.png`/`.ico`).

### Changed
- Redesigned login (gradient hero, real logo, pills) + `PassDialog`
  in the same look.
- Topbar with fixed "TorShield"; Proxy page and sidebar in dashboard
  style (light-purple navigation in dark mode).
- **Guest enters with no password** (local plaintext config).
- Add button shows inline error/success instead of failing silently.

## [1.2.0] — 2026-09-19 — AES-256 vault + local users + featured IP

### Added
- **AES-256-GCM vault** on everything at rest: `config.enc` + master
  password (PBKDF2-SHA256 600k), gate on launch (create/ask/change), shred
  plaintext, `Change password` on Diagnostics.
- **Local users (optional)**: start screen with sign-in/create/delete or
  go without user; encrypted names (device key), PBKDF2 password, vault
  and Tor data separated per user.
- **Featured IP** on Home: big number + country + copy ("…"
  while fetching).

## [1.1.1] — 2026-09-19 — Anti-personal-data audit

### Privacy (real finding fixed)
- `config.json` stored absolute app paths (`C:\Users\<name>\...`).
  Now saves portable form (`%PROGRAMFILES%`, `%LOCALAPPDATA%`, …) and
  expands only at runtime (`sysprotect.portable/expand`); automatic migration.
- Full sweep: source free of names/paths/IPs/emails; exe free of username,
  hostname or project path (0 occurrences); generated `torrc`/TOML are
  recreatable functional cache (see `🧹 Clear data`).

## [1.1.0] — 2026-09-19 — Home toggle, nmap Scanner, combined DNSCrypt

### Added
- Home with big **Connect/Disconnect** button (press to turn on, press to
  turn off) plus the onion.
- **◉ Scanner page**: uses the **real nmap** if installed (Quick, Services,
  Full, OS, ping sweep, custom, --open, -Pn, save report)
  or built-in scanner (top ports + banner + rDNS, optionally via Tor).
- **Combined DNSCrypt** (`Tor + local`): local stub rises with Tor;
  firewall already allows it together. Third mode on the DNS tab.

## [1.0.2] — 2026-09-19 — Full Rust removal

### Removed
- Entire `tor-shield/` folder (source + 14.9 GB `target/`).
- Rust toolchain (`rustup self uninstall`: 0.76 GB `.cargo` + 1.28 GB
  `.rustup` removed; no `cargo`/`rustc`/`rustup` on the machine).
- Arti data (`%LOCALAPPDATA%\torproject`), test temps (`torprobe`,
  probe logs). Total freed: **~17 GB**.
- Leftovers: only the empty `tor-shield/` folder (locked by open
  Explorer/VS Code — close and delete manually).

## [1.0.1] — 2026-09-19 — Full parity with Rust

- Item-by-item audit against TorShield Rust (v0.12): 4 things missing,
  all implemented — stats cards on Home, Cancel button while
  connecting, Open folder/Restore buttons on Diagnostics (methods existed,
  no button), WebTunnel warning on the Bridges tab, 8 i18n keys.

## [1.0.0] — 2026-09-19 — Python migration + official tor

### Decided
- Complete rewrite in **Python + PyQt6 + stem + official tor.exe**
  (Expert Bundle 15.0.23 in `vendor/`), after proving Arti stalled
  on consensus (`15%` / `Can't bootstrap a Tor directory`) while the
  C daemon bootstrapped 100% + `IsTor:true` + `NEWNYM` on the same machine/network.

### Added (parity)
- Onion button, phases, IP/country, new identity, bridges (Direct→custom,
  Paste, auto-enable, lyrebird for obfs4), upstream, SOCKS, DNSCrypt,
  Total Protection + per-app, Logs (real tor.log), Diagnostics (Tor/network/wipe),
  Update, ☰ menu, themes, PT-BR/EN/ES, single instance, auto firewall.
