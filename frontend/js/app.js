/**
 * App principal — gerencia estado, renderização, navegação e eventos.
 */

// ── Estado global ──────────────────────────────────────────────────────────

const State = {
  funcionarios:  [],
  mes:           new Date().getMonth() + 1,  // 1–12
  ano:           new Date().getFullYear(),
  config:        {},
  feriados:      {},          // "YYYY-MM-DD": true
  activePage:    "ponto",     // ponto | dashboard | ocr | config
  activeFuncId:  null,
  registros:     {},          // funcId: [rows]
};

// ── Inicialização ─────────────────────────────────────────────────────────

async function init() {
  try {
    await Promise.all([
      loadFuncionarios(),
      loadConfig(),
      loadFeriados(),
    ]);
    renderAll();
    setupMesAnoControls();
    setupPageNav();
    checkOcrStatus();
  } catch (e) {
    toast("⚠ Erro ao conectar com o servidor. Verifique se o servidor está rodando.", "error");
    console.error(e);
  }
}

async function loadFuncionarios() {
  State.funcionarios = await API.listarFuncionarios();
  if (State.funcionarios.length > 0 && !State.activeFuncId) {
    State.activeFuncId = State.funcionarios[0].id;
  }
}

async function loadConfig() {
  State.config = await API.obterConfig();
}

async function loadFeriados() {
  const list = await API.listarFeriados(State.ano);
  State.feriados = {};
  list.forEach(f => { State.feriados[f.data] = f.nome || true; });
}

// ── Navegação ─────────────────────────────────────────────────────────────

function setupPageNav() {
  document.querySelectorAll("[data-page]").forEach(btn => {
    btn.addEventListener("click", () => showPage(btn.dataset.page));
  });
}

function showPage(page) {
  State.activePage = page;
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  document.querySelectorAll("[data-page]").forEach(b => b.classList.remove("active"));
  const pg = document.getElementById(`page-${page}`);
  if (pg) pg.classList.add("active");
  document.querySelectorAll(`[data-page="${page}"]`).forEach(b => b.classList.add("active"));

  if (page === "dashboard") renderDashboard();
  if (page === "ocr")       renderOcrPage();
  if (page === "ia")        renderIAPage();
  if (page === "config") {
    renderConfigPage();
    if (typeof renderFeriadosList === "function") renderFeriadosList();
    renderIAConfig();
  }
}

// ── ASSISTENTE IA (Ollama) ──────────────────────────────────────────────────
async function renderIAConfig() {
  try {
    const c = await API.iaConfig();
    const bu = document.getElementById("iaBaseUrl");
    const md = document.getElementById("iaModel");
    const info = document.getElementById("iaKeyInfo");
    const badge = document.getElementById("iaStatusBadge");
    if (bu) bu.value = c.base_url || "https://ollama.com/v1";
    if (md) md.value = c.model || "";
    const kf = document.getElementById("iaApiKey");
    if (kf) {
      kf.value = "";  // nunca repopula a chave (segurança)
      kf.placeholder = c.has_key
        ? `✓ Chave salva (${c.key_mask}) — deixe em branco para manter`
        : "cole a chave aqui (fica salva localmente)";
    }
    if (info) info.innerHTML = c.has_key
      ? `<span style="color:var(--green);">✓ Chave salva (${c.key_mask}). Modelo: <b>${c.model||"—"}</b></span>`
      : "Nenhuma chave salva ainda.";
    if (badge) {
      const ok = c.has_key && c.model;
      badge.className = `engine-pill ${ok ? "ok" : "off"}`;
      badge.textContent = ok ? "Configurado ✓" : "Não configurado";
    }
  } catch (_) {}
}

async function iaSalvar() {
  const c = {
    base_url: document.getElementById("iaBaseUrl")?.value || "https://ollama.com/v1",
    api_key:  document.getElementById("iaApiKey")?.value || "",
    model:    document.getElementById("iaModel")?.value || "",
  };
  try {
    await API.iaSalvarConfig(c);
    const k = document.getElementById("iaApiKey"); if (k) k.value = "";  // limpa o campo
    toast("✓ Configuração da IA salva!", "success");
    renderIAConfig();
  } catch (e) { toast("⚠ " + e.message, "error"); }
}

async function iaCarregarModelos() {
  try {
    // salva primeiro (caso a key tenha sido digitada agora)
    const k = document.getElementById("iaApiKey")?.value;
    if (k) await API.iaSalvarConfig({
      base_url: document.getElementById("iaBaseUrl")?.value || "https://ollama.com/v1",
      api_key: k, model: document.getElementById("iaModel")?.value || "",
    });
    const r = await API.iaModelos();
    const dl = document.getElementById("iaModelList");
    if (dl) dl.innerHTML = (r.modelos || []).map(m => `<option value="${m}">`).join("");
    toast(`✓ ${r.modelos.length} modelo(s) disponível(is)`, "success");
  } catch (e) { toast("⚠ " + e.message, "error"); }
}

async function iaTestar() {
  const res = document.getElementById("iaTesteResultado");
  if (res) res.innerHTML = `<span class="spinner" style="width:14px;height:14px;"></span> Testando...`;
  try {
    // garante que salvou antes de testar
    await iaSalvarSilencioso();
    const r = await API.iaTestar();
    if (res) res.innerHTML = `<span style="color:var(--green);">✓ Conexão OK — resposta: "${r.resposta}"</span>`;
  } catch (e) {
    if (res) res.innerHTML = `<span style="color:var(--red);">✗ ${e.message}</span>`;
  }
}

async function iaSalvarSilencioso() {
  const k = document.getElementById("iaApiKey")?.value;
  const c = {
    base_url: document.getElementById("iaBaseUrl")?.value || "https://ollama.com/v1",
    model:    document.getElementById("iaModel")?.value || "",
  };
  if (k) c.api_key = k;
  await API.iaSalvarConfig(c);
}

async function renderIAPage() {
  const lbl = document.getElementById("iaAnoLabel");
  if (lbl) lbl.textContent = State.ano;
  try {
    const c = await API.iaConfig();
    const badge = document.getElementById("iaPageStatus");
    const ok = c.has_key && c.model;
    if (badge) {
      badge.className = `engine-pill ${ok ? "ok" : "off"}`;
      badge.textContent = ok ? `Pronto (${c.model})` : "Configure em ⚙ Configurações";
    }
  } catch (_) {}
}

function iaSugestao(btn) {
  const inp = document.getElementById("iaPergunta");
  if (inp) { inp.value = btn.textContent; iaPerguntar(); }
}

async function iaPerguntar() {
  const inp = document.getElementById("iaPergunta");
  const pergunta = inp?.value?.trim();
  if (!pergunta) return;
  const out = document.getElementById("iaResposta");
  const btn = document.getElementById("iaBtnPerguntar");
  if (btn) { btn.disabled = true; btn.textContent = "Pensando..."; }
  if (out) out.innerHTML = `<span class="spinner" style="width:18px;height:18px;"></span> Consultando a IA...`;
  try {
    const r = await API.iaPerguntar(pergunta, State.ano);
    if (out) out.textContent = r.resposta;
  } catch (e) {
    if (out) out.innerHTML = `<span style="color:var(--red);">⚠ ${e.message}</span>`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "Perguntar"; }
  }
}

// ── Controles mês/ano ─────────────────────────────────────────────────────

function setupMesAnoControls() {
  const selMes = document.getElementById("selMes");
  const inpAno = document.getElementById("inpAno");
  if (selMes) {
    MESES_NOMES.forEach((n, i) => {
      const o = document.createElement("option");
      o.value = i + 1;
      o.textContent = n;
      if (i + 1 === State.mes) o.selected = true;
      selMes.appendChild(o);
    });
    selMes.addEventListener("change", async () => {
      State.mes = parseInt(selMes.value);
      await loadFeriados();
      renderAll();
    });
  }
  if (inpAno) {
    inpAno.value = State.ano;
    inpAno.addEventListener("change", async () => {
      State.ano = parseInt(inpAno.value) || new Date().getFullYear();
      await loadFeriados();
      renderAll();
    });
  }
}

