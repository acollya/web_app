# Knowledge Base & Chat Optimization Schema

## 📋 Visão Geral

Este schema implementa um sistema completo de otimização de chat com IA, incluindo:

1. **Sistema RAG (Retrieval Augmented Generation)** - Busca vetorial de contexto relevante
2. **Sessões Conversacionais** - Continuidade entre conversas
3. **Cache Inteligente** - Reutilização de respostas similares
4. **Monitoramento de Custos** - Tracking de tokens e gastos
5. **Rate Limiting** - Controle de uso por usuário
6. **Knowledge Base** - Base de conhecimento sobre terapia

## 🗄️ Estrutura de Tabelas

### 1. `chat_sessions`
Gerencia sessões de conversa com contexto persistente.

```sql
- id: UUID (PK)
- user_id: UUID (FK -> users)
- title: TEXT (título da sessão)
- summary: TEXT (resumo gerado por IA)
- context_window: INTEGER (nº de mensagens em contexto)
- is_active: BOOLEAN
- created_at, updated_at, last_message_at: TIMESTAMPTZ
```

### 2. `chat_messages` (atualizada)
Mensagens com embeddings vetoriais para busca semântica.

```sql
- id: UUID (PK)
- user_id: UUID (FK -> users)
- session_id: UUID (FK -> chat_sessions)
- role: TEXT ('user' | 'assistant')
- content: TEXT
- embedding: vector(1536) -- Vetor de 1536 dimensões
- tokens_used: INTEGER
- model: TEXT
- metadata: JSONB
- created_at: TIMESTAMPTZ
```

### 3. `message_cache`
Cache de respostas similares para economia de custos.

```sql
- id: UUID (PK)
- query_embedding: vector(1536)
- query_text: TEXT
- response_text: TEXT
- model: TEXT
- tokens_used: INTEGER
- hit_count: INTEGER (contador de reutilizações)
- last_used_at: TIMESTAMPTZ
- created_at: TIMESTAMPTZ
- expires_at: TIMESTAMPTZ (expira em 7 dias)
```

### 4. `token_usage`
Monitoramento detalhado de uso de tokens e custos.

```sql
- id: UUID (PK)
- user_id: UUID (FK -> users)
- session_id: UUID (FK -> chat_sessions)
- operation_type: TEXT ('chat' | 'embedding' | 'reflection' | 'insight')
- model: TEXT
- prompt_tokens: INTEGER
- completion_tokens: INTEGER
- total_tokens: INTEGER
- estimated_cost: DECIMAL(10,6) (custo em USD)
- created_at: TIMESTAMPTZ
```

### 5. `rate_limits`
Controle de taxa de uso por usuário.

```sql
- id: UUID (PK)
- user_id: UUID (FK -> users)
- operation_type: TEXT
- request_count: INTEGER
- window_start: TIMESTAMPTZ
- window_end: TIMESTAMPTZ (janela de 1 hora)
- created_at, updated_at: TIMESTAMPTZ
```

### 6. `knowledge_base`
Base de conhecimento geral sobre terapia.

```sql
- id: UUID (PK)
- category: TEXT ('faq' | 'therapy_technique' | 'coping_strategy' | 'resource')
- title: TEXT
- content: TEXT
- embedding: vector(1536)
- metadata: JSONB
- is_active: BOOLEAN
- created_at, updated_at: TIMESTAMPTZ
```

## 🔍 Funções de Busca

### `search_similar_messages()`
Busca mensagens similares usando embeddings.

```sql
SELECT * FROM search_similar_messages(
  query_embedding := '[0.1, 0.2, ...]'::vector,
  match_threshold := 0.8,
  match_count := 5,
  target_user_id := 'user-uuid'
);
```

**Retorna:**
- `message_id`: UUID da mensagem
- `content`: Conteúdo da mensagem
- `role`: 'user' ou 'assistant'
- `similarity`: Score de similaridade (0-1)
- `created_at`: Data da mensagem

### `search_message_cache()`
Busca no cache de respostas.

```sql
SELECT * FROM search_message_cache(
  query_embedding := '[0.1, 0.2, ...]'::vector,
  match_threshold := 0.95,
  match_count := 1
);
```

