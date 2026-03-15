# -*- coding: utf-8 -*-
"""
agente.py — Lógica do agente MAIA (determinístico + wrappers LLM)
-----------------------------------------------------------------
- SEMPRE consulta as bases locais (perfil_investidor.json, transacoes.csv, produtos_financeiros.json)
- Guardrails (LGPD, fora de escopo)
- Normalização de texto (sem acentos) + regex → matching menos rígido
- Formatação Markdown + rodapé de Fontes
- Determinísticos: orçamento, saldo, gasto total, gasto por categoria, maior gasto, metas
- Produtos: listagem/explicação e “quanto rende X?”
- Recomendação EDUCATIVA compatível com o perfil (sem recomendar ativo específico)
- Perfil do investidor (resposta direta)
- Montar contexto (para botão da sidebar “Ver contexto atual”)
- Wrappers do Ollama (LLM opcional; apenas reescreve, não cria fatos)
"""

from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta
import re
import unicodedata
import json
import pandas as pd

# =========================
# Guardrails (LGPD & Escopo)
# =========================
SENSIVEIS_PATTERNS = [
    r"\bsenha\b", r"\btoken\b", r"\bcvv\b", r"\bcvc\b",
    r"\bcpf\b", r"\bn[úu]mero do cart[aã]o\b", r"\bcart[aã]o\b"
]
FORA_ESCOPO_PATTERNS = [
    r"\btempo\b", r"\bclima\b", r"previs[aã]o do tempo", r"meteorologia",
    r"medicina", r"diagn[oó]stico", r"programa[cç][aã]o"
]

def eh_sensivel(texto: str) -> bool:
    t = (texto or "").lower()
    return any(re.search(p, t) for p in SENSIVEIS_PATTERNS)

def fora_escopo(texto: str) -> bool:
    t = (texto or "").lower()
    return any(re.search(p, t) for p in FORA_ESCOPO_PATTERNS)

# =========================
# Normalização / utilidades
# =========================
def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def _normaliza(txt: str) -> str:
    t = (txt or "").strip().lower()
    t = _strip_accents(t)
    return t

def extrair_primeiro_nome(nome_raw: Optional[str]) -> str:
    try:
        if not nome_raw or not isinstance(nome_raw, str):
            return "cliente"
        nome = nome_raw.strip()
        tokens = [t for t in nome.split() if len(t) > 1]
        if not tokens:
            return "cliente"
        stop = {"da", "de", "do", "das", "dos", "e"}
        for t in tokens:
            if t.lower() not in stop:
                return t
        return tokens[0]
    except Exception:
        return "cliente"

# =========================
# Formatação e templates
# =========================
def fmt_moeda(valor: float) -> str:
    s = f"{valor:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def md_titulo(texto: str) -> str:
    return f"**{texto}**"

def md_subtitulo(texto: str) -> str:
    return f"**{texto}**"

def md_lista(itens: List[str]) -> str:
    return "\n".join([f"- {i}" for i in itens])

def md_disclaimer() -> str:
    return "_Disclaimer: estimativa/educativo; não constitui recomendação._"

def fonte_rodape(arquivos: List[str]) -> str:
    unicos = sorted(set([str(a) for a in arquivos if a]))
    if not unicos:
        return ""
    return "\n\n> **Fontes**: " + ", ".join(unicos) + "."

# --- TEMPLATE de produtos (para evitar NameError) ---
def tpl_resposta_produtos(resumos: List[str], dicas: List[str]) -> str:
    lista_prod = md_lista(resumos) if resumos else "- (Nenhum produto encontrado)"
    lista_dicas = md_lista(dicas) if dicas else ""
    return (
        f"{md_titulo('📚 Produtos relacionados')}\n\n"
        f"{lista_prod}\n\n"
        f"{md_disclaimer()}"
        f"{fonte_rodape(['produtos_financeiros.json'])}\n\n"
        f"{lista_dicas}"
    )

