# CertHub — Plano de Desenvolvimento MVP

> **Objetivo**: Transformar o CertHub em um produto funcional e robusto para gerenciamento do ciclo de vida de certificados digitais, com controle de demandas, usuários, integração OpenSSL e categorização inteligente de certificados.

---

## Visão Geral

```
Estado atual                      →   Estado desejado (MVP)
──────────────────────────────────────────────────────────────────
Demandas simples (REQ)            →   Ciclo completo: Geração → WO/CRQ → Instalação
Sem controle de acesso            →   Sistema de usuários com perfis
Operações em lote (remover)       →   Removido e limpo
Certificados sem ciclo de vida    →   6 estados de ciclo de vida
Sem integração OpenSSL            →   Toolbox OpenSSL integrado
Sem agentes/skills configurados   →   Agentes e skills configurados
```

---

## Épicos e Tarefas

### ÉPICO 1 — Remoção de Operações em Lote
> **Prioridade: Alta** | Deve ser feita primeiro pois simplifica a base de código

- [ ] **1.1** Remover o router `batch.py` e desregistrá-lo em `main.py`
- [ ] **1.2** Remover as tabelas `batch_ops` e `batch_op_items` do schema (manter retrocompatibilidade com migration)
- [ ] **1.3** Remover a aba "Op. em Lote" do `index.html` (nav link)
- [ ] **1.4** Remover a view `views.batch` e código relacionado em `app.js`
- [ ] **1.5** Mover os fluxos Mermaid (FLOWS) para o router de demandas como documentação de processo
- [ ] **1.6** Limpar imports e referências órfãs

---

### ÉPICO 2 — Sistema de Usuários
> **Prioridade: Alta** | Base para controle de acesso

#### Backend
- [ ] **2.1** Criar tabela `users` no schema (`SCHEMA_V6`):
  ```sql
  CREATE TABLE users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE,
      display_name TEXT NOT NULL DEFAULT '',
      email TEXT NOT NULL DEFAULT '',
      role TEXT NOT NULL DEFAULT 'viewer'
          CHECK (role IN ('admin','operator','viewer')),
      password_hash TEXT NOT NULL,
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
  );
  ```
- [ ] **2.2** Criar router `users.py` com endpoints:
  - `GET /users` — listar usuários (admin)
  - `POST /users` — criar usuário (admin)
  - `PUT /users/{id}` — editar usuário (admin)
  - `DELETE /users/{id}` — desativar usuário (admin)
  - `POST /users/{id}/reset-password` — redefinir senha (admin)
  - `GET /users/me` — perfil do usuário autenticado
  - `PUT /users/me` — atualizar próprio perfil
- [ ] **2.3** Implementar autenticação via sessão com cookie:
  - `POST /auth/login` — autenticar e criar sessão
  - `POST /auth/logout` — encerrar sessão
  - Hash de senhas com `hashlib.pbkdf2_hmac`
- [ ] **2.4** Criar middleware de autenticação em `main.py`
- [ ] **2.5** Seed do usuário admin padrão (`admin` / `certhub@2025`)
- [ ] **2.6** Registrar `user_id` no `activity_log` (adicionar coluna via migration)
- [ ] **2.7** Adicionar campo `assigned_to` nas demandas (referência a user_id)

#### Frontend
- [ ] **2.8** Criar tela de login (`/login`) com formulário de autenticação
- [ ] **2.9** Criar view de administração de usuários (`#/users`)
- [ ] **2.10** Exibir usuário logado no sidebar (nome + role badge)
- [ ] **2.11** Controlar visibilidade de ações por role (admin vs operator vs viewer)
- [ ] **2.12** Adicionar opção de logout no sidebar

---

### ÉPICO 3 — Ciclo de Vida de Demandas (Geração → Instalação via WO/CRQ)
> **Prioridade: Alta** | Core do produto

#### Conceito
Quando uma demanda de **geração/emissão** é concluída (certificado emitido), o sistema cria automaticamente (ou sugere criar) uma **demanda de instalação** vinculada, por meio de uma WO (Work Order) ou CRQ (Change Request).

#### Backend
- [ ] **3.1** Criar tabela `work_orders` no schema:
  ```sql
  CREATE TABLE work_orders (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      wo_number TEXT NOT NULL UNIQUE,     -- WO0012345 ou CRQ0012345
      wo_type TEXT NOT NULL DEFAULT 'WO'
          CHECK (wo_type IN ('WO','CRQ')),
      req_id INTEGER REFERENCES reqs(id) ON DELETE SET NULL,
      parent_req_id INTEGER REFERENCES reqs(id) ON DELETE SET NULL,
      title TEXT NOT NULL DEFAULT '',
      description TEXT DEFAULT '',
      status TEXT NOT NULL DEFAULT 'aberta'
          CHECK (status IN ('aberta','em_andamento','concluida','cancelada')),
      scheduled_at TEXT,
      completed_at TEXT,
      assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
      updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
  );
  ```
