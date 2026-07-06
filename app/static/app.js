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
        <div class="modal-header"><h2>${esc(title)}</h2>
          <button class="btn btn-ghost btn-sm" data-close>✕</button></div>
        <div class="modal-body">${bodyHtml}</div>
        ${footer ? `<div class="modal-footer">${footer}</div>` : ""}
      </div>
    </div>`;
  const overlay = $(".modal-overlay", root);
  overlay.addEventListener("click", e => {
    if (e.target === overlay || e.target.closest("[data-close]")) closeModal();
  });
  return $(".modal", root);
}
function closeModal() { $("#modal-root").innerHTML = ""; }

const ENVS = ["PRD", "TQS", "HMP", "DES"];
const STATUSES = ["aberta", "csr_gerada", "cert_emitido", "instalado", "concluida", "cancelada"];
const STATUS_LABEL = {
  aberta: "Aberta", csr_gerada: "CSR gerada", cert_emitido: "Cert. emitido",
  instalado: "Instalado", concluida: "Concluída", cancelada: "Cancelada",
};
const envBadge = e => `<span class="badge badge-${esc(e)}">${esc(e)}</span>`;
const statusBadge = s => `<span class="badge badge-${esc(s)}">${esc(STATUS_LABEL[s] || s)}</span>`;
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
    </div>`;
};

