---
name: accessibility-tester
description: "React Native + WCAG 2.1 accessibility review. Checks accessibilityRole, accessibilityLabel, touch targets (44px), contrast ratios, screen reader compatibility, keyboard nav, and LGPD-sensitive component handling. Specific to Acollya mobile (Expo SDK 55, React Native 0.83.4)."
---
# Accessibility Tester — Acollya Mobile

Guia de revisão de acessibilidade para o app Acollya (React Native + Expo SDK 55). Foca em WCAG 2.1 Level AA aplicado ao contexto de saúde mental — usuários em crise ou sob estresse cognitivo elevado.

## Quando aplicar

Use este skill ao:
- Criar ou revisar telas em `acollya-mobile/src/screens/`
- Criar ou modificar componentes em `acollya-mobile/src/components/`
- Implementar modais, banners ou alertas
- Antes de considerar qualquer tela completa (pré-merge)

---

## Checklist de Revisão (aplique em ordem)

### 1. Touch Targets (CRÍTICO)
- Mínimo **44×44dp** para todos os elementos tocáveis
- Verificar: `TouchableOpacity`, `Pressable`, `TouchableHighlight`
- React Native tip: usar `hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}` quando o elemento visual for menor

```tsx
// ✅ Correto
<Pressable style={styles.btn} hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}>

// ❌ Errado — elemento menor que 44dp sem hitSlop
<TouchableOpacity style={{ width: 24, height: 24 }}>
```

### 2. accessibilityRole (CRÍTICO)
Todo elemento interativo precisa de role explícita:

| Componente | Role correta |
|------------|-------------|
| Botão de ação | `button` |
| Link de navegação | `link` |
| Campo de texto | `text` (automático com TextInput) |
| Imagem decorativa | `none` ou `image` com `accessibilityLabel` |
| Título de seção | `header` |
| Alerta/banner | `alert` |
| Switch/toggle | `switch` |
| Checkbox | `checkbox` |

### 3. accessibilityLabel (CRÍTICO)
- Ícones sem texto: **obrigatório** ter `accessibilityLabel`
- Botões com só ícone (ex: mic, send, heart): descrever a ação, não o ícone

```tsx
// ✅ Correto
<Pressable accessibilityRole="button" accessibilityLabel="Enviar mensagem">
  <Icon name="send" />
</Pressable>

// ❌ Errado — sem label, screen reader lê "image" ou nada
<Pressable>
  <Icon name="send" />
</Pressable>
```

### 4. Contraste de Cor (ALTA)
Mínimo WCAG 2.1 AA:
- Texto normal: **4.5:1**
- Texto grande (18sp+) ou bold (14sp+): **3:1**
- Elementos de UI / bordas: **3:1**

Referência de tokens Acollya:
| Uso | Cor | Fundo | Status |
|-----|-----|-------|--------|
| Texto principal | `Colors.text` (#2C2A28) | `Colors.background` (#F7F5F2) | ✅ passa |
| Texto secundário | `Colors.textSecondary` | `Colors.background` | verificar |
| Texto muted | `Colors.textMuted` | `Colors.background` | ⚠️ verificar sempre |
| Texto em botão primário | branco | `Colors.lavandaProfunda` | ✅ passa |

### 5. accessibilityState (MÉDIA)
Estados dinâmicos devem ser comunicados:

```tsx
// ✅ Loading, disabled, selected
<Pressable
  accessibilityState={{ disabled: isLoading, busy: isLoading }}
  accessibilityLabel={isLoading ? "Enviando..." : "Enviar"}
>

// ✅ Toggle states
<Pressable
  accessibilityRole="switch"
  accessibilityState={{ checked: isEnabled }}
>
```

### 6. accessibilityHint (MÉDIA)
Para ações não óbvias, adicionar hint:

```tsx
<Pressable
  accessibilityRole="button"
  accessibilityLabel="Gravar áudio"
  accessibilityHint="Toque e segure para gravar uma mensagem de voz"
>
```

### 7. Ordem de foco (MÉDIA)
- Verificar se a ordem de leitura do TalkBack/VoiceOver faz sentido
- Modais devem capturar o foco: usar `accessible={true}` no container + `importantForAccessibility="yes"`
- Ao fechar modal, retornar foco ao elemento trigger

### 8. Textos dinâmicos / anúncios (MÉDIA)
Para conteúdo que muda sem navegação:

```tsx
// CrisisBanner — exemplo de uso correto
<View accessibilityRole="alert" accessibilityLiveRegion="polite">
  <Text>Recurso de crise disponível</Text>
</View>
```

### 9. Reduced Motion (BAIXA)
Verificar animações quando `useReducedMotion()` retorna `true`:

```tsx
import { useReducedMotion } from 'react-native-reanimated';

const reducedMotion = useReducedMotion();
const animConfig = reducedMotion
  ? { duration: 0 }
  : { duration: 300, easing: Easing.ease };
```

### 10. Componentes críticos do Acollya

**CrisisBanner** (`components/CrisisBanner.tsx`):
- Deve ter `accessibilityRole="alert"`
- Botão de CVV: `accessibilityLabel="Ligar para o CVV - Centro de Valorização da Vida"`
- `accessibilityLiveRegion="assertive"` (urgente — interrompe leitura atual)

**VoiceInputButton** (`components/VoiceInputButton.tsx`):
- Deve comunicar estado: "Toque para gravar" → "Gravando..." → "Toque para parar"
- `accessibilityState={{ busy: isRecording }}`

**Campos de texto no onboarding:**
- Sempre com `accessibilityLabel` descritivo
- `returnKeyType` adequado ao fluxo

---

## Erros comuns no Acollya

| Erro | Onde procurar | Fix |
|------|--------------|-----|
| Ícones sem label | Componentes com `<Icon>` sem texto | Adicionar `accessibilityLabel` ao Pressable pai |
| Botão de enviar sem descrição | ChatScreen send button | `accessibilityLabel="Enviar mensagem"` |
| Heart icon sem role | HomeScreen | `accessibilityRole="image"` ou `"none"` se decorativo |
| Modal sem captura de foco | SubscriptionScreen planos | Adicionar `accessible` no container do modal |
| Textos muted com baixo contraste | Timestamps, hints | Verificar ratio com `Colors.textMuted` |

---

## Referência PT-BR para accessibilityLabel

Usar PT-BR em todas as labels (usuários brasileiros usam TalkBack/VoiceOver em PT-BR):

| Ação | Label PT-BR |
|------|------------|
| Voltar | "Voltar" |
| Fechar | "Fechar" |
| Enviar mensagem | "Enviar mensagem" |
| Gravar áudio | "Gravar mensagem de voz" |
| Mais opções | "Mais opções" |
| Curtir / favoritar | "Favoritar" |
| Excluir | "Excluir" |
| Editar | "Editar" |
| Compartilhar | "Compartilhar" |