# =========================
# Determinísticos principais
# =========================
def analisar_orcamento(df_tx: pd.DataFrame, janela_dias: int = 30, max_linhas: int = 10) -> Tuple[str, Dict]:
    if df_tx is None or df_tx.empty:
        return ("Não encontrei transações para analisar. "
                "Podemos ajustar a janela ou importar a base primeiro."
                + fonte_rodape(['transacoes.csv'])), {
            "janela_dias": janela_dias, "entrada": 0.0, "saida": 0.0, "saldo": 0.0, "top_categorias": []
        }

    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df = df_tx[df_tx["data"].dt.date >= inicio].copy()
    if df.empty:
        df = df_tx.copy()

    total_saida = float(df.loc[_normaliza_series(df["tipo"]) == "saida", "valor"].sum())
    total_entrada = float(df.loc[_normaliza_series(df["tipo"]) != "saida", "valor"].sum())
    saldo = total_entrada - total_saida

    por_cat = (
        df[_normaliza_series(df["tipo"]) == "saida"]
        .groupby("categoria")["valor"].sum()
        .sort_values(ascending=False)
        .head(5)
    )
    top_categorias = [(cat, float(v)) for cat, v in por_cat.items()]

    sample = df.sort_values("data", ascending=False).head(max_linhas)
    ultimas_tx = []
    for _, r in sample.iterrows():
        data_fmt = r["data"].strftime("%Y-%m-%d") if pd.notnull(r["data"]) else "----"
        val_fmt = fmt_moeda(float(r["valor"]))
        ultimas_tx.append(f"{data_fmt} · {r['descricao']} · {r['categoria']} · {val_fmt} · {r['tipo']}")

    texto = (
        f"{md_titulo('📊 Análise de orçamento')}\n\n"
        f"{md_lista([f'Janela de análise: {janela_dias} dias', f'Entradas: {fmt_moeda(total_entrada)}', f'Saídas: {fmt_moeda(total_saida)}', f'Saldo: {fmt_moeda(saldo)}'])}\n\n"
        f"{md_subtitulo('Principais categorias de despesa')}\n"
        f"{md_lista([f'**{c}**: {fmt_moeda(v)}' for c, v in top_categorias]) if top_categorias else '- (Sem despesas no período)'}\n\n"
        f"{md_subtitulo('Últimas transações')}\n"
        f"{md_lista(ultimas_tx) if ultimas_tx else '- (Sem transações no período)'}\n\n"
        f"{md_disclaimer()}"
        f"{fonte_rodape(['transacoes.csv'])}"
    )
    fatos = {"janela_dias": janela_dias, "entrada": total_entrada, "saida": total_saida, "saldo": saldo, "top_categorias": top_categorias}
    return texto, fatos

def simular_meta_dados(valor_meta: float, meses: int, aporte_inicial: float = 0.0, taxa_mensal: float = 0.0) -> Tuple[str, Optional[Dict]]:
    if meses <= 0:
        return "O prazo informado é inválido. Use ao menos 1 mês.", None

    if taxa_mensal <= 0:
        restante = max(0.0, valor_meta - aporte_inicial)
        aporte_mensal = restante / meses
    else:
        i = taxa_mensal
        fator = ((1 + i) ** meses - 1) / i
        restante = max(0.0, valor_meta - aporte_inicial * ((1 + i) ** meses))
        aporte_mensal = (restante / fator) if fator > 0 else restante / meses

    taxa_txt = f"{taxa_mensal*100:.2f}% a.m." if taxa_mensal > 0 else "sem taxa (estimativa conservadora)"
    texto = (
        f"{md_titulo('🎯 Simulação de meta')}\n\n"
        f"{md_lista([f'Meta: {fmt_moeda(valor_meta)}', f'Prazo: {meses} meses', f'Consideração: {taxa_txt}'])}\n\n"
        f"{md_subtitulo('➡️ Aporte mensal estimado:')} {md_titulo(fmt_moeda(aporte_mensal))}\n\n"
        f"Quer ver o passo a passo do cálculo?\n\n"
        f"{md_disclaimer()}"
    )
    fatos = {"meta_total": valor_meta, "meses": meses, "aporte_inicial": aporte_inicial, "taxa_mensal": taxa_mensal, "aporte_mensal": aporte_mensal}
    return texto, fatos

