# Journal Reflection Edge Function

Edge Function para gerar reflexões empáticas sobre entradas de diário usando OpenAI.

## Funcionalidades

- ✅ Geração de reflexões personalizadas com GPT-3.5-turbo
- ✅ Validação de autenticação do usuário
- ✅ Salvamento automático da reflexão no banco
- ✅ Reflexões empáticas e encorajadoras
- ✅ Segurança: apenas o dono da entrada pode gerar reflexão

## Variáveis de Ambiente Necessárias

```bash
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

## Deploy

```bash
# Fazer deploy da função
supabase functions deploy journal-reflection

# Configurar secrets (se ainda não configurados)
supabase secrets set OPENAI_API_KEY=sk-...
```

## Uso

### Request

```bash
POST /journal-reflection
Content-Type: application/json
Authorization: Bearer <user-jwt-token>

{
  "entryId": "uuid-da-entrada",
  "content": "Hoje foi um dia difícil...",
  "userId": "uuid-do-usuario"
}
```

### Response (Sucesso)

```json
{
  "success": true,
  "reflection": "É compreensível que você esteja se sentindo assim. Dias difíceis fazem parte da jornada humana..."
}
```

### Response (Erro)

```json
{
  "error": "Usuário não autenticado"
}
```

## Estrutura de Dados

### Tabela: journal_entries
- `id`: UUID da entrada
- `user_id`: UUID do usuário
- `content`: conteúdo da entrada
- `ai_reflection`: reflexão gerada pela IA
- `created_at`: timestamp de criação
- `updated_at`: timestamp de atualização

### Tabela: users
- `name`: nome do usuário (usado para personalização)

## Características da Reflexão

A reflexão gerada pela IA:
- Valida os sentimentos expressos
- Oferece perspectivas positivas quando apropriado
- É breve (2-3 parágrafos)
- É calorosa e não julgadora
- Termina com uma pergunta reflexiva ou encorajamento

## Segurança

- Requer autenticação via JWT token
- Verifica se o usuário autenticado é o dono da entrada
- Usa Supabase Service Role Key apenas no backend
- Headers CORS configurados

## Exemplo de Integração Frontend

```typescript
const generateReflection = async (entryId: string, content: string) => {
  const { data: { session } } = await supabase.auth.getSession();
  
  const response = await fetch(
    `${SUPABASE_URL}/functions/v1/journal-reflection`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${session?.access_token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        entryId,
        content,
        userId: session?.user?.id,
      }),
    }
  );
  
  const result = await response.json();
  return result.reflection;
};
```