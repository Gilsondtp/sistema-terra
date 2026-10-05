import os
import re
import time
import json
import threading
import unicodedata
from datetime import date, datetime

from database import (
    get_db_connection,
    get_config,
    listar_clientes,
    listar_produtos,
    BASE_DIR,
)

# Somente arquivos de chapa TIFF (.tif, .tiff, .tff) devem ser coletados
VALID_TIFF_EXTENSIONS = {".tif", ".tiff", ".tff"}

# Mapeamento padrão com suporte a dimensões diretas e invertidas (ex: 660x530 e 530x660)
DEFAULT_FOLDER_MAP = {
    "510x400": "GTO",
    "400x510": "GTO",
    "650x550": "MO",
    "550x650": "MO",
    "660x530": "Adast",
    "530x660": "Adast",
    "521": "521",
    "745x605": "Speed",
    "605x745": "Speed",
    "700x630": "700x630",
    "630x700": "700x630",
    "660x550": "Noel 660x550",
    "550x660": "Noel 660x550",
    "724": "724",
    "solna": "Solna",
    "gto": "GTO",
    "mo": "MO",
    "adast": "Adast",
    "adst": "Adast",
    "speed": "Speed",
}

# Vocabulário gráfico para separar palavras coladas quando estiverem na mesma caixa (tudo minúsculo ou tudo maiúsculo)
PALAVRAS_GRAFICA = [
    "santinhos", "santinho", "praguinhas", "praguinha", "pragao", "panfletos", "panfleto",
    "folhetos", "folheto", "folders", "folder", "cartazes", "cartaz", "catalogos", "catalogo",
    "revistas", "revista", "encartes", "encarte", "sacolas", "sacola", "embalagens", "embalagem",
    "rotulos", "rotulo", "adesivos", "adesivo", "etiquetas", "etiqueta", "blocos", "bloco",
    "taloes", "talao", "receituarios", "receituario", "fichas", "ficha", "envelopes", "envelope",
    "calendarios", "calendario", "agendas", "agenda", "cadernos", "caderno", "apostilas", "apostila",
    "convites", "convite", "ingressos", "ingresso", "cardapios", "cardapio", "bandejas", "bandeja",
    "pastas", "pasta", "laudos", "laudo", "sorteios", "sorteio", "propostas", "proposta",
    "montagens", "montagem", "dobradinhas", "dobradinha", "regravacao", "reimpressao", "refeito",
    "frente", "verso", "aberto", "aberta", "fechado", "fechada", "miolo", "capa", "chapas", "chapa",
    "cores", "cor", "papel", "couche", "offset", "supremo", "duplex", "triplex", "bighand",
    "professor", "professora", "doutor", "doutora", "mestre", "vereador", "prefeito", "deputado",
    "coligacao", "eleicao", "campanha", "outubro", "novembro", "dezembro", "setembro", "agosto",
    "ofertas", "oferta", "promocao", "sorte",
]


def eh_arquivo_tiff_valido(nome_arquivo):
    """
    Retorna True somente se o arquivo tiver extensão .tif, .tiff ou .tff
    e não for arquivo temporário/oculto do sistema ou do RIP.
    """
    if not nome_arquivo:
        return False
    base = os.path.basename(nome_arquivo).strip()
    if not base or base.startswith(".") or base.startswith("~"):
        return False
    _, ext = os.path.splitext(base)
    return ext.lower() in VALID_TIFF_EXTENSIONS


def obter_data_real_arquivo(caminho_arquivo):
    """
    Obtém a data real de gravação/modificação do arquivo no sistema de arquivos (YYYY-MM-DD).
    Garante que arquivos de dias anteriores não sejam listados como se fossem de hoje.
    """
    try:
        mtime = os.path.getmtime(caminho_arquivo)
        return date.fromtimestamp(mtime).isoformat()
    except Exception:
        return date.today().isoformat()