def resumo_maior_gasto(df_tx: pd.DataFrame, janela_dias: int = 30) -> str:
    if df_tx is None or df_tx.empty:
        return ("Não encontrei transações para analisar. Podemos ajustar a janela ou importar a base primeiro."
                + fonte_rodape(['transacoes.csv']))

    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df = df_tx[df_tx["data"].dt.date >= inicio].copy()
    if df.empty:
        df = df_tx.copy()

    df_saida = df[_normaliza_series(df["tipo"]) == "saida"].copy()
    if df_saida.empty:
        return (
            f"{md_titulo('📉 Maior gasto no período')}\n\n"
            f"Na janela de {janela_dias} dias não encontrei despesas registradas.\n\n"
            f"{md_disclaimer()}"
            f"{fonte_rodape(['transacoes.csv'])}"
        )

    por_cat = df_saida.groupby("categoria")["valor"].sum().sort_values(ascending=False)
    cat_top = por_cat.index[0]
    val_top = float(por_cat.iloc[0])

    idx_max = df_saida["valor"].idxmax()
    row_max = df_saida.loc[idx_max]
    data_fmt = row_max["data"].strftime("%Y-%m-%d") if pd.notnull(row_max["data"]) else "----"
    desc = str(row_max["descricao"])
    cat = str(row_max["categoria"])
    val = float(row_max["valor"])

    return (
        f"{md_titulo('📉 Maior gasto no período')}\n\n"
        f"{md_lista([f'Janela de análise: {janela_dias} dias', f'Categoria de maior despesa: **{cat_top}** ({fmt_moeda(val_top)})'])}\n\n"
        f"{md_subtitulo('Maior transação registrada')}\n"
        f"- {data_fmt} · {desc} · {cat} · {fmt_moeda(val)}\n\n"
        f"{md_disclaimer()}"
        f"{fonte_rodape(['transacoes.csv'])}"
    )

# =========================
# Orçamento: saldo / gasto total / gasto por categoria
# =========================
def eh_intencao_saldo(texto: str) -> bool:
    t = _normaliza(texto)
    gatilhos = [
        "saldo", "quanto sobrou", "quanto tenho sobrando",
        "quanto ficou no final", "sobrou quanto", "quanto resta", "quanto restou"
    ]
    padroes = [
        r".*\bquanto\b.*\bsobrou\b.*",
        r".*\bsaldo\b.*",
        r".*\bquanto\b.*\brest(ou|a)\b.*",
    ]
    return any(g in t for g in gatilhos) or any(re.search(p, t) for p in padroes)

def resposta_saldo(df_tx: pd.DataFrame, janela_dias: int = 30) -> str:
    if df_tx is None or df_tx.empty:
        return ("Não encontrei transações para analisar. Podemos ajustar a janela ou importar a base primeiro."
                + fonte_rodape(['transacoes.csv']))
    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df = df_tx[df_tx["data"].dt.date >= inicio].copy()
    if df.empty:
        df = df_tx.copy()

    total_saida = float(df.loc[_normaliza_series(df["tipo"]) == "saida", "valor"].sum())
    total_entrada = float(df.loc[_normaliza_series(df["tipo"]) != "saida", "valor"].sum())
    saldo = total_entrada - total_saida

    return (
        f"{md_titulo('💰 Saldo no período')}\n\n"
        f"{md_lista([f'Janela de análise: {janela_dias} dias', f'Entradas: {fmt_moeda(total_entrada)}', f'Saídas: {fmt_moeda(total_saida)}', f'Saldo: {fmt_moeda(saldo)}'])}\n\n"
        f"{md_disclaimer()}"
        f"{fonte_rodape(['transacoes.csv'])}"
    )

def eh_intencao_total_gasto(texto: str) -> bool:
    t = _normaliza(texto)
    gatilhos = [
        "quanto gastei", "gastei quanto", "total gasto", "total de gastos",
        "gastos no periodo", "quanto gastei no periodo", "gastei no periodo"
    ]
    padroes = [
        r"^\s*quanto gastei\??\s*$",
        r"^\s*gastei quanto\??\s*$",
        r".*\btotal\b.*\bgast[oa]s?\b.*",
    ]
    return any(g in t for g in gatilhos) or any(re.search(p, t) for p in padroes)

