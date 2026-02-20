import { serve } from 'https://deno.land/std@0.168.0/http/server.ts';
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

// ========================================
// INTERFACES
// ========================================

interface ChatRequest {
  message: string;
  session_id?: string;
  user_id: string;
}

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  created_at: string;
  similarity?: number;
}

interface KBEntry {
  kb_id: string;
  title: string;
  content: string;
  category: string;
  similarity: number;
}

interface CachedResponse {
  cache_id: string;
  response_text: string;
  similarity: number;
  hit_count: number;
}

interface TokenUsageData {
  user_id: string;
  session_id: string;
  operation_type: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost: number;
}

// ========================================
// CONFIGURAÇÕES
// ========================================

const OPENAI_API_KEY = Deno.env.get('OPENAI_CHAT_API_KEY');
const SUPABASE_URL = Deno.env.get('SUPABASE_URL');
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

const CONFIG = {
  model: 'gpt-4o-mini',
  embeddingModel: 'text-embedding-3-small',
  temperature: 0.7,
  maxTokens: 800,
  contextWindow: 10,
  cacheThreshold: 0.95,
  similarityThreshold: 0.8,
  knowledgeBaseThreshold: 0.7,
  maxMessagesPerDay: 50, // Limite para usuários free
  // Custos por 1M tokens (USD)
  costs: {
    'gpt-4o-mini': { input: 0.15, output: 0.60 },
    'text-embedding-3-small': 0.02,
  },
};

// System Prompt da Acollya
const SYSTEM_PROMPT = `Você é a Acollya, uma psicóloga virtual especializada em Terapia Cognitivo-Comportamental (TCC) e Terapia Relacional Sistêmica. Seu objetivo é oferecer suporte emocional, ajudar usuários a compreenderem seus pensamentos e emoções, e fornecer estratégias práticas de enfrentamento.

**Sua Personalidade:**
- Empática, acolhedora e não-julgadora
- Profissional, mas com tom caloroso e humano
- Adaptada ao público brasileiro e latino-americano
- Usa linguagem acessível, evitando jargões técnicos excessivos

**Suas Responsabilidades:**
1. **Escuta Ativa:** Demonstre compreensão genuína das preocupações do usuário
2. **Validação Emocional:** Reconheça e valide os sentimentos expressos
3. **Orientação Terapêutica:** Ofereça insights baseados em TCC e abordagens sistêmicas
4. **Estratégias Práticas:** Sugira técnicas de enfrentamento aplicáveis no dia a dia
5. **Educação Psicológica:** Explique conceitos de forma clara quando relevante
6. **Encaminhamento:** Recomende ajuda profissional presencial quando necessário

**Diretrizes Importantes:**
- Nunca diagnostique condições médicas ou psiquiátricas
- Não prescreva medicamentos ou tratamentos médicos
- Em casos de risco iminente (suicídio, violência), oriente a buscar ajuda emergencial imediata
- Respeite limites éticos da psicologia online
- Mantenha confidencialidade e empatia em todas as interações
- Adapte sua linguagem ao nível de compreensão do usuário
- Faça perguntas abertas para aprofundar a compreensão
- Celebre progressos e pequenas vitórias

**Técnicas que você pode sugerir:**
- Respiração diafragmática e relaxamento
- Reestruturação cognitiva (identificar e questionar pensamentos automáticos)
- Técnicas de grounding (5-4-3-2-1)
- Registro de pensamentos e emoções
- Estabelecimento de metas realistas
- Mindfulness e atenção plena
- Resolução de problemas estruturada

**Quando encaminhar para profissional:**
- Sintomas graves ou persistentes (>2 semanas)
- Pensamentos suicidas ou autodestrutivos
- Abuso de substâncias
- Trauma severo não resolvido
- Necessidade de diagnóstico formal ou medicação
- Situações que requerem intervenção presencial

Lembre-se: você é um apoio complementar, não substitui terapia presencial. Seu papel é oferecer suporte, orientação e ferramentas práticas dentro dos limites éticos da psicologia online.`;

// ========================================
// FUNÇÕES AUXILIARES
// ========================================

