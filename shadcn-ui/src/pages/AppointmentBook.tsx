import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { PageHeader } from '@/components/PageHeader';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { appointmentService } from '@/services/appointmentService';
import { paymentService } from '@/services/paymentService';
import { Therapist, TherapistAvailability } from '@/types/appointment';
import { useToast } from '@/hooks/use-toast';
import { Star, Calendar as CalendarIcon, Clock, CreditCard } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';

export default function AppointmentBook() {
  const { therapistId } = useParams<{ therapistId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { user } = useAuthStore();
  
  const [therapist, setTherapist] = useState<Therapist | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date>();
  const [availability, setAvailability] = useState<TherapistAvailability | null>(null);
  const [selectedTime, setSelectedTime] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [isBooking, setIsBooking] = useState(false);

  useEffect(() => {
    loadTherapist();
  }, [therapistId]);

  useEffect(() => {
    if (selectedDate) {
      loadAvailability();
    }
  }, [selectedDate]);

  const loadTherapist = async () => {
    if (!therapistId) return;
    
    try {
      const data = await appointmentService.getTherapist(therapistId);
      setTherapist(data);
    } catch (error) {
      toast({
        title: 'Erro ao carregar terapeuta',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
      navigate('/appointments');
    } finally {
      setIsLoading(false);
    }
  };

  const loadAvailability = async () => {
    if (!therapistId || !selectedDate) return;
    
    try {
      const dateStr = selectedDate.toISOString().split('T')[0];
      const data = await appointmentService.getAvailability(therapistId, dateStr);
      setAvailability(data);
      setSelectedTime('');
    } catch (error) {
      toast({
        title: 'Erro ao carregar disponibilidade',
        description: 'Tente novamente',
        variant: 'destructive',
      });
    }
  };

  const handleBooking = async () => {
    if (!therapistId || !selectedDate || !selectedTime || !therapist) return;

    setIsBooking(true);
    try {
      // Create appointment
      const dateStr = selectedDate.toISOString().split('T')[0];
      const appointment = await appointmentService.createAppointment({
        therapistId,
        date: dateStr,
        time: selectedTime,
      });

      // Process payment
      const isPremium = user?.planCode === 1;
      const amount = isPremium && therapist.premiumDiscount
        ? therapist.hourlyRate * (1 - therapist.premiumDiscount / 100)
        : therapist.hourlyRate;

      const paymentResult = await paymentService.processPayment({
        amount,
        description: `Consulta com ${therapist.name}`,
        appointmentId: appointment.id,
      });

      if (paymentResult.success) {
        // Update appointment status
        await appointmentService.updateAppointmentStatus(appointment.id, 'paid');
        
        toast({
          title: 'Consulta agendada com sucesso!',
          description: 'Você receberá um e-mail com os detalhes',
        });
        
        // Navigate to home after successful booking
        navigate('/home');
      } else {
        toast({
          title: 'Erro no pagamento',
          description: 'Não foi possível processar o pagamento',
          variant: 'destructive',
        });
      }
    } catch (error) {
      toast({
        title: 'Erro ao agendar',
        description: 'Tente novamente mais tarde',
        variant: 'destructive',
      });
    } finally {
      setIsBooking(false);
    }
  };

  if (isLoading || !therapist) {
    return (
      <div className="min-h-screen bg-offwhite flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-lavanda-profunda border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const isPremium = user?.planCode === 1;
  const finalPrice = isPremium && therapist.premiumDiscount
    ? therapist.hourlyRate * (1 - therapist.premiumDiscount / 100)
    : therapist.hourlyRate;

  const canBook = selectedDate && selectedTime;

  return (
    <div className="min-h-screen bg-offwhite pb-20">
      <PageHeader title="Agendar Consulta" showBack onBack={() => navigate('/appointments/new')} />
      
      <div className="max-w-2xl mx-auto px-6 py-6 space-y-6">
        {/* Therapist Info */}
        <div className="bg-white rounded-2xl p-6">
          <div className="flex gap-4 mb-4">
            <img
              src={therapist.photo}
              alt={therapist.name}
              className="w-24 h-24 rounded-full object-cover bg-lavanda-serenidade"
            />
            
            <div className="flex-1">
              <h2 className="font-heading font-bold text-xl text-azul-salvia mb-1">
                {therapist.name}
              </h2>
              
              <div className="flex items-center gap-1 mb-2">
                {[...Array(5)].map((_, i) => (
                  <Star
                    key={i}
                    className={`w-4 h-4 ${
                      i < Math.floor(therapist.rating)
                        ? 'fill-amarelo-acolhedor text-amarelo-acolhedor'
                        : 'text-cinza-neutro'
                    }`}
                  />
                ))}
                <span className="text-sm text-azul-salvia/70 ml-1">
                  {therapist.rating.toFixed(1)}
                </span>
              </div>

              <div className="flex flex-wrap gap-2">
                {therapist.specialties.map((specialty, idx) => (
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

          {therapist.bio && (
            <p className="text-sm text-azul-salvia/70 mb-3">
              {therapist.bio}
            </p>
          )}

          {therapist.credentials && therapist.credentials.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {therapist.credentials.map((credential, idx) => (
                <span
                  key={idx}
                  className="text-xs text-azul-salvia/60 bg-offwhite px-2 py-1 rounded"
                >
                  {credential}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Date Selection */}
        <div className="bg-white rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <CalendarIcon className="w-5 h-5 text-lavanda-profunda" />
            <h3 className="font-heading font-bold text-lg text-azul-salvia">
              Escolha a data
            </h3>
          </div>
          
          <Calendar
            mode="single"
            selected={selectedDate}
            onSelect={setSelectedDate}
            disabled={(date) => date < new Date() || date.getDay() === 0}
            className="rounded-xl border border-cinza-neutro"
          />
        </div>

        {/* Time Selection */}
        {selectedDate && availability && (
          <div className="bg-white rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-5 h-5 text-lavanda-profunda" />
              <h3 className="font-heading font-bold text-lg text-azul-salvia">
                Escolha o horário
              </h3>
            </div>
            
            <div className="grid grid-cols-3 gap-3">
              {availability.availableSlots.map((slot) => (
                <button
                  key={slot}
                  onClick={() => setSelectedTime(slot)}
                  className={`h-12 rounded-xl border-2 font-medium transition-all ${
                    selectedTime === slot
                      ? 'border-lavanda-profunda bg-lavanda-profunda text-white'
                      : 'border-cinza-neutro text-azul-salvia hover:border-lavanda-profunda/50'
                  }`}
                >
                  {slot}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Summary */}
        {canBook && (
          <div className="bg-white rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <CreditCard className="w-5 h-5 text-lavanda-profunda" />
              <h3 className="font-heading font-bold text-lg text-azul-salvia">
                Resumo do agendamento
              </h3>
            </div>
            
            <div className="space-y-3 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-azul-salvia/70">Terapeuta:</span>
                <span className="font-medium text-azul-salvia">{therapist.name}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-azul-salvia/70">Data:</span>
                <span className="font-medium text-azul-salvia">
                  {selectedDate?.toLocaleDateString('pt-BR')}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-azul-salvia/70">Horário:</span>
                <span className="font-medium text-azul-salvia">{selectedTime}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-azul-salvia/70">Duração:</span>
                <span className="font-medium text-azul-salvia">1 hora</span>
              </div>
              
              <div className="border-t border-cinza-neutro pt-3 mt-3">
                {isPremium && therapist.premiumDiscount ? (
                  <div className="flex justify-between items-end">
                    <span className="text-azul-salvia/70">Valor:</span>
                    <div className="text-right">
                      <p className="text-xs text-azul-salvia/50 line-through">
                        R$ {therapist.hourlyRate.toFixed(2)}
                      </p>
                      <p className="text-xl font-bold text-verde-esperanca">
                        R$ {finalPrice.toFixed(2)}
                      </p>
                      <p className="text-xs text-verde-esperanca">
                        Desconto Premium aplicado
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-between items-center">
                    <span className="text-azul-salvia/70">Valor:</span>
                    <p className="text-xl font-bold text-azul-salvia">
                      R$ {therapist.hourlyRate.toFixed(2)}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <Button
              onClick={handleBooking}
              disabled={isBooking}
              className="w-full h-14 bg-lavanda-profunda hover:bg-lavanda-profunda/90 text-white rounded-xl text-lg font-semibold"
            >
              {isBooking ? 'Processando...' : 'Confirmar e Pagar'}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}