- [ ] **3.2** Criar router `work_orders.py` com CRUD completo
- [ ] **3.3** Lógica de criação automática: quando `req.status` muda para `cert_emitido`, sugerir criação de WO/CRQ de instalação
- [ ] **3.4** Endpoint `POST /reqs/{req_id}/create-installation-wo` — cria WO vinculada
- [ ] **3.5** Sugestão automática: ambientes PRD → recomendar CRQ; outros → WO
- [ ] **3.6** Campo `wo_number` (referência externa) na tabela `reqs` para rastrear WOs do ServiceNow

#### Frontend
- [ ] **3.7** Criar view de Work Orders (`#/work-orders`)
- [ ] **3.8** No detalhe da demanda: exibir WOs vinculadas e botão "Criar WO de Instalação"
- [ ] **3.9** Modal de criação de WO/CRQ: número, tipo (WO/CRQ), descrição, responsável, data prevista
- [ ] **3.10** Quando status muda para `cert_emitido`: prompt sugerindo criação de WO de instalação
- [ ] **3.11** Badge visual na listagem de demandas indicando se tem WO vinculada
- [ ] **3.12** Dashboard: card com contagem de WOs abertas

---

### ÉPICO 4 — Categorização do Ciclo de Vida dos Certificados
> **Prioridade: Média** | Controle de inventário

#### Estados do certificado (lifecycle)

| Estado          | Descrição                                        |
|-----------------|--------------------------------------------------|
| `pedido`        | CSR gerada, aguardando emissão pela CA           |
| `instalado`     | Certificado emitido e instalado em produção      |
| `em_inventario` | Disponível mas não instalado                     |
| `reservado`     | Reservado para uso futuro / em instalação        |
| `excluir`       | Marcado para exclusão / revogação pendente       |
| `fim_de_vida`   | Vencido, revogado ou fora de uso                 |

#### Backend
- [ ] **4.1** Adicionar coluna `lifecycle_status` na tabela `certificates` via migration `SCHEMA_V7`
- [ ] **4.2** Atualizar `CertUpdate` model para aceitar `lifecycle_status`
- [ ] **4.3** Regras de transição automática:
  - Cert importado sem REQ → `em_inventario`
  - Cert com `not_after` no passado → `fim_de_vida`
  - Cert com local de instalação registrado → `instalado`
- [ ] **4.4** Endpoint `PUT /certs/{id}/lifecycle` para atualizar status manualmente
- [ ] **4.5** Filtro por `lifecycle_status` no `GET /certs`
- [ ] **4.6** Dashboard: contagem por `lifecycle_status`

#### Frontend
- [ ] **4.7** Badge colorido de lifecycle em todas as listagens de certificados
- [ ] **4.8** Filtro de lifecycle na view Certificados
- [ ] **4.9** Edição rápida de lifecycle via dropdown inline
- [ ] **4.10** Painel de lifecycle no Dashboard (contadores por estado)

---

### ÉPICO 5 — Integração com OpenSSL
> **Prioridade: Média** | Toolbox prático

#### Backend
- [ ] **5.1** Criar serviço `openssl.py` em `app/services/`:
  - Verificar se `openssl` está no PATH
  - Wrapper seguro para comandos com timeout e sanitização de inputs
- [ ] **5.2** Criar router `openssl_tools.py` com endpoints:
  - `POST /openssl/inspect` — inspecionar cert/CSR/PFX (retorna texto formatado + metadados)
  - `POST /openssl/convert` — converter formatos (PEM↔DER, PFX→PEM, PEM→PFX)
  - `POST /openssl/verify-chain` — verificar cadeia com `openssl verify`
  - `POST /openssl/check-match` — verificar se chave+CSR+cert combinam (modulus)
  - `POST /openssl/s-client` — checar certificado de servidor por hostname:porta
  - `GET /openssl/version` — retornar versão do openssl instalado
- [ ] **5.3** Segurança: sanitizar inputs, evitar injeção, usar subprocess com lista de args (nunca shell=True)
- [ ] **5.4** Todos os endpoints retornam `{ stdout, stderr, command_display }` para transparência

#### Frontend
- [ ] **5.5** Criar view "Toolbox OpenSSL" (`#/openssl`) com tabs:
  - **Inspecionar**: upload de arquivo → saída formatada
  - **Converter**: upload + seleção de formato destino → download
  - **Verificar Cadeia**: upload cert + cadeia → resultado visual
  - **Match Key/CSR/Cert**: 3 uploads → comparação de modulus
  - **S-Client**: input hostname:porta → resultado do handshake
- [ ] **5.6** Exibir sempre o comando OpenSSL equivalente executado
- [ ] **5.7** Botão "Copiar comando" para cada operação
- [ ] **5.8** Link para a Toolbox a partir dos detalhes de certificado

