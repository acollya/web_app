# Appointment Booking Edge Function

Gerenciar agendamentos de consultas com terapeutas.

## Funcionalidades

- ✅ Criar agendamentos
- ✅ Cancelar agendamentos
- ✅ Verificar disponibilidade
- ✅ Gerar links do Google Meet
- ✅ Validação de horários

## Variáveis de Ambiente

```bash
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

## Deploy

```bash
supabase functions deploy appointment-booking
```

## Uso

### Criar Agendamento

```bash
POST /appointment-booking
Authorization: Bearer <jwt-token>

{
  "userId": "uuid-do-usuario",
  "therapistId": "therapist-1",
  "date": "2025-02-15",
  "time": "14:00",
  "action": "create"
}
```

### Cancelar Agendamento

```bash
POST /appointment-booking
Authorization: Bearer <jwt-token>

{
  "userId": "uuid-do-usuario",
  "appointmentId": "appointment-123",
  "action": "cancel"
}
```

### Response (Criar)

```json
{
  "success": true,
  "appointment": {
    "id": "appointment-123",
    "userId": "user-456",
    "therapistId": "therapist-1",
    "therapistName": "Dra. Ana Silva",
    "date": "2025-02-15",
    "time": "14:00",
    "status": "pending",
    "meetLink": "https://meet.google.com/acollya-abc123",
    "amount": 150,
    "createdAt": "2025-01-15T10:30:00Z"
  },
  "message": "Agendamento criado com sucesso! 📅"
}
```

## Validações

- ✅ Data deve ser futura
- ✅ Horário entre 8h-20h (horário comercial)
- ✅ Verifica conflitos de horário
- ✅ Apenas um agendamento por horário/terapeuta

## Status de Agendamento

- `pending`: Aguardando confirmação
- `confirmed`: Confirmado
- `cancelled`: Cancelado
- `completed`: Concluído