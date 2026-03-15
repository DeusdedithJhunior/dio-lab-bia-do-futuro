# Base de Conhecimento

## Dados Utilizados

A base de conhecimento utiliza os arquivos da pasta `data/`, que representam o **conjunto mínimo e realista** para análise financeira no MVP.

| Arquivo                         | Formato | Utilização no Agente                                                                                                                                                                                                                 |
| ------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`historico_atendimento.csv`** | CSV     | Contextualiza interações anteriores (`data`, `canal`, `tema`, `resumo`, `resolvido`) para que a MAIA mantenha continuidade no atendimento e evite repetição.                                                                         |
| **`perfil_investidor.json`**    | JSON    | Contém dados pessoais e financeiros do usuário (`renda_mensal`, `perfil_investidor`, `metas`, `objetivo_principal`). Usado para **personalizar explicações**, priorizar metas e calibrar respostas (sem recomendação).               |
| **`produtos_financeiros.json`** | JSON    | Catálogo de produtos de referência (Tesouro Selic, CDB, LCI/LCA, **Ações**, **FIIs**, **Criptoativos**, **BDRs**). Usado para FAQs didáticas, comparações e **citação de fonte**.                                                    |
| **`transacoes.csv`**            | CSV     | Análise de comportamento financeiro. Estrutura: `data`, `descricao`, `categoria`, `valor`, `tipo`. Serve para orçamento, padrões de gasto e apoio às simulações. Não há `user_id`: o dataset representa um **cliente único** no MVP. |

***

## Adaptações nos Dados

Os arquivos foram mantidos **quase totalmente intactos**, com **apenas uma alteração planejada** para fins didáticos:

### ✔ `produtos_financeiros.json` (alterado intencionalmente)

Trocamos produtos mais complexos por opções **mais familiares ao usuário leigo**:

*   **Ações** (mercado variável, risco alto)
*   **FIIs** (fundos imobiliários, variável)
*   **Criptoativos** (alta volatilidade)
*   **BDRs** (exposição ao dólar)
*   Mantivemos RF: Tesouro Selic, CDB, LCI/LCA

**Motivos:**

1.  Facilitar explicações sobre renda fixa x variável.
2.  Demonstrar risco, volatilidade e exposição ao câmbio.
3.  Permitir que a MAIA eduque o usuário sem prometer retorno.

> Todos os dados são **mockados** e não constituem recomendação ou sugestão de investimento.

***

## Estratégia Geral de Integração da Base

A MAIA segue uma arquitetura **híbrida**, formada por:

### 1) **Motor Determinístico (Python)** → Fonte de verdade

Tudo que envolve **cálculo**, **busca**, **formatação de fatos**, **validação** ou **insumos numéricos** é feito **localmente**, incluindo:

*   janela de transações
*   totais (entrada/saída/saldo)
*   top categorias
*   cálculo de aporte mensal (metas)
*   resumo de produtos
*   montagem do contexto

Esse motor garante:

*   consistência
*   ausência de alucinação
*   rastreabilidade dos dados
*   decisões transparentes

### 2) **LLM Local (Ollama)** → Reescrita natural (opcional)

O LLM **não calcula** nada.  
Ele recebe **apenas os fatos determinísticos** e gera uma explicação mais fluida e natural.

O LLM funciona como um **"narrador inteligente"**, não como fonte de verdade.

#### APIs utilizadas no projeto:

*   `/api/chat` → multi-turn (mensagens como system/user/assistant)
*   Modelos recomendados:
    *   `llama3.2:3b-instruct`
    *   `phi3:mini`
    *   `mistral:7b-instruct`

Se o LLM falhar/estiver desligado, MAIA responde com **templates determinísticos bem formatados** (fallback seguro).

***

## Estratégia de Uso da Base de Conhecimento

### A MAIA **não envia** a base inteira ao LLM.

Ela utiliza **recortes inteligentes**, selecionados conforme intenção:

### 1) Na intenção **orcamento**

Contexto inclui:

*   janela X dias
*   entradas, saídas, saldo
*   top categorias
*   últimas transações
*   (opcional) histórico recente

### 2) Na intenção **meta**

Contexto inclui:

*   valor da meta
*   prazo
*   aporte inicial
*   cálculo determinístico
*   passo a passo **sob demanda** (usuário responde “sim”)

### 3) Na intenção **produtos**

Inclui somente:

*   produtos relacionados à pergunta
*   resumo amigável
*   riscos principais
*   observações educativas (cripto, volatilidade; BDR, exposição ao dólar)

### 4) Na intenção **faq**

Inclui:

*   perfil do usuário
*   metas existentes
*   histórico recente

***

## Exemplos de Uso com LLM (Versão Oficial)

### 1) Reescrita de orçamento (Ollama)

```python
payload = {
    "model": "llama3.2:3b-instruct",
    "messages": [
        {"role": "system", "content": "Você é a MAIA... regras de segurança..."},
        {"role": "user", "content": (
            "Reescreva de forma clara e didática, sem inventar nada. "
            "Use SOMENTE os fatos a seguir:\n"
            "Janela_dias=30\n"
            "Entradas=R$ 5000\n"
            "Saidas=R$ 2364\n"
            "Saldo=R$ 2636\n"
            "TopCategorias=Alimentacao:450; Moradia:1200; Lazer:55\n"
        )}
    ],
    "options": {"temperature": 0.2}
}
```

***

## Exemplo de Contexto Montado (oficial)

```text
Perfil do cliente:
- Nome: João Silva
- Renda mensal: R$ 5000.00
- Perfil investidor: moderado
- Objetivo principal: Construir reserva de emergência

Metas:
- Completar reserva de emergência: R$ 15000.00 até 2026-06

Últimas transações (até 10 linhas):
- 2025-10-03 · Supermercado · alimentacao · R$ 450,00 · saida
- 2025-10-10 · Restaurante · alimentacao · R$ 120,00 · saida
- 2025-10-12 · Uber · transporte · R$ 45,00 · saida

Interações recentes:
- 2025-10-12: chat · Metas financeiras — Cliente acompanhou o progresso (resolvido: sim)

Produtos de referência (fonte: produtos_financeiros.json):
- Tesouro Selic (renda_fixa, risco baixo)
- CDB (renda_fixa, risco baixo)
- Ações (renda_variavel, risco alto)
- Criptoativos (alta volatilidade)
- BDRs (exposição ao dólar)

Instruções:
- Use APENAS os dados acima.
- Não invente informações.
- Citar fonte ao explicar produtos.
- Não prometa retornos financeiros.
```

***

## Regras Específicas de Comportamento da MAIA (Baseado na Base de Conhecimento)

### Ao falar de **BDRs**

*   Sempre mencionar **exposição ao dólar**.

### Ao falar de **Criptoativos**

*   Sempre mencionar **alta volatilidade**.
*   Sempre classificar como **educacional**, nunca recomendação.

### Ao fazer cálculos de meta

*   Se o usuário pedir:  
    → “*Quer ver o passo a passo?*”  
    e ele responder “**sim**”:  
    → mostrar equações + substituições numéricas.

### Ao falar de orçamento

*   Sempre trazer:
    *   entradas
    *   saídas
    *   saldo
    *   principais categorias
    *   transações recentes

***

## Conclusão

A **Base de Conhecimento** é o alicerce da MAIA.  
Ela fornece **dados reais, estáveis e explicáveis**, enquanto o **Ollama local** permite:

*   respostas mais naturais,
*   tom humano,
*   sem perda de precisão,
*   sem dependência de API paga.

A estrutura atual combina:

*   **determinístico (exatidão)**
*   **LLM local (naturalidade)**
*   **guardrails (segurança obrigatória)**
*   **contexto recortado (anti-alucinação)**

Tudo rodando **localmente**, **offline**, **custo zero**.

***
OU  
➡️ o `README.md` de instalação/execução final do projeto MAIA.
