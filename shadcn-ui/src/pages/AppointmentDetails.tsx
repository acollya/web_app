import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { appointmentService } from '@/services/appointmentService';
import { Appointment } from '@/types/appointment';
import { useToast } from '@/hooks/use-toast';
import { Calendar, Clock, Video, Star, ExternalLink, MapPin, Phone, Mail } from 'lucide-react';

export default function AppointmentDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadAppointment();
  }, [id]);

  const loadAppointment = async () => {
    if (!id) return;
    
    try {
      const data = await appointmentService.getAppointment(id);
      setAppointment(data);
    } catch (error) {
      toast({
        title: 'Erro ao carregar agendamento',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
      navigate('/appointments/my');
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoinMeet = () => {
    if (!appointment?.meetLink) return;
    
    // Try to open in Google Meet app first (deep link)
    const meetAppLink = appointment.meetLink.replace('https://meet.google.com/', 'googlemeet://');
    window.location.href = meetAppLink;
    
    // Fallback to web after a delay
    setTimeout(() => {
      window.open(appointment.meetLink, '_blank');
    }, 1000);
  };

  if (isLoading || !appointment) {
    return (
      <div className="min-h-screen bg-offwhite flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const canJoin = appointmentService.canJoinAppointment(appointment);
  const appointmentDate = new Date(`${appointment.date}T${appointment.time}`);
  const isPast = appointmentDate < new Date();

  return (
    <div className="min-h-screen bg-offwhite pb-20">
      <PageHeader title="Detalhes da Consulta" showBack />
      
      <div className="max-w-2xl mx-auto px-6 py-6 space-y-6">
        {/* Therapist Info */}
        <div className="bg-white rounded-2xl p-6">
          <div className="flex gap-4 mb-4">
            <img
              src={appointment.therapist.photo}
              alt={appointment.therapist.name}
              className="w-24 h-24 rounded-full object-cover bg-lavanda-serenidade"
            />
            
            <div className="flex-1">
              <h2 className="font-heading font-bold text-xl text-azul-salvia mb-1">
                {appointment.therapist.name}
              </h2>
              
              <div className="flex items-center gap-1 mb-2">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`w-4 h-4 ${
                      i < Math.floor(appointment.therapist.rating)
                        ? 'fill-amarelo-acolhedor text-amarelo-acolhedor'
                        : 'text-cinza-neutro'
                    }`}
                  />
                ))}
                <span className="text-sm text-azul-salvia/70 ml-1">
                  {appointment.therapist.rating.toFixed(1)}
                </span>
              </div>

              <div className="flex flex-wrap gap-2">
                {appointment.therapist.specialties.map((specialty, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-lavanda-serenidade text-lavanda-profunda text-xs rounded-full font-medium"
                  >
                    {specialty}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {appointment.therapist.bio && (
            <p className="text-sm text-azul-salvia/70">
              {appointment.therapist.bio}
            </p>
          )}
        </div>

        {/* Appointment Details */}
        <div className="bg-white rounded-2xl p-6">
          <h3 className="font-heading font-bold text-lg text-azul-salvia mb-4">
            Informações da Consulta
          </h3>
          
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-lavanda-serenidade rounded-full flex items-center justify-center flex-shrink-0">
                <Calendar className="w-5 h-5 text-lavanda-profunda" />
              </div>
              <div>
                <p className="text-sm text-azul-salvia/70">Data</p>
                <p className="font-medium text-azul-salvia">
                  {new Date(appointment.date).toLocaleDateString('pt-BR', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-lavanda-serenidade rounded-full flex items-center justify-center flex-shrink-0">
                <Clock className="w-5 h-5 text-lavanda-profunda" />
              </div>
              <div>
                <p className="text-sm text-azul-salvia/70">Horário</p>
                <p className="font-medium text-azul-salvia">{appointment.time}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-lavanda-serenidade rounded-full flex items-center justify-center flex-shrink-0">
                <Video className="w-5 h-5 text-lavanda-profunda" />
              </div>
              <div>
                <p className="text-sm text-azul-salvia/70">Formato</p>
                <p className="font-medium text-azul-salvia">Videochamada (Google Meet)</p>
              </div>
            </div>

            <div className="border-t border-cinza-neutro pt-3 mt-3">
              <div className="flex justify-between items-center">
                <span className="text-azul-salvia/70">Status do Pagamento</span>
                {appointment.status === 'paid' ? (
                  <span className="px-3 py-1 bg-verde-esperanca/20 text-verde-esperanca text-sm rounded-full font-medium">
                    Pago
                  </span>
                ) : (
                  <span className="px-3 py-1 bg-amarelo-acolhedor/20 text-amarelo-acolhedor text-sm rounded-full font-medium">
                    Pendente
                  </span>
                )}
              </div>
              
              <div className="flex justify-between items-center mt-2">
                <span className="text-azul-salvia/70">Valor</span>
                <span className="text-lg font-bold text-azul-salvia">
                  R$ {appointment.amount.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Meet Link */}
        {appointment.status === 'paid' && appointment.meetLink && (
          <div className="bg-lavanda-profunda rounded-2xl p-6 text-white">
            <div className="flex items-center gap-2 mb-3">
              <Video className="w-6 h-6" />
              <h3 className="font-heading font-bold text-lg">
                Link da Consulta
              </h3>
            </div>
            
            <p className="text-sm text-white/80 mb-4">
              {canJoin
                ? 'Sua consulta está disponível! Clique no botão abaixo para entrar.'
                : isPast
                ? 'Esta consulta já foi realizada.'
                : 'O link estará disponível 10 minutos antes do horário agendado.'}
            </p>

            {!isPast && (
              <Button
                onClick={handleJoinMeet}
                disabled={!canJoin}
                className={`w-full h-12 rounded-xl font-semibold ${
                  canJoin
                    ? 'bg-white text-lavanda-profunda hover:bg-white/90'
                    : 'bg-white/20 text-white/50 cursor-not-allowed'
                }`}
              >
                <ExternalLink className="w-5 h-5 mr-2" />
                {canJoin ? 'Entrar na Consulta' : 'Aguardando horário'}
              </Button>
            )}
          </div>
        )}

        {/* Important Info */}
        <div className="bg-amarelo-acolhedor/10 border border-amarelo-acolhedor/30 rounded-xl p-4">
          <h4 className="font-semibold text-azul-salvia mb-2">Informações Importantes</h4>
          <ul className="text-sm text-azul-salvia/80 space-y-1 list-disc list-inside">
            <li>Certifique-se de ter uma conexão estável de internet</li>
            <li>Encontre um ambiente tranquilo e privado</li>
            <li>Teste sua câmera e microfone antes da consulta</li>
            <li>Chegue com alguns minutos de antecedência</li>
          </ul>
        </div>

        {/* Contact Support */}
        <div className="bg-white rounded-2xl p-6">
          <h3 className="font-heading font-bold text-lg text-azul-salvia mb-3">
            Precisa de Ajuda?
          </h3>
          <p className="text-sm text-azul-salvia/70 mb-4">
            Entre em contato com nosso suporte se tiver alguma dúvida
          </p>
          <div className="space-y-2">
            <a
              href="mailto:suporte@acollya.com"
              className="flex items-center gap-2 text-sm text-lavanda-profunda hover:underline"
            >
              <Mail className="w-4 h-4" />
              suporte@acollya.com
            </a>
            <a
              href="https://wa.me/5511999999999"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-sm text-lavanda-profunda hover:underline"
            >
              <Phone className="w-4 h-4" />
              (11) 99999-9999
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}