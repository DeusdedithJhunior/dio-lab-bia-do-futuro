# -*- coding: utf-8 -*-
"""
app.py — UI (Streamlit) da MAIA
--------------------------------
- Sidebar padrão (LLM, modelo, janela, debug, contexto + diagnóstico)
- Saudação única (streaming) com nome do perfil e rerun
- Roteamento robusto: resumo de finanças, recomendação (educativa/compatível), gasto total,
  gasto por categoria, saldo, maior gasto, metas, rentabilidade de produto, produtos,
  perfil de investidor, ajuda, fallback
- Determinístico é fonte de verdade; LLM só reescreve (opcional)
"""

from pathlib import Path
from typing import Optional
import json
import re
import time

import pandas as pd
import streamlit as st

import config
import agente

# ============ CONFIG DA PÁGINA ============
st.set_page_config(page_title="MAIA - Assistente Financeira", page_icon="📈", layout="centered")
st.title("📈 MAIA — Assistente Financeira (MVP Local)")
st.caption("MVP educativo, sem recomendação. Dados mockados em `../data/`.")

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

# ============ STREAMING ============
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

    # Diagnóstico das funções carregadas (ajuda a detectar AttributeError)
    with st.expander("Diagnóstico (dev)"):
        try:
            funcs = [
                "eh_intencao_resumo_financas", "resposta_resumo_financas",
                "eh_intencao_total_gasto", "resposta_total_gasto",
                "eh_intencao_saldo", "resposta_saldo",
                "eh_intencao_gasto_categoria", "resposta_gasto_categoria",
                "eh_intencao_maior_gasto", "resumo_maior_gasto",
                "eh_intencao_recomendacao", "resposta_recomendacao_contextual",
                "eh_intencao_perfil_investidor", "resposta_perfil_investidor",
                "eh_intencao_rentabilidade_produto", "buscar_produto",
            ]
            snap = [f"{f}: {hasattr(agente, f)}" for f in funcs]
            st.code("Funções no módulo agente:\n" + "\n".join(snap))
            st.caption(f"agente.py carregado de: {getattr(agente, '__file__', 'desconhecido')}")
        except Exception as e:
            st.error(f"Diagnóstico falhou: {e}")

# ============ HISTÓRICO + BOAS-VINDAS ============
if "historico" not in st.session_state:
    st.session_state.historico = []
if "welcomed" not in st.session_state:
    st.session_state.welcomed = False

def mensagem_boas_vindas(perfil_dict: dict) -> str:
    primeiro = agente.extrair_primeiro_nome(perfil_dict.get("nome") if isinstance(perfil_dict, dict) else None)
    tratamento = f"Sr {primeiro}" if primeiro != "cliente" else "cliente"
    return (
        f"**Oi, {tratamento}! Tudo bem? Eu sou a MAIA.** 👋\n\n"
        "Posso te ajudar a **simular uma meta**, **analisar seu orçamento** ou **explicar produtos** "
        "(Tesouro, CDB, LCI/LCA, Ações, FIIs, Cripto e BDRs).\n\n"
        "**Como posso ajudar hoje?**"
    )