// ── Render principal ──────────────────────────────────────────────────────

function renderAll() {
  renderSidebar();
  renderPontoPage();
  // Funções definidas no HTML inline — chamadas sem override
  if (typeof updateTitle      === "function") updateTitle();
  if (typeof populateOcrSelect === "function") populateOcrSelect();
}

// ── SIDEBAR ───────────────────────────────────────────────────────────────

function renderSidebar() {
  const list = document.getElementById("sidebarFuncList");
  if (!list) return;
  list.innerHTML = State.funcionarios.map(f => `
    <button class="func-item ${f.id === State.activeFuncId ? "active" : ""}"
            onclick="selectFunc(${f.id})">
      <div class="func-avatar-sm">${initials(f.nome)}</div>
      <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${f.nome}</span>
    </button>
  `).join("") || `<div style="padding:8px 16px;font-size:11px;color:var(--text-muted);">Nenhum funcionário</div>`;
}

function selectFunc(id) {
  State.activeFuncId = id;
  renderSidebar();
  renderPontoPage();
}

// ── PÁGINA PONTO ──────────────────────────────────────────────────────────

async function renderPontoPage() {
  const container = document.getElementById("pontoContainer");
  if (!container) return;

  if (!State.funcionarios.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="es-icon">👤</div>
        <div class="es-text">Nenhum funcionário cadastrado.<br>Clique em <b>+ Funcionário</b> para começar.</div>
      </div>`;
    return;
  }

  // Renderiza só o funcionário ativo
  const func = State.funcionarios.find(f => f.id === State.activeFuncId)
            || State.funcionarios[0];
  State.activeFuncId = func.id;

  // Carrega registros
  let rows = [];
  try {
    rows = await API.listarMes(func.id, State.ano, State.mes);
    State.registros[func.id] = rows;
  } catch (e) {
    console.error(e);
  }

  container.innerHTML = buildFuncCard(func, rows);
  attachPontoEvents(func, rows);
}

// ── CARD FUNCIONÁRIO ──────────────────────────────────────────────────────

function buildFuncCard(func, rows) {
  // Totais
  let sumH = 0, sumN = 0, sumE = 0, sumNot = 0, diasTrab = 0;
  rows.forEach(r => {
    if (r.total_min !== null && r.total_min !== undefined) {
      sumH    += r.total_min    || 0;
      sumN    += r.previsto_min || 0;
      sumE    += r.saldo_min    || 0;
      sumNot  += r.noturno_min  || 0;
      diasTrab++;
    }
  });
  const saldoCls = sumE > 0 ? "green" : sumE < 0 ? "red" : "white";
  const badgeCls = sumE > 0 ? "badge-green" : sumE < 0 ? "badge-red" : "badge-gray";

  const metricsHtml = `
    <div class="metrics-grid" style="padding:12px 16px 0;">
      <div class="metric-card">
        <div class="metric-label">Total de Horas</div>
        <div class="metric-value white">${minutesToStr(sumH)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Add. Noturno</div>
        <div class="metric-value blue">${minutesToStr(sumNot) || "—"}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Horas Previstas</div>
        <div class="metric-value white">${minutesToStr(sumN)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Saldo do Mês</div>
        <div class="metric-value ${saldoCls}">${sumE >= 0 ? "+" : ""}${minutesToStr(sumE)}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Dias Trabalhados</div>
        <div class="metric-value white">${diasTrab}</div>
      </div>
    </div>`;

  const tabelaHtml = buildTabelaPonto(func, rows);

  const legendaHtml = `
    <div class="legenda" style="padding:8px 16px;">
      <span class="leg-item"><span class="leg-dot" style="background:#0A2010;border:1px solid var(--green-dim);"></span>Saldo positivo</span>
      <span class="leg-item"><span class="leg-dot" style="background:#1A0808;border:1px solid #3d1b1b;"></span>Saldo negativo</span>
      <span class="leg-item"><span class="leg-dot" style="background:var(--yellow-bg);border:1px solid #5a3e00;"></span>Feriado</span>
      <span class="leg-item"><span class="leg-dot" style="background:var(--border-light);border:1px solid var(--border);"></span>Entrada atrasada</span>
    </div>`;

  return `
  <div class="func-card" id="fcard-${func.id}">
    <div class="func-card-header">
      <div class="func-card-left">
        <div class="func-avatar">${initials(func.nome)}</div>
        <div>
          <div class="func-name">${func.nome}</div>
          <div class="func-summary">${diasTrab} dia(s) · Total: ${minutesToStr(sumH)} · Noturno: ${minutesToStr(sumNot)}</div>
        </div>
      </div>
      <div class="func-card-right">
        <span class="badge ${badgeCls}">Saldo: ${sumE >= 0 ? "+" : ""}${minutesToStr(sumE)}</span>
        <div class="dd-wrap" id="dd-func-${func.id}">
          <button class="btn btn-sm" onclick="event.stopPropagation();toggleDD('dd-func-${func.id}')">⚙ Ações ▾</button>
          <div class="dd-menu">
            <button class="dd-item" onclick="closeAllDD();API.downloadExcel(${func.id},${State.ano},${State.mes})">⬇ Exportar Excel</button>
            <button class="dd-item" onclick="closeAllDD();API.downloadCsv(${func.id},${State.ano},${State.mes})">📄 Exportar CSV</button>
            <button class="dd-item" onclick="closeAllDD();API.downloadJson(${func.id},${State.ano},${State.mes})">{ } Exportar JSON</button>
            <div class="dd-divider"></div>
            <button class="dd-item" onclick="closeAllDD();relatorioMensal(${func.id})">🖨 Relatório Mensal</button>
            <button class="dd-item" onclick="closeAllDD();relatorioAnual([${func.id}])">📊 Relatório Anual</button>
            <div class="dd-divider"></div>
            <button class="dd-item" onclick="closeAllDD();limparMes(${func.id})">↺ Limpar Mês</button>
            <div class="dd-divider"></div>
            <button class="dd-item danger" onclick="closeAllDD();removerFunc(${func.id})">🗑 Remover Funcionário</button>
          </div>
        </div>
      </div>
    </div>
    ${metricsHtml}
    <div class="table-wrap" style="padding:0 0 0;">
      ${tabelaHtml}
    </div>
    ${legendaHtml}
  </div>`;
}

// ── TABELA PONTO ──────────────────────────────────────────────────────────

function buildTabelaPonto(func, rows) {
  const totalDias = diasNoMes(State.ano, State.mes);

  let rowsHtml = "";
  for (let d = 1; d <= totalDias; d++) {
    const dataStr = `${State.ano}-${String(State.mes).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
    const row = rows.find(r => r.data === dataStr) || { data: dataStr };
    const dw = diaSemana(dataStr);  // 0=dom, 6=sáb
    const isFer = !!State.feriados[dataStr];
    const isFds = dw === 0 || dw === 6;

    const totalMin   = row.total_min;
    const saldoMin   = row.saldo_min;
    const noturnoMin = row.noturno_min;
    const prevMin    = row.previsto_min;

    let trCls = "";
    if (isFer && totalMin !== null) trCls = "row-fer";
    else if (saldoMin !== null && saldoMin > 0) trCls = "row-ot";
    else if (saldoMin !== null && saldoMin < 0) trCls = "row-neg";
    else if (isFds)  trCls = "row-fds";

    const diaLabel = DS_NOMES[dw];
    const diaCls   = `dia-cell ${isFer ? "feriado-dia" : ""} ${isFds ? "fds-dia" : ""}`;

    // Confiança OCR
    const confE  = row.conf_entrada  ?? 1;
    const confS  = row.conf_saida    ?? 1;
    const confII = row.conf_ini_int  ?? 1;
    const confFI = row.conf_fim_int  ?? 1;
    const CONF   = parseFloat(State.config.conf_minima ?? 0.65);

    const inCls  = row.entrada         ? (confE  < CONF ? "low-conf" : "filled") : "";
    const iiCls  = row.inicio_intervalo ? (confII < CONF ? "low-conf" : "filled") : "";
    const fiCls  = row.fim_intervalo    ? (confFI < CONF ? "low-conf" : "filled") : "";
    const saCls  = row.saida           ? (confS  < CONF ? "low-conf" : "filled") : "";

    const saldoStr = saldoMin !== null
      ? `<span style="color:${saldoMin>0?"var(--green)":saldoMin<0?"var(--red)":"var(--text-muted)"}">${saldoMin>=0?"+":""}${minutesToStr(saldoMin)}</span>`
      : `<span class="muted">—</span>`;

    rowsHtml += `
    <tr class="${trCls}" id="tr-${func.id}-${d}">
      <td class="${diaCls}">
        <div class="day-num">${d}<button class="fbtn ${isFer?"on":""}" title="${isFer?"Remover feriado":"Marcar feriado"}"
          onclick="toggleFeriado('${dataStr}')">F</button></div>
        <div class="day-label">${diaLabel}${isFer?"<br><span style='color:var(--yellow);font-size:8px;'>Fer.</span>":""}</div>
      </td>
      <td><input class="t-input ${inCls}" id="t-${func.id}-${d}-entrada"
            value="${row.entrada||""}" placeholder="--:--"
            onblur="saveField(${func.id},'${dataStr}','entrada',this.value)"
            onkeydown="navNext(event,${func.id},${d},'entrada')" /></td>
      <td><input class="t-input ${iiCls}" id="t-${func.id}-${d}-inicioInt"
            value="${row.inicio_intervalo||""}" placeholder="--:--"
            onblur="saveField(${func.id},'${dataStr}','inicio_intervalo',this.value)"
            onkeydown="navNext(event,${func.id},${d},'inicioInt')"
            ${isFer?"style='opacity:.35;pointer-events:none;'":""} /></td>
      <td><input class="t-input ${fiCls}" id="t-${func.id}-${d}-fimInt"
            value="${row.fim_intervalo||""}" placeholder="--:--"
            onblur="saveField(${func.id},'${dataStr}','fim_intervalo',this.value)"
            onkeydown="navNext(event,${func.id},${d},'fimInt')"
            ${isFer?"style='opacity:.35;pointer-events:none;'":""} /></td>
      <td><input class="t-input ${saCls}" id="t-${func.id}-${d}-saida"
            value="${row.saida||""}" placeholder="--:--"
            onblur="saveField(${func.id},'${dataStr}','saida',this.value)"
            onkeydown="navNext(event,${func.id},${d},'saida')" /></td>
      <td class="calc-cell ${totalMin!==null?"white":"muted"}">${minutesToStr(totalMin)}</td>
      <td class="calc-cell ${noturnoMin?"info":"muted"}">${minutesToStr(noturnoMin)}</td>
      <td class="calc-cell ${prevMin?"":"muted"}">${prevMin?minutesToStr(prevMin):"—"}</td>
      <td class="calc-cell">${saldoStr}</td>
    </tr>`;
  }

  return `
  <table class="ponto" id="tabela-${func.id}">
    <thead>
      <tr>
        <th>DIA</th>
        <th>ENTRADA</th>
        <th>INÍCIO INTERVALO</th>
        <th>FIM INTERVALO</th>
        <th>SAÍDA</th>
        <th>TOTAL</th>
        <th>ADD. NOTURNO</th>
        <th>PREVISTO</th>
        <th>SALDO</th>
      </tr>
    </thead>
    <tbody>${rowsHtml}</tbody>
  </table>`;
}

// ── EVENTOS TABELA ────────────────────────────────────────────────────────

function attachPontoEvents(func, rows) {
  // Máscara automática em todos os inputs de hora
  document.querySelectorAll(".t-input").forEach(inp => applyTimeMask(inp));
}

// ── SALVAR CAMPO ──────────────────────────────────────────────────────────

async function saveField(funcId, dataStr, campo, value) {
  const func   = State.funcionarios.find(f => f.id === funcId);
  const cached = (State.registros[funcId] || []).find(r => r.data === dataStr) || {};

  const payload = {
    funcionario_id:   funcId,
    data:             dataStr,
    entrada:          cached.entrada          || null,
    inicio_intervalo: cached.inicio_intervalo || null,
    fim_intervalo:    cached.fim_intervalo     || null,
    saida:            cached.saida            || null,
    feriado:          !!State.feriados[dataStr] ? 1 : 0,
    fonte:            "manual",
  };

  payload[campo] = value || null;

  // Auto-preenche intervalo na primeira digitação (se não for feriado)
  if (!State.feriados[dataStr] && func) {
    const jornada = (func.jornada || "07:00-17:00").split("-");
    if (!payload.inicio_intervalo && (campo === "entrada" || campo === "saida")) {
      payload.inicio_intervalo = func.int_inicio || "12:00";
    }
    if (!payload.fim_intervalo && (campo === "entrada" || campo === "saida")) {
      payload.fim_intervalo = func.int_fim || "13:00";
    }
  }

  try {
    const saved = await API.salvarRegistro(payload);
    // Atualiza cache
    const idx = (State.registros[funcId] || []).findIndex(r => r.data === dataStr);
    if (idx >= 0) State.registros[funcId][idx] = saved;
    else {
      if (!State.registros[funcId]) State.registros[funcId] = [];
      State.registros[funcId].push(saved);
    }
    // Atualiza células calc sem re-render completo
    updateCalcCells(funcId, dataStr, saved);
    updateCardHeader(funcId);
  } catch (e) {
    console.error("Erro ao salvar:", e);
    toast("⚠ Erro ao salvar: " + e.message, "error");
  }
}

function updateCalcCells(funcId, dataStr, saved) {
  const d = parseInt(dataStr.split("-")[2]);
  const row = document.querySelector(`#tr-${funcId}-${d}`);
  if (!row) return;

  const cells = row.querySelectorAll(".calc-cell");
  if (cells.length < 4) return;

  const [totalCell, notCell, prevCell, saldoCell] = cells;
  const saldo = saved.saldo_min;
  const noturno = saved.noturno_min;
  const prev = saved.previsto_min;
  const total = saved.total_min;

  totalCell.textContent = minutesToStr(total);
  totalCell.className   = `calc-cell ${total !== null ? "white" : "muted"}`;

  notCell.textContent = minutesToStr(noturno);
  notCell.className   = `calc-cell ${noturno ? "info" : "muted"}`;

  prevCell.textContent = prev ? minutesToStr(prev) : "—";
  prevCell.className   = `calc-cell ${prev ? "" : "muted"}`;

  saldoCell.innerHTML = saldo !== null
    ? `<span style="color:${saldo>0?"var(--green)":saldo<0?"var(--red)":"var(--text-muted)"}">${saldo>=0?"+":""}${minutesToStr(saldo)}</span>`
    : `<span class="muted">—</span>`;

  // Linha colorida
  row.className = saldo !== null && saldo > 0 ? "row-ot"
    : saldo !== null && saldo < 0 ? "row-neg"
    : State.feriados[dataStr] ? "row-fer"
    : "";
}

function updateCardHeader(funcId) {
  const regs = State.registros[funcId] || [];
  let sumH = 0, sumN = 0, sumE = 0, sumNot = 0, dias = 0;
  regs.forEach(r => {
    if (r.total_min !== null && r.total_min !== undefined) {
      sumH += r.total_min || 0;
      sumN += r.previsto_min || 0;
      sumE += r.saldo_min || 0;
      sumNot += r.noturno_min || 0;
      dias++;
    }
  });

  const func = State.funcionarios.find(f => f.id === funcId);
  const summaryEl = document.querySelector(`#fcard-${funcId} .func-summary`);
  if (summaryEl) summaryEl.textContent = `${dias} dia(s) · Total: ${minutesToStr(sumH)} · Noturno: ${minutesToStr(sumNot)}`;

  const badgeEl = document.querySelector(`#fcard-${funcId} .badge`);
  if (badgeEl) {
    badgeEl.textContent = `Saldo: ${sumE >= 0 ? "+" : ""}${minutesToStr(sumE)}`;
    badgeEl.className = `badge ${sumE > 0 ? "badge-green" : sumE < 0 ? "badge-red" : "badge-gray"}`;
  }

  // Atualiza métricas
  const mCards = document.querySelectorAll(`#fcard-${funcId} .metric-value`);
  if (mCards.length >= 5) {
    mCards[0].textContent = minutesToStr(sumH);
    mCards[1].textContent = sumNot ? minutesToStr(sumNot) : "—";
    mCards[2].textContent = minutesToStr(sumN);
    mCards[3].textContent = `${sumE >= 0 ? "+" : ""}${minutesToStr(sumE)}`;
    mCards[3].className = `metric-value ${sumE > 0 ? "green" : sumE < 0 ? "red" : "white"}`;
    mCards[4].textContent = String(dias);
  }
}

// ── NAVEGAÇÃO ENTRE CAMPOS ────────────────────────────────────────────────

function navNext(event, funcId, dia, campo) {
  if (event.key !== "Enter" && event.key !== "Tab") return;
  if (event.key === "Tab") return;  // deixa tab nativo
  event.preventDefault();

  const totalDias = diasNoMes(State.ano, State.mes);
  const isFer = !!State.feriados[
    `${State.ano}-${String(State.mes).padStart(2,"0")}-${String(dia).padStart(2,"0")}`
  ];

  let nextId = null;
  if (campo === "entrada") {
    nextId = isFer ? `t-${funcId}-${dia}-saida` : `t-${funcId}-${dia}-inicioInt`;
  } else if (campo === "inicioInt") {
    nextId = `t-${funcId}-${dia}-fimInt`;
  } else if (campo === "fimInt") {
    nextId = `t-${funcId}-${dia}-saida`;
  } else if (campo === "saida") {
    // Avança para próximo dia útil
    let next = dia + 1;
    while (next <= totalDias) {
      const dw = diaSemana(`${State.ano}-${String(State.mes).padStart(2,"0")}-${String(next).padStart(2,"0")}`);
      if (dw !== 0) break;  // pula domingos
      next++;
    }
    if (next <= totalDias) nextId = `t-${funcId}-${next}-entrada`;
  }

  if (nextId) {
    const el = document.getElementById(nextId);
    if (el) { el.focus(); el.select(); }
  }
}

// ── FERIADO ───────────────────────────────────────────────────────────────

async function toggleFeriado(dataStr) {
  try {
    if (State.feriados[dataStr]) {
      await API.removerFeriado(dataStr);
      delete State.feriados[dataStr];
      toast("Feriado removido");
    } else {
      await API.criarFeriado(dataStr, null);
      State.feriados[dataStr] = true;
      toast("Dia marcado como feriado");
    }
    // Re-carrega e re-renderiza
    const rows = await API.listarMes(State.activeFuncId, State.ano, State.mes);
    State.registros[State.activeFuncId] = rows;
    await renderPontoPage();
  } catch (e) {
    toast("⚠ " + e.message, "error");
  }
}

// ── ADICIONAR FUNCIONÁRIO ─────────────────────────────────────────────────

async function adicionarFuncionario() {
  const nome = document.getElementById("inputNomeFunc")?.value?.trim();
  if (!nome) { toast("Informe o nome do funcionário", "error"); return; }
  try {
    const f = await API.criarFuncionario({ nome });
    State.funcionarios.push(f);
    State.activeFuncId = f.id;
    document.getElementById("inputNomeFunc").value = "";
    document.getElementById("modalAddFunc").classList.add("hidden");
    renderAll();
    toast(`✓ ${f.nome} adicionado!`, "success");
  } catch (e) {
    toast("⚠ " + e.message, "error");
  }
}

// ── REMOVER FUNCIONÁRIO ───────────────────────────────────────────────────

async function removerFunc(id) {
  const f = State.funcionarios.find(f => f.id === id);
  if (!f || !confirm(`Remover "${f.nome}" permanentemente?`)) return;
  try {
    await API.removerFuncionario(id);
    State.funcionarios = State.funcionarios.filter(f => f.id !== id);
    if (State.activeFuncId === id) {
      State.activeFuncId = State.funcionarios[0]?.id || null;
    }
    renderAll();
    toast("Funcionário removido");
  } catch (e) {
    toast("⚠ " + e.message, "error");
  }
}

// ── LIMPAR MÊS ────────────────────────────────────────────────────────────

async function limparMes(funcId) {
  const f = State.funcionarios.find(f => f.id === funcId);
  if (!f) return;
  const nomeMes = MESES_NOMES[State.mes - 1];
  if (!confirm(`Limpar todos os horários de "${f.nome}" em ${nomeMes}/${State.ano}?`)) return;
  try {
    await API.limparMes(funcId, State.ano, State.mes);
    State.registros[funcId] = [];
    await renderPontoPage();
    toast(`↺ ${nomeMes}/${State.ano} de ${f.nome} limpo!`);
  } catch (e) {
    toast("⚠ " + e.message, "error");
  }
}

// ── DASHBOARD ─────────────────────────────────────────────────────────────

async function renderDashboard() {
  const container = document.getElementById("dashContainer");
  if (!container) return;
  container.innerHTML = `<div style="display:flex;align-items:center;gap:8px;padding:20px;color:var(--text-muted);"><div class="spinner"></div> Carregando...</div>`;

  try {
    const data = await API.dashboard(State.ano, State.mes);

    const totalFuncs   = data.length;
    const totalHoras   = data.reduce((a, r) => a + (r.total_h || 0), 0);
    const totalSaldo   = data.reduce((a, r) => a + (r.saldo || 0), 0);
    const totalDias    = data.reduce((a, r) => a + (r.dias_trabalhados || 0), 0);

    const dashCards = `
    <div class="dash-grid">
      <div class="dash-card">
        <div class="dash-icon">👥</div>
        <div class="dash-info">
          <div class="d-label">Funcionários Ativos</div>
          <div class="d-val" style="color:var(--blue)">${totalFuncs}</div>
        </div>
      </div>
      <div class="dash-card">
        <div class="dash-icon">⏱</div>
        <div class="dash-info">
          <div class="d-label">Total Horas (equipe)</div>
          <div class="d-val">${minutesToStr(totalHoras)}</div>
        </div>
      </div>
      <div class="dash-card">
        <div class="dash-icon">📊</div>
        <div class="dash-info">
          <div class="d-label">Saldo Total (equipe)</div>
          <div class="d-val" style="color:${totalSaldo>=0?"var(--green)":"var(--red)"}">${totalSaldo>=0?"+":""}${minutesToStr(totalSaldo)}</div>
        </div>
      </div>
      <div class="dash-card">
        <div class="dash-icon">📅</div>
        <div class="dash-info">
          <div class="d-label">Total Dias Trabalhados</div>
          <div class="d-val">${totalDias}</div>
        </div>
      </div>
    </div>`;

    const tableRows = data.map(r => {
      const saldo = r.saldo || 0;
      const cls = saldo > 0 ? "green" : saldo < 0 ? "red" : "";
      const progressPct = r.previsto ? Math.min(100, Math.round((r.total_h / r.previsto) * 100)) : 0;
      return `
      <tr>
        <td>
          <div style="display:flex;align-items:center;gap:8px;">
            <div class="func-avatar-sm">${initials(r.nome)}</div>
            <span style="font-weight:500;">${r.nome}</span>
          </div>
        </td>
        <td style="text-align:center;">${r.dias_trabalhados || 0}</td>
        <td style="text-align:center;font-family:var(--font-mono);">${minutesToStr(r.total_h)}</td>
        <td style="text-align:center;font-family:var(--font-mono);">${minutesToStr(r.previsto)}</td>
        <td style="text-align:center;">
          <div style="min-width:80px;">
            <div class="progress-bar"><div class="progress-fill ${cls}" style="width:${progressPct}%"></div></div>
            <div style="font-size:10px;color:var(--text-muted);margin-top:2px;">${progressPct}%</div>
          </div>
        </td>
        <td style="text-align:center;font-family:var(--font-mono);font-weight:600;color:${saldo>0?"var(--green)":saldo<0?"var(--red)":"var(--text-secondary)"};">
          ${saldo>=0?"+":""}${minutesToStr(saldo)}
        </td>
        <td style="text-align:center;font-family:var(--font-mono);color:var(--blue);">${minutesToStr(r.noturno)}</td>
        <td style="text-align:center;">
          <button class="btn btn-sm btn-ghost" onclick="API.downloadExcel(${r.id},${State.ano},${State.mes})">⬇ Excel</button>
        </td>
      </tr>`;
    }).join("");

    container.innerHTML = `
    ${dashCards}
    <div class="card">
      <div class="card-header">
        <div class="card-header-left">
          <span class="card-title">📋 Resumo — ${MESES_NOMES[State.mes-1]} ${State.ano}</span>
        </div>
        <div class="card-header-right">
          <button class="btn btn-sm btn-success" onclick="API.downloadExcelTodos(${State.ano},${State.mes})">⬇ Excel Geral</button>
        </div>
      </div>
      <div style="overflow-x:auto;">
        <table class="dash-table">
          <thead>
            <tr>
              <th>Funcionário</th>
              <th>Dias</th>
              <th>Total H.</th>
              <th>Previsto</th>
              <th>Progresso</th>
              <th>Saldo</th>
              <th>Noturno</th>
              <th></th>
            </tr>
          </thead>
          <tbody>${tableRows || `<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:20px;">Nenhum registro no período</td></tr>`}</tbody>
        </table>
      </div>
    </div>`;
  } catch (e) {
    container.innerHTML = `<div class="empty-state"><div class="es-icon">⚠</div><div class="es-text">${e.message}</div></div>`;
  }
}

// ── OCR ───────────────────────────────────────────────────────────────────

async function checkOcrStatus() {
  try {
    const status = await API.statusOcr();
    const badge = document.getElementById("ocrStatusBadge");
    if (!badge) return;
    badge.className = `engine-pill ${status.ready ? "ok" : "off"}`;
    badge.textContent = status.ready
      ? `OCR: ${status.engine_name || "Pronto"}`
      : "OCR: Não configurado";
    badge.title = Object.entries(status.engines)
      .map(([k,v]) => `${k}: ${v}`).join("\n");
  } catch (_) {}
}

async function renderOcrPage() {
  const statusArea = document.getElementById("ocrEngineStatus");
  if (!statusArea) return;
  try {
    const status = await API.statusOcr();
    // Mostra apenas engines presentes (PaddleOCR só aparece se instalado)
    const pills = Object.entries(status.engines).map(([k, v]) => {
      const ok = v && v !== false;
      const label = ok && typeof v === "string" && v.length > 1
        ? `${k} ${v}` : k;
      return `<span class="engine-pill ${ok ? "ok" : "off"}" title="${v}">${label}: ${ok ? "✓" : "✗"}</span>`;
    }).join(" ");
    statusArea.innerHTML = pills || `<span class="engine-pill off">Nenhum engine OCR encontrado</span>`;
  } catch (_) {}

  // Popula func select
  const sel = document.getElementById("ocrFuncSelect");
  if (sel && State.funcionarios?.length) {
    sel.innerHTML = `<option value="">\u2014 Selecione o funcionário \u2014</option>` +
      State.funcionarios.map(f =>
        `<option value="${f.id}" ${f.id === State.activeFuncId ? "selected" : ""}>${f.nome}</option>`
      ).join("");
  }

  // Gera o cartão em branco de exemplo
  buildBcpRows();
}

// ── Cartão em branco de exemplo ─────────────────────────────────────────────

function buildBcpRows() {
  const cont = document.getElementById("bcpRows");
  if (!cont) return;

  // Exemplos de horários realistas (com variações naturais)
  const exemplosDias = [
    { dia: 1,  ent: "07:02", sai1: "11:28", ent2: "13:04", sai2: "17:33" },
    { dia: 2,  ent: "06:58", sai1: "11:30", ent2: "13:02", sai2: "17:35" },
    { dia: 3,  ent: "",      sai1: "",       ent2: "",       sai2: ""      }, // vazio
    { dia: 4,  ent: "",      sai1: "",       ent2: "",       sai2: ""      }, // vazio
    { dia: 5,  ent: "07:00", sai1: "11:31", ent2: "13:00", sai2: "17:30" },
  ];

  cont.innerHTML = exemplosDias.map(d => `
    <div class="bcp-row">
      <div class="bcp-col bcp-dia-c">${d.dia}</div>
      <div class="bcp-col bcp-time-c ${d.ent ? "bcp-filled" : ""}">${d.ent || ""}</div>
      <div class="bcp-col bcp-time-c ${d.sai1 ? "bcp-filled" : ""}">${d.sai1 || ""}</div>
      <div class="bcp-col bcp-time-c ${d.ent2 ? "bcp-filled" : ""}">${d.ent2 || ""}</div>
      <div class="bcp-col bcp-time-c ${d.sai2 ? "bcp-filled" : ""}">${d.sai2 || ""}</div>
      <div class="bcp-col bcp-time-c bcp-extra-col"></div>
      <div class="bcp-col bcp-time-c bcp-extra-col"></div>
      <div class="bcp-col bcp-extra-c"></div>
    </div>
  `).join("") + `
    <div class="bcp-row bcp-hint-row">
      <div class="bcp-col bcp-dia-c" style="color:var(--text-muted);font-size:9px;">6…</div>
      <div class="bcp-col bcp-time-c" style="font-size:9px;color:var(--text-muted);letter-spacing:0;">HH:MM</div>
      <div class="bcp-col bcp-time-c" style="font-size:9px;color:var(--text-muted);letter-spacing:0;">HH:MM</div>
      <div class="bcp-col bcp-time-c" style="font-size:9px;color:var(--text-muted);letter-spacing:0;">HH:MM</div>
      <div class="bcp-col bcp-time-c" style="font-size:9px;color:var(--text-muted);letter-spacing:0;">HH:MM</div>
      <div class="bcp-col bcp-time-c bcp-extra-col" style="font-size:9px;color:var(--text-muted);">HE</div>
      <div class="bcp-col bcp-time-c bcp-extra-col" style="font-size:9px;color:var(--text-muted);">HE</div>
      <div class="bcp-col bcp-extra-c"></div>
    </div>`;
}

function toggleCardExample() {
  const body = document.getElementById("ocrExampleBody");
  const btn  = document.getElementById("btnToggleExample");
  if (!body) return;
  const hidden = body.style.display === "none";
  body.style.display = hidden ? "" : "none";
  if (btn) btn.textContent = hidden ? "▲ Ocultar" : "▼ Mostrar";
}

// ── Dropzone helpers ─────────────────────────────────────────────────────────

function handleDrop(event, inputId, labelId) {
  const inp = document.getElementById(inputId);
  if (inp && event.dataTransfer.files.length) {
    inp.files = event.dataTransfer.files;
    updateDropzoneLabel(inputId, labelId);
  }
}

function updateDropzoneLabel(inputId, labelId) {
  const inp = document.getElementById(inputId);
  const lbl = document.getElementById(labelId);
  if (!inp || !lbl) return;
  if (inp.files && inp.files.length) {
    const f = inp.files[0];
    const sizeKb = Math.round(f.size / 1024);
    lbl.innerHTML = `📎 <strong>${f.name}</strong><br><small>${sizeKb} KB</small>`;
  }
}

function limparOcr() {
  ["ocrFileInput", "ocrFileInput2"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  updateDropzoneLabel("ocrFileInput",  "dropzoneLabel");
  updateDropzoneLabel("ocrFileInput2", "dropzoneLabel2");
  // Reset label texts
  const l1 = document.getElementById("dropzoneLabel");
  const l2 = document.getElementById("dropzoneLabel2");
  if (l1) l1.innerHTML = "Arraste ou clique<br><small>Face 1 · dias 1–15</small>";
  if (l2) l2.innerHTML = "Arraste ou clique<br><small>Face 2 · dias 16–31</small>";

  const res = document.getElementById("ocrResult");
  if (res) res.innerHTML = "";
}

// ── Processar OCR ────────────────────────────────────────────────────────────

async function processarOcr() {
  const fileInput  = document.getElementById("ocrFileInput");
  const fileInput2 = document.getElementById("ocrFileInput2");
  const funcSel    = document.getElementById("ocrFuncSelect");
  const resultDiv  = document.getElementById("ocrResult");

  if (!fileInput?.files?.length) {
    toast("Selecione pelo menos a Face 1 do cartão ponto", "error");
    return;
  }

  const funcId = funcSel ? parseInt(funcSel.value) || null : null;
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  if (fileInput2?.files?.length) {
    fd.append("file2", fileInput2.files[0]);
  }
  if (funcId) fd.append("funcionario_id", funcId);

  const btn = document.getElementById("btnProcessarOcr");
  if (btn) { btn.disabled = true; btn.innerHTML = `<div class="spinner"></div> Processando...`; }

  if (resultDiv) resultDiv.innerHTML = `
    <div style="padding:24px;text-align:center;color:var(--text-muted);">
      <div class="spinner" style="margin:0 auto 12px;width:36px;height:36px;border-width:3px;"></div>
      <div style="font-size:13px;font-weight:500;">Analisando cartão com OCR…</div>
      <div style="font-size:11px;margin-top:6px;opacity:.7;">Detectando grade e lendo horários célula por célula</div>
    </div>`;

  try {
    const result = await API.processarCartao(fd);
    renderOcrResult(result, funcId);
  } catch (e) {
    if (resultDiv) resultDiv.innerHTML = `
      <div class="empty-state" style="color:var(--red);">
        <div class="es-icon">⚠</div>
        <div class="es-text">${e.message}</div>
      </div>`;
    toast("⚠ " + e.message, "error");
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = "🔍 Processar OCR"; }
  }
}

// ── OCR via IA (experimental) ─────────────────────────────────────────────────
async function processarOcrIA() {
  const fileInput  = document.getElementById("ocrFileInput");
  const fileInput2 = document.getElementById("ocrFileInput2");
  const funcSel    = document.getElementById("ocrFuncSelect");
  const resultDiv  = document.getElementById("ocrResult");

  if (!fileInput?.files?.length) {
    toast("Selecione pelo menos a Face 1 do cartão ponto", "error");
    return;
  }
  const funcId = funcSel ? parseInt(funcSel.value) || null : null;
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  if (fileInput2?.files?.length) fd.append("file2", fileInput2.files[0]);
  if (funcId) fd.append("funcionario_id", funcId);

  const btn = document.getElementById("btnProcessarIA");
  if (btn) { btn.disabled = true; btn.innerHTML = `<div class="spinner"></div> IA lendo...`; }
  if (resultDiv) resultDiv.innerHTML = `
    <div style="padding:24px;text-align:center;color:var(--text-muted);">
      <div class="spinner" style="margin:0 auto 12px;width:36px;height:36px;border-width:3px;"></div>
      <div style="font-size:13px;font-weight:500;">A IA está tentando ler o cartão…</div>
      <div style="font-size:11px;margin-top:6px;opacity:.7;">Experimental — pode demorar e errar mais que o OCR</div>
    </div>`;
  try {
    const result = await API.iaLerCartao(fd);
    if (!result.registros || !result.registros.length) {
      resultDiv.innerHTML = `<div class="empty-state" style="color:var(--yellow);">
        <div class="es-icon">🤖</div><div class="es-text">${result.msg || "A IA não conseguiu ler."}</div></div>`;
      toast("A IA não extraiu horários", "error");
      return;
    }
    renderOcrResult(result, funcId);
    toast(result.msg || "IA processou o cartão", "success");
  } catch (e) {
    resultDiv.innerHTML = `<div class="empty-state" style="color:var(--red);">
      <div class="es-icon">⚠</div><div class="es-text">${e.message}</div></div>`;
    toast("⚠ " + e.message, "error");
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = "🤖 Tentar com IA (experimental)"; }
  }
}

// ── Renderizar resultado OCR ──────────────────────────────────────────────────

function renderOcrResult(result, funcId) {
  const div = document.getElementById("ocrResult");
  if (!div) return;

  const registros = result.registros || [];
  if (!registros.length) {
    div.innerHTML = `
      <div class="ocr-result">
        <div class="ocr-result-header">
          <span>⚠ Nenhum horário detectado</span>
          <span>Arquivo: ${result.arquivo || "—"}</span>
        </div>
        <div style="padding:20px 16px;">
          <p style="font-size:12px;color:var(--text-secondary);line-height:1.7;">
            <strong>Sugestões para melhorar o resultado:</strong><br>
            • Use scan em <strong>150 DPI ou superior</strong> (evite fotos de celular inclinadas)<br>
            • A imagem deve estar <strong>reta</strong>, não inclinada<br>
            • Prefira <strong>fundo branco</strong> com boa iluminação<br>
            • Envie <strong>uma face por vez</strong> (não sobreponha as duas faces)
          </p>
        </div>
      </div>`;
    return;
  }

  const CONF_MIN = parseFloat(State.config.conf_minima ?? 0.65);
  const campos   = ["entrada","inicio_intervalo","fim_intervalo","saida"];
  const labels   = ["Entrada","Início Int.","Fim Int.","Saída"];

  // Informações sobre as duas faces
  const face1Count = result.face1_count || registros.filter(r => r.dia <= 15).length;
  const face2Count = result.face2_count || registros.filter(r => r.dia >= 16).length;
  const duasFaces  = result.duas_faces;

  // Lê valores editáveis do resultado (pode ter sido alterados manualmente)
  function getFieldVal(rDia, campo) {
    const inp = document.getElementById(`ocr-${rDia}-${campo}`);
    return inp ? inp.value : null;
  }

  const tableRows = registros.map(r => {
    const cells = campos.map((c) => {
      const field = r[c] || {};
      const val   = field.value || "";
      const conf  = field.conf  ?? 1.0;
      const low   = field.low_conf || conf < CONF_MIN;
      const cls   = low && val ? "low-conf" : val ? "filled" : "";
      return `<td>
        <input class="t-input ${cls}" id="ocr-${r.dia}-${c}"
               value="${val}" placeholder="--:--"
               title="Confiança: ${confLabel(conf)}" />
        ${low && val ? `<div class="conf-badge conf-low" style="font-size:9px;margin-top:1px;">${confLabel(conf)}</div>` : ""}
      </td>`;
    }).join("");

    // Destaca linha se todos os campos estão vazios
    const allEmpty = campos.every(c => !(r[c]?.value));
    return `<tr class="${allEmpty ? "ocr-row-empty" : ""}">
      <td style="text-align:center;font-weight:700;font-size:13px;color:var(--text-secondary);">${r.dia}</td>
      ${cells}
      <td style="text-align:center;">
        <button class="btn btn-ghost btn-sm btn-icon" onclick="limparLinhaOcr(${r.dia})" title="Limpar linha">✕</button>
      </td>
    </tr>`;
  }).join("");

  div.innerHTML = `
  <div class="ocr-result">
    <div class="ocr-result-header">
      <span>✅ ${registros.length} dias detectados</span>
      <span style="display:flex;gap:8px;align-items:center;">
        ${duasFaces ? `<span class="engine-pill ok">Face 1: ${face1Count} · Face 2: ${face2Count}</span>` : ""}
        <span style="font-size:10px;opacity:.7;">${result.engine_used === "paddle" ? "PaddleOCR" : "Tesseract"}</span>
      </span>
    </div>
    <div style="padding:10px 16px 6px;">
      <p style="font-size:11px;color:var(--text-secondary);line-height:1.6;margin:0;">
        Revise os campos marcados em <span style="color:var(--yellow);font-weight:600;">amarelo</span> (baixa confiança).
        Campos em <span style="color:var(--green);font-weight:600;">verde</span> foram detectados com boa confiança.
        Edite diretamente se necessário antes de importar.
      </p>
    </div>
    <div style="overflow-x:auto;padding:0 16px 8px;">
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead>
          <tr style="background:var(--bg-raised);">
            <th style="padding:6px 4px;color:var(--text-muted);font-size:10px;text-transform:uppercase;width:36px;">Dia</th>
            ${labels.map(l => `<th style="padding:6px 4px;color:var(--text-muted);font-size:10px;text-transform:uppercase;">${l}</th>`).join("")}
            <th style="width:28px;"></th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>
    <div style="padding:12px 16px;border-top:1px solid var(--border);display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
      <button class="btn btn-primary" id="btnImportarOcr"
              onclick="importarOcrAtual(${funcId || "null"})">
        ⬇ Importar para Cartão Ponto
      </button>
      <button class="btn btn-ghost btn-sm" onclick="limparOcr()">↺ Novo OCR</button>
      <span style="font-size:11px;color:var(--text-muted);">Apenas campos com horário válido serão importados</span>
    </div>
  </div>`;

  // Aplica máscara de hora
  document.querySelectorAll("#ocrResult .t-input").forEach(applyTimeMask);

  // Guarda os registros originais no botão para importação
  document.getElementById("btnImportarOcr")?._registros; // já usa closure do funcId
  window._ocrRegistros = registros;
}

function limparLinhaOcr(dia) {
  ["entrada","inicio_intervalo","fim_intervalo","saida"].forEach(c => {
    const el = document.getElementById(`ocr-${dia}-${c}`);
    if (el) { el.value = ""; el.className = "t-input"; }
  });
}

async function importarOcrAtual(funcId) {
  if (!funcId) { toast("Selecione um funcionário para importar", "error"); return; }
  const registros = window._ocrRegistros || [];
  const CONF_MIN  = parseFloat(State.config.conf_minima ?? 0.65);

  const lote = registros
    .map(r => {
      const campos = ["entrada","inicio_intervalo","fim_intervalo","saida"];
      const rec = { funcionario_id: funcId, fonte: "ocr" };

      // Lê valores do formulário (podem ter sido editados pelo usuário)
      const dataStr = `${State.ano}-${String(State.mes).padStart(2,"0")}-${String(r.dia).padStart(2,"0")}`;
      rec.data = dataStr;
      campos.forEach(c => {
        const el = document.getElementById(`ocr-${r.dia}-${c}`);
        rec[c] = el?.value || r[c]?.value || null;
      });
      rec.conf_entrada  = r.entrada?.conf          ?? 1.0;
      rec.conf_saida    = r.saida?.conf            ?? 1.0;
      rec.conf_ini_int  = r.inicio_intervalo?.conf ?? 1.0;
      rec.conf_fim_int  = r.fim_intervalo?.conf    ?? 1.0;

      return rec;
    })
    .filter(r => r.entrada || r.saida);

  if (!lote.length) { toast("Nenhum registro válido para importar", "error"); return; }

  try {
    const btn = document.getElementById("btnImportarOcr");
    if (btn) { btn.disabled = true; btn.textContent = "Importando…"; }
    const res = await API.salvarLote(lote);
    toast(`✅ ${res.saved} registros importados!`, "success");
    State.activeFuncId = funcId;
    showPage("ponto");
    await renderPontoPage();
  } catch (e) {
    toast("⚠ Erro ao importar: " + e.message, "error");
    const btn = document.getElementById("btnImportarOcr");
    if (btn) { btn.disabled = false; btn.innerHTML = "⬇ Importar para Cartão Ponto"; }
  }
}


async function importarOcr(funcId, registros) {
  if (!funcId) {
    toast("Selecione um funcionário para importar", "error");
    return;
  }
  const CONF_MIN = parseFloat(State.config.conf_minima ?? 0.65);
  const lote = registros
    .filter(r => r.entrada?.value || r.saida?.value)
    .map(r => {
      const dataStr = `${State.ano}-${String(State.mes).padStart(2,"0")}-${String(r.dia).padStart(2,"0")}`;
      return {
        funcionario_id:   funcId,
        data:             dataStr,
        entrada:          r.entrada?.value         || null,
        inicio_intervalo: r.inicio_intervalo?.value || null,
        fim_intervalo:    r.fim_intervalo?.value    || null,
        saida:            r.saida?.value            || null,
        conf_entrada:     r.entrada?.conf           ?? 1.0,
        conf_saida:       r.saida?.conf             ?? 1.0,
        conf_ini_int:     r.inicio_intervalo?.conf  ?? 1.0,
        conf_fim_int:     r.fim_intervalo?.conf      ?? 1.0,
        fonte:            "ocr",
      };
    });

  if (!lote.length) {
    toast("Nenhum registro válido para importar", "error");
    return;
  }

  try {
    const res = await API.salvarLote(lote);
    toast(`✅ ${res.saved} registros importados!`, "success");
    State.activeFuncId = funcId;
    showPage("ponto");
    await renderPontoPage();
  } catch (e) {
    toast("⚠ Erro ao importar: " + e.message, "error");
  }
}

// ── CONFIG ────────────────────────────────────────────────────────────────

const DIAS_SEMANA = ["Domingo","Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado"];
const SCHED_PADRAO = {
  "0": {ativo:false, entrada:"07:00", intInicio:"11:30", intFim:"13:00", saida:"12:00"},
  "1": {ativo:true,  entrada:"07:00", intInicio:"11:30", intFim:"13:00", saida:"17:30"},
  "2": {ativo:true,  entrada:"07:00", intInicio:"11:30", intFim:"13:00", saida:"17:30"},
  "3": {ativo:true,  entrada:"07:00", intInicio:"11:30", intFim:"13:00", saida:"17:30"},
  "4": {ativo:true,  entrada:"07:00", intInicio:"11:30", intFim:"13:00", saida:"17:30"},
  "5": {ativo:true,  entrada:"07:00", intInicio:"11:30", intFim:"13:00", saida:"16:30"},
  "6": {ativo:false, entrada:"07:00", intInicio:"11:30", intFim:"13:00", saida:"12:00"},
};

function _cargaPrevista(s) {
  if (!s || !s.ativo) return "--";
  const ini = parseTime(s.entrada), fim = parseTime(s.saida);
  const ii = parseTime(s.intInicio), fi = parseTime(s.intFim);
  if (ini === null || fim === null) return "--";
  let m;
  if (ii !== null && fi !== null && ii > ini && fi < fim) m = (ii - ini) + (fim - fi);
  else m = fim - ini;
  return minutesToStr(m);
}

async function renderConfigPage() {
  const cfg = State.config || {};
  const ni = document.getElementById("cfgNoturnoInicio");
  if (ni) ni.value = cfg.noturno_inicio || "22:00";
  const fr = document.getElementById("cfgFeriadoRate");
  if (fr) fr.value = String(cfg.feriado_rate || "50");
  renderScheduleTable();
}

function renderScheduleTable() {
  const tbody = document.getElementById("schedTableBody");
  if (!tbody) return;
  const sched = (State.config && State.config.schedule) ? State.config.schedule : SCHED_PADRAO;
  let html = "";
  for (let dw = 0; dw <= 6; dw++) {
    const s = sched[String(dw)] || SCHED_PADRAO[String(dw)];
    const dis = s.ativo ? "" : "disabled";
    const op  = s.ativo ? "1" : "0.4";
    const inp = (field, val) =>
      `<input class="t-input" id="sch-${dw}-${field}" value="${val||""}" ${dis} maxlength="5"
        oninput="schedMask(this)" onchange="schedChange(${dw},'${field}',this.value)"
        style="width:64px;text-align:center;font-family:var(--font-mono);" />`;
    html += `<tr style="opacity:${op};border-bottom:1px solid var(--border-light);">
      <td style="padding:5px 8px;font-weight:500;">${DIAS_SEMANA[dw]}</td>
      <td style="padding:5px 8px;text-align:center;">
        <input type="checkbox" ${s.ativo?"checked":""} onchange="schedAtivo(${dw},this.checked)" style="width:16px;height:16px;cursor:pointer;" />
      </td>
      <td style="padding:5px 8px;">${inp("entrada", s.entrada)}</td>
      <td style="padding:5px 8px;">${inp("intInicio", s.intInicio)}</td>
      <td style="padding:5px 8px;">${inp("intFim", s.intFim)}</td>
      <td style="padding:5px 8px;">${inp("saida", s.saida)}</td>
      <td style="padding:5px 8px;text-align:right;font-family:var(--font-mono);color:var(--text-secondary);" id="carga-${dw}">${_cargaPrevista(s)}</td>
    </tr>`;
  }
  tbody.innerHTML = html;
}

function _ensureSchedule() {
  if (!State.config) State.config = {};
  if (!State.config.schedule) State.config.schedule = JSON.parse(JSON.stringify(SCHED_PADRAO));
  return State.config.schedule;
}

function schedMask(input) {
  let v = input.value.replace(/\D/g, "").slice(0, 4);
  if (v.length >= 3) v = v.slice(0, 2) + ":" + v.slice(2);
  input.value = v;
}

function schedChange(dw, field, value) {
  const sched = _ensureSchedule();
  if (!sched[String(dw)]) sched[String(dw)] = {...SCHED_PADRAO[String(dw)]};
  const p = parseTime(value);
  sched[String(dw)][field] = p !== null
    ? `${String(Math.floor(p/60)).padStart(2,"0")}:${String(p%60).padStart(2,"0")}`
    : value;
  const cargaEl = document.getElementById(`carga-${dw}`);
  if (cargaEl) cargaEl.textContent = _cargaPrevista(sched[String(dw)]);
}

function schedAtivo(dw, ativo) {
  const sched = _ensureSchedule();
  if (!sched[String(dw)]) sched[String(dw)] = {...SCHED_PADRAO[String(dw)]};
  sched[String(dw)].ativo = ativo;
  renderScheduleTable();
}

async function salvarConfigCompleta() {
  const cfg = {
    noturno_inicio: document.getElementById("cfgNoturnoInicio")?.value || "22:00",
    feriado_rate:   document.getElementById("cfgFeriadoRate")?.value || "50",
    schedule:       _ensureSchedule(),
  };
  try {
    await API.salvarConfig(cfg);
    Object.assign(State.config, cfg);
    toast("✓ Configuração salva!", "success");
    // Recalcula todos os registros existentes com a nova escala
    await recalcularTudo();
  } catch (e) {
    toast("⚠ " + e.message, "error");
  }
}

async function restaurarEscalaPadrao() {
  if (!confirm("Restaurar a escala padrão (Seg–Qui 07:00–17:30, Sex 07:00–16:30)?")) return;
  State.config.schedule = JSON.parse(JSON.stringify(SCHED_PADRAO));
  renderScheduleTable();
  toast("Escala restaurada — clique em Salvar para aplicar");
}

// Recalcula todos os registros de todos os funcionários no servidor
async function recalcularTudo() {
  // Reenvia cada registro existente para forçar recálculo com a nova escala
  for (const f of State.funcionarios) {
    try {
      // pega todos os meses que têm registros (varre o ano corrente ±1)
      for (let mes = 1; mes <= 12; mes++) {
        const regs = await API.listarMes(f.id, State.ano, mes);
        const comDados = regs.filter(r => r.entrada || r.saida || r.inicio_intervalo || r.fim_intervalo);
        for (const r of comDados) {
          await API.salvarRegistro({
            funcionario_id: f.id, data: r.data,
            entrada: r.entrada, inicio_intervalo: r.inicio_intervalo,
            fim_intervalo: r.fim_intervalo, saida: r.saida,
            feriado: r.feriado ? 1 : 0, fonte: r.fonte || "manual",
          });
        }
      }
    } catch (_) {}
  }
  renderPontoPage();
}

// ── EXPORTAR / IMPORTAR BANCO DE DADOS (formato antigo, igual ao Importar JSON) ──
async function exportarBancoDados() {
  try {
    const r = await fetch("/api/exportar-json");
    if (!r.ok) throw new Error("Falha ao exportar");
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const hoje = new Date().toISOString().slice(0,10);
    a.href = url; a.download = `cartao_ponto_backup_${hoje}.json`; a.click();
    URL.revokeObjectURL(url);
    toast("💾 Banco de dados exportado!", "success");
  } catch (e) { toast("⚠ " + e.message, "error"); }
}

async function importarBancoDados(event) {
  const file = event.target.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    // Usa o MESMO conversor do "Importar JSON" (formato antigo → novo)
    const fd = new FormData();
    fd.append("file", new Blob([text], {type:"application/json"}), file.name);
    const r = await fetch("/api/importar-json", { method: "POST", body: fd });
    if (!r.ok) { const e = await r.json().catch(()=>({detail:"Erro"})); throw new Error(e.detail || "Arquivo inválido"); }
    const res = await r.json();
    // recarrega tudo
    await loadFuncionarios();
    await loadConfig();
    await loadFeriados();
    if (typeof populateOcrSelect === "function") populateOcrSelect();
    renderAll();
    toast(`📂 ${res.msg || "Banco importado!"}`, "success");
  } catch (e) {
    toast("⚠ " + e.message, "error");
  } finally {
    event.target.value = "";
  }
}

// ── MODAIS ────────────────────────────────────────────────────────────────

function openModal(id) {
  document.getElementById(id)?.classList?.remove("hidden");
  const input = document.querySelector(`#${id} .form-input`);
  if (input) setTimeout(() => input.focus(), 100);
}
function closeModal(id) {
  document.getElementById(id)?.classList?.add("hidden");
}
function handleModalKey(event, id) {
  if (event.key === "Enter") {
    if (id === "modalAddFunc") adicionarFuncionario();
  }
  if (event.key === "Escape") closeModal(id);
}

// ── ARRANQUE ──────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", init);