def resposta_total_gasto(df_tx: pd.DataFrame, janela_dias: int = 30) -> str:
    if df_tx is None or df_tx.empty:
        return ("Não encontrei transações para analisar. Podemos ajustar a janela ou importar a base primeiro."
                + fonte_rodape(['transacoes.csv']))
    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df = df_tx[df_tx["data"].dt.date >= inicio].copy()
    if df.empty:
        df = df_tx.copy()

    total_saida = float(df.loc[_normaliza_series(df["tipo"]) == "saida", "valor"].sum())

    return (
        f"{md_titulo('🧾 Gasto total no período')}\n\n"
        f"{md_lista([f'Janela de análise: {janela_dias} dias', f'Gasto total: {fmt_moeda(total_saida)}'])}\n\n"
        f"{md_disclaimer()}"
        f"{fonte_rodape(['transacoes.csv'])}"
    )

CATEGORIA_SINONIMOS = {
    "alimentacao": ["alimentacao", "alimentação", "restaurante", "supermercado", "mercado", "comida", "refeicao"],
    "transporte": ["transporte", "uber", "combustivel", "combustível", "gasolina"],
    "lazer": ["lazer", "netflix", "cinema", "entretenimento"],
    "moradia": ["moradia", "aluguel", "condominio", "luz", "agua", "energia"],
    "saude": ["saude", "saúde", "farmacia", "farmácia", "medico", "médico", "plano"],
}

def _normaliza_series(s: pd.Series) -> pd.Series:
    return s.astype(str).map(_normaliza)

def _mapear_categoria(user_txt: str, categorias_base: List[str]) -> Optional[str]:
    t = _normaliza(user_txt)
    for canon, lista in CATEGORIA_SINONIMOS.items():
        for s in lista:
            if _normaliza(s) in t:
                return canon
    for c in categorias_base:
        if _normaliza(c) in t:
            return _normaliza(c)
    return None

def eh_intencao_gasto_categoria(texto: str) -> bool:
    t = _normaliza(texto)
    padroes = [
        r"quanto gastei (em|no|na|com) .+",
        r"gastei quanto (em|no|na|com) .+",
        r"gasto (em|no|na|com) .+",
        r"quanto gastei .*aliment"
    ]
    return any(re.search(p, t) for p in padroes)

def resposta_gasto_categoria(df_tx: pd.DataFrame, pergunta: str, janela_dias: int = 30) -> str:
    if df_tx is None or df_tx.empty:
        return ("Não encontrei transações para analisar. Podemos ajustar a janela ou importar a base primeiro."
                + fonte_rodape(['transacoes.csv']))

    categorias_existentes = sorted(set(df_tx["categoria"].astype(str).tolist()))
    cat = _mapear_categoria(pergunta, categorias_existentes)
    if not cat:
        return (
            "Não identifiquei a categoria corretamente nessa pergunta. "
            "Você pode repetir, por exemplo: *'Quanto gastei com alimentação?'*"
            + fonte_rodape(['transacoes.csv'])
        )

    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df = df_tx[df_tx["data"].dt.date >= inicio].copy()
    if df.empty:
        df = df_tx.copy()

    df_cat = df[(_normaliza_series(df["tipo"]) == "saida") & (_normaliza_series(df["categoria"]) == cat)]
    total = float(df_cat["valor"].sum())

    return (
        f"{md_titulo('🍽️ Gasto por categoria')}\n\n"
        f"{md_lista([f'Categoria: **{cat}**', f'Janela de análise: {janela_dias} dias', f'Total gasto: {fmt_moeda(total)}'])}\n\n"
        f"{md_disclaimer()}"
        f"{fonte_rodape(['transacoes.csv'])}"
    )

# =========================
# Maior gasto — intenção
# =========================
def eh_intencao_maior_gasto(texto: str) -> bool:
    t = _normaliza(texto)
    gatilhos = [
        "maior gasto", "maior despesa", "gasto mais alto", "despesa mais alta",
        "categoria mais cara", "qual foi meu maior gasto", "qual foi o meu maior gasto",
        "top gasto", "top despesa"
    ]
    padroes = [
        r".*\bmaior\b.*\bgasto\b.*",
        r".*\bmaior\b.*\bdespesa\b.*",
        r".*\bcategoria\b.*\bmais\b.*\bcara\b.*",
    ]
    return any(g in t for g in gatilhos) or any(re.search(p, t) for p in padroes)

