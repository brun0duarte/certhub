---
name: cert-manager-dev
description: |
  Skill especializada no desenvolvimento do CertHub — aplicação interna de gerenciamento
  do ciclo de vida de certificados digitais. Fornece contexto completo sobre a arquitetura,
  convenções de código, schema do banco de dados e guias de implementação para novas
  funcionalidades.

  Use esta skill quando estiver trabalhando em qualquer tarefa relacionada ao projeto
  CertHub localizado em /home/bruno/cert-manager.
---

# CertHub Dev — Skill de Desenvolvimento

## O que é o CertHub

O CertHub é uma aplicação web interna de gerenciamento do ciclo de vida de certificados digitais X.509. Serve a equipe de criptografia para:

- Gerenciar demandas de emissão, renovação e revogação de certificados
- Controlar locais de instalação e o ticket de mudança (WO/CRQ) vinculado, com checklist de ativação
- Inventariar certificados com ciclo de vida (pedido → instalado → fim_de_vida)
- Gerar e decodificar CSRs
- Validar cadeias de certificação
- Integrar com OpenSSL para operações de conversão e inspeção

## Stack Técnica

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11+, FastAPI, SQLite (via `sqlite3` stdlib) |
| Frontend | HTML + CSS + JavaScript vanilla (SPA com hash routing) |
| Autenticação | Sessão com cookie assinado (`itsdangerous`) |
| Crypto | `cryptography` (Hazmat + x509) |
| CLI | OpenSSL 3.x (via subprocess) |

## Localização do Projeto

```
/home/bruno/cert-manager/
├── README.md             # Visão geral, como rodar, abas da aplicação
├── .gemini/
│   ├── rules.md         # Regras e convenções do projeto
│   └── skills/          # Skills do projeto
├── app/
│   ├── main.py          # FastAPI app
│   ├── db.py            # Schema SQLite + migrations + seeds
│   ├── routers/         # Endpoints por domínio
│   └── services/        # Lógica reutilizável
├── data/
│   ├── certhub.db       # Banco SQLite
│   └── files/           # Arquivos de certificados
├── requirements.txt
└── docker-compose.yml
```

## Como Rodar Localmente

```bash
cd /home/bruno/cert-manager
# Ativar venv
source .venv/bin/activate  # Linux/Mac
# Iniciar servidor
python run.py              # ou: uvicorn app.main:app --reload
# Acesse: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

## Schema do Banco de Dados (resumo)

```
reqs             — Demandas (REQ0012345)
certificates     — Certificados X.509 importados
install_locations — Locais de instalação de certificados
install_tasks    — Checklist de ativação de CRQ (tarefas por demanda)
csrs             — CSRs geradas
users            — Usuários da aplicação
activity_log     — Histórico de ações
tasks            — Kanban de tarefas
docs             — Manuais e cheatsheets
reply_templates  — Templates de resposta para e-mail
settings         — Configurações da aplicação
```

## Como Adicionar um Novo Router

1. Criar `app/routers/meu_dominio.py`:
```python
from fastapi import APIRouter, HTTPException
from ..db import get_db, log_activity

router = APIRouter(tags=["meu-dominio"])

@router.get("/meu-dominio")
def list_items():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM ...").fetchall()]
    conn.close()
    return rows
```

2. Registrar em `app/main.py`:
```python
from .routers import meu_dominio
# ...
for router in (..., meu_dominio.router):
    app.include_router(router, prefix="/api")
```

## Como Adicionar uma Migration

Em `app/db.py`:
```python
SCHEMA_VN = """
ALTER TABLE existente ADD COLUMN nova_col TEXT NOT NULL DEFAULT '';
CREATE TABLE nova_tabela (...);
"""

# Em init_db():
if version < N:
    conn.executescript(SCHEMA_VN)
    conn.execute("PRAGMA user_version = N")
    conn.commit()
```

## Como Adicionar uma View no Frontend

Em `app/static/app.js`:
```javascript
views.minhaView = async () => {
  const data = await api("/meu-dominio");
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Título</div>
      <div class="view-sub">Subtítulo</div>
    </div></div>
    <!-- conteúdo -->
  `;
  // event listeners
};
```

Em `app/static/index.html`:
```html
<a href="#/minha-view" data-view="minhaView" title="Minha View">
  <span>🔧</span><span class="nav-txt">Minha View</span>
</a>
```

## Estado do Projeto

Sistema de usuários com autenticação/roles, ciclo de vida Geração → Instalação (mesma
REQ muda `demand_type`, nunca cria uma segunda linha), checklist de ativação de CRQ,
trilha de auditoria (`activity_log` + `views.auditoria`) e decoder geral (CSR/cert/
chave/PFX) já estão implementados. Operações em lote e o módulo dedicado de WO/CRQ
foram avaliados e removidos — WO/CRQ hoje é só campo livre (`external_wo`/`external_crq`)
dentro do fluxo de instalação, sem router próprio.

## Dicas Importantes

- **Nunca usar `shell=True`** em subprocess — segurança
- **Sempre escapar** dados do servidor com `esc()` no frontend antes de interpolar em HTML
- **Sempre fechar** a conexão com `conn.close()` após uso
- **Manter retrocompatibilidade** nas migrations — nunca fazer DROP
- O arquivo `app/static/app.js` tem ~1840 linhas — navegue por seções comentadas
