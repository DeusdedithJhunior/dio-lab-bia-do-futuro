***

# Base de Conhecimento

## Dados Utilizados

A base de conhecimento utiliza os arquivos da pasta `data`, conforme a estrutura **real do projeto**.

| Arquivo                         | Formato | Utilização no Agente                                                                                                                                                                                      |
| ------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`historico_atendimento.csv`** | CSV     | Contextualiza interações anteriores do cliente (colunas: `data, canal, tema, resumo, resolvido`), evitando repetição e mantendo continuidade no atendimento.                                              |
| **`perfil_investidor.json`**    | JSON    | Informa dados pessoais e financeiros (ex.: `renda_mensal, perfil_investidor, metas`) para **personalizar explicações** e **priorizar metas** (sem recomendação regulada).                                 |
| **`produtos_financeiros.json`** | JSON    | Base de referência de produtos (Tesouro Selic, CDB, LCI/LCA, **Ações**, **FIIs**, **Criptoativos**, **BDRs**) para FAQs, comparações e **citação de fonte**.                                              |
| **`transacoes.csv`**            | CSV     | Analisa padrão de gastos (colunas: `data, descricao, categoria, valor, tipo`) para insights orçamentários e simulações de metas. Não há `user_id`; o conjunto é tratado como um **cliente único** do MVP. |

***

## Adaptações nos Dados

Os arquivos foram **mantidos como fornecidos**, **sem mudanças estruturais** nos CSV/JSON originais — com **uma exceção** documentada abaixo para fins didáticos.

**Alterações realizadas em `data/produtos_financeiros.json`:**

*   Substituímos opções menos intuitivas para o público geral (ex.: *Fundo Multimercado*, *Fundo de Ações*) por itens de **mais fácil entendimento** e **didáticos para o MVP**:
    *   Inclusão/ajuste de **Ações** (mercado variável, risco alto, aporte mínimo 1.00).
    *   Inclusão/ajuste de **FIIs** (fundo imobiliário, variável, risco alto, aporte mínimo 10.00).
    *   Inclusão de **Criptoativos** (ex.: Bitcoin — mercado de alta volatilidade).
    *   Inclusão de **BDRs (Recibos de Depósito de Ações)** — **exposição ao dólar** e a empresas globais.
*   **Motivos:**
    1.  **Facilidade de entendimento** para usuários iniciantes.
    2.  Melhor base para **explicar “mercado variável”** (volatilidade e risco).
    3.  Possibilitar conversas sobre **diversificação** e **exposição cambial** (“exposição ao dólar” via BDRs), sem prometer retornos.

> **Importante:** Embora alguns campos de “rentabilidade” estejam descritos como “Variável” (condizente com RV), todo o conteúdo é **mockado** para demonstração e **não constitui recomendação**.

***

## Estratégia de Integração

### Como os dados são carregados?

Há duas abordagens, dependendo do seu fluxo:

#### 1) Injeção direta no prompt (copiar e colar)

Boa para **prototipagem** e **demonstrações** sem backend.  
Inclua apenas o **recorte necessário**.

```text
[Contexto para o agente]

Perfil do cliente:
- Nome: João Silva
- Renda mensal: R$ 5.000,00
- Perfil investidor: moderado
- Objetivo principal: Construir reserva de emergência
- Metas:
  • Completar reserva de emergência: R$ 15.000 até 2026-06
  • Entrada do apartamento: R$ 50.000 até 2027-12

Últimas transações:
- 2025-10-03, Supermercado, alimentacao, R$ 450,00, saida
- 2025-10-10, Restaurante, alimentacao, R$ 120,00, saida
- 2025-10-12, Uber, transporte, R$ 45,00, saida

Produtos de referência:
- Tesouro Selic (renda fixa, risco baixo)
- CDB Liquidez Diária (renda fixa, risco baixo)
- LCI/LCA (renda fixa, risco baixo; carência)
- Ações (mercado variável, risco alto)
- FIIs (fundo imobiliário, variável)
- Criptoativos (alta volatilidade)
- BDRs (variável, com exposição ao dólar)

Instruções:
- Use APENAS o contexto acima; se algo não estiver aqui, diga que não sabe.
- Ao mencionar produtos, cite a fonte: "produtos_financeiros.json".
- Se fizer cálculo, ofereça: "Quer ver como calculei?".
- Não prometa rentabilidade; trate números como exemplo educativo (mockado).
```

