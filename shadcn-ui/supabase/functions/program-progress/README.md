# Program Progress Edge Function

Atualizar e gerenciar progresso em programas de autocuidado.

## Funcionalidades

- ✅ Marcar capítulos como concluídos
- ✅ Resetar progresso
- ✅ Calcular porcentagem de conclusão
- ✅ Tracking de progresso por programa

## Variáveis de Ambiente

```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

## Deploy

```bash
supabase functions deploy program-progress
```

## Uso

### Marcar Capítulo como Concluído

```bash
POST /program-progress
Authorization: Bearer <jwt-token>

{
  "userId": "uuid-do-usuario",
  "programId": "program-1",
  "chapterId": "chapter-3",
  "action": "complete"
}
```

### Resetar Progresso

```bash
POST /program-progress
Authorization: Bearer <jwt-token>

{
  "userId": "uuid-do-usuario",
  "programId": "program-1",
  "chapterId": "chapter-3",
  "action": "reset"
}
```

### Response

```json
{
  "success": true,
  "progress": {
    "totalChapters": 10,
    "completedChapters": 3,
    "percentageComplete": 30,
    "lastUpdated": "2025-01-15T10:30:00Z",
    "chapters": [
      {
        "id": "chapter-1",
        "completed": true,
        "completedAt": "2025-01-10T14:20:00Z"
      },
      {
        "id": "chapter-2",
        "completed": true,
        "completedAt": "2025-01-12T09:15:00Z"
      },
      {
        "id": "chapter-3",
        "completed": true,
        "completedAt": "2025-01-15T10:30:00Z"
      }
    ]
  },
  "message": "Capítulo marcado como concluído! 🎉"
}
```

## Ações Suportadas

- `complete`: Marca capítulo como concluído
- `reset`: Remove conclusão do capítulo