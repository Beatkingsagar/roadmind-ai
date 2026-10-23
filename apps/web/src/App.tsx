import React, { useState } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { ReplayProvider } from './context/ReplayContext';
import { RouteProvider, useRoute } from './context/RouteContext';
import { Sidebar, type ActiveTab } from './components/layout/Sidebar';
import { Topbar } from './components/layout/Topbar';
import { MapView } from './components/map/MapView';
import { RoutePlanner } from './components/planner/RoutePlanner';
import { ScenarioComparison } from './components/planner/ScenarioComparison';
import { ReportForm } from './components/incidents/ReportForm';
import { IncidentList } from './components/incidents/IncidentList';
import { ForecastView } from './components/forecasting/ForecastView';
import { MemoryPriorityView } from './components/memory/MemoryPriorityView';
import { EvaluationView } from './components/evaluations/EvaluationView';
import { DashboardOverview } from './components/dashboard/DashboardOverview';
import { SettingsView } from './components/settings/SettingsView';

const MainAppLayout: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [mobileOpen, setMobileOpen] = useState<boolean>(false);
  const { activeSimulation } = useRoute();

  return (
    <div className="app-container">
      {/* Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      {/* Main Content Area */}
      <div className="main-content">
        <Topbar
          activeTab={activeTab}
          onOpenMobile={() => setMobileOpen(true)}
        />

        <main
          className="workspace-area"
          style={{
            padding: activeTab === 'map' ? '0' : '20px',
            overflow: activeTab === 'map' ? 'hidden' : 'auto',
          }}
        >
          {activeTab === 'dashboard' && (
            <DashboardOverview onNavigate={setActiveTab} />
          )}

          {activeTab === 'map' && (
            <MapView />
          )}

          {activeTab === 'planner' && (
            <div style={{ maxWidth: '1100px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
                <RoutePlanner />
                <div className="card" style={{ padding: 0, overflow: 'hidden', height: '360px', position: 'relative' }}>
                  <MapView />
                </div>
              </div>

              {activeSimulation && (
                <ScenarioComparison simulation={activeSimulation} />
              )}
            </div>
          )}

          {activeTab === 'report' && (
            <ReportForm onSuccess={() => setActiveTab('incidents')} />
          )}

          {activeTab === 'incidents' && (
            <IncidentList
              onOpenReportForm={() => setActiveTab('report')}
              onNavigateToMap={() => setActiveTab('map')}
            />
          )}

          {activeTab === 'forecasting' && (
            <ForecastView />
          )}

          {activeTab === 'memory' && (
            <MemoryPriorityView onNavigateToMap={() => setActiveTab('map')} />
          )}

          {activeTab === 'evaluations' && (
            <EvaluationView />
          )}

          {activeTab === 'settings' && (
            <SettingsView />
          )}
        </main>
      </div>
    </div>
  );
};

export function App() {
  return (
    <ThemeProvider>
      <ReplayProvider>
        <RouteProvider>
          <MainAppLayout />
        </RouteProvider>
      </ReplayProvider>
    </ThemeProvider>
  );
}

export default App;