# =========================
# Produtos — busca / rentabilidade
# =========================
def buscar_produto(pergunta: str, produtos: List[Dict]) -> Tuple[str, List[Dict]]:
    t = _normaliza(pergunta)
    encontrados = []
    for p in produtos:
        nome = _normaliza(str(p.get("nome", "")))
        cat = _normaliza(str(p.get("categoria", "")))

        if nome and nome.split() and nome.split()[0] in t and p not in encontrados:
            encontrados.append(p)
        if cat and cat in t and p not in encontrados:
            encontrados.append(p)

        for chave in ["tesouro", "cdb", "lci", "lca", "acoes", "fii", "bdr", "cripto", "criptoativos"]:
            if (chave in t) and (chave in nome) and (p not in encontrados):
                encontrados.append(p)

    if not encontrados:
        texto = tpl_resposta_produtos(
            resumos=[
                "Tesouro Selic — renda fixa, risco baixo",
                "CDB — renda fixa, risco baixo",
                "LCI/LCA — renda fixa, risco baixo (carência)",
                "Ações — renda variável, risco alto",
                "FIIs — renda variável, risco alto",
                "Criptoativos — alta volatilidade",
                "BDRs — renda variável, com exposição ao dólar"
            ],
            dicas=[]
        )
        return texto, []

    resumos, fatos_prod, dicas = [], [], []
    for p in encontrados[:6]:
        resumos.append(
            f"**{p.get('nome')}** ({p.get('categoria')}, risco: {p.get('risco')}) — "
            f"rentabilidade: {p.get('rentabilidade')}; aporte mínimo: {fmt_moeda(float(p.get('aporte_minimo', 0.0)))}"
        )
        fatos_prod.append({
            "nome": p.get("nome"),
            "categoria": p.get("categoria"),
            "risco": p.get("risco"),
            "rentabilidade": p.get("rentabilidade"),
            "aporte_minimo": float(p.get("aporte_minimo", 0.0))
        })

    if any("bdr" in _normaliza(p.get("nome","")) for p in encontrados):
        dicas.append("BDRs têm **exposição ao dólar** (variação cambial impacta os preços).")
    if any("cripto" in _normaliza(p.get("nome","")) for p in encontrados):
        dicas.append("Criptoativos possuem **alta volatilidade**; valores podem oscilar rapidamente.")

    texto = tpl_resposta_produtos(resumos, dicas)
    return texto, fatos_prod

def eh_intencao_rentabilidade_produto(texto: str) -> Optional[str]:
    t = _normaliza(texto)
    m = re.search(r"quanto rende (o|a|um|uma)?\s*(.+)", t)
    if m:
        return m.group(2).strip()
    return None

def resposta_rentabilidade_produto(produtos: List[Dict], nome_busca: str) -> str:
    nome_norm = _normaliza(nome_busca)
    match = None
    for p in produtos:
        if nome_norm in _normaliza(p.get("nome","")):
            match = p
            break
    if not match:
        return (
            f"Não encontrei **{nome_busca}** em nossa base de produtos. "
            "Posso listar alternativas da mesma categoria, se quiser."
            + fonte_rodape(['produtos_financeiros.json'])
        )

    return (
        f"{md_titulo('ℹ️ Rentabilidade informada na base')}\n\n"
        f"- **Produto:** {match.get('nome')}\n"
        f"- **Categoria:** {match.get('categoria')}  ·  **Risco:** {match.get('risco')}\n"
        f"- **Rentabilidade (descrição):** {match.get('rentabilidade')}\n"
        f"- **Aporte mínimo:** {fmt_moeda(float(match.get('aporte_minimo', 0.0)))}\n\n"
        f"{md_disclaimer()}"
        + fonte_rodape(['produtos_financeiros.json'])
    )

# =========================
# Recomendação EDUCATIVA por perfil + reserva (sem alucinação)
# =========================
def eh_intencao_recomendacao(texto: str) -> bool:
    t = _normaliza(texto)
    gatilhos = [
        "onde investir", "o que investir", "qual investimento",
        "recomenda pra mim", "recomendacao", "recomendaria",
        "melhor investimento", "melhor aplicacao", "aplicar dinheiro",
        "melhor lugar para investir", "me indica um investimento",
        "o que vc indica para investir", "em que devo investir"
    ]
    padroes = [
        r".*\b(recomend|indica|sugere)\b.*\binvest(ir|imento)\b.*",
        r".*\bonde\b.*\binvest(ir)?\b.*",
    ]
    return any(g in t for g in gatilhos) or any(re.search(p, t) for p in padroes)

