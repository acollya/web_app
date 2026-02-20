# Supabase Edge Function: chat-ai (Python)
# Endpoint de chat com IA usando OpenAI API
# Implementa limite de mensagens para usuários free

import os
import json
from datetime import datetime, timezone
from supabase import create_client, Client
import openai
from http.server import BaseHTTPRequestHandler

# ========== ENV VARS ==========
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')

if not OPENAI_API_KEY:
    print('⚠️ OPENAI_API_KEY não definido')
if not SUPABASE_URL:
    print('⚠️ SUPABASE_URL não definido')
if not SUPABASE_SERVICE_ROLE_KEY:
    print('⚠️ SUPABASE_SERVICE_ROLE_KEY não definido')

# ========== CLIENTES ==========
openai.api_key = OPENAI_API_KEY
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ========== CORS HEADERS ==========
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json',
}


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()

    def do_POST(self):
        """Handle POST request for chat"""
        try:
            # 1) Ler body
            content_length = int(self.headers.get('Content-Length', 0))
            body_bytes = self.rfile.read(content_length)
            body = json.loads(body_bytes.decode('utf-8'))

            message = body.get('message', '').strip()
            user_id = body.get('userId', '').strip()
            session_id = body.get('sessionId', '')

            if not message or not user_id:
                self._send_error(400, 'message e userId são obrigatórios')
                return

            # 2) Buscar dados do usuário
            user_response = supabase.table('users').select(
                'id, plan_code, messages_today, name'
            ).eq('id', user_id).single().execute()

            if not user_response.data:
                self._send_error(404, 'Usuário não encontrado')
                return

            user = user_response.data
            plan_code = user.get('plan_code', 0)
            messages_today = user.get('messages_today', 0)
            user_name = user.get('name', 'Usuário')

            # 3) Verificar limite de mensagens (free = max 10/dia)
            if plan_code == 0 and messages_today >= 10:
                self._send_error(
                    403,
                    'Limite de mensagens diário atingido. Faça upgrade para premium para mensagens ilimitadas.'
                )
                return

            # 4) Chamar OpenAI API
            try:
                system_prompt = f"""Você é um assistente de saúde mental empático e acolhedor chamado Acollya.
Seu objetivo é fornecer suporte emocional, ouvir ativamente e oferecer orientações gentis.
Você está conversando com {user_name}.
Seja caloroso, compreensivo e não julgue. Ofereça conselhos práticos quando apropriado.
Mantenha respostas concisas (2-4 parágrafos) e acessíveis."""

                completion = openai.ChatCompletion.create(
                    model='gpt-3.5-turbo',
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': message}
                    ],
                    max_tokens=500,
                    temperature=0.7,
                )

                ai_response = completion.choices[0].message.content.strip()

            except Exception as openai_error:
                print(f'❌ Erro ao chamar OpenAI API: {openai_error}')
                self._send_error(500, f'Erro ao processar mensagem com IA: {str(openai_error)}')
                return

            # 5) Incrementar contador de mensagens
            new_count = messages_today + 1
            supabase.table('users').update({
                'messages_today': new_count,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', user_id).execute()

            # 6) Salvar mensagens no banco
            now_iso = datetime.now(timezone.utc).isoformat()

            # Mensagem do usuário
            supabase.table('chat_messages').insert({
                'user_id': user_id,
                'session_id': session_id or None,
                'role': 'user',
                'content': message,
                'created_at': now_iso,
            }).execute()

            # Resposta da IA
            supabase.table('chat_messages').insert({
                'user_id': user_id,
                'session_id': session_id or None,
                'role': 'assistant',
                'content': ai_response,
                'created_at': now_iso,
            }).execute()

            # 7) Retornar resposta
            response_data = {
                'success': True,
                'response': ai_response,
                'messagesRemaining': None if plan_code == 1 else (10 - new_count),
            }

            self._send_json(200, response_data)

        except Exception as e:
            print(f'❌ Erro interno: {e}')
            self._send_error(500, f'Erro interno: {str(e)}')

    def _send_json(self, status_code: int, data: dict):
        """Send JSON response"""
        self.send_response(status_code)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _send_error(self, status_code: int, message: str):
        """Send error response"""
        self._send_json(status_code, {'error': message})