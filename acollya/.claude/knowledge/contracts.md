# Technical Contracts

_Contratos que não podem mudar de forma unilateral — qualquer alteração exige atualização coordenada de todos os consumidores._

---

## SSE Chat Streaming Protocol

**Backend → Mobile** via Server-Sent Events. Localização: `app/api/v1/endpoints/chat.py`

```
event: delta
data: {"content": "texto parcial da resposta"}

event: done
data: {"message_id": "uuid", "usage": {"input_tokens": 123, "output_tokens": 456}}

event: error
data: {"code": "rate_limit", "message": "Limite de mensagens diário atingido. Tente novamente amanhã."}
```

**Invariantes:**
- Os 3 tipos de evento (`delta`, `done`, `error`) são fixos — não renomear
- `delta.content` é sempre string (chunk de texto)
- `done` sempre contém `message_id` e `usage`
- `error` sempre contém `code` e `message` em PT-BR
- O mobile (chatService.ts) parseia esses exatos campos

**Códigos de erro conhecidos:**
| code | HTTP | Situação |
|------|------|---------|
| `rate_limit` | 429 | Limite diário atingido |
| `trial_expired` | 402 | Trial encerrado |
| `auth_required` | 401 | Token expirado |
| `internal_error` | 500 | Erro genérico |

---

## Subscription Plan Codes

```
plan_code=0  →  Gratuito   →  10 msgs/dia  →  7 dias trial  →  R$0
plan_code=1  →  Essencial  →  20 msgs/dia  →  (sem trial)   →  R$39,90/mês
plan_code=2  →  Completo   →  ilimitado    →  (sem trial)   →  R$79,90/mês
```

**Regras:**
- `is_premium` = plan_code in (1, 2) AND status in ("active", "trialing")
- `is_essencial` = plan_code == 1 AND status == "active"
- `is_completo` = plan_code == 2 AND status == "active"
- trial aplica-se APENAS ao plano Free (plan_code=0, status="trialing")
- `_message_limit()` em `chat.py`: plan_code 2 → 9999, plan_code 1 → 20, else → 10

---

## RevenueCat Webhook

**Endpoint:** `POST /api/v1/subscriptions/webhook/revenuecat`

**Mapeamento product_id → plan_code:**
```python
_PRODUCT_PLAN_CODE = {
    "acollya_essencial_monthly": 1,
    "acollya_completo_monthly": 2,
}
_DEFAULT_PAID_PLAN_CODE = 2  # fallback para produtos não mapeados
```

**Eventos tratados:**
- `INITIAL_PURCHASE`, `RENEWAL`, `UNCANCELLATION` → GRANT (ativa plano)
- `CANCELLATION`, `EXPIRATION`, `BILLING_ISSUE` → REVOKE (desativa)

**Segurança:** Header `X-RevenueCat-Signature` validado via HMAC SHA256 com `revenue_cat_webhook_secret`

---

## JWT Auth

```
Algorithm: RS256
Access token:  15 minutos
Refresh token: 30 dias (rotação — invalidar o antigo ao renovar)
```

**Endpoints:**
- `POST /auth/token/refresh` — renova access token (body: `{refresh_token}`)
- Qualquer 401 no mobile → tentar refresh → se falhar → logout

---

## Embedding / RAG

```
Modelo:      text-embedding-3-small (OpenAI)
Dimensão:    1536
Threshold:   0.45 (cosine similarity)
Top-K:       5 chunks por query
```

**Tabelas com colunas Vector(1536):** `chat_messages`, `journal_entries`, `mood_checkins`

**Índice:** IVFFlat com `lists=50` (adequado até ~500k registros; escalar para `lists=100+` com >100k usuários)

---

## API Response Envelope

Todas as respostas de erro seguem:
```json
{
  "detail": "Mensagem em PT-BR",
  "code": "snake_case_code"
}
```

Respostas de sucesso: sem envelope — retornam o schema diretamente (Pydantic model).
