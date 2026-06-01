"""
Módulo de banco de dados SQLite.
Gerencia criação de tabelas e conexão.
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "database" / "ponto.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Cria todas as tabelas se não existirem."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS funcionarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT    NOT NULL,
            matricula   TEXT    UNIQUE,
            cargo       TEXT,
            jornada     TEXT    DEFAULT '07:00-17:00',
            int_inicio  TEXT    DEFAULT '12:00',
            int_fim     TEXT    DEFAULT '13:00',
            ativo       INTEGER DEFAULT 1,
            criado_em   TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS registros (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id      INTEGER NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
            data                TEXT    NOT NULL,
            entrada             TEXT,
            inicio_intervalo    TEXT,
            fim_intervalo       TEXT,
            saida               TEXT,
            total_min           INTEGER,
            previsto_min        INTEGER,
            saldo_min           INTEGER,
            noturno_min         INTEGER,
            feriado             INTEGER DEFAULT 0,
            conf_entrada        REAL    DEFAULT 1.0,
            conf_saida          REAL    DEFAULT 1.0,
            conf_ini_int        REAL    DEFAULT 1.0,
            conf_fim_int        REAL    DEFAULT 1.0,
            fonte               TEXT    DEFAULT 'manual',
            criado_em           TEXT    DEFAULT (datetime('now','localtime')),
            UNIQUE(funcionario_id, data)
        );

        CREATE TABLE IF NOT EXISTS feriados (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            data    TEXT    NOT NULL UNIQUE,
            nome    TEXT
        );

        CREATE TABLE IF NOT EXISTS configuracoes (
            chave   TEXT PRIMARY KEY,
            valor   TEXT
        );

        CREATE TABLE IF NOT EXISTS ocr_templates (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        TEXT    NOT NULL,
            layout_json TEXT,
            criado_em   TEXT    DEFAULT (datetime('now','localtime'))
        );
    """)

    # Configurações padrão
    defaults = [
        ("noturno_inicio", "22:00"),
        ("noturno_fim",    "05:00"),
        ("he_50_pct",      "50"),
        ("he_100_pct",     "100"),
        ("conf_minima",    "0.65"),
    ]
    for chave, valor in defaults:
        cur.execute(
            "INSERT OR IGNORE INTO configuracoes(chave,valor) VALUES(?,?)",
            (chave, valor),
        )

    conn.commit()
    conn.close()
