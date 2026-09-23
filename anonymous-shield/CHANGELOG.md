# Changelog — Anonymous Shield

## [1.8.1] — 2026-09-21 — Título proporcional + ícone sem cebola

### Mudado
- Login: nome "Anonymous Shield" em linha única reduzida (15px) — não
  corta mais o "A" inicial nem o "D" final no painel de 300px.
- Ícone novo (opção A): escudo + rota de 3 nós + cadeado, sem cebola
  (marca do Tor Project) — aplicado no exe, login e marca da sidebar.
- Botão principal da página Tor redesenhado como escudo (era anéis de
  cebola); emojis 🧅 trocados por 🛡/🌐 em sidebar, login e fileiras.

## [1.8.0] — 2026-09-21 — Renomeado para Anonymous Shield

### Mudado (marca)
- Nome/marca trocados em tudo (código, UI, instalador, firewall,
  pastas de dados com migração automática da pasta antiga, User-Agent).
  Motivo: a política de marca do Tor Project proíbe "Tor" em nome de
  produto de terceiros sem autorização escrita.
- Resquício intencional único: pepper criptográfico interno (mudá-lo
  invalidaria os perfis existentes).
- Regras de firewall antigas (TorShield-*) são limpas na reversão.
- Sobre → texto com Tor™ + crédito + "não afiliado" + licenças.

## [1.7.2] — Agendador + backup de perfil

### Adicionado
- ⏰ Agendador (página Tor): ligar/desligar e girar IP por horário
  (HH:MM, dispara 1x por minuto, mostra o próximo).
- ⬆⬇ Backup do perfil (Diagnóstico): exporta/importa o cofre em ZIP
  (valida conteúdo, pede confirmação, senha do backup ao entrar).

## [1.7.1] — Sidebar arrastável

### Adicionado
- Botão ✎ Organizar na sidebar: arraste itens p/ reordenar (inclusive
  entre seções); ↺ restaura o padrão. Ordem salva por perfil.

## [1.7.0] — Tradução total (10 idiomas × 476 chaves) — 2026-09-20 — E2E real do Tor

### Adicionado
- `tests/test_e2e_tor.py` (TORSHIELD_E2E=1): bootstrap + IsTor + Chrome
  headless via Tor + proxy ida/volta. Provado: 3 passed.
- Botão "Teste ponta a ponta" no Diagnóstico (saída/DNS/proxy).

## [1.6.3] — 2026-09-20 — Sem auto-conectar + login traduzido

### Mudado
- Tor só conecta no clique (auto-conectar desligado por padrão;
  quem ligou de propósito mantém via toggle).
- Frases do login traduzidas nos 10 pacotes (feats, boas-vindas,
  Caps Lock, rodapé, vazio, dica convidado).

## [1.6.2] — 2026-09-20 — Circuito sempre visível

### Corrigido
- Card Circuito mostrava "Sem circuito" para sempre: faltavam o
  `_circuit_job`, a conexão do signal e o reset do busy. Agora exibe
  guarda→meio→saída com bandeiras + fallback p/ qualquer circuito.

## [1.6.1] — 2026-09-20 — Circuito Tor + DNS atual + nomes dos modos

### Adicionado
- Card Circuito Tor no Dashboard (guarda→meio→saída com bandeiras + IP,
  botão novo circuito, atualiza sozinho).
- Linha "DNS atual" (stub local, saída Tor ou DNS do sistema).
- Descrição de cada modo pronta + nomes corretos nos botões.

## [1.6.0] — 2026-09-20 — Modos, banda, SOCKS por app, conjure

### Adicionado
- Modos prontos (Tor): ⚡ Rápido, 🥷 Anonimato, 🧱 Anti-censura
  (detecta o atual; censura usa melhor transporte das bridges salvas).
- Tráfego ao vivo no Dashboard (↓/↑ por segundo via controle).
- SOCKS dedicado por app (9160+i no torrc; abrir usa a porta do app;
  interruptor agora vale de verdade).
- conjure-client como transporte (já vinha no pacote).

## [1.5.3] — 2026-09-20 — Barra de título escura

