# Pre-Launch Legal Checklist — LGPD

_Agentes: ao endereçar um item, marcar como ✅ e anotar o arquivo/PR._
_Compliance-auditor e legal-advisor devem verificar este arquivo antes de qualquer release._
_Última auditoria completa: 2026-08-29 (compliance-auditor) — achados incorporados abaixo._

**Status: 8 de 15 itens originais completos + 9 itens novos da auditoria**

---

## Checklist original

| # | Item | Status | Notas |
|---|------|--------|-------|
| 1 | ML data retention inconsistency | ✅ **2026-08-29** | `delete_me` agora HARD-DELETA chat/diário/humor/persona/sessões (conteúdo + embeddings); zero retenção p/ ML; MyDataScreen alinhada. ADR-011 |
| 2 | Consentimento separado p/ dado de saúde (Art. 11) | ✅ **2026-08-29** | Checkbox destacado no modal + `health_data_consent` no User + **gate server-side `get_consented_user`** (403 em chat/mood/journal/media até consentir) |
| 3 | `terms_version` no User | ✅ **2026-08-29** | Migration 024 + `settings.terms_version` ("2026-08-28") gravada no consents |
| 4 | Privacy Policy URL publicada | ❌ **KADU** | URLs definidas: `acollya.com.br/privacidade` (constants/legal.ts) — falta publicar |
| 5 | ToS URL publicado | ❌ **KADU** | `acollya.com.br/termos` — falta publicar |
| 6 | DPA com Anthropic | ❌ **KADU** | Zero-retention/no-training — o modal JÁ afirma isso; precisa respaldo contratual |
| 7 | DPA com OpenAI | ❌ **KADU** | Idem |
| 8 | Verificação de idade | ✅ **2026-08-29** | birth_date no modal + validação server-side. **DECISÃO: mínimo 18 anos** (auditoria C2: 13-17 exigiria consentimento parental Art. 14; reduzir só com parecer jurídico + fluxo parental) |
| 9 | Crisis audit log | ✅ | — |
| 10 | Privacy Nutrition Labels (Apple) | ❌ **KADU** | App Store Connect |
| 11 | Data Safety Form (Google) | ❌ **KADU** | Play Console |
| 12 | Audit termos proibidos | ✅ **2026-08-29** | Prompts corrigidos (chat/mood/journal não se posicionam mais como "terapeuta/especialista clínica" — viraram "assistente que utiliza técnicas..."); UI já estava limpa |
| 13 | CNPJ/razão social no app | 🟡 estrutura ✅ | Tela Sobre exibe empresa + links legais; **KADU: preencher dados reais em `constants/legal.ts`** |
| 14 | AWS sa-east-1 | ✅ | — |
| 15 | Endpoint de exportação (Art. 18) | ✅ **2026-08-29** | `GET /users/me/export` (rate 3/h) — perfil, humor, diário, conversas, persona, progresso, agendamentos, **crise e assinaturas** (acesso completo); botão no MyDataScreen |

## Itens novos (auditoria 2026-08-29)

| # | Item | Prioridade | Status |
|---|------|-----------|--------|
| 16 | S3 Lifecycle no prefixo `tts/` (áudios TTS persistem fora do erasure) | ALTA | ❌ infra (1 regra no bucket) |
| 17 | Transferência internacional Art. 33 — texto no consentimento | ALTA | ✅ modal menciona EUA + garantias; ❌ respaldo contratual = DPAs (#6/#7) |
| 18 | Prazo de retenção + expurgo de `crisis_events` | ALTA | ❌ definição jurídica (base corrigida p/ Art. 16 I) |
| 19 | Revogação de consentimento sem deletar conta (Art. 8 §5) | MÉDIA | ❌ roadmap |
| 20 | Fluxo de re-aceite quando terms_version mudar | MÉDIA | ❌ roadmap |
| 21 | TTL/retention nos log groups (CloudWatch) + garantir zero conteúdo em logs | MÉDIA | ❌ infra |
| 22 | RIPD (Art. 38) + RoPA (Art. 37) | MÉDIA | ❌ documento (legal-advisor pode rascunhar) |
| 23 | Export assíncrono (Share trunca JSON grande) | MÉDIA | ❌ roadmap |
| 24 | Encarregado/DPO nomeado publicamente (Art. 41) | BAIXA | ❌ **KADU** |
| 25 | Plano de resposta a incidente / notificação ANPD (Art. 48) | BAIXA | ❌ documento |

---

## Arquitetura de consentimento (implementada 2026-08-29)

```
SSO (Google/Apple) → conta criada com terms_accepted=FALSE, sem birth_date
      ↓ (token válido, MAS…)
get_consented_user → 403 em TODAS as rotas sensíveis (chat, mood, journal, media)
      ↓
TermsAcceptanceModal: termos + privacidade + CONSENTIMENTO SAÚDE destacado
  (Art. 11, menção a transferência internacional) + nascimento (18+, validado
  client E server) → POST /users/me/consents grava tudo + terms_version
      ↓
Menor de idade → conta descartada (deleteAccount + logout)
```

## Termos proibidos (referência rápida)

Nunca usar em UI copy, push, e-mails ou system prompts:
`psicoterapia` · `diagnóstico/diagnosticar` · `tratamento/tratar` · `clínico/clínica`
· `terapia por IA` · `alternativa ao psicólogo/à terapia` · `prescrição/medicação/remédio`
· **posicionar a IA como "terapeuta" ou "especialista em Terapia X"** (corrigido nos prompts)

Permitido: encaminhamento a profissional real ("busque um psicólogo", "terapia de casal
como caminho principal") e disclaimers negativos ("não substitui diagnóstico").

**Substitutos seguros:** apoio emocional ✅ · reflexão guiada ✅ · acompanhamento de humor ✅
· "utiliza técnicas cognitivo-comportamentais" ✅ (em vez de "especializada em TCC")
