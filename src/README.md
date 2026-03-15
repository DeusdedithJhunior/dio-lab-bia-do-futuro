***

# 📘 MAIA — Assistente Financeira (MVP Local)

MAIA é uma assistente financeira educativa 100% **local**, construída com:

*   **Streamlit** (interface)
*   **Motor determinístico em Python** (cálculos reais)
*   **LLM local via Ollama** (reescrita opcional de respostas)
*   **Base de conhecimento mockada** (CSV + JSON em `/data`)

O objetivo é oferecer uma experiência fluida, segura e offline para análises de orçamento, metas e explicações financeiras.

***

## 📂 Estrutura do Repositório

    .
    ├── data/                       # Base mockada (CSV/JSON)
    │   ├── transacoes.csv
    │   ├── historico_atendimento.csv
    │   ├── perfil_investidor.json
    │   └── produtos_financeiros.json
    │
    ├── src/                        # Código-fonte principal
    │   ├── app.py                  # Interface Streamlit
    │   ├── agente.py               # Lógica determinística e ferramentas do agente
    │   ├── config.py               # Configurações (modelos, URL do Ollama, system prompt)
    │   └── requirements.txt        # Dependências do projeto
    │
    └── README.md                   # Este arquivo (documentação principal)

***

## 🧠 Componentes do Sistema

### 🔹 `app.py`

*   Controla a interface em Streamlit
*   Renderiza histórico, saudação personalizada e barra de input
*   Integra com `agente.py` para cálculos e decisões
*   Integra com Ollama (quando ativado)
*   Faz streaming das respostas

### 🔹 `agente.py`

*   Análise de orçamento
*   Simulação de metas
*   Identificação de maior gasto
*   Busca de produtos financeiros
*   Guardrails (LGPD, fora de escopo)
*   Formatação markdown
*   Wrapper do Ollama
*   Detecção de intenções (“meta”, “maior gasto”, “orçamento”, etc.)

### 🔹 `config.py`

*   Modelos disponíveis do Ollama
*   URL do servidor local (`http://localhost:11434/api/chat`)
*   Modelo padrão (`mistral:7b-instruct`)
*   System prompt da MAIA
*   Janela de análise padrão

### 🔹 Pasta `data/`

*   Contém as bases que alimentam o motor determinístico
*   Todos os dados são mockados e **não representam pessoas reais**

***

## 🛠 Dependências

Arquivo: `src/requirements.txt`

```txt
streamlit==1.31.0
pandas==2.2.1
requests==2.31.0
```

***

## ▶️ Como Rodar o Projeto

### 1) Clonar o repositório

```bash
git clone https://github.com/SeuUsuario/SeuRepositorio.git
cd SeuRepositorio
```

***

### 2) Criar e ativar ambiente virtual

#### Windows – PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

***

### 3) Instalar dependências

```bash
pip install -r src/requirements.txt
```

***

### 4) (Opcional, mas recomendado) Instalar modelo do Ollama

Se quiser usar a reescrita por IA local:

```bash
ollama pull mistral:7b-instruct
```

Testar:

```bash
ollama list
```

> Se preferir, também funciona com:  
> `mistral:latest`, `llama3.2:3b-instruct`, `phi3:mini`  
> Basta selecionar na sidebar do app.

***

### 5) Executar a aplicação

```bash
cd src
streamlit run app.py
```

O app abrirá automaticamente em:

    http://localhost:8501

***

## 🧭 Como Usar a MAIA

*   A MAIA dá boas-vindas chamando você pelo nome (vindo do perfil)
*   Pergunte:
    *   “qual foi o meu maior gasto?”
    *   “quero juntar 10 mil em 12 meses”
    *   “o que é um BDR?”
    *   “por que meus gastos subiram?”
*   Responda “sim” para ver cálculos passo a passo
*   Ative o modo **“Usar LLM local (Ollama)”** para respostas mais naturais

***

## 🔐 Segurança

*   Não solicita nem aceita: senha, CPF, CVV, token, dados de terceiros
*   Não responde temas fora de finanças
*   Não faz recomendações de investimento
*   Não acessa APIs externas
*   Todo conteúdo é mockado para fins educacionais

***

## 🚀 Roadmap (opcional)

*   ☑ Refatoração em módulos
*   ☐ Gráficos de orçamento
*   ☐ Dashboard consolidado
*   ☐ Exportação de relatório em PDF
*   ☐ Modo de voz (TTS/STT)
*   ☐ Integração com FAISS para histórico expandido

***

## 💬 Suporte

Abra uma **issue** ou envie sugestões via PR.  
Sinta-se à vontade para adaptar, melhorar e evoluir a MAIA.

***