### Mudado
- Título das janelas escuro combinando (roxo #1e1b4b no Win11),
  mantendo botões nativos. Vale p/ login, senhas e app.

## [1.5.2] — 2026-09-20 — Login em dois painéis

### Mudado
- Login redesenhado: painel lateral de marca (logo, versão, recursos)
  + formulário (perfis, senha 48px, olho alinhado, Caps Lock, entrar 50px).

## [1.5.1] — 2026-09-20 — DNS no padrão + 115 chaves traduzidas

### Adicionado
- Página DNS redesenhada (hero, segmentado, chip de escuta).
- +40 chaves nos 10 pacotes de idioma (115 no total por idioma).
- Instalador Inno Setup (`installer.iss`), update que se aplica e
  reinicia, botão Tor Browser, DNS no Check Status, pytest + git.

## [1.5.0] — 2026-09-20 — Janela Tor identificada

### Mudado
- "Abrir com Tor" abre página inicial roxa "TorShield — janela Tor":
  impossível confundir com o Chrome normal/anônimo.

## [1.4.9] — 2026-09-20 — Auditoria: threads + vazamento de credencial

### Segurança/Correções
- Nenhum `shell=True`, bind 0.0.0.0, eval ou pickle; tudo via listas de
  args; SOCKS/controle/DNS só em 127.0.0.1.
- Widgets nunca mais tocados de worker threads (`_ui_call` + `_push_log`
  thread-safe; firewall/DNS/updater reorganizados).
- Senha do proxy upstream mascarada nos logs (`user:***`).
- Repo do updater sanitizado; metadados do update via Tor quando conectado.
- `program="..."` com aspas nas regras de firewall (paths com espaço).

## [1.4.8] — 2026-09-20 — Atualizar = projeto, via GitHub ou URL

### Mudado
- Página Atualizar deixa claro: atualiza o TorShield (o app), não o Tor
  (o Tor embutido vem junto). Fontes: release GitHub ou URL direta com
  SHA-256 esperado opcional (confere de verdade quando informado).

## [1.4.7] — 2026-09-20 — 10 idiomas traduzidos de verdade

### Adicionado
- Tradução manual das telas principais em FR/DE/IT/ZH/JA/RU/NL/TR/AR/HI
  (fallback por chave p/ EN no resto; demais 37 seguem selecionáveis).
  Corrigido lookup case-insensitive (`zh-CN`).

## [1.4.6] — 2026-09-20 — Credencial fora do disco + updater honesto

### Segurança
- torrc NUNCA mais tem senha de upstream: vai só host:porta; a
  credencial é aplicada em runtime via SETCONF na porta de controle.
- Updater: confirmação explícita se o repositório mudar + status
  Authenticode (válida/sem/inválida) de cada download. Limite honesto:
  checksum do próprio release não prova origem contra conta invadida.

## [1.4.5] — 2026-09-20 — Rotação automática de IP

### Adicionado
- Página Tor: liga/desliga + intervalo em segundos/minutos (mín. 60s),
  contagem regressiva e troca (nova identidade) automática no tempo.

## [1.4.4] — 2026-09-20 — Botão Trocar IP no Dashboard

### Adicionado
- Botão 🔄 no hero do Dashboard: nova identidade Tor (novo IP de saída).
  Só ativo quando conectado.

## [1.4.3] — 2026-09-20 — Evitar 5/9/14 Olhos + torrc atômico

### Adicionado
- Saída fora dos 5/9/14 Olhos (você escolhe): Todos|−5|−9|−14 no card
  de saída; vale ao vivo (controle) ou no torrc do próximo connect.

### Corrigido
- Escrita do torrc atômica (temp+replace) + 6 tentativas com backoff +
  fallback único: stress 20/20 OK mesmo com filtro travando o arquivo.

## [1.4.2] — 2026-09-20 — Desligar sem travar + forense de crash

### Corrigido
- Desligar não congela mais a UI (removido `wait(3000)` bloqueante) e não
  derruba a janela (provado com Tor real + 60s de UI após desligar).
- Forense: `crash.log`/`error.log` na pasta de dados se algo fatal ocorrer.

## [1.4.1] — 2026-09-20 — Desligar/falhar restaura a internet sozinho

### Corrigido
- Desligar ou cancelar o Tor (e falha de conexão com proteção total)
  restaura proxy + firewall automaticamente — sem mais internet morta.
- Tor escolhe sozinho onde consegue escrever (padrão→Local→Temp) e
  registra o local no log.

## [1.4.0] — 2026-09-20 — Botão Restaurar internet (sem-rede após proteção total)

### Corrigido
- "Sem internet há 1h após implementar coisas": a v1.3.9 fez a proteção
  total = proxy do Windows + firewall bloqueando tudo fora do Tor. Se o
  app crashava/fechava antes de desfazer (bug "Desligar fecha o app" em
  aberto), o PC ficava com proxy morto `socks=127.0.0.1:9150` + regras
  `TorShield-BlockAll/Allow` — sem rede mesmo com o app fechado.
- `↺ Restaurar padrão` NÃO tocava em proxy/firewall (só zerava o config),
  então não adiantava.

### Adicionado
- Botão vermelho **🌐 Restaurar internet (padrão)** em Diagnóstico e em
  Proteção Total: restaura o proxy anterior (ou desliga o proxy local),
  apaga as regras BlockAll/Allow e limpa `protect_total/firewall_on/
  kill_switch`. Preserva proxy de terceiros e idioma/tema.
- `sysprotect.emergency_restore()`: mesma lógica reutilizável.
- `reset_config` agora chama a restauração antes de zerar; `closeEvent`
  sempre restaura ao sair (best-effort).
- `Restaurar-Internet.bat`: socorro sem o app (PC offline) — rode como
  administrador no PC afetado.

## [1.3.9] — 2026-09-20 — Apps de verdade no Tor + total bloqueia resto

### Corrigido
- "Abrir com Tor" agora funciona: Chromium via `--proxy-server` + perfil
  dedicado com anti-WebRTC; Firefox via perfil `user.js` (WebRTC off,
  sem DoH); demais via `ALL_PROXY`. Antes o Chrome ignorava a variável.
- Proteção total agora = Tor + proxy do Windows + firewall bloqueando o
  resto (tor.exe/lyrebird sempre liberados): tudo passa pelo Tor ou fica
  sem internet, não só a lista de apps.

### Adicionado
- Botão "Testar vazamento" (ipleak.net no navegador via Tor) na página
  Aplicativos + log do método usado ao abrir cada app.
- Desligar/cancelar o Tor com proteção total restaura tudo ao padrão
  (proxy anterior, firewall limpo, flags off) + reversão automática ao
  abrir se sobrou bloqueio de sessão morta.

## [1.3.8] — 2026-09-20 — Hero travado em 95% + KPIs clicáveis

### Corrigido
- Hero do Dashboard congelava no último quadro do bootstrap (95%):
  `_tick` não sincronizava o hero quando conectado. Agora mostra
  CONECTADO 100% + IP de saída.
- KPIs viraram botões: Proteção liga/desliga a proteção total;
  Tor/SOCKS/DNS navegam para as páginas.

## [1.3.7] — 2026-09-20 — Desligar não fecha + check de status

### Corrigido
- Desligar o Tor não fecha mais o app: sinais do worker velho são
  desligados no `disconnect` (eram eles que resususcitavam "conectando"
  e derrubavam a janela); progresso/erro/saída tardios ignorados.
- Barra travada em 95% com status CONECTADO: mesma causa (sinal tardio);
  agora é impossível regredir após conectado.

### Adicionado
- Botão ⟳ **Check Status** no hero do Dashboard: consulta fase do
  bootstrap (controle) + saída IsTor e mostra o resultado no hero e no log.

## [1.3.6] — 2026-09-20 — torrc à prova de trava

### Corrigido
- `write_torrc` com fallback: se o `torrc` principal estiver travado
  (DENY, trava de outro processo), usa `torrc-<pid>` e segue; órfãos
  >7 dias são limpos. Provado contra arquivo envenenado.
- Causa do Erro 13 mapeada: arquivo com escrita negada apesar de
  `<usuario>:(F)` (trava externa ao DACL); pasta e ACLs verificadas saudáveis.

## [1.3.5] — 2026-09-20 — ACE nula + diálogos legíveis

### Corrigido
- Erro 13 raiz: ACE herdada vazia `<usuario>:(I)` sem permissões no torrc.
  Reparo agora é `icacls /reset` + `/grant` explícito aditivo
  (`acl_repair`, nunca remove nada); pasta `tor-data` com F explícito.
- Diálogos de erro (QMessageBox) com tema: fundo escuro + texto claro
  no modo escuro, fundo branco + texto escuro no claro.

## [1.3.4] — 2026-09-20 — Scanner-via-Tor + diagnóstico Erro 13

### Corrigido
- Scanner "Via Tor" em localhost/rede local agora é barrado com aviso
  claro (antes inundava o tor.log com "malformed hostname" rejeitado
  pelos exits — comportamento correto do Tor, alvo inválido nosso).
- Erro 13 no torrc: `icacls /reset` também na pasta `data` + diagnóstico
  da ACL anexado à mensagem quando tudo falha.
- Log sem "✗ ✗" duplicado nas falhas do Tor.

## [1.3.3] — 2026-09-20 — Correção Erro 13 no torrc (admin)

### Corrigido
- `lock_private` não mexe mais em herança de ACL (`icacls /inheritance:r`
  travava o torrc com Permission denied, mordida na v1.3.1 ao rodar como
  administrador). Pasta do perfil já restringe a SYSTEM/Admin/dono.
- `write_torrc` com auto-reparo: `icacls /reset` no arquivo/pasta e nova
  tentativa antes de falhar (cura arquivos travados pela v1.3.1).

## [1.3.2] — 2026-09-20 — Painel nmap completo

### Adicionado
- Scanner com todas as funções: tipos (-sS/-sT/-sU/-sN/-sF/-sX/-sA),
  portas (`-F`/`-p-`/faixas), descoberta (-Pn/-sn/-PS/-PA/-PU), -sV/-O/-A,
  --reason, timing T0–T5, fragmentação (-f), decoys (-D), NSE
  (--script/--script-args), saídas -oN/-oX/-oG, preview ao vivo do comando
  e aviso quando exige administrador. Perfis rápidos preenchem o painel.

## [1.3.2] — 2026-09-20 — Correção Erro 13 no torrc (admin)

### Corrigido
- `lock_private` não mexe mais em herança de ACL (`icacls /inheritance:r`
  travava o torrc com Permission denied, mordida na v1.3.1 ao rodar como
  administrador). Pasta do perfil já restringe a SYSTEM/Admin/dono.
- `write_torrc` com auto-reparo: `icacls /reset` no arquivo/pasta e nova
  tentativa antes de falhar (cura arquivos travados pela v1.3.1).

## [1.3.1] — 2026-09-20 — Auditoria de segurança (8 itens)

### Segurança (todos verificados com teste automatizado `sec_verify.py`)
- **VPN sem rastro**: `vpn_pass` só em memória (`to_dict` remove, `load`
  expurga legado); `ovpn-auth.txt` com ACL restrita (`lock_private`) e
  triturado 25s após conectar + ao desconectar/falhar; dica na UI.
- **Atualizador com SHA-256**: baixa checksum publicado do release e
  compara; hash divergente = arquivo apagado + alerta; sem checksum =
  aviso explícito.
- **torrc blindado**: bridges/PT/upstream sanitizados (1 linha cada, sem
  CR/LF); arquivo com ACL só-usuário (`lock_private`).
- **Senha mínima 8** (era 4) em criar/trocar/usuário; senhas antigas
  continuam valendo.
- Tor embutido **0.4.9.12 = último security release** (verificado em
  2026-09-20); versão exibida na página Atualizar (`tor_ver`).
- Higiene: `SESSAO.md` sem caminhos pessoais; exe verificado com
  0 ocorrências de username. `_device_secret` documentado como
  ofuscação (DPAPI futuro).

## [Unreleased] — era dashboard (2026-09-20, já no exe do desktop)

### Adicionado
- **Dashboard**: página inicial com hero, 4 KPIs (Tor/SOCKS/proteção/DNS),
  ações rápidas e atividade recente; sidebar com seções.
- **Página 🗂 Aplicativos**: interruptor por app (só ativados usam o Tor),
  "Abrir com Tor", adicionar por caminho/`…`/Enter,
  auto-detecção (Chrome/Edge/Discord...).
- **Página 🔒 VPN**: VPNs externas detectadas + OpenVPN própria
  (Tor-sobre-VPN), kill-switch libera exes da VPN, log embutido.
- **50 idiomas** no login e na topbar (PT/EN/ES completos, resto via EN),
  detecção automática do sistema.
- **Ícone caveira-cebola** (novo `assets/icon.png`/`.ico`).

### Mudado
- Login redesenhado (hero gradiente, logo real, pills) + `PassDialog`
  no mesmo visual.
- Topbar com "TorShield" fixo; página Proxy e sidebar no padrão dashboard
  (navegação roxo-clara no modo escuro).
- **Convidado entra sem senha** (config em texto local).
- Botão Adicionar mostra erro/sucesso inline em vez de falhar em silêncio.

## [1.2.0] — 2026-09-19 — Cofre AES-256 + usuários locais + IP em destaque

### Adicionado
- **Cofre AES-256-GCM** em tudo parado: `config.enc` + senha mestra
  (PBKDF2-SHA256 600k), porta no arranque (criar/pedir/trocar), triturar
  plaintext, `Trocar senha` no Diagnóstico.
- **Usuários locais (opcional)**: tela inicial com entrar/criar/excluir ou
  ir sem usuário; nomes criptografados (chave do dispositivo), senha por
  PBKDF2, cofre e dados Tor separados por usuário.
- **IP em destaque** no Início: número grande + país + copiar (e "…"
  enquanto busca).

## [1.1.1] — 2026-09-19 — Auditoria anti-dados-pessoais

### Privacidade (achado real corrigido)
- `config.json` guardava paths absolutos de apps (`C:\Users\<nome>\...`).
  Agora salva forma portátil (`%PROGRAMFILES%`, `%LOCALAPPDATA%`, …) e
  expande só em runtime (`sysprotect.portable/expand`); migração automática.
- Varredura completa: fonte sem nomes/paths/IPs/emails; exe sem username,
  hostname ou path de projeto (0 ocorrências); `torrc`/TOML gerados são
  cache funcional recriável (ver `🧹 Limpar dados`).

## [1.1.0] — 2026-09-19 — Home toggle, Scanner nmap, DNSCrypt combinado

### Adicionado
- Início com botão largo **Conectar/Desligar** (aperta p/ ligar, aperta p/
  desligar) além da cebola.
- Página **◉ Scanner**: usa o **nmap real** se instalado (Rápida, Serviços,
  Completa, SO, ping sweep, personalizado, --open, -Pn, salvar relatório)
  ou scanner embutido (top portas + banner + rDNS, opcional via Tor).
- **DNSCrypt combinado** (`Tor + local`): stub local sobe junto com o Tor;
  firewall já o libera junto. Terceiro modo na aba DNS.

## [1.0.2] — 2026-09-19 — Remoção total do Rust

### Removido
- Pasta `tor-shield/` inteira (fonte + `target/` de 14,9 GB).
- Toolchain Rust (`rustup self uninstall`: `.cargo` 0,76 GB + `.rustup`
  1,28 GB removidos; sem `cargo`/`rustc`/`rustup` na máquina).
- Dados do Arti (`%LOCALAPPDATA%\torproject`), temps de teste (`torprobe`,
  logs de sonda). Total liberado: **~17 GB**.
- Resto: só a pasta vazia `tor-shield/` (travada por Explorer/VS Code
  abertos nela — fechar e apagar manualmente).

## [1.0.1] — 2026-09-19 — Paridade total com o Rust

Auditoria item a item contra o TorShield Rust (v0.12): faltavam 4 coisas,
todas implementadas — cards de estatísticas no Início, botão Cancelar
conectando, botões Abrir pasta/Restaurar no Diagnóstico (métodos existiam,
sem botão), aviso WebTunnel na aba Pontes, 8 chaves i18n.

## [1.0.0] — 2026-09-19 — Migração Python + tor oficial

### Decidido
- Reescrita completa em **Python + PyQt6 + stem + tor.exe oficial**
  (Expert Bundle 15.0.23 em `vendor/`), após prova de que o Arti travava
  no consenso (`15%` / `Can't bootstrap a Tor directory`) enquanto o
  daemon C bootstrap 100% + `IsTor:true` + `NEWNYM` na mesma máquina/rede.

### Adicionado (paridade)
- Botão-cebola, fases, IP/país, nova identidade, bridges (Direto→custom,
  Colar, auto-ativa, lyrebird p/ obfs4), upstream, SOCKS, DNSCrypt,
  Proteção Total + por app, Logs (tor.log real), Diagnóstico (Tor/rede/wipe),
  Atualizar, menu ☰, temas, PT-BR/EN/ES, instância única, firewall auto.