def gasto_medio_mensal(df_tx: pd.DataFrame, janela_dias: int) -> float:
    if df_tx is None or df_tx.empty:
        return 0.0
    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df = df_tx[df_tx["data"].dt.date >= inicio].copy()
    if df.empty:
        df = df_tx.copy()
    saidas = df[_normaliza_series(df["tipo"]) == "saida"]["valor"].sum()
    fator = 30 / max(1, janela_dias)
    return float(saidas * fator)

def extrair_reserva_existente(perfil: Dict) -> float:
    try:
        metas = perfil.get("metas", []) or []
        for m in metas:
            nome = str(m.get("meta","")).lower()
            if "reserva" in nome:
                for k in ["acumulado", "valor_ja_guardado", "guardado"]:
                    if k in m:
                        return float(m.get(k, 0.0))
        return 0.0
    except Exception:
        return 0.0

def _compatibilizar_produtos_por_perfil(perfil: Dict, produtos: List[Dict]) -> List[Dict]:
    perf = _normaliza(str(perfil.get("perfil_investidor","")))
    if "conserv" in perf:
        alvo = {"baixo"}
    elif "moder" in perf:
        alvo = {"baixo", "medio", "médio"}
    elif "arroj" in perf or "agress" in perf:
        alvo = {"baixo", "medio", "médio", "alto"}
    else:
        alvo = {"baixo", "medio", "médio"}

    out = []
    for p in produtos:
        r = _normaliza(str(p.get("risco","")))
        if r in alvo:
            out.append(p)
    return out[:6]

def resposta_recomendacao_contextual(df_tx: pd.DataFrame, perfil: Dict, produtos: List[Dict], janela_dias: int = 30) -> str:
    perfil_inv = str(perfil.get("perfil_investidor","")).strip()
    if not perfil_inv:
        return ("Não encontrei seu **perfil de investidor** na base. "
                "Atualize o `perfil_investidor.json` para personalizar melhor a explicação."
                + fonte_rodape(['perfil_investidor.json']))

    nome = perfil.get("nome")
    primeiro = extrair_primeiro_nome(nome) if nome else "cliente"
    trat = f"Sr {primeiro}" if primeiro != "cliente" else "cliente"

    gasto_mensal = gasto_medio_mensal(df_tx, janela_dias)
    alvo_3m = gasto_mensal * 3
    alvo_6m = gasto_mensal * 6
    ja_tem = extrair_reserva_existente(perfil)

    compativeis = _compatibilizar_produtos_por_perfil(perfil, produtos)
    if not compativeis:
        lista_prod = "- (Não encontrei produtos compatíveis na base atual)"
    else:
        linhas = []
        for p in compativeis:
            linhas.append(
                f"- **{p.get('nome')}** ({p.get('categoria')}, risco: {p.get('risco')}, liquidez: {p.get('liquidez','-')}) — {p.get('rentabilidade')}"
            )
        lista_prod = "\n".join(linhas)

    partes = []
    partes.append(f"**Oi, {trat}!**\n\nPara falar de investimentos com segurança, começamos pela **reserva de emergência**.")
    partes.append(
        f"\n**Estimativa baseada nas suas saídas (janela de {janela_dias} dias):**\n"
        f"- Gasto mensal aproximado: **{fmt_moeda(gasto_mensal)}**\n"
        f"- Reserva sugerida (3–6 meses): **{fmt_moeda(alvo_3m)}** a **{fmt_moeda(alvo_6m)}**"
    )
    if ja_tem > 0:
        falta_3m = max(0.0, alvo_3m - ja_tem)
        falta_6m = max(0.0, alvo_6m - ja_tem)
        partes.append(
            f"\nNo seu perfil, consta que você **já possui ~{fmt_moeda(ja_tem)}** guardados. "
            f"Para **3 meses**, faltaria ~**{fmt_moeda(falta_3m)}**; para **6 meses**, ~**{fmt_moeda(falta_6m)}**."
        )
    else:
        partes.append("\nNão localizei valor já acumulado para a reserva no seu perfil.")

    partes.append(
        f"\n**Exemplos educativos compatíveis com seu perfil ({perfil_inv}):**\n{lista_prod}\n\n"
        "> ℹ️ *Conteúdo educativo; não constitui recomendação.*"
    )
    partes.append(
        "\n**Próximo passo (se quiser):** posso **simular** quanto guardar por mês "
        "para atingir a reserva desejada no seu prazo."
    )
    partes.append(fonte_rodape(['transacoes.csv', 'perfil_investidor.json', 'produtos_financeiros.json']))

    return "".join(partes)

