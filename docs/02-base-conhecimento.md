# Base de Conhecimento

## Dados Utilizados

A base de conhecimento utiliza os arquivos da pasta `data/`, que representam o **conjunto mínimo e realista** para análise financeira no MVP.

| Arquivo                         | Formato | Utilização no Agente                                                                                                                                                                                                                 |
| ------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`historico_atendimento.csv`** | CSV     | Contextualiza interações anteriores (`data`, `canal`, `tema`, `resumo`, `resolvido`) para que a MAIA mantenha continuidade no atendimento e evite repetição.                                                                         |
| **`perfil_investidor.json`**    | JSON    | Contém dados pessoais e financeiros do usuário (`renda_mensal`, `perfil_investidor`, `metas`, `objetivo_principal`). Usado para **personalizar explicações**, priorizar metas e calibrar respostas (sem recomendação).               |
| **`produtos_financeiros.json`** | JSON    | Catálogo de produtos de referência (Tesouro Selic, CDB, LCI/LCA, **Ações**, **FIIs**, **Criptoativos**, **BDRs**). Usado para FAQs didáticas, comparações e **citação de fonte**.                                                    |
| **`transacoes.csv`**            | CSV     | Análise de comportamento financeiro. Estrutura: `data`, `descricao`, `categoria`, `valor`, `tipo`. Serve para orçamento, padrões de gasto e apoio às simulações. Não há `user_id`: o dataset representa um **cliente único** no MVP. |

---

## Adaptações nos Dados

Os arquivos foram mantidos **quase totalmente intactos**, com **apenas uma alteração planejada** para fins didáticos:

### ✔ `produtos_financeiros.json` (alterado intencionalmente)

Incluímos produtos familiares ao usuário leigo:

- **Ações**  
- **FIIs**  
- **Criptoativos** (alta volatilidade)  
- **BDRs** (exposição ao dólar)  
- Tesouro Selic, CDB, LCI/LCA (renda fixa)

> Todos os dados são **mockados** e não constituem recomendação.

---

## Estratégia Geral de Integração da Base

### 1) **Motor Determinístico (Python)** — *Fonte de Verdade*

O motor determinístico é responsável por:

- Cálculos financeiros  
- Detecção de intenção  
- Agregações (entrada, saída, saldo)  
- Top categorias  
- Aporte mensal (metas)  
- Maior gasto  
- Resumo de produtos  
- Montagem do contexto

Ele garante:

- Consistência  
- Transparência  
- Rastreabilidade  
- Zero alucinação  

### 2) **LLM Local (Ollama)** — *Reescrita Natural (Opcional)*

- O LLM **não calcula**  
- Recebe **somente fatos determinísticos**  
- Reescreve respostas de forma mais fluida  
- Nunca recebe o CSV inteiro  
- Funciona como **narrador**, não como fonte de verdade  

APIs usadas:  
- `/api/chat`  
Modelos comuns:  
- `mistral:7b-instruct`  
- `mistral:latest`  
- `phi3:mini`

---

# 🎛️ Menu Lateral (Sidebar) — Impacto na Base de Conhecimento

A sidebar é um componente padrão da MAIA e **controla como a base de conhecimento é usada**.

## Componentes da Sidebar e relação com a base

### **1. Usar LLM local (Ollama)**
- **ON:** o LLM reescreve o texto, usando os fatos determinísticos.  
- **OFF:** respostas puramente determinísticas, sem IA.  
*A base consultada é a mesma; só muda o formato da resposta.*

---

### **2. Modelo (Ollama)**
Ex.: `mistral:7b-instruct`, `mistral:latest`, `phi3:mini`.

- Define *como* a resposta será escrita (estilo).  
- Os cálculos e dados permanecem iguais.

---

### **3. Janela de Análise (dias)**
Afeta diretamente:

- quantidade de transações carregadas  
- cálculo de entradas  
- cálculo de saídas  
- saldo  
- categorias principais  
- maior gasto  
- últimas transações mostradas  

Esse parâmetro define **o recorte de dados do `transacoes.csv`** usado em cada análise.

---

### **4. Mostrar status dos arquivos (debug)**
Exibe se os arquivos da pasta `data/`:

- existem  
- estão no formato correto  
- podem ser carregados  

Recurso útil para auditoria e manutenção.

---

### **5. Ver contexto atual**
Mostra o contexto consolidado que o motor determinístico monta, incluindo:

- perfil  
- metas  
- transações filtradas pela janela  
- histórico  
- produtos disponíveis  

É uma ferramenta de transparência e depuração.

---

## Estratégia de Uso da Base por Intenção

### 🔹 **Intenção: orçamento**
Usa:

- transações filtradas pela janela  
- totais  
- saldo  
- categorias  
- transações recentes  
- histórico opcional  

### 🔹 **Intenção: meta**
Inclui:

- valor da meta  
- prazo  
- aporte inicial  
- cálculo determinístico  
- passo a passo sob demanda  

### 🔹 **Intenção: produtos**
Inclui:

- produtos relacionados à pergunta  
- rentabilidade geral (sem prometer retorno)  
- risco e observações educativas  
- citações obrigatórias de fonte  

### 🔹 **Intenção: maior gasto**
Inclui:

- categoria com maior soma  
- maior transação individual  
- janela escolhida  

### 🔹 **Intenção: FAQ**
Inclui:

- perfil  
- metas existentes  
- histórico breve  

---

## Conclusão

A **Base de Conhecimento** é o núcleo do processo da MAIA.  
Ela fornece **fatos concretos**, enquanto:

- o motor determinístico garante precisão e segurança  
- o Ollama (opcional) melhora a comunicação  
- a **sidebar define como os dados serão recortados e utilizados**

O resultado é um agente:

- explicável  
- transparente  
- auditável  
- totalmente local  
- sem dependência de serviços externos  
