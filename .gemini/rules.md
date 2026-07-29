# CertHub — Regras do Projeto

## Contexto
O CertHub é uma aplicação interna de gerenciamento do ciclo de vida de certificados digitais, desenvolvida em **FastAPI + SQLite + SPA vanilla JS**.

Consulte `plan.md` na raiz do projeto para o plano de desenvolvimento completo.

---

## Arquitetura

```
app/
  main.py          # FastAPI app, registro de routers, middleware
  db.py            # Schema SQLite, migrações versionadas, seeds, helpers
  routers/         # Um arquivo por domínio (reqs, certs, users, etc.)
  services/        # Lógica pura reutilizável (crypto, parsing, openssl)
  static/
    app.js         # SPA vanilla JS — todas as views estão aqui
    index.html     # Shell HTML — apenas nav e containers
    styles.css     # CSS customizado (dark mode, tokens CSS)
```

---

## Convenções de Código

### Backend (Python / FastAPI)

- **Routers**: um arquivo por domínio em `app/routers/`. Sempre usar `APIRouter(tags=[...])`.
- **Modelos Pydantic**: `XxxIn` para input, `XxxUpdate` para PATCH parcial.
- **Banco de dados**: sempre usar `conn = get_db()` e `conn.close()` — sem ORM.
- **Migrations**: schema versionado via `PRAGMA user_version`. Nunca alterar schemas existentes, apenas adicionar `SCHEMA_Vn` e incrementar o `user_version`.
- **Activity log**: chamar `log_activity(conn, action, detail, req_id)` para todas as ações importantes.
- **Erros**: usar `raise HTTPException(status_code, "mensagem clara")` — mensagens em português.
- **Segurança**: nunca usar `shell=True` em subprocess. Sempre usar lista de argumentos.
- **Imports**: agrupar em stdlib → third-party → local; separados por linha em branco.

### Frontend (JavaScript)

- **SPA**: todas as views são funções em `views.{nome}` e registradas no objeto `views`.
- **API calls**: sempre usar a função `api(path, opts)` — nunca `fetch` diretamente.
- **HTML dinâmico**: sempre usar `esc(valor)` ao interpolar dados do servidor no HTML.
- **Toasts**: `toast("mensagem", "ok"|"err")` para feedback ao usuário.
- **Modais**: usar a função `modal(title, bodyHtml, { footer, large })`.
- **Navegação**: links de nav via `#/nome-da-view` — hash routing.
- **Sem frameworks**: não usar React, Vue, etc. — vanilla JS puro.

### CSS

- Usar variáveis CSS (`--var-name`) para cores e tokens do design system.
- Sempre usar o tema dark por padrão (`data-theme="dark"` no `<html>`).
- Classes utilitárias existentes: `.btn`, `.btn-primary`, `.btn-danger`, `.btn-ghost`, `.input`, `.badge`, `.badge-*`, `.panel`, `.tbl`, `.grid`, `.modal`, `.toast`.

---

## Padrões de Nomenclatura

| Contexto | Convenção | Exemplo |
|----------|-----------|---------|
| Tabelas SQL | snake_case singular | `work_order`, `certificate` |
| Colunas SQL | snake_case | `created_at`, `req_id` |
| Routers Python | snake_case | `work_orders.py` |
| Funções Python | snake_case | `create_work_order()` |
| Endpoints URL | kebab-case | `/work-orders/{id}` |
| Views JS | camelCase | `views.workOrders` |
| IDs HTML | kebab-case | `id="wo-number"` |
| Classes CSS | kebab-case | `.badge-instalado` |

---

## Segurança

- **Autenticação**: toda requisição (exceto `/auth/login` e `/static`) deve verificar sessão ativa.
- **Autorização**: endpoints destrutivos (DELETE) e administrativos (usuários) exigem role `admin`.
- **Validação de inputs**: validar no Pydantic E na camada SQL (constraints CHECK).
- **Senhas**: usar `hashlib.pbkdf2_hmac('sha256', ...)` com salt aleatório. Nunca armazenar em texto claro.
- **Subprocess**: sempre `subprocess.run([...], capture_output=True, timeout=30)` — nunca `shell=True`.
- **Upload de arquivos**: validar extensão e tamanho máximo (10MB). Sanitizar nome com `folders.sanitize()`.

---

## Padrão de Response das APIs

```python
# Sucesso com dados
return row  # dict ou lista de dicts

# Sucesso sem dados
return {"ok": True}

# Erro
raise HTTPException(400, "Mensagem de erro clara em português")

# Criação
return row  # retornar o recurso criado (201 implícito no FastAPI)
```

---

## Migrações de Banco de Dados

```python
# Em db.py — adicionar novo SCHEMA_Vn:
SCHEMA_V8 = """
CREATE TABLE nova_tabela (...);
ALTER TABLE existente ADD COLUMN nova_col TEXT NOT NULL DEFAULT '';
"""

# Em init_db():
if version < 8:
    conn.executescript(SCHEMA_V8)
    conn.execute("PRAGMA user_version = 8")
    conn.commit()
```

**Regra**: nunca fazer `DROP TABLE` ou remover colunas em migrations — manter retrocompatibilidade.

---

## Fluxo de Trabalho

1. Implementar backend (router + serviço + migration) primeiro
2. Testar via `/docs` (FastAPI Swagger UI)
3. Implementar frontend (view JS + estilos CSS)
4. Testar end-to-end no browser
5. Atualizar `plan.md` marcando as tarefas concluídas

---

## Referências Rápidas

- **Schema atual**: `app/db.py` — função `init_db()`
- **Constantes compartilhadas**: `app/db.py` (topo do arquivo) e `app/static/app.js` (topo)
- **Plano de desenvolvimento**: `plan.md`
- **Dados de demo**: `scripts/demo_data.py`
