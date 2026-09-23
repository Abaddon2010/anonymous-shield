# 🛡️ Anonymous Shield — cliente Tor para desktop (Windows)

Cliente **Tor** para Windows em **Python + PyQt6 + tor oficial**, inspirado no Orbot:
botão-cebola com progresso real de bootstrap, IP/país de saída, bridges
(obfs4/snowflake/webtunnel), proxy upstream, SOCKS local, DNSCrypt, proteção
total (proxy do Windows + kill-switch no firewall) e atualização pela aba Atualizar.

> **Tor™** é marca do The Tor Project, Inc. — este produto **não** é afiliado
> nem endossado por eles. Site oficial: https://www.torproject.org/

## 📥 Baixar

Vá em [**Releases**](../../releases) e baixe o `AnonymousShield.exe` da versão
desejada (compilado automaticamente por GitHub Actions a cada tag `v*`).
Não precisa instalar Python: PyQt6, Tor e transportes já vão embutidos.

## 📁 Estrutura

```
anonymous-shield/   app (main.py, anonshield/, assets/, vendor/, tests/)
  vendor/           tor.exe oficial + lyrebird/conjure + GeoIP + licenças
.github/workflows/ build do exe + Release automática
LICENSE / LICENSE-APACHE   licença dupla do código: Apache-2.0 OU GPL-3.0
```

## 🔨 Rodar do fonte / compilar

```bash
cd anonymous-shield
pip install -r requirements.txt
python main.py            # rodar
python -m PyInstaller --noconfirm AnonymousShield.spec   # gerar o exe
```

## 📄 Licença

Código próprio em **licença dupla Apache-2.0 / GPL-3.0** (ver `LICENSE-APACHE`
e `LICENSE`). Inclui software de terceiros: Tor (BSD-3-clause),
OpenSSL (Apache-2.0), libevent, zlib — textos integrais na página
**Sobre** do app e em `anonymous-shield/vendor/docs/`.
