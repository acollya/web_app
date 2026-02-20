-- ========================================
-- ACOLLYA KNOWLEDGE BASE & CHAT OPTIMIZATION SCHEMA
-- ========================================
-- Este schema implementa:
-- 1. Sistema de embeddings vetoriais (RAG)
-- 2. Sessões conversacionais com contexto
-- 3. Cache inteligente de respostas
-- 4. Monitoramento de tokens e custos
-- 5. Rate limiting por usuário
-- ========================================

-- Habilitar extensão pgvector para embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ========================================
-- 1. CHAT SESSIONS - Gestão de Sessões Conversacionais
-- ========================================
CREATE TABLE IF NOT EXISTS public.chat_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  title TEXT, -- Título gerado automaticamente ou definido pelo usuário
  summary TEXT, -- Resumo da conversa gerado por IA
  context_window INTEGER DEFAULT 10, -- Número de mensagens a manter em contexto
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_message_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para chat_sessions
CREATE INDEX idx_chat_sessions_user_id ON public.chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_is_active ON public.chat_sessions(is_active);
CREATE INDEX idx_chat_sessions_last_message_at ON public.chat_sessions(last_message_at DESC);

-- ========================================
-- 2. CHAT MESSAGES - Mensagens com Embeddings
-- ========================================
-- Atualizar tabela existente para adicionar campos necessários
ALTER TABLE public.chat_messages 
  ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS embedding vector(1536), -- OpenAI text-embedding-3-small gera vetores de 1536 dimensões
  ADD COLUMN IF NOT EXISTS tokens_used INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS model TEXT DEFAULT 'gpt-4o-mini',
  ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Índices para busca vetorial e performance
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON public.chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_embedding ON public.chat_messages USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ========================================
-- 3. MESSAGE CACHE - Cache de Respostas Similares
-- ========================================
CREATE TABLE IF NOT EXISTS public.message_cache (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  query_embedding vector(1536) NOT NULL,
  query_text TEXT NOT NULL,
  response_text TEXT NOT NULL,
  model TEXT NOT NULL,
  tokens_used INTEGER NOT NULL,
  hit_count INTEGER DEFAULT 0, -- Contador de quantas vezes foi reutilizado
  last_used_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days' -- Cache expira em 7 dias
);

