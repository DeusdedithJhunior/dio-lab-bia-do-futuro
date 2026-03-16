***

# Base de Conhecimento

A MAIA consulta **exclusivamente** as bases **locais** na pasta `data/`.  
Todos os cálculos e fatos são produzidos pelo **motor determinístico** (Python, em `agente.py`).  
Quando uma resposta usar dados dessas bases, ela **deve finalizar** com o rodapé:

> **Fontes**: *lista de arquivos efetivamente usados*.

Se a informação **não existir** nas bases, a MAIA **admite a ausência** (sem “completar” com suposição).

***

## 1) Dados Utilizados (arquivos em `data/`)

| Arquivo                         | Formato | Utilização no Agente                                                                                                                                                                                                                                                        |
| ------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`transacoes.csv`**            | CSV     | Base para **orçamento**: gasto total por período, gasto **por categoria** (com sinônimos), **saldo** (entradas – saídas), **maior gasto** (categoria líder + maior transação), e **estimativa de gasto mensal** (para reserva de 3–6 meses).                                |
| **`perfil_investidor.json`**    | JSON    | Dados do cliente para personalização **educativa**: `perfil_investidor` (conservador/moderado/arrojado), `renda_mensal`, `objetivo_principal`, `metas` (inclui valor já guardado para **reserva**, se existir).                                                             |
| **`produtos_financeiros.json`** | JSON    | Catálogo para **FAQ de produtos**, **“quanto rende X?”** (texto cadastrado), e para **exemplos educativos compatíveis** por **risco** na recomendação (sem indicar ativo específico). Observações educativas: BDR → **exposição ao dólar**; Cripto → **alta volatilidade**. |
| **`historico_atendimento.csv`** | CSV     | Opcional, voltado a **transparência e debug** (“Ver contexto atual”). **Não** altera cálculos. Pode futuramente servir a memória superficial (ex.: mostrar último tema), **sem** impactar números.                                                                          |

***

## 1.1) Alterações intencionais na base (MVP)

Para fins didáticos e para cobrir melhor as intenções do agente, **alteramos a base original** de produtos:

*   **`produtos_financeiros.json` — ampliado intencionalmente**
    *   **Ampliação do catálogo**: adicionamos **Ações**, **FIIs**, **Criptoativos** (alta volatilidade) e **BDRs** (exposição ao dólar), além de Tesouro Selic, CDB e LCI/LCA.
    *   **Padronização de campos por item**:
        *   `nome`, `categoria`, `risco` (`baixo`/`medio`/`alto`), `rentabilidade` (texto educativo, sem promessa), `liquidez` (se houver), `aporte_minimo` (número).
    *   **Usos no agente**:
        *   **FAQ/Explicação** e **“Quanto rende X?”** → a MAIA exibe o **texto** de `rentabilidade` cadastrado (não promete retorno).
        *   **Recomendação educativa** → a MAIA **filtra exemplos compatíveis** por **risco** do `perfil_investidor.json` (sem recomendar ativo específico).
    *   **Observações educativas aplicadas automaticamente**:
        *   **BDR** → citar **exposição ao dólar**.
        *   **Cripto** → citar **alta volatilidade**.
    *   **Atenção**: todos os dados são **mockados** e **não** constituem recomendação.

> Os demais arquivos (`transacoes.csv`, `perfil_investidor.json`, `historico_atendimento.csv`) **foram mantidos sem alterações estruturais**. O agente apenas **lê** esses dados localmente e, quando não encontra uma informação, **admite a ausência**.

***

## 2) Esquemas esperados (dicionário de dados)

### 2.1. `transacoes.csv` (obrigatório)

*   **Colunas obrigatórias**: `data`, `descricao`, `categoria`, `valor`, `tipo`
*   **Tipos**:
    *   `data`: ISO ou legível (parseado via `pd.to_datetime` com `errors='coerce'`)
    *   `descricao`: texto livre
    *   `categoria`: texto (ex.: Alimentação, Transporte, etc.)
    *   `valor`: número (positivo)
    *   `tipo`: texto (**“saida”** = despesa; qualquer outro valor = **entrada**)
*   **Janela de análise (dias)**: controlada na **sidebar** (7–90).  
    Se o filtro por data ficar vazio, a MAIA usa o **CSV completo** (fallback explícito na resposta).

**Categorias & sinônimos**  
Para mapear frases como “*Quanto gastei com comida?*”, o agente usa sinônimos canônicos (ex.: `alimentacao` ← alimentação, restaurante, mercado, refeição).  
Você pode **ampliar a lista** no código (`CATEGORIA_SINONIMOS`) conforme o vocabulário real.

***

### 2.2. `perfil_investidor.json` (obrigatório)

**Exemplo mínimo:**

```json
{
  "nome": "Cliente Fictício",
  "perfil_investidor": "Conservador",
  "renda_mensal": 5000,
  "objetivo_principal": "Reserva e curto prazo",
  "metas": [
    { "meta": "Reserva de emergência", "acumulado": 2000 }
  ]
}
```

**Campos usados:**

*   `perfil_investidor` → compatibilidade por **risco**:  
    Conservador → **baixo** | Moderado → **baixo/medio** | Arrojado → **baixo/medio/alto**
*   `metas` → se houver meta de “reserva” com valor (`acumulado`, `valor_ja_guardado`, `guardado`), a MAIA **reconhece** quanto já foi guardado.

***

### 2.3. `produtos_financeiros.json` (obrigatório)

**Exemplo de item:**

```json
{
  "nome": "Tesouro Selic",
  "categoria": "Renda Fixa",
  "risco": "baixo",
  "rentabilidade": "Pós-fixada próxima à Selic; adequada para reserva",
  "liquidez": "D+0/D+1",
  "aporte_minimo": 30.0
}
```

