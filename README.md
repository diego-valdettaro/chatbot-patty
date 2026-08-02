# Chatbot de pedidos Patty

MVP local en Streamlit para validar un chatbot de pedidos B2C en espanol.

## Requisitos

- Python 3.14 o compatible.
- Entorno virtual en `.venv`.

## Instalacion

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Ejecutar la app

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Ejecutar tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Configuracion local del LLM

La integracion del agente usa OpenAI cuando `PATTY_LLM_MODEL` y `OPENAI_API_KEY` estan
configurados. Copia `.env.example` a `.env` y completa los valores. La aplicacion carga ese
archivo automaticamente al usar el chat; `.env` ya esta excluido de Git.

```powershell
PATTY_LLM_PROVIDER=openai
PATTY_LLM_MODEL=<modelo-elegido>
PATTY_LLM_REASONING_EFFORT=low
OPENAI_API_KEY=<tu-api-key>
LANGSMITH_API_KEY=<tu-langsmith-api-key>
LANGSMITH_PROJECT=patty-chatbot
```

Las variables definidas directamente en PowerShell tienen prioridad sobre los valores del `.env`.
El chat requiere LangSmith y siempre envia trazas al proyecto configurado.

## Code comments

Production code uses concise English comments to document business rules, layer boundaries,
state transitions, and non-obvious implementation decisions. New code should follow the same
style: explain why a block exists or which invariant it protects, rather than restating syntax.
