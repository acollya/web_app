# Guia de Componentes UI - Acollya PWA

Componentes UI para melhorar a experiência do usuário com indicadores de limite, loading states e toasts.

## Componentes Criados

### 1. MessageLimitIndicator

**Arquivo:** `/src/components/MessageLimitIndicator.tsx`

**Propósito:** Mostrar mensagens restantes para usuários free e incentivar upgrade.

**Props:**
```typescript
interface MessageLimitIndicatorProps {
  messagesRemaining: number | null; // null = premium (ilimitado)
  totalMessages?: number; // padrão: 10
  className?: string;
}
```

**Recursos:**
- ✅ Badge com contagem de mensagens
- ✅ Barra de progresso visual
- ✅ Alerta quando restam ≤3 mensagens
- ✅ Botão "Upgrade to Premium"
- ✅ Indicador "Premium" para usuários pagantes
- ✅ Animação de pulse quando limite baixo

**Uso:**
```tsx
import { MessageLimitIndicator } from '@/components/MessageLimitIndicator';

// Usuário free
<MessageLimitIndicator messagesRemaining={7} />

// Usuário premium
<MessageLimitIndicator messagesRemaining={null} />
```

---

### 2. AILoadingState

**Arquivo:** `/src/components/AILoadingState.tsx`

**Propósito:** Indicador de loading durante chamadas à IA.

**Componentes:**
1. `AILoadingState` - Loading genérico
2. `AITypingIndicator` - Indicador de digitação para chat

**Props AILoadingState:**
```typescript
interface AILoadingStateProps {
  message?: string; // padrão: "IA está pensando"
  className?: string;
}
```

**Recursos:**
- ✅ Ícone Sparkles animado
- ✅ Spinner rotativo
- ✅ Pontos pulsantes
- ✅ Mensagem customizável
- ✅ Design consistente com tema

**Uso:**
```tsx
import { AILoadingState, AITypingIndicator } from '@/components/AILoadingState';

// Loading genérico
<AILoadingState message="Gerando reflexão..." />

// Indicador de digitação (para chat)
<AITypingIndicator />
```

---

### 3. RateLimitToast

**Arquivo:** `/src/components/RateLimitToast.tsx`

**Propósito:** Toast de notificação quando limite de mensagens é atingido.

**Componentes:**
1. `RateLimitToast` - Componente visual
2. `useRateLimitToast` - Hook para integração com shadcn toast

**Props RateLimitToast:**
```typescript
interface RateLimitToastProps {
  onUpgrade?: () => void; // callback customizado
}
```

**Recursos:**
- ✅ Ícone de alerta
- ✅ Tempo até reset (meia-noite)
- ✅ Botão "Upgrade to Premium"
- ✅ Informação de preço
- ✅ Design destacado

**Uso com shadcn toast:**
```tsx
import { useToast } from '@/hooks/use-toast';
import { useRateLimitToast } from '@/components/RateLimitToast';

function MyComponent() {
  const { toast } = useToast();
  const { showRateLimitToast } = useRateLimitToast();

  const handleError = (error: Error) => {
    if (error.message.includes('Limite de mensagens')) {
      showRateLimitToast(toast);
    }
  };
}
```

**Uso direto:**
```tsx
import { RateLimitToast } from '@/components/RateLimitToast';

<RateLimitToast onUpgrade={() => navigate('/subscription')} />
```

---

## Integração nos Componentes Existentes

### Chat.tsx

**Localização:** `/src/pages/Chat.tsx` (ou onde estiver o componente de chat)

**Integrações necessárias:**

1. **Adicionar MessageLimitIndicator no topo:**
```tsx
import { MessageLimitIndicator } from '@/components/MessageLimitIndicator';
import { chatService } from '@/services/chatService';

function Chat() {
  const [messagesRemaining, setMessagesRemaining] = useState<number | null>(
    chatService.getMessagesRemaining()
  );

  return (
    <div>
      <MessageLimitIndicator messagesRemaining={messagesRemaining} />
      {/* resto do chat */}
    </div>
  );
}
```

2. **Adicionar AITypingIndicator durante resposta:**
```tsx
import { AITypingIndicator } from '@/components/AILoadingState';

function Chat() {
  const [isAITyping, setIsAITyping] = useState(false);

  const sendMessage = async (message: string) => {
    setIsAITyping(true);
    try {
      const response = await chatService.sendMessage({ message, sessionId });
      // processar resposta
    } catch (error) {
      // tratar erro
    } finally {
      setIsAITyping(false);
    }
  };

  return (
    <div>
      {messages.map(msg => <Message key={msg.id} {...msg} />)}
      {isAITyping && <AITypingIndicator />}
    </div>
  );
}
```

