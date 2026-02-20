import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';

export default function Settings() {
  return (
    <Layout showBottomNav={false}>
      <div className="px-6 py-8">
        <PageHeader title="Configurações" subtitle="Personalize sua experiência" />
        <p className="text-azul-salvia/70 mt-2">Em desenvolvimento...</p>
      </div>
    </Layout>
  );
}