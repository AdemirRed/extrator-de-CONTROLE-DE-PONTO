/**
 * Geração de relatórios imprimíveis (A4) — interface nova.
 * Busca dados da API e produz HTML idêntico ao do sistema antigo.
 *   - Relatório Mensal (individual / todos)
 *   - Relatório Anual (individual / todos, com ranking "melhor funcionário")
 */

const REL_MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
                   "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
const REL_DS = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"];

// ── CSS compartilhado (A4 portrait) ─────────────────────────────────────────
const REL_CSS = `
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:Arial,Helvetica,sans-serif;font-size:10px;color:#000;background:#fff;padding:20px 24px;}
.hdr{border:2.5px solid #000;margin-bottom:14px;}
.hdr-top{background:#000;color:#fff;padding:7px 14px;display:flex;align-items:baseline;justify-content:space-between;}
.hdr-top h1{font-size:13px;font-weight:900;text-transform:uppercase;letter-spacing:2px;}
.hdr-top span{font-size:9px;letter-spacing:1px;opacity:.85;}
.hdr-bot{display:grid;grid-template-columns:repeat(4,1fr);gap:0;}
.hdr-item{padding:7px 12px;border-right:.5px solid #ccc;}
.hdr-item:last-child{border-right:none;}
.hi-label{font-size:8px;text-transform:uppercase;letter-spacing:.5px;color:#666;margin-bottom:2px;}
.hi-val{font-size:11.5px;font-weight:700;}
.hi-val.pos{color:#000;} .hi-val.neg{color:#000;}
table{width:100%;border-collapse:collapse;margin-bottom:14px;font-size:9.5px;}
thead tr{background:#222;color:#fff;}
th{padding:4px 3px;text-align:center;font-size:8.5px;text-transform:uppercase;letter-spacing:.3px;white-space:nowrap;}
th:first-child{width:26px;}
td{padding:2.8px 3px;border-bottom:.3px solid #e0e0e0;text-align:center;white-space:nowrap;}
tr:nth-child(even) td{background:#f6f6f6;}
tr.ot td{font-weight:700;}
tr.ot td:first-child{border-left:3px solid #000;padding-left:2px;}
tr.ut td{font-style:italic;color:#555;}
tr.ut td:first-child{border-left:3px dashed #999;padding-left:2px;}
tr.fds td{color:#bbb;font-weight:normal;}
tr.fer td{font-weight:bold;}
tr.fer td:first-child{border-left:3px double #000;padding-left:2px;}
tr.fer td.saldo:before{content:"★ ";}
tr.sem-dados td{color:#bbb;}
td.saldo{font-weight:700;}
td.saldo.pos{color:#000;} td.saldo.neg{color:#000;}
tfoot tr td{border-top:2px solid #000;background:#ebebeb;font-weight:700;font-size:10px;padding:4px 3px;}
.section-title{font-size:10px;font-weight:900;text-transform:uppercase;letter-spacing:1px;margin:14px 0 7px;
  padding-bottom:4px;border-bottom:1.5px solid #000;}
.sum{border:1.5px solid #000;padding:10px 14px;margin-bottom:12px;page-break-inside:avoid;}
.sum-title{font-size:10px;font-weight:900;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;
  padding-bottom:5px;border-bottom:1.5px solid #000;}
.sum-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin-bottom:12px;}
.sbox{border:1px solid #ccc;padding:6px 9px;}
.sb-lbl{font-size:7.5px;text-transform:uppercase;letter-spacing:.4px;color:#666;margin-bottom:3px;}
.sb-val{font-size:15px;font-weight:900;letter-spacing:-.5px;}
.sb-val.neg{border-bottom:3px solid #000;}
.destaques{display:flex;flex-direction:column;gap:5px;margin-bottom:12px;}
.dest-item{font-size:9.5px;padding:5px 9px;border:1px solid #ddd;border-left:4px solid #888;}
.dest-item.dest-pos{border-left-color:#000;}
.dest-item.dest-neg{border-left-color:#000;background:#f6f6f6;}
.assin{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:18px;page-break-inside:avoid;}
.abox{border-top:1.5px solid #000;padding-top:4px;text-align:center;font-size:8.5px;color:#444;}
.footer{margin-top:10px;font-size:7.5px;color:#aaa;text-align:center;border-top:.5px solid #ddd;padding-top:5px;}
.legend{font-size:8px;color:#666;margin-bottom:12px;display:flex;gap:16px;flex-wrap:wrap;align-items:center;}
.leg-item{display:flex;align-items:center;gap:5px;}
.leg-bar{width:10px;height:12px;flex-shrink:0;}
.leg-bar.ot{border-left:3px solid #000;} .leg-bar.ut{border-left:3px dashed #999;}
/* Ranking */
.rank-wrap{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;}
.rank-card{border:1.5px solid #000;}
.rank-card h3{background:#000;color:#fff;font-size:9px;text-transform:uppercase;letter-spacing:1px;padding:5px 10px;}
.rank-card table{margin:0;font-size:9px;}
.rank-card td{text-align:left;padding:3px 8px;}
.rank-card td:first-child{width:30px;text-align:center;font-size:12px;}
.rank-card td.rn{font-weight:600;}
.rank-card td:last-child{text-align:right;font-weight:700;font-family:monospace;}
.rank-card tr.rank1 td{background:#fff3cc;}
.melhor{border:2.5px solid #000;padding:12px 16px;margin-bottom:14px;display:flex;align-items:center;gap:16px;page-break-inside:avoid;}
.melhor .trofeu{font-size:40px;}
.melhor .ml-lbl{font-size:8px;text-transform:uppercase;letter-spacing:1.5px;color:#666;}
.melhor .ml-nome{font-size:22px;font-weight:900;letter-spacing:-.5px;}
.melhor .ml-sub{font-size:9px;color:#444;margin-top:3px;}
.page-block{page-break-after:always;}
.page-block:last-child{page-break-after:auto;}
.noPrint{margin-bottom:16px;text-align:center;}
.btn-print{background:#000;color:#fff;border:none;padding:9px 22px;font-size:12px;font-family:Arial,sans-serif;
  cursor:pointer;border-radius:3px;letter-spacing:.5px;}
.btn-print:hover{background:#333;}
@media print{ .noPrint{display:none!important;} body{padding:6px 10px;}
  tr.ot td,.melhor,.rank-card tr.rank1 td{-webkit-print-color-adjust:exact;print-color-adjust:exact;} }
@page{size:A4 portrait;margin:12mm 10mm;}
`;

