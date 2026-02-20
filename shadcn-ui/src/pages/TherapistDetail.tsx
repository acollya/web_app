import { useParams } from 'react-router-dom';
import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';

export default function TherapistDetail() {
  const { id } = useParams();
  
  return (
    <Layout showBottomNav={false}>
      <div className="px-6 py-8">
        <PageHeader title="Detalhes do Terapeuta" subtitle={`ID: ${id}`} />
        <p className="text-azul-salvia/70 mt-2">Em desenvolvimento...</p>
      </div>
    </Layout>
  );
}