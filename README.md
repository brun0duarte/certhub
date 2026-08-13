# 🔐 CertHub — Gerenciador de Certificados Digitais

Aplicação web **local** para gerenciar todo o ciclo de vida de certificados digitais:
demandas (REQ), geração de senhas, CSRs (wildcard/SAN), leitura automática de
certificados, locais de instalação, manuais/comandos úteis e painel de vencimentos.

## Como rodar

### Windows (trabalho)
```bat
run.bat
```
Cria o venv, instala as dependências e abre o navegador em `http://127.0.0.1:8477`.

### Linux/macOS
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

### Docker
```bash
docker compose up -d --build
# acessa em http://127.0.0.1:8477 — dados persistem em ./data
```
> Nota: no container os engines que dependem do SO (certreq, abrir pasta no
> Explorer, hsmutil instalado no host) ficam indisponíveis; o engine **local**
> de CSR e todo o restante funcionam normalmente.

## Abas

| Aba | O que faz |
|---|---|
| 📊 Dashboard | Vencimentos (≤30/60/90 dias), REQs por status/ambiente, gráficos e atividade recente |
| 📡 Monitor | Painel dedicado de vencimentos, com sinalização para renovação |
| 📋 Geração | Demandas de geração/recebimento/renovação/revogação — CRUD com senha automática, aba "Certificado Gerado" (CSR) x "Certificado Importado" |
| 🔧 Instalação | Demanda avança pra fase de instalação (mesma REQ, muda `demand_type`) — ticket WO/CRQ, checklist de ativação com templates de tarefa/mensagem, evidências e notas |
| 🗄️ Histórico | Busca global por qualquer demanda, incluindo concluídas/canceladas |
| 🗂️ Kanban | Quadro de tarefas dos projetos — colunas, prioridades, categorias, drag-and-drop, busca |
| 📝 Gerar CSR | Wildcard/SAN via `cryptography`, `.inf` p/ certreq ou HSM (hsmutil) |
| 🔍 Decoder | Decoder geral com auto-detecção: CSR, certificado, chave privada ou PFX (PEM/DER) |
| 📜 Certificados | Importa e classifica (servidor/cliente mTLS/CA), filtra por emissor/ambiente, cadeia completa com PEM copiável |
| 🔗 Validar cadeia | Análise elo a elo (assinaturas, validade, hostname), AIA e servidor remoto TLS |
| 🔑 Senhas | Gerador com política configurável (módulo `secrets`), cópia individual ou de todas |
| 📖 Manuais & Comandos | Guias de instalação (Apache, Nginx, IIS, Tomcat, Azure Key Vault, AWS ACM/Secrets Manager, mainframe RACDCERT, Azion, Windows Server, Akamai) + cheatsheets certutil/certreq/openssl/keytool |
| 👥 Usuários | Gestão de contas, roles (admin/operator/viewer) |
| 🕵️ Auditoria | Log de toda ação registrada no sistema — quem criou/editou o quê e quando, com filtros por usuário/ação/busca |
| 🎨 Aparência | Tema claro/escuro, menu lateral/compacto/horizontal, cor de destaque |
| ⚙️ Configurações | Pastas, alertas, política de senha, templates do HSM e de resposta |

## Autenticação

Toda a API exige sessão autenticada (cookie assinado via `itsdangerous`). Usuário admin
padrão criado no primeiro boot: `admin` / `certhub@2025` — **senha de desenvolvimento,
troque antes de qualquer uso além de demonstração local.**

## Dados de demonstração

```bash
.venv/bin/python scripts/demo_data.py           # cria usuários/demandas/certificados fictícios (bancofic.com.br)
.venv/bin/python scripts/demo_data.py --remove  # remove tudo que o script criou (usuários são preservados)
```

### Usuários de demonstração

Além do `admin`, o seed cria 5 contas de teste (senha `{usuário}@2026`, ex. `alex@2026`):

| Usuário | Role | Senha |
|---|---|---|
| alex | admin | `alex@2026` |
| bruno | admin | `bruno@2026` |
| carlos | operator | `carlos@2026` |
| davi | operator | `davi@2026` |
| leonardo | viewer | `leonardo@2026` |

## Estrutura de pastas por demanda

`{base}/{ENV}/{REQ}_{CN}/` com subpastas `csr/`, `cert/` e `backup/` — template
configurável na aba Configurações.

## HSM (Dinamo Networks)

v1 integra via **hsmutil** (templates de comando configuráveis em Configurações).
A integração com o SDK JavaScript oficial (helper Node.js) está planejada — ver
`app/services/hsm/dinamo_js.py`.

## Segurança (v1)

As senhas ficam em texto puro no SQLite local (`data/certhub.db`), por decisão
de simplicidade. Não exponha a porta para a rede; upgrade planejado: senha
mestra + criptografia (PBKDF2 + Fernet).