#### 2) Carregamento via código (Python)

```python
# -*- coding: utf-8 -*-
"""
Integração de dados (compatível com a base real do projeto).
- transacoes.csv: data, descricao, categoria, valor, tipo
- historico_atendimento.csv: data, canal, tema, resumo, resolvido
- perfil_investidor.json: dados pessoais, renda, metas, perfil_investidor
- produtos_financeiros.json: Tesouro, CDB, LCI/LCA, Ações, FIIs, Cripto, BDRs
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path("data")
ARQ_TX = DATA_DIR / "transacoes.csv"
ARQ_HIST = DATA_DIR / "historico_atendimento.csv"
ARQ_PERFIL = DATA_DIR / "perfil_investidor.json"
ARQ_PRODUTOS = DATA_DIR / "produtos_financeiros.json"

# ---- Leitura ----
df_tx = pd.read_csv(ARQ_TX)  # data, descricao, categoria, valor, tipo
df_hist = pd.read_csv(ARQ_HIST)  # data, canal, tema, resumo, resolvido

with open(ARQ_PERFIL, "r", encoding="utf-8") as f:
    perfil = json.load(f)

with open(ARQ_PRODUTOS, "r", encoding="utf-8") as f:
    produtos = json.load(f)

# ---- Conversões/garantias (sem alterar arquivos) ----
df_tx["data"] = pd.to_datetime(df_tx["data"], errors="coerce")
df_hist["data"] = pd.to_datetime(df_hist["data"], errors="coerce")

# Define uma janela de 30 dias; se não houver, usa as últimas N transações
hoje = datetime.now().date()
inicio_30d = hoje - timedelta(days=30)
df_tx_janela = df_tx[df_tx["data"].dt.date >= inicio_30d].sort_values("data", ascending=False)
N = 10
df_tx_ctx = df_tx_janela.head(N) if len(df_tx_janela) else df_tx.sort_values("data", ascending=False).head(N)

def linha_tx(row):
    data_fmt = row["data"].strftime("%Y-%m-%d") if pd.notnull(row["data"]) else "----"
    valor_fmt = f"R$ {float(row['valor']):.2f}".replace(".", ",")
    return f"- {data_fmt} | {row['descricao']} | {row['categoria']} | {valor_fmt} | {row['tipo']}"

linhas_tx = "\n".join(df_tx_ctx.apply(linha_tx, axis=1).tolist())

# Histórico recente (3 itens)
hist_recent = df_hist.sort_values("data", ascending=False).head(3)
linhas_hist = "\n".join([
    f"- {r['data'].strftime('%Y-%m-%d')}: {r['canal']} • {r['tema']} — {r['resumo']} (resolvido: {r['resolvido']})"
    for _, r in hist_recent.iterrows()
])

# Produtos (resumo amigável)
def resumir_prod(p):
    nome = p.get("nome", "Produto")
    cat = p.get("categoria", "-")
    risco = p.get("risco", "-")
    rent = p.get("rentabilidade", "Variável")
    return f"- {nome} ({cat}, risco: {risco}) — rentabilidade: {rent}"

linhas_prod = "\n".join([resumir_prod(p) for p in produtos])

# Perfil e metas
nome = perfil.get("nome")
renda_mensal = perfil.get("renda_mensal")
perfil_inv = perfil.get("perfil_investidor")
objetivo_principal = perfil.get("objetivo_principal")
metas_fmt = "\n".join([
    f"- {m.get('meta')}: R$ {m.get('valor_necessario')} até {m.get('prazo')}"
] for m in perfil.get("metas", [])) if perfil.get("metas") else "- (sem metas registradas)"

contexto = f"""
Perfil do cliente:
- Nome: {nome}
- Renda mensal: R$ {renda_mensal}
- Perfil investidor: {perfil_inv}
- Objetivo principal: {objetivo_principal}

Metas:
{metas_fmt}

Últimas transações (até {N} linhas):
{linhas_tx}

Interações recentes:
{linhas_hist}

Produtos de referência (fonte: produtos_financeiros.json):
{linhas_prod}

Instruções ao agente:
- Responda usando apenas o contexto; se faltar algo, diga que não sabe.
- Ao citar produtos, mantenha linguagem educativa; não prometa retornos.
- Se fizer cálculo, ofereça: "Quer ver como calculei?".
- Para BDRs, explique que há "exposição ao dólar".
""".strip()

print(contexto)

# Exemplo de mensagens ao LLM (pseudocódigo)
# mensagens = [
#     {"role": "system", "content": "Você é a MAIA, assistente financeira educativa. Não invente dados..."},
#     {"role": "user", "content": contexto},
#     {"role": "user", "content": "Quero planejar a entrada do apartamento para 2027-12. Quanto devo guardar por mês?"}
# ]
# resposta = chamar_llm(mensagens)
# print(resposta)
```

