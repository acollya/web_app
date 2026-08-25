---
name: qa-expert
description: "QA strategy and quality perspective for Acollya. Test coverage goals, risk assessment, mobile+API testing checklist, release criteria, and quality gates. Use to think through quality before finalizing a feature — test-automator writes the actual tests."
---
# QA Expert — Acollya

Perspectiva de qualidade para o app Acollya. Este skill injeta raciocínio de QA no contexto atual — o agente `test-automator` é o responsável por **escrever** os testes.

## Quando usar

- Ao finalizar uma feature nova — "o que pode quebrar aqui?"
- Ao avaliar cobertura antes de um merge em `main`
- Ao identificar riscos em mudanças que tocam múltiplos serviços
- Ao planejar estratégia de testes para uma nova área

---

## Mapa de Risco — Acollya

### Tier 1 — CRÍTICO (qualquer falha = experiência destruída ou risco ao usuário)

| Área | O que testar | Tipo de teste |
|------|-------------|--------------|
| Crisis detection | Regex detecta todas as variações de ideação suicida | Unit (regex patterns) |
| SSE streaming | delta/done/error chegam na ordem correta; done sempre fecha stream | Integration |
| Auth JWT | Token expirado retorna 401; refresh renova corretamente | Integration |
| Rate limiter | Mensagem 11 no plano Free retorna 429; contagem reseta à meia-noite | Integration + Redis |
| Subscription gate | plan_code=0 não acessa features de plan_code=1/2 | Integration |

### Tier 2 — ALTA (falha = usuário frustrado, risco de churn)

| Área | O que testar |
|------|-------------|
| RAG retrieval | Contexto relevante é recuperado; threshold 0.45 não traz ruído |
| MoodCheckin flow | Não abre duplicata; registra corretamente no banco |
| Journal save | Persiste; embeddings gerados em background sem bloquear UI |
| RevenueCat webhook | GRANT ativa plan_code correto; REVOKE desativa |
| LGPD delete | Anonimiza dados sem hard delete; todos os serviços respeitam |

### Tier 3 — MÉDIA (falha = bug visível mas não catastrófico)

| Área | O que testar |
|------|-------------|
| HomeScreen checklist | Itens corretos exibidos; subtitle oculta sem mood do dia |
| Navigation state | Nav guard previne telas duplicadas em todos os fluxos |
| SubscriptionScreen | plan_name correto exibido; "Restaurar compras" visível |
| Onboarding order | mood → chat → journal → program |

---

## Critérios de Qualidade

### Cobertura de testes (metas)

| Área | Meta | Status |
|------|------|--------|
| Backend core (auth, chat, subscription) | >80% | ❓ não medido |
| Backend services (rag, journal, mood) | >70% | ❓ não medido |
| Mobile hooks e store | >60% | ❓ não medido |
| Mobile screens críticas (Chat, MoodCheckin) | >50% | ❓ não medido |

### Release criteria — checklist pré-merge em `main`

- [ ] Testes unitários passando (zero falhas)
- [ ] Nenhum endpoint novo sem teste de integration
- [ ] Crisis detection não foi alterado sem validação de regex
- [ ] SSE protocol não foi alterado sem atualização de ambos os lados
- [ ] Dados de saúde novos passaram por compliance-auditor
- [ ] Funcionalidade testada manualmente no dev client (não Expo Go)
- [ ] Rate limiting testado (simular limite atingido)
- [ ] Nenhuma exception em português foi revertida para inglês

---

## Framework de Análise de Risco

Para cada mudança, avaliar:

**1. Blast radius** — quantos usuários/flows afetados se quebrar?  
**2. Reversibilidade** — dá pra reverter rápido em produção?  
**3. Observabilidade** — saberemos que quebrou? Tem log/alert?  
**4. Dados sensíveis** — envolve dados de saúde mental?  

| Blast radius | Reversível | Risco resultante |
|-------------|-----------|-----------------|
| Alto | Sim | MÉDIO — monitorar |
| Alto | Não | CRÍTICO — bloquear merge |
| Baixo | Sim | BAIXO — ok prosseguir |
| Baixo | Não | MÉDIO — testar exaustivamente |

---

## Padrões de Teste por Tipo

### Backend (pytest + httpx)

```python
# Padrão para endpoint com auth
async def test_rate_limit_free_plan(client, free_user_token, redis_client):
    # Enviar 10 mensagens (limite do Free)
    for i in range(10):
        resp = await client.post("/chat", headers=auth(free_user_token), json={...})
        assert resp.status_code == 200
    # 11ª deve retornar 429
    resp = await client.post("/chat", headers=auth(free_user_token), json={...})
    assert resp.status_code == 429
    assert "Limite de mensagens" in resp.json()["detail"]
```

### Mobile (Jest + Testing Library)

```tsx
// Padrão para navegação guard
it('não navega para MoodCheckin se já está aberto', () => {
  const { getByTestId } = render(<MoodHistoryScreen navigation={mockNav} />);
  // mockNav.getState() retorna routes com MoodCheckin
  fireEvent.press(getByTestId('checkin-btn'));
  expect(mockNav.navigate).not.toHaveBeenCalled();
  expect(mockNav.goBack).toHaveBeenCalled();
});
```

---

## Anti-patterns de qualidade no Acollya

| Anti-pattern | Risco | Solução |
|-------------|-------|---------|
| Testar apenas o happy path no chat | Crisis path não coberto | Testar cenários de crise explicitamente |
| Mock do Redis em testes de rate limit | Limite real pode diferir do mockado | Usar Redis real em testes de integração |
| Não testar SSE com conexão lenta | Stream pode cortar | Testar com latência simulada |
| Testes só em Expo Go | Comportamento difere do dev client | Sempre validar no dev client final |
| Ignorar background tasks nos testes | embed_and_store pode silenciosamente falhar | Verificar que não há exceção vazando |
