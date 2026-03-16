# Avaliação e Métricas

Este documento descreve **como avaliar** a MAIA e **quais métricas** acompanhar. As orientações refletem o funcionamento do agente no código final:

- Respostas **determinísticas** consultam **exclusivamente** as bases locais em `data/`:
  - `transacoes.csv`
  - `perfil_investidor.json`
  - `produtos_financeiros.json`
  - (opcional) `historico_atendimento.csv` para contexto de debug
- O **LLM (Ollama)** é **opcional** e **apenas reescreve** o texto; **não altera números**.
- Todas as respostas que usam base **devem finalizar** com o rodapé `> **Fontes**: ...`.

---

## Como Avaliar seu Agente

Há duas formas complementares de avaliar:

1. **Testes estruturados (scripts e caderno de testes)**  
   Você executa perguntas controladas e confere se a saída:
   - usa a **base correta** (verificando o rodapé e o cálculo);
   - respeita a **janela de análise** (dias) configurada na sidebar;
   - não “alucina” quando **não há dado** (retorna mensagem de ausência).

2. **Feedback real (testes com pessoas)**  
   3–5 pessoas usam o chat e pontuam de 1 a 5:
   - **Assertividade** (respondeu ao que foi perguntado?)
   - **Segurança** (evitou inventar? citou fontes?)
   - **Coerência** (compatível com o perfil do cliente?)
   - **Clareza** (texto claro; se LLM ligado, a reescrita ajudou?)

---

## Métricas de Qualidade

| Métrica                         | O que avalia                                                     | Como medir no projeto                                                                                                                             | Exemplo de teste                                                                 |
| ------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Assertividade**              | Se a resposta **cobre** exatamente a intenção da pergunta.       | Checar se a intenção correta foi disparada (gasto total vs. por categoria, saldo, recomendação, etc.).                                            | Perguntar *“Qual é meu saldo?”* e verificar entradas/saídas/saldo no `transacoes.csv`. |
| **Segurança (anti‑alucinação)**| Se o agente **não inventa** dados e **sempre cita as Fontes**.   | Conferir rodapé `> **Fontes**: ...` e as mensagens de “não encontrado” quando aplicável.                                                          | Perguntar *“Quanto rende o produto XYZ?”* quando XYZ não existe.                |
| **Coerência (perfil)**         | Se a resposta **respeita** o perfil do cliente.                  | Ver se recomendação educativa lista apenas exemplos compatíveis por **risco** (conservador/moderado/arrojado) com base em `perfil_investidor.json`. | Perguntar *“Onde investir?”* e conferir os exemplos vs. perfil.                 |
| **Confiabilidade de cálculo**  | Se somas e filtros batem com a base, respeitando a **janela**.   | Conferir cálculo de gasto/saldo/maior gasto na janela (7–90 dias).                                                                                | Perguntar *“Quanto gastei com alimentação?”* e cruzar com a soma no CSV.        |
| **Clareza da resposta**        | Se a redação é clara e estruturada (títulos, bullets).           | Com LLM ON, o texto deve estar mais “humano”, **preservando fatos**.                                                                              | Comparar respostas com LLM OFF vs. ON.                                          |
| **Citação de fontes**          | Se a resposta lista **exatamente** as bases consultadas.         | Conferir se aparecem “transacoes.csv”, “perfil_investidor.json”, “produtos_financeiros.json” conforme o caso.                                     | Qualquer pergunta que consulta base.                                            |

---

## Exemplos de Cenários de Teste

> **Regras da plataforma:**
>
> - **Janela de análise** controlada pela sidebar (7–90 dias).
> - **LLM OFF** para validar cálculo e fontes; **LLM ON** para avaliar clareza (sem alterar números).
> - Espera-se que toda resposta baseada em dados finalize com `> **Fontes**: ...`.

### Teste 1: Consulta de gastos (por categoria)

- **Pergunta:** `Quanto gastei com alimentação?`
- **O que o agente faz:**
  - Intenção: **gasto por categoria**
  - Base: `transacoes.csv`
  - Filtro: **tipo = saída** e **categoria ~ alimentação** (com sinônimos)
  - Respeita **janela** da sidebar
- **Resposta esperada:** Valor (soma) baseado no CSV com rodapé `Fontes: transacoes.csv`.
- **Critério de aceitação:** A soma bate com o total das saídas da categoria (na janela).
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 2: Recomendação de produto (educativa por perfil)