function _relAbrir(titulo, corpoHtml) {
  const html = `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>${titulo}</title><style>${REL_CSS}</style></head><body>
<div class="noPrint"><button class="btn-print" onclick="window.print()">🖨 Imprimir / Salvar PDF</button></div>
${corpoHtml}</body></html>`;
  const win = window.open("", "_blank", "width=900,height=950,scrollbars=yes");
  if (win) { win.document.write(html); win.document.close(); }
  else toast("⚠ Permita pop-ups para abrir o relatório", "error");
}

// ── Bloco do RELATÓRIO MENSAL de um funcionário ─────────────────────────────
function _blocoMensal(func, regs, ano, mes) {
  let sumH=0, sumN=0, sumE=0, sumNot=0, diasTrab=0, tbody="";
  regs.forEach(r => {
    const dw = diaSemana(r.data);            // 0=Dom..6=Sáb
    const total = r.total_min, prev = r.previsto_min, saldo = r.saldo_min, not = r.noturno_min;
    const fer = !!r.is_feriado, fds = (dw === 0 || dw === 6);
    const hasData = total !== null && total !== undefined;
    if (hasData) { sumH+=total; sumN+=prev||0; sumE+=saldo||0; sumNot+=not||0; diasTrab++; }
    const esSab = (dw === 6) && hasData && !fer;
    const hasOt = hasData && saldo > 0, hasUt = hasData && saldo < 0;
    let cls = fer && hasData ? "fer" : (fds && !hasData) ? "fds" : hasOt ? "ot" : hasUt ? "ut" : "";
    const d = parseInt(r.data.slice(-2));
    const diaLabel = fer ? `${String(d).padStart(2,"0")}<br><small>Fer.</small>`
                     : esSab ? `${String(d).padStart(2,"0")}<br><small>Sáb+</small>`
                     : String(d).padStart(2,"0");
    const saldoTxt = hasData && saldo !== null ? (saldo>0?"+":"")+minutesToStr(saldo) : "—";
    tbody += `<tr class="${cls}">
      <td>${diaLabel}</td><td>${REL_DS[dw]}</td>
      <td>${r.entrada||"—"}</td><td>${r.inicio_intervalo||"—"}</td>
      <td>${r.fim_intervalo||"—"}</td><td>${r.saida||"—"}</td>
      <td>${hasData?minutesToStr(total):"—"}</td>
      <td>${prev>0?minutesToStr(prev):"—"}</td>
      <td class="saldo">${saldoTxt}</td>
      <td>${not>0?minutesToStr(not):"—"}</td>
    </tr>`;
  });
  const hoje = new Date().toLocaleDateString("pt-BR");
  const saldoCls = sumE>=0?"pos":"neg";
  return `<div class="page-block">
  <div class="hdr">
    <div class="hdr-top"><h1>Controle de Ponto — Relatório Mensal</h1><span>Sistema de Cartão Ponto</span></div>
    <div class="hdr-bot">
      <div class="hdr-item"><div class="hi-label">Funcionário</div><div class="hi-val">${func.nome.toUpperCase()}</div></div>
      <div class="hdr-item"><div class="hi-label">Período</div><div class="hi-val">${REL_MESES[mes-1].toUpperCase()} / ${ano}</div></div>
      <div class="hdr-item"><div class="hi-label">Dias Trabalhados</div><div class="hi-val">${diasTrab} dia(s)</div></div>
      <div class="hdr-item"><div class="hi-label">Emitido em</div><div class="hi-val">${hoje}</div></div>
    </div>
  </div>
  <table>
    <thead><tr><th>Dia</th><th>Sem</th><th>Entrada</th><th>In.Int</th><th>Fm.Int</th><th>Saída</th><th>Total</th><th>Previsto</th><th>Saldo</th><th>Noturno</th></tr></thead>
    <tbody>${tbody}</tbody>
    <tfoot><tr>
      <td colspan="6" style="text-align:right;font-size:8.5px;text-transform:uppercase;color:#555;">Totais do Mês</td>
      <td>${minutesToStr(sumH)}</td><td>${minutesToStr(sumN)}</td>
      <td class="saldo">${(sumE>=0?"+":"")+minutesToStr(sumE)}</td>
      <td>${sumNot>0?minutesToStr(sumNot):"—"}</td>
    </tr></tfoot>
  </table>
  <div class="sum">
    <div class="sum-title">▌ Resumo do Mês</div>
    <div class="sum-grid">
      <div class="sbox"><div class="sb-lbl">Total Trabalhado</div><div class="sb-val">${minutesToStr(sumH)}</div></div>
      <div class="sbox"><div class="sb-lbl">Horas Previstas</div><div class="sb-val">${minutesToStr(sumN)}</div></div>
      <div class="sbox"><div class="sb-lbl">Saldo do Mês</div><div class="sb-val ${saldoCls}">${(sumE>=0?"+":"")+minutesToStr(sumE)}</div></div>
      <div class="sbox"><div class="sb-lbl">Adicional Noturno</div><div class="sb-val">${sumNot>0?minutesToStr(sumNot):"—"}</div></div>
      <div class="sbox"><div class="sb-lbl">Dias Trabalhados</div><div class="sb-val">${diasTrab}</div></div>
    </div>
  </div>
  <div class="legend">
    <span class="leg-item"><span class="leg-bar ot"></span><b>Borda sólida</b> = horas extras</span>
    <span class="leg-item"><span class="leg-bar ut"></span><i>Borda tracejada</i> = horas a menos</span>
    <span class="leg-item">★ Feriado &nbsp;|&nbsp; Sáb+ = sábado (100% extra)</span>
  </div>
  <div class="assin">
    <div class="abox">Assinatura do Funcionário</div>
    <div class="abox">Assinatura do Empregador / RH</div>
  </div>
  <div class="footer">Relatório gerado automaticamente pelo Sistema de Cartão Ponto — ${hoje}</div>
</div>`;
}

