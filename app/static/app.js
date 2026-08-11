/* CertHub — SPA vanilla */
"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];
const main = $("#main");

/* ---------------- helpers ---------------- */
async function api(path, opts = {}) {
  if (opts.json !== undefined) {
    opts.body = JSON.stringify(opts.json);
    opts.headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    delete opts.json;
  }
  const res = await fetch("/api" + path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

function toast(msg, type = "ok") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  $("#toast-root").appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function copyText(text, label = "Copiado!") {
  try {
    await navigator.clipboard.writeText(text);
  } catch (_) {
    const ta = document.createElement("textarea");
    ta.value = text; document.body.appendChild(ta);
    ta.select(); document.execCommand("copy"); ta.remove();
  }
  toast(label);
}

function modal(title, bodyHtml, { footer = "", large = false } = {}) {
  const root = $("#modal-root");
  root.innerHTML = `
    <div class="modal-overlay">
      <div class="modal ${large ? "modal-lg" : ""}">
        <div class="modal-header">
          <h2>${title}</h2>
          <button class="btn btn-ghost btn-sm" data-close>&times;</button>
        </div>
        <div class="modal-body">${bodyHtml}</div>
        ${footer ? `<div class="modal-footer">${footer}</div>` : ""}
      </div>
    </div>`;

  const overlay = $(".modal-overlay", root);
  if (overlay) {
    overlay.onclick = e => {
      if (e.target === overlay || e.target.closest("[data-close]")) closeModal();
    };
  }
  return root;
}

function closeModal() { $("#modal-root").innerHTML = ""; }

window.showSanModal = function(mainCn, sansString) {
  const sans = (sansString || "")
    .split(",")
    .map(s => s.trim().replace(/^dns:/i, '').replace(/^ip:/i, ''))
    .filter(Boolean);
  const uniqueSans = Array.from(new Set(sans));
  
  modal(`🏷️ Subject Alternative Names (SANs) — ${esc(mainCn)}`, `
    <div class="banner banner-info" style="margin-bottom:14px">
      Este certificado foi emitido como <strong>Multi-Domínio / SAN</strong> e é válido para os <strong>${uniqueSans.length} nomes alternativos</strong> listados abaixo.
      A busca no sistema por qualquer um destes nomes identificará este certificado.
    </div>

    <div class="field"><label>CN Principal (Common Name)</label>
      <div style="display:flex;gap:6px">
        <input class="input mono" value="${esc(mainCn)}" readonly>
        <button class="btn btn-sm" onclick="copyText('${esc(mainCn)}', 'CN copiado!')">📋 Copiar</button>
      </div>
    </div>

    <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Nomes Alternativos (${uniqueSans.length})</h3>
    <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(240px, 1fr));gap:8px;max-height:300px;overflow-y:auto;padding:4px">
      ${uniqueSans.map(san => `
        <div class="badge" style="padding:8px 10px;font-family:var(--font-mono);font-size:12px;display:flex;align-items:center;justify-content:space-between;background:var(--bg-sunken);border:1px solid var(--border);border-radius:6px">
          <span>🌐 <strong>${esc(san)}</strong></span>
          <div style="display:flex;gap:4px">
            <button class="btn btn-sm btn-ghost" style="padding:1px 5px" title="Copiar este SAN" onclick="copyText('${esc(san)}', 'SAN copiado!')">📋</button>
            <button class="btn btn-sm btn-ghost" style="padding:1px 5px" title="Filtrar por este SAN" onclick="closeModal(); location.hash='#/certs'; setTimeout(() => { const el=$('#cf-search'); if(el){ el.value='${esc(san)}'; el.oninput(); } }, 200)">🔍</button>
          </div>
        </div>
      `).join('')}
    </div>
  `, { large: true, footer: `<button class="btn" data-close>Fechar</button>` });
};


const ENVS = ["PRD", "TQS", "HMP", "DES"];
const STATUSES = ["aberta", "csr_gerada", "cert_emitido", "instalado", "concluida", "cancelada"];
const STATUS_LABEL = {
  aberta: "Aberta", csr_gerada: "CSR gerada", cert_emitido: "Cert. emitido",
  instalado: "Instalado", concluida: "Concluída", cancelada: "Cancelada",
};
const DEMAND_TYPES = {
  geracao: "Geração", recebimento: "Recebimento", revogacao: "Revogação",
  instalacao: "Instalação",
  // Legacy types for backwards compat
  emissao: "Emissão", renovacao: "Renovação",
  usuario: "Cert. Usuário", instalacao_existente: "Instalação Existente", outro: "Outro",
};
const CERT_CATEGORIES = {
  sectigo_dv: "Sectigo DV", sectigo_ov: "Sectigo OV", sectigo_ev: "Sectigo EV",
  ac_interna_apl_prd: "AC Interna APL (PRD)", ac_icp_testes: "AC ICP Testes",
  apple: "Apple", bandeiras: "Bandeiras (Elo/Visa)", parceiro_externo: "Parceiro Externo",
  sepro: "Sepro", outro: "Outro",
};
const INSTALL_TYPES = {
  mainframe: "Mainframe", balanceador: "Balanceador",
  keyvault_azure: "Key Vault Azure", aws_cert_manager: "AWS Cert Manager",
  secrets_manager: "Secrets Manager", azion: "Azion", akamai: "Akamai",
  iis: "IIS", apache: "Apache", nginx: "Nginx", tomcat: "Tomcat", outro: "Outro",
};
const LIFECYCLE_STATUS = {
  pedido: 'Pedido',
  instalado: 'Instalado',
  em_inventario: 'Em Inventário',
  reservado: 'Reservado',
  excluir: 'Excluir',
  fim_de_vida: 'Fim de Vida',
  em_renovacao: 'Em Renovação',
};
const INSTALL_TASK_STATUS = { pendente: 'Pendente', em_andamento: 'Em andamento', sucesso: 'Sucesso', falha: 'Falha' };
const OWNERSHIP_LABEL = { interno: 'Privado (Interno)', externo: 'Público (Externo)' };
const ownershipBadge = o => {
  const isPub = o === 'externo' || o === 'publico';
  return `<span class="badge ${isPub ? 'badge-purple' : 'badge-blue'}" title="${isPub ? 'Certificado Público / Chave privada não controlada internamente' : 'Certificado Privado / Chave privada controlada internamente'}">${isPub ? '🌐 Público' : '🔒 Privado'}</span>`;
};

const envBadge = e => `<span class="badge badge-${esc(e)}">${esc(e)}</span>`;
const statusBadge = s => `<span class="badge badge-${esc(s)}">${esc(STATUS_LABEL[s] || s)}</span>`;
const demandBadge = d => `<span class="badge badge-demand-${esc(d)}">${esc(DEMAND_TYPES[d] || d)}</span>`;
const lifecycleBadge = s => `<span class="badge badge-lc-${esc(s)}">${esc(LIFECYCLE_STATUS[s] || s)}</span>`;
function daysBadge(days) {
  if (days === null || days === undefined) return "";
  const cls = days < 0 ? "days-danger" : days <= 30 ? "days-danger" : days <= 60 ? "days-warn" : "days-ok";
  const label = days < 0 ? `vencido há ${-days}d` : `${days}d restantes`;
  return `<span class="badge badge-${cls}">${label}</span>`;
}
const fmtDate = s => (s ? String(s).slice(0, 10).split("-").reverse().join("/") : "—");
const fmtDateTime = s => (s ? fmtDate(s) + " " + String(s).slice(11, 16) : "—");

/* mini renderizador de markdown (títulos, código, listas, negrito, links) */
function renderMd(src) {
  const lines = String(src).split("\n");
  let html = "", inCode = false, codeBuf = [], listType = null;
  const closeList = () => { if (listType) { html += `</${listType}>`; listType = null; } };
  const inline = t => esc(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
  for (const line of lines) {
    if (line.trimStart().startsWith("```")) {
      if (inCode) {
        html += `<pre class="code-block"><button class="btn btn-sm copy-btn" data-copy-code>Copiar</button><code>${esc(codeBuf.join("\n"))}</code></pre>`;
        codeBuf = [];
      }
      inCode = !inCode; continue;
    }
    if (inCode) { codeBuf.push(line); continue; }
    const h = line.match(/^(#{1,3})\s+(.*)/);
    if (h) { closeList(); html += `<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`; continue; }
    const li = line.match(/^\s*[-*]\s+(.*)/);
    if (li) {
      if (listType !== "ul") { closeList(); html += "<ul>"; listType = "ul"; }
      html += `<li>${inline(li[1])}</li>`; continue;
    }
    const ol = line.match(/^\s*\d+\.\s+(.*)/);
    if (ol) {
      if (listType !== "ol") { closeList(); html += "<ol>"; listType = "ol"; }
      html += `<li>${inline(ol[1])}</li>`; continue;
    }
    closeList();
    if (line.startsWith(">")) { html += `<blockquote>${inline(line.slice(1).trim())}</blockquote>`; continue; }
    if (line.trim() === "") continue;
    html += `<p>${inline(line)}</p>`;
  }
  closeList();
  if (inCode && codeBuf.length)
    html += `<pre class="code-block"><code>${esc(codeBuf.join("\n"))}</code></pre>`;
  return html;
}

/* ---------------- roteamento ---------------- */
const views = {};
let csrPrefill = null;

async function navigate() {
  const name = (location.hash || "#/dashboard").replace("#/", "").split("?")[0];
  const view = views[name] || views.dashboard;
  $$("#nav a").forEach(a => a.classList.toggle("active", a.dataset.view === name));
  main.innerHTML = `<div class="empty">Carregando…</div>`;
  try { await view(); } catch (e) { main.innerHTML = `<div class="empty">Erro: ${esc(e.message)}</div>`; }
}
window.addEventListener("hashchange", navigate);

/* ---------------- Dashboard ---------------- */
views.dashboard = async () => {
  const d = await api("/dashboard");
  const exp = d.expiring;
  const alerts = d.alert_days;
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Dashboard</div>
      <div class="view-sub">Visão geral das demandas e vencimentos</div>
    </div></div>
    <div class="grid grid-cards">
      <div class="stat-card stat-red"><div class="stat-value">${exp.vencidos}</div><div class="stat-label">Vencidos</div></div>
      ${alerts.map((a, i) => `
        <div class="stat-card ${i === 0 ? "stat-red" : i === 1 ? "stat-amber" : "stat-green"}">
          <div class="stat-value">${exp["ate_" + a]}</div>
          <div class="stat-label">Vencem em ≤ ${a} dias</div>
        </div>`).join("")}
      <div class="stat-card stat-accent"><div class="stat-value">${d.totals.reqs_abertas}</div><div class="stat-label">REQs em aberto</div></div>
      <div class="stat-card"><div class="stat-value">${d.totals.certificados}</div><div class="stat-label">Certificados</div></div>
    </div>
    ${d.lifecycle ? `
    <div class="panel mt">
      <h3>Certificados por Lifecycle</h3>
      <div class="lc-grid">
        ${Object.entries(d.lifecycle).map(([s, n]) => 
          `<div class="lc-stat">${lifecycleBadge(s)}<span class="lc-n">${n}</span></div>`
        ).join('')}
      </div>
    </div>` : ''}
    <div class="grid grid-2 mt">
      <div class="panel">
        <h3>Próximos vencimentos</h3>
        ${d.next_expiring.length ? `<table class="tbl"><thead><tr><th>CN</th><th>REQ</th><th>Vence</th><th></th></tr></thead>
          <tbody>${d.next_expiring.map(c => `
            <tr><td>${esc(c.cn)}</td>
                <td class="mono">${esc(c.req_number || "—")} ${c.env ? envBadge(c.env) : ""}</td>
                <td>${fmtDate(c.not_after)}</td>
                <td>${daysBadge(c.days_left)}</td></tr>`).join("")}
          </tbody></table>` : `<div class="empty">Nenhum certificado próximo do vencimento 🎉</div>`}
      </div>
      <div class="panel">
        <h3>Atividade recente</h3>
        ${d.activity.length ? `<ul class="timeline">${d.activity.map(a => `
          <li><div>${esc(a.action.replaceAll("_", " "))} ${a.req_number ? `<span class="mono">· ${esc(a.req_number)}</span>` : ""}</div>
              <div class="muted">${esc(a.detail)}</div>
              <div class="t-when">${fmtDateTime(a.created_at)}</div></li>`).join("")}
        </ul>` : `<div class="empty">Sem atividade ainda</div>`}
      </div>
    </div>
    <div class="panel mt">
      <h3>Demandas por ambiente e status</h3>
      <div class="chips">
        ${ENVS.map(e => `<span class="badge badge-${e}">${e}: ${d.by_env[e] || 0}</span>`).join("")}
        &nbsp;·&nbsp;
        ${STATUSES.map(s => `<span class="badge badge-${s}">${STATUS_LABEL[s]}: ${d.by_status[s] || 0}</span>`).join("")}
      </div>
    </div>
    ${(d.reqs_by_month && d.reqs_by_month.length) || (d.key_types && d.key_types.length) ? `
    <div class="grid grid-2 mt">
      ${d.reqs_by_month && d.reqs_by_month.length ? `
      <div class="panel"><h3>Demandas criadas por mês</h3>
        ${chartVBars(d.reqs_by_month.map(r => ({ label: r.month, n: r.n })), { fmt: fmtMonth })}
      </div>` : ''}
      ${d.key_types && d.key_types.length ? `
      <div class="panel"><h3>Tipos de chave</h3>
        ${chartHBars(d.key_types.map(r => ({ label: r.label, n: r.n })))}
      </div>` : ''}
      ${d.cert_health ? `
      <div class="panel"><h3>Saúde dos certificados</h3>
        ${chartDonut([
          { label: 'Vencidos', n: d.cert_health.vencidos, color: 'var(--red)' },
          { label: '≤ 30 dias', n: d.cert_health.ate_30, color: 'var(--amber)' },
          { label: '31–90 dias', n: d.cert_health.ate_90, color: 'var(--accent)' },
          { label: '> 90 dias', n: d.cert_health.ok, color: 'var(--green)' },
        ])}
      </div>` : ''}
    </div>` : ''}`;
};

/* ---------------- Kanban ---------------- */
const LANES = [
  ["backlog", "📥 Backlog"], ["a_fazer", "📌 A fazer"],
  ["em_andamento", "⚙️ Em andamento"], ["concluido", "✅ Concluído"],
];
const PRIO_LABEL = { alta: "Alta", media: "Média", baixa: "Baixa" };
const prioBadge = p => `<span class="badge badge-prio-${esc(p)}">${esc(PRIO_LABEL[p] || p)}</span>`;

views.kanban = async () => {
  let filterCat = "";
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Kanban</div>
      <div class="view-sub">Tarefas dos projetos — arraste os cartões entre as colunas</div>
    </div>
    <div class="toolbar">
      <select class="input" id="k-filter"><option value="">Todas as categorias</option></select>
      <button class="btn btn-primary" id="k-new">＋ Nova tarefa</button>
    </div></div>
    <div class="kanban" id="k-board"></div>`;

  async function load() {
    const data = await api("/tasks" + (filterCat ? `?category=${encodeURIComponent(filterCat)}` : ""));
    const sel = $("#k-filter");
    sel.innerHTML = `<option value="">Todas as categorias</option>` +
      data.categories.map(c => `<option value="${esc(c)}" ${c === filterCat ? "selected" : ""}>${esc(c)}</option>`).join("");

    $("#k-board").innerHTML = LANES.map(([lane, label]) => {
      const cards = data.tasks.filter(t => t.lane === lane);
      return `
        <div class="kanban-col" data-lane="${lane}">
          <div class="kanban-col-head"><span>${label}</span><span class="kanban-count">${cards.length}</span></div>
          ${cards.map(t => `
            <div class="kanban-card ${lane === "concluido" ? "k-done" : ""}" draggable="true" data-task="${t.id}">
              <div class="k-meta">${prioBadge(t.priority)}<span class="badge k-cat">${esc(t.category)}</span></div>
              <div class="k-title">${esc(t.title)}</div>
              ${t.description ? `<div class="k-desc">${esc(t.description)}</div>` : ""}
            </div>`).join("") || `<div class="k-empty">—</div>`}
        </div>`;
    }).join("");

    const byId = Object.fromEntries(data.tasks.map(t => [t.id, t]));
    $$(".kanban-card").forEach(card => {
      card.ondragstart = e => {
        e.dataTransfer.setData("text/plain", card.dataset.task);
        e.dataTransfer.effectAllowed = "move";
      };
      card.onclick = () => taskModal(byId[+card.dataset.task], load);
    });
    $$(".kanban-col").forEach(col => {
      col.ondragover = e => { e.preventDefault(); col.classList.add("drag-over"); };
      col.ondragleave = () => col.classList.remove("drag-over");
      col.ondrop = async e => {
        e.preventDefault();
        col.classList.remove("drag-over");
        const id = +e.dataTransfer.getData("text/plain");
        if (!id) return;
        try {
          await api(`/tasks/${id}/move`, { method: "POST", json: { lane: col.dataset.lane } });
          load();
        } catch (err) { toast(err.message, "err"); }
      };
    });
  }

  $("#k-filter").onchange = () => { filterCat = $("#k-filter").value; load(); };
  $("#k-new").onclick = () => taskModal(null, load);
  await load();
};

function taskModal(t, onDone) {
  modal(t ? "Editar tarefa" : "Nova tarefa", `
    <div class="field"><label>Título</label>
      <input class="input" id="t-title" value="${t ? esc(t.title) : ""}" placeholder="O que precisa ser feito?"></div>
    <div class="form-row">
      <div class="field"><label>Categoria</label>
        <input class="input" id="t-cat" list="t-cats" value="${t ? esc(t.category) : ""}" placeholder="certhub, wiki, hsm…">
        <datalist id="t-cats">${["certhub", "wiki", "hsm", "processos", "geral"].map(c => `<option>${c}</option>`).join("")}</datalist></div>
      <div class="field"><label>Prioridade</label>
        <select class="input" id="t-prio">${["alta", "media", "baixa"].map(p =>
          `<option value="${p}" ${t && t.priority === p ? "selected" : ""}>${PRIO_LABEL[p]}</option>`).join("")}</select></div>
      <div class="field"><label>Coluna</label>
        <select class="input" id="t-lane">${LANES.map(([v, l]) =>
          `<option value="${v}" ${t && t.lane === v ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    </div>
    <div class="field"><label>Descrição</label>
      <textarea class="input" id="t-desc" rows="5">${t ? esc(t.description || "") : ""}</textarea></div>
  `, { footer: `
      ${t ? `<button class="btn btn-danger" id="t-delete">Excluir</button>` : ""}
      <button class="btn" data-close>Cancelar</button>
      <button class="btn btn-primary" id="t-save">${t ? "Salvar" : "Criar tarefa"}</button>` });

  $("#t-save").onclick = async () => {
    const body = {
      title: $("#t-title").value, description: $("#t-desc").value,
      category: $("#t-cat").value || "geral",
      priority: $("#t-prio").value, lane: $("#t-lane").value,
    };
    try {
      if (t) await api(`/tasks/${t.id}`, { method: "PUT", json: body });
      else await api("/tasks", { method: "POST", json: body });
      closeModal(); toast(t ? "Tarefa atualizada" : "Tarefa criada");
      onDone && onDone();
    } catch (e) { toast(e.message, "err"); }
  };
  if (t) $("#t-delete").onclick = async () => {
    if (!confirm(`Excluir a tarefa "${t.title}"?`)) return;
    await api(`/tasks/${t.id}`, { method: "DELETE" });
    closeModal(); toast("Tarefa excluída"); onDone && onDone();
  };
}

/* ---------------- Monitor de Vencimentos ---------------- */
views.monitor = async () => {
  let pendingOnly = false;
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">📡 Monitor de Vencimentos</div>
      <div class="view-sub">Certificados próximos ao vencimento e vencidos — inicie demandas a partir daqui</div>
    </div></div>
    <div class="panel">
      <div class="toolbar" style="margin-bottom:12px">
        <input class="input" id="m-search" placeholder="Buscar CN, REQ…" style="min-width:220px">
        <select class="input" id="m-days">
          <option value="30">Vencem em 30 dias</option>
          <option value="60">Vencem em 60 dias</option>
          <option value="90" selected>Vencem em 90 dias</option>
          <option value="180">Vencem em 180 dias</option>
          <option value="365">Vencem em 1 ano</option>
        </select>
        <select class="input" id="m-ownership">
          <option value="">Todos</option>
          <option value="interno">Interno</option>
          <option value="externo">Externo</option>
        </select>
        <label style="display:flex;align-items:center;gap:6px;cursor:pointer;white-space:nowrap">
          <input type="checkbox" id="m-pending"> Somente pendentes
        </label>
      </div>
      <div id="m-table"></div>
    </div>`;

  async function load() {
    const days = $("#m-days").value;
    const search = $("#m-search").value.toLowerCase();
    const ownershipFilter = $("#m-ownership").value;
    pendingOnly = $("#m-pending").checked;
    let rows = await api(`/monitor/expiring?days=${days}&pending_only=${pendingOnly}`);
    if (search) rows = rows.filter(r => (r.cn||'').toLowerCase().includes(search) || (r.sans||'').toLowerCase().includes(search) || (r.req_number||'').toLowerCase().includes(search));
    if (ownershipFilter) rows = rows.filter(r => (r.ownership || 'interno') === ownershipFilter);

    $("#m-table").innerHTML = rows.length ? `
      <table class="tbl"><thead><tr>
        <th>CN</th><th>Env</th><th>Vencimento</th><th>Restam</th><th>Tipo</th><th>Lifecycle</th><th>Status</th><th>Ações</th>
      </tr></thead><tbody>
      ${rows.map(r => {
        const sanCount = (r.sans || "").split(",").map(s=>s.trim()).filter(Boolean).length;
        return `<tr${r.has_active_demand ? ' style="opacity:0.6"' : ''}>
        <td>${esc(r.cn)} ${sanCount ? `<button class="btn btn-sm btn-ghost" style="padding:1px 5px;font-size:10px;margin-left:4px" onclick="showSanModal('${esc(r.cn)}', '${esc(r.sans)}')">🏷️ SAN (${sanCount})</button>` : ''}</td>
        <td>${envBadge(r.env || '—')}</td>
        <td>${fmtDate(r.not_after)}</td>
        <td>${daysBadge(r.days_left)}</td>
        <td>${ownershipBadge(r.ownership || 'interno')}</td>
        <td>${lifecycleBadge(r.lifecycle_status)}</td>
        <td>${r.has_active_demand ? '<span class="badge badge-lc-em_renovacao">🔄 Em andamento</span>' : '<span class="badge badge-days-ok">Aguardando</span>'}</td>
        <td style="white-space:nowrap">
          ${r.has_active_demand ? '<span class="muted">Demanda ativa</span>' :
            `<button class="btn btn-sm btn-primary" data-renew="${r.id}" data-cn="${esc(r.cn)}" data-env="${esc(r.env||'PRD')}" data-ownership="${esc(r.ownership||'interno')}" data-partner="${esc(r.external_partner||'')}" data-email="${esc(r.partner_email||'')}">🔄 Renovar</button>`
          }
        </td>
      </tr>`;
      }).join('')}
      </tbody></table>`
    : `<div class="empty">🎉 Nenhum certificado pendente${pendingOnly ? ' (filtro ativo)' : ''}!</div>`;

    $$("[data-renew]").forEach(el => el.onclick = () => {
      const cn = el.dataset.cn, env = el.dataset.env, certId = el.dataset.renew;
      const ownership = el.dataset.ownership, partner = el.dataset.partner, email = el.dataset.email;
      newDemandModal('renovacao', { cn, env, certId, ownership, external_partner: partner, partner_email: email }, load);
    });
  }

  $("#m-search").oninput = () => { clearTimeout(window._mt); window._mt = setTimeout(load, 300); };
  $("#m-days").onchange = $("#m-ownership").onchange = $("#m-pending").onchange = load;
  await load();
};

/* ---------------- Demandas de Geração / Recebimento ---------------- */
views.geracao = async () => {
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">📋 Demandas de Geração</div>
      <div class="view-sub">REQs de geração e recebimento de certificados em andamento</div>
    </div>
    <button class="btn btn-primary" id="g-new">＋ Nova demanda</button></div>
    <div class="panel">
      <div class="toolbar" style="margin-bottom:12px">
        <input class="input" id="g-search" placeholder="Buscar REQ, CN…" style="min-width:220px">
        <select class="input" id="g-env"><option value="">Ambiente</option>${ENVS.map(e => `<option>${e}</option>`).join('')}</select>
        <select class="input" id="g-status"><option value="">Status</option>${STATUSES.map(s => `<option value="${s}">${STATUS_LABEL[s]}</option>`).join('')}</select>
        <select class="input" id="g-type">
          <option value="geracao,recebimento">Todos</option>
          <option value="geracao">Geração</option>
          <option value="recebimento">Recebimento</option>
        </select>
      </div>
      <div id="g-table"></div>
    </div>`;

  async function load() {
    const demandType = $("#g-type").value || 'geracao,recebimento';
    const params = new URLSearchParams({
      search: $("#g-search").value,
      env: $("#g-env").value,
      status: $("#g-status").value,
      demand_type: demandType,
    });
    const rows = await api("/reqs?" + params);
    const active = rows.filter(r => r.status !== 'concluida' && r.status !== 'cancelada');
    const shown = $("#g-status").value ? rows : active;

    $("#g-table").innerHTML = shown.length ? `
      <table class="tbl"><thead><tr>
        <th>REQ</th><th>Tipo</th><th>CN</th><th>Env</th><th>Status</th><th>Senha</th><th>Certs</th><th>Criada</th><th></th>
      </tr></thead><tbody>
      ${shown.map(r => `<tr>
        <td class="mono">${esc(r.req_number)}</td>
        <td>${demandBadge(r.demand_type)}</td>
        <td>${esc(r.cn)}</td>
        <td>${envBadge(r.env)}</td>
        <td>${statusBadge(r.status)}</td>
        <td>${r.password ? `<span class="password-cell" data-pwd="${esc(r.password)}" title="Clique para copiar">••••••••</span>` : '—'}</td>
        <td>${r.cert_count}</td>
        <td>${fmtDate(r.created_at)}</td>
        <td><button class="btn btn-sm" data-open="${r.id}">Abrir</button></td>
      </tr>`).join('')}
      </tbody></table>`
    : `<div class="empty">Nenhuma demanda em andamento. Crie uma nova ou aguarde o Monitor!</div>`;

    $$("[data-pwd]").forEach(el => el.onclick = () => copyText(el.dataset.pwd, "Senha copiada!"));
    $$("[data-open]").forEach(el => el.onclick = () => openReq(+el.dataset.open, load));
  }

  $("#g-search").oninput = () => { clearTimeout(window._gt); window._gt = setTimeout(load, 300); };
  $("#g-env").onchange = $("#g-status").onchange = $("#g-type").onchange = load;
  $("#g-new").onclick = () => newDemandModal('geracao', {}, load);
  await load();
};

/* ---------------- Demandas de Instalação ---------------- */
views.instalacao = async () => {
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">🔧 Demandas de Instalação</div>
      <div class="view-sub">REQs de instalação pendentes — somem ao ser concluídas</div>
    </div></div>
    <div class="panel">
      <div class="toolbar" style="margin-bottom:12px">
        <input class="input" id="i-search" placeholder="Buscar REQ, CN…" style="min-width:220px">
        <select class="input" id="i-env"><option value="">Ambiente</option>${ENVS.map(e => `<option>${e}</option>`).join('')}</select>
        <select class="input" id="i-status"><option value="">Somente Ativas</option>${STATUSES.map(s => `<option value="${s}">${STATUS_LABEL[s]}</option>`).join('')}</select>
      </div>
      <div id="i-table"></div>
    </div>`;

  async function load() {
    const params = new URLSearchParams({
      search: $("#i-search").value,
      env: $("#i-env").value,
      status: $("#i-status").value,
      demand_type: 'instalacao',
    });
    const rows = await api("/reqs?" + params);
    const shown = $("#i-status").value ? rows : rows.filter(r => !['concluida', 'cancelada', 'instalado'].includes(r.status));

    $("#i-table").innerHTML = shown.length ? `
      <table class="tbl"><thead><tr>
        <th>REQ</th><th>CN</th><th>Env</th><th>Status</th><th>Locais</th><th>Criada</th><th></th>
      </tr></thead><tbody>
      ${shown.map(r => `<tr>
        <td class="mono">${esc(r.req_number)}</td>
        <td>${esc(r.cn)}</td>
        <td>${envBadge(r.env)}</td>
        <td>${statusBadge(r.status)}</td>
        <td>${r.location_count || 0}</td>
        <td>${fmtDate(r.created_at)}</td>
        <td><button class="btn btn-sm" data-open="${r.id}">Abrir</button></td>
      </tr>`).join('')}
      </tbody></table>`
    : `<div class="empty">Sem demandas de instalação ativas! 🎉</div>`;

    $$("[data-open]").forEach(el => el.onclick = () => openReq(+el.dataset.open, load));
  }

  $("#i-search").oninput = () => { clearTimeout(window._it); window._it = setTimeout(load, 300); };
  $("#i-env").onchange = $("#i-status").onchange = load;
  await load();
};

async function newDemandModal(defaultType, opts = {}, onDone) {
  const isPrd = (opts.env || 'PRD') === 'PRD';
  modal(`Nova Demanda — ${DEMAND_TYPES[defaultType] || defaultType}`, `
    <div class="form-row">
      <div class="field"><label>Número REQ (ServiceNow)</label>
        <input class="input mono" id="nd-req" placeholder="REQ0012345" value="${esc(opts.req_number||'')}"></div>
      <div class="field"><label>Ambiente</label>
        <select class="input" id="nd-env">${ENVS.map(e => `<option ${e === (opts.env||'PRD') ? 'selected':''}>${e}</option>`).join('')}</select></div>
    </div>
    <div class="form-row">
      <div class="field"><label>Tipo de Demanda</label>
        <select class="input" id="nd-type" ${defaultType === 'renovacao' ? 'disabled' : ''}>
          <option value="geracao" ${defaultType==='geracao'?'selected':''}>Geração</option>
          <option value="recebimento" ${defaultType==='recebimento'?'selected':''}>Recebimento</option>
          <option value="renovacao" ${defaultType==='renovacao'?'selected':''}>Renovação</option>
          <option value="revogacao" ${defaultType==='revogacao'?'selected':''}>Revogação</option>
        </select></div>
      <div class="field"><label>Propriedade do Certificado</label>
        <select class="input" id="nd-ownership" ${defaultType === 'renovacao' ? 'disabled' : ''}>
          <option value="interno" ${(opts.ownership || 'interno') === 'interno' ? 'selected' : ''}>🔒 Privado / Interno (Chave Privada controlada)</option>
          <option value="externo" ${(opts.ownership || 'interno') === 'externo' ? 'selected' : ''}>🌐 Público / Externo (Sem Chave Privada)</option>
        </select></div>
    </div>
    <div class="field"><label>CN (Common Name)</label>
      <input class="input" id="nd-cn" placeholder="www.exemplo.com.br" value="${esc(opts.cn||'')}">
      <div id="nd-cn-notice" style="display:none;font-size:11px;color:var(--green);margin-top:3px"></div>
    </div>
    <div class="form-row" id="nd-partner-box" style="display:none">
      <div class="field"><label>Parceiro Externo / Solicitante</label>
        <input class="input" id="nd-partner" placeholder="Ex: Empresa Parceira, Gateway X" value="${esc(opts.external_partner||'')}" ${defaultType === 'renovacao' ? 'readonly' : ''}></div>
      <div class="field"><label>E-mail do Parceiro</label>
        <input class="input" id="nd-partner-email" placeholder="parceiro@empresa.com" value="${esc(opts.partner_email||'')}" ${defaultType === 'renovacao' ? 'readonly' : ''}></div>
      <div class="field"><label>Matrícula / ID</label>
        <input class="input mono" id="nd-partner-reg" placeholder="MAT-12345" value="${esc(opts.partner_registration||'')}" ${defaultType === 'renovacao' ? 'readonly' : ''}></div>
    </div>
    <div class="form-row">
      <div class="field" id="nd-ticket-container">
        <label id="nd-ticket-label">${isPrd ? 'Número da CRQ (ServiceNow — PRD)' : 'Work Order / WO (ServiceNow)'}</label>
        <input class="input mono" id="nd-ticket" placeholder="${isPrd ? 'CRQ0012345' : 'WO0012345'}">
      </div>
    </div>
    <div class="field"><label>Notas / observações</label>
      <textarea class="input" id="nd-notes" placeholder="Detalhes da demanda, solicitante, sistema…"></textarea></div>
    <div class="checkbox-row"><input type="checkbox" id="nd-auto" checked>
      <label for="nd-auto" style="margin:0">Gerar senha automaticamente</label></div>
  `, { footer: `<button class="btn" data-close>Cancelar</button>
                <button class="btn btn-primary" id="nd-save">Criar demanda</button>` });

  const updatePartnerBox = () => {
    const isExt = $("#nd-ownership").value === 'externo';
    $("#nd-partner-box").style.display = isExt ? 'flex' : 'none';
  };
  $("#nd-ownership").onchange = updatePartnerBox;
  updatePartnerBox();


  const updateTicketField = () => {
    const env = $("#nd-env").value;
    const prd = env === 'PRD';
    $("#nd-ticket-label").textContent = prd ? 'Número da CRQ (ServiceNow — PRD)' : 'Work Order / WO (ServiceNow — ' + env + ')';
    $("#nd-ticket").placeholder = prd ? 'CRQ0012345' : 'WO0012345';
  };
  $("#nd-env").onchange = updateTicketField;

  const lookupCNHistory = async () => {
    const cnVal = $("#nd-cn").value.trim();
    if (!cnVal) return;
    try {
      const data = await api(`/reqs/history-by-cn?cn=${encodeURIComponent(cnVal)}`);
      if (data.latest) {
        if (!$("#nd-partner").value && data.latest.external_partner) $("#nd-partner").value = data.latest.external_partner;
        if (!$("#nd-partner-email").value && data.latest.partner_email) $("#nd-partner-email").value = data.latest.partner_email;
        if (!$("#nd-partner-reg").value && data.latest.partner_registration) $("#nd-partner-reg").value = data.latest.partner_registration;
        if (!$("#nd-notes").value && data.latest.notes) $("#nd-notes").value = data.latest.notes;
        $("#nd-cn-notice").innerHTML = `✨ ${data.reqs.length} demanda(s) anterior(es) encontrada(s) — dados preenchidos automaticamente!`;
        $("#nd-cn-notice").style.display = "";
      } else if (data.reqs.length > 0) {
        $("#nd-cn-notice").innerHTML = `ℹ️ ${data.reqs.length} demanda(s) anterior(es) encontrada(s) para este CN.`;
        $("#nd-cn-notice").style.display = "";
      }
    } catch (e) {}
  };
  $("#nd-cn").onchange = lookupCNHistory;
  if (opts.cn) lookupCNHistory();

  $("#nd-save").onclick = async () => {
    try {
      const env = $("#nd-env").value;
      const ticketVal = $("#nd-ticket").value.trim();
      const isPrdEnv = env === 'PRD';
      const row = await api("/reqs", { method: "POST", json: {
        req_number: $("#nd-req").value || undefined,
        cn: $("#nd-cn").value,
        env: env,
        notes: $("#nd-notes").value,
        demand_type: $("#nd-type").value, // it's disabled but .value still gets the selected option
        auto_password: $("#nd-auto").checked,
        external_crq: isPrdEnv ? ticketVal : '',
        external_wo: !isPrdEnv ? ticketVal : '',
        external_partner: $("#nd-partner").value,
        partner_email: $("#nd-partner-email").value,
        partner_registration: $("#nd-partner-reg").value,
        ownership: $("#nd-ownership").value,
      }});

      // If created from monitor, flag the cert as em_renovacao
      if (opts.certId) {
        await api(`/monitor/certs/${opts.certId}/flag-renewal`, { method: "POST" }).catch(() => {});
      }
      // Se for renovação, auto-importa locais de instalação de demandas anteriores do mesmo CN
      if ($("#nd-type").value === 'renovacao' || defaultType === 'renovacao') {
        await api(`/reqs/${row.id}/import-previous-locations`, { method: "POST" }).catch(() => {});
      }
      closeModal();

      toast(`Demanda ${row.req_number} criada` + (row.password ? ' · senha gerada' : ''));
      onDone && onDone();
    } catch (e) { toast(e.message, "err"); }
  };

}


/* ---------------- Demandas (legado) ---------------- */

function fillTemplate(content, r) {
  const cert = (r.certificates && r.certificates[0]) || {};
  const locList = r.locations || [];
  const locaisStr = locList
    .map(l => l.server + (l.path_or_store ? ` (${l.path_or_store})` : "")).join("; ");
  const servidoresStr = [...new Set(locList.map(l => l.server).filter(Boolean))].join(", ");

  const map = {
    // REQ / Demanda
    req: r.req_number || "",
    req_number: r.req_number || "",
    demanda: r.req_number || "",

    // CN / Domain
    cn: r.cn || "",
    common_name: r.cn || "",
    url: r.cn || "",

    // Environment
    env: r.env || "",
    ambiente: r.env || "",

    // Status
    status: STATUS_LABEL[r.status] || r.status || "",

    // Demand Type
    tipo: DEMAND_TYPES[r.demand_type] || r.demand_type || "",
    demand_type: DEMAND_TYPES[r.demand_type] || r.demand_type || "",

    // ServiceNow Tickets (WO & CRQ)
    wo: r.external_wo || "",
    external_wo: r.external_wo || "",
    work_order: r.external_wo || "",
    crq: r.external_crq || "",
    external_crq: r.external_crq || "",
    mudanca: r.external_crq || r.external_wo || "",

    // Password / Senha
    senha: r.password || "",
    password: r.password || "",

    // External Partner / Parceiro Externo
    parceiro_externo: r.external_partner || cert.external_partner || "",
    parceiro: r.external_partner || cert.external_partner || "",
    external_partner: r.external_partner || cert.external_partner || "",
    email_parceiro: r.partner_email || cert.partner_email || "",
    partner_email: r.partner_email || cert.partner_email || "",
    matricula_parceiro: r.partner_registration || cert.partner_registration || "",
    partner_registration: r.partner_registration || cert.partner_registration || "",


    // Notes / Observações
    notas: r.notes || "",
    notes: r.notes || "",
    observacoes: r.notes || "",


    // Certificate details
    vencimento: (cert.not_after || r.not_after || r.vencimento) ? fmtDate(cert.not_after || r.not_after || r.vencimento) : "Aguardando emissão",
    validade: (cert.not_after || r.not_after || r.vencimento) ? fmtDate(cert.not_after || r.not_after || r.vencimento) : "Aguardando emissão",
    not_after: (cert.not_after || r.not_after || r.vencimento) ? fmtDate(cert.not_after || r.not_after || r.vencimento) : "Aguardando emissão",
    emissor: cert.issuer_cn || cert.issuer || r.issuer_cn || r.issuer || r.emissor || "Aguardando emissão",
    issuer: cert.issuer_cn || cert.issuer || r.issuer_cn || r.issuer || r.emissor || "Aguardando emissão",

    sans: cert.sans || r.sans || "",
    serial: cert.serial || r.serial || "",
    thumbprint: cert.thumbprint_sha1 || r.thumbprint_sha1 || "",
    fingerprint: cert.thumbprint_sha1 || r.thumbprint_sha1 || "",


    // Locations / Servers
    locais: locaisStr,
    locations: locaisStr,
    servidores: servidoresStr || locaisStr,
    servidor: servidoresStr || locaisStr,

    // Date
    data: fmtDate(new Date().toISOString()),
    date: fmtDate(new Date().toISOString()),
  };

  return content.replace(/\{(\w+)\}/g, (m, k) =>
    map[k] !== undefined && map[k] !== null && String(map[k]).trim() !== ""
      ? String(map[k]) : `[${k}?]`);
}

function fillTaskMessage(template, task, r) {
  const map = {
    tarefa: task.title || "",
    status: INSTALL_TASK_STATUS[task.status] || task.status || "",
    instrucoes: task.instructions || "",
    notas: task.notes || "",
    evidencias: (task.evidence && task.evidence.length)
      ? task.evidence.map(e => e.filename).join(", ") : "nenhuma",
    req: r.req_number || "",
    cn: r.cn || "",
    env: r.env || "",
    data: fmtDate(new Date().toISOString()),
  };
  return template.replace(/\{(\w+)\}/g, (m, k) =>
    map[k] !== undefined && map[k] !== null && String(map[k]).trim() !== ""
      ? String(map[k]) : `[${k}?]`);
}


async function openReq(id, onDone) {
  const [r, tpls] = await Promise.all([api(`/reqs/${id}`), api("/templates")]);
  let csrInfo = null;
  if (r.csr_pem) {
    try { csrInfo = await api("/csr/decode", { method: "POST", json: { pem: r.csr_pem } }); }
    catch (_) { csrInfo = null; }
  }
  const isInstall = r.demand_type === 'instalacao';
  const cert = (r.certificates && r.certificates[0]) || {};
  const isPublic = r.ownership === 'externo' || r.ownership === 'publico' || (cert && (cert.ownership === 'externo' || cert.ownership === 'publico')) || Boolean(r.external_partner);

  modal(`${r.req_number} — ${r.cn}`, `
    <div class="chips" style="margin-bottom:14px">
      ${envBadge(r.env)} ${statusBadge(r.status)} ${ownershipBadge(r.ownership || (isPublic ? 'externo' : 'interno'))}
      <span class="muted">criada em ${fmtDateTime(r.created_at)}</span>
    </div>

    <div class="form-row">
      <div class="field"><label>Status</label>
        <select class="input" id="d-status">${STATUSES.filter(s => s !== "instalado" || isInstall).map(s =>
          `<option value="${s}" ${s === r.status ? "selected" : ""}>${STATUS_LABEL[s]}</option>`).join("")}</select></div>
      <div class="field"><label>Propriedade / Tipo</label>
        <select class="input" id="d-ownership">
          <option value="interno" ${(r.ownership || 'interno') === 'interno' ? 'selected' : ''}>🔒 Privado (Interno)</option>
          <option value="externo" ${r.ownership === 'externo' || isPublic ? 'selected' : ''}>🌐 Público (Externo)</option>
        </select></div>
      <div class="field"><label>Senha</label>
        <div style="display:flex;gap:6px">
          <input class="input mono" id="d-pwd" type="password" value="${esc(r.password || "")}" readonly>
          <button class="btn btn-sm" id="d-pwd-toggle" title="Mostrar/ocultar">👁️</button>
          <button class="btn btn-sm" id="d-pwd-copy" title="Copiar">📋</button>
          <button class="btn btn-sm" id="d-pwd-regen" title="Regenerar">🎲</button>
        </div></div>
    </div>

    ${(cert.cert_category && cert.cert_category.includes('sepro')) || r.cn.includes('serpro') ? `
    <div class="panel mt" style="background:var(--accent-soft);border:1px solid var(--accent);padding:10px 14px">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div><strong>🌐 Certificado Serpro / ICP-Brasil</strong>
          <div class="muted">Acesse a plataforma Serpro para avisos, emissão e validação presencial.</div></div>
        <a href="https://certificados.serpro.gov.br" target="_blank" class="btn btn-sm btn-primary">Portal Serpro ↗</a>
      </div>
    </div>` : ''}

    <div class="form-row mt">
      <div class="field"><label>Notas / observações</label>
        <textarea class="input" id="d-notes" rows="2">${esc(r.notes || "")}</textarea></div>
    </div>

    <div id="d-partner-section" style="${isPublic ? 'display:block' : 'display:none'}">
      <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">
        Parceiro Externo / Solicitante (para Certificados Públicos)
      </h3>
      ${r.demand_type === 'renovacao' ? `
      <div class="panel" style="background:var(--blue-soft);border:1px solid var(--blue);padding:8px 12px;margin-bottom:12px;font-size:12px">
        ℹ️ <strong>Passo 1:</strong> Notifique o parceiro abaixo para que nos envie o certificado atualizado (clique no botão 'Notificar Parceiro' para gerar a resposta pronta).
      </div>
      ` : ''}
      <div class="form-row">
        <div class="field"><label>Nome / Empresa Parceira</label>
          <input class="input" id="d-partner" placeholder="Ex: Terceiro X, Gateway Y" value="${esc(r.external_partner || (cert && cert.external_partner) || '')}"></div>
        <div class="field"><label>E-mail do Parceiro</label>
          <input class="input" id="d-partner-email" placeholder="parceiro@empresa.com" value="${esc(r.partner_email || (cert && cert.partner_email) || '')}"></div>
        <div class="field"><label>Matrícula / ID</label>
          <input class="input mono" id="d-partner-reg" placeholder="MAT-12345" value="${esc(r.partner_registration || (cert && cert.partner_registration) || '')}"></div>
      </div>
      <div style="margin-top:6px">
        <button class="btn btn-sm btn-ghost" id="d-notify-partner">📩 Notificar Parceiro via Template</button>
      </div>
    </div>


    <div class="field mt"><label>Pasta da demanda</label>
      <div style="display:flex;gap:6px;align-items:center">
        <input class="input mono" value="${esc(r.folder)}" readonly>
        <button class="btn btn-sm" id="d-folder-make">Criar</button>
        <button class="btn btn-sm" id="d-folder-open" ${r.folder_exists ? "" : "disabled"}>Abrir</button>
      </div></div>

    <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Resposta pronta</h3>
    <div style="display:flex;gap:6px">
      <select class="input" id="d-tpl"><option value="">— escolha um template —</option>
        ${tpls.map(t => `<option value="${t.id}">${esc(t.name)}</option>`).join("")}</select>
      <button class="btn" id="d-tpl-copy" disabled>📋 Copiar</button>
    </div>
    <textarea class="input mono" id="d-tpl-preview" rows="9" readonly
      style="display:none;margin-top:8px"></textarea>

    <div style="display:flex;justify-content:space-between;align-items:center;margin:16px 0 8px">
      <h3 style="margin:0;font-size:13px;color:var(--text-dim);text-transform:uppercase">Locais de instalação</h3>
      <button class="btn btn-sm btn-ghost" id="d-import-locs" title="Recuperar locais de instalação das demandas anteriores deste CN">🔄 Importar locais anteriores</button>
    </div>
    <div id="d-locs">${r.locations.map(l => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
        <div><strong>${esc(l.server)}</strong> <span class="muted">${esc(l.path_or_store)}</span>
          ${isInstall ? `<select class="input" style="width:auto;margin-left:8px;display:inline" data-loc-status="${l.id}">
            <option value="pendente" ${(l.status||'pendente')==='pendente'?'selected':''}>Pendente</option>
            <option value="instalado" ${l.status==='instalado'?'selected':''}>Instalado</option>
            <option value="falhou" ${l.status==='falhou'?'selected':''}>Falhou</option>
          </select>` : (l.installed_at ? `<span class="muted">· instalado ${fmtDate(l.installed_at)}</span>` : '')}
          ${l.notes ? `<div class="muted">${esc(l.notes)}</div>` : ""}</div>
        <button class="btn btn-sm btn-danger" data-del-loc="${l.id}">✕</button>
      </div>`).join("") || `<div class="muted">Nenhum local registrado.</div>`}</div>
    <div class="form-row mt">
      <div class="field"><label>Servidor</label><input class="input" id="l-server" placeholder="SRVWEB01"></div>
      <div class="field"><label>Caminho / store</label><input class="input" id="l-path" placeholder="IIS binding 443 · LocalMachine\\My"></div>
    </div>
    <button class="btn btn-sm" id="l-add">＋ Adicionar local</button>

    <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Certificado</h3>
    <div class="tabs">
      <button class="tab-btn active" type="button" data-tab="gerado">📝 Certificado Gerado</button>
      <button class="tab-btn" type="button" data-tab="importado">📥 Certificado Importado</button>
    </div>
    <div class="tab-panel" id="tab-gerado">
      ${csrInfo ? `
      <table class="tbl"><tbody>
        <tr><th>CN</th><td>${esc(csrInfo.cn)}</td></tr>
        <tr><th>Subject</th><td>${esc(csrInfo.subject)}</td></tr>
        <tr><th>SANs</th><td>${esc(csrInfo.sans)}</td></tr>
        <tr><th>Chave</th><td>${esc(csrInfo.key_type)}</td></tr>
        <tr><th>Hash</th><td>${esc(csrInfo.sig_algo)}</td></tr>
      </tbody></table>
      <div style="display:flex;justify-content:space-between;align-items:center;margin:8px 0 4px">
        <label class="muted" style="font-size:12px">CSR (PEM)</label>
        <button class="btn btn-sm" id="d-csr-copy">📋 Copiar PEM</button>
      </div>
      <textarea class="input mono" id="d-csr-pem" rows="6" readonly>${esc(csrInfo.pem)}</textarea>`
      : `<div class="panel mt" style="background:var(--bg-sunken);padding:8px 12px;border-left:3px solid var(--border);font-size:12px">
          Nenhuma CSR gerada para esta demanda ainda.
         </div>`}
    </div>
    <div class="tab-panel" id="tab-importado" style="display:none">
      <div style="display:flex;justify-content:flex-end;margin-bottom:8px">
        <button class="btn btn-sm btn-primary" id="d-import-cert">📥 Importar Certificado (.cer / .pfx / .pem)</button>
      </div>
      ${r.certificates.length ? `
      <div class="subtabs">
        <button class="subtab-btn active" type="button" data-subtab="resumo">Resumo</button>
        <button class="subtab-btn" type="button" data-subtab="dump">Dump completo</button>
      </div>
      ${r.certificates.map(c => `
      <div class="panel mt" style="padding:12px 14px">
        <div class="subtab-panel" data-subpanel="resumo">
          <table class="tbl"><tbody>
            <tr><th style="width:140px">CN</th><td><strong>${esc(c.cn)}</strong></td></tr>
            <tr><th>Tipo</th><td>${certTypeBadge(c.cert_type)}</td></tr>
            <tr><th>Lifecycle</th><td><span class="badge badge-lc-${esc(c.lifecycle_status || 'em_inventario')}">${esc(LIFECYCLE_STATUS[c.lifecycle_status] || c.lifecycle_status || 'em_inventario')}</span></td></tr>
            <tr><th>SANs</th><td>${esc(c.sans || '—')}</td></tr>
            <tr><th>Emissor</th><td>${esc(c.issuer_cn || c.issuer || '—')}</td></tr>
            <tr><th>Validade</th><td>${fmtDate(c.not_before)} → ${fmtDate(c.not_after)}</td></tr>
            <tr><th>Chave</th><td>${esc(c.key_type || '—')}</td></tr>
            <tr><th>Thumbprint (SHA1)</th><td class="mono">${esc(c.thumbprint_sha1 || '—')}</td></tr>
            <tr><th>Origem</th><td>${esc(c.source || '—')}</td></tr>
          </tbody></table>
        </div>
        <div class="subtab-panel" data-subpanel="dump" style="display:none">
          <table class="tbl"><tbody>${Object.entries(c).map(([k, v]) =>
            `<tr><th style="width:180px">${esc(k)}</th><td class="mono" style="word-break:break-all">${
              v === null || v === "" ? "—" : esc(String(v))}</td></tr>`).join("")}
          </tbody></table>
        </div>
      </div>`).join("")}`
        : `<div class="panel mt" style="background:var(--bg-sunken);padding:8px 12px;border-left:3px solid var(--amber);font-size:12px">
            ⚠️ <strong>Certificado Pendente:</strong> Você precisa importar o certificado emitido (Arquivo .cer/.pfx ou Texto PEM) usando o botão acima para concluir esta demanda.
           </div>`}
    </div>


    ${isInstall ? (r.env === 'PRD' ? `
      <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">
        Ticket de Instalação em Produção
        <span class="badge badge-red" style="margin-left:8px;font-weight:normal">🔒 PRD — Mudança (CRQ)</span>
      </h3>
      <div class="form-row" style="align-items:flex-end">
        <div class="field"><label>Número da Mudança (CRQ)</label>
          <input class="input mono" id="d-crq-ext" placeholder="CRQ0012345" value="${esc(r.external_crq || '')}">
        </div>
        <button class="btn" id="d-wo-save">Salvar CRQ</button>
      </div>` : `
      <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">
        Work Order de Instalação
        <span class="badge badge-amber" style="margin-left:8px;font-weight:normal">🔧 ${r.env} — Work Order (WO)</span>
      </h3>
      <div class="form-row" style="align-items:flex-end">
        <div class="field"><label>Work Order de Instalação (WO)</label>
          <input class="input mono" id="d-wo-ext" placeholder="WO0012345" value="${esc(r.external_wo || '')}">
        </div>
        <button class="btn" id="d-wo-save">Salvar WO</button>
      </div>`) : ''}

    ${isInstall && r.env === 'PRD' ? `
    <div class="csr-subject-section mt">
      <button class="section-toggle" id="d-checklist-toggle" type="button">
        <span>✅ Checklist de Ativação (CRQ) — ${(r.install_tasks || []).length} tarefa(s)</span>
        <span class="toggle-arrow" id="d-checklist-arrow">▾</span>
      </button>
      <div class="section-body" id="d-checklist-body">
    <div id="d-checklist">${(r.install_tasks || []).map(t => `
      <div class="panel mt" style="padding:10px 14px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
          <div><strong>${esc(t.title)}</strong>
            <div class="muted">${esc(t.instructions)}</div></div>
          <select class="input" style="width:auto" data-task-status="${t.id}">
            ${Object.entries(INSTALL_TASK_STATUS).map(([v, label]) =>
              `<option value="${v}" ${v === t.status ? "selected" : ""}>${label}</option>`).join("")}
          </select>
        </div>
        <div class="field mt" style="margin-top:8px"><label style="font-size:11px">Notas</label>
          <textarea class="input" rows="2" data-task-notes="${t.id}">${esc(t.notes || "")}</textarea>
          <button class="btn btn-sm mt" data-task-save-notes="${t.id}">Salvar notas</button></div>
        <div class="mt">
          <label style="font-size:11px" class="muted">Evidências</label>
          <div data-task-evidence="${t.id}">${t.evidence.length ? t.evidence.map(e => `
            <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0">
              <a href="/api/install-tasks/${t.id}/evidence/${e.id}" target="_blank" class="mono">📎 ${esc(e.filename)}</a>
              <button class="btn btn-sm btn-danger" data-ev-del="${e.id}" data-ev-task="${t.id}">✕</button>
            </div>`).join("") : `<div class="muted">Nenhuma evidência anexada.</div>`}</div>
          <input type="file" data-task-file="${t.id}" style="margin-top:6px">
        </div>
        <button class="btn btn-sm mt" data-task-copy-msg="${t.id}">📋 Copiar mensagem</button>
      </div>`).join("") || `<div class="muted">Nenhuma tarefa no checklist.</div>`}</div>
      </div>
    </div>
    ` : ''}


    ${(r.past_reqs && r.past_reqs.length) ? `
    <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Demandas Anteriores deste Certificado (${esc(r.cn)})</h3>
    <table class="tbl mb">
      <thead>
        <tr><th>REQ</th><th>Tipo</th><th>Ambiente</th><th>Status</th><th>Criada em</th><th>Ação</th></tr>
      </thead>
      <tbody>
        ${r.past_reqs.map(p => `
          <tr>
            <td class="mono"><strong>${esc(p.req_number)}</strong></td>
            <td>${demandBadge(p.demand_type)}</td>
            <td>${envBadge(p.env)}</td>
            <td>${statusBadge(p.status)}</td>
            <td>${fmtDate(p.created_at)}</td>
            <td><button class="btn btn-sm" data-open-past="${p.id}">Abrir ↗</button></td>
          </tr>
        `).join("")}
      </tbody>
    </table>` : ''}

    <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Histórico de Atividades</h3>
    <ul class="timeline">${r.activity.map(a => `
      <li><div>${esc(a.action.replaceAll("_", " "))}</div>
        <div class="muted">${esc(a.detail)}</div>
        <div class="t-when">${fmtDateTime(a.created_at)}</div></li>`).join("") || ""}</ul>
  `, { large: true, footer: `
      <button class="btn btn-danger" id="d-delete">Excluir demanda</button>
      ${(!isPublic && (r.demand_type === 'geracao' || r.demand_type === 'renovacao')) ? `<button class="btn" id="d-gocsr">📝 Gerar CSR</button>` : ''}
      <button class="btn btn-primary" id="d-save">Salvar</button>` });

  if ($("#d-import-cert")) {
    $("#d-import-cert").onclick = () => {
      importCertModal(() => { openReq(id, onDone); }, id);
    };
  }

  $$(".tab-btn").forEach(btn => btn.onclick = () => {
    $$(".tab-btn").forEach(b => b.classList.toggle("active", b === btn));
    $$(".tab-panel").forEach(p => p.style.display = p.id === `tab-${btn.dataset.tab}` ? "block" : "none");
  });
  $$(".subtab-btn").forEach(btn => btn.onclick = () => {
    $$(".subtab-btn").forEach(b => b.classList.toggle("active", b === btn));
    $$(".subtab-panel").forEach(p => p.style.display = p.dataset.subpanel === btn.dataset.subtab ? "block" : "none");
  });
  if ($("#d-csr-copy")) {
    $("#d-csr-copy").onclick = () => copyText($("#d-csr-pem").value, "PEM copiado!");
  }


  $$("[data-open-past]").forEach(btn => btn.onclick = () => {
    closeModal();
    openReq(+btn.dataset.openPast, onDone);
  });



  $("#d-tpl").onchange = () => {
    const tpl = tpls.find(t => t.id === +$("#d-tpl").value);
    const preview = $("#d-tpl-preview");
    if (!tpl) { preview.style.display = "none"; $("#d-tpl-copy").disabled = true; return; }
    preview.value = fillTemplate(tpl.content, r);
    preview.style.display = "";
    $("#d-tpl-copy").disabled = false;
  };
  $("#d-tpl-copy").onclick = () => copyText($("#d-tpl-preview").value, "Resposta copiada!");
  $("#d-pwd-toggle").onclick = () => {
    const el = $("#d-pwd");
    el.type = el.type === 'password' ? 'text' : 'password';
  };
  $("#d-pwd-copy").onclick = () => copyText($("#d-pwd").value, "Senha copiada!");
  $("#d-pwd-regen").onclick = async () => {
    if (!confirm("Regenerar a senha desta demanda?")) return;
    const res = await api(`/reqs/${id}/password/regenerate`, { method: "POST" });
    $("#d-pwd").value = res.password;
    toast("Nova senha gerada");
  };
  // Location status tracking (instalação)
  $$("[data-loc-status]").forEach(sel => sel.onchange = async () => {
    try {
      await api(`/locations/${sel.dataset.locStatus}/status`, { method: "PUT", json: { status: sel.value } });
      toast(`Local atualizado: ${sel.value}`);
    } catch (e) { toast(e.message, "err"); }
  });
  $("#d-folder-make").onclick = async () => {
    const res = await api(`/reqs/${id}/folder`, { method: "POST" });
    toast("Pasta criada: " + res.folder);
    $("#d-folder-open").disabled = false;
  };
  $("#d-folder-open").onclick = async () => {
    try { await api("/files/open", { method: "POST", json: { path: r.folder } }); }
    catch (e) { toast(e.message, "err"); }
  };
  if ($("#d-import-locs")) {
    $("#d-import-locs").onclick = async () => {
      try {
        const res = await api(`/reqs/${id}/import-previous-locations`, { method: "POST" });
        toast(`✅ Importados ${res.added} locais de demandas anteriores`);
        closeModal(); openReq(id, onDone);
      } catch (e) { toast(e.message, "err"); }
    };
  }
  $("#l-add").onclick = async () => {
    if (!$("#l-server").value.trim()) return toast("Informe o servidor", "err");
    try {
      await api(`/reqs/${id}/locations`, { method: "POST", json: {
        server: $("#l-server").value, path_or_store: $("#l-path").value,
      }});
      closeModal(); openReq(id, onDone);
    } catch (e) { toast(e.message, "err"); }
  };
  $$("[data-del-loc]").forEach(el => el.onclick = async () => {
    await api(`/locations/${el.dataset.delLoc}`, { method: "DELETE" });
    closeModal(); openReq(id, onDone);
  });
  if ($("#d-gocsr")) {
    $("#d-gocsr").onclick = () => {
      csrPrefill = { req_id: id, cn: r.cn, req_number: r.req_number };
      closeModal(); location.hash = "#/csr";
    };
  }
  if ($("#d-notify-partner")) {
    $("#d-notify-partner").onclick = () => {
      const partnerTpl = tpls.find(t => t.name.toLowerCase().includes("parceiro") || t.name.toLowerCase().includes("vencimento")) || tpls[0];
      if (partnerTpl) {
        $("#d-tpl").value = partnerTpl.id;
        $("#d-tpl").onchange();
        $("#d-tpl-preview").scrollIntoView({ behavior: 'smooth', block: 'center' });
        toast("Template de notificação gerado abaixo!");
      } else {
        toast("Nenhum template de notificação encontrado", "err");
      }
    };
    
    // Auto-select template if this is an external renewal
    if (r.demand_type === 'renovacao' && isPublic) {
        setTimeout(() => {
            const partnerTpl = tpls.find(t => t.name.toLowerCase().includes("parceiro") || t.name.toLowerCase().includes("vencimento")) || tpls[0];
            if (partnerTpl) {
                $("#d-tpl").value = partnerTpl.id;
                $("#d-tpl").onchange();
            }
        }, 100);
    }
  }
  if ($("#d-ownership")) {
    $("#d-ownership").onchange = () => {
      const isExt = $("#d-ownership").value === 'externo';
      if ($("#d-partner-section")) {
        $("#d-partner-section").style.display = isExt ? 'block' : 'none';
      }
    };
  }
  $("#d-save").onclick = async () => {
    try {
      const newStatus = $("#d-status").value;
      await api(`/reqs/${id}`, { method: "PUT", json: {
        status: newStatus,
        notes: $("#d-notes").value,
        ownership: $("#d-ownership") ? $("#d-ownership").value : undefined,
        external_partner: $("#d-partner") ? $("#d-partner").value : undefined,
        partner_email: $("#d-partner-email") ? $("#d-partner-email").value : undefined,
        partner_registration: $("#d-partner-reg") ? $("#d-partner-reg").value : undefined,
      }});
      closeModal(); toast("Demanda atualizada"); onDone && onDone();

      // Ao concluir geração/recebimento/renovação, avançar a mesma REQ para fase de instalação
      if (newStatus === 'concluida' && (r.demand_type === 'geracao' || r.demand_type === 'recebimento' || r.demand_type === 'renovacao')) {
        try {
          const inst = await api(`/reqs/${id}/advance-to-installation`, { method: "POST" });
          toast(`✅ ${inst.req_number} avançou para Instalação!`);
          onDone && onDone();
        } catch (e) { toast(e.message, 'err'); }
      }
    } catch (e) { toast(e.message, "err"); }
  };

  // Ticket externo de instalação (WO para não-PRD, CRQ para PRD)
  if ($("#d-wo-save")) {
    $("#d-wo-save").onclick = async () => {
      try {
        const payload = r.env === 'PRD'
          ? { external_crq: $("#d-crq-ext") ? $("#d-crq-ext").value : '' }
          : { external_wo: $("#d-wo-ext") ? $("#d-wo-ext").value : '' };
        await api(`/reqs/${id}`, { method: "PUT", json: payload });
        toast("Ticket de instalação salvo");
      } catch (e) { toast(e.message, "err"); }
    };
  }

  $$("[data-task-status]").forEach(el => el.onchange = async () => {
    try {
      await api(`/install-tasks/${el.dataset.taskStatus}`, { method: "PUT", json: { status: el.value } });
      const task = (r.install_tasks || []).find(t => t.id === +el.dataset.taskStatus);
      if (task) task.status = el.value;
      toast("Status da tarefa atualizado");
    } catch (e) { toast(e.message, "err"); }
  });
  $$("[data-task-copy-msg]").forEach(el => el.onclick = () => {
    const task = (r.install_tasks || []).find(t => t.id === +el.dataset.taskCopyMsg);
    if (!task) return;
    copyText(fillTaskMessage(task.message_template || "", task, r), "Mensagem copiada!");
  });
  if ($("#d-checklist-toggle")) {
    $("#d-checklist-toggle").onclick = () => {
      const body = $("#d-checklist-body");
      const arrow = $("#d-checklist-arrow");
      const isOpen = body.style.display !== "none";
      body.style.display = isOpen ? "none" : "";
      arrow.textContent = isOpen ? "▸" : "▾";
    };
  }
  $$("[data-task-save-notes]").forEach(el => el.onclick = async () => {
    const taskId = el.dataset.taskSaveNotes;
    const notesVal = $(`[data-task-notes="${taskId}"]`).value;
    try {
      await api(`/install-tasks/${taskId}`, { method: "PUT", json: { notes: notesVal } });
      const task = (r.install_tasks || []).find(t => t.id === +taskId);
      if (task) task.notes = notesVal;
      toast("Notas salvas");
    } catch (e) { toast(e.message, "err"); }
  });
  $$("[data-task-file]").forEach(el => el.onchange = async () => {
    const taskId = el.dataset.taskFile;
    const file = el.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      await api(`/install-tasks/${taskId}/evidence`, { method: "POST", body: fd });
      toast("Evidência anexada"); openReq(id, onDone);
    } catch (e) { toast(e.message, "err"); }
  });
  $$("[data-ev-del]").forEach(el => el.onclick = async () => {
    if (!confirm("Remover esta evidência?")) return;
    try {
      await api(`/install-tasks/${el.dataset.evTask}/evidence/${el.dataset.evDel}`, { method: "DELETE" });
      toast("Evidência removida"); openReq(id, onDone);
    } catch (e) { toast(e.message, "err"); }
  });


  $("#d-delete").onclick = async () => {
    if (!confirm(`Excluir a demanda ${r.req_number}? O histórico e locais serão removidos.`)) return;
    await api(`/reqs/${id}`, { method: "DELETE" });
    closeModal(); toast("Demanda excluída"); onDone && onDone();
  };
}

/* ---------------- Gerar CSR ---------------- */
/* ---------------- Gerar CSR (enhanced) ---------------- */
views.csr = async () => {
  const reqs = await api("/reqs");
  const open = reqs.filter(r => !["concluida", "cancelada"].includes(r.status));
  const pre = csrPrefill; csrPrefill = null;

  // Build open reqs options
  const reqOpts = open.map(r =>
    `<option value="${r.id}"${pre && pre.req_id === r.id ? " selected" : ""}>${r.req_number} · ${r.cn} (${r.env})</option>`
  ).join("");

  main.innerHTML =
    '<div class="view-header"><div>' +
    '<div class="view-title">Gerar CSR</div>' +
    '<div class="view-sub">Chave + CSR com suporte a wildcard e SANs — local, certreq ou HSM</div>' +
    '</div></div>' +
    '<div class="grid grid-2">' +
    '<div class="panel">' +
    '<div class="field"><label>Engine</label>' +
    '<select class="input" id="c-engine">' +
    '<option value="local">Local (biblioteca cryptography)</option>' +
    '<option value="certreq">certreq — Windows (.inf)</option>' +
    '<option value="hsmutil">HSM (hsmutil CLI)</option>' +
    '</select></div>' +
    '<div class="field"><label>Demanda vinculada (opcional — salva os arquivos na pasta da REQ)</label>' +
    '<select class="input" id="c-req"><option value="">— nenhuma —</option>' + reqOpts + '</select></div>' +
    '<div class="field"><label>CN (Common Name)</label>' +
    '<div style="display:flex;gap:6px">' +
    '<input class="input" id="c-cn" placeholder="www.exemplo.com.br" value="' + (pre ? pre.cn : "") + '">' +
    '<button class="btn" id="c-wild" title="Transformar em wildcard">*.</button>' +
    '</div></div>' +
    '<div class="field"><label>SANs — um por linha (o CN é incluído automaticamente)</label>' +
    '<textarea class="input mono" id="c-sans" placeholder="exemplo.com.br\napp.exemplo.com.br"></textarea></div>' +
    '<div class="csr-subject-section">' +
    '<button class="section-toggle" id="c-subject-toggle">' +
    '<span>🔧 Atributos do Subject DN (O, OU, C, ST, L, E)</span>' +
    '<span class="toggle-arrow" id="c-subject-arrow">▸</span>' +
    '</button>' +
    '<div class="section-body" id="c-subject-body" style="display:none">' +
    '<div class="form-row">' +
    '<div class="field"><label>Organização (O)</label><input class="input" id="c-org" placeholder="Empresa S.A."></div>' +
    '<div class="field"><label>Unidade Org. (OU)</label><input class="input" id="c-ou" placeholder="TI / Infra"></div>' +
    '</div>' +
    '<div class="form-row">' +
    '<div class="field"><label>País (C)</label><input class="input" id="c-country" placeholder="BR" maxlength="2"></div>' +
    '<div class="field"><label>Estado (ST)</label><input class="input" id="c-state" placeholder="SP"></div>' +
    '<div class="field"><label>Localidade (L)</label><input class="input" id="c-locality" placeholder="São Paulo"></div>' +
    '</div>' +
    '<div class="field"><label>E-mail (E)</label><input class="input" id="c-email" placeholder="pki@empresa.com.br" type="email"></div>' +
    '</div></div>' +
    '<div class="form-row" style="margin-top:12px">' +
    '<div class="field"><label>Tipo de chave</label>' +
    '<select class="input" id="c-key">' +
    '<option value="rsa2048">RSA 2048</option>' +
    '<option value="rsa4096">RSA 4096</option>' +
    '<option value="ecp256">EC P-256</option>' +
    '</select></div>' +
    '</div>' +
    '<div class="field" id="c-label-field" style="display:none"><label>Label da chave no HSM</label>' +
    '<input class="input mono" id="c-label" placeholder="cert_exemplo_2026"></div>' +
    '<button class="btn btn-primary" id="c-go">⚙️ Gerar CSR</button>' +
    '</div>' +
    '<div class="panel" id="c-result"><h3>Resultado</h3>' +
    '<div class="empty">Preencha o formulário e clique em "Gerar CSR".</div></div>' +
    '</div>';

  $("#c-subject-toggle").onclick = () => {
    const body = $("#c-subject-body");
    const arrow = $("#c-subject-arrow");
    const isOpen = body.style.display === "none";
    body.style.display = isOpen ? "" : "none";
    arrow.textContent = isOpen ? "▾" : "▸";
  };

  $("#c-engine").onchange = () =>
    $("#c-label-field").style.display = $("#c-engine").value === "hsmutil" ? "" : "none";

  $("#c-wild").onclick = () => {
    const el = $("#c-cn");
    const v = el.value.trim().replace(/^\*\./, "").replace(/^www\./, "");
    el.value = v ? "*." + v : "*.";
  };

  $("#c-go").onclick = async () => {
    const btn = $("#c-go");
    btn.disabled = true; btn.textContent = "Gerando…";
    try {
      const res = await api("/csr/generate", { method: "POST", json: {
        cn: $("#c-cn").value,
        sans: $("#c-sans").value.split("\n").map(s => s.trim()).filter(Boolean),
        key_type: $("#c-key").value,
        org: $("#c-org") ? $("#c-org").value : "",
        ou: $("#c-ou") ? $("#c-ou").value : "",
        country: $("#c-country") ? $("#c-country").value.toUpperCase() : "",
        state: $("#c-state") ? $("#c-state").value : "",
        locality: $("#c-locality") ? $("#c-locality").value : "",
        email: $("#c-email") ? $("#c-email").value : "",
        engine: $("#c-engine").value,
        req_id: $("#c-req").value ? +$("#c-req").value : null,
        hsm_label: $("#c-label") ? $("#c-label").value : "",
      }});
      renderCsrResult(res);
      if (res.ok) toast("CSR gerada com sucesso");
      else toast("Falha na geração — veja a saída", "err");
    } catch (e) { toast(e.message, "err"); }
    btn.disabled = false; btn.textContent = "⚙️ Gerar CSR";
  };

  function renderCsrResult(res) {
    let html = "<h3>Resultado — engine " + esc(res.engine) + "</h3>";
    if (res.csr_pem) {
      html += '<div class="field"><label>CSR (cole no portal da CA)</label>' +
        '<textarea class="input mono" rows="12" id="r-csr" readonly>' + esc(res.csr_pem) + '</textarea></div>' +
        '<button class="btn btn-sm" id="r-copy-csr">📋 Copiar CSR</button>';
    }
    if (res.key_pem) {
      html += '<div class="field mt"><label>⚠️ Chave privada (sem REQ vinculada, não foi salva — guarde agora!)</label>' +
        '<textarea class="input mono" rows="6" id="r-key" readonly>' + esc(res.key_pem) + '</textarea></div>' +
        '<button class="btn btn-sm" id="r-copy-key">📋 Copiar chave</button>';
    }
    if (res.inf_content) {
      html += '<div class="field"><label>Arquivo .inf para certreq</label>' +
        '<textarea class="input mono" rows="12" id="r-inf" readonly>' + esc(res.inf_content) + '</textarea></div>' +
        '<button class="btn btn-sm" id="r-copy-inf">📋 Copiar .inf</button>' +
        '<div class="field mt"><label>Comando (executar no servidor Windows)</label>' +
        '<pre class="code-block">' + esc(res.command) + '</pre></div>';
    }
    if (res.output && !res.csr_pem) {
      html += '<div class="field mt"><label>Saída do comando</label>' +
        '<pre class="code-block">' + esc(res.output) + '</pre></div>';
    }
    if (res.saved) {
      html += '<div class="muted mt">Arquivos salvos:<br>' +
        Object.entries(res.saved).map(([k, v]) => '<span class="mono">' + esc(k) + ": " + esc(v) + "</span>").join("<br>") +
        '</div>';
    }
    $("#c-result").innerHTML = html;
    const bind = (btn, src, label) => { const b = $(btn); if (b) b.onclick = () => copyText($(src).value, label); };
    bind("#r-copy-csr", "#r-csr", "CSR copiada!");
    bind("#r-copy-key", "#r-key", "Chave copiada!");
    bind("#r-copy-inf", "#r-inf", ".inf copiado!");
  }
};



/* ---------------- Decoder geral ---------------- */
views.decoder = async () => {
  const reqs = await api("/reqs");
  let decoded = null;
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Decoder</div>
      <div class="view-sub">Cole ou envie um certificado, CSR, chave privada ou PFX — o tipo é detectado automaticamente</div>
    </div></div>
    <div class="grid grid-2">
      <div class="panel">
        <div class="field"><label>Arquivo (.csr / .pem / .crt / .cer / .der / .key / .pfx / .p12)</label>
          <input class="input" type="file" id="dc-file"></div>
        <div class="field"><label>Ou cole o conteúdo em PEM</label>
          <textarea class="input mono" id="dc-pem" rows="11"
            placeholder="-----BEGIN CERTIFICATE-----"></textarea></div>
        <div class="field" id="dc-pwd-box" style="display:none">
          <label>Senha (PFX / chave criptografada)</label>
          <input class="input" type="password" id="dc-pwd"></div>
        <button class="btn btn-primary" id="dc-go">🔍 Decodificar</button>
        <div id="dc-result" class="mt"></div>
      </div>
      <div class="panel">
        <h3>Repositório de CSRs</h3>
        <div id="dc-list"></div>
      </div>
    </div>`;

  async function loadList() {
    const rows = await api("/csrs");
    $("#dc-list").innerHTML = rows.length ? `
      <table class="tbl"><thead><tr>
        <th>CN</th><th>Chave</th><th>REQ</th><th>Criada</th><th></th>
      </tr></thead><tbody>${rows.map(s => `
        <tr>
          <td title="${esc(s.subject)}">${esc(s.cn)}</td>
          <td class="muted">${esc(s.key_type)}</td>
          <td class="mono">${esc(s.req_number || "—")} ${s.env ? envBadge(s.env) : ""}</td>
          <td>${fmtDate(s.created_at)}</td>
          <td style="white-space:nowrap">
            <button class="btn btn-sm" data-copy-pem="${s.id}" title="Copiar PEM">📋</button>
            <button class="btn btn-sm btn-danger" data-del-csr="${s.id}">✕</button>
          </td>
        </tr>`).join("")}</tbody></table>`
      : `<div class="empty">Nenhuma CSR guardada ainda.</div>`;
    $$("[data-copy-pem]").forEach(el => el.onclick = () =>
      copyText(rows.find(s => s.id === +el.dataset.copyPem).pem, "PEM copiado!"));
    $$("[data-del-csr]").forEach(el => el.onclick = async () => {
      if (!confirm("Remover esta CSR do repositório?")) return;
      await api(`/csrs/${el.dataset.delCsr}`, { method: "DELETE" });
      toast("CSR removida"); loadList();
    });
  }

  const row = (k, v, mono) => `<tr><th style="width:120px">${k}</th>
    <td class="${mono ? "mono" : ""}">${esc(v || "—")}</td></tr>`;

  $("#dc-file").onchange = async () => {
    const f = $("#dc-file").files[0];
    if (f && /\.(pem|csr|crt|cer|key|txt|req)$/i.test(f.name)) $("#dc-pem").value = await f.text();
  };

  $("#dc-go").onclick = async () => {
    const file = $("#dc-file").files[0];
    const pem = $("#dc-pem").value.trim();
    const password = $("#dc-pwd").value;
    const form = new FormData();
    if (pem) form.append("pem_text", pem);
    else if (file) form.append("file", file);
    else return toast("Envie um arquivo ou cole o conteúdo", "err");
    if (password) form.append("password", password);

    try {
      decoded = await api("/decode", { method: "POST", body: form });
    } catch (e) { decoded = null; $("#dc-result").innerHTML = ""; return toast(e.message, "err"); }

    if (decoded.type === "needs_password") {
      $("#dc-pwd-box").style.display = "block";
      $("#dc-result").innerHTML = "";
      return toast(decoded.hint === "pfx" ? "Informe a senha do PFX" : "Chave criptografada — informe a senha", "err");
    }

    if (decoded.type === "csr") {
      $("#dc-result").innerHTML = `
        <table class="tbl">
          ${row("Tipo", "CSR")}${row("CN", decoded.cn)}${row("Subject", decoded.subject, 1)}
          ${row("SANs", decoded.sans)}${row("Chave", decoded.key_type)}
          ${row("Hash", decoded.sig_algo)}
          <tr><th>Assinatura</th><td><span class="badge badge-days-${decoded.signature_valid ? "ok" : "danger"}">
            ${decoded.signature_valid ? "válida ✓" : "INVÁLIDA ✗"}</span></td></tr>
        </table>
        <div class="form-row mt">
          <div class="field" style="margin:0"><select class="input" id="dc-req">
            <option value="">— sem demanda —</option>
            ${reqs.map(r => `<option value="${r.id}">${esc(r.req_number)} · ${esc(r.cn)} (${r.env})</option>`).join("")}
          </select></div>
          <button class="btn btn-primary" id="dc-save">＋ Adicionar ao repositório</button>
        </div>`;
      $("#dc-save").onclick = async () => {
        try {
          await api("/csrs", { method: "POST", json: {
            pem: decoded.pem, req_id: $("#dc-req").value ? +$("#dc-req").value : null,
          }});
          toast("CSR adicionada ao repositório"); loadList();
        } catch (e) { toast(e.message, "err"); }
      };
      return;
    }

    if (decoded.type === "cert") {
      $("#dc-result").innerHTML = `<table class="tbl">
        ${row("Tipo", "Certificado")}${row("CN", decoded.cn)}${row("Subject", decoded.subject, 1)}
        ${row("Emissor", decoded.issuer, 1)}${row("SANs", decoded.sans)}
        ${row("Categoria", CERT_TYPE_LABEL[decoded.cert_type] || decoded.cert_type)}
        ${row("Serial", decoded.serial, 1)}${row("Thumbprint SHA1", decoded.thumbprint_sha1, 1)}
        ${row("Válido de", decoded.not_before)}${row("Válido até", decoded.not_after)}
        ${row("Chave", decoded.key_type)}
      </table>`;
      return;
    }

    if (decoded.type === "key") {
      $("#dc-result").innerHTML = `<table class="tbl">
        ${row("Tipo", "Chave privada")}${row("Chave", decoded.key_type)}
        ${row("Criptografada", decoded.encrypted ? "Sim" : "Não")}
      </table>`;
      return;
    }

    if (decoded.type === "pfx") {
      $("#dc-result").innerHTML = `<table class="tbl">
        ${row("Tipo", "PFX / PKCS12")}
        ${row("Contém chave privada", decoded.has_key ? "Sim" : "Não")}
        ${row("Certificados extras na cadeia", decoded.extra_certs)}
        ${decoded.cert ? row("CN do certificado", decoded.cert.cn) : ""}
        ${decoded.cert ? row("Emissor", decoded.cert.issuer, 1) : ""}
      </table>`;
      return;
    }
  };
  await loadList();
};

/* ---------------- Certificados ---------------- */
const CERT_TYPE_LABEL = {
  servidor: "Servidor TLS", cliente_mtls: "Cliente mTLS",
  ambos: "Servidor + Cliente", ca: "CA", "": "—",
};
const certTypeBadge = t => t
  ? `<span class="badge badge-tipo-${esc(t)}">${esc(CERT_TYPE_LABEL[t] || t)}</span>`
  : `<span class="muted">—</span>`;

views.certs = async () => {
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Certificados</div>
      <div class="view-sub">Importe um arquivo e os dados são lidos automaticamente</div>
    </div>
    <div class="toolbar">
      <button class="btn" id="cert-relink" title="Recalcular vínculos entre certificados e emissores">🔗 Revincular cadeias</button>
      <button class="btn btn-primary" id="cert-import">⬆ Importar certificado</button>
    </div></div>
    <div class="panel">
      <div class="toolbar" style="margin-bottom:12px">
        <input class="input" id="cf-search" placeholder="Buscar CN, SAN, emissor, REQ…" style="min-width:220px">
        <select class="input" id="cf-exp">
          <option value="">Validade</option>
          <option value="0">Vencidos</option>
          <option value="30">Vencem em ≤ 30d</option>
          <option value="60">Vencem em ≤ 60d</option>
          <option value="90">Vencem em ≤ 90d</option>
        </select>
        <select class="input" id="cf-type">
          <option value="">Tipo</option>
          ${["servidor", "cliente_mtls", "ambos", "ca"].map(t =>
            `<option value="${t}">${CERT_TYPE_LABEL[t]}</option>`).join("")}
        </select>
        <select class="input" id="cf-lifecycle">
          <option value="">Todos Lifecycle</option>
          ${Object.entries(LIFECYCLE_STATUS).map(([k, v]) => 
            `<option value="${k}">${esc(v)}</option>`).join("")}
        </select>
        <select class="input" id="cf-issuer"><option value="">Emissor</option></select>
      </div>
      <div id="cert-table"></div>
    </div>`;

  let issuerSel = "";
  async function load() {
    const params = new URLSearchParams({
      search: $("#cf-search").value,
      cert_type: $("#cf-type").value,
      lifecycle: $("#cf-lifecycle").value,
      issuer_cn: issuerSel,
    });
    if ($("#cf-exp").value !== "") params.set("expiring_days", $("#cf-exp").value);
    const data = await api("/certs?" + params);
    const rows = data.certs;
    $("#cf-issuer").innerHTML = `<option value="">Emissor</option>` +
      data.issuers.map(i => `<option value="${esc(i)}" ${i === issuerSel ? "selected" : ""}>${esc(i)}</option>`).join("");

    $("#cert-table").innerHTML = rows.length ? `
      <table class="tbl"><thead><tr>
        <th>CN</th><th>Tipo</th><th>REQ</th><th>Validade</th><th></th><th>Emissor</th><th>Lifecycle</th><th></th>
      </tr></thead><tbody>${rows.map(c => {
        const sanList = (c.sans || "").split(",").map(s=>s.trim()).filter(Boolean);
        return `
        <tr>
          <td>${esc(c.cn)} ${sanList.length ? `<button class="btn btn-sm btn-ghost" style="padding:1px 5px;font-size:10px;margin-left:4px" onclick="showSanModal('${esc(c.cn)}', '${esc(c.sans)}')">🏷️ SAN (${sanList.length})</button>` : ''} ${c.issued_count ? `<span class="badge k-cat" title="Certificados emitidos por esta CA no repositório">emite ${c.issued_count}</span>` : ""}</td>
          <td>${certTypeBadge(c.cert_type)}</td>
          <td class="mono">${esc(c.req_number || "—")} ${c.env ? envBadge(c.env) : ""}</td>
          <td>${fmtDate(c.not_before)} → <strong>${fmtDate(c.not_after)}</strong></td>
          <td>${daysBadge(c.days_left)}</td>
          <td class="muted" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
              title="${esc(c.issuer || "")}">
            ${c.parent_cn ? `<span title="Emissor presente no repositório — cadeia vinculada">🔗</span> ` : ""}${esc(c.issuer_cn || c.issuer || "")}</td>
          <td>${lifecycleBadge(c.lifecycle_status)}</td>
          <td style="white-space:nowrap">
            <button class="btn btn-sm" data-detail="${c.id}">Detalhes</button>
            <button class="btn btn-sm btn-danger" data-del="${c.id}">✕</button>
          </td>
        </tr>`;
      }).join("")}</tbody></table>`

      : `<div class="empty">Nenhum certificado encontrado.</div>`;
    $$("[data-detail]").forEach(el => el.onclick = () =>
      certDetail(rows.find(c => c.id === +el.dataset.detail), load));
    $$("[data-del]").forEach(el => el.onclick = async () => {
      if (!confirm("Remover este certificado do registro?")) return;
      await api(`/certs/${el.dataset.del}`, { method: "DELETE" });
      toast("Certificado removido"); load();
    });
  }
  $("#cf-search").oninput = () => { clearTimeout(window._t2); window._t2 = setTimeout(load, 300); };
  $("#cf-exp").onchange = $("#cf-type").onchange = $("#cf-lifecycle").onchange = load;
  $("#cf-issuer").onchange = () => { issuerSel = $("#cf-issuer").value; load(); };
  $("#cert-import").onclick = () => importCertModal(load);
  $("#cert-relink").onclick = async () => {
    const res = await api("/certs/relink", { method: "POST" });
    toast(`${res.total} certificados revisados · ${res.linked} vínculos de cadeia`);
    load();
  };
  await load();
};

function certDetail(c, onDone) {
  if (!c) return;
  const sanList = (c.sans || "").split(",").map(s=>s.trim()).filter(Boolean);
  const row = (k, v, mono) => `<tr><th style="width:140px">${k}</th><td class="${mono ? "mono" : ""}">${esc(v || "—")}</td></tr>`;
  modal("Detalhes do certificado", `
    <table class="tbl">
      ${row("CN", c.cn)}
      <tr><th>SANs</th><td>${c.sans ? `${esc(c.sans)} <button class="btn btn-sm btn-ghost" style="padding:1px 5px;font-size:11px;margin-left:6px" onclick="showSanModal('${esc(c.cn)}', '${esc(c.sans)}')">🏷️ Ver todos (${sanList.length})</button>` : '<span class="muted">—</span>'}</td></tr>
      ${row("Subject", c.subject, 1)}

      ${row("Emissor", c.issuer, 1)}
      <tr><th>Cadeia</th><td>${c.parent_cn
        ? `🔗 emitido por <strong>${esc(c.parent_cn)}</strong> (no repositório)`
        : `emissor <strong>${esc(c.issuer_cn || "?")}</strong> não está no repositório — importe a CA e use "Revincular cadeias"`}</td></tr>
      ${row("Serial", c.serial, 1)}
      ${row("Thumbprint SHA1", c.thumbprint_sha1, 1)}
      ${row("Válido de", fmtDateTime(c.not_before))}${row("Válido até", fmtDateTime(c.not_after))}
      ${row("Chave", c.key_type)}${row("Arquivo", c.file_path, 1)}
      ${row("REQ", c.req_number)}
      ${row("Lifecycle atual", lifecycleBadge(c.lifecycle_status))}
    </table>
    <div class="form-row mt">
      <div class="field" style="margin:0"><label>Lifecycle</label>
        <select class="input" id="cd-lifecycle">
          ${Object.entries(LIFECYCLE_STATUS).map(([k, v]) => 
            `<option value="${k}" ${c.lifecycle_status === k ? "selected" : ""}>${esc(v)}</option>`).join("")}
        </select></div>
      <button class="btn" id="cd-save-lifecycle" style="align-self:flex-end">Salvar lifecycle</button>
    </div>
    <div class="form-row mt">
      <div class="field" style="margin:0"><label>Tipo</label>
        <select class="input" id="cd-type">
          <option value="">— não classificado —</option>
          ${["servidor", "cliente_mtls", "ambos", "ca"].map(t =>
            `<option value="${t}" ${c.cert_type === t ? "selected" : ""}>${CERT_TYPE_LABEL[t]}</option>`).join("")}
        </select></div>
      <button class="btn" id="cd-save-type" style="align-self:flex-end">Salvar tipo</button>
      <button class="btn" id="cd-copy-thumb" style="align-self:flex-end">📋 Thumbprint</button>
      <button class="btn" id="cd-copy-pem" style="align-self:flex-end">📋 Copiar PEM</button>
      <button class="btn" id="cd-history" style="align-self:flex-end">📜 Histórico</button>
    </div>
  `, { large: true });
  $("#cd-copy-thumb").onclick = () => copyText(c.thumbprint_sha1 || "", "Thumbprint copiado!");
  $("#cd-copy-pem").onclick = async () => {
    try {
      const { pem } = await api(`/certs/${c.id}/pem`);
      copyText(pem, "PEM copiado!");
    } catch (e) { toast(e.message, "err"); }
  };
  $("#cd-save-type").onclick = async () => {
    await api(`/certs/${c.id}`, { method: "PUT", json: { cert_type: $("#cd-type").value } });
    closeModal(); toast("Tipo atualizado"); onDone && onDone();
  };
  $("#cd-save-lifecycle").onclick = async () => {
    await api(`/certs/${c.id}/lifecycle`, { method: "PUT", json: { lifecycle_status: $("#cd-lifecycle").value } });
    closeModal(); toast("Lifecycle atualizado"); onDone && onDone();
  };
  $("#cd-history").onclick = async () => {
    try {
      const h = await api(`/certs/${c.id}/history`);
      closeModal();
      modal(`Histórico — ${esc(c.cn)}`, `
        <h3 style="margin:0 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Demandas vinculadas</h3>
        ${h.reqs.length ? `<table class="tbl"><thead><tr><th>REQ</th><th>Tipo</th><th>Env</th><th>Status</th><th>Criada</th></tr></thead><tbody>
          ${h.reqs.map(rr => `<tr>
            <td class="mono">${esc(rr.req_number)}</td>
            <td>${esc(DEMAND_TYPES[rr.demand_type] || rr.demand_type || '—')}</td>
            <td>${envBadge(rr.env)}</td>
            <td>${statusBadge(rr.status)}</td>
            <td>${fmtDate(rr.created_at)}</td>
          </tr>`).join('')}</tbody></table>` : '<div class="muted">Nenhuma demanda.</div>'}
        <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Outros certificados com mesmo CN</h3>
        ${h.related_certs.filter(rc => rc.id !== c.id).length ? `<table class="tbl"><thead><tr><th>Serial</th><th>Válido até</th><th>Lifecycle</th></tr></thead><tbody>
          ${h.related_certs.filter(rc => rc.id !== c.id).map(rc => `<tr>
            <td class="mono muted">${esc((rc.serial||'').slice(0,16))}…</td>
            <td>${fmtDate(rc.not_after)}</td>
            <td>${lifecycleBadge(rc.lifecycle_status)}</td>
          </tr>`).join('')}</tbody></table>` : '<div class="muted">Nenhum outro certificado.</div>'}
        <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Atividade</h3>
        <ul class="timeline">${h.activity.map(a => `
          <li><div>${esc(a.action.replaceAll('_',' '))} ${a.req_number ? `<span class="mono">· ${esc(a.req_number)}</span>` : ''}</div>
            <div class="muted">${esc(a.detail)}</div>
            <div class="t-when">${fmtDateTime(a.created_at)}</div></li>`).join('') || '<li class="muted">Sem atividade.</li>'}
        </ul>
      `, { large: true });
    } catch (e) { toast(e.message, "err"); }
  };
}

async function importCertModal(onDone, defaultReqId = null) {
  const reqs = await api("/reqs");
  modal("Importar Certificado", `
    <div style="display:flex;gap:16px;margin-bottom:14px;border-bottom:1px solid var(--border);padding-bottom:10px">
      <label style="cursor:pointer;font-weight:600;display:flex;align-items:center;gap:6px">
        <input type="radio" name="ic-mode" value="file" checked> 📁 Enviar Arquivo (.cer, .crt, .pem, .pfx)
      </label>
      <label style="cursor:pointer;font-weight:600;display:flex;align-items:center;gap:6px">
        <input type="radio" name="ic-mode" value="text"> 📝 Colar Conteúdo PEM
      </label>
    </div>

    <div id="ic-box-file">
      <div class="field"><label>Arquivo (.cer, .crt, .pem, .der, .pfx, .p12)</label>
        <input class="input" type="file" id="i-file" accept=".cer,.crt,.pem,.der,.pfx,.p12"></div>
      <div class="field"><label>Senha (apenas para PFX/P12)</label>
        <input class="input" type="password" id="i-pwd" placeholder="Senha do arquivo PFX (se houver)"></div>
    </div>

    <div id="ic-box-text" style="display:none">
      <div class="field"><label>Conteúdo PEM (-----BEGIN CERTIFICATE-----)</label>
        <textarea class="input mono" id="i-pem-text" rows="8" placeholder="-----BEGIN CERTIFICATE-----\nMIIDXzCCAkegAwIBAgIU...\n-----END CERTIFICATE-----"></textarea></div>
    </div>

    <div class="field mt"><label>Vincular à demanda (opcional)</label>
      <select class="input" id="i-req"><option value="">— nenhuma —</option>
        ${reqs.map(r => `<option value="${r.id}" ${r.id === defaultReqId ? "selected" : ""}>${esc(r.req_number)} · ${esc(r.cn)} (${r.env})</option>`).join("")}
      </select></div>
    <div class="muted">Os metadados (CN, SANs, Emissor, Validade, Serial, Thumbprint) serão lidos automaticamente.</div>
  `, { footer: `<button class="btn" data-close>Cancelar</button>
                <button class="btn btn-primary" id="i-go">Importar Certificado</button>` });

  $$("[name='ic-mode']").forEach(radio => radio.onchange = () => {
    const isText = $("input[name='ic-mode']:checked").value === 'text';
    $("#ic-box-file").style.display = isText ? 'none' : 'block';
    $("#ic-box-text").style.display = isText ? 'block' : 'none';
  });

  $("#i-go").onclick = async () => {
    const isText = $("input[name='ic-mode']:checked").value === 'text';
    const fd = new FormData();
    if (isText) {
      const textVal = $("#i-pem-text").value.trim();
      if (!textVal) return toast("Cole o conteúdo PEM do certificado", "err");
      fd.append("pem_text", textVal);
    } else {
      const file = $("#i-file").files[0];
      if (!file) return toast("Selecione um arquivo de certificado", "err");
      fd.append("file", file);
      fd.append("password", $("#i-pwd").value);
    }
    if ($("#i-req").value) fd.append("req_id", $("#i-req").value);

    try {
      const cert = await api("/certs/import", { method: "POST", body: fd });
      closeModal();
      if (cert.csr_match === false) {
        toast(`⚠️ ATENÇÃO: O certificado ${cert.cn} NÃO corresponde à CSR gerada nesta demanda!`, "err");
      } else if (cert.csr_match === true) {
        toast(`✅ Certificado ${cert.cn} verificado: Chave pública corresponde à CSR!`, "ok");
      } else {
        toast(`✅ Certificado ${cert.cn} importado · vence ${fmtDate(cert.not_after)}`);
      }

      if (!cert.chain_found && cert.issuer_name) {

        modal("⚠️ Cadeia de Certificação não encontrada", `
          <div class="banner banner-warn" style="margin-bottom:12px">
            A cadeia de certificação (CA) do emissor <strong>"${esc(cert.issuer_name)}"</strong> não foi identificada no sistema.
          </div>
          <p style="margin:12px 0;font-size:13px">Deseja importar o certificado da CA Emissora (Raiz ou Intermediária) agora?</p>
        `, { footer: `
          <button class="btn" id="ca-skip">Continuar sem CA</button>
          <button class="btn btn-primary" id="ca-import">📥 Importar CA Emissora</button>
        `});
        $("#ca-skip").onclick = () => { closeModal(); onDone && onDone(); };
        $("#ca-import").onclick = () => { closeModal(); importCertModal(onDone); };
      } else {
        onDone && onDone();
      }
    } catch (e) { toast(e.message, "err"); }
  };
}


/* ---------------- Senhas ---------------- */
views.passwords = async () => {
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Gerador de senhas</div>
      <div class="view-sub">Senhas fortes com política configurável (módulo secrets)</div>
    </div></div>
    <div class="grid grid-2">
      <div class="panel">
        <div class="form-row">
          <div class="field"><label>Tamanho</label>
            <input class="input" type="number" id="p-length" value="16" min="8" max="64"></div>
          <div class="field"><label>Quantidade</label>
            <input class="input" type="number" id="p-count" value="3" min="1" max="20"></div>
        </div>
        <div class="checkbox-row"><input type="checkbox" id="p-upper" checked><label for="p-upper" style="margin:0">Maiúsculas (A-Z)</label></div>
        <div class="checkbox-row"><input type="checkbox" id="p-lower" checked><label for="p-lower" style="margin:0">Minúsculas (a-z)</label></div>
        <div class="checkbox-row"><input type="checkbox" id="p-digits" checked><label for="p-digits" style="margin:0">Dígitos (0-9)</label></div>
        <div class="checkbox-row"><input type="checkbox" id="p-symbols" checked><label for="p-symbols" style="margin:0">Símbolos (!@#$%&*+-=?)</label></div>
        <div class="checkbox-row"><input type="checkbox" id="p-amb" checked><label for="p-amb" style="margin:0">Excluir caracteres ambíguos (O/0, I/l/1…)</label></div>
        <button class="btn btn-primary mt" id="p-go">Gerar senhas</button>
      </div>
      <div class="panel"><h3>Senhas geradas</h3><div id="p-result" class="empty">—</div></div>
    </div>`;
  $("#p-go").onclick = async () => {
    const res = await api("/passwords/generate", { method: "POST", json: {
      length: +$("#p-length").value, count: +$("#p-count").value,
      upper: $("#p-upper").checked, lower: $("#p-lower").checked,
      digits: $("#p-digits").checked, symbols: $("#p-symbols").checked,
      exclude_ambiguous: $("#p-amb").checked,
    }});
    $("#p-result").className = "";
    $("#p-result").innerHTML = `
      <div style="display:flex;justify-content:flex-end;margin-bottom:4px">
        <button class="btn btn-sm" id="p-copy-all">📋 Copiar todas</button></div>` +
      res.passwords.map(p => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
        <span class="mono" style="font-size:15px">${esc(p)}</span>
        <button class="btn btn-sm" data-copy="${esc(p)}">📋</button>
      </div>`).join("");
    $("#p-copy-all").onclick = () =>
      copyText(res.passwords.join("\n"), `${res.passwords.length} senhas copiadas!`);
    $$("[data-copy]", $("#p-result")).forEach(el =>
      el.onclick = () => copyText(el.dataset.copy, "Senha copiada!"));
  };
};

/* ---------------- Manuais & Comandos ---------------- */
views.docs = async () => {
  const docs = await api("/docs");
  const cats = {};
  docs.forEach(d => (cats[d.category] = cats[d.category] || []).push(d));
  const CAT_LABEL = { manual: "📘 Manuais", certutil: "🪟 certutil", certreq: "🪟 certreq",
                      openssl: "🔧 OpenSSL", keytool: "☕ keytool", outros: "📎 Outros" };
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Manuais &amp; Comandos</div>
      <div class="view-sub">Guias de instalação e cheatsheets — editáveis</div>
    </div>
    <button class="btn btn-primary" id="doc-new">＋ Novo documento</button></div>
    <div class="docs-layout">
      <div class="panel" id="doc-list">
        ${Object.entries(cats).map(([cat, list]) => `
          <div class="doc-list-cat">${CAT_LABEL[cat] || cat}</div>
          ${list.map(d => `<button class="doc-list-item" data-doc="${d.id}">${esc(d.title)}</button>`).join("")}
        `).join("") || `<div class="empty">Nenhum documento</div>`}
      </div>
      <div class="panel" id="doc-content"><div class="empty">Selecione um documento à esquerda.</div></div>
    </div>`;

  async function show(id) {
    $$(".doc-list-item").forEach(b => b.classList.toggle("active", +b.dataset.doc === id));
    const d = await api(`/docs/${id}`);
    $("#doc-content").innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span class="muted">Atualizado em ${fmtDateTime(d.updated_at)}</span>
        <span><button class="btn btn-sm" id="doc-edit">✏️ Editar</button>
        <button class="btn btn-sm btn-danger" id="doc-del">Excluir</button></span>
      </div>
      <div class="md">${renderMd(d.content_md)}</div>`;
    $$("[data-copy-code]", $("#doc-content")).forEach(btn =>
      btn.onclick = () => copyText(btn.parentElement.textContent.replace(/^Copiar/, "").trim(), "Comando copiado!"));
    $("#doc-edit").onclick = () => editDoc(d);
    $("#doc-del").onclick = async () => {
      if (!confirm(`Excluir "${d.title}"?`)) return;
      await api(`/docs/${id}`, { method: "DELETE" });
      toast("Documento excluído"); views.docs();
    };
  }

  function editDoc(d) {
    modal(d ? "Editar documento" : "Novo documento", `
      <div class="form-row">
        <div class="field"><label>Título</label>
          <input class="input" id="e-title" value="${d ? esc(d.title) : ""}"></div>
        <div class="field"><label>Categoria</label>
          <select class="input" id="e-cat">
            ${["manual", "certutil", "certreq", "openssl", "keytool", "outros"].map(c =>
              `<option ${d && d.category === c ? "selected" : ""}>${c}</option>`).join("")}
          </select></div>
      </div>
      <div class="field"><label>Conteúdo (Markdown — use \`\`\` para blocos de comando)</label>
        <textarea class="input mono" id="e-content" rows="18">${d ? esc(d.content_md) : ""}</textarea></div>
    `, { large: true, footer: `<button class="btn" data-close>Cancelar</button>
        <button class="btn btn-primary" id="e-save">Salvar</button>` });
    $("#e-save").onclick = async () => {
      const body = { title: $("#e-title").value, category: $("#e-cat").value,
                     content_md: $("#e-content").value };
      if (!body.title.trim()) return toast("Informe o título", "err");
      if (d) await api(`/docs/${d.id}`, { method: "PUT", json: body });
      else await api("/docs", { method: "POST", json: body });
      closeModal(); toast("Documento salvo"); views.docs();
    };
  }

  $$(".doc-list-item").forEach(b => b.onclick = () => show(+b.dataset.doc));
  $("#doc-new").onclick = () => editDoc(null);
  if (docs.length) show(docs[0].id);
};

/* ---------------- Configurações ---------------- */
views.settings = async () => {
  const s = await api("/settings");
  const policy = JSON.parse(s.password_policy);
  const hsm = JSON.parse(s.hsmutil_templates);
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Configurações</div>
      <div class="view-sub">Pastas, alertas, política de senha e integração HSM</div>
    </div>
    <button class="btn btn-primary" id="s-save">💾 Salvar tudo</button></div>

    <div class="panel">
      <h3>Arquivos e pastas</h3>
      <div class="field"><label>Pasta base dos arquivos</label>
        <input class="input mono" id="s-base" value="${esc(s.base_dir)}"></div>
      <div class="field"><label>Template das pastas por demanda — placeholders: {env} {req} {cn}</label>
        <input class="input mono" id="s-template" value="${esc(s.folder_template)}"></div>
    </div>

    <div class="panel">
      <h3>Alertas de vencimento</h3>
      <div class="field"><label>Dias de alerta (separados por vírgula)</label>
        <input class="input" id="s-alerts" value="${esc(s.alert_days)}"></div>
    </div>

    <div class="panel">
      <h3>Política de senha (auto-geração das REQs)</h3>
      <div class="form-row">
        <div class="field"><label>Tamanho</label>
          <input class="input" type="number" id="s-plen" value="${policy.length}" min="8" max="64"></div>
      </div>
      <div class="checkbox-row"><input type="checkbox" id="s-pupper" ${policy.upper ? "checked" : ""}><label for="s-pupper" style="margin:0">Maiúsculas</label></div>
      <div class="checkbox-row"><input type="checkbox" id="s-plower" ${policy.lower ? "checked" : ""}><label for="s-plower" style="margin:0">Minúsculas</label></div>
      <div class="checkbox-row"><input type="checkbox" id="s-pdigits" ${policy.digits ? "checked" : ""}><label for="s-pdigits" style="margin:0">Dígitos</label></div>
      <div class="checkbox-row"><input type="checkbox" id="s-psymbols" ${policy.symbols ? "checked" : ""}><label for="s-psymbols" style="margin:0">Símbolos</label></div>
      <div class="checkbox-row"><input type="checkbox" id="s-pamb" ${policy.exclude_ambiguous ? "checked" : ""}><label for="s-pamb" style="margin:0">Excluir ambíguos</label></div>
    </div>

    <div class="panel">
      <h3>HSM — templates do hsmutil</h3>
      <div class="muted" style="margin-bottom:10px">
        Placeholders disponíveis: <code>{label}</code> <code>{cn}</code> <code>{sans}</code>
        <code>{keysize}</code> <code>{key_type}</code> <code>{out}</code></div>
      <div class="field"><label>Gerar chave</label>
        <input class="input mono" id="s-hgenkey" value="${esc(hsm.gen_key || "")}" placeholder="hsmutil genkey -l {label} -s {keysize}"></div>
      <div class="field"><label>Gerar CSR</label>
        <input class="input mono" id="s-hgencsr" value="${esc(hsm.gen_csr || "")}" placeholder="hsmutil gencsr -l {label} -cn {cn} -san {sans} -o {out}"></div>
      <div class="field"><label>Exportar chave</label>
        <input class="input mono" id="s-hexport" value="${esc(hsm.export_key || "")}" placeholder="hsmutil export -l {label} -o {out}"></div>
      <div class="field"><label>Engine padrão de CSR</label>
        <select class="input" id="s-engine">
          ${["local", "certreq", "hsmutil"].map(e =>
            `<option ${s.csr_default_engine === e ? "selected" : ""}>${e}</option>`).join("")}
        </select></div>
    </div>

    <div class="panel">
      <h3>Templates de resposta</h3>
      <div class="muted" style="margin-bottom:10px">
        Placeholders preenchidos com os dados da demanda: <code>{req}</code> <code>{cn}</code>
        <code>{env}</code> <code>{status}</code> <code>{senha}</code> <code>{vencimento}</code>
        <code>{emissor}</code> <code>{sans}</code> <code>{serial}</code> <code>{thumbprint}</code>
        <code>{locais}</code> <code>{notas}</code> <code>{data}</code></div>
      <div id="tpl-list"></div>
      <button class="btn btn-sm mt" id="tpl-new">＋ Novo template</button>
    </div>

    <div class="panel">
      <h3>Checklist de Ativação (CRQ)</h3>
      <div class="muted" style="margin-bottom:10px">
        Tarefas padrão criadas automaticamente em toda demanda de instalação em PRD (mudança/CRQ).
        A ordem aqui define a ordem exibida na demanda.</div>
      <div id="ck-list"></div>
      <button class="btn btn-sm mt" id="ck-new">＋ Nova tarefa padrão</button>
    </div>`;

  async function loadTpls() {
    const tpls = await api("/templates");
    $("#tpl-list").innerHTML = tpls.length ? tpls.map(t => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--border)">
        <div><strong>${esc(t.name)}</strong>
          <span class="muted">· atualizado ${fmtDateTime(t.updated_at)}</span></div>
        <span><button class="btn btn-sm" data-tpl-edit="${t.id}">✏️ Editar</button>
        <button class="btn btn-sm btn-danger" data-tpl-del="${t.id}">✕</button></span>
      </div>`).join("") : `<div class="muted">Nenhum template.</div>`;
    $$("[data-tpl-edit]").forEach(el => el.onclick = () =>
      tplModal(tpls.find(t => t.id === +el.dataset.tplEdit), loadTpls));
    $$("[data-tpl-del]").forEach(el => el.onclick = async () => {
      const t = tpls.find(x => x.id === +el.dataset.tplDel);
      if (!confirm(`Excluir o template "${t.name}"?`)) return;
      await api(`/templates/${t.id}`, { method: "DELETE" });
      toast("Template excluído"); loadTpls();
    });
  }

  function tplModal(t, onDone) {
    modal(t ? "Editar template" : "Novo template", `
      <div class="field"><label>Nome</label>
        <input class="input" id="tp-name" value="${t ? esc(t.name) : ""}"></div>
      <div class="field"><label>Conteúdo — use {req} {cn} {env} {senha} {vencimento} {locais} etc.</label>
        <textarea class="input mono" id="tp-content" rows="14">${t ? esc(t.content) : ""}</textarea></div>
    `, { large: true, footer: `<button class="btn" data-close>Cancelar</button>
        <button class="btn btn-primary" id="tp-save">Salvar</button>` });
    $("#tp-save").onclick = async () => {
      const body = { name: $("#tp-name").value, content: $("#tp-content").value };
      try {
        if (t) await api(`/templates/${t.id}`, { method: "PUT", json: body });
        else await api("/templates", { method: "POST", json: body });
        closeModal(); toast("Template salvo"); onDone && onDone();
      } catch (e) { toast(e.message, "err"); }
    };
  }

  $("#tpl-new").onclick = () => tplModal(null, loadTpls);
  await loadTpls();

  async function loadChecklist() {
    const tpls = await api("/checklist-templates");
    $("#ck-list").innerHTML = tpls.length ? tpls.map(t => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--border)">
        <div>
          <span class="mono muted">#${t.position}</span> <strong>${esc(t.title)}</strong>
          ${!t.active ? '<span class="badge badge-days-danger" style="margin-left:6px">inativa</span>' : ''}
          <div class="muted">${esc(t.instructions)}</div>
        </div>
        <span style="white-space:nowrap"><button class="btn btn-sm" data-ck-edit="${t.id}">✏️ Editar</button>
        <button class="btn btn-sm btn-danger" data-ck-del="${t.id}">✕</button></span>
      </div>`).join("") : `<div class="muted">Nenhuma tarefa padrão cadastrada.</div>`;
    $$("[data-ck-edit]").forEach(el => el.onclick = () =>
      checklistTplModal(tpls.find(t => t.id === +el.dataset.ckEdit), loadChecklist));
    $$("[data-ck-del]").forEach(el => el.onclick = async () => {
      const t = tpls.find(x => x.id === +el.dataset.ckDel);
      if (!confirm(`Excluir a tarefa padrão "${t.title}"?`)) return;
      await api(`/checklist-templates/${t.id}`, { method: "DELETE" });
      toast("Tarefa padrão excluída"); loadChecklist();
    });
  }

  const DEFAULT_MESSAGE_TEMPLATE = "📋 {tarefa} — {status}\nDemanda: {req} · {cn} ({env})\n"
    + "Instruções: {instrucoes}\nNotas: {notas}\nEvidências: {evidencias}\nAtualizado em {data}";

  function checklistTplModal(t, onDone) {
    modal(t ? "Editar tarefa padrão" : "Nova tarefa padrão", `
      <div class="form-row">
        <div class="field"><label>Título</label>
          <input class="input" id="ck-title" value="${t ? esc(t.title) : ""}"></div>
        <div class="field" style="max-width:110px"><label>Ordem</label>
          <input class="input" type="number" id="ck-position" value="${t ? t.position : 0}"></div>
      </div>
      <div class="field"><label>Instruções</label>
        <textarea class="input" id="ck-instructions" rows="4">${t ? esc(t.instructions) : ""}</textarea></div>
      <div class="field"><label>Mensagem (template para copiar/colar no ticket)</label>
        <div class="muted" style="margin-bottom:4px">Placeholders: <code>{tarefa}</code> <code>{status}</code>
          <code>{req}</code> <code>{cn}</code> <code>{env}</code> <code>{instrucoes}</code>
          <code>{notas}</code> <code>{evidencias}</code> <code>{data}</code></div>
        <textarea class="input mono" id="ck-message" rows="6">${esc((t ? t.message_template : "") || DEFAULT_MESSAGE_TEMPLATE)}</textarea></div>
      <div class="checkbox-row"><input type="checkbox" id="ck-active" ${!t || t.active ? "checked" : ""}>
        <label for="ck-active" style="margin:0">Ativa (entra no checklist de novas instalações)</label></div>
    `, { large: true, footer: `<button class="btn" data-close>Cancelar</button>
        <button class="btn btn-primary" id="ck-save">Salvar</button>` });
    $("#ck-save").onclick = async () => {
      const body = {
        title: $("#ck-title").value,
        instructions: $("#ck-instructions").value,
        message_template: $("#ck-message").value,
        position: +$("#ck-position").value || 0,
        active: $("#ck-active").checked,
      };
      try {
        if (t) await api(`/checklist-templates/${t.id}`, { method: "PUT", json: body });
        else await api("/checklist-templates", { method: "POST", json: body });
        closeModal(); toast("Tarefa padrão salva"); onDone && onDone();
      } catch (e) { toast(e.message, "err"); }
    };
  }

  $("#ck-new").onclick = () => checklistTplModal(null, loadChecklist);
  await loadChecklist();

  $("#s-save").onclick = async () => {
    try {
      await api("/settings", { method: "PUT", json: { values: {
        base_dir: $("#s-base").value,
        folder_template: $("#s-template").value,
        alert_days: $("#s-alerts").value,
        password_policy: JSON.stringify({
          length: +$("#s-plen").value,
          upper: $("#s-pupper").checked, lower: $("#s-plower").checked,
          digits: $("#s-pdigits").checked, symbols: $("#s-psymbols").checked,
          exclude_ambiguous: $("#s-pamb").checked,
        }),
        hsmutil_templates: JSON.stringify({
          gen_key: $("#s-hgenkey").value, gen_csr: $("#s-hgencsr").value,
          export_key: $("#s-hexport").value,
        }),
        csr_default_engine: $("#s-engine").value,
      }}});
      toast("Configurações salvas");
    } catch (e) { toast(e.message, "err"); }
  };
};

/* ---------------- Validar cadeia ---------------- */
views.validate = async () => {
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Validar cadeia</div>
      <div class="view-sub">Análise elo a elo: assinaturas, validade, hostname e cadeia completa</div>
    </div></div>
    <div class="grid grid-2">
      <div>
        <div class="panel">
          <h3>Arquivos locais</h3>
          <div class="field"><label>Certificado + intermediárias (.cer .crt .pem .der .p7b — selecione vários)</label>
            <input class="input" type="file" id="v-files" multiple accept=".cer,.crt,.pem,.der,.p7b"></div>
          <div class="field"><label>Hostname a conferir (opcional)</label>
            <input class="input" id="v-host" placeholder="www.exemplo.com.br"></div>
          <div class="checkbox-row"><input type="checkbox" id="v-aia">
            <label for="v-aia" style="margin:0">Baixar intermediárias faltantes via AIA (requer acesso à URL da CA)</label></div>
          <button class="btn btn-primary" id="v-go">🔗 Validar cadeia</button>
        </div>
        <div class="panel">
          <h3>Servidor remoto (TLS)</h3>
          <div class="form-row">
            <div class="field" style="flex:3"><label>Host</label>
              <input class="input" id="v-rhost" placeholder="intranet.exemplo.com.br"></div>
            <div class="field"><label>Porta</label>
              <input class="input" id="v-rport" type="number" value="443"></div>
          </div>
          <button class="btn btn-primary" id="v-rgo">🌐 Consultar servidor</button>
        </div>
      </div>
      <div class="panel" id="v-result"><h3>Resultado</h3>
        <div class="empty">Envie arquivos ou consulte um servidor.</div></div>
    </div>`;

  const VERDICT = {
    valida: ["✅", "Cadeia válida e completa até a raiz"],
    incompleta: ["⚠️", "Elos válidos, mas a cadeia não chega a uma raiz autoassinada"],
    invalida: ["❌", "Cadeia inválida — há elo quebrado ou certificado fora da validade"],
  };

  function renderResult(res) {
    const [icon, label] = VERDICT[res.verdict] || ["❓", res.verdict];
    let html = `<h3>Resultado${res.server ? ` — ${esc(res.server)}` : ""}</h3>
      <div class="verdict ${esc(res.verdict)}">${icon} ${esc(label)}</div>`;
    if (res.tls) html += `<div class="chips" style="margin-bottom:10px">
      <span class="badge k-cat">${esc(res.tls.version || "")}</span>
      <span class="badge k-cat">${esc(res.tls.cipher || "")}</span></div>`;
    if (res.hostname) html += `<div class="chips" style="margin-bottom:10px">
      <span class="badge badge-days-${res.hostname_ok ? "ok" : "danger"}">
        hostname ${esc(res.hostname)}: ${res.hostname_ok ? "confere ✓" : "NÃO confere ✗"}</span></div>`;

    html += res.chain.map((c, i) => {
      const bad = c.sig_ok === false || c.expired || c.not_yet_valid;
      const kind = i === 0 ? "📄 Certificado final" : c.self_signed ? "🏛️ Raiz (autoassinada)" : "🔗 Intermediária";
      const sig = c.self_signed
        ? (c.sig_ok ? "autoassinatura válida ✓" : "autoassinatura inválida ✗")
        : c.sig_ok === null ? "emissor não fornecido"
        : c.sig_ok ? `assinatura de "${esc(c.issuer_cn)}" válida ✓` : `assinatura inválida ✗ ${esc(c.sig_error)}`;
      return `${i > 0 ? `<div class="chain-arrow">▲ assinado por</div>` : ""}
        <div class="chain-link ${bad ? "bad" : ""}">
          <div class="k-meta"><span class="badge ${bad ? "badge-days-danger" : "badge-days-ok"}">${kind}</span>
            ${daysBadge(c.days_left)} ${c.is_ca ? `<span class="badge k-cat">CA</span>` : ""}</div>
          <div class="k-title">${esc(c.cn)}</div>
          <div class="muted">${fmtDate(c.not_before.slice(0, 10))} → ${fmtDate(c.not_after.slice(0, 10))}
            · ${esc(c.key)} · ${esc(c.sig_algo)}</div>
          <div class="muted">${sig}</div>
          ${c.sans.length ? `<div class="muted">SANs: ${esc(c.sans.join(", "))}</div>` : ""}
          <div class="muted mono" style="font-size:11px">serial ${esc(c.serial)}</div>
        </div>`;
    }).join("");

    if (res.missing) {
      html += `<div class="chain-arrow">▲ assinado por</div>
        <div class="chain-link bad"><div class="k-title">❓ ${esc(res.missing.issuer)}</div>
        <div class="muted">Emissor não fornecido.${res.missing.aia_url
          ? ` Disponível via AIA: <span class="mono">${esc(res.missing.aia_url)}</span> — marque a opção AIA e valide de novo.`
          : ""}</div></div>`;
    }
    if (res.warnings.length) html += `<div class="mt">${res.warnings.map(w =>
      `<div class="muted">⚠️ ${esc(w)}</div>`).join("")}</div>`;
    $("#v-result").innerHTML = html;
  }

  $("#v-go").onclick = async () => {
    const files = $("#v-files").files;
    if (!files.length) return toast("Selecione ao menos um arquivo", "err");
    const fd = new FormData();
    [...files].forEach(f => fd.append("files", f));
    fd.append("hostname", $("#v-host").value);
    fd.append("fetch_aia", $("#v-aia").checked);
    const btn = $("#v-go"); btn.disabled = true;
    try { renderResult(await api("/validate/chain", { method: "POST", body: fd })); }
    catch (e) { toast(e.message, "err"); }
    btn.disabled = false;
  };
  $("#v-rgo").onclick = async () => {
    if (!$("#v-rhost").value.trim()) return toast("Informe o host", "err");
    const btn = $("#v-rgo"); btn.disabled = true; btn.textContent = "Consultando…";
    try {
      renderResult(await api("/validate/remote", { method: "POST", json: {
        host: $("#v-rhost").value, port: +$("#v-rport").value || 443,
        fetch_aia: $("#v-aia") ? $("#v-aia").checked : false,
      }}));
    } catch (e) { toast(e.message, "err"); }
    btn.disabled = false; btn.textContent = "🌐 Consultar servidor";
  };
};

/* ---------------- Analytics ---------------- */
const PALETTE = ["var(--accent)", "var(--green)", "var(--amber)", "var(--purple)",
                 "var(--teal)", "var(--red)", "var(--gray)"];
const fmtMonth = m => m ? `${m.slice(5, 7)}/${m.slice(2, 4)}` : "";

function chartVBars(items, { fmt = l => l, color = "var(--accent)" } = {}) {
  if (!items.length) return `<div class="empty">Sem dados</div>`;
  const max = Math.max(...items.map(i => i.n), 1);
  return `<div class="chart-vbars">${items.map(i => `
    <div class="vbar-col" title="${esc(i.label)}: ${i.n}">
      <div class="vbar-val">${i.n || ""}</div>
      <div class="vbar" style="height:${Math.round(i.n / max * 120) + 2}px;background:${color}"></div>
      <div class="vbar-label">${esc(fmt(i.label))}</div>
    </div>`).join("")}</div>`;
}

function chartHBars(items, colorOf = (i, idx) => PALETTE[idx % PALETTE.length]) {
  if (!items.length) return `<div class="empty">Sem dados</div>`;
  const max = Math.max(...items.map(i => i.n), 1);
  return items.map((i, idx) => `
    <div class="hbar-row">
      <div class="hbar-label" title="${esc(i.label)}">${esc(i.label)}</div>
      <div class="hbar-track"><div class="hbar"
        style="width:${Math.max(i.n / max * 100, 2)}%;background:${colorOf(i, idx)}"></div></div>
      <div class="hbar-val">${i.n}</div>
    </div>`).join("");
}

function chartDonut(items) {
  const data = items.filter(i => i.n > 0);
  const total = data.reduce((s, i) => s + i.n, 0);
  if (!total) return `<div class="empty">Sem dados</div>`;
  let acc = 0;
  const stops = data.map((i, idx) => {
    const from = acc / total * 360; acc += i.n;
    return `${i.color || PALETTE[idx % PALETTE.length]} ${from}deg ${acc / total * 360}deg`;
  });
  return `<div class="donut-wrap">
    <div class="donut" style="background:conic-gradient(${stops.join(",")})">
      <div class="donut-hole">${total}</div></div>
    <div class="donut-legend">${data.map((i, idx) => `
      <div><span class="dot" style="background:${i.color || PALETTE[idx % PALETTE.length]}"></span>
        ${esc(i.label)} <strong>${i.n}</strong></div>`).join("")}</div>
  </div>`;
}

/* views.analytics removida — dados fundidos no dashboard */

/* ---------------- Usuários ---------------- */
views.users = async () => {
  main.innerHTML = `<div class="empty">Carregando…</div>`;
  if (window._currentUser?.role !== 'admin') {
    main.innerHTML = `<div class="empty">Acesso negado</div>`;
    return;
  }
  
  const users = await api("/users");
  
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Usuários</div>
      <div class="view-sub">Gerenciamento de acesso ao CertHub</div>
    </div>
    <button class="btn btn-primary" id="btn-new-user">+ Novo usuário</button>
    </div>
    
    <div class="panel">
      <table class="table">
        <thead>
          <tr>
            <th>Usuário</th>
            <th>Nome</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          ${users.map(u => `
            <tr>
              <td>${esc(u.username)}</td>
              <td>${esc(u.display_name)}</td>
              <td>${esc(u.email)}</td>
              <td><span class="badge badge-role-${esc(u.role)}">${esc(u.role)}</span></td>
              <td>${u.active ? '<span class="badge badge-ok">Ativo</span>' : '<span class="badge badge-warn">Inativo</span>'}</td>
              <td class="row-actions">
                <button class="btn btn-ghost btn-sm" data-edit="${u.id}">Editar</button>
                <button class="btn btn-ghost btn-sm" data-reset="${u.id}">Senha</button>
                <button class="btn btn-ghost btn-sm" data-del="${u.id}" ${u.id === window._currentUser.id ? 'disabled' : ''}>Desativar</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>`;
    
  $("#btn-new-user").onclick = () => showUserModal();
  
  $$("[data-edit]").forEach(btn => btn.onclick = () => {
    const u = users.find(x => x.id == btn.dataset.edit);
    if (u) showUserModal(u);
  });
  
  $$("[data-reset]").forEach(btn => btn.onclick = () => {
    const id = btn.dataset.reset;
    const body = `
      <div class="form-group"><label>Nova senha</label>
      <input type="password" id="u-new-pwd" class="input"></div>
    `;
    const m = modal("Redefinir Senha", body, {
      footer: `<button class="btn" data-close>Cancelar</button>
               <button class="btn btn-primary" id="btn-save-pwd">Salvar</button>`
    });
    $("#btn-save-pwd", m).onclick = async () => {
      const p = $("#u-new-pwd", m).value;
      if (!p) return toast("Senha não pode ser vazia", "error");
      await api(`/users/${id}/reset-password`, { method: "POST", json: { new_password: p } });
      toast("Senha redefinida!");
      closeModal();
    };
  });
  
  $$("[data-del]").forEach(btn => btn.onclick = async () => {
    if (!confirm("Desativar este usuário?")) return;
    await api(`/users/${btn.dataset.del}`, { method: "DELETE" });
    toast("Usuário desativado!");
    views.users();
  });
};

function showUserModal(u = null) {
  const isEdit = !!u;
  const body = `
    <div class="form-group"><label>Username</label>
    <input type="text" id="u-user" class="input" value="${esc(u?.username)}" ${isEdit ? "disabled" : ""}></div>
    <div class="form-group"><label>Nome de exibição</label>
    <input type="text" id="u-name" class="input" value="${esc(u?.display_name)}"></div>
    <div class="form-group"><label>Email</label>
    <input type="email" id="u-email" class="input" value="${esc(u?.email)}"></div>
    <div class="form-group"><label>Role</label>
    <select id="u-role" class="input">
      <option value="viewer" ${u?.role === 'viewer' ? 'selected' : ''}>Visualizador (viewer)</option>
      <option value="operator" ${u?.role === 'operator' ? 'selected' : ''}>Operador (operator)</option>
      <option value="admin" ${u?.role === 'admin' ? 'selected' : ''}>Administrador (admin)</option>
    </select></div>
    ${isEdit ? `
    <div class="form-group"><label>Status</label>
    <select id="u-active" class="input">
      <option value="1" ${u?.active ? 'selected' : ''}>Ativo</option>
      <option value="0" ${!u?.active ? 'selected' : ''}>Inativo</option>
    </select></div>
    ` : `
    <div class="form-group"><label>Senha provisória</label>
    <input type="password" id="u-pwd" class="input"></div>
    `}
  `;
  const m = modal(isEdit ? "Editar Usuário" : "Novo Usuário", body, {
    footer: `<button class="btn" data-close>Cancelar</button>
             <button class="btn btn-primary" id="btn-save-user">Salvar</button>`
  });
  
  $("#btn-save-user", m).onclick = async () => {
    const data = {
      display_name: $("#u-name", m).value,
      email: $("#u-email", m).value,
      role: $("#u-role", m).value
    };
    try {
      if (isEdit) {
        data.active = parseInt($("#u-active", m).value);
        await api(`/users/${u.id}`, { method: "PUT", json: data });
        toast("Usuário atualizado!");
      } else {
        data.username = $("#u-user", m).value;
        data.password = $("#u-pwd", m).value;
        if (!data.username || !data.password) return toast("Username e senha obrigatórios", "error");
        await api("/users", { method: "POST", json: data });
        toast("Usuário criado!");
      }
      closeModal();
      views.users();
    } catch (e) {
      toast(e.message, "error");
    }
  };
}

/* ---------------- Aparência ---------------- */
const ACCENTS = [
  ["blue", "#3b6ef6"], ["green", "#1f9d63"], ["purple", "#7a4fd4"],
  ["teal", "#0e8f96"], ["amber", "#b97e0a"], ["red", "#d4384c"],
];

views.appearance = async () => {
  const cur = () => ({
    theme: document.documentElement.dataset.theme,
    layout: document.documentElement.dataset.layout || "side",
    accent: document.documentElement.dataset.accent || "blue",
  });
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Aparência</div>
      <div class="view-sub">Preferências visuais — salvas neste navegador</div>
    </div></div>
    <div class="panel"><h3>Tema</h3>
      <div class="appearance-grid">
        <div class="app-opt" data-set="theme" data-val="light"><div class="opt-icon">🌞</div>Claro</div>
        <div class="app-opt" data-set="theme" data-val="dark"><div class="opt-icon">🌙</div>Escuro</div>
      </div></div>
    <div class="panel"><h3>Posição do menu</h3>
      <div class="appearance-grid">
        <div class="app-opt" data-set="layout" data-val="side"><div class="opt-icon">◧</div>Lateral</div>
        <div class="app-opt" data-set="layout" data-val="compact"><div class="opt-icon">▮</div>Compacto (só ícones)</div>
        <div class="app-opt" data-set="layout" data-val="top"><div class="opt-icon">⬒</div>Horizontal</div>
      </div></div>
    <div class="panel"><h3>Cor de destaque</h3>
      <div class="appearance-grid">
        ${ACCENTS.map(([name, hex]) => `
          <div class="swatch" data-set="accent" data-val="${name}" title="${name}"
               style="background:${hex}"></div>`).join("")}
      </div></div>`;

  function refresh() {
    const c = cur();
    $$("[data-set]").forEach(el =>
      el.classList.toggle("active", c[el.dataset.set] === el.dataset.val));
  }
  $$("[data-set]").forEach(el => el.onclick = () => {
    const { set, val } = el.dataset;
    if (set === "theme") applyTheme(val);
    if (set === "layout") applyLayout(val);
    if (set === "accent") applyAccent(val);
    refresh();
  });
  refresh();
};

/* ---------------- tema ---------------- */
const themeBtn = $("#theme-toggle");
const collapseBtn = $("#menu-collapse");
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  localStorage.setItem("certhub-theme", t);
  themeBtn.innerHTML = t === "dark"
    ? `☀️<span class="nav-txt"> Tema claro</span>`
    : `🌙<span class="nav-txt"> Tema escuro</span>`;
}
function applyLayout(l) {
  document.documentElement.dataset.layout = l;
  localStorage.setItem("certhub-layout", l);
  collapseBtn.textContent = l === "compact" ? "⇥" : "⇤";
  collapseBtn.title = l === "compact" ? "Expandir menu" : "Recolher menu";
}
collapseBtn.onclick = () =>
  applyLayout(document.documentElement.dataset.layout === "compact" ? "side" : "compact");
function applyAccent(a) {
  document.documentElement.dataset.accent = a;
  localStorage.setItem("certhub-accent", a);
}
themeBtn.onclick = () =>
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
applyTheme(localStorage.getItem("certhub-theme") || "dark");
applyLayout(localStorage.getItem("certhub-layout") || "side");
applyAccent(localStorage.getItem("certhub-accent") || "blue");

(async () => {
  try {
    const me = await api('/auth/me');
    window._currentUser = me;
    const userEl = document.getElementById('sidebar-user');
    if (userEl) {
      userEl.innerHTML = `<span class="user-name">${esc(me.display_name || me.username)}</span><span class="badge badge-role-${esc(me.role)}">${esc(me.role)}</span>`;
    }
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
      btnLogout.onclick = async () => {
        await fetch('/api/auth/logout', { method: 'POST' });
        window.location.href = '/login';
      };
    }
  } catch (e) {
    if (!location.pathname.includes('/login')) {
      window.location.href = '/login';
      return;
    }
  }
  navigate();
})();

/* views.workOrders removida — WO/CRQ gerida dentro modal de instalação */
