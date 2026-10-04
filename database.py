import os
import re
import json
import shutil
import sqlite3
from datetime import datetime, date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "sistema_terra.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def get_db_connection(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def parse_money(val):
    if val is None or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    s = s.replace("R$", "").replace(" ", "")
    if not s:
        return 0.0
    # Se possui vírgula e ponto (ex: 1.234,56)
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def format_money_br(val):
    try:
        v = float(val or 0.0)
    except (ValueError, TypeError):
        v = 0.0
    formatted = f"{v:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def parse_date_iso(val):
    if not val:
        return date.today().isoformat()
    s = str(val).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    if re.match(r"^\d{2}/\d{2}/\d{4}$", s):
        d, m, y = s.split("/")
        return f"{y}-{m}-{d}"
    try:
        return datetime.fromisoformat(s[:10]).date().isoformat()
    except Exception:
        return date.today().isoformat()


def format_date_br(val):
    if not val:
        return ""
    s = str(val).strip()[:10]
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        y, m, d = s.split("-")
        return f"{d}/{m}/{y}"
    return s


def format_date_short(val):
    if not val:
        return ""
    s = str(val).strip()[:10]
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        y, m, d = s.split("-")
        return f"{d}/{m}"
    return s


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        );

        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cnpj TEXT DEFAULT '',
            apelidos TEXT DEFAULT '',
            telefone TEXT DEFAULT '',
            rua_bairro TEXT DEFAULT '',
            cidade TEXT DEFAULT '',
            fatura_anterior REAL DEFAULT 0.0,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_cliente_nome ON clientes(nome);

        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            pasta_hotfolder TEXT DEFAULT '',
            estoque_inicial INTEGER DEFAULT 0,
            estoque_atual INTEGER DEFAULT 0,
            estoque_consumido INTEGER DEFAULT 0,
            data_cadastro TEXT,
            preco REAL DEFAULT 0.0,
            valor_compra REAL DEFAULT 0.0,
            anotacoes TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_produto_nome ON produtos(nome);

        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NULL,
            cliente_nome_original TEXT DEFAULT '',
            identificado INTEGER DEFAULT 1,
            origem TEXT DEFAULT 'manual',
            data_lancamento TEXT NOT NULL,
            valor_entrega REAL DEFAULT 0.0,
            valor_pagamento REAL DEFAULT 0.0,
            fatura_anterior REAL DEFAULT 0.0,
            pagamento_fatura_anterior REAL DEFAULT 0.0,
            saldo_fatura_anterior REAL DEFAULT 0.0,
            observacao TEXT DEFAULT '',
            data_registro TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE RESTRICT ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_lancamento_data ON lancamentos(data_lancamento);
        CREATE INDEX IF NOT EXISTS idx_lancamento_cliente ON lancamentos(cliente_id);

        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lancamento_id INTEGER NOT NULL,
            produto_id INTEGER NULL,
            descricao TEXT DEFAULT '',
            quantidade INTEGER DEFAULT 1,
            valor REAL DEFAULT 0.0,
            cores_detectadas TEXT DEFAULT '',
            arquivos_origem TEXT DEFAULT '',
            pasta_origem TEXT DEFAULT '',
            FOREIGN KEY (lancamento_id) REFERENCES lancamentos(id) ON DELETE CASCADE ON UPDATE CASCADE,
            FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE RESTRICT ON UPDATE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_servico_lancamento ON servicos(lancamento_id);
        CREATE INDEX IF NOT EXISTS idx_servico_produto ON servicos(produto_id);

        CREATE TABLE IF NOT EXISTS arquivos_monitorados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caminho_completo TEXT UNIQUE,
            nome_arquivo TEXT,
            pasta_produto TEXT,
            chave_agrupamento TEXT,
            cor_detectada TEXT,
            pagina_detectada TEXT,
            lancamento_id INTEGER NULL,
            servico_id INTEGER NULL,
            data_lancamento TEXT,
            ignorado INTEGER NOT NULL DEFAULT 0,
            data_deteccao TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_arq_chave ON arquivos_monitorados(chave_agrupamento);

        CREATE TABLE IF NOT EXISTS lancamentos_caixa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            operacao TEXT NOT NULL,
            cliente_id INTEGER NULL,
            lancamento_id INTEGER NULL,
            origem TEXT DEFAULT 'manual',
            usuario TEXT DEFAULT 'sistema',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_caixa_data ON lancamentos_caixa(data);
        CREATE INDEX IF NOT EXISTS idx_caixa_operacao ON lancamentos_caixa(operacao);
        """
    )

    # Migrações leves para bancos existentes.
    try:
        cur.execute("ALTER TABLE arquivos_monitorados ADD COLUMN ignorado INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass

    # CNPJ foi adicionado depois da criação do banco. Mantém compatibilidade com
    # bancos SQLite já instalados, sem recriar nem perder dados dos clientes.
    colunas_clientes = {row["name"] for row in cur.execute("PRAGMA table_info(clientes)").fetchall()}
    if "cnpj" not in colunas_clientes:
        cur.execute("ALTER TABLE clientes ADD COLUMN cnpj TEXT DEFAULT ''")

    # Configurações padrão
    default_hotfolder_local = os.path.join(BASE_DIR, "hotfolder_output")
    defaults = {
        "hotfolder_network_path": r"\\RIPCTP\Manuela\OutPut",
        "hotfolder_local_path": default_hotfolder_local,
        "hotfolder_ativo": "1",
        "hotfolder_intervalo_seg": "5",
        "hotfolder_data_minima": "2026-10-01",
        "empresa_nome": "Terra Fotolito",
        "empresa_endereco": "Campinas de Pirajá, nº 24 - Pirajá - Salvador - Ba.",
        "empresa_telefone": "71 3242-6120",
        "empresa_email": "terrafotolitos@hotmail.com",
        "empresa_pix": "71 98221-8592 - Erilio Texerira L. Filho",
    }
    for k, v in defaults.items():
        cur.execute(
            "INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)",
            (k, v),
        )

    # Garante que hotfolder_local_path aponte para a pasta local real do sistema operacional atual (ex: Windows)
    row_local = cur.execute(
        "SELECT valor FROM configuracoes WHERE chave = 'hotfolder_local_path'"
    ).fetchone()
    if not row_local or not row_local[0] or row_local[0].startswith("/home/user"):
        if os.name == "nt" or not os.path.exists(row_local[0] if row_local else ""):
            cur.execute(
                "UPDATE configuracoes SET valor = ? WHERE chave = 'hotfolder_local_path'",
                (default_hotfolder_local,),
            )

    # Seed inicial a partir de 'Lancamentos 30_09_final.sql' caso exista e ainda não tenha sido carregado
    cur.execute("SELECT COUNT(*) FROM clientes")
    qtd_clientes = cur.fetchone()[0]
    sql_final_path = os.path.join(BASE_DIR, "Lancamentos 30_09_final.sql")
    if qtd_clientes < 30 and os.path.exists(sql_final_path):
        conn.commit()
        with open(sql_final_path, "r", encoding="utf-8", errors="replace") as f_sql:
            importar_dump_sql(f_sql.read(), conn=conn)
    elif qtd_clientes == 0:
        clientes_iniciais = [
            ("Falcao", "falcao", "(71) 99100-2545", "caji", "Lauro de Freitas", 0.0),
            ("Manuela", "manuela", "", "Estrada de Camp. Pirajá", "Salvador", 0.0),
            ("Exxograf", "exxograf, exograf", "", "Calçada", "Salvador", 0.0),
            ("Noel", "noel", "", "Pirajá", "Salvador", 0.0),
            ("Vangraf", "vangraf", "", "", "Feira de Santana", 0.0),
            ("Jacograf", "jacograf", "", "Centro", "Lauro de Freitas", 0.0),
            ("Norte Grafica", "nortegrafica, norte", "", "Caji", "Lauro de Freitas", 0.0),
            ("Gold", "gold", "", "Centro", "Feira de Santana", 0.0),
            ("CADS", "cads", "", "AV. MACHADO DE ASSIS N 85 - ALTO DO ALENCAR", "Juazeiro - Ba", 0.0),
            ("IPLAST", "iplast", "", "", "Sergipe", 0.0),
            ("Aqui Grafica", "aquigrafica, aqui", "", "Centro", "Lauro de Freitas", 0.0),
            ("Flavia", "flavia", "", "Centro", "Salvador", 0.0),
            ("Demerval", "demerval", "", "Marechal Rondon", "Salvador", 0.0),
            ("Jaelson", "jaelson", "", "Bonfim", "Salvador", 0.0),
            ("Sou Grafica", "sougrafica, sou", "", "", "Salvador", 0.0),
            ("Ribas", "ribas", "", "Via Expressa", "Salvador", 0.0),
            ("Perdas", "perdas", "", "-----", "Salvador", 0.0),
            ("Terra Fotolito", "terrafotolito, terra", "(71) 3242-6120", "Av. Estados Unidos, Edf. Wildberg, nº 18, sala 335", "Salvador", 0.0),
            ("Marinho", "marinho", "", "Calçada", "Salvador", 0.0),
            ("Impact", "impact", "", "Centro", "Alagoinhas", 0.0),
            ("Nordeste", "nordeste", "", "São Cristóvão", "Salvador", 0.0),
            ("Gilberto", "gilberto", "", "São Caetano", "Salvador", 0.0),
            ("PBA - embalagens", "pba, pbaembalagens", "", "Centro", "Salvador", 0.0),
            ("Fonte Viva", "fonteviva", "", "Av. Apolonio Sales, 1059", "Paulo Afonso", 0.0),
            ("Vilacy", "vilacy", "", "Centro", "Lauro de Freitas", 0.0),
            ("Gilson", "gilson", "", "Salvador", "Salvador", 0.0),
        ]
        cur.executemany(
            """
            INSERT INTO clientes (nome, apelidos, telefone, rua_bairro, cidade, fatura_anterior)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            clientes_iniciais,
        )

    # Seed inicial de produtos (Chapas) caso a tabela esteja vazia
    cur.execute("SELECT COUNT(*) FROM produtos")
    if cur.fetchone()[0] == 0:
        produtos_iniciais = [
            # (nome, pasta_hotfolder, estoque_inicial, estoque_atual, estoque_consumido, data_cadastro, preco, valor_compra, anotacoes)
            ("Adast", "660x530, Adast", 393, 94, 299, "2025-05-29", 40.00, 13.54, "Chapa 660x530 - Adast"),
            ("MO", "650x550, MO", 661, 514, 147, "2025-05-29", 40.00, 14.24, "Chapa 650x550 - MO"),
            ("GTO", "510x400, GTO", 537, 505, 32, "2025-05-29", 30.00, 8.83, "Chapa 510x400 - GTO"),
            ("Speed", "745x605, Speed", 300, 278, 22, "2025-05-29", 50.00, 18.30, "Chapa 745x605 - Speed"),
            ("521", "521", 368, 308, 60, "2025-05-29", 30.00, 9.28, "Chapa 521"),
            ("724", "724", 41, 3, 38, "2025-05-29", 50.00, 20.01, "Chapa 724"),
            ("Solna", "Solna", 432, 422, 10, "2025-05-29", 40.00, 12.20, "Chapa Solna"),
        ]
        cur.executemany(
            """
            INSERT INTO produtos (nome, pasta_hotfolder, estoque_inicial, estoque_atual, estoque_consumido, data_cadastro, preco, valor_compra, anotacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            produtos_iniciais,
        )

    # Seed inicial do caixa (importado de fluxo caixa_abril.sql)
    cur.execute("SELECT COUNT(*) FROM lancamentos_caixa")
    if cur.fetchone()[0] == 0:
        caixa_iniciais = [
            ("Serviços ctp", "2025-04-30", 3085.50, "receita", "sistema"),
            ("Pagamentos de serviços", "2025-04-30", 2000.00, "recebido", "sistema"),
            ("Salario Antonio Carlos", "2025-04-30", 1200.00, "despesa", "sistema"),
            ("Combustivel", "2025-03-29", 400.00, "despesa", "sistema"),
            ("Atendimento eletronico", "2025-03-29", 600.00, "despesa", "sistema"),
            ("Motoboy", "2025-04-29", 160.00, "despesa", "sistema"),
            ("Eletronico", "2025-04-29", 350.00, "despesa", "sistema"),
            ("Creditos para SR serviços", "2024-10-30", 28540.00, "transferido", "sistema"),
            ("Alimentaçao do eletronico", "2025-02-27", 150.00, "despesa", "sistema"),
            ("Combustivel", "2025-02-27", 554.00, "despesa", "sistema"),
            ("Atendimento do eletronico", "2025-02-27", 800.00, "despesa", "sistema"),
            ("Combustivel - visitas e entregas", "2025-01-29", 180.00, "despesa", "sistema"),
            ("Combustivel - visitas e entregas", "2024-12-29", 200.00, "despesa", "sistema"),
            ("Combustivel - visitas e entregas", "2024-10-29", 534.00, "despesa", "sistema"),
            ("Motoboy", "2025-01-29", 180.00, "despesa", "sistema"),
            ("Motoboy", "2024-12-19", 310.00, "despesa", "sistema"),
            ("Insumos - metassilicato", "2024-11-24", 110.00, "despesa", "sistema"),
            ("Motoboy", "2024-10-30", 300.00, "despesa", "sistema"),
            ("Retirada Erilio", "2024-12-29", 3000.00, "despesa", "sistema"),
            ("Salario Antonio Carlos", "2024-11-29", 1200.00, "despesa", "sistema"),
            ("Salario Gilson", "2024-10-29", 2000.00, "despesa", "sistema"),
            ("Salario Gilson", "2024-12-29", 2500.00, "despesa", "sistema"),
            ("Salario Gilson", "2025-01-29", 2500.00, "despesa", "sistema"),
            ("Salario Gilson", "2025-03-29", 2500.00, "despesa", "sistema"),
        ]
        cur.executemany(
            """
            INSERT INTO lancamentos_caixa (descricao, data, valor, operacao, usuario)
            VALUES (?, ?, ?, ?, ?)
            """,
            caixa_iniciais,
        )

    conn.commit()
    conn.close()


# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
def get_config():
    conn = get_db_connection()
    rows = conn.execute("SELECT chave, valor FROM configuracoes").fetchall()
    conn.close()
    return {r["chave"]: r["valor"] for r in rows}


def set_config(dados):
    conn = get_db_connection()
    with conn:
        for k, v in dados.items():
            conn.execute(
                "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) "
                "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                (k, str(v)),
            )
    conn.close()


# ==============================================================================
# CLIENTES
# ==============================================================================
def normalizar_cnpj(valor):
    """Guarda apenas os 14 dígitos do CNPJ, aceitando entrada com ou sem máscara."""
    return re.sub(r"\D", "", str(valor or ""))[:14]


def formatar_cnpj(valor):
    """Aplica a máscara brasileira ao CNPJ completo; preserva valores parciais."""
    bruto = str(valor or "").strip()
    digitos = normalizar_cnpj(bruto)
    if len(digitos) == 14:
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"
    return bruto


def listar_clientes(termo=None):
    conn = get_db_connection()
    if termo:
        like = f"%{termo}%"
        conditions = ["nome LIKE ?", "rua_bairro LIKE ?", "cidade LIKE ?", "apelidos LIKE ?"]
        params = [like, like, like, like]
        cnpj_termo = normalizar_cnpj(termo)
        if cnpj_termo:
            conditions.append("cnpj LIKE ?")
            params.append(f"%{cnpj_termo}%")
        rows = conn.execute(
            f"SELECT * FROM clientes WHERE {' OR '.join(conditions)} ORDER BY nome COLLATE NOCASE",
            params,
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM clientes ORDER BY nome COLLATE NOCASE"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_cliente(cliente_id):
    if not cliente_id:
        return None
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def criar_cliente(nome, telefone="", rua_bairro="", cidade="", fatura_anterior=0.0, apelidos="", cnpj=""):
    conn = get_db_connection()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO clientes (nome, cnpj, apelidos, telefone, rua_bairro, cidade, fatura_anterior)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome.strip(),
                normalizar_cnpj(cnpj),
                (apelidos or "").strip(),
                (telefone or "").strip(),
                (rua_bairro or "").strip(),
                (cidade or "").strip(),
                parse_money(fatura_anterior),
            ),
        )
        new_id = cur.lastrowid
    conn.close()
    return new_id


def atualizar_cliente(cliente_id, nome, telefone="", rua_bairro="", cidade="", fatura_anterior=None, apelidos=None, cnpj=None):
    conn = get_db_connection()
    old = buscar_cliente(cliente_id)
    if not old:
        conn.close()
        return False
    fat = old["fatura_anterior"] if fatura_anterior is None else parse_money(fatura_anterior)
    ap = old.get("apelidos", "") if apelidos is None else apelidos.strip()
    cnpj_valor = old.get("cnpj", "") if cnpj is None else normalizar_cnpj(cnpj)
    with conn:
        conn.execute(
            """
            UPDATE clientes
            SET nome = ?, cnpj = ?, apelidos = ?, telefone = ?, rua_bairro = ?, cidade = ?, fatura_anterior = ?
            WHERE id = ?
            """,
            (
                nome.strip(),
                cnpj_valor,
                ap,
                (telefone or "").strip(),
                (rua_bairro or "").strip(),
                (cidade or "").strip(),
                fat,
                int(cliente_id),
            ),
        )
    conn.close()
    return True


def excluir_cliente(cliente_id):
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM lancamentos WHERE cliente_id = ?", (cliente_id,)
    ).fetchone()[0]
    if count > 0:
        conn.close()
        return False, "Não é possível excluir um cliente que possui lançamentos registrados."
    with conn:
        conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.close()
    return True, "Cliente excluído com sucesso!"


# ==============================================================================
# PRODUTOS & ESTOQUE (INTEGRADOS)
# ==============================================================================
def listar_produtos():
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT
            id,
            nome,
            pasta_hotfolder,
            estoque_inicial,
            estoque_atual,
            estoque_consumido,
            (estoque_inicial - estoque_atual) AS consumo_calculado,
            data_cadastro,
            preco,
            valor_compra,
            anotacoes
        FROM produtos
        ORDER BY nome COLLATE NOCASE
        """
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        est_ini = int(d["estoque_inicial"] or 0)
        est_atu = int(d["estoque_atual"] or 0)
        # Mantém consistência do estoque_consumido
        consumido = int(d["estoque_consumido"] or max(0, est_ini - est_atu))
        d["estoque_consumido"] = consumido
        perc = round((est_atu / est_ini) * 100, 1) if est_ini > 0 else 0.0
        d["percentual_disponivel"] = perc
        if perc <= 10:
            d["status_estoque"] = "CRÍTICO"
        elif perc <= 20:
            d["status_estoque"] = "BAIXO"
        else:
            d["status_estoque"] = "OK"
        d["valor_estoque_inicial"] = round(est_ini * float(d["valor_compra"] or 0), 2)
        d["valor_estoque_atual"] = round(est_atu * float(d["valor_compra"] or 0), 2)
        d["custo_chapas_consumidas"] = round(consumido * float(d["valor_compra"] or 0), 2)
        result.append(d)
    return result


def buscar_produto(produto_id):
    if not produto_id:
        return None
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def criar_produto(nome, estoque_inicial, data_cadastro, preco, valor_compra, anotacoes="", pasta_hotfolder=""):
    est_ini = int(estoque_inicial or 0)
    dt = parse_date_iso(data_cadastro)
    pr = parse_money(preco)
    vc = parse_money(valor_compra)
    conn = get_db_connection()
    with conn:
        cur = conn.execute(
            """
            INSERT INTO produtos
            (nome, pasta_hotfolder, estoque_inicial, estoque_atual, estoque_consumido, data_cadastro, preco, valor_compra, anotacoes)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (
                nome.strip(),
                (pasta_hotfolder or "").strip(),
                est_ini,
                est_ini,
                dt,
                pr,
                vc,
                (anotacoes or "").strip(),
            ),
        )
        new_id = cur.lastrowid
    conn.close()
    return new_id


def atualizar_produto(produto_id, nome, estoque_inicial, data_cadastro, preco, valor_compra, anotacoes="", pasta_hotfolder=None, estoque_atual_override=None):
    conn = get_db_connection()
    old = conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    if not old:
        conn.close()
        return False
    est_ini = int(estoque_inicial or 0)
    old_ini = int(old["estoque_inicial"] or 0)
    old_atu = int(old["estoque_atual"] or 0)
    old_cons = int(old["estoque_consumido"] or max(0, old_ini - old_atu))

    if estoque_atual_override is not None and str(estoque_atual_override).strip() != "":
        novo_atu = int(estoque_atual_override)
        novo_cons = max(0, est_ini - novo_atu)
    else:
        if old_atu >= old_ini:
            novo_atu = est_ini
            novo_cons = 0
        else:
            consumo = old_ini - old_atu
            novo_atu = max(0, est_ini - consumo)
            novo_cons = consumo

    pasta = old["pasta_hotfolder"] if pasta_hotfolder is None else pasta_hotfolder.strip()
    dt = parse_date_iso(data_cadastro)
    pr = parse_money(preco)
    vc = parse_money(valor_compra)

    with conn:
        conn.execute(
            """
            UPDATE produtos
            SET nome = ?,
                pasta_hotfolder = ?,
                estoque_inicial = ?,
                estoque_atual = ?,
                estoque_consumido = ?,
                data_cadastro = ?,
                preco = ?,
                valor_compra = ?,
                anotacoes = ?
            WHERE id = ?
            """,
            (
                nome.strip(),
                pasta,
                est_ini,
                novo_atu,
                novo_cons,
                dt,
                pr,
                vc,
                (anotacoes or "").strip(),
                int(produto_id),
            ),
        )
    conn.close()
    return True


def movimentar_estoque_produto(produto_id, quantidade, tipo="entrada"):
    """
    Permite adicionar novas chapas ao estoque ('entrada'), registrar saída avulsa ('saida'),
    ou virar o mês igualando o estoque_inicial ao estoque_atual ('virar_mes').
    """
    conn = get_db_connection()
    p = conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    if not p:
        conn.close()
        return False
    qtd = int(quantidade or 0)
    with conn:
        if tipo == "entrada":
            novo_ini = int(p["estoque_inicial"] or 0) + qtd
            novo_atu = int(p["estoque_atual"] or 0) + qtd
            conn.execute(
                "UPDATE produtos SET estoque_inicial = ?, estoque_atual = ? WHERE id = ?",
                (novo_ini, novo_atu, int(produto_id)),
            )
        elif tipo == "saida":
            novo_atu = max(0, int(p["estoque_atual"] or 0) - qtd)
            novo_cons = int(p["estoque_consumido"] or 0) + qtd
            conn.execute(
                "UPDATE produtos SET estoque_atual = ?, estoque_consumido = ? WHERE id = ?",
                (novo_atu, novo_cons, int(produto_id)),
            )
        elif tipo == "virar_mes":
            atu = int(p["estoque_atual"] or 0)
            conn.execute(
                "UPDATE produtos SET estoque_inicial = ?, estoque_consumido = 0 WHERE id = ?",
                (atu, int(produto_id)),
            )
    conn.close()
    return True


def excluir_produto(produto_id):
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM servicos WHERE produto_id = ?", (produto_id,)
    ).fetchone()[0]
    if count > 0:
        conn.close()
        return False, "Não é possível excluir um produto que está em uso em lançamentos."
    with conn:
        conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    conn.close()
    return True, "Produto excluído com sucesso!"


def listar_estoque_critico(limite_percentual=20):
    produtos = listar_produtos()
    criticos = []
    for p in produtos:
        if p["percentual_disponivel"] <= limite_percentual:
            criticos.append(
                {
                    "id": p["id"],
                    "nome": p["nome"],
                    "estoque_inicial": p["estoque_inicial"],
                    "estoque_atual": p["estoque_atual"],
                    "consumo_real": p["estoque_consumido"],
                    "percentual": p["percentual_disponivel"],
                    "status": "ESTOQUE CRÍTICO" if p["percentual_disponivel"] <= 10 else "ESTOQUE BAIXO",
                    "preco": p["preco"],
                    "valor_compra": p["valor_compra"],
                }
            )
    criticos.sort(key=lambda x: x["percentual"])
    return criticos


# ==============================================================================
# LANÇAMENTOS E SERVIÇOS
# ==============================================================================
def _sincronizar_pagamento_caixa(conn, lancamento_id, cliente_id, data_lancamento, valor_pagamento, pagamento_fatura_anterior):
    """
    Mantém o módulo de Caixa sincronizado com os pagamentos lançados nos lançamentos de clientes.
    """
    conn.execute(
        "DELETE FROM lancamentos_caixa WHERE lancamento_id = ? AND origem = 'lancamento_cliente'",
        (lancamento_id,),
    )
    total_pgto = float(valor_pagamento or 0.0) + float(pagamento_fatura_anterior or 0.0)
    if total_pgto > 0:
        cliente_nome = "Cliente"
        if cliente_id:
            row_c = conn.execute("SELECT nome FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
            if row_c:
                cliente_nome = row_c["nome"]
        desc = f"Pagtº Cliente: {cliente_nome} (Lanç. #{lancamento_id})"
        conn.execute(
            """
            INSERT INTO lancamentos_caixa (descricao, data, valor, operacao, cliente_id, lancamento_id, origem, usuario)
            VALUES (?, ?, ?, 'recebido', ?, ?, 'lancamento_cliente', 'sistema')
            """,
            (desc, data_lancamento, total_pgto, cliente_id, lancamento_id),
        )


def criar_lancamento(dados):
    conn = get_db_connection()
    try:
        with conn:
            cliente_id = dados.get("cliente_id")
            if cliente_id in ("", "null", "None", 0, "0", None):
                cliente_id = None
            else:
                cliente_id = int(cliente_id)

            identificado = 1 if cliente_id is not None else 0
            cliente_nome_original = (dados.get("cliente_nome_original") or "").strip()
            origem = dados.get("origem") or "manual"
            data_lancamento = parse_date_iso(dados.get("data_lancamento"))
            valor_entrega = parse_money(dados.get("valor_entrega", 0))
            valor_pagamento = parse_money(dados.get("valor_pagamento", 0))
            fatura_anterior = parse_money(dados.get("fatura_anterior", 0))
            pagamento_fatura_anterior = parse_money(dados.get("pagamento_fatura_anterior", 0))
            saldo_fatura_anterior = fatura_anterior - pagamento_fatura_anterior
            observacao = (dados.get("observacao") or "").strip()

            cur = conn.execute(
                """
                INSERT INTO lancamentos
                (cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                 valor_entrega, valor_pagamento, fatura_anterior, pagamento_fatura_anterior,
                 saldo_fatura_anterior, observacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cliente_id,
                    cliente_nome_original,
                    identificado,
                    origem,
                    data_lancamento,
                    valor_entrega,
                    valor_pagamento,
                    fatura_anterior,
                    pagamento_fatura_anterior,
                    saldo_fatura_anterior,
                    observacao,
                ),
            )
            lancamento_id = cur.lastrowid

            servicos = dados.get("servicos") or []
            for s in servicos:
                descricao = (s.get("descricao") or "").strip()
                quantidade = int(s.get("quantidade") or 0)
                prod_raw = s.get("produto_id")
                produto_id = int(prod_raw) if (prod_raw not in ("", "null", "None", None) and str(prod_raw).isdigit()) else None
                valor = parse_money(s.get("valor", 0))
                cores = (s.get("cores_detectadas") or "").strip()
                arquivos = (s.get("arquivos_origem") or "").strip()
                pasta_origem = (s.get("pasta_origem") or "").strip()

                conn.execute(
                    """
                    INSERT INTO servicos
                    (lancamento_id, produto_id, descricao, quantidade, valor, cores_detectadas, arquivos_origem, pasta_origem)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lancamento_id,
                        produto_id,
                        descricao,
                        quantidade,
                        valor,
                        cores,
                        arquivos,
                        pasta_origem,
                    ),
                )

                if produto_id is not None and quantidade > 0:
                    conn.execute(
                        """
                        UPDATE produtos
                        SET estoque_atual = estoque_atual - ?,
                            estoque_consumido = estoque_consumido + ?
                        WHERE id = ?
                        """,
                        (quantidade, quantidade, produto_id),
                    )

            _sincronizar_pagamento_caixa(
                conn,
                lancamento_id,
                cliente_id,
                data_lancamento,
                valor_pagamento,
                pagamento_fatura_anterior,
            )
        conn.close()
        return lancamento_id
    except Exception as e:
        conn.close()
        raise e


def atualizar_lancamento(lancamento_id, dados):
    conn = get_db_connection()
    try:
        with conn:
            lancamento_id = int(lancamento_id)
            old_lanc = conn.execute(
                "SELECT * FROM lancamentos WHERE id = ?", (lancamento_id,)
            ).fetchone()
            if not old_lanc:
                return False

            cliente_id = dados.get("cliente_id")
            if cliente_id in ("", "null", "None", 0, "0", None):
                cliente_id = None
            else:
                cliente_id = int(cliente_id)

            identificado = 1 if cliente_id is not None else 0
            cliente_nome_original = dados.get(
                "cliente_nome_original", old_lanc["cliente_nome_original"]
            )
            data_lancamento = parse_date_iso(dados.get("data_lancamento"))
            valor_entrega = parse_money(dados.get("valor_entrega", 0))
            valor_pagamento = parse_money(dados.get("valor_pagamento", 0))
            fatura_anterior = parse_money(dados.get("fatura_anterior", 0))
            pagamento_fatura_anterior = parse_money(dados.get("pagamento_fatura_anterior", 0))
            saldo_fatura_anterior = fatura_anterior - pagamento_fatura_anterior
            observacao = (dados.get("observacao") or "").strip()

            conn.execute(
                """
                UPDATE lancamentos
                SET cliente_id = ?,
                    cliente_nome_original = ?,
                    identificado = ?,
                    data_lancamento = ?,
                    valor_entrega = ?,
                    valor_pagamento = ?,
                    fatura_anterior = ?,
                    pagamento_fatura_anterior = ?,
                    saldo_fatura_anterior = ?,
                    observacao = ?
                WHERE id = ?
                """,
                (
                    cliente_id,
                    cliente_nome_original,
                    identificado,
                    data_lancamento,
                    valor_entrega,
                    valor_pagamento,
                    fatura_anterior,
                    pagamento_fatura_anterior,
                    saldo_fatura_anterior,
                    observacao,
                    lancamento_id,
                ),
            )

            # Estorna estoque dos serviços antigos antes de substituir
            servicos_antigos = conn.execute(
                "SELECT * FROM servicos WHERE lancamento_id = ?", (lancamento_id,)
            ).fetchall()
            for sa in servicos_antigos:
                if sa["produto_id"] is not None and sa["quantidade"] > 0:
                    conn.execute(
                        """
                        UPDATE produtos
                        SET estoque_atual = estoque_atual + ?,
                            estoque_consumido = MAX(0, estoque_consumido - ?)
                        WHERE id = ?
                        """,
                        (sa["quantidade"], sa["quantidade"], sa["produto_id"]),
                    )

            conn.execute("DELETE FROM servicos WHERE lancamento_id = ?", (lancamento_id,))

            servicos = dados.get("servicos") or []
            for s in servicos:
                descricao = (s.get("descricao") or "").strip()
                quantidade = int(s.get("quantidade") or 0)
                prod_raw = s.get("produto_id")
                produto_id = int(prod_raw) if (prod_raw not in ("", "null", "None", None) and str(prod_raw).isdigit()) else None
                valor = parse_money(s.get("valor", 0))
                cores = (s.get("cores_detectadas") or "").strip()
                arquivos = (s.get("arquivos_origem") or "").strip()
                pasta_origem = (s.get("pasta_origem") or "").strip()

                conn.execute(
                    """
                    INSERT INTO servicos
                    (lancamento_id, produto_id, descricao, quantidade, valor, cores_detectadas, arquivos_origem, pasta_origem)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lancamento_id,
                        produto_id,
                        descricao,
                        quantidade,
                        valor,
                        cores,
                        arquivos,
                        pasta_origem,
                    ),
                )

                if produto_id is not None and quantidade > 0:
                    conn.execute(
                        """
                        UPDATE produtos
                        SET estoque_atual = estoque_atual - ?,
                            estoque_consumido = estoque_consumido + ?
                        WHERE id = ?
                        """,
                        (quantidade, quantidade, produto_id),
                    )

            _sincronizar_pagamento_caixa(
                conn,
                lancamento_id,
                cliente_id,
                data_lancamento,
                valor_pagamento,
                pagamento_fatura_anterior,
            )
        conn.close()
        return True
    except Exception as e:
        conn.close()
        raise e