def formatar_descricao_servico(texto):
    """
    Restaura espaços com limites de palavra/medida reconhecíveis e remove extensões
    residuais do RIP no final. Não corrige a grafia nem substitui letras do nome original.
    Exemplo: 'Santinho7x10JooeKtiaA4x1ps' -> 'Santinho 7x10 Jooe Ktia A 4x1'
    """
    if not texto:
        return ""
    s = str(texto).strip()

    # 0. Remove eventual sufixo residual 'ps C', 'ps K', 'ps M', 'ps Y' ou 'psC1' etc.
    s = re.sub(
        r"(?:[\.\s_\-]*(?:ps|pdf|cdr|eps))[\s_\-\.]*[cmykCMYK]?(?:[\s_\-\.\(\[]*\d{1,3}[\)\]]*)?$",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()

    # 1. Remove extensões de arquivo de origem que o RIP cola no final (ps, pdf, cdr, eps, prn, plt, ai, indd, psd)
    s = re.sub(
        r"(?:[\.\s_\-]*(?:ps|pdf|cdr|eps|ai|prn|plt|indd|psd))+$",
        "",
        s,
        flags=re.IGNORECASE,
    ).strip()

    # 2. Troca underscores, hifens e pontos por espaço
    s = re.sub(r"[_\-\.]+", " ", s)

    # 3. Separa medidas/cores tipo 7x10, 4x1, 4x0, 4x4, 7x10cm colocando espaço antes e depois
    s = re.sub(r"([a-zA-Z])(\d+[xX]\d+(?:cm|mm|m)?)", r"\1 \2", s)
    s = re.sub(r"(\d+[xX]\d+(?:cm|mm|m)?)([a-zA-Z])", r"\1 \2", s)

    # 4. Separa CamelCase: minúscula seguida de Maiúscula (ex: JooeKtia -> Jooe Ktia, UldoricoMagno -> Uldorico Magno)
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    # Separa Maiúscula seguida de Maiúscula+minúscula (ex: MarciaEJaco -> Marcia E Jaco)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)

    # 5. Separa números colados em palavras comuns (preservando 7x10, 4x1, A3, A4, A5, v1, v2, v3)
    s = re.sub(r"(?<![\d])([b-uB-Uw-zW-Z])(\d)", r"\1 \2", s)
    s = re.sub(
        r"(\d)(?![xX]\d)(?!(?:cm|mm|mil|un)\b)([a-zA-Z])",
        r"\1 \2",
        s,
        flags=re.IGNORECASE,
    )

    # 6. Segmenta iterativamente palavras gráficas conhecidas quando vierem coladas na mesma caixa
    for _ in range(3):
        tokens = s.split()
        novos_tokens = []
        mudou = False
        for tok in tokens:
            if len(tok) >= 6 and (tok.islower() or tok.isupper()):
                dividido = False
                for pal in PALAVRAS_GRAFICA:
                    m_ini = re.match(
                        rf"^({pal})([a-zA-Z0-9]{{2,}})$", tok, flags=re.IGNORECASE
                    )
                    if m_ini:
                        novos_tokens.extend([m_ini.group(1), m_ini.group(2)])
                        dividido = True
                        mudou = True
                        break
                    m_fim = re.match(
                        rf"^([a-zA-Z0-9]{{2,}})({pal})$", tok, flags=re.IGNORECASE
                    )
                    if m_fim:
                        novos_tokens.extend([m_fim.group(1), m_fim.group(2)])
                        dividido = True
                        mudou = True
                        break
                if not dividido:
                    novos_tokens.append(tok)
            else:
                novos_tokens.append(tok)
        s = " ".join(novos_tokens)
        if not mudou:
            break

    s = re.sub(r"\s+", " ", s).strip()
    return s


def limpar_e_corrigir_registros_monitorados():
    """
    1. Remove do banco de dados quaisquer registros monitorados que NÃO tenham extensão .tif / .tiff / .tff.
    2. Corrige a data_lancamento de arquivos monitorados sincronizando com a data real do arquivo no disco.
    """
    conn = get_db_connection()
    try:
        try:
            conn.execute(
                "ALTER TABLE arquivos_monitorados ADD COLUMN ignorado INTEGER NOT NULL DEFAULT 0"
            )
        except Exception:
            pass
        cfg = get_config()
        data_minima = (cfg.get("hotfolder_data_minima") or "2026-10-01").strip()

        # Corrige pontualmente saldos confirmados no fechamento de Setembro -> Outubro
        # para instalações que ainda tenham os valores antigos no banco local.
        ajustes_fatura_setembro = {
            24: (2090.00, 1900.50),   # Armo
            11: (8523.00, 8783.00),   # CADS
            5:  (6315.00, 6947.50),   # Exxograf
            3:  (13200.00, 13242.50), # Falcao
            10: (1402.50, 1082.50),   # Gold
            6:  (8330.00, 8312.00),   # Noel
            18: (4812.50, 5195.00),   # Ribas
            23: (10192.50, 8852.50), # Nordeste — fechamento confirmado pela fatura de setembro
            30: (1795.00, 1870.00),   # Visiongraf
        }
        with conn:
            for cid_aj, (val_antigo, val_correto) in ajustes_fatura_setembro.items():
                row_cli = conn.execute(
                    "SELECT fatura_anterior FROM clientes WHERE id = ?", (cid_aj,)
                ).fetchone()
                if cid_aj == 23:
                    # Só aplicar no banco já virado para outubro; se setembro ainda
                    # estiver lançado, não há dados suficientes para corrigir linhas individuais.
                    setembro_pendente = conn.execute(
                        """
                        SELECT 1 FROM lancamentos
                        WHERE cliente_id = ?
                          AND (data_lancamento <= '2026-09-30' OR data_lancamento IS NULL)
                        LIMIT 1
                        """,
                        (cid_aj,),
                    ).fetchone()
                    if setembro_pendente:
                        continue
                if row_cli and abs(float(row_cli["fatura_anterior"] or 0.0) - val_antigo) < 0.05:
                    conn.execute(
                        "UPDATE clientes SET fatura_anterior = ? WHERE id = ?",
                        (val_correto, cid_aj),
                    )
                    conn.execute(
                        """
                        UPDATE lancamentos
                        SET fatura_anterior = ?,
                            saldo_fatura_anterior = ? - COALESCE(pagamento_fatura_anterior, 0.0)
                        WHERE cliente_id = ?
                        """,
                        (val_correto, val_correto, cid_aj),
                    )

        rows = conn.execute(
            "SELECT id, caminho_completo, nome_arquivo, pasta_produto, cor_detectada, lancamento_id, data_lancamento, ignorado FROM arquivos_monitorados"
        ).fetchall()

        # Reprocessa automaticamente registros que tinham ficado com sufixo residual 'ps C/K/M/Y'
        # ou cuja cor_detectada mudou com o novo parser (ex: antes 'UNICA' e agora 'C'/'M'/'Y'/'K')
        servs_ps = conn.execute(
            """
            SELECT s.id, s.lancamento_id, s.descricao, s.quantidade, s.produto_id
            FROM servicos s
            JOIN lancamentos l ON s.lancamento_id = l.id
            WHERE l.origem = 'hotfolder'
            """
        ).fetchall()
        lids_reprocessar = set()
        for sv in servs_ps:
            desc_sv = (sv["descricao"] or "").strip()
            if re.search(r"(?:\b(?:ps|pdf|cdr|eps)\s+[cmykCMYK]|(?:ps|pdf|cdr|eps)[cmykCMYK])$", desc_sv, flags=re.IGNORECASE):
                lids_reprocessar.add(sv["lancamento_id"])

        for r in rows:
            if not r["ignorado"] and r["lancamento_id"] and eh_arquivo_tiff_valido(r["nome_arquivo"]):
                _, cor_nova, _ = extrair_cor_e_base(r["nome_arquivo"])
                if (r["cor_detectada"] or "UNICA") != cor_nova:
                    lids_reprocessar.add(r["lancamento_id"])

        if lids_reprocessar:
            with conn:
                for lid in lids_reprocessar:
                    servs = conn.execute(
                        "SELECT produto_id, quantidade FROM servicos WHERE lancamento_id = ?",
                        (lid,),
                    ).fetchall()
                    for s in servs:
                        if s["produto_id"] and s["quantidade"]:
                            conn.execute(
                                """
                                UPDATE produtos
                                SET estoque_atual = estoque_atual + ?,
                                    estoque_consumido = MAX(0, estoque_consumido - ?)
                                WHERE id = ?
                                """,
                                (s["quantidade"], s["quantidade"], s["produto_id"]),
                            )
                    conn.execute("DELETE FROM servicos WHERE lancamento_id = ?", (lid,))
                    conn.execute("DELETE FROM lancamentos WHERE id = ?", (lid,))
                    conn.execute(
                        "DELETE FROM arquivos_monitorados WHERE lancamento_id = ? AND ignorado = 0",
                        (lid,),
                    )
            rows = conn.execute(
                "SELECT id, caminho_completo, nome_arquivo, pasta_produto, cor_detectada, lancamento_id, data_lancamento, ignorado FROM arquivos_monitorados"
            ).fetchall()
        lancamentos_remover = set()
        arq_ids_remover = []

        for r in rows:
            if not eh_arquivo_tiff_valido(r["nome_arquivo"]):
                arq_ids_remover.append(r["id"])
                if r["lancamento_id"]:
                    lancamentos_remover.add(r["lancamento_id"])
            elif r["caminho_completo"] and os.path.exists(r["caminho_completo"]):
                data_real = obter_data_real_arquivo(r["caminho_completo"])
                if r["data_lancamento"] != data_real:
                    with conn:
                        conn.execute(
                            "UPDATE arquivos_monitorados SET data_lancamento = ? WHERE id = ?",
                            (data_real, r["id"]),
                        )
                        if r["lancamento_id"]:
                            conn.execute(
                                "UPDATE lancamentos SET data_lancamento = ? WHERE id = ? AND origem = 'hotfolder'",
                                (data_real, r["lancamento_id"]),
                            )
                if data_minima and data_real < data_minima and r["lancamento_id"]:
                    lancamentos_remover.add(r["lancamento_id"])
                    with conn:
                        conn.execute(
                            "UPDATE arquivos_monitorados SET ignorado = 1, lancamento_id = NULL, servico_id = NULL WHERE id = ?",
                            (r["id"],),
                        )

        if arq_ids_remover or lancamentos_remover:
            with conn:
                for lid in lancamentos_remover:
                    servs = conn.execute(
                        "SELECT produto_id, quantidade FROM servicos WHERE lancamento_id = ?",
                        (lid,),
                    ).fetchall()
                    for s in servs:
                        if s["produto_id"] and s["quantidade"]:
                            conn.execute(
                                """
                                UPDATE produtos
                                SET estoque_atual = estoque_atual + ?,
                                    estoque_consumido = MAX(0, estoque_consumido - ?)
                                WHERE id = ?
                                """,
                                (s["quantidade"], s["quantidade"], s["produto_id"]),
                            )
                    conn.execute("DELETE FROM servicos WHERE lancamento_id = ?", (lid,))
                    conn.execute("DELETE FROM lancamentos WHERE id = ?", (lid,))
                for aid in arq_ids_remover:
                    conn.execute("DELETE FROM arquivos_monitorados WHERE id = ?", (aid,))
    except Exception:
        pass
    finally:
        conn.close()


def remover_acentos(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_compacto(texto):
    s = remover_acentos(texto).lower()
    return re.sub(r"[^a-z0-9]", "", s)


def extrair_variantes_dimensao(texto):
    """
    Se o texto contiver dimensões numéricas como '530 x 660', '660x530', '510 x 400',
    retorna as duas variantes ('530x660' e '660x530') para que qualquer ordem bata com o produto.
    """
    if not texto:
        return set()
    variantes = {normalizar_compacto(texto)}
    m = re.search(r"(\d{3,4})\s*[xX\*_\-\s]\s*(\d{3,4})", str(texto))
    if m:
        d1, d2 = m.group(1), m.group(2)
        variantes.add(f"{d1}x{d2}")
        variantes.add(f"{d2}x{d1}")
    return variantes


def damerau_levenshtein(s1, s2):
    len1, len2 = len(s1), len(s2)
    d = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        d[i][0] = i
    for j in range(len2 + 1):
        d[0][j] = j

    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost,
            )
            if (
                i > 1
                and j > 1
                and s1[i - 1] == s2[j - 2]
                and s1[i - 2] == s2[j - 1]
            ):
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len1][len2]


