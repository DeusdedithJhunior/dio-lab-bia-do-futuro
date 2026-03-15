# -*- coding: utf-8 -*-
"""
agente.py — Lógica do agente MAIA
----------------------------------
Sem dependências de Streamlit (UI). Somente lógica, formatação, cálculos e wrappers do LLM.
"""

from typing import Optional, Tuple, List, Dict
from datetime import datetime, timedelta
import re
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
    t = texto.lower()
    return any(re.search(p, t) for p in SENSIVEIS_PATTERNS)

def fora_escopo(texto: str) -> bool:
    t = texto.lower()
    return any(re.search(p, t) for p in FORA_ESCOPO_PATTERNS)

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

def md_obs(texto: str) -> str:
    return f"\n> ℹ️ *{texto}*\n"

def md_disclaimer() -> str:
    return "_Disclaimer: estimativa/educativo; não constitui recomendação._"

def tpl_resposta_meta(valor_meta: float, meses: int, aporte_mensal: float, taxa_txt: str) -> str:
    return (
        f"{md_titulo('🎯 Simulação de meta')}\n\n"
        f"{md_lista([f'Meta: {fmt_moeda(valor_meta)}', f'Prazo: {meses} meses', f'Consideração: {taxa_txt}'])}\n\n"
        f"{md_subtitulo('➡️ Aporte mensal estimado:')} {md_titulo(fmt_moeda(aporte_mensal))}\n\n"
        f"Quer ver o passo a passo do cálculo?\n\n"
        f"{md_disclaimer()}"
    )

def tpl_resposta_orcamento(total_entrada: float, total_saida: float, saldo: float, top_categorias: List[Tuple[str, float]], ultimas_tx: List[str], janela_dias: int) -> str:
    linhas_cat = md_lista([f"**{c}**: {fmt_moeda(v)}" for c, v in top_categorias]) if top_categorias else "- (Sem despesas no período)"
    linhas_tx = md_lista(ultimas_tx) if ultimas_tx else "- (Sem transações no período)"
    return (
        f"{md_titulo('📊 Análise de orçamento')}\n\n"
        f"{md_lista([f'Janela de análise: {janela_dias} dias', f'Entradas: {fmt_moeda(total_entrada)}', f'Saídas: {fmt_moeda(total_saida)}', f'Saldo: {fmt_moeda(saldo)}'])}\n\n"
        f"{md_subtitulo('Principais categorias de despesa')}\n{linhas_cat}\n\n"
        f"{md_subtitulo('Últimas transações')}\n{linhas_tx}\n\n"
        f"{md_disclaimer()}"
    )

def tpl_resposta_produtos(resumos: List[str], dicas: List[str]) -> str:
    lista_prod = md_lista(resumos)
    lista_dicas = md_lista(dicas) if dicas else ""
    return (
        f"{md_titulo('📚 Produtos relacionados')}\n\n"
        f"{lista_prod}\n"
        f"{md_obs('Fonte: produtos_financeiros.json')}\n"
        f"{lista_dicas}\n"
        f"_Conteúdo educativo e mockado para o MVP; não constitui recomendação._"
    )