**Usos no agente:**

*   Listagem/explicação de produtos;
*   “Quanto rende X?” (exibe **o texto** de `rentabilidade` cadastrado);
*   Reforços educativos: **BDR** (exposição ao dólar), **Cripto** (alta volatilidade);
*   Filtragem por **risco** para **exemplos compatíveis** na recomendação educativa.

***

### 2.4. `historico_atendimento.csv` (opcional)

*   **Colunas**: `data`, `canal`, `tema`, `resumo`, `resolvido`
*   **Uso atual**: exibido em **“Ver contexto atual”** (sidebar) para **transparência** e **depuração**.
*   **Não** altera cálculos nem respostas determinísticas.

***

## 3) Estratégia determinística (Fonte de Verdade)

O **motor determinístico** (em `agente.py`) é responsável por:

*   Detecção de intenção (regex + normalização sem acento);
*   Leitura/filtragem das bases;
*   Cálculos (somas, agregações, metas);
*   Geração de texto com **rodapé de Fontes**.

**Anti‑alucinação**

*   Se a base estiver ausente/vazia para a intenção, a MAIA **admite** (“Não encontrei…”, “Não tenho essa informação…”).
*   Com LLM ON, o modelo **apenas reescreve**; **nunca** altera **números/fatos**.

***

## 4) Uso da Base por Intenção (Pergunta → Base(s))

| Intenção / Pergunta                             | Base(s) usada(s)                                                        | Observações determinísticas                                                                                            |
| ----------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **Gasto total no período** (“Quanto gastei?”)   | `transacoes.csv`                                                        | Soma **saídas** na **janela**.                                                                                         |
| **Gasto por categoria** (“…com alimentação?”)   | `transacoes.csv`                                                        | Soma **saídas** da **categoria** (sinônimos), respeitando **janela**.                                                  |
| **Saldo no período** (“Qual é meu saldo?”)      | `transacoes.csv`                                                        | **Entradas – saídas** na **janela**.                                                                                   |
| **Maior gasto** (“Qual foi meu maior gasto?”)   | `transacoes.csv`                                                        | Categoria líder + maior transação no período.                                                                          |
| **Recomendação (educativa)** (“Onde investir?”) | `perfil_investidor.json`, `transacoes.csv`, `produtos_financeiros.json` | Calcula **reserva 3–6 meses** (gasto mensal estimado) e lista **exemplos compatíveis** por **risco** (sem prescrição). |
| **Produtos (listagem/explicação)**              | `produtos_financeiros.json`                                             | Lista itens com **nome/categoria/risco/liquidez/rentabilidade textual**; BDR/Cripto com observações educativas.        |
| **“Quanto rende X?”**                           | `produtos_financeiros.json`                                             | Se o produto não existir, **admite** ausência (não inventa).                                                           |
| **Perfil de investidor** (“Qual meu perfil?”)   | `perfil_investidor.json`                                                | Exibe `perfil_investidor`, `renda_mensal`, `objetivo_principal`, contagem de `metas`.                                  |
| **Meta (simulação)**                            | — (determinístico puro)                                                 | Calcula aporte mensal (com/sem taxa).                                                                                  |
| **Fora do escopo / Sensíveis**                  | —                                                                       | Recusa educada; **sem** fontes.                                                                                        |

***

## 5) Efeito da Sidebar sobre a Base

1.  **Usar LLM (ON/OFF)**
    *   **OFF** → resposta 100% determinística;
    *   **ON** → LLM recebe **FATOS** + **INSTRUÇÕES** + **FONTES** e **apenas reescreve** (sem mudar números).  
        *A base consultada não muda — só a forma de redação.*

2.  **Modelo (Ollama)**
    *   Ex.: `mistral:7b-instruct`, `mistral:latest`, `phi3:mini`, `llama3.2:3b-instruct`
    *   Impacta o **estilo**, não os **fatos**.

3.  **Janela de análise (dias)**
    *   Recorta `transacoes.csv` para **todas as intenções** baseadas em transações (gasto total, categoria, saldo, maior gasto, gasto mensal estimado para reserva).

4.  **Mostrar status dos arquivos (debug)**
    *   Verifica existência/formato das bases. Útil para auditoria.

5.  **Ver contexto atual**
    *   Mostra um **snapshot** (perfil, amostra de transações filtradas, histórico, produtos). Não altera cálculos.

***

## 6) Boas práticas de manutenção da base

*   **`transacoes.csv`**: colunas exatas; datas válidas; valores numéricos; padronização de categorias.
*   **`perfil_investidor.json`**: `perfil_investidor` coerente; metas com campo de valor quando houver “reserva”.
*   **`produtos_financeiros.json`**: itens completos; `rentabilidade` em **texto educativo**; sem promessas de retorno.
*   **`historico_atendimento.csv`**: útil para transparência; não influencia números.

***

## 7) Regras de anti‑alucinação

1.  A MAIA só apresenta **números e fatos** derivados das bases **locais**.
2.  **Rodapé de Fontes** é obrigatório quando a resposta usa base(s).
3.  Se o dado **não existir**, a MAIA **diz que não tem**.
4.  Com LLM ON, o modelo **não** altera **números**; só **reescreve**.

***

## 8) Conclusão

A **Base de Conhecimento** é o núcleo do comportamento **explicável, auditável e local** da MAIA.  
O determinístico garante **precisão** e **segurança**; o LLM (opcional) melhora a **clareza** da resposta, **sem** tocar em números.  
A **sidebar** determina **como** os dados são recortados (janela) e **se** haverá reescrita pelo LLM.

**Resultado**: um agente **transparente**, **anti‑alucinação** e **focado no dado** que você controla.

***