3. **Mostrar RateLimitToast quando limite atingido:**
```tsx
import { useToast } from '@/hooks/use-toast';
import { useRateLimitToast } from '@/components/RateLimitToast';

function Chat() {
  const { toast } = useToast();
  const { showRateLimitToast } = useRateLimitToast();

  const sendMessage = async (message: string) => {
    try {
      const response = await chatService.sendMessage({ message, sessionId });
      setMessagesRemaining(chatService.getMessagesRemaining());
    } catch (error: any) {
      if (error.message.includes('Limite de mensagens')) {
        showRateLimitToast(toast);
      } else {
        toast({
          title: 'Erro',
          description: error.message,
          variant: 'destructive',
        });
      }
    }
  };
}
```

---

### Journal.tsx

**Localização:** `/src/pages/Journal.tsx` (ou onde estiver o componente de diário)

**Integrações necessárias:**

1. **Adicionar AILoadingState durante geração de reflexão:**
```tsx
import { AILoadingState } from '@/components/AILoadingState';
import { journalService } from '@/services/journalService';

function Journal() {
  const [isGeneratingReflection, setIsGeneratingReflection] = useState(false);

  const generateReflection = async (entryId: string, content: string) => {
    setIsGeneratingReflection(true);
    try {
      const reflection = await journalService.getReflection(entryId, content);
      // mostrar reflexão
    } catch (error: any) {
      toast({
        title: 'Erro',
        description: error.message,
        variant: 'destructive',
      });
    } finally {
      setIsGeneratingReflection(false);
    }
  };

  return (
    <div>
      {isGeneratingReflection && (
        <AILoadingState message="Gerando reflexão sobre sua entrada..." />
      )}
      {/* resto do journal */}
    </div>
  );
}
```

2. **Mostrar toasts de erro:**
```tsx
import { useToast } from '@/hooks/use-toast';

function Journal() {
  const { toast } = useToast();

  const generateReflection = async (entryId: string, content: string) => {
    try {
      const reflection = await journalService.getReflection(entryId, content);
      toast({
        title: 'Reflexão Gerada',
        description: 'Sua reflexão foi gerada com sucesso!',
      });
    } catch (error: any) {
      toast({
        title: 'Erro ao Gerar Reflexão',
        description: error.message,
        variant: 'destructive',
      });
    }
  };
}
```

---

## Estilos e Temas

Todos os componentes usam:
- ✅ shadcn-ui components
- ✅ Tailwind CSS
- ✅ Lucide React icons
- ✅ Suporte a dark mode
- ✅ Animações suaves
- ✅ Design responsivo

## Acessibilidade

- ✅ Cores com contraste adequado
- ✅ Textos legíveis
- ✅ Animações respeitam `prefers-reduced-motion`
- ✅ Elementos interativos com foco visível

## Customização

### Cores do Progresso

```tsx
<MessageLimitIndicator
  messagesRemaining={3}
  className="custom-class"
/>
```

### Mensagem de Loading

```tsx
<AILoadingState message="Processando sua solicitação..." />
```

### Callback de Upgrade

```tsx
<RateLimitToast
  onUpgrade={() => {
    // lógica customizada
    analytics.track('upgrade_clicked');
    navigate('/subscription');
  }}
/>
```

## Testes

### Testar MessageLimitIndicator

```tsx
// Usuário com 3 mensagens restantes (alerta)
<MessageLimitIndicator messagesRemaining={3} />

// Usuário com 10 mensagens restantes (normal)
<MessageLimitIndicator messagesRemaining={10} />

// Usuário premium
<MessageLimitIndicator messagesRemaining={null} />
```

### Testar AILoadingState

```tsx
// Simular loading
const [loading, setLoading] = useState(false);

<button onClick={() => setLoading(!loading)}>
  Toggle Loading
</button>

{loading && <AILoadingState />}
```

### Testar RateLimitToast

```tsx
// Simular erro de limite
const simulateRateLimit = () => {
  showRateLimitToast(toast);
};

<button onClick={simulateRateLimit}>
  Simular Limite
</button>
```

---

## Checklist de Integração

- [ ] MessageLimitIndicator adicionado ao Chat
- [ ] AITypingIndicator adicionado ao Chat
- [ ] RateLimitToast integrado com tratamento de erros do Chat
- [ ] AILoadingState adicionado ao Journal
- [ ] Toasts de erro adicionados ao Journal
- [ ] Testado em modo demo e produção
- [ ] Testado em dark mode
- [ ] Testado em mobile e desktop
- [ ] Animações funcionando corretamente
- [ ] Navegação para /subscription funcionando

---

## Próximos Passos

1. ✅ Integrar componentes nos arquivos Chat.tsx e Journal.tsx
2. ✅ Testar fluxo completo de limite de mensagens
3. ✅ Testar loading states durante chamadas à IA
4. ✅ Verificar analytics de cliques em "Upgrade"
5. ✅ Ajustar estilos se necessário