async function generateEmbedding(text: string): Promise<number[]> {
  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: CONFIG.embeddingModel,
      input: text,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI Embedding API error: ${error}`);
  }

  const data = await response.json();
  return data.data[0].embedding;
}

async function searchCache(
  supabase: any,
  embedding: number[],
  threshold: number = CONFIG.cacheThreshold
): Promise<CachedResponse | null> {
  const { data, error } = await supabase.rpc('search_message_cache', {
    query_embedding: embedding,
    match_threshold: threshold,
    match_count: 1,
  });

  if (error) {
    console.error('Error searching cache:', error);
    return null;
  }

  if (data && data.length > 0) {
    // Atualizar hit_count e last_used_at
    await supabase
      .from('message_cache')
      .update({
        hit_count: data[0].hit_count + 1,
        last_used_at: new Date().toISOString(),
      })
      .eq('id', data[0].cache_id);

    return data[0];
  }

  return null;
}

async function searchSimilarMessages(
  supabase: any,
  embedding: number[],
  userId: string,
  threshold: number = CONFIG.similarityThreshold
): Promise<Message[]> {
  const { data, error } = await supabase.rpc('search_similar_messages', {
    query_embedding: embedding,
    match_threshold: threshold,
    match_count: 5,
    target_user_id: userId,
  });

  if (error) {
    console.error('Error searching similar messages:', error);
    return [];
  }

  return data || [];
}

async function searchKnowledgeBase(
  supabase: any,
  embedding: number[],
  threshold: number = CONFIG.knowledgeBaseThreshold
): Promise<KBEntry[]> {
  const { data, error } = await supabase.rpc('search_knowledge_base', {
    query_embedding: embedding,
    match_threshold: threshold,
    match_count: 3,
  });

  if (error) {
    console.error('Error searching knowledge base:', error);
    return [];
  }

  return data || [];
}

async function getSessionMessages(
  supabase: any,
  sessionId: string,
  limit: number = CONFIG.contextWindow
): Promise<Message[]> {
  const { data, error } = await supabase
    .from('chat_messages')
    .select('id, content, role, created_at')
    .eq('session_id', sessionId)
    .order('created_at', { ascending: false })
    .limit(limit);

  if (error) {
    console.error('Error fetching session messages:', error);
    return [];
  }

  return (data || []).reverse();
}

function buildContext(
  sessionMessages: Message[],
  similarMessages: Message[],
  kbEntries: KBEntry[]
): string {
  let context = '';

  // Adicionar mensagens da sessão atual
  if (sessionMessages.length > 0) {
    context += '### Histórico da Conversa Atual:\n';
    sessionMessages.forEach((msg) => {
      context += `${msg.role === 'user' ? 'Usuário' : 'Acollya'}: ${msg.content}\n`;
    });
    context += '\n';
  }

  // Adicionar mensagens similares de conversas anteriores
  if (similarMessages.length > 0) {
    context += '### Contexto de Conversas Anteriores (Relevantes):\n';
    similarMessages.forEach((msg) => {
      context += `- ${msg.content} (similaridade: ${(msg.similarity! * 100).toFixed(1)}%)\n`;
    });
    context += '\n';
  }

  // Adicionar conhecimento da base
  if (kbEntries.length > 0) {
    context += '### Conhecimento Relevante da Base:\n';
    kbEntries.forEach((entry) => {
      context += `**${entry.title}** (${entry.category}):\n${entry.content}\n\n`;
    });
  }

  return context;
}

async function checkRateLimit(supabase: any, userId: string): Promise<{ allowed: boolean; remaining: number }> {
  // Verificar e resetar contador diário se necessário
  await supabase.rpc('reset_daily_message_count');

  // Buscar usuário
  const { data: user, error } = await supabase
    .from('users')
    .select('messages_today, plan_code')
    .eq('id', userId)
    .single();

  if (error || !user) {
    console.error('Error fetching user:', error);
    return { allowed: true, remaining: -1 }; // Permitir em caso de erro
  }

  // Verificar limite (apenas para usuários free)
  if (user.plan_code === 'free' || !user.plan_code) {
    const remaining = CONFIG.maxMessagesPerDay - user.messages_today;
    if (remaining <= 0) {
      return { allowed: false, remaining: 0 };
    }
    return { allowed: true, remaining };
  }

  // Usuários pagos não têm limite
  return { allowed: true, remaining: -1 };
}

async function incrementMessageCount(supabase: any, userId: string): Promise<void> {
  await supabase.rpc('increment', {
    table_name: 'users',
    row_id: userId,
    column_name: 'messages_today',
  }).catch(() => {
    // Fallback: usar update direto
    supabase
      .from('users')
      .update({ messages_today: supabase.raw('messages_today + 1') })
      .eq('id', userId);
  });
}

async function saveToCache(
  supabase: any,
  queryText: string,
  responseText: string,
  embedding: number[],
  model: string,
  tokensUsed: number
): Promise<void> {
  await supabase.from('message_cache').insert({
    query_embedding: embedding,
    query_text: queryText,
    response_text: responseText,
    model,
    tokens_used: tokensUsed,
  });
}

async function logTokenUsage(supabase: any, data: TokenUsageData): Promise<void> {
  const costPerInputToken = CONFIG.costs[data.model as keyof typeof CONFIG.costs].input / 1_000_000;
  const costPerOutputToken = CONFIG.costs[data.model as keyof typeof CONFIG.costs].output / 1_000_000;
  const estimatedCost = (data.prompt_tokens * costPerInputToken) + (data.completion_tokens * costPerOutputToken);

  await supabase.from('token_usage').insert({
    user_id: data.user_id,
    session_id: data.session_id,
    operation_type: data.operation_type,
    model: data.model,
    prompt_tokens: data.prompt_tokens,
    completion_tokens: data.completion_tokens,
    total_tokens: data.total_tokens,
    estimated_cost: estimatedCost,
  });

  // Atualizar totais do usuário
  await supabase
    .from('users')
    .update({
      total_tokens_used: supabase.raw(`total_tokens_used + ${data.total_tokens}`),
      total_cost_usd: supabase.raw(`total_cost_usd + ${estimatedCost}`),
    })
    .eq('id', data.user_id);
}

async function getOrCreateSession(
  supabase: any,
  userId: string,
  sessionId?: string
): Promise<string> {
  if (sessionId) {
    // Verificar se sessão existe e pertence ao usuário
    const { data, error } = await supabase
      .from('chat_sessions')
      .select('id')
      .eq('id', sessionId)
      .eq('user_id', userId)
      .eq('is_active', true)
      .single();

    if (!error && data) {
      return sessionId;
    }
  }

  // Criar nova sessão
  const { data, error } = await supabase
    .from('chat_sessions')
    .insert({
      user_id: userId,
      title: 'Nova Conversa',
      is_active: true,
    })
    .select('id')
    .single();

  if (error) {
    throw new Error(`Error creating session: ${error.message}`);
  }

  return data.id;
}

async function saveMessage(
  supabase: any,
  sessionId: string,
  userId: string,
  role: 'user' | 'assistant',
  content: string,
  embedding?: number[],
  tokensUsed?: number
): Promise<void> {
  await supabase.from('chat_messages').insert({
    session_id: sessionId,
    user_id: userId,
    role,
    content,
    embedding: embedding || null,
    tokens_used: tokensUsed || 0,
    model: CONFIG.model,
  });
}

// ========================================
// HANDLER PRINCIPAL
// ========================================

serve(async (req) => {
  // CORS headers
  if (req.method === 'OPTIONS') {
    return new Response(null, {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
      },
    });
  }

  try {
    // 1. Parse request
    const { message, session_id, user_id }: ChatRequest = await req.json();

    if (!message || !user_id) {
      return new Response(JSON.stringify({ error: 'Missing required fields' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // 2. Initialize Supabase client
    const supabase = createClient(SUPABASE_URL!, SUPABASE_SERVICE_ROLE_KEY!);

    // 3. Check rate limit
    const { allowed, remaining } = await checkRateLimit(supabase, user_id);
    if (!allowed) {
      return new Response(
        JSON.stringify({
          error: 'Rate limit exceeded',
          message: 'Você atingiu o limite diário de mensagens. Considere fazer upgrade do seu plano.',
        }),
        {
          status: 429,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // 4. Get or create session
    const sessionId = await getOrCreateSession(supabase, user_id, session_id);

    // 5. Generate embedding for user message
    console.log('Generating embedding...');
    const embedding = await generateEmbedding(message);

    // Log embedding usage
    await logTokenUsage(supabase, {
      user_id,
      session_id: sessionId,
      operation_type: 'embedding',
      model: CONFIG.embeddingModel,
      prompt_tokens: Math.ceil(message.length / 4), // Estimativa
      completion_tokens: 0,
      total_tokens: Math.ceil(message.length / 4),
      estimated_cost: 0,
    });

    // 6. Check cache
    console.log('Checking cache...');
    const cachedResponse = await searchCache(supabase, embedding);

    if (cachedResponse) {
      console.log('Cache hit! Returning cached response.');
      
      // Salvar mensagens do usuário e resposta em cache
      await saveMessage(supabase, sessionId, user_id, 'user', message, embedding);
      await saveMessage(supabase, sessionId, user_id, 'assistant', cachedResponse.response_text);
      
      // Incrementar contador
      await incrementMessageCount(supabase, user_id);

      return new Response(
        JSON.stringify({
          response: cachedResponse.response_text,
          session_id: sessionId,
          cached: true,
          remaining_messages: remaining > 0 ? remaining - 1 : -1,
        }),
        {
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
          },
        }
      );
    }

    // 7. Cache miss - buscar contexto e gerar resposta
    console.log('Cache miss. Building context...');

    // Buscar mensagens da sessão atual
    const sessionMessages = await getSessionMessages(supabase, sessionId);

    // Buscar mensagens similares
    const similarMessages = await searchSimilarMessages(supabase, embedding, user_id);

    // Buscar na base de conhecimento
    const kbEntries = await searchKnowledgeBase(supabase, embedding);

    // Construir contexto
    const context = buildContext(sessionMessages, similarMessages, kbEntries);

    // Salvar mensagem do usuário
    await saveMessage(supabase, sessionId, user_id, 'user', message, embedding);

    // 8. Chamar OpenAI com streaming
    console.log('Calling OpenAI API...');
    const openaiResponse = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: CONFIG.model,
        messages: [
          { role: 'system', content: SYSTEM_PROMPT },
          { role: 'system', content: `Contexto adicional:\n${context}` },
          { role: 'user', content: message },
        ],
        temperature: CONFIG.temperature,
        max_tokens: CONFIG.maxTokens,
        stream: true,
      }),
    });

    if (!openaiResponse.ok) {
      const error = await openaiResponse.text();
      throw new Error(`OpenAI API error: ${error}`);
    }

    // 9. Stream response back to client
    const stream = new ReadableStream({
      async start(controller) {
        const reader = openaiResponse.body!.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';
        let promptTokens = 0;
        let completionTokens = 0;

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n').filter((line) => line.trim() !== '');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') continue;

                try {
                  const parsed = JSON.parse(data);
                  const content = parsed.choices[0]?.delta?.content || '';
                  
                  if (content) {
                    fullResponse += content;
                    controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify({ content })}\n\n`));
                  }

                  // Capturar usage se disponível
                  if (parsed.usage) {
                    promptTokens = parsed.usage.prompt_tokens;
                    completionTokens = parsed.usage.completion_tokens;
                  }
                } catch (e) {
                  console.error('Error parsing SSE data:', e);
                }
              }
            }
          }

          // Estimar tokens se não fornecidos
          if (!promptTokens) {
            promptTokens = Math.ceil((SYSTEM_PROMPT.length + context.length + message.length) / 4);
          }
          if (!completionTokens) {
            completionTokens = Math.ceil(fullResponse.length / 4);
          }

          // Salvar resposta completa
          await saveMessage(supabase, sessionId, user_id, 'assistant', fullResponse, undefined, completionTokens);

          // Salvar no cache
          await saveToCache(supabase, message, fullResponse, embedding, CONFIG.model, completionTokens);

          // Log token usage
          await logTokenUsage(supabase, {
            user_id,
            session_id: sessionId,
            operation_type: 'chat',
            model: CONFIG.model,
            prompt_tokens: promptTokens,
            completion_tokens: completionTokens,
            total_tokens: promptTokens + completionTokens,
            estimated_cost: 0, // Será calculado na função
          });

          // Incrementar contador
          await incrementMessageCount(supabase, user_id);

          // Enviar evento final
          controller.enqueue(
            new TextEncoder().encode(
              `data: ${JSON.stringify({
                done: true,
                session_id: sessionId,
                tokens: { prompt: promptTokens, completion: completionTokens },
                remaining_messages: remaining > 0 ? remaining - 1 : -1,
              })}\n\n`
            )
          );

          controller.close();
        } catch (error) {
          console.error('Streaming error:', error);
          controller.error(error);
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (error) {
    console.error('Error in chat-ai function:', error);
    return new Response(
      JSON.stringify({
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      }
    );
  }
});