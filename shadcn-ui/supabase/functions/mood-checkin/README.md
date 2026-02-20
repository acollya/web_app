# Mood Check-in Edge Function

Processar check-ins de humor com análise IA opcional.

## Funcionalidades

- ✅ Registrar check-ins de humor
- ✅ Validação de dados
- ✅ Insights IA com OpenAI (opcional)
- ✅ Salvamento no banco de dados

## Variáveis de Ambiente

```bash
OPENAI_API_KEY=sk-... (opcional)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

## Deploy

```bash
supabase functions deploy mood-checkin
```

## Uso

### Request

```bash
POST /mood-checkin
Authorization: Bearer <jwt-token>

{
  "userId": "uuid-do-usuario",
  "mood": "ansioso",
  "intensity": 7,
  "note": "Dia estressante no trabalho",
  "activities": ["trabalho", "exercício"],
  "generateInsight": true
}
```

### Response

```json
{
  "success": true,
  "checkin": {
    "id": "checkin-123",
    "mood": "ansioso",
    "intensity": 7,
    "note": "Dia estressante no trabalho",
    "createdAt": "2025-01-15T10:30:00Z"
  },
  "insight": "É compreensível sentir ansiedade em dias estressantes. Lembre-se de fazer pausas e praticar respiração profunda quando se sentir sobrecarregado.",
  "message": "Check-in de humor registrado com sucesso! 💙"
}
```

## Parâmetros

- `userId` (obrigatório): UUID do usuário
- `mood` (obrigatório): Tipo de humor (feliz, triste, ansioso, etc.)
- `intensity` (obrigatório): Intensidade 1-10
- `note` (opcional): Nota adicional
- `activities` (opcional): Lista de atividades do dia
- `generateInsight` (opcional): Gerar insight IA (padrão: false)

## Insights IA

Se `generateInsight: true` e `OPENAI_API_KEY` configurado:
- Gera insight personalizado com GPT-3.5-turbo
- Insight empático e encorajador (2-3 frases)
- Fallback para mensagem padrão se API falhar