# =========================
# Determinísticos (cálculos)
# =========================
def analisar_orcamento(df_tx: pd.DataFrame, janela_dias: int = 30, max_linhas: int = 10) -> Tuple[str, Dict]:
    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df = df_tx[df_tx["data"].dt.date >= inicio].copy()
    if df.empty:
        df = df_tx.copy()

    total_saida = float(df.loc[df["tipo"].str.lower() == "saida", "valor"].sum())
    total_entrada = float(df.loc[df["tipo"].str.lower() != "saida", "valor"].sum())
    saldo = total_entrada - total_saida

    por_cat = (
        df[df["tipo"].str.lower() == "saida"]
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

    texto = tpl_resposta_orcamento(total_entrada, total_saida, saldo, top_categorias, ultimas_tx, janela_dias)
    fatos = {
        "janela_dias": janela_dias,
        "entrada": total_entrada,
        "saida": total_saida,
        "saldo": saldo,
        "top_categorias": top_categorias
    }
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
    texto = tpl_resposta_meta(valor_meta, meses, aporte_mensal, taxa_txt)
    fatos = {
        "meta_total": valor_meta,
        "meses": meses,
        "aporte_inicial": aporte_inicial,
        "taxa_mensal": taxa_mensal,
        "aporte_mensal": aporte_mensal
    }
    return texto, fatos

def resumo_maior_gasto(df_tx: pd.DataFrame, janela_dias: int = 30) -> str:
    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df = df_tx[df_tx["data"].dt.date >= inicio].copy()
    if df.empty:
        df = df_tx.copy()

    df_saida = df[df["tipo"].str.lower() == "saida"].copy()
    if df_saida.empty:
        return (
            f"{md_titulo('📉 Maior gasto no período')}\n\n"
            f"Na janela de {janela_dias} dias não encontrei despesas registradas.\n\n"
            f"{md_disclaimer()}"
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
    )

def buscar_produto(pergunta: str, produtos: List[Dict]) -> Tuple[str, List[Dict]]:
    t = pergunta.lower()
    encontrados = []
    for p in produtos:
        nome = str(p.get("nome", "")).lower()
        cat = str(p.get("categoria", "")).lower()
        if any(k in t for k in [nome.split()[0]]) or (cat and cat in t):
            encontrados.append(p)
        for chave in ["tesouro", "cdb", "lci", "lca", "ações", "acoes", "fii", "bdr", "cripto"]:
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

    if any("bdr" in str(p.get("nome", "")).lower() for p in encontrados):
        dicas.append("BDRs têm **exposição ao dólar** (variação cambial impacta os preços).")
    if any("cripto" in str(p.get("nome", "")).lower() for p in encontrados):
        dicas.append("Criptoativos possuem **alta volatilidade**; valores podem oscilar rapidamente.")

    texto = tpl_resposta_produtos(resumos, dicas)
    return texto, fatos_prod

# =========================
# Continuação ("sim") / Intenções
# =========================
AFFIRMATIVOS = {
    "sim", "claro", "ok", "isso", "isso mesmo", "por favor", "sim!", "s", "manda",
    "quero", "quero sim", "segue", "pode mostrar", "mostra", "mostrar", "pode explicar"
}
NEGATIVOS = {"nao", "não", "n", "agora nao", "depois", "fica para depois"}

def _normaliza(txt: str) -> str:
    t = txt.strip().lower()
    mapa = {"é": "e", "ê": "e", "á": "a", "ã": "a", "â": "a", "í": "i", "ó": "o", "ô": "o", "ú": "u"}
    for k, v in mapa.items():
        t = t.replace(k, v)
    return t

def eh_afirmativo(texto: str) -> bool:
    t = _normaliza(texto)
    return any(t == a or t.startswith(a) for a in AFFIRMATIVOS)

def eh_negativo(texto: str) -> bool:
    t = _normaliza(texto)
    return any(t == n or t.startswith(n) for n in NEGATIVOS)

def eh_intencao_maior_gasto(texto: str) -> bool:
    t = _normaliza(texto)
    gatilhos = [
        "maior gasto", "maior despesa", "gasto mais alto", "despesa mais alta",
        "categoria mais cara", "qual foi meu maior gasto", "qual foi o meu maior gasto"
    ]
    return any(g in t for g in gatilhos)

# =========================
# Montagem de contexto (para debug/inspeção)
# =========================
def montar_contexto(df_tx: pd.DataFrame,
                    df_hist: pd.DataFrame,
                    perfil: Dict,
                    produtos: List[Dict],
                    janela_dias: int = 30,
                    max_tx: int = 10,
                    max_hist: int = 3) -> str:
    nome = perfil.get("nome")
    renda_mensal = perfil.get("renda_mensal")
    perfil_inv = perfil.get("perfil_investidor")
    objetivo_principal = perfil.get("objetivo_principal")
    metas = perfil.get("metas", [])
    metas_fmt = "\n".join([
        f"- {m.get('meta')}: R$ {m.get('valor_necessario')} até {m.get('prazo')}"
        for m in metas
    ]) if metas else "- (sem metas registradas)"

    hoje = datetime.now().date()
    inicio = hoje - timedelta(days=janela_dias)
    df_tx_sel = df_tx[df_tx["data"].dt.date >= inicio].sort_values("data", ascending=False)
    if df_tx_sel.empty:
        df_tx_sel = df_tx.sort_values("data", ascending=False)
    df_tx_ctx = df_tx_sel.head(max_tx)

    def linha_tx(row):
        data_fmt = row["data"].strftime("%Y-%m-%d") if pd.notnull(row["data"]) else "----"
        valor_fmt = fmt_moeda(float(row['valor']))
        return f"- {data_fmt} · {row['descricao']} · {row['categoria']} · {valor_fmt} · {row['tipo']}"

    linhas_tx = "\n".join(df_tx_ctx.apply(linha_tx, axis=1).tolist())

    df_hist_sel = df_hist.sort_values("data", ascending=False).head(max_hist)
    linhas_hist = "\n".join([
        f"- {r['data'].strftime('%Y-%m-%d')}: {r['canal']} • {r['tema']} — {r['resumo']} (resolvido: {r['resolvido']})"
        for _, r in df_hist_sel.iterrows()
    ]) if not df_hist_sel.empty else "- (sem registros recentes)"

    def resumir_prod(p):
        nomep = p.get("nome", "Produto")
        cat = p.get("categoria", "-")
        risco = p.get("risco", "-")
        rent = p.get("rentabilidade", "Variável")
        return f"- {nomep} ({cat}, risco: {risco}) — rentabilidade: {rent}"
    linhas_prod = "\n".join([resumir_prod(p) for p in produtos])

    contexto = f"""
Perfil do cliente:
- Nome: {nome}
- Renda mensal: R$ {renda_mensal}
- Perfil investidor: {perfil_inv}
- Objetivo principal: {objetivo_principal}

Metas:
{metas_fmt}

Últimas transações (até {len(df_tx_ctx)} linhas):
{linhas_tx}

Interações recentes:
{linhas_hist}

Produtos de referência (fonte: produtos_financeiros.json):
{linhas_prod}
""".strip()
    return contexto

# =========================
# Explicação passo a passo (meta)
# =========================
def explicar_meta_step_by_step(meta: float, meses: int, aporte_inicial: float, taxa_mensal: float, aporte_mensal: float) -> str:
    meta_fmt = fmt_moeda(meta)
    aporte_ini_fmt = fmt_moeda(aporte_inicial)
    aporte_mensal_fmt = fmt_moeda(aporte_mensal)

    if taxa_mensal <= 0:
        return (
            f"{md_titulo('🧮 Passo a passo — meta sem juros (estimativa conservadora)')}\n\n"
            f"{md_lista([f'Meta (M): {meta_fmt}', f'Prazo (n): {meses} meses', f'Aporte inicial (P): {aporte_ini_fmt}', f'Taxa (i): 0% a.m.'])}\n\n"
            f"{md_subtitulo('Fórmula usada')}\n"
            f"Montante sem juros mensais: `M = P + A * n`\n\n"
            f"{md_subtitulo('Isolando o aporte mensal (A)')}\n"
            f"`A = (M - P) / n`\n\n"
            f"{md_subtitulo('Substituindo os valores')}\n"
            f"`A = ({meta_fmt} - {aporte_ini_fmt}) / {meses}`\n\n"
            f"{md_subtitulo('Resultado')}\n"
            f"**Aporte mensal estimado: {aporte_mensal_fmt}**\n\n"
            f"{md_disclaimer()}"
        )

    taxa_pct = f"{taxa_mensal*100:.2f}% a.m."
    return (
        f"{md_titulo('🧮 Passo a passo — meta com juros compostos (anuidade)')}\n\n"
        f"{md_lista([f'Meta (M): {meta_fmt}', f'Prazo (n): {meses} meses', f'Aporte inicial (P): {aporte_ini_fmt}', f'Taxa (i): {taxa_pct}'])}\n\n"
        f"{md_subtitulo('Fórmula do montante com anuidade')}\n"
        f"`M = P * (1+i)^n + A * ((1+i)^n - 1)/i`\n\n"
        f"{md_subtitulo('Isolando o aporte mensal (A)')}\n"
        f"`A = [ M - P * (1+i)^n ]  *  i / [ (1+i)^n - 1 ]`\n\n"
        f"{md_subtitulo('Substituindo os valores')}\n"
        f"Substitui-se `M`, `P`, `i` e `n` com os números da sua simulação.\n\n"
        f"{md_subtitulo('Resultado')}\n"
        f"**Aporte mensal estimado: {aporte_mensal_fmt}**\n\n"
        f"{md_disclaimer()}"
    )

# =========================
# Wrappers do Ollama (LLM)
# =========================
def perguntar_ollama(system_prompt: str, user_content: str, url: str, modelo: str) -> Optional[str]:
    """Chama o Ollama em /api/chat com system + user; retorna texto ou None."""
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

def reescrever_com_llm(usar_llm: bool, modelo: str, system_prompt: str, instrucoes: str, fatos: str, url: str) -> Optional[str]:
    """Pede ao LLM para reescrever mantendo SOMENTE os fatos fornecidos."""
    if not usar_llm:
        return None
    conteudo = (
        "Reescreva de forma clara e didática, mantendo TODOS os números e fatos. "
        "Use Markdown com títulos e bullets quando fizer sentido. "
        "Não invente dados, não recomende investimentos.\n\n"
        f"INSTRUÇÕES:\n{instrucoes}\n\nFATOS:\n{fatos}"
    )
    return perguntar_ollama(system_prompt, conteudo, url, modelo)

# =========================
# Utilitário para nome
# =========================
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