# =========================
# Perfil do investidor (resposta direta)
# =========================
def eh_intencao_perfil_investidor(texto: str) -> bool:
    t = _normaliza(texto)
    gatilhos = [
        "meu perfil de investidor", "qual meu perfil", "qual o meu perfil",
        "perfil de investidor", "meu perfil investidor", "sou conservador", "sou moderado", "sou arrojado"
    ]
    return any(g in t for g in gatilhos)

def resposta_perfil_investidor(perfil: Dict) -> str:
    nome = perfil.get("nome", "-")
    perfil_inv = perfil.get("perfil_investidor", "-")
    renda = perfil.get("renda_mensal", "-")
    objetivo = perfil.get("objetivo_principal", "-")
    metas = perfil.get("metas", [])
    qtd_metas = len(metas) if isinstance(metas, list) else 0

    return (
        f"{md_titulo('🧾 Seu perfil de investidor')}\n\n"
        f"{md_lista([f'Nome: {nome}', f'Perfil: **{perfil_inv}**', f'Renda mensal: {renda}', f'Objetivo principal: {objetivo}', f'Quantidade de metas: {qtd_metas}'])}\n\n"
        f"{md_disclaimer()}"
        f"{fonte_rodape(['perfil_investidor.json'])}"
    )

# =========================
# Montar contexto (para sidebar)
# =========================
def montar_contexto(df_tx: pd.DataFrame, df_hist: pd.DataFrame, perfil: Dict, produtos: List[Dict],
                    janela_dias: int = 30, max_tx: int = 10, max_hist: int = 3) -> str:
    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df_tx_sel = df_tx[df_tx["data"].dt.date >= inicio].sort_values("data", ascending=False)
    if df_tx_sel.empty:
        df_tx_sel = df_tx.sort_values("data", ascending=False)
    tx_txt = df_tx_sel.head(max_tx).to_string(index=False)

    hist_txt = df_hist.sort_values("data", ascending=False).head(max_hist).to_string(index=False)
    prod_txt = json.dumps(produtos[:5], ensure_ascii=False, indent=2)

    out = []
    out.append("## Perfil")
    out.append(json.dumps(perfil, ensure_ascii=False, indent=2))
    out.append(f"\n## Transações (últimas {max_tx})")
    out.append(tx_txt)
    out.append(f"\n## Histórico (últimos {max_hist})")
    out.append(hist_txt)
    out.append("\n## Produtos (amostra)")
    out.append(prod_txt)
    return "\n".join(out)

# =========================
# Wrappers do Ollama (LLM)
# =========================
def perguntar_ollama(system_prompt: str, user_content: str, url: str, modelo: str) -> Optional[str]:
    try:
        import requests
        payload = {
            "model": modelo,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "options": {"temperature": 0.2}
        }
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "message" in data and "content" in data["message"]:
            return data["message"]["content"]
        if "messages" in data and isinstance(data["messages"], list) and data["messages"]:
            return data["messages"][-1].get("content", "")
        return None
    except Exception:
        return None

def reescrever_com_llm(usar_llm: bool, modelo: str, system_prompt: str,
                       instrucoes: str, fatos: str, url: str, fontes: Optional[List[str]] = None) -> Optional[str]:
    if not usar_llm:
        return None
    fontes_txt = ""
    if fontes:
        unicos = ", ".join(sorted(set([str(a) for a in fontes])))
        fontes_txt = f"\n\nFONTES (use e cite no final): {unicos}"
    conteudo = (
        "Reescreva de forma clara e didática, mantendo TODOS os números e fatos. "
        "Use Markdown com títulos e bullets quando fizer sentido. "
        "NÃO invente dados, NÃO recomende investimentos."
        f"{fontes_txt}\n\n"
        f"INSTRUÇÕES:\n{instrucoes}\n\nFATOS:\n{fatos}"
    )
    return perguntar_ollama(system_prompt, conteudo, url, modelo)