if not st.session_state.welcomed:
    texto_boas = mensagem_boas_vindas(perfil)
    if st.session_state.get("usar_llm"):
        llm_welcome = agente.perguntar_ollama(
            config.SYSTEM_PROMPT,
            "Reescreva esta mensagem de boas-vindas de forma acolhedora, mantendo o conteúdo:\n\n" + texto_boas,
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

# ============ ENTRADA ============
pergunta = st.chat_input("Digite sua pergunta (ex.: 'Como estão as minhas finanças?' ou 'Quanto gastei com alimentação?')")
if pergunta:
    # Guardrails
    if agente.eh_sensivel(pergunta):
        resp = "Não tenho acesso e não posso solicitar dados sensíveis (senha, CPF, CVV, etc.). Posso te ajudar com orçamento, metas ou produtos."
        st.session_state.historico += [{"role": "user", "content": pergunta}, {"role": "assistant", "content": resp}]
        st.rerun()
    if agente.fora_escopo(pergunta):
        resp = "Sou especializada em finanças e não tenho informações sobre esse assunto. Posso ajudar com orçamento, metas e produtos financeiros."
        st.session_state.historico += [{"role": "user", "content": pergunta}, {"role": "assistant", "content": resp}]
        st.rerun()

    st.session_state.historico.append({"role": "user", "content": pergunta})
    with st.chat_message("user"):
        st.markdown(pergunta)

    assistant_box = st.chat_message("assistant")
    with assistant_box:
        info = st.empty()
        info.markdown("*Digitando…*")

    t = pergunta.lower()
    usar_llm_flag = st.session_state.usar_llm
    modelo_sel = st.session_state.get("modelo_ollama", config.OLLAMA_MODEL_DEFAULT)
    janela_atual = st.session_state.get("janela", config.DEFAULT_WINDOW_DAYS)

    # ===== ROTEAMENTO POR INTENÇÃO =====
    # 0) Resumo executivo “Como estão as minhas finanças?”
    if agente.eh_intencao_resumo_financas(pergunta):
        base_resp = agente.resposta_resumo_financas(df_tx, perfil, produtos, janela_dias=janela_atual)
        if usar_llm_flag:
            fatos = (
                f"Janela_dias={janela_atual}\n"
                f"Resumo_orcamento=entradas/saidas/saldo/top_categorias/maior_tx/ultimas\n"
                f"Perfil={perfil.get('perfil_investidor','-')}\n"
                f"Exemplos_educativos=compatibilidade_por_risco\n"
            )
            instrucoes = (
                "Reescreva em tom executivo, claro e acolhedor. "
                "Mantenha números e fatos. Estruture em seções curtas. "
                "Inclua próximos passos. Não recomende ativo específico."
            )
            _ = agente.reescrever_com_llm(
                usar_llm_flag, modelo_sel, config.SYSTEM_PROMPT,
                instrucoes, fatos, config.OLLAMA_URL,
                fontes=['transacoes.csv', 'perfil_investidor.json', 'produtos_financeiros.json']
            )

    # 1) Recomendação EDUCATIVA compatível com perfil
    elif agente.eh_intencao_recomendacao(pergunta):
        base_resp = agente.resposta_recomendacao_contextual(df_tx, perfil, produtos, janela_dias=janela_atual)
        if usar_llm_flag:
            fatos = (
                f"Gasto_mensal_aprox={agente.fmt_moeda(agente.gasto_medio_mensal(df_tx, janela_atual))}\n"
                f"Reserva_3m_6m_intervalo=calc_em_texto\n"
                f"Janela_dias={janela_atual}\n"
                f"Perfil={perfil.get('perfil_investidor','-')}\n"
            )
            instrucoes = (
                "Reescreva acolhedor, preservando números e a ideia de reserva 3-6 meses. "
                "Inclua um próximo passo para simulação. Não recomende ativo específico."
            )
            _ = agente.reescrever_com_llm(
                usar_llm_flag, modelo_sel, config.SYSTEM_PROMPT,
                instrucoes, fatos, config.OLLAMA_URL,
                fontes=['transacoes.csv', 'perfil_investidor.json', 'produtos_financeiros.json']
            )

    # 2) Gasto total no período
    elif agente.eh_intencao_total_gasto(pergunta):
        base_resp = agente.resposta_total_gasto(df_tx, janela_dias=janela_atual)

    # 3) Gasto por categoria
    elif agente.eh_intencao_gasto_categoria(pergunta):
        base_resp = agente.resposta_gasto_categoria(df_tx, pergunta, janela_dias=janela_atual)

    # 4) Saldo
    elif agente.eh_intencao_saldo(pergunta):
        base_resp = agente.resposta_saldo(df_tx, janela_dias=janela_atual)

    # 5) Maior gasto
    elif agente.eh_intencao_maior_gasto(pergunta):
        base_resp = agente.resumo_maior_gasto(df_tx, janela_dias=janela_atual)

    # 6) Perfil de investidor
    elif agente.eh_intencao_perfil_investidor(pergunta):
        base_resp = agente.resposta_perfil_investidor(perfil)

    # 7) Metas
    elif any(k in t for k in ["meta", "juntar", "guardar", "objetivo"]):
        nums = re.findall(r"(\d+[.,]?\d*)", pergunta)
        if len(nums) >= 2:
            valor = float(nums[0].replace(",", "."))
            meses = int(float(nums[1].replace(",", ".")) * 12) if "ano" in t else int(float(nums[1].replace(",", ".")))
            texto_meta, fatos_meta = agente.simular_meta_dados(
                valor_meta=valor, meses=meses, aporte_inicial=0.0, taxa_mensal=0.0
            )
            base_resp = texto_meta

            if usar_llm_flag and fatos_meta:
                fatos = (
                    f"Meta_total={agente.fmt_moeda(fatos_meta['meta_total'])}\n"
                    f"Prazo_meses={fatos_meta['meses']}\n"
                    f"Aporte_inicial={agente.fmt_moeda(fatos_meta['aporte_inicial'])}\n"
                    f"Taxa_mensal=0.00% a.m.\n"
                    f"Aporte_mensal={agente.fmt_moeda(fatos_meta['aporte_mensal'])}\n"
                )
                instrucoes = "Explique a simulação com bullets e destaque do aporte. Ofereça 'Quer ver o passo a passo?'."
                _ = agente.reescrever_com_llm(
                    usar_llm_flag, modelo_sel, config.SYSTEM_PROMPT,
                    instrucoes, fatos, config.OLLAMA_URL,
                    fontes=['perfil_investidor.json']
                )
        else:
            base_resp = (
                f"{agente.md_titulo('🎯 Simulação de meta')}\n\n"
                "Para simular a meta, informe o **valor** e o **prazo em meses**.\n\n"
                "Ex.: `Quero juntar 10000 em 12 meses`."
            )

    # 8) “Quanto rende X?”
    elif (nome_prod := agente.eh_intencao_rentabilidade_produto(pergunta)) is not None:
        base_resp = agente.resposta_rentabilidade_produto(produtos, nome_prod)

    # 9) Produtos (listagem/explicação)
    elif any(k in t for k in ["produto", "tesouro", "cdb", "lci", "lca", "ações", "acoes", "fii", "bdr", "cripto"]):
        texto_prod, _ = agente.buscar_produto(pergunta, produtos)
        base_resp = texto_prod

    # 10) Ajuda
    elif any(k in t for k in ["ajuda", "dúvida", "duvida", "como funciona"]):
        base_resp = "Posso te ajudar com orçamento, metas, simulações simples e explicar produtos financeiros da nossa base. Sobre o que deseja falar?"

    # 11) Fallback
    else:
        base_resp = (
            "Não entendi exatamente. Você pode perguntar, por exemplo:\n"
            "- *Como estão as minhas finanças?*\n"
            "- *Quanto gastei?*\n"
            "- *Quanto gastei com alimentação?*\n"
            "- *Qual é meu saldo?*\n"
            "- *Qual investimento você recomenda para mim?* (educativo, baseado no seu perfil)\n"
            "- *Quanto rende o produto Tesouro Selic?*\n"
            "- *Qual o meu perfil de investidor?*"
        )

    # Exibir com streaming e persistir
    with assistant_box:
        info.empty()
        stream_texto(base_resp, atraso_chars=0.008, atraso_paragrafo=0.12)

    st.session_state.historico.append({"role": "assistant", "content": base_resp})
    st.rerun()
