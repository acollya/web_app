# Therapist Matching Edge Function

Algoritmo de matching inteligente de terapeutas baseado em preferências do usuário.

## Funcionalidades

- ✅ Matching baseado em múltiplos critérios
- ✅ Sistema de pontuação ponderada
- ✅ Ranking de compatibilidade
- ✅ Razões de match explicadas
- ✅ Top 3 terapeutas recomendados

## Variáveis de Ambiente

```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

## Deploy

```bash
supabase functions deploy therapist-matching
```

## Uso

### Request

```bash
POST /therapist-matching
Authorization: Bearer <jwt-token>

{
  "userId": "uuid-do-usuario",
  "answers": {
    "preferredGender": "female",
    "specializations": ["ansiedade", "depressão"],
    "ageRange": "middle",
    "approach": ["TCC", "Mindfulness"],
    "language": ["português"],
    "availability": "morning",
    "budget": "medium"
  }
}
```

### Response

```json
{
  "success": true,
  "matches": [
    {
      "id": "1",
      "name": "Dra. Ana Silva",
      "specialization": "Ansiedade e Depressão",
      "bio": "Especialista em TCC com 10 anos de experiência",
      "rating": 4.8,
      "hourlyRate": 150,
      "score": 85,
      "matchReasons": [
        "Gênero preferido",
        "Especialização em ansiedade, depressão",
        "Abordagem: TCC, Mindfulness",
        "Disponível no período: morning"
      ]
    }
  ],
  "totalAnalyzed": 4
}
```

## Critérios de Matching

| Critério | Peso | Descrição |
|----------|------|-----------|
| Gênero | 10 | Preferência de gênero do terapeuta |
| Especializações | 30 | Match de áreas de especialização |
| Faixa Etária | 5 | Preferência de idade do terapeuta |
| Abordagem | 20 | Abordagem terapêutica (TCC, EMDR, etc.) |
| Idioma | 10 | Idiomas falados |
| Disponibilidade | 10 | Horários disponíveis |
| Orçamento | 15 | Faixa de preço |
| Avaliação | 10 | Rating do terapeuta (bonus) |

**Score máximo:** 100 pontos