-- Índices para cache
CREATE INDEX idx_message_cache_embedding ON public.message_cache USING ivfflat (query_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_message_cache_expires_at ON public.message_cache(expires_at);

-- ========================================
-- 4. TOKEN USAGE - Monitoramento de Custos
-- ========================================
CREATE TABLE IF NOT EXISTS public.token_usage (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  session_id UUID REFERENCES public.chat_sessions(id) ON DELETE SET NULL,
  operation_type TEXT NOT NULL, -- 'chat', 'embedding', 'reflection', 'insight'
  model TEXT NOT NULL,
  prompt_tokens INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  total_tokens INTEGER NOT NULL DEFAULT 0,
  estimated_cost DECIMAL(10, 6) DEFAULT 0, -- Custo estimado em USD
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para token_usage
CREATE INDEX idx_token_usage_user_id ON public.token_usage(user_id);
CREATE INDEX idx_token_usage_session_id ON public.token_usage(session_id);
CREATE INDEX idx_token_usage_created_at ON public.token_usage(created_at DESC);
CREATE INDEX idx_token_usage_operation_type ON public.token_usage(operation_type);

-- ========================================
-- 5. RATE LIMITING - Controle de Taxa de Uso
-- ========================================
CREATE TABLE IF NOT EXISTS public.rate_limits (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  operation_type TEXT NOT NULL, -- 'chat', 'embedding', 'reflection'
  request_count INTEGER DEFAULT 0,
  window_start TIMESTAMPTZ DEFAULT NOW(),
  window_end TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 hour',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, operation_type, window_start)
);

-- Índices para rate_limits
CREATE INDEX idx_rate_limits_user_id ON public.rate_limits(user_id);
CREATE INDEX idx_rate_limits_window_end ON public.rate_limits(window_end);

-- ========================================
-- 6. KNOWLEDGE BASE - Base de Conhecimento Geral
-- ========================================
CREATE TABLE IF NOT EXISTS public.knowledge_base (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  category TEXT NOT NULL, -- 'faq', 'therapy_technique', 'coping_strategy', 'resource'
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(1536) NOT NULL,
  metadata JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para knowledge_base
CREATE INDEX idx_knowledge_base_category ON public.knowledge_base(category);
CREATE INDEX idx_knowledge_base_embedding ON public.knowledge_base USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_knowledge_base_is_active ON public.knowledge_base(is_active);

-- ========================================
-- 7. ATUALIZAR TABELA USERS - Adicionar Campos de Controle
-- ========================================
ALTER TABLE public.users 
  ADD COLUMN IF NOT EXISTS messages_today INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS messages_reset_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 day',
  ADD COLUMN IF NOT EXISTS total_tokens_used INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS total_cost_usd DECIMAL(10, 2) DEFAULT 0;

-- ========================================
-- 8. FUNÇÕES AUXILIARES
-- ========================================

-- Função para buscar mensagens similares usando embeddings
CREATE OR REPLACE FUNCTION search_similar_messages(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.8,
  match_count int DEFAULT 5,
  target_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
  message_id uuid,
  content text,
  role text,
  similarity float,
  created_at timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    cm.id,
    cm.content,
    cm.role,
    1 - (cm.embedding <=> query_embedding) as similarity,
    cm.created_at
  FROM public.chat_messages cm
  WHERE 
    cm.embedding IS NOT NULL
    AND (target_user_id IS NULL OR cm.user_id = target_user_id)
    AND 1 - (cm.embedding <=> query_embedding) > match_threshold
  ORDER BY cm.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Função para buscar no cache de respostas
CREATE OR REPLACE FUNCTION search_message_cache(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.95,
  match_count int DEFAULT 1
)
RETURNS TABLE (
  cache_id uuid,
  response_text text,
  similarity float,
  hit_count integer
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    mc.id,
    mc.response_text,
    1 - (mc.query_embedding <=> query_embedding) as similarity,
    mc.hit_count
  FROM public.message_cache mc
  WHERE 
    mc.expires_at > NOW()
    AND 1 - (mc.query_embedding <=> query_embedding) > match_threshold
  ORDER BY mc.query_embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Função para buscar na base de conhecimento
CREATE OR REPLACE FUNCTION search_knowledge_base(
  query_embedding vector(1536),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 3,
  target_category text DEFAULT NULL
)
RETURNS TABLE (
  kb_id uuid,
  title text,
  content text,
  category text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    kb.id,
    kb.title,
    kb.content,
    kb.category,
    1 - (kb.embedding <=> query_embedding) as similarity
  FROM public.knowledge_base kb
  WHERE 
    kb.is_active = TRUE
    AND (target_category IS NULL OR kb.category = target_category)
    AND 1 - (kb.embedding <=> query_embedding) > match_threshold
  ORDER BY kb.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Função para resetar contador de mensagens diárias
CREATE OR REPLACE FUNCTION reset_daily_message_count()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE public.users
  SET 
    messages_today = 0,
    messages_reset_at = NOW() + INTERVAL '1 day'
  WHERE messages_reset_at <= NOW();
END;
$$;

-- Função para limpar cache expirado
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  DELETE FROM public.message_cache
  WHERE expires_at <= NOW();
END;
$$;

-- Função para atualizar last_message_at em sessões
CREATE OR REPLACE FUNCTION update_session_last_message()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE public.chat_sessions
  SET 
    last_message_at = NEW.created_at,
    updated_at = NEW.created_at
  WHERE id = NEW.session_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para atualizar last_message_at
DROP TRIGGER IF EXISTS trigger_update_session_last_message ON public.chat_messages;
CREATE TRIGGER trigger_update_session_last_message
  AFTER INSERT ON public.chat_messages
  FOR EACH ROW
  WHEN (NEW.session_id IS NOT NULL)
  EXECUTE FUNCTION update_session_last_message();

-- Trigger para updated_at em chat_sessions
DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON public.chat_sessions;
CREATE TRIGGER update_chat_sessions_updated_at 
  BEFORE UPDATE ON public.chat_sessions
  FOR EACH ROW 
  EXECUTE FUNCTION update_updated_at_column();

-- Trigger para updated_at em rate_limits
DROP TRIGGER IF EXISTS update_rate_limits_updated_at ON public.rate_limits;
CREATE TRIGGER update_rate_limits_updated_at 
  BEFORE UPDATE ON public.rate_limits
  FOR EACH ROW 
  EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- 9. ROW LEVEL SECURITY (RLS)
-- ========================================

ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rate_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.knowledge_base ENABLE ROW LEVEL SECURITY;

-- Políticas para chat_sessions
CREATE POLICY "Users can view own chat sessions" ON public.chat_sessions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own chat sessions" ON public.chat_sessions
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own chat sessions" ON public.chat_sessions
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own chat sessions" ON public.chat_sessions
  FOR DELETE USING (auth.uid() = user_id);

-- Políticas para token_usage
CREATE POLICY "Users can view own token usage" ON public.token_usage
  FOR SELECT USING (auth.uid() = user_id);

-- Políticas para rate_limits
CREATE POLICY "Users can view own rate limits" ON public.rate_limits
  FOR SELECT USING (auth.uid() = user_id);

-- Políticas para message_cache (público para leitura, apenas service role pode escrever)
CREATE POLICY "Anyone can read message cache" ON public.message_cache
  FOR SELECT USING (true);

-- Políticas para knowledge_base (público para leitura)
CREATE POLICY "Anyone can read knowledge base" ON public.knowledge_base
  FOR SELECT USING (is_active = true);

-- ========================================
-- 10. ATUALIZAR POLÍTICAS RLS EXISTENTES
-- ========================================

-- Atualizar política de chat_messages para incluir session_id
DROP POLICY IF EXISTS "Users can view own chat messages" ON public.chat_messages;
CREATE POLICY "Users can view own chat messages" ON public.chat_messages
  FOR SELECT USING (
    auth.uid() = user_id 
    OR session_id IN (
      SELECT id FROM public.chat_sessions WHERE user_id = auth.uid()
    )
  );

-- ========================================
-- 11. VIEWS ÚTEIS
-- ========================================

-- View para estatísticas de uso por usuário
CREATE OR REPLACE VIEW user_usage_stats AS
SELECT 
  u.id as user_id,
  u.email,
  u.name,
  u.plan_code,
  u.messages_today,
  u.total_tokens_used,
  u.total_cost_usd,
  COUNT(DISTINCT cs.id) as total_sessions,
  COUNT(DISTINCT cm.id) as total_messages,
  COALESCE(SUM(tu.total_tokens), 0) as tokens_this_month,
  COALESCE(SUM(tu.estimated_cost), 0) as cost_this_month
FROM public.users u
LEFT JOIN public.chat_sessions cs ON cs.user_id = u.id
LEFT JOIN public.chat_messages cm ON cm.user_id = u.id
LEFT JOIN public.token_usage tu ON tu.user_id = u.id 
  AND tu.created_at >= date_trunc('month', NOW())
GROUP BY u.id, u.email, u.name, u.plan_code, u.messages_today, u.total_tokens_used, u.total_cost_usd;

-- View para sessões ativas
CREATE OR REPLACE VIEW active_chat_sessions AS
SELECT 
  cs.*,
  u.name as user_name,
  u.email as user_email,
  COUNT(cm.id) as message_count,
  MAX(cm.created_at) as last_message_time
FROM public.chat_sessions cs
JOIN public.users u ON u.id = cs.user_id
LEFT JOIN public.chat_messages cm ON cm.session_id = cs.id
WHERE cs.is_active = true
GROUP BY cs.id, u.name, u.email;

-- ========================================
-- 12. DADOS INICIAIS (OPCIONAL)
-- ========================================

-- Inserir algumas entradas na base de conhecimento (exemplos)
INSERT INTO public.knowledge_base (category, title, content, embedding, metadata) VALUES
  ('therapy_technique', 'Respiração Diafragmática', 'A respiração diafragmática é uma técnica de relaxamento que ajuda a reduzir ansiedade e estresse. Inspire profundamente pelo nariz por 4 segundos, segure por 4 segundos, e expire lentamente pela boca por 6 segundos.', array_fill(0, ARRAY[1536])::vector, '{"tags": ["ansiedade", "relaxamento", "técnica"]}'),
  ('coping_strategy', 'Técnica 5-4-3-2-1', 'Uma técnica de grounding para ansiedade: identifique 5 coisas que você vê, 4 que você pode tocar, 3 que você ouve, 2 que você cheira, e 1 que você pode saborear.', array_fill(0, ARRAY[1536])::vector, '{"tags": ["ansiedade", "grounding", "mindfulness"]}'),
  ('faq', 'Quando procurar ajuda profissional', 'É importante procurar um profissional de saúde mental quando: sintomas persistem por mais de 2 semanas, interferem no trabalho ou relacionamentos, incluem pensamentos suicidas, ou causam sofrimento significativo.', array_fill(0, ARRAY[1536])::vector, '{"tags": ["ajuda", "profissional", "emergência"]}')
ON CONFLICT DO NOTHING;

-- ========================================
-- 13. COMENTÁRIOS PARA DOCUMENTAÇÃO
-- ========================================

COMMENT ON TABLE public.chat_sessions IS 'Sessões de chat com contexto conversacional persistente';
COMMENT ON TABLE public.message_cache IS 'Cache de respostas similares para otimização de custos';
COMMENT ON TABLE public.token_usage IS 'Monitoramento detalhado de uso de tokens e custos';
COMMENT ON TABLE public.rate_limits IS 'Controle de taxa de uso por usuário e operação';
COMMENT ON TABLE public.knowledge_base IS 'Base de conhecimento geral sobre terapia e saúde mental';

COMMENT ON COLUMN public.chat_messages.embedding IS 'Vetor de embedding (1536 dimensões) gerado por text-embedding-3-small';
COMMENT ON COLUMN public.chat_messages.tokens_used IS 'Número de tokens usados nesta mensagem';
COMMENT ON COLUMN public.chat_sessions.context_window IS 'Número de mensagens anteriores a incluir no contexto';

-- ========================================
-- FIM DO SCHEMA
-- ========================================