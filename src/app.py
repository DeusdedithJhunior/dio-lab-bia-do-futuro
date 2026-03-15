# -*- coding: utf-8 -*-
"""
app.py — UI (Streamlit) da MAIA
--------------------------------
- Sidebar padrão (LLM toggle, modelo, janela, debug, contexto)
- Saudação única (streaming) com nome do perfil e rerun
- Roteamento de intenções (meta, orçamento, maior gasto, produtos, ajuda)
- Fluxo híbrido: determinístico -> opcional reescrita pelo Ollama
"""

from pathlib import Path
from typing import Optional
import json
import re
import time
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# Nossos módulos
import config
import agente

# ============ CONFIG DA PÁGINA ============
st.set_page_config(page_title="MAIA - Assistente Financeira", page_icon="📈", layout="centered")
st.title("📈 MAIA — Assistente Financeira (MVP Local)")
st.caption("MVP educativo, sem recomendação. Dados mockados em `../data/`.")

# CSS leve para legibilidade
st.markdown("""
<style>
section.main .block-container { max-width: 900px; }
.stChatMessage { line-height: 1.46; font-size: 1.02rem; }
code, pre, kbd { font-size: 0.95rem !important; }
</style>
""", unsafe_allow_html=True)

# ============ CAMINHOS ============
BASE_DIR: Path = Path(__file__).resolve().parent
DATA_DIR: Path = BASE_DIR.parent / "data"

ARQ_TX: Path       = DATA_DIR / "transacoes.csv"
ARQ_HIST: Path     = DATA_DIR / "historico_atendimento.csv"
ARQ_PERFIL: Path   = DATA_DIR / "perfil_investidor.json"
ARQ_PRODUTOS: Path = DATA_DIR / "produtos_financeiros.json"

COLS_TRANSACOES = ["data", "descricao", "categoria", "valor", "tipo"]
COLS_HISTORICO  = ["data", "canal", "tema", "resumo", "resolvido"]

# ============ CACHE DE DADOS ============
@st.cache_data(show_spinner=False)
def carregar_dados():
    df_tx = pd.read_csv(ARQ_TX)
    falt = [c for c in COLS_TRANSACOES if c not in df_tx.columns]
    if falt:
        raise ValueError(f"[transacoes.csv] Colunas ausentes: {falt}")
    df_tx["data"] = pd.to_datetime(df_tx["data"], errors="coerce")

    df_hist = pd.read_csv(ARQ_HIST)
    falt = [c for c in COLS_HISTORICO if c not in df_hist.columns]
    if falt:
        raise ValueError(f"[historico_atendimento.csv] Colunas ausentes: {falt}")
    df_hist["data"] = pd.to_datetime(df_hist["data"], errors="coerce")

    with open(ARQ_PERFIL, "r", encoding="utf-8") as f:
        perfil = json.load(f)
    with open(ARQ_PRODUTOS, "r", encoding="utf-8") as f:
        produtos = json.load(f)

    if not isinstance(produtos, list) or not produtos:
        raise ValueError("[produtos_financeiros.json] Deve ser lista com ao menos 1 produto.")
    return df_tx, df_hist, perfil, produtos

try:
    df_tx, df_hist, perfil, produtos = carregar_dados()
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# ============ FUNÇÃO DE STREAMING ============
def stream_texto(texto: str, atraso_chars: float = 0.008, atraso_paragrafo: float = 0.12):
    box = st.empty()
    buffer = ""
    for bloco in texto.split("\n\n"):
        for ch in bloco:
            buffer += ch
            box.markdown(buffer + "▌")
            time.sleep(atraso_chars)
        buffer += "\n\n"
        box.markdown(buffer)
        time.sleep(atraso_paragrafo)

