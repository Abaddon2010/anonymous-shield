# 🛡️ Anonymous Shield — Tor desktop client (Python)

**Tor** client for Windows (and beta Linux) built with **Python + PyQt6 +
official tor** (C daemon via `stem`), inspired by Orbot. Proven path: 100%
bootstrap + `IsTor:true` on the same machine/network.

> **Tor™** is a trademark of The Tor Project, Inc. — this product is **not**
> affiliated with or endorsed by them. https://www.torproject.org/

## Features

- 🧅 Onion button + real progress (`bootstrap-phase`), exit IP + country,
  new identity, live circuit (guard→middle→exit) and bandwidth
- 🌉 Bridges: direct/auto/obfs4/snowflake/webtunnel/custom, clipboard
  auto-fill, auto-enable; bundled lyrebird for obfs4
- ⇄ Upstream (`Socks5Proxy`/`Socks4Proxy`/`HTTPSProxy` in torrc, password
  via control port only — never on disk)
- 🔌 Local SOCKS served by tor (`SocksPort`) + dedicated SOCKS per app
- 🛡 Optional DNSCrypt (tor / local stub / combined)
- 🛡 Total protection: system proxy + firewall kill-switch (admin) + per-app
- 🖥 Logs (real `tor.log` + events, optional never-store-logs mode),
  ⟡ Diagnostics (Tor/network tests, leak check, wipe, rescue),
  ⟳ Update (GitHub API + SHA-256 + restart), ⓘ About (full license texts)
- ⏰ Scheduler + IP auto-rotation, profile backup (ZIP), local users with
  AES-256-GCM vault, ☰ draggable sidebar, light/dark theme, **50 languages**
  (PT-BR/EN/ES complete, rest via EN fallback), single instance

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

## Build the executable (Windows)

```bash
python -m PyInstaller --noconfirm AnonymousShield.spec
# dist/AnonymousShield.exe  (~90 MB: Qt + tor + PTs embedded)
```

## 🐧 Linux (Debian/Ubuntu — beta)

```bash
sudo apt install -y tor obfs4proxy python3-pyqt6 python3-pip python3-venv
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Uses the **system Tor** — no embedded binary on Linux. Firewall kill-switch
and system proxy on Linux are under construction (see root README).

## Layout

```
anonymous-shield/
  main.py  requirements.txt  README.md  CHANGELOG.md  installer.iss
  anonshield/  config.py  i18n*.py  torctl.py  sysprotect.py
               gui.py  uilogic.py  users.py  vault.py  widgets.py
  assets/  icon.png  icon.ico
  vendor/  tor/tor.exe  tor/pluggable_transports/  data/geoip*  docs/
  tests/
```

## Privacy

Zero names, personal paths or machine data in the source (everything via
OS env/API). Examples use `192.0.2.x` / `127.0.0.1`.

## License

Own code dual-licensed **Apache-2.0 / GPL-3.0** (`LICENSE-APACHE`, `LICENSE`
at repo root). Bundles Tor (BSD-3-clause), OpenSSL (Apache-2.0), libevent,
zlib — full texts in `vendor/docs/` and on the app's About page.
