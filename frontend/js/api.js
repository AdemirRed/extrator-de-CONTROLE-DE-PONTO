/**
 * Cliente API — todas as chamadas ao backend FastAPI.
 */

const BASE = "";  // mesmo host

const API = {
  // ── Funcionários ──────────────────────────────────────────────────────────
  async listarFuncionarios() {
    return _get("/api/funcionarios");
  },
  async criarFuncionario(data) {
    return _post("/api/funcionarios", data);
  },
  async atualizarFuncionario(id, data) {
    return _put(`/api/funcionarios/${id}`, data);
  },
  async removerFuncionario(id) {
    return _delete(`/api/funcionarios/${id}`);
  },

  // ── Registros ─────────────────────────────────────────────────────────────
  async listarMes(funcionarioId, ano, mes) {
    return _get(`/api/registros/mes?funcionario_id=${funcionarioId}&ano=${ano}&mes=${mes}`);
  },
  async salvarRegistro(data) {
    return _post("/api/registros", data);
  },
  async salvarLote(registros) {
    return _post("/api/registros/lote", registros);
  },
  async limparMes(funcionarioId, ano, mes) {
    return _delete(`/api/registros/${funcionarioId}/mes?ano=${ano}&mes=${mes}`);
  },
  async dashboard(ano, mes) {
    return _get(`/api/registros/dashboard?ano=${ano}&mes=${mes}`);
  },
  async anual(funcionarioId, ano) {
    return _get(`/api/registros/anual?funcionario_id=${funcionarioId}&ano=${ano}`);
  },

  // ── Feriados ──────────────────────────────────────────────────────────────
  async listarFeriados(ano) {
    return _get(`/api/feriados?ano=${ano}`);
  },
  async criarFeriado(data, nome) {
    return _post("/api/feriados", { data, nome });
  },
  async removerFeriado(data) {
    return _delete(`/api/feriados/${data}`);
  },

  // ── Configurações ─────────────────────────────────────────────────────────
  async obterConfig() {
    return _get("/api/config");
  },
  async salvarConfig(config) {
    return _post("/api/config", config);
  },

  // ── IA (Ollama) ───────────────────────────────────────────────────────────
  async iaConfig()            { return _get("/api/ia/config"); },
  async iaSalvarConfig(c)     { return _post("/api/ia/config", c); },
  async iaModelos()           { return _get("/api/ia/modelos"); },
  async iaTestar()            { return _post("/api/ia/testar", {}); },
  async iaPerguntar(pergunta, ano) { return _post("/api/ia/perguntar", { pergunta, ano }); },
  async iaLerCartao(formData) {
    const r = await fetch("/api/ia/ler-cartao", { method: "POST", body: formData });
    if (!r.ok) { const e = await r.json().catch(()=>({detail:r.statusText})); throw new Error(e.detail || "Erro"); }
    return r.json();
  },

  // ── OCR ───────────────────────────────────────────────────────────────────
  async statusOcr() {
    return _get("/api/ocr/status");
  },
  async processarCartao(formData) {
    const resp = await fetch("/api/ocr/processar", {
      method: "POST",
      body: formData,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || "Erro no OCR");
    }
    return resp.json();
  },

  // ── Exports ───────────────────────────────────────────────────────────────
  downloadExcel(funcId, ano, mes) {
    window.location.href = `/api/exports/excel?funcionario_id=${funcId}&ano=${ano}&mes=${mes}`;
  },
  downloadCsv(funcId, ano, mes) {
    window.location.href = `/api/exports/csv?funcionario_id=${funcId}&ano=${ano}&mes=${mes}`;
  },
  downloadJson(funcId, ano, mes) {
    window.location.href = `/api/exports/json?funcionario_id=${funcId}&ano=${ano}&mes=${mes}`;
  },
  downloadExcelTodos(ano, mes) {
    window.location.href = `/api/exports/todos/excel?ano=${ano}&mes=${mes}`;
  },
};

// ── helpers fetch ─────────────────────────────────────────────────────────

async function _get(url) {
  const r = await fetch(BASE + url);
  if (!r.ok) throw new Error(`GET ${url}: ${r.status}`);
  return r.json();
}

async function _post(url, body) {
  const r = await fetch(BASE + url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(e.detail || `POST ${url}: ${r.status}`);
  }
  return r.json();
}

async function _put(url, body) {
  const r = await fetch(BASE + url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`PUT ${url}: ${r.status}`);
  return r.json();
}

async function _delete(url) {
  const r = await fetch(BASE + url, { method: "DELETE" });
  if (!r.ok) throw new Error(`DELETE ${url}: ${r.status}`);
  return r.json();
}
