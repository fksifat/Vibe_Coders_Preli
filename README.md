# QueueStorm — AI-Powered Ticket Investigator

**SUST CSE Carnival 2026 · Codex Community Hackathon · Online Preliminary**

An AI-powered CRM ticket investigation service built with FastAPI and Gemini. Analyzes customer support tickets alongside transaction history to classify, route, and draft safe customer replies.

---

## 🚀 Quick Start

```bash
git clone <your-repo-url>
cd SUST_Hackathon_Preli

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Service is live at `http://localhost:8000`

---

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check → `{"status": "ok"}` |
| `POST` | `/analyze-ticket` | Investigate and classify a ticket |
| `GET` | `/docs` | Interactive Swagger UI |

### Example Request

```bash
curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-001",
    "complaint": "I sent 5000 taka to a wrong number around 2pm today.",
    "language": "en",
    "channel": "in_app_chat",
    "user_type": "customer",
    "transaction_history": [
      {
        "transaction_id": "TXN-9101",
        "timestamp": "2026-04-14T14:08:22Z",
        "type": "transfer",
        "amount": 5000,
        "counterparty": "+8801719876543",
        "status": "completed"
      }
    ]
  }'
```

---

## 🏗️ Architecture

```
app/
├── main.py                   # FastAPI app + middleware
├── api/routes.py             # /health + /analyze-ticket
├── models/
│   ├── request.py            # TicketRequest, TransactionEntry
│   └── response.py           # TicketResponse, HealthResponse
├── services/
│   ├── validator.py          # Input validation
│   ├── complaint_parser.py   # Extract amount, time hints, keyword signals
│   ├── transaction_matcher.py # Rule-based transaction ID matching
│   ├── evidence_engine.py    # consistent/inconsistent/insufficient_data
│   ├── classifier.py         # Gemini (primary) + rule-based (fallback)
│   ├── severity.py           # Deterministic severity rules
│   ├── router.py             # Deterministic department routing
│   ├── review_engine.py      # human_review_required decision
│   ├── safety.py             # Safety scrubber for customer_reply
│   └── response_generator.py # Main pipeline orchestrator
├── prompts/
│   └── investigator_prompt.txt # Gemini system prompt
└── utils/
    ├── enums.py              # All enums (spec-accurate)
    └── helpers.py            # JSON parser, language detector
```

---

## 🤖 AI Approach

### Gemini (Primary)
- **Model**: `gemini-2.5-flash` via `google-generativeai` SDK
- **Role**: Generates `case_type`, `agent_summary`, `recommended_next_action`, `customer_reply`
- **Context injected**: Full complaint, transaction history as JSON, pre-computed `relevant_transaction_id` and `evidence_verdict`
- **Temperature**: 0.15 (consistent, deterministic output)

### Rule-Based Logic (Always runs, overrides Gemini for critical fields)
- **Transaction matching**: Amount extraction → time filtering → type filtering → duplicate detection
- **Evidence verdict**: Established-recipient pattern detection, duplicate proof
- **Severity**: Deterministic per case type and evidence verdict
- **Department**: Exact spec mapping
- **Human review**: Calibrated against all 10 sample cases

### Fallback Chain
`Gemini` → `Rule-based classifier` (if API key missing, API error, or invalid response)

---

## 🛡️ Safety Logic

All outputs pass through a safety scrubber (`services/safety.py`):

1. **Credential protection** (−15 pts penalty): Detects and removes any sentence requesting PIN, OTP, password, or card number from `customer_reply`
2. **No unauthorized refunds** (−10 pts penalty): Replaces "we will refund you" → "any eligible amount will be returned through official channels"
3. **No third-party redirects** (−10 pts penalty): Detects and removes third-party contact instructions
4. **Prompt injection resistance**: Gemini prompt explicitly instructs the model to ignore instructions embedded in the complaint
5. **Credential reminder**: Every `customer_reply` ends with a safety reminder about not sharing PIN/OTP (language-aware: Bangla for `bn` complaints)

---

## 💰 Models & Cost Reasoning

| Model | Provider | Where it runs | Why chosen |
|-------|----------|--------------|------------|
| `gemini-2.5-flash` | Google AI | Gemini API (cloud) | Free tier available, fast (~2–5s), high accuracy for structured JSON output, multilingual (Bangla support) |

**Cost**: ~0 for the preliminary round volume on Gemini free tier. No GPU needed.

---

## 📦 Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI 0.115.6 |
| Validation | Pydantic v2 |
| AI | Google Gemini 2.5 Flash |
| Server | Uvicorn (ASGI) |
| Deployment | Render |
| Language | Python 3.11 |

---

## 🧪 Running Sample Case Tests

```bash
# With server running on localhost:8000
python tests/sample_cases.py
```

---

## ☁️ Deployment (Render)

1. Push to GitHub
2. Connect repo to [Render](https://render.com) → New Web Service
3. Set environment variable: `GEMINI_API_KEY=<your_key>`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Health check path: `/health`

Or use the included `render.yaml` for automatic configuration.

---

## ⚠️ Assumptions & Limitations

- Transaction history timestamps are used for time-based filtering; hidden test cases are assumed to have realistic relative timestamps
- Bangla language detection uses Unicode range `\u0980-\u09FF`
- The fallback rule-based classifier covers all 8 case types but has lower nuance than Gemini
- Gemini response time is typically 2–8 seconds; well within the 30s enforced limit
- Amount extraction uses regex; very unusual number formats may not be caught