def _base_para_comparar_arquivos_cor(texto):
    """Normaliza a base RIP sem uma possível cor/página terminal para comparar irmãos."""
    base = str(texto or "").strip(" _-.()[]")
    base = re.sub(r"(?i)(?:ps|pdf|cdr|eps|ai|prn|plt|indd|psd)$", "", base).strip(" _-.")
    # Em nomes como job_1C, o número é página e fica antes do identificador de cor.
    m_pag = re.search(r"(?:[\s_\-\.]+(?:pag(?:ina)?[\s_\-]*|p[\s_\-]*)?\d{1,3}|[\(\[]\d{1,3}[\)\]])$", base, flags=re.IGNORECASE)
    if m_pag and not re.search(r"\d\s*[xX]\s*\d{1,3}$", base):
        base = base[:m_pag.start()].strip(" _-.()[]")
    return normalizar_compacto(base)


def _irmaos_confirmam_cor(stem_atual, cor_candidata, arquivos_irmaos):
    """Só trata uma letra final minúscula como cor quando outros TIFFs confirmam a série."""
    prefixo_atual = _base_para_comparar_arquivos_cor(stem_atual[:-1])
    if not prefixo_atual:
        return False

    cores_encontradas = {str(cor_candidata).upper()}
    for nome in arquivos_irmaos or []:
        stem = os.path.splitext(os.path.basename(nome))[0].strip()

        # Remove paginação RIP colada depois da cor/extensão de origem (ex.: psC1, psY02).
        m_num = re.search(
            r"(?i)(?:[cmyk]|gray|grey|black|preto|cyan|magenta|yellow|ps|pdf|cdr|eps)(\d{1,3})$",
            stem,
        )
        if m_num and not re.search(r"\d[xX]\d{1,3}$", stem):
            stem = stem[:m_num.start(1)].rstrip(" _-.()[]")

        # Também aceita paginação separada: _1, -p2, (3), [4].
        m_pag = re.search(
            r"(?:[\s_\-\.]+(?:pag(?:ina)?[\s_\-]*|p[\s_\-]*)?(\d{1,3})|[\s_\-\.]*[\(\[](\d{1,3})[\)\]])$",
            stem,
            flags=re.IGNORECASE,
        )
        if m_pag and not re.search(r"\d\s*[xX]\s*\d{1,3}$", stem):
            stem = stem[:m_pag.start()].strip(" _-.()[]")

        if not stem or stem[-1].lower() not in "cmyk":
            continue
        cor_irma = stem[-1].upper()
        prefixo_irma = _base_para_comparar_arquivos_cor(stem[:-1])
        if prefixo_irma == prefixo_atual:
            cores_encontradas.add(cor_irma)
            if len(cores_encontradas) > 1:
                return True

    return False


