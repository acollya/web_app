import { Layout } from '@/components/Layout';
import { PageHeader } from '@/components/PageHeader';

export default function Analytics() {
  return (
    <Layout>
      <div className="px-6 py-8">
        <PageHeader title="Análise de Emoções" subtitle="Seus padrões emocionais" />
        <p className="text-azul-salvia/70 mt-2">Em desenvolvimento...</p>
      </div>
    </Layout>
  );
}