**Retorna:**
- `cache_id`: UUID do cache
- `response_text`: Resposta armazenada
- `similarity`: Score de similaridade
- `hit_count`: Número de reutilizações

### `search_knowledge_base()`
Busca na base de conhecimento.

```sql
SELECT * FROM search_knowledge_base(
  query_embedding := '[0.1, 0.2, ...]'::vector,
  match_threshold := 0.7,
  match_count := 3,
  target_category := 'therapy_technique'
);
```

**Retorna:**
- `kb_id`: UUID do item
- `title`: Título
- `content`: Conteúdo
- `category`: Categoria
- `similarity`: Score de similaridade

## 🛠️ Funções Auxiliares

### `reset_daily_message_count()`
Reseta contador de mensagens diárias (executar via cron).

```sql
SELECT reset_daily_message_count();
```

### `cleanup_expired_cache()`
Remove cache expirado (executar via cron).

```sql
SELECT cleanup_expired_cache();
```

## 📊 Views

### `user_usage_stats`
Estatísticas de uso por usuário.

```sql
SELECT * FROM user_usage_stats WHERE user_id = 'user-uuid';
```

**Campos:**
- `user_id`, `email`, `name`, `plan_code`
- `messages_today`: Mensagens enviadas hoje
- `total_sessions`: Total de sessões
- `total_messages`: Total de mensagens
- `tokens_this_month`: Tokens usados no mês
- `cost_this_month`: Custo estimado no mês

### `active_chat_sessions`
Sessões ativas com estatísticas.

```sql
SELECT * FROM active_chat_sessions WHERE user_id = 'user-uuid';
```

## 🚀 Como Aplicar o Schema

### 1. Via Supabase CLI

```bash
# Aplicar migration
supabase db push

# Ou aplicar arquivo específico
psql $DATABASE_URL -f supabase/migrations/20240119_knowledge_base_schema.sql
```

### 2. Via Supabase Dashboard

1. Acesse o projeto no Supabase Dashboard
2. Vá em **SQL Editor**
3. Cole o conteúdo do arquivo `20240119_knowledge_base_schema.sql`
4. Execute

## 📈 Monitoramento de Custos

### Custos Estimados (OpenAI)

**GPT-4o-mini:**
- Input: $0.150 / 1M tokens
- Output: $0.600 / 1M tokens

**text-embedding-3-small:**
- $0.020 / 1M tokens

### Exemplo de Cálculo

```sql
-- Custo total do usuário no mês atual
SELECT 
  user_id,
  SUM(estimated_cost) as total_cost_usd,
  SUM(total_tokens) as total_tokens
FROM token_usage
WHERE created_at >= date_trunc('month', NOW())
GROUP BY user_id;
```

## 🔒 Segurança (RLS)

Todas as tabelas possuem Row Level Security habilitado:

- ✅ Usuários só acessam seus próprios dados
- ✅ Cache e knowledge base são públicos (read-only)
- ✅ Service role tem acesso total

## 🎯 Próximos Passos

Após aplicar este schema:

1. ✅ Implementar Edge Function `chat-ai` otimizada (TypeScript)
2. ✅ Integrar geração de embeddings
3. ✅ Implementar sistema RAG completo
4. ✅ Configurar cron jobs para limpeza
5. ✅ Atualizar frontend para usar sessões

## 📝 Notas Importantes

- **pgvector**: Certifique-se de que a extensão está habilitada
- **Embeddings**: Use `text-embedding-3-small` (1536 dimensões)
- **Cache**: Expira automaticamente em 7 dias
- **Rate Limiting**: Janela de 1 hora por padrão
- **Context Window**: 10 mensagens por padrão (ajustável)

## 🐛 Troubleshooting

### Erro: "extension vector does not exist"

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Erro: "operator does not exist: vector <=> vector"

Certifique-se de que pgvector está instalado corretamente.

### Performance lenta em buscas vetoriais

Ajuste o parâmetro `lists` nos índices IVFFlat:

```sql
CREATE INDEX idx_name ON table USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100); -- Ajuste conforme tamanho da tabela
```

## 📚 Referências

- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [Supabase Vector Search](https://supabase.com/docs/guides/ai/vector-columns)