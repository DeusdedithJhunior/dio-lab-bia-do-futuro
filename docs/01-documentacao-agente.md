# Documentação do Agente - MAIA

Este documento descreve **o funcionamento do agente**, **as intenções suportadas** e **o fluxo determinístico** da MAIA, conforme a implementação final (`src/agente.py`, `src/app.py`, `src/config.py`).

---

## Visão Geral

- A MAIA é um agente **determinístico**, que consulta **exclusivamente** bases locais na pasta `data/` para produzir as respostas.  
- O **LLM (Ollama)** é **opcional** e atua **apenas** na **reescrita** do texto final (clareza/organização). **Nunca** calcula, cria fatos ou altera números.
- Sempre que uma resposta usar alguma base, a MAIA finaliza com um **rodapé de Fontes**:  
  `> **Fontes**: transacoes.csv, perfil_investidor.json, ...`

### Bases padrão
- `transacoes.csv`  
- `perfil_investidor.json`  
- `produtos_financeiros.json`  
- (opcional) `historico_atendimento.csv` — apenas para **exibir contexto** no botão “Ver contexto atual”.

### Janela de análise (dias)
Definida na **sidebar** (7–90 dias). Todos os cálculos que dependem de transações respeitam esta janela.

---

## Arquitetura (alto nível)

1. **Usuário pergunta** (chat UI — `app.py`).  
2. **Roteador de intenções** (regex + normalização sem acentos, em `agente.py`).  
3. **Executor determinístico**:
   - Lê a(s) base(s) necessárias;
   - Calcula/filtra (sem inventar);
   - Monta texto + **rodapé de Fontes**.
4. **(Opcional) LLM** reescreve o texto (sem mudar números/fatos).  
5. A resposta é exibida por streaming no chat.

> **Nota**: quando uma base estiver ausente/vazia para a intenção, a MAIA **admite a limitação** (ex.: “Não encontrei transações…”), em vez de inventar.

---

## Intenções Suportadas

> O reconhecimento não depende de frases fixas. Usamos **normalização** (removendo acentos) + **gatilhos** + **regex**.

1. **Gasto total no período**  
   - Ex.: “quanto gastei?”, “gastei quanto?”  
   - **Base**: `transacoes.csv`  
   - **Cálculo**: soma de **saídas** na **janela**.  
   - **Funções**: `eh_intencao_total_gasto` → `resposta_total_gasto`

2. **Gasto por categoria**  
   - Ex.: “quanto gastei com alimentação?”  
   - **Base**: `transacoes.csv`  
   - **Cálculo**: soma de saídas para a categoria (com sinônimos).  
   - **Funções**: `eh_intencao_gasto_categoria` → `resposta_gasto_categoria`

3. **Saldo no período**  
   - Ex.: “qual é meu saldo?”, “quanto sobrou?”  
   - **Base**: `transacoes.csv`  
   - **Cálculo**: entradas – saídas na janela.  
   - **Funções**: `eh_intencao_saldo` → `resposta_saldo`

4. **Maior gasto**  
   - Ex.: “qual foi meu maior gasto?”, “categoria mais cara?”  
   - **Base**: `transacoes.csv`  
   - **Cálculo**: categoria líder em despesas + maior transação.  
   - **Funções**: `eh_intencao_maior_gasto` → `resumo_maior_gasto`

5. **Recomendação (educativa, compatível com perfil)**  
   - Ex.: “qual investimento você recomenda para mim?”, “onde investir?”  
   - **Bases**: `perfil_investidor.json`, `transacoes.csv`, `produtos_financeiros.json`  
   - **Lógica**:
     - Estima **gasto mensal** (saídas escaladas para 30 dias) para **reserva 3–6 meses**;
     - Verifica se já existe valor acumulado para reserva no perfil;
     - Lista **exemplos compatíveis** por **risco** (conservador/moderado/arrojado) — **sem recomendar ativo específico**;
     - **Rodapé de Fontes** com as três bases.
   - **Funções**: `eh_intencao_recomendacao` → `resposta_recomendacao_contextual`

6. **Produtos (listagem/explicação)**  
   - Ex.: “explique CDB”, “quais produtos de renda fixa?”  
   - **Base**: `produtos_financeiros.json`  
   - **Funções**: `buscar_produto` (usa `tpl_resposta_produtos`)

7. **“Quanto rende X?”**  
   - Ex.: “quanto rende Tesouro Selic?”, “quanto rende produto XYZ?”  
   - **Base**: `produtos_financeiros.json`  
   - **Comportamento**: se não achar, **admite** ausência (não inventa).  
   - **Funções**: `eh_intencao_rentabilidade_produto` → `resposta_rentabilidade_produto`

8. **Perfil de investidor**  
   - Ex.: “qual o meu perfil de investidor?”  
   - **Base**: `perfil_investidor.json`  
   - **Funções**: `eh_intencao_perfil_investidor` → `resposta_perfil_investidor`

9. **Metas (simulação)**  
   - Ex.: “quero juntar 10000 em 12 meses”  
   - **Cálculo**: aporte mensal (com/sem taxa) — **determinístico**.  
   - **Funções**: `simular_meta_dados` (detalhamento passo a passo pode ser feito no próximo turno)

10. **Guardrails**  
   - **Fora do escopo**: clima, medicina, etc. → recusa educada.  
   - **Dados sensíveis**: senha, CPF, CVV → recusa imediata.

11. **Fallback**  
   - Sugere exemplos úteis quando a intenção não é reconhecida.

---

## LLM (Ollama) — Modo Opcional

- **Quando ON**: a UI chama `reescrever_com_llm` com:
  - `INSTRUÇÕES` (estilo/ênfase)
  - `FATOS` (números e dados calculados)
  - `FONTES` (arquivos consultados — para citar no rodapé)
- **Nunca substitui** os números do determinístico; serve apenas para **clareza**.

> **Modelos disponíveis (configuráveis na sidebar):** `mistral:7b-instruct`, `mistral:latest`, `phi3:mini`, `llama3.2:3b-instruct`.

---

## Execução

```bash
# requisitos
pip install -r src/requirements.txt

# executar
streamlit run src/app.py