def extrair_cor_e_base(nome_arquivo, arquivos_irmaos=None):
    """
    Analisa o nome de um arquivo .tif/.tiff/.tff gerado pelo RIP (Raster Precision Screen)
    e retorna:
      (base_sem_cor_e_pagina, cor_detectada, pagina_detectada)

    Executa múltiplas passadas no final do nome do arquivo para remover em QUALQUER ordem:
    - Número de página/cópia/chapa: (1), (2), [1], _1, -1, .1, _p1, _pag1, 001, 1
    - Cor da chapa: C, M, Y, K, (C), (M), (Y), (K), GRAY, BLACK, CYAN, MAGENTA, YELLOW, PANTONE...
    - Extensão do arquivo de origem colada pelo RIP: ps, pdf, cdr, eps, ai, prn, plt
    Garantindo que todas as chapas do mesmo serviço tenham exatamente a mesma base e
    sejam agrupadas em 1 ÚNICO lançamento com a quantidade total de cores/chapas.
    """
    arquivos_irmaos = arquivos_irmaos or []
    nome_limpo = os.path.basename(nome_arquivo)
    stem, _ = os.path.splitext(nome_limpo)

    original_stem = stem.strip()
    cor = None
    pagina = None

    for _ in range(5):
        mudou = False

        # A) Remove sufixo de página/cópia explícito no final: ' (1)', '(1)', '[1]', '_p1', '_pag1', '_001', '-1', '.1'
        m_pag_exp = re.search(
            r"(?:[\s_\-\.]+(?:pag(?:ina)?[\s_\-]*|p[\s_\-]*)?(\d{1,3})|[\s_\-\.]*[\(\[](\d{1,3})[\)\]])$",
            original_stem,
            flags=re.IGNORECASE,
        )
        if m_pag_exp:
            # Garante que não é parte de medida tipo '7x10' ou '4x1'
            if not re.search(r"\d\s*[xX]\s*\d{1,3}$", original_stem):
                if not pagina:
                    pagina = m_pag_exp.group(1) or m_pag_exp.group(2)
                original_stem = original_stem[: m_pag_exp.start()].strip(" _-.()[]")
                mudou = True

        # B) Remove número colado logo após cor ou após ps/pdf/cdr (ex: '...psC1', '...ps(C)1', '...psC001', '...ps1', '...GRAY1')
        m_num_colado = re.search(
            r"(?:[cmykCMYK]|gray|grey|black|preto|cyan|magenta|yellow|ps|pdf|cdr|eps)[\)\]]*(\d{1,3})$",
            original_stem,
            flags=re.IGNORECASE,
        )
        if m_num_colado:
            if not re.search(r"\d[xX]\d{1,3}$", original_stem):
                if not pagina:
                    pagina = m_num_colado.group(1)
                original_stem = original_stem[: m_num_colado.start(1)].strip(" _-.()[]")
                mudou = True

        # C) Verifica padrão PANTONE / SPOT / COR ESPECIAL no final
        if not cor:
            m_pantone = re.search(
                r"(?:[\s_\-\.\(\[]+)?(pantone[\s_\-\w]*|spot[\s_\-\w]*|cor[\s_\-]*especial[\s_\-\w]*)[\)\]]*$",
                original_stem,
                flags=re.IGNORECASE,
            )
            if m_pantone:
                cor_raw = m_pantone.group(1).strip(" _-()[]").upper()
                cor = re.sub(r"\s+", " ", cor_raw)
                original_stem = original_stem[: m_pantone.start()].strip(" _-.()[]")
                mudou = True

        # D) Verifica padrão GRAY / GREY / CYAN / MAGENTA / YELLOW / BLACK por extenso
        if not cor:
            m_extenso = re.search(
                r"(?:[\s_\-\.\(\[]+)?(gray|grey|cinza|cyan|ciano|magenta|yellow|amarelo|black|preto)[\)\]]*$",
                original_stem,
                flags=re.IGNORECASE,
            )
            if m_extenso:
                mapa_cor = {
                    "gray": "GRAY",
                    "grey": "GRAY",
                    "cinza": "GRAY",
                    "cyan": "C",
                    "ciano": "C",
                    "magenta": "M",
                    "yellow": "Y",
                    "amarelo": "Y",
                    "black": "K",
                    "preto": "K",
                }
                cor = mapa_cor.get(m_extenso.group(1).lower(), m_extenso.group(1).upper())
                original_stem = original_stem[: m_extenso.start()].strip(" _-.()[]")
                mudou = True

        # E) Verifica padrão com separador ou número ou parênteses antes de C, M, Y, K
        if not cor:
            m_sep = re.search(
                r"(?:[\s_\-\.\(\[]+|(?<=\d))([cmykCMYK])[\)\]]*$",
                original_stem,
            )
            if m_sep:
                cor = m_sep.group(1).upper()
                original_stem = original_stem[: m_sep.start()].strip(" _-.()[]")
                mudou = True

        # F) Verifica transição minúscula -> Maiúscula C, M, Y, K no final (ex: "...psY", "...psM", "...psK", "...psC")
        if not cor:
            m_camel = re.search(r"(?<=[a-z])([CMYK])$", original_stem)
            if m_camel:
                cor = m_camel.group(1).upper()
                original_stem = original_stem[:-1].strip(" _-.()[]")
                mudou = True

        # G) Sufixo colado sem separador. Exige contexto confiável para não cortar
        # palavras legítimas terminadas em c, m, y ou k (ex.: Dynamic, Party, Click).
        if not cor and len(original_stem) >= 4 and original_stem[-1].lower() in "cmyk":
            cand_char = original_stem[-1]
            cand_prefix = original_stem[:-1]
            tem_extensao_rip = cand_prefix.lower().endswith(("ps", "pdf", "cdr", "eps"))
            confirmado_por_irmaos = _irmaos_confirmam_cor(
                original_stem, cand_char, arquivos_irmaos
            )

            if tem_extensao_rip or confirmado_por_irmaos:
                cor = cand_char.upper()
                original_stem = cand_prefix.strip(" _-.()[]")
                mudou = True

        # H) Remove extensão do arquivo de origem que o RIP cola antes da cor (ex: "ps", "pdf", "cdr", "eps")
        m_src_ext = re.search(
            r"(?:[\.\s_\-]*|(?:(?<=[0-9a-zA-Z])))(ps|pdf|cdr|eps|ai|prn|plt|indd|psd)$",
            original_stem,
            flags=re.IGNORECASE,
        )
        if m_src_ext:
            original_stem = original_stem[: m_src_ext.start()].strip(" _-.()[]")
            mudou = True

        if not mudou:
            break

    if not cor:
        cor = "UNICA"

    return original_stem.strip(), cor, pagina