# ============ SIDEBAR ============
with st.sidebar:
    st.header("Configurações")

    usar_llm = st.toggle("Usar LLM local (Ollama)", value=False)
    st.session_state.usar_llm = usar_llm

    modelo = st.selectbox("Modelo (Ollama)", config.OLLAMA_MODELS, index=0)
    st.session_state.modelo_ollama = modelo

    janela = st.slider("Janela de análise (dias)", 7, 90, config.DEFAULT_WINDOW_DAYS, step=1)
    st.session_state.janela = janela

    st.divider()
    if st.checkbox("Mostrar status dos arquivos (debug)", value=False):
        st.subheader("📂 Status dos Arquivos")
        for p in [ARQ_TX, ARQ_HIST, ARQ_PERFIL, ARQ_PRODUTOS]:
            st.write(f"`{p}` — {'OK' if p.exists() else 'FALTANDO'}")

    st.divider()
    if st.button("Ver contexto atual"):
        ctx = agente.montar_contexto(df_tx, df_hist, perfil, produtos, janela_dias=janela)
        st.code(ctx, language="markdown")

# ============ HISTÓRICO + BOAS-VINDAS ============
if "historico" not in st.session_state:
    st.session_state.historico = []
if "welcomed" not in st.session_state:
    st.session_state.welcomed = False

def mensagem_boas_vindas(nome_cliente: Optional[str]) -> str:
    primeiro = agente.extrair_primeiro_nome(nome_cliente)
    tratamento = f"Sr {primeiro}" if primeiro != "cliente" else "cliente"
    return (
        f"**Oi, {tratamento}! Tudo bem? Eu sou a MAIA.** 👋\n\n"
        "Posso te ajudar a **simular uma meta**, **analisar seu orçamento** ou **explicar produtos** "
        "(Tesouro, CDB, LCI/LCA, Ações, FIIs, Cripto e BDRs).\n\n"
        "**Como posso ajudar hoje?**"
    )

if not st.session_state.welcomed:
    texto_boas = mensagem_boas_vindas(perfil.get("nome") if isinstance(perfil, dict) else None)

    if st.session_state.get("usar_llm"):
        llm_welcome = agente.perguntar_ollama(
            config.SYSTEM_PROMPT,
            "Reescreva esta mensagem de boas-vindas de forma acolhedora, em até 3 parágrafos, mantendo o conteúdo:\n\n" + texto_boas,
            config.OLLAMA_URL,
            st.session_state.get("modelo_ollama", config.OLLAMA_MODEL_DEFAULT),
        )
        if llm_welcome:
            texto_boas = llm_welcome

    with st.chat_message("assistant"):
        stream_texto(texto_boas, atraso_chars=0.008, atraso_paragrafo=0.12)

    st.session_state.historico.append({"role": "assistant", "content": texto_boas})
    st.session_state.welcomed = True
    st.rerun()

