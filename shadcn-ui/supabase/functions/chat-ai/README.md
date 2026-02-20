# Chat AI Edge Function (Python)

Edge Function em Python para chat com IA usando OpenAI API.

## Funcionalidades

- ✅ Chat com GPT-3.5-turbo
- ✅ Limite de mensagens para usuários free (10/dia)
- ✅ Mensagens ilimitadas para usuários premium
- ✅ Salvamento automático de mensagens no Supabase
- ✅ Contador de mensagens diárias
- ✅ Sistema de sessões de chat

## Variáveis de Ambiente Necessárias

```bash
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

## Deploy

```bash
# Fazer deploy da função
supabase functions deploy chat-ai

# Configurar secrets
supabase secrets set OPENAI_API_KEY=sk-...
```

## Uso

### Request

```bash
POST /chat-ai
Content-Type: application/json

{
  "message": "Estou me sentindo ansioso hoje",
  "userId": "uuid-do-usuario",
  "sessionId": "uuid-da-sessao" // opcional
}
```

### Response (Sucesso)

```json
{
  "success": true,
  "response": "Resposta empática da IA...",
  "messagesRemaining": 7  // null para premium
}
```

### Response (Limite Atingido)

```json
{
  "error": "Limite de mensagens diário atingido. Faça upgrade para premium para mensagens ilimitadas."
}
```

## Estrutura de Dados

### Tabela: users
- `plan_code`: 0 (free) ou 1 (premium)
- `messages_today`: contador de mensagens do dia
- `name`: nome do usuário para personalização

### Tabela: chat_messages
- `user_id`: UUID do usuário
- `session_id`: UUID da sessão (opcional)
- `role`: 'user' ou 'assistant'
- `content`: conteúdo da mensagem
- `created_at`: timestamp

## Notas

- Usuários free: máximo 10 mensagens/dia
- Usuários premium (plan_code=1): mensagens ilimitadas
- O contador `messages_today` deve ser resetado diariamente (via cron job ou trigger)
- Implementado em Python conforme requisito do projeto