def atribuir_cliente_lancamento(lancamento_id, cliente_id, salvar_apelido=False):
    conn = get_db_connection()
    with conn:
        lanc = conn.execute(
            "SELECT * FROM lancamentos WHERE id = ?", (int(lancamento_id),)
        ).fetchone()
        cli = conn.execute(
            "SELECT * FROM clientes WHERE id = ?", (int(cliente_id),)
        ).fetchone()
        if not lanc or not cli:
            conn.close()
            return False

        fatura_anterior = float(cli["fatura_anterior"] or 0.0)
        pgto_ant = float(lanc["pagamento_fatura_anterior"] or 0.0)
        saldo_ant = fatura_anterior - pgto_ant

        conn.execute(
            """
            UPDATE lancamentos
            SET cliente_id = ?,
                identificado = 1,
                fatura_anterior = CASE WHEN fatura_anterior = 0 THEN ? ELSE fatura_anterior END,
                saldo_fatura_anterior = CASE WHEN fatura_anterior = 0 THEN ? ELSE saldo_fatura_anterior END
            WHERE id = ?
            """,
            (int(cliente_id), fatura_anterior, saldo_ant, int(lancamento_id)),
        )

        if salvar_apelido and lanc["cliente_nome_original"]:
            novo_ap = lanc["cliente_nome_original"].strip().lower()
            atuais = [a.strip() for a in (cli["apelidos"] or "").split(",") if a.strip()]
            if novo_ap and novo_ap not in [a.lower() for a in atuais]:
                atuais.append(novo_ap)
                conn.execute(
                    "UPDATE clientes SET apelidos = ? WHERE id = ?",
                    (", ".join(atuais), int(cliente_id)),
                )

        _sincronizar_pagamento_caixa(
            conn,
            int(lancamento_id),
            int(cliente_id),
            lanc["data_lancamento"],
            lanc["valor_pagamento"],
            lanc["pagamento_fatura_anterior"],
        )
    conn.close()
    return True