- **Pergunta:** `Qual investimento você recomenda para mim?`
- **O que o agente faz:**
  - Intenção: **recomendação educativa** (sem recomendar ativo)
  - Bases: `perfil_investidor.json`, `transacoes.csv`, `produtos_financeiros.json`
  - Passos:
    1. Estima **gasto mensal** (saídas escaladas para 30 dias)
    2. Sugere **reserva 3–6 meses** (apenas cálculo)
    3. Lista **exemplos compatíveis** por **risco** com o **perfil**
    4. Rodapé com **todas as fontes** usadas
- **Resposta esperada:** Texto educativo citando reserva, exemplos compatíveis por risco, sem “recomendar” título específico; rodapé com as três fontes.
- **Critério de aceitação:** Os exemplos respeitam o risco do perfil; nenhum ativo específico é prescrito.
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 3: Pergunta fora do escopo

- **Pergunta:** `Qual a previsão do tempo?`
- **O que o agente faz:**
  - Intenção: **fora do escopo** (guardrail)
  - Base: —
  - Responde educadamente que **só trata de finanças**.
- **Resposta esperada:** Mensagem de recusa educada; **sem** fontes (ou com nota de que não há dados de clima).
- **Critério de aceitação:** Não há tentativa de responder com dados inexistentes.
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 4: Informação inexistente

- **Pergunta:** `Quanto rende o produto XYZ?`
- **O que o agente faz:**
  - Intenção: **rentabilidade de produto**
  - Base: `produtos_financeiros.json`
  - Se **não encontrar**: admite ausência; **não inventa**.
- **Resposta esperada:** Mensagem de “não encontrado” + rodapé `Fontes: produtos_financeiros.json`.
- **Critério de aceitação:** A resposta é negativa (sem suposição) e cita a base correta.
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 5: Saldo no período

- **Pergunta:** `Qual é meu saldo?`
- **O que o agente faz:**
  - Intenção: **saldo**
  - Base: `transacoes.csv`
  - Cálculo: **entradas – saídas** respeitando a **janela**
- **Resposta esperada:** Entradas, saídas e saldo; rodapé `Fontes: transacoes.csv`.
- **Critério de aceitação:** Somas batem com o CSV (na janela).
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 6: Gasto total (sem categoria)

- **Pergunta:** `Quanto gastei?`
- **O que o agente faz:**
  - Intenção: **gasto total no período**
  - Base: `transacoes.csv`
  - Soma apenas **saídas** na **janela**
- **Resposta esperada:** Valor total de gastos no período; rodapé `Fontes: transacoes.csv`.
- **Critério de aceitação:** Soma de saídas na janela confere com o CSV.
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 7: Maior gasto

- **Pergunta:** `Qual foi meu maior gasto?`
- **O que o agente faz:**
  - Intenção: **maior gasto**
  - Base: `transacoes.csv`
  - Retorna **categoria líder** e **maior transação** no período
- **Resposta esperada:** Categoria e maior transação; rodapé `Fontes: transacoes.csv`.
- **Critério de aceitação:** Ambos (categoria líder e maior transação) são consistentes com o CSV na janela.
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 8: Perfil de investidor

- **Pergunta:** `Qual o meu perfil de investidor?`
- **O que o agente faz:**
  - Intenção: **perfil de investidor**
  - Base: `perfil_investidor.json`
  - Exibe perfil/renda/objetivo/metas (contagem)
- **Resposta esperada:** Informações do perfil; rodapé `Fontes: perfil_investidor.json`.
- **Critério de aceitação:** Valores exibidos correspondem ao JSON.
- **Resultado:** [x] Correto  [ ] Incorreto

### Teste 9: Fallback orientativo (pergunta ambígua)

- **Pergunta (exemplos):** `gasto total no período` / `me ajuda` / `não entendi`
- **O que o agente faz:**
  - Intenção: **não reconhecida** → **fallback**
  - Exibe uma lista curta de **perguntas do escopo**, baseadas nas intenções do projeto, por exemplo:
    - *Quanto gastei?*
    - *Quanto gastei com alimentação?*
    - *Qual é meu saldo?*
    - *Qual investimento você recomenda para mim?* (educativo, baseado no seu perfil)
    - *Quanto rende o produto Tesouro Selic?*
    - *Qual o meu perfil de investidor?*
- **Resposta esperada:** Mensagem de “Não entendi exatamente…” seguida de bullets com perguntas úteis do escopo (como na captura de tela).
- **Critério de aceitação:** Não tenta calcular nada; apenas orienta o usuário com itens coerentes com as bases do projeto.
- **Resultado:** [x] Correto  [ ] Incorreto

---

## Procedimento de Teste (passo a passo)

1. Abra o app:
   ```bash
   streamlit run src/app.py
