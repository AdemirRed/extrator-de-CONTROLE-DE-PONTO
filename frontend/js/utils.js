/**
 * Funções utilitárias compartilhadas.
 */

const MESES_NOMES = [
  "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
  "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
];
const DS_NOMES = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"];

// ── Tempo ──────────────────────────────────────────────────────────────────

function parseTime(t) {
  if (!t || typeof t !== "string") return null;
  const p = t.trim().split(":");
  if (p.length !== 2) return null;
  const h = parseInt(p[0]), m = parseInt(p[1]);
  if (isNaN(h) || isNaN(m) || h < 0 || h > 23 || m < 0 || m > 59) return null;
  return h * 60 + m;
}

function minutesToStr(min) {
  if (min === null || min === undefined) return "—";
  const neg = min < 0;
  const abs = Math.abs(min);
  const h = Math.floor(abs / 60), m = abs % 60;
  const s = `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}`;
  return neg ? `-${s}` : s;
}

function formatDate(dateStr) {
  // "2026-05-07" → "07/05/2026"
  if (!dateStr) return "";
  const parts = dateStr.split("-");
  return `${parts[2]}/${parts[1]}/${parts[0]}`;
}

function diaSemana(dateStr) {
  // retorna 0=dom...6=sáb
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d).getDay();
}

function diasNoMes(ano, mes) {
  return new Date(ano, mes, 0).getDate();
}

// ── Inputs de hora com máscara ─────────────────────────────────────────────

function applyTimeMask(input) {
  input.addEventListener("input", function () {
    let v = this.value.replace(/\D/g, "").slice(0, 4);
    if (v.length >= 3) v = v.slice(0, 2) + ":" + v.slice(2);
    this.value = v;
  });
  input.addEventListener("blur", function () {
    const v = this.value;
    if (!v) return;
    const p = parseTime(v);
    if (p === null) {
      this.value = "";
      this.classList.remove("filled");
    } else {
      const h = Math.floor(p / 60), m = p % 60;
      this.value = `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}`;
      this.classList.add("filled");
    }
  });
}

// ── Toast ─────────────────────────────────────────────────────────────────

function toast(msg, type = "default") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.style.borderColor = type === "error" ? "var(--red)"
    : type === "success" ? "var(--green)"
    : "var(--border)";
  el.style.display = "block";
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.style.display = "none"; }, 2800);
}

// ── Dropdown ──────────────────────────────────────────────────────────────

function toggleDD(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const was = el.classList.contains("open");
  closeAllDD();
  if (!was) el.classList.add("open");
}

function closeAllDD() {
  document.querySelectorAll(".dd-wrap.open").forEach(e => e.classList.remove("open"));
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".dd-wrap")) closeAllDD();
});

// ── Iniciais ──────────────────────────────────────────────────────────────

function initials(nome) {
  if (!nome) return "?";
  const parts = nome.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// ── Confiança OCR ─────────────────────────────────────────────────────────

function confClass(conf) {
  if (conf === null || conf === undefined) return "";
  if (conf >= 0.85) return "conf-high";
  if (conf >= 0.65) return "conf-medium";
  return "conf-low";
}

function confLabel(conf) {
  if (conf === null || conf === undefined) return "—";
  return `${Math.round(conf * 100)}%`;
}