### Como os dados são usados no prompt?

*   O agente **não envia a base inteira**; apenas **o trecho relevante** por intenção (ex.: transações recentes em orçamento; lista resumida de produtos em FAQs).
*   O **prompt do sistema** mantém as **regras de segurança** (não inventar, citar fonte, pedir confirmação, disclaimers), enquanto os **dados variáveis** entram como **contexto**.
*   Para **BDRs**, deixar claro que existe **exposição ao dólar** (câmbio influencia).
*   Para **Criptoativos**, **volatilidade alta**: respostas **educativas**, sem promessa de retorno.

***

## Exemplo de Contexto Montado

```text
Perfil do cliente:
- Nome: João Silva
- Renda mensal: R$ 5000.0
- Perfil investidor: moderado
- Objetivo principal: Construir reserva de emergência

Metas:
- Completar reserva de emergência: R$ 15000.0 até 2026-06
- Entrada do apartamento: R$ 50000.0 até 2027-12

Últimas transações (até 10 linhas):
- 2025-10-25 | Combustível | transporte | R$ 250,00 | saida
- 2025-10-20 | Academia | saude | R$ 99,00 | saida
- 2025-10-15 | Conta de Luz | moradia | R$ 180,00 | saida
- 2025-10-12 | Uber | transporte | R$ 45,00 | saida
- 2025-10-10 | Restaurante | alimentacao | R$ 120,00 | saida
- 2025-10-07 | Farmácia | saude | R$ 89,00 | saida
- 2025-10-05 | Netflix | lazer | R$ 55,90 | saida
- 2025-10-03 | Supermercado | alimentacao | R$ 450,00 | saida
- 2025-10-02 | Aluguel | moradia | R$ 1200,00 | saida
- 2025-10-01 | Salário | receita | R$ 5000,00 | entrada

Interações recentes:
- 2025-10-12: chat • Metas financeiras — Cliente acompanhou o progresso da reserva de emergência (resolvido: sim)
- 2025-10-01: chat • Tesouro Selic — Cliente pediu explicação sobre o funcionamento do Tesouro Direto (resolvido: sim)
- 2025-09-22: telefone • Problema no app — Erro ao visualizar extrato foi corrigido (resolvido: sim)

Produtos de referência (fonte: produtos_financeiros.json):
- Tesouro Selic (renda_fixa, risco: baixo) — rentabilidade: 100% da Selic
- CDB Liquidez Diária (renda_fixa, risco: baixo) — rentabilidade: 102% do CDI
- LCI/LCA (renda_fixa, risco: baixo) — rentabilidade: 95% do CDI
- Ações (mercado_variavel, risco: alto) — rentabilidade: Variável
- FIIs (fundo_imobiliario, risco: alto) — rentabilidade: Variável
- Criptoativos (cripto, risco: alto) — rentabilidade: Alta volatilidade
- BDRs (mercado_variavel, risco: alto) — rentabilidade: Variável (com exposição ao dólar)

Instruções ao agente:
- Responda usando somente o contexto acima; se faltar algo, diga que não sabe.
- Ao citar produtos, mencione a fonte "produtos_financeiros.json".
- Em simulações, ofereça "Quer ver como calculei?".
- Não prometa rentabilidade; dados são mockados e educativos.
```

***
