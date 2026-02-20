import { useParams } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';

export default function Booking() {
  const { therapistId } = useParams();
  
  return (
    <Layout showBottomNav={false}>
      <div className="px-6 py-8">
        <PageHeader title="Agendar Consulta" subtitle={`Terapeuta ID: ${therapistId}`} />
        <p className="text-azul-salvia/70 mt-2">Em desenvolvimento...</p>
      </div>
    </Layout>
  );
}