def identificar_cliente_e_servico(base_nome, lista_clientes=None):
    """
    Recebe o nome base do arquivo (sem cor, sem página e sem ps/pdf) e identifica:
    - O cliente (por similaridade tolerante a erros)
    - Somente a descrição do serviço, já formatada com espaços entre as palavras!
    """
    if lista_clientes is None:
        lista_clientes = listar_clientes()

    texto_limpo = re.sub(r"[_\-\.]+", " ", base_nome).strip()
    texto_limpo = re.sub(r"\s+", " ", texto_limpo)

    candidatos = []
    palavras_genericas = {"grafica", "editora", "embalagens", "impressos", "offset", "sacolas"}

    for c in lista_clientes:
        cid = c["id"]
        cnome = c["nome"].strip()
        nomes_teste = [cnome]
        if c.get("apelidos"):
            for ap in c["apelidos"].split(","):
                if ap.strip():
                    nomes_teste.append(ap.strip())
        partes_nome = cnome.split()
        if len(partes_nome) > 1 and normalizar_compacto(partes_nome[0]) not in palavras_genericas:
            nomes_teste.append(partes_nome[0])

        for nt in nomes_teste:
            norm_comp = normalizar_compacto(nt)
            if len(norm_comp) >= 2:
                candidatos.append(
                    {
                        "cliente_id": cid,
                        "cliente_nome": cnome,
                        "padrao_original": nt,
                        "padrao_norm": norm_comp,
                        "tokens_norm": [normalizar_compacto(t) for t in nt.split() if normalizar_compacto(t)],
                    }
                )

    candidatos.sort(key=lambda x: len(x["padrao_norm"]), reverse=True)
    palavras = texto_limpo.split(" ")

    # CASO 1: Com separação de palavras
    if len(palavras) >= 2:
        melhor_match = None
        melhor_distancia = 999
        melhor_num_palavras = 0

        for cand in candidatos:
            n_tok = len(cand["tokens_norm"])
            if len(palavras) <= n_tok:
                continue
            trecho_arquivo = "".join(normalizar_compacto(w) for w in palavras[:n_tok])
            alvo = cand["padrao_norm"]
            if not trecho_arquivo or not alvo:
                continue

            dist = damerau_levenshtein(trecho_arquivo, alvo)
            max_tol = 0 if len(alvo) <= 3 else (1 if len(alvo) <= 6 else 2)

            if dist <= max_tol:
                score = (dist, -len(alvo))
                if melhor_match is None or score < (melhor_distancia, -len(melhor_match["padrao_norm"])):
                    melhor_match = cand
                    melhor_distancia = dist
                    melhor_num_palavras = n_tok

        if melhor_match:
            cliente_orig = " ".join(palavras[:melhor_num_palavras])
            servico_raw = " ".join(palavras[melhor_num_palavras:]).strip()
            servico_desc = formatar_descricao_servico(servico_raw) or formatar_descricao_servico(base_nome)
            return {
                "cliente_id": melhor_match["cliente_id"],
                "cliente_nome": melhor_match["cliente_nome"],
                "cliente_nome_original": cliente_orig,
                "descricao_servico": servico_desc,
                "identificado": True,
            }

    # CASO 2: Sem espaços (ex: "GilbertoSantinho7x10JooeKtiaA4x1")
    compacto_total = normalizar_compacto(base_nome)
    melhor_prefixo = None
    melhor_dist_pref = 999
    melhor_tam_corte = 0

    for cand in candidatos:
        alvo = cand["padrao_norm"]
        L = len(alvo)
        if L < 3 or len(compacto_total) <= L:
            continue

        max_tol = 1 if L <= 6 else 2
        for tam in (L, L - 1, L + 1):
            if tam < 3 or tam >= len(compacto_total):
                continue
            pref = compacto_total[:tam]
            dist = damerau_levenshtein(pref, alvo)
            if dist <= max_tol:
                if pref[0] != alvo[0] and (len(pref) < 2 or pref[1] != alvo[0]):
                    continue
                score = (dist, -L)
                if melhor_prefixo is None or score < (melhor_dist_pref, -len(melhor_prefixo["padrao_norm"])):
                    melhor_prefixo = cand
                    melhor_dist_pref = dist
                    melhor_tam_corte = tam

    if melhor_prefixo:
        chars_consumidos = 0
        idx_corte = 0
        for idx, ch in enumerate(base_nome):
            if re.match(r"[a-zA-Z0-9]", remover_acentos(ch)):
                chars_consumidos += 1
            if chars_consumidos >= melhor_tam_corte:
                idx_corte = idx + 1
                break

        cliente_orig = base_nome[:idx_corte].strip(" _-.")
        servico_raw = base_nome[idx_corte:].strip(" _-.")
        servico_desc = formatar_descricao_servico(servico_raw) or "Serviço CTP"
        return {
            "cliente_id": melhor_prefixo["cliente_id"],
            "cliente_nome": melhor_prefixo["cliente_nome"],
            "cliente_nome_original": cliente_orig,
            "descricao_servico": servico_desc,
            "identificado": True,
        }

    # CASO 3: Cliente NÃO IDENTIFICADO
    texto_formatado = formatar_descricao_servico(base_nome)
    partes_fmt = texto_formatado.split()
    if len(partes_fmt) >= 2:
        cliente_orig = partes_fmt[0]
        servico_desc = " ".join(partes_fmt[1:])
    else:
        cliente_orig = base_nome
        servico_desc = texto_formatado or base_nome

    return {
        "cliente_id": None,
        "cliente_nome": "Não Identificado",
        "cliente_nome_original": cliente_orig,
        "descricao_servico": servico_desc,
        "identificado": False,
    }


