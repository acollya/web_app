import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { appointmentService } from '@/services/appointmentService';
import { paymentService } from '@/services/paymentService';
import { Appointment } from '@/types/appointment';
import { useToast } from '@/hooks/use-toast';
import { Calendar, Clock, Video, CreditCard } from 'lucide-react';

export default function AppointmentMy() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [payingId, setPayingId] = useState<string | null>(null);

  useEffect(() => {
    loadAppointments();
  }, []);

  const loadAppointments = async () => {
    try {
      const data = await appointmentService.getMyAppointments();
      // Sort by date and time, most recent first
      const sorted = data.sort((a, b) => {
        const dateA = new Date(`${a.date}T${a.time}`);
        const dateB = new Date(`${b.date}T${b.time}`);
        return dateB.getTime() - dateA.getTime();
      });
      setAppointments(sorted);
    } catch (error) {
      toast({
        title: 'Erro ao carregar agendamentos',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handlePayment = async (appointment: Appointment) => {
    setPayingId(appointment.id);
    try {
      const paymentResult = await paymentService.processPayment({
        amount: appointment.amount,
        description: `Consulta com ${appointment.therapist.name}`,
        appointmentId: appointment.id,
      });

      if (paymentResult.success) {
        await appointmentService.updateAppointmentStatus(appointment.id, 'paid');
        toast({
          title: 'Pagamento confirmado!',
          description: 'Sua consulta está confirmada',
        });
        loadAppointments();
      } else {
        toast({
          title: 'Erro no pagamento',
          description: 'Não foi possível processar o pagamento',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Erro ao processar pagamento',
        description: 'Tente novamente',
        variant: 'destructive',
      });
    } finally {
      setPayingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-offwhite flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (appointments.length === 0) {
    return (
      <div className="min-h-screen bg-offwhite">
        <PageHeader title="Meus Agendamentos" showBack />
        
        <div className="max-w-2xl mx-auto px-6 py-20 text-center">
          <div className="w-20 h-20 bg-lavanda-serenidade rounded-full flex items-center justify-center mx-auto mb-6">
            <Calendar className="w-10 h-10 text-lavanda-profunda" />
          </div>
          <h2 className="text-xl font-heading font-bold text-azul-salvia mb-2">
            Nenhuma consulta agendada
          </h2>
          <p className="text-azul-salvia/70 mb-8">
            Agende sua primeira consulta com um terapeuta
          </p>
          <Button
            onClick={() => navigate('/appointments/new')}
            className="bg-lavanda-profunda hover:bg-lavanda-profunda/90 text-white rounded-xl px-8"
          >
            Agendar Consulta
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-offwhite pb-20">
      <PageHeader title="Meus Agendamentos" showBack />
      
      <div className="max-w-2xl mx-auto px-6 py-6 space-y-4">
        {appointments.map((appointment) => {
          const canJoin = appointmentService.canJoinAppointment(appointment);
          const appointmentDate = new Date(`${appointment.date}T${appointment.time}`);
          const isPast = appointmentDate < new Date();

          return (
            <div
              key={appointment.id}
              className="bg-white rounded-2xl p-5 shadow-sm border border-cinza-neutro/30"
            >
              <div className="flex gap-4 mb-4">
                <img
                  src={appointment.therapist.photo}
                  alt={appointment.therapist.name}
                  className="w-16 h-16 rounded-full object-cover bg-lavanda-serenidade flex-shrink-0"
                />
                
                <div className="flex-1 min-w-0">
                  <h3 className="font-heading font-bold text-lg text-azul-salvia mb-1">
                    {appointment.therapist.name}
                  </h3>
                  
                  <div className="flex items-center gap-4 text-sm text-azul-salvia/70 mb-2">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      <span>{new Date(appointment.date).toLocaleDateString('pt-BR')}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      <span>{appointment.time}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {appointment.status === 'paid' ? (
                      <span className="px-2 py-1 bg-verde-esperanca/20 text-verde-esperanca text-xs rounded-full font-medium">
                        Pago
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-amarelo-acolhedor/20 text-amarelo-acolhedor text-xs rounded-full font-medium">
                        Pendente
                      </span>
                    )}
                    
                    {isPast && (
                      <span className="px-2 py-1 bg-cinza-neutro/20 text-azul-salvia/60 text-xs rounded-full font-medium">
                        Concluída
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                {appointment.status === 'pending' && (
                  <Button
                    onClick={() => handlePayment(appointment)}
                    disabled={payingId === appointment.id}
                    className="flex-1 bg-verde-esperanca hover:bg-verde-esperanca/90 text-white rounded-xl h-11"
                  >
                    <CreditCard className="w-4 h-4 mr-2" />
                    {payingId === appointment.id ? 'Processando...' : 'Pagar Agora'}
                  </Button>
                )}

                {appointment.status === 'paid' && !isPast && (
                  <Button
                    onClick={() => navigate(`/appointments/details/${appointment.id}`)}
                    disabled={!canJoin}
                    className={`flex-1 rounded-xl h-11 ${
                      canJoin
                        ? 'bg-lavanda-profunda hover:bg-lavanda-profunda/90 text-white'
                        : 'bg-cinza-neutro/20 text-azul-salvia/50 cursor-not-allowed'
                    }`}
                  >
                    <Video className="w-4 h-4 mr-2" />
                    {canJoin ? 'Iniciar Consulta' : 'Aguardando horário'}
                  </Button>
                )}

                {appointment.status === 'paid' && (
                  <Button
                    onClick={() => navigate(`/appointments/details/${appointment.id}`)}
                    variant="outline"
                    className="flex-1 border-lavanda-profunda/30 text-lavanda-profunda hover:bg-lavanda-serenidade rounded-xl h-11"
                  >
                    Ver Detalhes
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}