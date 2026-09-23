# 🛡️ Anonymous Shield v1.0.0 — Orbot para Desktop (Python)

Cliente **Tor** multi-sistema em **Python + PyQt6 + tor oficial** (daemon C
via `stem`), inspirado no **Orbot**. Sucessor do Anonymous Shield Rust/Arti:
o motor C conecta como o Tor Browser (provado: bootstrap 100% + `IsTor:true`).

## Por que Python desta vez

- Usa o **mesmo daemon Tor do Tor Browser** (`tor.exe` 0.4.9, Expert Bundle
  15.0.23 incluso em `vendor/`) — consenso rápido, guards testados.
- `stem` fala com a ControlPort (bootstrap ao vivo, `NEWNYM`, etc.).
- SOCKS nativo do tor (sem reimplementar), `lyrebird` incluso p/ **obfs4**.

## Funcionalidades (paridade com o Rust)

- 🧅 Botão-cebola + progresso real (`bootstrap-phase`), IP de saída + país
- 🌉 Bridges: Direto/auto/obfs4/snowflake/webtunnel/custom, botão Colar,
  auto-ativa, aviso de PT ausente; obfs4 via lyrebird embutido
- ⇄ Upstream (`Socks5Proxy`/`Socks4Proxy`/`HTTPSProxy` no torrc)
- 🔌 SOCKS local servido pelo tor (`SocksPort`)
- 🛡 DNSCrypt opcional (tor / stub `dnscrypt-proxy` + teste sem deps)
- 🛡 Proteção Total: proxy do Windows + kill-switch firewall (admin) + por app
- 🖥 Logs (log real do `tor.log` + eventos), ⟡ Diagnóstico (teste Tor/rede/
  wipe), ⟳ Atualizar (GitHub API + download)
- ☰ Menu lateral, tema claro/escuro, **PT-BR/EN/ES**, instância única,
  firewall auto (admin), kill-switch restaurado ao sair

## Rodar do fonte

```bash
pip install -r requirements.txt
python main.py
```

## Gerar o executável

```bash
pyinstaller --noconfirm --onefile --windowed --name AnonymousShield \
  --icon assets/icon.ico --add-data "vendor;vendor" --add-data "assets;assets" \
  main.py
# dist/AnonymousShield.exe  (~100 MB: Qt + tor + PTs embutidos)
```

## Layout

```
tor-shield-py/
  main.py  requirements.txt  README.md  CHANGELOG.md
  anonshield/  config.py  i18n.py  torctl.py  sysprotect.py  gui.py  uilogic.py
  assets/  icon.png  icon.ico
  vendor/  tor/tor.exe  tor/pluggable_transports/lyrebird.exe  data/geoip*
```

## Privacidade

Zero nomes, caminhos pessoais ou dados da máquina no fonte (tudo via
env/API do SO). Exemplos com `192.0.2.x` / `127.0.0.1`.