def resolver_produto_por_pasta(nome_pasta, lista_produtos=None):
    """
    Associa a pasta do Hot Folder (ex: '530 x 660', '660 x 530', '660x530', '510x400', '400x510', '521', '745x605')
    ao Produto ('chapa') cadastrado no sistema.
    Reconhece automaticamente dimensões invertidas (AxB == BxA) e espaços.
    """
    if not nome_pasta:
        return None
    if lista_produtos is None:
        lista_produtos = listar_produtos()

    variantes_pasta = extrair_variantes_dimensao(nome_pasta)
    if not variantes_pasta:
        return None

    for p in lista_produtos:
        variantes_prod = set()
        variantes_prod.update(extrair_variantes_dimensao(p["nome"]))
        for item_cfg in (p.get("pasta_hotfolder") or "").split(","):
            if item_cfg.strip():
                variantes_prod.update(extrair_variantes_dimensao(item_cfg.strip()))
        if variantes_pasta.intersection(variantes_prod):
            return p

    for vp in variantes_pasta:
        for k_map, alvo_padrao in DEFAULT_FOLDER_MAP.items():
            if k_map == vp or k_map in vp:
                alvo_norm = normalizar_compacto(alvo_padrao)
                for p in lista_produtos:
                    if normalizar_compacto(p["nome"]) == alvo_norm:
                        return p

    pasta_norm = normalizar_compacto(nome_pasta)
    for p in lista_produtos:
        pastas_cfg = [normalizar_compacto(x) for x in (p.get("pasta_hotfolder") or "").split(",") if x.strip()]
        for cfg in pastas_cfg:
            if cfg and (cfg in pasta_norm or pasta_norm in cfg):
                return p

    return None


