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
| 📊 Dashboard | Vencimentos (≤30/60/90 dias), REQs por status/ambiente, atividade |
| 📋 Demandas | CRUD de REQs com senha automática, notas, locais de instalação, histórico |
| 📝 Gerar CSR | Wildcard/SAN via `cryptography`, `.inf` p/ certreq ou HSM (hsmutil) |
| 📜 Certificados | Importa .cer/.pem/.der/.pfx e lê os campos automaticamente |
| 🔑 Senhas | Gerador com política configurável (módulo `secrets`) |
| 📖 Manuais | Guias de instalação + cheatsheets certutil/certreq/openssl/keytool |
| ⚙️ Configurações | Pastas, alertas, política de senha, templates do HSM |

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
