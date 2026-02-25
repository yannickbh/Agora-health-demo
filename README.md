# 🏥 Assistente Hospitalar — Powered by Agora ConvoAI

Um agente de IA por voz para atendimento a pacientes e visitantes de hospitais. Pacientes podem **ligar e falar naturalmente** para obter respostas instantâneas de uma base de conhecimento com **50+ perguntas frequentes** — sem esperar na linha.

Construído com **Agora ConvoAI** + **OpenAI GPT-4o** + **OpenAI TTS**.

---

## Arquitetura

```
Paciente (microfone do navegador) ──► Canal Agora ──► Agente ConvoAI
                                                          │
                                                  GPT-4o (Base de Conhecimento)
                                                          │
                                                  OpenAI TTS (shimmer)
                                                          │
                                  Canal Agora ◄──── Resposta por Voz
```

---

## Quick Start

### 1. Criar e ativar ambiente virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar credenciais

```bash
cp .env.example .env
# Preencha suas chaves Agora, OpenAI (e opcionalmente Azure TTS) no .env
```

Você precisará de:

| Credencial | Onde obter |
|---|---|
| Agora App ID + Certificate | [console.agora.io](https://console.agora.io) |
| Agora Customer ID + Secret | console.agora.io → Perfil → RESTful API |
| OpenAI API Key | [platform.openai.com](https://platform.openai.com) |
| Azure TTS Key *(opcional)* | [portal.azure.com](https://portal.azure.com) |

> ⚠️ A funcionalidade **Conversational AI** precisa estar ativada no seu App ID no console Agora.

### 4. Iniciar o servidor

```bash
# Windows
.venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000

# Linux/Mac
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 5. Abrir no navegador

Acesse **http://127.0.0.1:8000** e clique em **Iniciar Chamada** 🎙️

---

## Base de Conhecimento

O agente conhece 50+ perguntas frequentes sobre o hospital nas seguintes categorias:

| Categoria | Qtd |
|---|---|
| Consultas e Agendamentos | 5 |
| Emergência e Pronto Atendimento | 5 |
| Cadastro e Convênios | 5 |
| Faturamento e Pagamentos | 5 |
| Prontuários Médicos | 5 |
| Horários de Visita e Normas | 5 |
| Departamentos e Serviços | 5 |
| Medicamentos e Prescrições | 5 |
| Exames e Procedimentos | 5 |
| Direitos do Paciente e Privacidade | 5 |

Para personalizar, edite `backend/data/knowledge_base.md`. As alterações são aplicadas ao iniciar uma nova chamada (não é necessário reiniciar o servidor).

---

## Endpoints da API

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/` | Página principal (frontend) |
| POST | `/start` | Inicia o agente IA em um canal |
| POST | `/stop/{channel}` | Para o agente IA |
| GET | `/token/{channel}/{uid}` | Gera token RTC para um usuário |
| GET | `/config` | Retorna o App ID (para o frontend) |
| GET | `/status` | Lista sessões ativas |
| GET | `/health` | Health check |

---

## Estrutura do Projeto

```
hospital-support-agent/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py             # Pydantic Settings (.env loader)
│   ├── routers/
│   │   ├── agent.py          # /start, /stop endpoints
│   │   └── system.py         # /health, /status, /token, /config
│   ├── services/
│   │   └── agora.py          # Token gen, Agora API helpers
│   └── data/
│       ├── knowledge_base.md # Base de conhecimento hospitalar
│       └── prompts.txt       # System prompt do agente
├── frontend/
│   ├── index.html            # UI principal
│   ├── css/styles.css        # Estilos
│   └── js/app.js             # Lógica Agora RTC + ConvoAI
├── .env.example              # Template de configuração
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Licença

MIT