// ── RELATÓRIO MENSAL INDIVIDUAL ─────────────────────────────────────────────
async function relatorioMensal(funcId) {
  const func = State.funcionarios.find(f => f.id === funcId);
  if (!func) return;
  const regs = await API.listarMes(funcId, State.ano, State.mes);
  _relAbrir(`Relatório — ${func.nome} — ${REL_MESES[State.mes-1]} ${State.ano}`,
            _blocoMensal(func, regs, State.ano, State.mes));
}

// ── RELATÓRIO MENSAL — TODOS ────────────────────────────────────────────────
async function relatorioMensalTodos() {
  if (!State.funcionarios.length) { toast("Nenhum funcionário", "error"); return; }
  let corpo = "";
  for (const func of State.funcionarios) {
    const regs = await API.listarMes(func.id, State.ano, State.mes);
    corpo += _blocoMensal(func, regs, State.ano, State.mes);
  }
  _relAbrir(`Relatório Mensal — Todos — ${REL_MESES[State.mes-1]} ${State.ano}`, corpo);
}

// ── Bloco do RELATÓRIO ANUAL de um funcionário ──────────────────────────────
function _blocoAnual(anualData, ano) {
  const M = anualData.meses;
  let totH=0,totN=0,totE=0,totNot=0,totTrab=0,totFer=0,totSab=0;
  let bestMes=-1,bestVal=-Infinity,worstMes=-1,worstVal=Infinity,maxNot=-1,maxNotVal=-1;
  M.forEach((r,m) => {
    totH+=r.sumH; totN+=r.sumN; totE+=r.sumE; totNot+=r.sumNot;
    totTrab+=r.diasTrab; totFer+=r.diasFer; totSab+=r.diasSab;
    if (r.diasTrab>0) {
      if (r.sumE>bestVal){bestVal=r.sumE;bestMes=m;}
      if (r.sumE<worstVal){worstVal=r.sumE;worstMes=m;}
      if (r.sumNot>maxNotVal){maxNotVal=r.sumNot;maxNot=m;}
    }
  });
  let rows = M.map((r,m) => {
    const has = r.diasTrab>0;
    const sCls = r.sumE>0?"pos":r.sumE<0?"neg":"";
    const sStr = r.sumE!==0?(r.sumE>0?"+":"")+minutesToStr(r.sumE):(has?minutesToStr(0):"—");
    return `<tr class="${!has?"sem-dados":""}">
      <td style="text-align:left;padding-left:8px;">${REL_MESES[m]}</td>
      <td>${has?r.diasTrab:"—"}</td><td>${has?minutesToStr(r.sumH):"—"}</td>
      <td>${has&&r.sumN>0?minutesToStr(r.sumN):"—"}</td>
      <td class="saldo ${sCls}">${sStr}</td>
      <td>${has&&r.sumNot>0?minutesToStr(r.sumNot):"—"}</td>
      <td>${has&&r.diasFer>0?r.diasFer:"—"}</td>
      <td>${has&&r.diasSab>0?r.diasSab:"—"}</td>
    </tr>`;
  }).join("");
  const tCls = totE>0?"pos":totE<0?"neg":"";
  const tStr = (totE>=0?"+":"")+minutesToStr(totE);
  const hoje = new Date().toLocaleDateString("pt-BR");
  const avg = totTrab>0?Math.round(totH/totTrab):0;
  const mesMaisH = totTrab>0 ? REL_MESES[M.reduce((a,r,i)=>r.sumH>M[a].sumH?i:a,0)] : "—";
  const dest = `
    ${bestMes>=0?`<div class="dest-item dest-pos">📈 Melhor saldo: <b>${REL_MESES[bestMes]}</b> (${bestVal>0?"+":""}${minutesToStr(bestVal)})</div>`:""}
    ${worstMes>=0&&worstMes!==bestMes?`<div class="dest-item dest-neg">📉 Pior saldo: <b>${REL_MESES[worstMes]}</b> (${worstVal>0?"+":""}${minutesToStr(worstVal)})</div>`:""}
    ${maxNot>=0&&maxNotVal>0?`<div class="dest-item">🌙 Maior adicional noturno: <b>${REL_MESES[maxNot]}</b> (${minutesToStr(maxNotVal)})</div>`:""}
    ${totTrab>0?`<div class="dest-item">📅 Média diária trabalhada: <b>${minutesToStr(avg)}</b></div>`:""}
    ${totTrab>0?`<div class="dest-item">🏆 Mês com mais horas: <b>${mesMaisH}</b></div>`:""}`;
  return `<div class="page-block">
  <div class="hdr">
    <div class="hdr-top"><h1>Controle de Ponto — Relatório Anual ${ano}</h1><span>Sistema de Cartão Ponto</span></div>
    <div class="hdr-bot">
      <div class="hdr-item"><div class="hi-label">Funcionário</div><div class="hi-val">${anualData.nome.toUpperCase()}</div></div>
      <div class="hdr-item"><div class="hi-label">Ano</div><div class="hi-val">${ano}</div></div>
      <div class="hdr-item"><div class="hi-label">Total Dias Trabalhados</div><div class="hi-val">${totTrab} dia(s)</div></div>
      <div class="hdr-item"><div class="hi-label">Emitido em</div><div class="hi-val">${hoje}</div></div>
    </div>
  </div>
  <div class="section-title">▌ Resumo Mensal</div>
  <table>
    <thead><tr><th style="text-align:left;padding-left:8px;">Mês</th><th>Dias</th><th>Total H.</th><th>Previsto</th><th>Saldo</th><th>Noturno</th><th>Feriados</th><th>Sábados</th></tr></thead>
    <tbody>${rows}</tbody>
    <tfoot><tr>
      <td style="text-align:right;font-size:8.5px;text-transform:uppercase;color:#555;">Total Anual</td>
      <td>${totTrab}</td><td>${minutesToStr(totH)}</td><td>${totN>0?minutesToStr(totN):"—"}</td>
      <td class="saldo ${tCls}">${tStr}</td><td>${totNot>0?minutesToStr(totNot):"—"}</td>
      <td>${totFer>0?totFer:"—"}</td><td>${totSab>0?totSab:"—"}</td>
    </tr></tfoot>
  </table>
  <div class="section-title">▌ Indicadores Anuais</div>
  <div class="sum-grid" style="grid-template-columns:repeat(3,1fr);">
    <div class="sbox"><div class="sb-lbl">Total Trabalhado</div><div class="sb-val">${minutesToStr(totH)}</div></div>
    <div class="sbox"><div class="sb-lbl">Horas Previstas</div><div class="sb-val">${totN>0?minutesToStr(totN):"—"}</div></div>
    <div class="sbox"><div class="sb-lbl">Saldo Anual</div><div class="sb-val ${tCls}">${tStr}</div></div>
    <div class="sbox"><div class="sb-lbl">Horas Extras</div><div class="sb-val">${totE>0?minutesToStr(totE):"—"}</div></div>
    <div class="sbox"><div class="sb-lbl">Déficit de Horas</div><div class="sb-val neg">${totE<0?minutesToStr(Math.abs(totE)):"—"}</div></div>
    <div class="sbox"><div class="sb-lbl">Adicional Noturno</div><div class="sb-val">${totNot>0?minutesToStr(totNot):"—"}</div></div>
    <div class="sbox"><div class="sb-lbl">Dias Trabalhados</div><div class="sb-val">${totTrab}</div></div>
    <div class="sbox"><div class="sb-lbl">Feriados Trab.</div><div class="sb-val">${totFer>0?totFer:"—"}</div></div>
    <div class="sbox"><div class="sb-lbl">Sábados Trab.</div><div class="sb-val">${totSab>0?totSab:"—"}</div></div>
  </div>
  <div class="section-title">▌ Destaques do Ano</div>
  <div class="destaques">${dest||'<div class="dest-item">Sem dados no ano.</div>'}</div>
  <div class="assin">
    <div class="abox">Assinatura do Funcionário</div>
    <div class="abox">Assinatura do Empregador / RH</div>
  </div>
  <div class="footer">Relatório Anual gerado automaticamente — ${hoje}</div>
</div>`;
}