def excluir_lancamento(lancamento_id):
    conn = get_db_connection()
    try:
        with conn:
            lancamento_id = int(lancamento_id)
            servicos = conn.execute(
                "SELECT * FROM servicos WHERE lancamento_id = ?", (lancamento_id,)
            ).fetchall()
            for s in servicos:
                if s["produto_id"] is not None and s["quantidade"] > 0:
                    conn.execute(
                        """
                        UPDATE produtos
                        SET estoque_atual = estoque_atual + ?,
                            estoque_consumido = MAX(0, estoque_consumido - ?)
                        WHERE id = ?
                        """,
                        (s["quantidade"], s["quantidade"], s["produto_id"]),
                    )
            # Marca arquivos do Hot Folder como ignorados para não serem reimportados automaticamente após exclusão manual
            try:
                conn.execute("ALTER TABLE arquivos_monitorados ADD COLUMN ignorado INTEGER NOT NULL DEFAULT 0")
            except Exception:
                pass
            conn.execute(
                """
                UPDATE arquivos_monitorados
                SET ignorado = 1, lancamento_id = NULL, servico_id = NULL
                WHERE lancamento_id = ?
                """,
                (lancamento_id,),
            )
            conn.execute(
                "DELETE FROM lancamentos_caixa WHERE lancamento_id = ? AND origem = 'lancamento_cliente'",
                (lancamento_id,),
            )
            conn.execute("DELETE FROM servicos WHERE lancamento_id = ?", (lancamento_id,))
            conn.execute("DELETE FROM lancamentos WHERE id = ?", (lancamento_id,))
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao excluir lancamento {lancamento_id}: {e}")
        conn.close()
        return False