# Render histórico
for msg in st.session_state.historico:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ============ ENTRADA DO USUÁRIO ============
pergunta = st.chat_input("Digite sua pergunta (ex.: 'Quero juntar 10000 em 12 meses')")
if pergunta:
    # Guardrails
    if agente.eh_sensivel(pergunta):
        resp = "Não tenho acesso e não posso solicitar dados sensíveis (senha, CPF, CVV, etc.). Posso te ajudar com orçamento, metas ou produtos."
        st.session_state.historico += [{"role": "user", "content": pergunta}, {"role": "assistant", "content": resp}]
        st.rerun()

    if agente.fora_escopo(pergunta):
        resp = "Sou especializada em finanças e não tenho informações sobre esse assunto. Posso ajudar com orçamento, metas e produtos (Tesouro, CDB, LCI/LCA, Ações, FIIs, Cripto e BDRs)."
        st.session_state.historico += [{"role": "user", "content": pergunta}, {"role": "assistant", "content": resp}]
        st.rerun()

    # Adiciona usuário
    st.session_state.historico.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    # Balão do assistente + placeholder "Digitando…"
    assistant_box = st.chat_message("assistant")
    with assistant_box:
        info = st.empty()
        info.markdown("*Digitando…*")

    # Continuação "sim" para passo a passo
    if st.session_state.get("aguardando_explicacao_meta"):
        if agente.eh_afirmativo(pergunta):
            ctx_meta = st.session_state["aguardando_explicacao_meta"]
            meta = float(ctx_meta["valor_meta"])
            meses = int(ctx_meta["meses"])
            aporte_inicial = float(ctx_meta["aporte_inicial"])
            taxa_mensal = float(ctx_meta["taxa_mensal"])

            if taxa_mensal <= 0:
                restante = max(0.0, meta - aporte_inicial)
                aporte_mensal = restante / meses
            else:
                i = taxa_mensal
                fator = ((1 + i) ** meses - 1) / i
                restante = max(0.0, meta - aporte_inicial * ((1 + i) ** meses))
                aporte_mensal = (restante / fator) if fator > 0 else restante / meses

            base_resp = agente.explicar_meta_step_by_step(meta, meses, aporte_inicial, taxa_mensal, aporte_mensal)

            st.session_state.pop("aguardando_explicacao_meta", None)
            with assistant_box:
                info.empty()
                stream_texto(base_resp, atraso_chars=0.008, atraso_paragrafo=0.12)
            st.session_state.historico.append({"role": "assistant", "content": base_resp})
            st.rerun()

        elif agente.eh_negativo(pergunta):
            st.session_state.pop("aguardando_explicacao_meta", None)
            base_resp = "Sem problemas! Se quiser ver o cálculo depois, é só pedir: *“mostre o passo a passo”*."
            with assistant_box:
                info.empty()
                stream_texto(base_resp, atraso_chars=0.008, atraso_paragrafo=0.12)
            st.session_state.historico.append({"role": "assistant", "content": base_resp})
            st.rerun()
        # se não for afirmativo/negativo, segue o fluxo abaixo

    # ===== Roteamento de intenção =====
    t = pergunta.lower()
    usar_llm_flag = st.session_state.usar_llm
    modelo_sel = st.session_state.get("modelo_ollama", config.OLLAMA_MODEL_DEFAULT)
    janela_atual = st.session_state.get("janela", config.DEFAULT_WINDOW_DAYS)

    if agente.eh_intencao_maior_gasto(pergunta):
        base_resp = agente.resumo_maior_gasto(df_tx, janela_dias=janela_atual)
        # (Opcional) poderíamos reescrever com LLM, mas costuma ser curto

    elif any(k in t for k in ["meta", "juntar", "guardar", "objetivo"]):
        nums = re.findall(r"(\d+[.,]?\d*)", pergunta)
        if len(nums) >= 2:
            valor = float(nums[0].replace(",", "."))
            meses = int(float(nums[1].replace(",", ".")) * 12) if "ano" in t else int(float(nums[1].replace(",", ".")))

            texto_meta, fatos_meta = agente.simular_meta_dados(valor_meta=valor, meses=meses, aporte_inicial=0.0, taxa_mensal=0.0)
            base_resp = texto_meta

            st.session_state["aguardando_explicacao_meta"] = {
                "valor_meta": valor, "meses": meses, "aporte_inicial": 0.0, "taxa_mensal": 0.0
            }

            # Reescrita opcional pelo LLM
            if usar_llm_flag and fatos_meta:
                fatos = (
                    f"Meta_total={agente.fmt_moeda(fatos_meta['meta_total'])}\n"
                    f"Prazo_meses={fatos_meta['meses']}\n"
                    f"Aporte_inicial={agente.fmt_moeda(fatos_meta['aporte_inicial'])}\n"
                    f"Taxa_mensal=0.00% a.m.\n"
                    f"Aporte_mensal={agente.fmt_moeda(fatos_meta['aporte_mensal'])}\n"
                )
                instrucoes = (
                    "Explique a simulação de meta com título, bullets e destaque do aporte mensal. "
                    "Finalize oferecendo 'Quer ver o passo a passo do cálculo?'."
                )
                llm_text = agente.reescrever_com_llm(usar_llm_flag, modelo_sel, config.SYSTEM_PROMPT, instrucoes, fatos, config.OLLAMA_URL)
                if llm_text:
                    base_resp = llm_text
        else:
            base_resp = (
                f"{agente.md_titulo('🎯 Simulação de meta')}\n\n"
                "Para simular a meta, informe o **valor** e o **prazo em meses**.\n\n"
                "Exemplo: `Quero juntar 10000 em 12 meses`."
            )
            st.session_state.pop("aguardando_explicacao_meta", None)

    elif any(k in t for k in ["orçamento", "orcamento", "gasto", "despesa", "categorias"]):
        texto_orc, fatos_orc = agente.analisar_orcamento(df_tx, janela_dias=janela_atual)
        base_resp = texto_orc
        if usar_llm_flag:
            cat_dados = "; ".join([f"{c}={agente.fmt_moeda(v)}" for c, v in fatos_orc["top_categorias"]]) or "sem_despesas"
            fatos = (
                f"Janela_dias={fatos_orc['janela_dias']}\n"
                f"Entradas={agente.fmt_moeda(fatos_orc['entrada'])}\n"
                f"Saidas={agente.fmt_moeda(fatos_orc['saida'])}\n"
                f"Saldo={agente.fmt_moeda(fatos_orc['saldo'])}\n"
                f"TopCategorias={cat_dados}\n"
            )
            instrucoes = (
                "Explique orçamento com título, bullets de Entradas/Saídas/Saldo e liste principais categorias. "
                "Finalize com uma dica educativa curta (sem recomendar)."
            )
            llm_text = agente.reescrever_com_llm(usar_llm_flag, modelo_sel, config.SYSTEM_PROMPT, instrucoes, fatos, config.OLLAMA_URL)
            if llm_text:
                base_resp = llm_text

    elif any(k in t for k in ["produto", "tesouro", "cdb", "lci", "lca", "ações", "acoes", "fii", "bdr", "cripto"]):
        texto_prod, fatos_prod = agente.buscar_produto(pergunta, produtos)
        base_resp = texto_prod
        if usar_llm_flag:
            if fatos_prod:
                linhas = [f"{p['nome']} | cat={p['categoria']} | risco={p['risco']} | rent={p['rentabilidade']} | aporte_min={agente.fmt_moeda(p['aporte_minimo'])}" for p in fatos_prod[:6]]
                fatos = "Produtos:\n" + "\n".join(linhas)
            else:
                fatos = "Produtos: nenhum_match_exato"
            instrucoes = (
                "Liste os produtos encontrados com bullets. "
                "Se houver BDR, mencione exposição ao dólar; se houver Cripto, alta volatilidade. "
                "Citar fonte 'produtos_financeiros.json'. Não recomendar."
            )
            llm_text = agente.reescrever_com_llm(usar_llm_flag, modelo_sel, config.SYSTEM_PROMPT, instrucoes, fatos, config.OLLAMA_URL)
            if llm_text:
                base_resp = llm_text

    elif any(k in t for k in ["ajuda", "dúvida", "duvida", "como funciona"]):
        base_resp = "Posso te ajudar com orçamento, metas, simulações simples e explicar produtos financeiros da nossa base (fonte: produtos_financeiros.json). O que você deseja?"

    else:
        base_resp = "Posso te ajudar com **orçamento**, **metas** e **produtos** (Tesouro, CDB, LCI/LCA, Ações, FIIs, Cripto e BDRs). Como prefere começar?"

    # Exibe com streaming e persiste
    with assistant_box:
        info.empty()
        stream_texto(base_resp, atraso_chars=0.008, atraso_paragrafo=0.12)

    st.session_state.historico.append({"role": "assistant", "content": base_resp})
    st.rerun()