// ── RELATÓRIO ANUAL (individual ou todos + ranking) ─────────────────────────
async function relatorioAnual(funcIds) {
  const alvos = funcIds === null ? State.funcionarios
              : State.funcionarios.filter(f => funcIds.includes(f.id));
  if (!alvos.length) { toast("Nenhum funcionário", "error"); return; }

  // Busca os dados anuais de cada funcionário
  const dados = [];
  for (const f of alvos) dados.push(await API.anual(f.id, State.ano));

  let corpo = dados.map(d => _blocoAnual(d, State.ano)).join("\n");

  // Ranking + "melhor funcionário" quando há mais de 1
  if (dados.length > 1) {
    const ranks = dados.map(d => {
      let tH=0,tE=0,tNot=0,tTrab=0;
      d.meses.forEach(r => { tH+=r.sumH; tE+=r.sumE; tNot+=r.sumNot; tTrab+=r.diasTrab; });
      return { nome:d.nome, tH, tE, tNot, tTrab };
    });
    const byHoras=[...ranks].sort((a,b)=>b.tH-a.tH);
    const bySaldo=[...ranks].sort((a,b)=>b.tE-a.tE);
    const byNot  =[...ranks].sort((a,b)=>b.tNot-a.tNot);
    const byDias =[...ranks].sort((a,b)=>b.tTrab-a.tTrab);
    const medals=["🥇","🥈","🥉"];
    const rankTable = (titulo, arr, fmt) => `<div class="rank-card"><h3>${titulo}</h3><table><tbody>${
      arr.map((r,i)=>`<tr class="${i===0?"rank1":""}"><td>${i<3?medals[i]:(i+1)+"º"}</td><td class="rn">${r.nome}</td><td>${fmt(r)}</td></tr>`).join("")
    }</tbody></table></div>`;
    const melhor = bySaldo[0];
    corpo += `<div class="page-block">
      <div class="hdr"><div class="hdr-top"><h1>Ranking de Funcionários — ${State.ano}</h1><span>Sistema de Cartão Ponto</span></div>
        <div class="hdr-bot">
          <div class="hdr-item"><div class="hi-label">Funcionários</div><div class="hi-val">${dados.length}</div></div>
          <div class="hdr-item"><div class="hi-label">Ano</div><div class="hi-val">${State.ano}</div></div>
          <div class="hdr-item"><div class="hi-label">Emitido em</div><div class="hi-val">${new Date().toLocaleDateString("pt-BR")}</div></div>
        </div>
      </div>
      <div class="melhor">
        <div class="trofeu">🏆</div>
        <div>
          <div class="ml-lbl">Funcionário do Ano ${State.ano}</div>
          <div class="ml-nome">${melhor.nome}</div>
          <div class="ml-sub">Melhor saldo de horas &nbsp;·&nbsp; ${melhor.tTrab} dias trabalhados &nbsp;·&nbsp; ${minutesToStr(melhor.tH)} totais</div>
        </div>
      </div>
      <div class="section-title">▌ Rankings do Ano</div>
      <div class="rank-wrap">
        ${rankTable("⏱ Mais Horas Trabalhadas", byHoras, r=>minutesToStr(r.tH))}
        ${rankTable("📈 Melhor Saldo", bySaldo, r=>(r.tE>=0?"+":"")+minutesToStr(r.tE))}
        ${rankTable("📅 Mais Dias Trabalhados", byDias, r=>r.tTrab+" dias")}
        ${rankTable("🌙 Mais Horas Noturnas", byNot, r=>r.tNot>0?minutesToStr(r.tNot):"—")}
      </div>
      <div class="footer">Ranking gerado automaticamente — ${new Date().toLocaleDateString("pt-BR")}</div>
    </div>`;
  }

  _relAbrir(`Relatório Anual ${State.ano}${dados.length===1?" — "+dados[0].nome:" — Todos"}`, corpo);
}
