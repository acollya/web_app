import { isDemoMode, getCurrentUser } from '@/lib/supabase';
import { callAppointmentBooking } from '@/lib/edgeFunctions';
import type { AppointmentDetails } from '@/types/edgeFunctions';

interface StoredAppointment {
  id: string;
  userId: string;
  therapistId: string;
  therapistName: string;
  date: string;
  time: string;
  status: string;
  meetLink: string;
  amount: number;
  createdAt: string;
}

export const appointmentService = {
  async bookAppointment(
    therapistId: string,
    date: string,
    time: string
  ): Promise<AppointmentDetails> {
    // Demo mode - return mock data
    if (isDemoMode()) {
      await new Promise((resolve) => setTimeout(resolve, 1000));

      const appointment: AppointmentDetails = {
        id: `appointment-${Date.now()}`,
        userId: 'demo-user',
        therapistId,
        therapistName: 'Dra. Ana Silva',
        date,
        time,
        status: 'pending',
        meetLink: `https://meet.google.com/demo-${Date.now()}`,
        amount: 150,
        createdAt: new Date().toISOString(),
      };

      const stored = localStorage.getItem('acollya_appointments');
      const appointments = stored ? JSON.parse(stored) : [];
      appointments.push(appointment);
      localStorage.setItem('acollya_appointments', JSON.stringify(appointments));

      return appointment;
    }

    // Production mode - use Edge Function
    try {
      const user = await getCurrentUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      const response = await callAppointmentBooking({
        userId: user.id,
        therapistId,
        date,
        time,
        action: 'create',
      });

      if (!response.appointment) {
        throw new Error('Appointment not created');
      }

      return response.appointment;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      console.error('Error booking appointment:', error);

      if (errorMessage.includes('não está disponível')) {
        throw new Error('Este horário não está disponível. Por favor, escolha outro.');
      }

      if (errorMessage.includes('inválida')) {
        throw new Error(
          'Data/hora inválida. Escolha uma data futura dentro do horário comercial (8h-20h).'
        );
      }

      throw new Error(errorMessage || 'Não foi possível agendar a consulta');
    }
  },

  async cancelAppointment(appointmentId: string): Promise<void> {
    // Demo mode - remove from localStorage
    if (isDemoMode()) {
      await new Promise((resolve) => setTimeout(resolve, 500));

      const stored = localStorage.getItem('acollya_appointments');
      if (stored) {
        const appointments = JSON.parse(stored) as StoredAppointment[];
        const updated = appointments.map((apt) =>
          apt.id === appointmentId ? { ...apt, status: 'cancelled' } : apt
        );
        localStorage.setItem('acollya_appointments', JSON.stringify(updated));
      }
      return;
    }

    // Production mode - use Edge Function
    try {
      const user = await getCurrentUser();
      if (!user) {
        throw new Error('User not authenticated');
      }

      await callAppointmentBooking({
        userId: user.id,
        therapistId: '', // Not needed for cancel
        date: '', // Not needed for cancel
        time: '', // Not needed for cancel
        action: 'cancel',
        appointmentId,
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erro desconhecido';
      console.error('Error cancelling appointment:', error);
      throw new Error(errorMessage || 'Não foi possível cancelar o agendamento');
    }
  },

  async getAppointments(): Promise<AppointmentDetails[]> {
    // Demo mode - get from localStorage
    if (isDemoMode()) {
      const stored = localStorage.getItem('acollya_appointments');
      return stored ? JSON.parse(stored) : [];
    }

    // Production mode - would use supabaseDataService
    try {
      const user = await getCurrentUser();
      if (!user) {
        return [];
      }

      // This would be implemented in supabaseDataService
      // For now, return empty array
      return [];
    } catch (error) {
      console.error('Error getting appointments:', error);
      return [];
    }
  },
};