def processar_arquivo_hotfolder(caminho_arquivo, nome_pasta_produto, data_ref=None, arquivos_irmaos=None):
    """
    Processa um arquivo individual .tif/.tiff/.tff detectado dentro de uma subpasta do Hot Folder.
    Agrupa todas as cores/chapas do mesmo serviço em 1 ÚNICO lançamento/serviço com a quantidade total de cores.
    """
    nome_arquivo = os.path.basename(caminho_arquivo)
    if not eh_arquivo_tiff_valido(nome_arquivo):
        return None

    caminho_abs = os.path.abspath(caminho_arquivo)

    if not data_ref:
        data_ref = obter_data_real_arquivo(caminho_arquivo)

    cfg = get_config()
    data_minima = (cfg.get("hotfolder_data_minima") or "2026-10-01").strip()
    if data_minima and data_ref < data_minima:
        return None

    conn = get_db_connection()
    try:
        conn.execute("ALTER TABLE arquivos_monitorados ADD COLUMN ignorado INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass

    ja_existe = conn.execute(
        "SELECT id, lancamento_id, ignorado FROM arquivos_monitorados WHERE caminho_completo = ?",
        (caminho_abs,),
    ).fetchone()

    if ja_existe:
        if ja_existe["ignorado"] == 1:
            conn.close()
            return None
        if ja_existe["lancamento_id"]:
            lanc_ativo = conn.execute(
                "SELECT id FROM lancamentos WHERE id = ?",
                (ja_existe["lancamento_id"],),
            ).fetchone()
            if lanc_ativo:
                conn.close()
                return None
        with conn:
            conn.execute(
                "UPDATE arquivos_monitorados SET ignorado = 1, lancamento_id = NULL, servico_id = NULL WHERE id = ?",
                (ja_existe["id"],),
            )
        conn.close()
        return None

    if arquivos_irmaos is None:
        pasta_dir = os.path.dirname(caminho_arquivo)
        try:
            arquivos_irmaos = [f for f in os.listdir(pasta_dir) if eh_arquivo_tiff_valido(f)]
        except Exception:
            arquivos_irmaos = [nome_arquivo]

    base_nome, cor, pagina = extrair_cor_e_base(nome_arquivo, arquivos_irmaos)
    if not base_nome:
        conn.close()
        return None

    clientes = listar_clientes()
    produtos = listar_produtos()

    info_cli = identificar_cliente_e_servico(base_nome, clientes)
    produto = resolver_produto_por_pasta(nome_pasta_produto, produtos)

    produto_id = produto["id"] if produto else None
    preco_unitario = float(produto["preco"] or 0.0) if produto else 0.0

    chave_cli = (
        f"ID_{info_cli['cliente_id']}"
        if info_cli["identificado"]
        else f"RAW_{normalizar_compacto(info_cli['cliente_nome_original'])}"
    )
    chave_prod = f"PROD_{produto_id}" if produto_id else f"PASTA_{normalizar_compacto(nome_pasta_produto)}"
    chave_serv = normalizar_compacto(info_cli["descricao_servico"]) or normalizar_compacto(base_nome)
    chave_agrupamento = f"{data_ref}::{chave_prod}::{chave_cli}::{chave_serv}"

    with conn:
        # Procura se já existe um serviço deste mesmo cliente + descrição + produto na mesma data
        reg_anterior = conn.execute(
            """
            SELECT lancamento_id, servico_id
            FROM arquivos_monitorados
            WHERE chave_agrupamento = ? AND ignorado = 0 AND servico_id IS NOT NULL
            ORDER BY id DESC LIMIT 1
            """,
            (chave_agrupamento,),
        ).fetchone()

        servico_existente = None
        lancamento_id = None
        if reg_anterior and reg_anterior["servico_id"]:
            servico_existente = conn.execute(
                "SELECT * FROM servicos WHERE id = ?",
                (reg_anterior["servico_id"],),
            ).fetchone()
            if servico_existente:
                lancamento_id = servico_existente["lancamento_id"]

        if servico_existente:
            servico_id = servico_existente["id"]
            cores_atuais = [c.strip() for c in (servico_existente["cores_detectadas"] or "").split(",") if c.strip()]

            # Normaliza o identificador de página+cor: página 1 ou sem página equivalem à chapa principal daquela cor (ex: C == P1-C)
            pag_int = int(pagina) if (pagina and str(pagina).isdigit()) else 1
            cor_label = f"P{pag_int}-{cor}" if (pag_int > 1 and cor != "UNICA") else cor

            # Verifica se esta exata cor (na mesma página) já foi contabilizada neste serviço (evita duplicar C, M, Y, K)
            cores_equivalentes = {cor_label, f"P1-{cor}" if pag_int == 1 else cor_label}
            cor_ja_contada = (cor in ("C", "M", "Y", "K", "GRAY")) and any(
                c in cores_equivalentes for c in cores_atuais
            )

            arqs_atuais = []
            try:
                arqs_atuais = json.loads(servico_existente["arquivos_origem"] or "[]")
            except Exception:
                arqs_atuais = []
            arqs_atuais.append(nome_arquivo)

            if not cor_ja_contada:
                nova_qtd = int(servico_existente["quantidade"] or 0) + 1
                novo_valor = round(nova_qtd * preco_unitario, 2)
                cores_atuais.append(cor_label)

                conn.execute(
                    """
                    UPDATE servicos
                    SET quantidade = ?,
                        valor = ?,
                        cores_detectadas = ?,
                        arquivos_origem = ?
                    WHERE id = ?
                    """,
                    (
                        nova_qtd,
                        novo_valor,
                        ", ".join(cores_atuais),
                        json.dumps(arqs_atuais, ensure_ascii=False),
                        servico_id,
                    ),
                )

                if produto_id is not None:
                    conn.execute(
                        """
                        UPDATE produtos
                        SET estoque_atual = estoque_atual - 1,
                            estoque_consumido = estoque_consumido + 1
                        WHERE id = ?
                        """,
                        (produto_id,),
                    )
            else:
                conn.execute(
                    "UPDATE servicos SET arquivos_origem = ? WHERE id = ?",
                    (json.dumps(arqs_atuais, ensure_ascii=False), servico_id),
                )
        else:
            cliente_id = info_cli["cliente_id"]
            identificado = 1 if info_cli["identificado"] else 0
            fatura_anterior = 0.0
            if cliente_id:
                row_c = conn.execute(
                    "SELECT fatura_anterior FROM clientes WHERE id = ?",
                    (cliente_id,),
                ).fetchone()
                if row_c:
                    fatura_anterior = float(row_c["fatura_anterior"] or 0.0)

            cur_l = conn.execute(
                """
                INSERT INTO lancamentos
                (cliente_id, cliente_nome_original, identificado, origem, data_lancamento,
                 valor_entrega, valor_pagamento, fatura_anterior, pagamento_fatura_anterior,
                 saldo_fatura_anterior, observacao)
                VALUES (?, ?, ?, 'hotfolder', ?, 0.0, 0.0, ?, 0.0, ?, ?)
                """,
                (
                    cliente_id,
                    info_cli["cliente_nome_original"],
                    identificado,
                    data_ref,
                    fatura_anterior,
                    fatura_anterior,
                    f"Auto Hot Folder ({nome_pasta_produto})",
                ),
            )
            lancamento_id = cur_l.lastrowid

            pag_int = int(pagina) if (pagina and str(pagina).isdigit()) else 1
            cor_label = f"P{pag_int}-{cor}" if (pag_int > 1 and cor != "UNICA") else cor
            valor_inicial = round(1 * preco_unitario, 2)
            cur_s = conn.execute(
                """
                INSERT INTO servicos
                (lancamento_id, produto_id, descricao, quantidade, valor, cores_detectadas, arquivos_origem, pasta_origem)
                VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    lancamento_id,
                    produto_id,
                    info_cli["descricao_servico"],
                    valor_inicial,
                    cor_label,
                    json.dumps([nome_arquivo], ensure_ascii=False),
                    nome_pasta_produto,
                ),
            )
            servico_id = cur_s.lastrowid

            if produto_id is not None:
                conn.execute(
                    """
                    UPDATE produtos
                    SET estoque_atual = estoque_atual - 1,
                        estoque_consumido = estoque_consumido + 1
                    WHERE id = ?
                    """,
                    (produto_id,),
                )

        conn.execute(
            """
            INSERT INTO arquivos_monitorados
            (caminho_completo, nome_arquivo, pasta_produto, chave_agrupamento,
             cor_detectada, pagina_detectada, lancamento_id, servico_id, data_lancamento, ignorado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                caminho_abs,
                nome_arquivo,
                nome_pasta_produto,
                chave_agrupamento,
                cor,
                pagina or "",
                lancamento_id,
                servico_id,
                data_ref,
            ),
        )

    conn.close()
    return {
        "arquivo": nome_arquivo,
        "pasta": nome_pasta_produto,
        "cliente_id": info_cli["cliente_id"],
        "cliente_nome": info_cli["cliente_nome"],
        "descricao_servico": info_cli["descricao_servico"],
        "cor": cor,
        "identificado": info_cli["identificado"],
        "lancamento_id": lancamento_id,
        "servico_id": servico_id,
    }


def escanear_diretorio_hotfolder(diretorio_raiz):
    """
    Escaneia todas as subpastas dentro de diretorio_raiz (ex: \\RIPCTP\Manuela\OutPut ou pasta local).
    Coleta APENAS arquivos .tif, .tiff ou .tff respeitando a data real de cada arquivo.
    """
    resultados = []
    if not diretorio_raiz or not os.path.exists(diretorio_raiz):
        return resultados

    try:
        entradas = sorted(os.listdir(diretorio_raiz))
    except Exception:
        return resultados

    for item in entradas:
        sub_path = os.path.join(diretorio_raiz, item)
        if os.path.isdir(sub_path):
            for root_dir, _, files in os.walk(sub_path):
                arquivos_tiff = sorted([f for f in files if eh_arquivo_tiff_valido(f)])
                for arq in arquivos_tiff:
                    arq_path = os.path.join(root_dir, arq)
                    try:
                        res = processar_arquivo_hotfolder(
                            arq_path,
                            nome_pasta_produto=item,
                            arquivos_irmaos=arquivos_tiff,
                        )
                        if res:
                            resultados.append(res)
                    except Exception as e:
                        print(f"Erro ao processar arquivo {arq_path}: {e}")
    return resultados


def executar_ciclo_monitoramento():
    """
    Remove registros sem extensão .tif/.tiff/.tff, corrige datas, reagrupa lançamentos antigos
    que estavam separados por cor/sem espaço e executa a varredura nas pastas configuradas.
    """
    limpar_e_corrigir_registros_monitorados()
    cfg = get_config()
    novos = []

    net_path = (cfg.get("hotfolder_network_path") or "").strip()
    local_path = os.path.join(BASE_DIR, "hotfolder_output")

    for pasta_padrao in ["510x400", "660x530", "650x550", "521", "745x605", "724", "Solna"]:
        os.makedirs(os.path.join(local_path, pasta_padrao), exist_ok=True)

    if net_path and os.path.exists(net_path):
        novos.extend(escanear_diretorio_hotfolder(net_path))

    if os.path.exists(local_path) and os.path.abspath(local_path) != os.path.abspath(net_path or ""):
        novos.extend(escanear_diretorio_hotfolder(local_path))

    return novos


class HotFolderWatcherThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.last_scan = None
        self.total_detected = 0

    def run(self):
        while self.running:
            try:
                cfg = get_config()
                if cfg.get("hotfolder_ativo", "1") == "1":
                    novos = executar_ciclo_monitoramento()
                    self.last_scan = datetime.now().strftime("%H:%M:%S")
                    if novos:
                        self.total_detected += len(novos)
                intervalo = max(2, int(cfg.get("hotfolder_intervalo_seg") or 5))
            except Exception:
                intervalo = 5
            time.sleep(intervalo)
