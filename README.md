# 🕐 Sistema de Cartão Ponto

Sistema web local para controle de ponto, com **leitura automática de cartões por OCR**,
**relatórios mensais/anuais** prontos para impressão (A4) e um **assistente de IA** que
responde perguntas em linguagem natural sobre os dados.

Funciona 100% offline na máquina (servidor local em Python + interface no navegador).
Os dados ficam salvos em um único arquivo JSON — sem banco de dados externo.

---

## 📑 Índice
- [Principais recursos](#-principais-recursos)
- [Como rodar (desenvolvimento)](#-como-rodar-desenvolvimento)
- [Gerar o pacote para o cliente](#-gerar-o-pacote-para-o-cliente)
- [Como o cliente usa](#-como-o-cliente-usa)
- [Estrutura do projeto](#-estrutura-do-projeto)
- [Funcionalidades em detalhe](#-funcionalidades-em-detalhe)
  - [Cartão ponto e cálculos](#cartão-ponto-e-cálculos)
  - [Configuração de horários (escala)](#configuração-de-horários-escala)
  - [OCR — leitura de cartões](#ocr--leitura-de-cartões)
  - [Relatórios](#relatórios)
  - [Importar / Exportar](#importar--exportar)
  - [Assistente de IA (Ollama)](#assistente-de-ia-ollama)
- [Formato dos dados](#-formato-dos-dados)
- [Solução de problemas](#-solução-de-problemas)
- [Segurança](#-segurança)

---

## ✨ Principais recursos

- **Cartão ponto por funcionário/mês** com cálculo automático de total, saldo (horas extras / a menos) e adicional noturno.
- **Escala por dia da semana** configurável (Seg–Qui 9h, Sex 8h, etc.), com carga prevista automática.
- **Feriados** (todas as horas contam como extra) e **sábado** (100% extra).
- **OCR** — lê fotos/scans de cartões **DATAPRINT** (frente e verso) com PaddleOCR e preenche os horários.
- **Relatórios A4** prontos para imprimir/PDF: mensal e anual, individual ou de todos, com **ranking "Funcionário do Ano"**.
- **Importar/Exportar** banco de dados em JSON (compatível com a versão antiga do sistema).
- **Assistente de IA** (Ollama) que responde perguntas como *"quantas horas extras o Ademir fez nas segundas-feiras?"*.
- **Pacote portátil** — roda na máquina do cliente sem instalar nada.

---

## 🚀 Como rodar (desenvolvimento)

Pré-requisito: **Python 3.11**.

```bash
# 1. Instalar dependências (uma vez)
pip install -r requirements.txt

# 2. Iniciar o servidor
python main.py
```

O navegador abre sozinho em **http://localhost:8000**.

> No Windows também dá para dar duplo-clique em **`iniciar.bat`**.

### Dependências (versões fixas e compatíveis)
> ⚠️ As versões são sensíveis: `numpy` **deve** ser 1.26.x e `opencv-python` 4.6.x,
> senão o PaddleOCR quebra (conflito de ABI). Sempre use `pip install -r requirements.txt`.

---

## 📦 Gerar o pacote para o cliente

O cliente recebe uma **pasta portátil** com o Python embutido — não precisa instalar nada.

**Forma fácil:** duplo-clique em **`EMPACOTAR.bat`**. Ele:
1. Baixa o Python embutido
2. Instala todas as dependências
3. Copia o sistema
4. Compacta em `CONTROLE_DE_PONTO_PORTATIL.zip`

O resultado (~357 MB) é o arquivo que você envia (WeTransfer, Google Drive, etc.).

> Para regerar só após mudar o **código** (sem mexer nas dependências), basta recopiar
> `main.py`, `backend/` e `frontend/` para dentro de `CONTROLE_DE_PONTO_PORTATIL/app/` e recompactar.

---

## 👤 Como o cliente usa

1. Descompacta o `CONTROLE_DE_PONTO_PORTATIL.zip` em qualquer lugar.
2. Dá **duplo-clique em `INICIAR.vbs`**.
3. O navegador abre sozinho — pronto.

Os dados ficam em `app\database\ponto.json` e são salvos automaticamente a cada alteração.

---

## 🗂 Estrutura do projeto

```
CONTROLE DE PONTO/
├── main.py                     # Servidor FastAPI (ponto de entrada)
├── requirements.txt            # Dependências (versões fixas)
├── iniciar.bat                 # Roda o sistema na máquina de dev
├── EMPACOTAR.bat               # Gera o pacote portátil + zip
├── empacotar_portavel.ps1      # Script de empacotamento (chamado pelo .bat)
├── INICIAR.vbs                 # Lançador dentro do pacote portátil
│
├── backend/
│   ├── storage.py              # Leitura/escrita do ponto.json + escala padrão
│   ├── utils/
│   │   ├── calculations.py     # Cálculo de total, saldo, noturno, previsto
│   │   └── exporters.py        # Exportação Excel/CSV/JSON
│   ├── ocr/
│   │   ├── processor.py        # Pré-processamento de imagem (OpenCV)
│   │   └── extractor.py        # Detecção da grade + leitura (PaddleOCR/Tesseract)
│   └── routes/
│       ├── funcionarios.py     # CRUD de funcionários
│       ├── registros.py        # Registros de ponto + dashboard + anual
│       ├── feriados.py         # Feriados
│       ├── config_route.py     # Configurações (escala, noturno, etc.)
│       ├── ocr_route.py        # Processamento OCR (1 ou 2 faces)
│       ├── importar.py         # Importa JSON do formato antigo → novo
│       ├── exportar.py         # Exporta no formato antigo
│       ├── backup_route.py     # Backup completo do banco
│       ├── state_route.py      # Estado (compat. com a versão antiga)
│       └── ia_route.py         # Integração com LLM (Ollama)
│
├── frontend/
│   ├── index.html              # Interface (SPA)
│   ├── css/style.css           # Tema escuro
│   └── js/
│       ├── app.js              # Lógica principal da interface
│       ├── api.js              # Cliente da API REST
│       ├── reports.js          # Geração dos relatórios A4
│       └── utils.js            # Funções utilitárias
│
├── database/                   # ponto.json (dados) — NÃO versionado
├── uploads/                    # Imagens enviadas ao OCR — NÃO versionado
└── exports/                    # Planilhas geradas — NÃO versionado
```

---

## 🔧 Funcionalidades em detalhe

### Cartão ponto e cálculos
- Cada funcionário tem uma tabela mensal com **Entrada · Início Intervalo · Fim Intervalo · Saída**.
- O sistema calcula automaticamente:
  - **Total** trabalhado no dia (descontando o almoço)
  - **Previsto** (conforme a escala do dia da semana)
  - **Saldo** = total − previsto (positivo = hora extra; negativo = hora devida)
  - **Adicional noturno** (horas após 22:00, configurável)
- **Feriado**: todas as horas contam como extra.
- **Sábado sem escala**: todas as horas contam como extra (sem almoço fantasma).

### Configuração de horários (escala)
Em **⚙ Configurações**:
- Tabela por dia da semana (Dom–Sáb), com Ativo, Entrada, Intervalo, Saída e **Carga Prevista** automática.
- **Início do adicional noturno** e **percentual de extra em feriado**.
- Botões **Salvar Configuração** e **Restaurar Padrão**.
- Ao salvar, os registros existentes são **recalculados** com a nova escala.

### OCR — leitura de cartões
Página **🔍 Importar OCR**:
- Aceita **JPG, PNG, PDF, TIFF**. O cartão DATAPRINT tem 2 faces:
  - **Face 1** = dias 1–15
  - **Face 2** = dias 16–31
- O sistema detecta a **grade da tabela** (por saturação de cor), recorta as células e lê com **PaddleOCR**.
- Usa o **número do dia carimbado** como âncora e remove o prefixo ("18 6:58" → 06:58).
- Campos com **baixa confiança** ficam destacados para revisão antes de importar.
- Botão **🤖 Tentar com IA (experimental)** — usa um modelo de visão (LLM). *Lê pior que o OCR em geral; requer modelo com visão configurado.*

> Dica: scanner (150+ DPI), imagem reta e nítida → melhor resultado.

### Relatórios
Tudo em **A4 retrato**, com botão "Imprimir / Salvar PDF":
- **Mensal individual** — tabela diária, totais, resumo, legenda e assinaturas.
- **Mensal — Todos** — um por página.
- **Anual individual** — 12 meses, indicadores e destaques.
- **Anual — Todos** — inclui página de **Ranking** com 🏆 **Funcionário do Ano** e rankings de horas/saldo/dias/noturno.

Acesso pelo botão **📋 Relatórios** (topo) ou pelo menu **⚙ Ações** de cada funcionário.

### Importar / Exportar
- **Importar JSON / Importar Banco de Dados** — lê o formato do sistema antigo (`meses["ano-M"]`, `inicioInt`/`fimInt`) e converte para o novo, recalculando tudo.
- **Exportar Banco de Dados** — gera um JSON no mesmo formato antigo (compatível e reimportável).
- **Exportar Excel/CSV/JSON** por funcionário no mês.

### Assistente de IA (Ollama)
Página **🤖 Assistente IA** + configuração em **⚙ Configurações**:
- Informe **Endpoint** (ex.: `https://ollama.com/v1`), **API Key** e **Modelo**.
- Pergunte em linguagem natural: *"quem fez mais horas extras este ano?"*, *"some o noturno do Ademir em maio"*.
- A IA recebe o **detalhe diário** (com dia da semana), então responde por dia da semana, período, feriado, etc.
- **Fracionamento automático (map-reduce)**: com muitos funcionários, divide os dados em blocos, analisa cada um e consolida em **uma resposta final**.

---

## 🧾 Formato dos dados

Tudo fica em `database/ponto.json`:

```jsonc
{
  "funcionarios": [
    { "id": 1, "nome": "ADEMIR", "jornada": "07:00-17:30",
      "int_inicio": "11:30", "int_fim": "13:00", "ativo": true }
  ],
  "registros": {
    "1": {
      "2026-05-04": {
        "entrada": "06:58", "inicio_intervalo": "11:30",
        "fim_intervalo": "12:13", "saida": "21:37",
        "total_min": 836, "previsto_min": 540, "saldo_min": 296,
        "noturno_min": null, "feriado": 0, "dia_semana": 0
      }
    }
  },
  "feriados": { "2026-05-01": "" },
  "config": {
    "noturno_inicio": "22:00",
    "feriado_rate": "50",
    "schedule": { "0": {...}, "1": {...}, "...": {} },
    "ia_base_url": "https://ollama.com/v1",
    "ia_model": "gpt-oss:120b:cloud"
    /* ia_api_key fica aqui também, mas NUNCA vai no pacote */
  }
}
```

---

## 🛠 Solução de problemas

| Problema | Causa / Solução |
|---|---|
| **`.ps1` abre no bloco de notas** | Normal. Use **`EMPACOTAR.bat`** (duplo-clique) ou botão direito → "Executar com PowerShell". |
| **OCR não lê** | Use scanner (150+ DPI), imagem reta. Foto de celular costuma falhar. |
| **OCR sem modelos** | Na 1ª leitura o PaddleOCR baixa os modelos (precisa de internet uma vez). |
| **`paddle`/`numpy` quebrado** | Versões erradas. Reinstale com `pip install -r requirements.txt` (numpy 1.26 + opencv 4.6). |
| **IA responde "(sem resposta)"** | Já tratado (mais tokens + fallback de reasoning). Reformule a pergunta se persistir. |
| **IA: leitura de cartão falha** | O modelo precisa ter **visão** (ex.: `llama3.2-vision`). `gpt-oss` é só texto. |
| **Porta 8000 ocupada** | Feche outra instância do sistema (ou `python.exe` no Gerenciador de Tarefas). |

---

## 🔒 Segurança

- A **chave da API de IA** fica em `database/ponto.json` (local). **Não é incluída** no pacote enviado ao cliente — cada um cadastra a sua.
- O `.gitignore` impede subir dados, imagens, pacotes e chaves para o repositório.
- Se uma chave for exposta acidentalmente, **gere uma nova e revogue a antiga** no provedor.

---

*Sistema de uso local — desenvolvido para automatizar o controle de ponto do RH.*