/* ---------------- Demandas ---------------- */
views.reqs = async () => {
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Demandas (REQ)</div>
      <div class="view-sub">Registro e acompanhamento das requisições de certificado</div>
    </div>
    <button class="btn btn-primary" id="new-req">＋ Nova demanda</button></div>
    <div class="panel">
      <div class="toolbar" style="margin-bottom:12px">
        <input class="input" id="f-search" placeholder="Buscar REQ, CN, notas…" style="min-width:220px">
        <select class="input" id="f-env"><option value="">Ambiente</option>${ENVS.map(e => `<option>${e}</option>`).join("")}</select>
        <select class="input" id="f-status"><option value="">Status</option>${STATUSES.map(s => `<option value="${s}">${STATUS_LABEL[s]}</option>`).join("")}</select>
      </div>
      <div id="req-table"></div>
    </div>`;

  async function load() {
    const params = new URLSearchParams({
      search: $("#f-search").value, env: $("#f-env").value, status: $("#f-status").value,
    });
    const rows = await api("/reqs?" + params);
    $("#req-table").innerHTML = rows.length ? `
      <table class="tbl"><thead><tr>
        <th>REQ</th><th>CN</th><th>Env</th><th>Status</th><th>Senha</th><th>Certs</th><th>Criada</th><th></th>
      </tr></thead><tbody>
      ${rows.map(r => `<tr>
        <td class="mono">${esc(r.req_number)}</td>
        <td>${esc(r.cn)}</td>
        <td>${envBadge(r.env)}</td>
        <td>${statusBadge(r.status)}</td>
        <td>${r.password ? `<span class="password-cell" data-pwd="${esc(r.password)}" title="Clique para copiar">••••••••</span>` : "—"}</td>
        <td>${r.cert_count}</td>
        <td>${fmtDate(r.created_at)}</td>
        <td><button class="btn btn-sm" data-open="${r.id}">Abrir</button></td>
      </tr>`).join("")}</tbody></table>`
      : `<div class="empty">Nenhuma demanda encontrada. Crie a primeira!</div>`;

    $$("[data-pwd]").forEach(el => el.onclick = () => copyText(el.dataset.pwd, "Senha copiada!"));
    $$("[data-open]").forEach(el => el.onclick = () => openReq(+el.dataset.open, load));
  }
  $("#f-search").oninput = () => { clearTimeout(window._t); window._t = setTimeout(load, 300); };
  $("#f-env").onchange = $("#f-status").onchange = load;
  $("#new-req").onclick = () => newReqModal(load);
  await load();
};

function newReqModal(onDone) {
  modal("Nova demanda", `
    <div class="form-row">
      <div class="field"><label>Número da REQ</label>
        <input class="input mono" id="n-req" placeholder="REQ0012345" maxlength="10"></div>
      <div class="field"><label>Ambiente</label>
        <select class="input" id="n-env">${ENVS.map(e => `<option>${e}</option>`).join("")}</select></div>
    </div>
    <div class="field"><label>CN (Common Name)</label>
      <input class="input" id="n-cn" placeholder="www.exemplo.com.br"></div>
    <div class="field"><label>Notas / observações</label>
      <textarea class="input" id="n-notes" placeholder="Detalhes da demanda, solicitante, sistema…"></textarea></div>
    <div class="checkbox-row"><input type="checkbox" id="n-auto" checked>
      <label for="n-auto" style="margin:0">Gerar senha automaticamente</label></div>
  `, { footer: `<button class="btn" data-close>Cancelar</button>
                <button class="btn btn-primary" id="n-save">Criar demanda</button>` });
  $("#n-save").onclick = async () => {
    try {
      const row = await api("/reqs", { method: "POST", json: {
        req_number: $("#n-req").value, cn: $("#n-cn").value,
        env: $("#n-env").value, notes: $("#n-notes").value,
        auto_password: $("#n-auto").checked,
      }});
      closeModal();
      toast(`Demanda ${row.req_number} criada` + (row.password ? " · senha gerada" : ""));
      onDone && onDone();
    } catch (e) { toast(e.message, "err"); }
  };
}

async function openReq(id, onDone) {
  const r = await api(`/reqs/${id}`);
  modal(`${r.req_number} — ${r.cn}`, `
    <div class="chips" style="margin-bottom:14px">${envBadge(r.env)} ${statusBadge(r.status)}
      <span class="muted">criada em ${fmtDateTime(r.created_at)}</span></div>

    <div class="form-row">
      <div class="field"><label>Status</label>
        <select class="input" id="d-status">${STATUSES.map(s =>
          `<option value="${s}" ${s === r.status ? "selected" : ""}>${STATUS_LABEL[s]}</option>`).join("")}</select></div>
      <div class="field"><label>Senha</label>
        <div style="display:flex;gap:6px">
          <input class="input mono" id="d-pwd" value="${esc(r.password || "")}" readonly>
          <button class="btn btn-sm" id="d-pwd-copy" title="Copiar">📋</button>
          <button class="btn btn-sm" id="d-pwd-regen" title="Regenerar">🎲</button>
        </div></div>
    </div>
    <div class="field"><label>Notas / observações</label>
      <textarea class="input" id="d-notes">${esc(r.notes || "")}</textarea></div>

    <div class="field"><label>Pasta da demanda</label>
      <div style="display:flex;gap:6px;align-items:center">
        <input class="input mono" value="${esc(r.folder)}" readonly>
        <button class="btn btn-sm" id="d-folder-make">Criar</button>
        <button class="btn btn-sm" id="d-folder-open" ${r.folder_exists ? "" : "disabled"}>Abrir</button>
      </div></div>

    <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Locais de instalação</h3>
    <div id="d-locs">${r.locations.map(l => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid var(--border)">
        <div><strong>${esc(l.server)}</strong> <span class="muted">${esc(l.path_or_store)}</span>
          ${l.installed_at ? `<span class="muted">· instalado ${fmtDate(l.installed_at)}</span>` : ""}
          ${l.notes ? `<div class="muted">${esc(l.notes)}</div>` : ""}</div>
        <button class="btn btn-sm btn-danger" data-del-loc="${l.id}">✕</button>
      </div>`).join("") || `<div class="muted">Nenhum local registrado.</div>`}</div>
    <div class="form-row mt">
      <div class="field"><label>Servidor</label><input class="input" id="l-server" placeholder="SRVWEB01"></div>
      <div class="field"><label>Caminho / store</label><input class="input" id="l-path" placeholder="IIS binding 443 · LocalMachine\\My"></div>
    </div>
    <button class="btn btn-sm" id="l-add">＋ Adicionar local</button>

    <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Certificados vinculados</h3>
    ${r.certificates.length ? `<table class="tbl"><tbody>${r.certificates.map(c => `
      <tr><td>${esc(c.cn)}</td><td>${fmtDate(c.not_after)}</td>
      <td class="mono muted">${esc((c.thumbprint_sha1 || "").slice(0, 16))}…</td></tr>`).join("")}</tbody></table>`
      : `<div class="muted">Nenhum certificado importado ainda.</div>`}

    <h3 style="margin:16px 0 8px;font-size:13px;color:var(--text-dim);text-transform:uppercase">Histórico</h3>
    <ul class="timeline">${r.activity.map(a => `
      <li><div>${esc(a.action.replaceAll("_", " "))}</div>
        <div class="muted">${esc(a.detail)}</div>
        <div class="t-when">${fmtDateTime(a.created_at)}</div></li>`).join("") || ""}</ul>
  `, { large: true, footer: `
      <button class="btn btn-danger" id="d-delete">Excluir demanda</button>
      <button class="btn" id="d-gocsr">📝 Gerar CSR</button>
      <button class="btn btn-primary" id="d-save">Salvar</button>` });

  $("#d-pwd-copy").onclick = () => copyText($("#d-pwd").value, "Senha copiada!");
  $("#d-pwd-regen").onclick = async () => {
    if (!confirm("Regenerar a senha desta demanda?")) return;
    const res = await api(`/reqs/${id}/password/regenerate`, { method: "POST" });
    $("#d-pwd").value = res.password;
    toast("Nova senha gerada");
  };
  $("#d-folder-make").onclick = async () => {
    const res = await api(`/reqs/${id}/folder`, { method: "POST" });
    toast("Pasta criada: " + res.folder);
    $("#d-folder-open").disabled = false;
  };
  $("#d-folder-open").onclick = async () => {
    try { await api("/files/open", { method: "POST", json: { path: r.folder } }); }
    catch (e) { toast(e.message, "err"); }
  };
  $("#l-add").onclick = async () => {
    if (!$("#l-server").value.trim()) return toast("Informe o servidor", "err");
    await api(`/reqs/${id}/locations`, { method: "POST", json: {
      server: $("#l-server").value, path_or_store: $("#l-path").value,
    }});
    closeModal(); openReq(id, onDone);
  };
  $$("[data-del-loc]").forEach(el => el.onclick = async () => {
    await api(`/locations/${el.dataset.delLoc}`, { method: "DELETE" });
    closeModal(); openReq(id, onDone);
  });
  $("#d-gocsr").onclick = () => {
    csrPrefill = { req_id: id, cn: r.cn, req_number: r.req_number };
    closeModal(); location.hash = "#/csr";
  };
  $("#d-save").onclick = async () => {
    await api(`/reqs/${id}`, { method: "PUT", json: {
      status: $("#d-status").value, notes: $("#d-notes").value,
    }});
    closeModal(); toast("Demanda atualizada"); onDone && onDone();
  };
  $("#d-delete").onclick = async () => {
    if (!confirm(`Excluir a demanda ${r.req_number}? O histórico e locais serão removidos.`)) return;
    await api(`/reqs/${id}`, { method: "DELETE" });
    closeModal(); toast("Demanda excluída"); onDone && onDone();
  };
}

/* ---------------- Gerar CSR ---------------- */
views.csr = async () => {
  const reqs = await api("/reqs");
  const open = reqs.filter(r => !["concluida", "cancelada"].includes(r.status));
  const pre = csrPrefill; csrPrefill = null;
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Gerar CSR</div>
      <div class="view-sub">Chave + CSR com suporte a wildcard e SANs — local, certreq ou HSM</div>
    </div></div>
    <div class="grid grid-2">
      <div class="panel">
        <div class="field"><label>Engine</label>
          <select class="input" id="c-engine">
            <option value="local">Local (biblioteca cryptography)</option>
            <option value="certreq">certreq — Windows (.inf)</option>
            <option value="hsmutil">HSM (hsmutil CLI)</option>
          </select></div>
        <div class="field"><label>Demanda vinculada (opcional — salva os arquivos na pasta da REQ)</label>
          <select class="input" id="c-req">
            <option value="">— nenhuma —</option>
            ${open.map(r => `<option value="${r.id}" ${pre && pre.req_id === r.id ? "selected" : ""}>
              ${esc(r.req_number)} · ${esc(r.cn)} (${r.env})</option>`).join("")}
          </select></div>
        <div class="field"><label>CN (Common Name)</label>
          <div style="display:flex;gap:6px">
            <input class="input" id="c-cn" placeholder="www.exemplo.com.br" value="${pre ? esc(pre.cn) : ""}">
            <button class="btn" id="c-wild" title="Transformar em wildcard">*.</button>
          </div></div>
        <div class="field"><label>SANs — um por linha (o CN é incluído automaticamente)</label>
          <textarea class="input mono" id="c-sans" placeholder="exemplo.com.br&#10;app.exemplo.com.br"></textarea></div>
        <div class="form-row">
          <div class="field"><label>Chave</label>
            <select class="input" id="c-key">
              <option value="rsa2048">RSA 2048</option>
              <option value="rsa4096">RSA 4096</option>
              <option value="ecp256">EC P-256</option>
            </select></div>
          <div class="field"><label>Organização (O)</label><input class="input" id="c-org" placeholder="Empresa"></div>
          <div class="field"><label>País (C)</label><input class="input" id="c-country" placeholder="BR" maxlength="2"></div>
        </div>
        <div class="field" id="c-label-field" style="display:none"><label>Label da chave no HSM</label>
          <input class="input mono" id="c-label" placeholder="cert_exemplo_2026"></div>
        <button class="btn btn-primary" id="c-go">Gerar CSR</button>
      </div>
      <div class="panel" id="c-result"><h3>Resultado</h3>
        <div class="empty">Preencha o formulário e clique em “Gerar CSR”.</div></div>
    </div>`;

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
        org: $("#c-org").value, country: $("#c-country").value.toUpperCase(),
        engine: $("#c-engine").value,
        req_id: $("#c-req").value ? +$("#c-req").value : null,
        hsm_label: $("#c-label").value,
      }});
      renderCsrResult(res);
      if (res.ok) toast("CSR gerada com sucesso"); else toast("Falha na geração — veja a saída", "err");
    } catch (e) { toast(e.message, "err"); }
    btn.disabled = false; btn.textContent = "Gerar CSR";
  };

  function renderCsrResult(res) {
    let html = `<h3>Resultado — engine ${esc(res.engine)}</h3>`;
    if (res.csr_pem) {
      html += `<div class="field"><label>CSR (cole no portal da CA)</label>
        <textarea class="input mono" rows="12" id="r-csr" readonly>${esc(res.csr_pem)}</textarea></div>
        <button class="btn btn-sm" id="r-copy-csr">📋 Copiar CSR</button>`;
    }
    if (res.key_pem) {
      html += `<div class="field mt"><label>⚠️ Chave privada (sem REQ vinculada, não foi salva — guarde agora!)</label>
        <textarea class="input mono" rows="6" id="r-key" readonly>${esc(res.key_pem)}</textarea></div>
        <button class="btn btn-sm" id="r-copy-key">📋 Copiar chave</button>`;
    }
    if (res.inf_content) {
      html += `<div class="field"><label>Arquivo .inf para certreq</label>
        <textarea class="input mono" rows="12" id="r-inf" readonly>${esc(res.inf_content)}</textarea></div>
        <button class="btn btn-sm" id="r-copy-inf">📋 Copiar .inf</button>
        <div class="field mt"><label>Comando (executar no servidor Windows)</label>
        <pre class="code-block">${esc(res.command)}</pre></div>`;
    }
    if (res.output && !res.csr_pem) {
      html += `<div class="field mt"><label>Saída do comando</label>
        <pre class="code-block">${esc(res.output)}</pre></div>`;
    }
    if (res.saved) {
      html += `<div class="muted mt">Arquivos salvos:<br>${Object.entries(res.saved)
        .map(([k, v]) => `<span class="mono">${esc(k)}: ${esc(v)}</span>`).join("<br>")}</div>`;
    }
    $("#c-result").innerHTML = html;
    const bind = (btn, src, label) => { const b = $(btn); if (b) b.onclick = () => copyText($(src).value, label); };
    bind("#r-copy-csr", "#r-csr", "CSR copiada!");
    bind("#r-copy-key", "#r-key", "Chave copiada!");
    bind("#r-copy-inf", "#r-inf", ".inf copiado!");
  }
};

/* ---------------- Certificados ---------------- */
views.certs = async () => {
  main.innerHTML = `
    <div class="view-header"><div>
      <div class="view-title">Certificados</div>
      <div class="view-sub">Importe um arquivo e os dados são lidos automaticamente</div>
    </div>
    <button class="btn btn-primary" id="cert-import">⬆ Importar certificado</button></div>
    <div class="panel">
      <div class="toolbar" style="margin-bottom:12px">
        <input class="input" id="cf-search" placeholder="Buscar CN, SAN, emissor, REQ…" style="min-width:240px">
        <select class="input" id="cf-exp">
          <option value="">Todos</option>
          <option value="0">Vencidos</option>
          <option value="30">Vencem em ≤ 30d</option>
          <option value="60">Vencem em ≤ 60d</option>
          <option value="90">Vencem em ≤ 90d</option>
        </select>
      </div>
      <div id="cert-table"></div>
    </div>`;

  async function load() {
    const params = new URLSearchParams({ search: $("#cf-search").value });
    if ($("#cf-exp").value !== "") params.set("expiring_days", $("#cf-exp").value);
    const rows = await api("/certs?" + params);
    $("#cert-table").innerHTML = rows.length ? `
      <table class="tbl"><thead><tr>
        <th>CN</th><th>REQ</th><th>Validade</th><th></th><th>Chave</th><th>Emissor</th><th></th>
      </tr></thead><tbody>${rows.map(c => `
        <tr>
          <td>${esc(c.cn)}</td>
          <td class="mono">${esc(c.req_number || "—")} ${c.env ? envBadge(c.env) : ""}</td>
          <td>${fmtDate(c.not_before)} → <strong>${fmtDate(c.not_after)}</strong></td>
          <td>${daysBadge(c.days_left)}</td>
          <td class="muted">${esc(c.key_type || "")}</td>
          <td class="muted" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(c.issuer || "")}</td>
          <td style="white-space:nowrap">
            <button class="btn btn-sm" data-detail="${c.id}">Detalhes</button>
            <button class="btn btn-sm btn-danger" data-del="${c.id}">✕</button>
          </td>
        </tr>`).join("")}</tbody></table>`
      : `<div class="empty">Nenhum certificado. Importe o primeiro!</div>`;
    $$("[data-detail]").forEach(el => el.onclick = () =>
      certDetail(rows.find(c => c.id === +el.dataset.detail)));
    $$("[data-del]").forEach(el => el.onclick = async () => {
      if (!confirm("Remover este certificado do registro?")) return;
      await api(`/certs/${el.dataset.del}`, { method: "DELETE" });
      toast("Certificado removido"); load();
    });
  }
  $("#cf-search").oninput = () => { clearTimeout(window._t2); window._t2 = setTimeout(load, 300); };
  $("#cf-exp").onchange = load;
  $("#cert-import").onclick = () => importCertModal(load);
  await load();
};

function certDetail(c) {
  if (!c) return;
  const row = (k, v, mono) => `<tr><th style="width:140px">${k}</th><td class="${mono ? "mono" : ""}">${esc(v || "—")}</td></tr>`;
  modal("Detalhes do certificado", `
    <table class="tbl">
      ${row("CN", c.cn)}${row("SANs", c.sans)}${row("Subject", c.subject, 1)}
      ${row("Emissor", c.issuer, 1)}${row("Serial", c.serial, 1)}
      ${row("Thumbprint SHA1", c.thumbprint_sha1, 1)}
      ${row("Válido de", fmtDateTime(c.not_before))}${row("Válido até", fmtDateTime(c.not_after))}
      ${row("Chave", c.key_type)}${row("Arquivo", c.file_path, 1)}
      ${row("REQ", c.req_number)}
    </table>
    <button class="btn btn-sm mt" id="cd-copy-thumb">📋 Copiar thumbprint</button>
  `, { large: true });
  $("#cd-copy-thumb").onclick = () => copyText(c.thumbprint_sha1 || "", "Thumbprint copiado!");
}

async function importCertModal(onDone) {
  const reqs = await api("/reqs");
  modal("Importar certificado", `
    <div class="field"><label>Arquivo (.cer, .crt, .pem, .der, .pfx, .p12)</label>
      <input class="input" type="file" id="i-file" accept=".cer,.crt,.pem,.der,.pfx,.p12"></div>
    <div class="field"><label>Senha (apenas para PFX/P12)</label>
      <input class="input" type="password" id="i-pwd"></div>
    <div class="field"><label>Vincular à demanda (opcional)</label>
      <select class="input" id="i-req"><option value="">— nenhuma —</option>
        ${reqs.map(r => `<option value="${r.id}">${esc(r.req_number)} · ${esc(r.cn)} (${r.env})</option>`).join("")}
      </select></div>
    <div class="muted">Os campos (CN, SANs, emissor, validade, thumbprint…) serão lidos automaticamente.</div>
  `, { footer: `<button class="btn" data-close>Cancelar</button>
                <button class="btn btn-primary" id="i-go">Importar</button>` });
  $("#i-go").onclick = async () => {
    const file = $("#i-file").files[0];
    if (!file) return toast("Selecione um arquivo", "err");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("password", $("#i-pwd").value);
    if ($("#i-req").value) fd.append("req_id", $("#i-req").value);
    try {
      const cert = await api("/certs/import", { method: "POST", body: fd });
      closeModal();
      toast(`Certificado ${cert.cn} importado · vence ${fmtDate(cert.not_after)}`);
      onDone && onDone();
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
    $("#p-result").innerHTML = res.passwords.map(p => `
      <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
        <span class="mono" style="font-size:15px">${esc(p)}</span>
        <button class="btn btn-sm" data-copy="${esc(p)}">📋</button>
      </div>`).join("");
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
    </div>`;

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

/* ---------------- tema ---------------- */
const themeBtn = $("#theme-toggle");
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  localStorage.setItem("certhub-theme", t);
  themeBtn.textContent = t === "dark" ? "☀️ Tema claro" : "🌙 Tema escuro";
}
themeBtn.onclick = () =>
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
applyTheme(localStorage.getItem("certhub-theme") || "dark");

navigate();
