# Mood Insights Edge Function

Gerar insights e análises do histórico de check-ins de humor.

## Funcionalidades

- ✅ Análise de padrões de humor
- ✅ Cálculo de tendências (melhora/piora)
- ✅ Distribuição de humores
- ✅ Recomendações personalizadas
- ✅ Suporte a múltiplos períodos

## Variáveis de Ambiente

```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

## Deploy

```bash
supabase functions deploy mood-insights
```

## Uso

### Request

```bash
POST /mood-insights
Authorization: Bearer <jwt-token>

{
  "userId": "uuid-do-usuario",
  "period": "month"
}
```

**Períodos suportados:** `week`, `month`, `year`

### Response

```json
{
  "success": true,
  "insights": {
    "period": "month",
    "totalCheckins": 25,
    "averageMood": 6.8,
    "moodDistribution": {
      "feliz": 10,
      "ansioso": 8,
      "calmo": 7
    },
    "trends": [
      "Seu humor tem melhorado consistentemente! 📈",
      "Você tem se sentido predominantemente feliz! Continue cultivando essa positividade. 😊"
    ],
    "recommendations": [
      "Continue com as práticas que têm funcionado para você.",
      "Mantenha suas rotinas saudáveis e continue monitorando seu bem-estar."
    ],
    "mostCommonMood": "feliz",
    "moodImprovement": 15.3
  }
}
```

## Métricas Calculadas

- **averageMood**: Média de intensidade (1-10)
- **moodDistribution**: Contagem por tipo de humor
- **moodImprovement**: % de melhora comparando primeira e segunda metade do período
- **mostCommonMood**: Humor mais frequente
- **trends**: Observações sobre padrões
- **recommendations**: Sugestões personalizadas