def excluir_servico_diario(servico_id, lancamento_id=None):
    """
    Exclui um serviço específico na tela de Lançamento Diário.
    Se o lançamento possuir apenas esse serviço (ou ficar sem serviços), exclui o lançamento inteiro.
    Se possuir múltiplos serviços, exclui apenas a linha clicada e preserva os demais serviços do lançamento.
    Marca arquivos monitorados correspondentes como ignorados (ignorado=1) para não reimportar do Hot Folder.
    """
    conn = get_db_connection()
    try:
        try:
            conn.execute("ALTER TABLE arquivos_monitorados ADD COLUMN ignorado INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass

        if servico_id and int(servico_id) > 0:
            servico_id = int(servico_id)
            serv = conn.execute(
                "SELECT * FROM servicos WHERE id = ?", (servico_id,)
            ).fetchone()
            if serv:
                lanc_id = serv["lancamento_id"]
                qtd_servs = conn.execute(
                    "SELECT COUNT(*) FROM servicos WHERE lancamento_id = ?",
                    (lanc_id,),
                ).fetchone()[0]

                if qtd_servs <= 1:
                    conn.close()
                    return excluir_lancamento(lanc_id)

                with conn:
                    if serv["produto_id"] is not None and serv["quantidade"] > 0:
                        conn.execute(
                            """
                            UPDATE produtos
                            SET estoque_atual = estoque_atual + ?,
                                estoque_consumido = MAX(0, estoque_consumido - ?)
                            WHERE id = ?
                            """,
                            (serv["quantidade"], serv["quantidade"], serv["produto_id"]),
                        )
                    conn.execute(
                        """
                        UPDATE arquivos_monitorados
                        SET ignorado = 1, lancamento_id = NULL, servico_id = NULL
                        WHERE servico_id = ?
                        """,
                        (servico_id,),
                    )
                    conn.execute("DELETE FROM servicos WHERE id = ?", (servico_id,))
                conn.close()
                return True

        conn.close()
        if lancamento_id:
            return excluir_lancamento(int(lancamento_id))
        return False
    except Exception as e:
        print(f"Erro ao excluir servico diario {servico_id}: {e}")
        conn.close()
        return False


def buscar_lancamento(lancamento_id):
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT l.*, COALESCE(c.nome, 'Não Identificado') AS cliente_nome
        FROM lancamentos l
        LEFT JOIN clientes c ON l.cliente_id = c.id
        WHERE l.id = ?
        """,
        (int(lancamento_id),),
    ).fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    servs = conn.execute(
        """
        SELECT s.*, p.nome AS produto_nome, p.preco AS produto_preco
        FROM servicos s
        LEFT JOIN produtos p ON s.produto_id = p.id
        WHERE s.lancamento_id = ?
        ORDER BY s.id ASC
        """,
        (d["id"],),
    ).fetchall()
    d["servicos"] = [dict(s) for s in servs]
    conn.close()
    return d


def listar_lancamentos(filtros=None):
    filtros = filtros or {}
    conn = get_db_connection()
    conditions = []
    params = []

    if filtros.get("cliente_id") == "nao_identificado":
        conditions.append("(l.cliente_id IS NULL OR l.identificado = 0)")
    elif filtros.get("cliente_id"):
        conditions.append("l.cliente_id = ?")
        params.append(int(filtros["cliente_id"]))

    if filtros.get("apenas_identificados"):
        conditions.append("l.cliente_id IS NOT NULL")

    if filtros.get("data_inicio"):
        conditions.append("l.data_lancamento >= ?")
        params.append(parse_date_iso(filtros["data_inicio"]))

    if filtros.get("data_fim"):
        conditions.append("l.data_lancamento <= ?")
        params.append(parse_date_iso(filtros["data_fim"]))

    if filtros.get("data_exata"):
        conditions.append("l.data_lancamento = ?")
        params.append(parse_date_iso(filtros["data_exata"]))

    if filtros.get("texto_servico"):
        conditions.append(
            """
            (EXISTS (
                SELECT 1 FROM servicos s
                WHERE s.lancamento_id = l.id AND s.descricao LIKE ?
            ) OR l.cliente_nome_original LIKE ? OR l.observacao LIKE ?)
            """
        )
        like = f"%{filtros['texto_servico']}%"
        params.extend([like, like, like])

    if filtros.get("produto_id"):
        conditions.append(
            """
            EXISTS (
                SELECT 1 FROM servicos s
                WHERE s.lancamento_id = l.id AND s.produto_id = ?
            )
            """
        )
        params.append(int(filtros["produto_id"]))

    where_sql = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    order_sql = filtros.get("order_by", "l.data_lancamento ASC, l.id ASC")

    query = f"""
        SELECT l.*, COALESCE(c.nome, 'Não Identificado') AS cliente_nome
        FROM lancamentos l
        LEFT JOIN clientes c ON l.cliente_id = c.id
        {where_sql}
        ORDER BY {order_sql}
    """
    rows = conn.execute(query, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        servs = conn.execute(
            """
            SELECT s.*, p.nome AS produto_nome, p.preco AS produto_preco
            FROM servicos s
            LEFT JOIN produtos p ON s.produto_id = p.id
            WHERE s.lancamento_id = ?
            ORDER BY s.id ASC
            """,
            (d["id"],),
        ).fetchall()
        d["servicos"] = [dict(s) for s in servs]
        total_servicos = sum(float(s["valor"] or 0.0) for s in d["servicos"])
        total_qtd = sum(int(s["quantidade"] or 0) for s in d["servicos"])
        d["total_servicos"] = total_servicos
        d["total_quantidade"] = total_qtd
        d["saldo"] = total_servicos + float(d["valor_entrega"] or 0.0) - float(d["valor_pagamento"] or 0.0)
        result.append(d)
    conn.close()
    return result


def fechar_fatura_cliente(cliente_id, data_inicio=None, data_fim=None):
    """
    Fecha a fatura do cliente no período:
    1. Calcula o saldo devedor (serviços + entrega - pagamento + saldo_fatura_anterior).
    2. Atualiza o campo fatura_anterior do cliente com esse novo saldo devedor.
    3. Apaga os lançamentos e serviços do período SEM estornar o estoque (pois as chapas foram consumidas).
    """
    cliente_id = int(cliente_id)
    filtros = {"cliente_id": cliente_id}
    if data_inicio:
        filtros["data_inicio"] = parse_date_iso(data_inicio)
    if data_fim:
        filtros["data_fim"] = parse_date_iso(data_fim)

    lancamentos = listar_lancamentos(filtros)
    if not lancamentos:
        return False, "Nenhum lançamento encontrado para o cliente no período informado."

    conn = get_db_connection()
    try:
        try:
            conn.execute("ALTER TABLE arquivos_monitorados ADD COLUMN ignorado INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        with conn:
            cli = conn.execute(
                "SELECT * FROM clientes WHERE id = ?", (cliente_id,)
            ).fetchone()
            if not cli:
                return False, "Cliente não encontrado."

            fatura_anterior = float(cli["fatura_anterior"] or 0.0)
            total_servicos = 0.0
            total_entrega = 0.0
            total_pagamento = 0.0
            total_pagamento_fatura_anterior = 0.0

            ids_para_apagar = []
            for l in lancamentos:
                ids_para_apagar.append(l["id"])
                for s in l["servicos"]:
                    total_servicos += float(s["valor"] or 0.0)
                total_entrega += float(l["valor_entrega"] or 0.0)
                total_pagamento += float(l["valor_pagamento"] or 0.0)
                total_pagamento_fatura_anterior += float(l["pagamento_fatura_anterior"] or 0.0)

            saldo_fatura_anterior = fatura_anterior - total_pagamento_fatura_anterior
            saldo_devedor = (total_servicos + total_entrega - total_pagamento) + saldo_fatura_anterior

            conn.execute(
                "UPDATE clientes SET fatura_anterior = ? WHERE id = ?",
                (round(saldo_devedor, 2), cliente_id),
            )

            # Marca arquivos monitorados do período como ignorados para não reimportar do Hot Folder
            placeholders = ",".join("?" for _ in ids_para_apagar)
            conn.execute(
                f"UPDATE arquivos_monitorados SET ignorado = 1, lancamento_id = NULL, servico_id = NULL WHERE lancamento_id IN ({placeholders})",
                ids_para_apagar,
            )
            # Apaga os serviços e lançamentos SEM devolver estoque (chapas já foram consumidas)
            conn.execute(
                f"DELETE FROM servicos WHERE lancamento_id IN ({placeholders})",
                ids_para_apagar,
            )
            conn.execute(
                f"DELETE FROM lancamentos WHERE id IN ({placeholders})",
                ids_para_apagar,
            )

        conn.close()
        return True, round(saldo_devedor, 2)
    except Exception as e:
        conn.close()
        return False, str(e)


def realizar_virada_mes(data_corte=None, modo_limpeza="somente_hotfolder_mes_atual"):
    """
    Realiza a transição (virada de mês) de TODOS os clientes de uma só vez:
    1. Faz backup automático de segurança do banco atual em backups/.
    2. Calcula o saldo final de cada cliente até `data_corte`:
       nova_fatura_anterior = (servicos + entregas - pagamentos)
                              + (fatura_anterior_cadastrada - pgto_fatura_anterior)
       e grava esse valor em `clientes.fatura_anterior`, preservando eventual saldo credor.
    3. Limpa os lançamentos antigos (sem estornar o estoque de chapas já consumidas):
       - 'somente_hotfolder_mes_atual': limpa todos os lançamentos <= data_corte e qualquer lançamento manual antigo do SQL,
         mantendo apenas o que o Hot Folder coletou após data_corte (no novo mês).
       - 'manter_apos_corte': limpa todos os lançamentos <= data_corte e mantém todos os lançamentos (manuais e Hot Folder) após data_corte.
       - 'limpar_tudo': limpa todos os lançamentos para começar o mês zerado apenas com os saldos em Fatura Anterior.
    4. Atualiza a data mínima do Hot Folder (hotfolder_data_minima) para o dia seguinte a data_corte,
       evitando que arquivos antigos de meses anteriores na pasta do RIP sejam coletados.
    5. Não apaga nem altera `lancamentos_caixa`: o histórico financeiro permanece preservado.
    """
    if not data_corte:
        data_corte = (date.today().replace(day=1) - timedelta(days=1)).isoformat()
    data_corte_iso = parse_date_iso(data_corte)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.exists(DB_PATH):
        shutil.copy2(
            DB_PATH,
            os.path.join(BACKUP_DIR, f"backup_fechamento_ate_{data_corte_iso}_{ts}.db"),
        )

    conn = get_db_connection()
    try:
        try:
            conn.execute("ALTER TABLE arquivos_monitorados ADD COLUMN ignorado INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        with conn:
            clientes = conn.execute("SELECT * FROM clientes").fetchall()
            clientes_atualizados = 0

            for c in clientes:
                cid = c["id"]
                fat_ant_atual = float(c["fatura_anterior"] or 0.0)

                if modo_limpeza == "somente_hotfolder_mes_atual":
                    cond_sql = "cliente_id = ? AND (data_lancamento <= ? OR origem != 'hotfolder') AND id >= 2700"
                    cond_join = "l.cliente_id = ? AND (l.data_lancamento <= ? OR l.origem != 'hotfolder') AND l.id >= 2700"
                    params_q = (cid, data_corte_iso)
                elif modo_limpeza == "limpar_tudo":
                    cond_sql = "cliente_id = ? AND id >= 2700"
                    cond_join = "l.cliente_id = ? AND l.id >= 2700"
                    params_q = (cid,)
                else:
                    cond_sql = "cliente_id = ? AND data_lancamento <= ? AND id >= 2700"
                    cond_join = "l.cliente_id = ? AND l.data_lancamento <= ? AND l.id >= 2700"
                    params_q = (cid, data_corte_iso)

                l_tot = conn.execute(
                    f"""
                    SELECT
                        COALESCE(SUM(valor_entrega), 0) AS ent,
                        COALESCE(SUM(valor_pagamento), 0) AS pgto,
                        COALESCE(SUM(pagamento_fatura_anterior), 0) AS pgto_fat
                    FROM lancamentos
                    WHERE {cond_sql}
                    """,
                    params_q,
                ).fetchone()

                s_tot = conn.execute(
                    f"""
                    SELECT COALESCE(SUM(s.valor), 0) AS srv
                    FROM servicos s
                    JOIN lancamentos l ON s.lancamento_id = l.id
                    WHERE {cond_join}
                    """,
                    params_q,
                ).fetchone()

                pgto_fat = float(l_tot["pgto_fat"] or 0.0)
                srv = float(s_tot["srv"] or 0.0)
                ent = float(l_tot["ent"] or 0.0)
                pgto = float(l_tot["pgto"] or 0.0)

                saldo_fatura_anterior = fat_ant_atual - pgto_fat
                nova_fat_ant = round((srv + ent - pgto) + saldo_fatura_anterior, 2)

                conn.execute(
                    "UPDATE clientes SET fatura_anterior = ? WHERE id = ?",
                    (nova_fat_ant, cid),
                )
                clientes_atualizados += 1

            # Define quais lançamentos devem ser removidos conforme o modo escolhido
            if modo_limpeza == "limpar_tudo":
                rows_del = conn.execute("SELECT id FROM lancamentos").fetchall()
            elif modo_limpeza == "somente_hotfolder_mes_atual":
                rows_del = conn.execute(
                    "SELECT id FROM lancamentos WHERE data_lancamento <= ? OR origem != 'hotfolder'",
                    (data_corte_iso,),
                ).fetchall()
            else:  # manter_apos_corte
                rows_del = conn.execute(
                    "SELECT id FROM lancamentos WHERE data_lancamento <= ?",
                    (data_corte_iso,),
                ).fetchall()

            ids_del = [r["id"] for r in rows_del]
            if ids_del:
                placeholders = ",".join("?" for _ in ids_del)
                conn.execute(
                    f"UPDATE arquivos_monitorados SET ignorado = 1, lancamento_id = NULL, servico_id = NULL WHERE lancamento_id IN ({placeholders})",
                    ids_del,
                )
                conn.execute(
                    f"DELETE FROM servicos WHERE lancamento_id IN ({placeholders})",
                    ids_del,
                )
                conn.execute(
                    f"DELETE FROM lancamentos WHERE id IN ({placeholders})",
                    ids_del,
                )

            # Atualiza fatura_anterior e saldo_fatura_anterior nos lançamentos remanescentes do mês novo
            conn.execute(
                """
                UPDATE lancamentos
                SET fatura_anterior = COALESCE((SELECT c.fatura_anterior FROM clientes c WHERE c.id = lancamentos.cliente_id), 0.0),
                    saldo_fatura_anterior = COALESCE((SELECT c.fatura_anterior FROM clientes c WHERE c.id = lancamentos.cliente_id), 0.0) - COALESCE(pagamento_fatura_anterior, 0.0)
                WHERE cliente_id IS NOT NULL
                """
            )

            # Calcula o 1º dia após a data de corte para configurar hotfolder_data_minima
            try:
                from datetime import timedelta
                dt_prox = date.fromisoformat(data_corte_iso) + timedelta(days=1)
                prox_iso = dt_prox.isoformat()
            except Exception:
                prox_iso = "2026-10-01"

            conn.execute(
                "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('hotfolder_data_minima', ?)",
                (prox_iso,),
            )

        conn.close()
        return True, f"Virada de mês concluída! Saldos até {format_date_br(data_corte_iso)} transferidos para 'Fatura Anterior' de {clientes_atualizados} clientes e {len(ids_del)} lançamentos antigos limpos."
    except Exception as e:
        conn.close()
        return False, f"Erro na virada de mês: {e}"


# ==============================================================================
# CAIXA INTEGRADO AO BANCO DE DADOS
# ==============================================================================
def listar_lancamentos_caixa(data_inicio=None, data_fim=None, operacao=None):
    conn = get_db_connection()
    conditions = []
    params = []
    if data_inicio:
        conditions.append("c.data >= ?")
        params.append(parse_date_iso(data_inicio))
    if data_fim:
        conditions.append("c.data <= ?")
        params.append(parse_date_iso(data_fim))
    if operacao:
        conditions.append("c.operacao = ?")
        params.append(operacao)

    where_sql = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = conn.execute(
        f"""
        SELECT c.*, cl.nome AS cliente_nome
        FROM lancamentos_caixa c
        LEFT JOIN clientes cl ON c.cliente_id = cl.id
        {where_sql}
        ORDER BY c.data DESC, c.id DESC
        """,
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def criar_lancamento_caixa(descricao, data_str, valor, operacao, cliente_id=None):
    conn = get_db_connection()
    dt = parse_date_iso(data_str)
    val = parse_money(valor)
    cid = int(cliente_id) if (cliente_id and str(cliente_id).isdigit()) else None
    with conn:
        cur = conn.execute(
            """
            INSERT INTO lancamentos_caixa (descricao, data, valor, operacao, cliente_id, origem, usuario)
            VALUES (?, ?, ?, ?, ?, 'manual', 'operador')
            """,
            (descricao.strip(), dt, val, operacao, cid),
        )
        new_id = cur.lastrowid
    conn.close()
    return new_id


def atualizar_lancamento_caixa(caixa_id, descricao, data_str, valor, operacao, cliente_id=None):
    conn = get_db_connection()
    dt = parse_date_iso(data_str)
    val = parse_money(valor)
    cid = int(cliente_id) if (cliente_id and str(cliente_id).isdigit()) else None
    with conn:
        conn.execute(
            """
            UPDATE lancamentos_caixa
            SET descricao = ?, data = ?, valor = ?, operacao = ?, cliente_id = ?
            WHERE id = ?
            """,
            (descricao.strip(), dt, val, operacao, cid, int(caixa_id)),
        )
    conn.close()
    return True


def excluir_lancamento_caixa(caixa_id):
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM lancamentos_caixa WHERE id = ?", (int(caixa_id),))
    conn.close()
    return True


def obter_saldos_e_pagamentos_clientes(data_inicio=None, data_fim=None):
    """
    Calcula para todos os clientes cadastrados os valores de:
    - Fatura anterior
    - Serviços e entregas no período
    - Pagamentos lançados (valor_pagamento + pagamento_fatura_anterior)
    - Saldo devedor total
    Para exibição integrada na Tela Caixa e no Demonstrativo.
    """
    clientes = listar_clientes()
    filtros = {"apenas_identificados": True}
    if data_inicio:
        filtros["data_inicio"] = data_inicio
    if data_fim:
        filtros["data_fim"] = data_fim
    lancamentos = listar_lancamentos(filtros)

    mapa = {}
    for c in clientes:
        mapa[c["id"]] = {
            "cliente_id": c["id"],
            "nome": c["nome"],
            "fatura_anterior": float(c["fatura_anterior"] or 0.0),
            "servicos": 0.0,
            "entregas": 0.0,
            "pagamentos_periodo": 0.0,
            "pagamentos_fatura_anterior": 0.0,
            "pagamentos_total": 0.0,
            "saldo_periodo": 0.0,
            "saldo_devedor": float(c["fatura_anterior"] or 0.0),
        }

    for l in lancamentos:
        cid = l["cliente_id"]
        if not cid:
            continue
        if cid not in mapa:
            mapa[cid] = {
                "cliente_id": cid,
                "nome": l["cliente_nome"],
                "fatura_anterior": 0.0,
                "servicos": 0.0,
                "entregas": 0.0,
                "pagamentos_periodo": 0.0,
                "pagamentos_fatura_anterior": 0.0,
                "pagamentos_total": 0.0,
                "saldo_periodo": 0.0,
                "saldo_devedor": 0.0,
            }
        item = mapa[cid]
        item["servicos"] += float(l["total_servicos"] or 0.0)
        item["entregas"] += float(l["valor_entrega"] or 0.0)
        item["pagamentos_periodo"] += float(l["valor_pagamento"] or 0.0)
        item["pagamentos_fatura_anterior"] += float(l["pagamento_fatura_anterior"] or 0.0)

    lista = []
    totais = {
        "fatura_anterior": 0.0,
        "servicos": 0.0,
        "entregas": 0.0,
        "pagamentos_total": 0.0,
        "saldo_periodo": 0.0,
        "saldo_devedor": 0.0,
    }
    for cid, item in mapa.items():
        item["pagamentos_total"] = item["pagamentos_periodo"] + item["pagamentos_fatura_anterior"]
        item["saldo_periodo"] = item["servicos"] + item["entregas"] - item["pagamentos_periodo"]
        saldo_fat_ant = item["fatura_anterior"] - item["pagamentos_fatura_anterior"]
        item["saldo_devedor"] = item["saldo_periodo"] + saldo_fat_ant
        lista.append(item)

        totais["fatura_anterior"] += item["fatura_anterior"]
        totais["servicos"] += item["servicos"]
        totais["entregas"] += item["entregas"]
        totais["pagamentos_total"] += item["pagamentos_total"]
        totais["saldo_periodo"] += item["saldo_periodo"]
        totais["saldo_devedor"] += item["saldo_devedor"]

    lista.sort(key=lambda x: x["nome"].lower())
    return lista, totais


# ==============================================================================
# BACKUP (EXPORTAR E IMPORTAR SQLITE / JSON / SQL)
# ==============================================================================
def exportar_backup_json():
    conn = get_db_connection()
    tabelas = [
        "configuracoes",
        "clientes",
        "produtos",
        "lancamentos",
        "servicos",
        "lancamentos_caixa",
        "arquivos_monitorados",
    ]
    payload = {
        "sistema": "Sistema Terra Python (SQLite)",
        "data_exportacao": datetime.now().isoformat(),
        "tabelas": {},
    }
    for t in tabelas:
        rows = conn.execute(f"SELECT * FROM {t}").fetchall()
        payload["tabelas"][t] = [dict(r) for r in rows]
    conn.close()
    return payload


def importar_backup_json(payload):
    if not isinstance(payload, dict) or "tabelas" not in payload:
        return False, "Formato de arquivo JSON inválido."
    # Cria cópia de segurança antes de importar
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, os.path.join(BACKUP_DIR, f"auto_pre_import_{timestamp}.db"))

    conn = get_db_connection()
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        with conn:
            ordem_limpeza = [
                "arquivos_monitorados",
                "servicos",
                "lancamentos",
                "lancamentos_caixa",
                "produtos",
                "clientes",
                "configuracoes",
            ]
            for t in ordem_limpeza:
                if t in payload["tabelas"]:
                    conn.execute(f"DELETE FROM {t}")

            ordem_insercao = list(reversed(ordem_limpeza))
            for t in ordem_insercao:
                registros = payload["tabelas"].get(t, [])
                for reg in registros:
                    cols = list(reg.keys())
                    placeholders = ",".join("?" for _ in cols)
                    col_names = ",".join(cols)
                    vals = [reg[c] for c in cols]
                    conn.execute(
                        f"INSERT OR REPLACE INTO {t} ({col_names}) VALUES ({placeholders})",
                        vals,
                    )
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()
        return True, "Backup JSON importado com sucesso!"
    except Exception as e:
        conn.close()
        return False, f"Erro ao importar JSON: {e}"


def _parse_mysql_values_block(values_str):
    """
    Analisa o bloco VALUES (...), (...); de um dump MySQL/phpMyAdmin,
    retornando uma lista de tuplas (listas de valores Python).
    Suporta strings com aspas simples escapadas (\' ou ''), quebras de linha \\r\\n, NULL e números.
    """
    rows = []
    current_row = []
    current_token = []
    in_string = False
    in_tuple = False
    i = 0
    n = len(values_str)

    while i < n:
        ch = values_str[i]
        if in_string:
            if ch == "\\":
                if i + 1 < n:
                    nxt = values_str[i + 1]
                    if nxt == "r":
                        current_token.append("\r")
                    elif nxt == "n":
                        current_token.append("\n")
                    elif nxt == "t":
                        current_token.append("\t")
                    else:
                        current_token.append(nxt)
                    i += 2
                    continue
            elif ch == "'":
                if i + 1 < n and values_str[i + 1] == "'":
                    current_token.append("'")
                    i += 2
                    continue
                else:
                    in_string = False
                    i += 1
                    continue
            current_token.append(ch)
            i += 1
        else:
            if ch == "(":
                in_tuple = True
                current_row = []
                current_token = []
                i += 1
            elif ch == "'" and in_tuple:
                in_string = True
                current_token = ["__STR__"]
                i += 1
            elif ch == "," and in_tuple:
                val = _convert_mysql_token(current_token)
                current_row.append(val)
                current_token = []
                i += 1
            elif ch == ")" and in_tuple:
                val = _convert_mysql_token(current_token)
                current_row.append(val)
                rows.append(current_row)
                in_tuple = False
                current_token = []
                i += 1
            elif ch == ";" and not in_tuple:
                break
            else:
                if in_tuple:
                    current_token.append(ch)
                i += 1
    return rows


def _convert_mysql_token(token_chars):
    if not token_chars:
        return None
    if token_chars[0] == "__STR__":
        return "".join(token_chars[1:])
    raw = "".join(token_chars).strip()
    if not raw or raw.upper() == "NULL":
        return None
    if re.match(r"^-?\d+$", raw):
        return int(raw)
    if re.match(r"^-?\d+\.\d+$", raw):
        return float(raw)
    return raw


def importar_dump_sql(sql_content, conn=None):
    """
    Importa tanto dumps SQLite quanto dumps MySQL/phpMyAdmin (como 'Lancamentos 30_09_final.sql').
    """
    close_after = False
    if conn is None:
        conn = get_db_connection()
        close_after = True

    eh_mysql = ("ENGINE=InnoDB" in sql_content) or ("phpMyAdmin" in sql_content) or ("SET SQL_MODE" in sql_content)
    if not eh_mysql:
        with conn:
            conn.executescript(sql_content)
        if close_after:
            conn.close()
        return True, "Script SQLite importado com sucesso!"

    padrao_insert = re.compile(
        r"INSERT\s+(?:DELAYED\s+)?(?:IGNORE\s+)?INTO\s+`?(\w+)`?\s*\(([^)]+)\)\s*VALUES\s*(.*?);",
        re.DOTALL | re.IGNORECASE,
    )

    default_pastas_por_id = {
        3: "660x530, 530x660, Adast",
        5: "510x400, 400x510, GTO",
        6: "745x605, 605x745, Speed",
        8: "724",
        9: "Solna",
        10: "521",
        15: "650x550, 550x650, MO",
        16: "700x630, 630x700",
    }

    conn.execute("PRAGMA foreign_keys = OFF;")
    try:
        with conn:
            # Verifica quais tabelas estão presentes no dump para atualizar de forma limpa
            tabelas_no_dump = set()
            for m in padrao_insert.finditer(sql_content):
                tabelas_no_dump.add(m.group(1).lower())

            if {"clientes", "produtos", "lancamentos", "servicos"}.intersection(tabelas_no_dump):
                if "servicos" in tabelas_no_dump:
                    conn.execute("DELETE FROM servicos WHERE lancamento_id IN (SELECT id FROM lancamentos WHERE origem = 'manual')")
                if "lancamentos" in tabelas_no_dump:
                    conn.execute("DELETE FROM lancamentos WHERE origem = 'manual'")
                if "produtos" in tabelas_no_dump:
                    conn.execute("DELETE FROM produtos")
                if "clientes" in tabelas_no_dump:
                    conn.execute("DELETE FROM clientes")

            for m in padrao_insert.finditer(sql_content):
                tabela = m.group(1).lower()
                cols = [c.strip().strip("`").lower() for c in m.group(2).split(",")]
                rows = _parse_mysql_values_block(m.group(3))

                if tabela == "clientes":
                    for r in rows:
                        d = dict(zip(cols, r))
                        nome = (d.get("nome") or "").strip()
                        # Gera apelido automático sem espaços para auxiliar Hot Folder
                        ap = re.sub(r"[^a-z0-9]", "", nome.lower())
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO clientes
                            (id, nome, apelidos, telefone, rua_bairro, cidade, fatura_anterior, data_cadastro)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                d.get("id"),
                                nome,
                                ap,
                                d.get("telefone") or "",
                                d.get("rua_bairro") or d.get("bairro") or "",
                                d.get("cidade") or "",
                                float(d.get("fatura_anterior") or 0.0),
                                d.get("data_cadastro") or datetime.now().isoformat(),
                            ),
                        )

                elif tabela == "produtos":
                    for r in rows:
                        d = dict(zip(cols, r))
                        pid = int(d.get("id"))
                        pasta_hf = default_pastas_por_id.get(pid, "")
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO produtos
                            (id, nome, pasta_hotfolder, estoque_inicial, estoque_atual, estoque_consumido,
                             data_cadastro, preco, valor_compra, anotacoes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                pid,
                                (d.get("nome") or "").strip(),
                                pasta_hf,
                                int(d.get("estoque_inicial") or 0),
                                int(d.get("estoque_atual") or 0),
                                int(d.get("estoque_consumido") or 0),
                                d.get("data_cadastro") or date.today().isoformat(),
                                float(d.get("preco") or 0.0),
                                float(d.get("valor_compra") or 0.0),
                                d.get("anotacoes") or "",
                            ),
                        )

                elif tabela == "lancamentos" and "cliente_id" in cols:
                    for r in rows:
                        d = dict(zip(cols, r))
                        lid = int(d.get("id"))
                        cid = d.get("cliente_id")
                        dt_lanc = str(d.get("data_lancamento") or "")[:10]
                        v_ent = float(d.get("valor_entrega") or 0.0)
                        v_pgto = float(d.get("valor_pagamento") or 0.0)
                        fat_ant = float(d.get("fatura_anterior") or 0.0)
                        pgto_ant = float(d.get("pagamento_fatura_anterior") or 0.0)
                        saldo_ant = float(d.get("saldo_fatura_anterior") or (fat_ant - pgto_ant))
                        obs = d.get("observacao") or ""
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO lancamentos
                            (id, cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                             valor_entrega, valor_pagamento, fatura_anterior, pagamento_fatura_anterior,
                             saldo_fatura_anterior, observacao, data_registro)
                            VALUES (?, ?, '', 1, 'manual', ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                lid,
                                cid,
                                dt_lanc,
                                v_ent,
                                v_pgto,
                                fat_ant,
                                pgto_ant,
                                saldo_ant,
                                obs,
                                d.get("data_registro") or datetime.now().isoformat(),
                            ),
                        )
                        _sincronizar_pagamento_caixa(conn, lid, cid, dt_lanc, v_pgto, pgto_ant)

                elif tabela == "servicos":
                    for r in rows:
                        d = dict(zip(cols, r))
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO servicos
                            (id, lancamento_id, produto_id, descricao, quantidade, valor, cores_detectadas, arquivos_origem, pasta_origem)
                            VALUES (?, ?, ?, ?, ?, ?, '', '', '')
                            """,
                            (
                                d.get("id"),
                                d.get("lancamento_id"),
                                d.get("produto_id"),
                                d.get("descricao") or "",
                                int(d.get("quantidade") or 0),
                                float(d.get("valor") or 0.0),
                            ),
                        )

                elif tabela in ("lancamentos_caixa", "lancamentos") and "operacao" in cols:
                    for r in rows:
                        d = dict(zip(cols, r))
                        op = d.get("operacao") or "despesa"
                        if op == "transferencia":
                            op = "transferido"
                        conn.execute(
                            """
                            INSERT OR REPLACE INTO lancamentos_caixa
                            (id, descricao, data, valor, operacao, origem, usuario)
                            VALUES (?, ?, ?, ?, ?, 'manual', ?)
                            """,
                            (
                                d.get("id"),
                                d.get("descricao") or "",
                                str(d.get("data") or d.get("data_lancamento") or "")[:10],
                                float(d.get("valor") or 0.0),
                                op,
                                d.get("usuario") or "sistema",
                            ),
                        )
        conn.execute("PRAGMA foreign_keys = ON;")
        if close_after:
            conn.close()
        return True, "Dump MySQL/phpMyAdmin importado com sucesso para o SQLite!"
    except Exception as e:
        conn.execute("PRAGMA foreign_keys = ON;")
        if close_after:
            conn.close()
        return False, f"Erro ao importar SQL: {e}"


def exportar_backup_sql():

    conn = get_db_connection()
    sql_lines = [
        "-- Backup SQLite - Sistema Terra (Python)",
        f"-- Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "PRAGMA foreign_keys = OFF;",
        "BEGIN TRANSACTION;",
    ]
    for line in conn.iterdump():
        if line not in ("BEGIN TRANSACTION;", "COMMIT;"):
            sql_lines.append(line)
    sql_lines.append("COMMIT;")
    sql_lines.append("PRAGMA foreign_keys = ON;")
    conn.close()
    return "\n".join(sql_lines)