---

### ÉPICO 6 — Refatorações e Melhorias Gerais
> **Prioridade: Baixa/Média**

- [ ] **6.1** Reorganizar `app.js` em seções comentadas (arquivo está com ~1840 linhas)
- [ ] **6.2** Tratamento de erros melhorado no frontend
- [ ] **6.3** Confirmação antes de excluir recursos (modal de confirmação genérico)
- [ ] **6.4** Paginação na listagem de demandas e certificados
- [ ] **6.5** Filtros avançados na view de Certificados
- [ ] **6.6** Exportar CSV de demandas/certificados

---

### ÉPICO 7 — Configuração de Agentes e Skills
> **Prioridade: Média**

- [ ] **7.1** Criar skill `cert-manager-dev` com contexto do projeto (arquitetura, convenções, schema)
- [ ] **7.2** Criar arquivo `.gemini/rules.md` com regras do projeto
- [ ] **7.3** Criar skill de referência OpenSSL com comandos e exemplos
- [ ] **7.4** Criar skill de segurança de certificados (boas práticas, checklist)

---

## Ordem de Implementação Recomendada

```
Sprint 1 (Limpeza e Base)
  ├── ÉPICO 1: Remover batch operations
  └── ÉPICO 2: Sistema de usuários

Sprint 2 (Fluxo Principal)
  ├── ÉPICO 3: Ciclo de vida WO/CRQ
  └── ÉPICO 4: Lifecycle dos certificados

Sprint 3 (Ferramentas e Polimento)
  ├── ÉPICO 5: Integração OpenSSL
  └── ÉPICO 6: Refatorações gerais

Sprint 4 (Infraestrutura de Dev)
  └── ÉPICO 7: Agentes e Skills
```

---

## Decisões de Design

### Autenticação
- MVP usa **sessão com cookie** (sem JWT) — mais simples e suficiente para uso interno
- Senha do admin inicial: `certhub@2025` (deve ser trocada no primeiro login)
- Roles: `admin` (tudo), `operator` (CRUD de demandas/certs), `viewer` (só leitura)

### WO vs CRQ
- **WO (Work Order)**: para ambientes não-PRD ou instalações sem janela de mudança
- **CRQ (Change Request)**: obrigatório para PRD — campo `scheduled_at` obrigatório
- O sistema sugere automaticamente CRQ quando ambiente for `PRD`

### Lifecycle de Certificados
- Transição semi-automática: sistema sugere com base em regras, operador pode sobrescrever
- `fim_de_vida` é aplicado automaticamente quando `not_after < now`

---

## Arquivos a Criar/Modificar

```
cert-manager/
├── plan.md                          ← Este arquivo ✅
├── app/
│   ├── main.py                      ← Modificar: remover batch, adicionar users/wo/openssl
│   ├── db.py                        ← Modificar: SCHEMA_V6 (users), V7 (lifecycle), V8 (work_orders)
│   ├── routers/
│   │   ├── batch.py                 ← REMOVER
│   │   ├── users.py                 ← CRIAR
│   │   ├── auth.py                  ← CRIAR
│   │   ├── work_orders.py           ← CRIAR
│   │   └── openssl_tools.py         ← CRIAR
│   ├── services/
│   │   ├── auth.py                  ← CRIAR (session management, password hashing)
│   │   └── openssl.py               ← CRIAR (subprocess wrapper)
│   └── static/
│       ├── app.js                   ← Modificar: remover batch, adicionar users/wo/openssl/lifecycle
│       ├── index.html               ← Modificar: nav links
│       └── styles.css               ← Modificar: lifecycle badges, login page
└── .gemini/
    ├── rules.md                     ← CRIAR
    └── skills/
        ├── cert-manager-dev/
        │   └── SKILL.md             ← CRIAR
        └── openssl-reference/
            └── SKILL.md             ← CRIAR
```

---

## Dependências Técnicas

| Pacote | Uso | Status |
|--------|-----|--------|
| `cryptography` | Parse de certs, conversões | ✅ Instalado |
| `hashlib` (stdlib) | Hash de senhas de usuários | ✅ Built-in |
| `itsdangerous` | Sessões seguras (cookie signing) | ❌ Adicionar |
| `openssl` (CLI) | Toolbox OpenSSL | ⚠️ Verificar no ambiente |
| `starlette.middleware` | Session middleware | ✅ Via FastAPI |

---

## Checklist de Qualidade (por Épico)

Antes de marcar um épico como completo:
- [ ] Endpoints testados via `/docs` (FastAPI Swagger)
- [ ] Sem imports não utilizados
- [ ] Migrations não quebram dados existentes
- [ ] Frontend: sem erros no console do browser
- [ ] Mensagens de erro claras para o usuário
- [ ] Activity log atualizado para ações importantes
