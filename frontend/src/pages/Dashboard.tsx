// Inside /frontend/src/pages/Dashboard.tsx or App.tsx (Ahmad's sandbox)
import { NewsIntelligenceWidget } from '../components/widgets/NewsIntelligenceWidget';

export function Dashboard() {
  return (
    <main className="p-6 space-y-6">
      {/* Other portfolio and scenario widgets */}
      <NewsIntelligenceWidget />
    </main>
  );
}