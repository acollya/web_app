# Pre-Launch Legal Checklist — LGPD

_Agentes: ao endereçar um item, marcar como ✅ e anotar o arquivo/PR._  
_Compliance-auditor e legal-advisor devem verificar este arquivo antes de qualquer release._

**Status atual: 2 de 15 itens completos**

---

| # | Item | Status | Arquivo / Ação | Prioridade |
|---|------|--------|----------------|-----------|
| 1 | ML data retention inconsistency em `user_service.py` — garantir que dados de saúde mental não sejam retidos para fine-tuning sem consentimento explícito | ❌ Aberto | `services/user_service.py` | CRÍTICA |
| 2 | Consentimento separado para dado de saúde (categoria especial LGPD Art. 11) | ❌ Aberto | Fluxo de onboarding | CRÍTICA |
| 3 | Campo `terms_version` no modelo User — rastrear versão dos termos aceitos | ❌ Aberto | `models/user.py` + migration | Alta |
| 4 | Privacy Policy URL publicada e acessível in-app | ❌ Aberto | URL externa + Settings screen | Alta |
| 5 | Terms of Service URL publicado e acessível in-app | ❌ Aberto | URL externa + Settings screen | Alta |
| 6 | Data Processing Agreement (DPA) com Anthropic assinado | ❌ Aberto | Contrato externo | Alta |
| 7 | Data Processing Agreement (DPA) com OpenAI assinado | ❌ Aberto | Contrato externo | Alta |
| 8 | Verificação de idade mínima (13+ anos) no onboarding | ❌ Aberto | Tela de onboarding | Alta |
| 9 | Crisis audit log implementado | ✅ Completo | — | CRÍTICA |
| 10 | App Store Privacy Nutrition Labels preenchidos | ❌ Aberto | App Store Connect | Alta |
| 11 | Play Store Data Safety Form preenchido | ❌ Aberto | Play Console | Alta |
| 12 | Audit de termos proibidos no copy e prompts do sistema ("psicoterapia", "diagnóstico", "tratamento", "clínico", "terapia por IA", "alternativa ao psicólogo") | ❌ Aberto | System prompts + UI strings | Alta |
| 13 | CNPJ / razão social exibidos na tela "Sobre" ou footer | ❌ Aberto | Tela de Settings/Sobre | Média |
| 14 | AWS em `sa-east-1` (São Paulo) para dados de saúde — confirma dado em território nacional | ✅ Completo | Infra CDK | Alta |
| 15 | Endpoint de exportação de dados do usuário (LGPD Art. 18 — direito de portabilidade) | ❌ Aberto | Novo endpoint `GET /users/me/export` | Alta |

---

## Termos proibidos (referência rápida)

Nunca usar em UI copy, push notifications, e-mails ou system prompts:

- `psicoterapia` / `psicoterapeuta`
- `diagnóstico` / `diagnosticar`
- `tratamento` / `tratar`
- `clínico` / `clínica`
- `terapia por IA`
- `alternativa ao psicólogo`
- `alternativa à terapia`
- `prescrição` / `medicação` / `remédio`

**Substitutos seguros:**
- "apoio emocional" ✅
- "reflexão guiada" ✅
- "acompanhamento de humor" ✅
- "conversa de bem-estar" ✅
- "insights personalizados" ✅

---

## Riscos legais mais críticos (para referência)

1. **Fine-tuning sem consentimento** — se dados de usuário forem usados para treinar modelos sem consentimento explícito e base legal clara (LGPD Art. 7/11)
2. **Responsabilidade civil em crises** — sem audit log rastreável de intervenções em crise (item 9 já resolvido)
3. **Transferência internacional** — dados de saúde enviados à Anthropic/OpenAI (US) sem cláusulas contratuais adequadas (DPAs — itens 6 e 7)
4. **Rejeição App Store** — Privacy Labels incompletos (item 10)
5. **Posicionamento CFP** — questionamento de "psicoterapia por IA" pelo Conselho Federal de Psicologia (mitigado pelos termos proibidos acima)
