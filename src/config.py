# -*- coding: utf-8 -*-
"""
config.py — Configurações do projeto MAIA
-----------------------------------------
Mantém as constantes do app: modelos, URL do Ollama, janela padrão e o SYSTEM_PROMPT.
Não depende de credenciais externas.
"""

# Ollama (endpoint local)
OLLAMA_URL: str = "http://localhost:11434/api/chat"

# Modelo padrão do projeto (pode ser trocado na sidebar)
OLLAMA_MODEL_DEFAULT: str = "mistral:7b-instruct"

# Lista de modelos oferecidos na UI (você pode incluir outros que instalar)
OLLAMA_MODELS = [
    "mistral:7b-instruct",
    "phi3:mini",
    "llama3.2:3b-instruct",
]

# Parâmetros de análise
DEFAULT_WINDOW_DAYS: int = 30

# Prompt do sistema (regras de segurança e estilo)
SYSTEM_PROMPT: str = (
    "Você é a MAIA, assistente financeira educativa. Responda com clareza, sem prometer retornos. "
    "Use apenas o contexto e os FATOS fornecidos (calculados pelo motor determinístico). "
    "Não invente números; não crie novos fatos. "
    "Ao falar de produtos, use tom educativo e cite 'produtos_financeiros.json' como fonte. "
    "BDRs têm exposição ao dólar; Cripto tem alta volatilidade. "
    "Em cálculos, ofereça 'Quer ver como calculei?'. "
    "Nunca peça senha/CPF/CVV; recuse temas fora de finanças. "
    'Formate em Markdown enxuto (títulos e bullets quando fizer sentido).'
)