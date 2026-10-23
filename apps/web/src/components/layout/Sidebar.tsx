import React from 'react';
import {
  LayoutDashboard,
  Map as MapIcon,
  Navigation,
  AlertTriangle,
  ShieldCheck,
  TrendingUp,
  BrainCircuit,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

export type ActiveTab =
  | 'dashboard'
  | 'map'
  | 'planner'
  | 'report'
  | 'incidents'
  | 'forecasting'
  | 'memory'
  | 'evaluations'
  | 'settings';

interface SidebarProps {
  activeTab: ActiveTab;
  onSelectTab: (tab: ActiveTab) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  incidentCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  incidentCount = 1,
}) => {
  const navItems = [
    { id: 'dashboard' as ActiveTab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'map' as ActiveTab, label: 'Live Map', icon: MapIcon },
    { id: 'planner' as ActiveTab, label: 'Route Planner', icon: Navigation, badge: 'Scenarios' },
    { id: 'report' as ActiveTab, label: 'Report Incident', icon: AlertTriangle },
    { id: 'incidents' as ActiveTab, label: 'Incidents & Review', icon: ShieldCheck, badge: incidentCount > 0 ? String(incidentCount) : undefined },
    { id: 'forecasting' as ActiveTab, label: 'Forecasting', icon: TrendingUp },
    { id: 'memory' as ActiveTab, label: 'Road Memory', icon: BrainCircuit },
    { id: 'evaluations' as ActiveTab, label: 'Evaluations', icon: BarChart3 },
    { id: 'settings' as ActiveTab, label: 'Settings', icon: Settings },
  ];

  const handleNavClick = (tab: ActiveTab) => {
    onSelectTab(tab);
    onCloseMobile();
  };

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      <div className="sidebar-header">
        <div className="brand-badge">
          <div className="brand-logo-icon">
            <Sparkles size={20} />
          </div>
          {!collapsed && (
            <div>
              <div className="brand-title">RoadMind AI</div>
              <div className="brand-subtitle">Sector 7 Corridor</div>
            </div>
          )}
        </div>
        <button
          type="button"
          className="btn btn-ghost btn-icon"
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => handleNavClick(item.id)}
              title={collapsed ? item.label : undefined}
            >
              <Icon size={18} />
              {!collapsed && <span>{item.label}</span>}
              {!collapsed && item.badge && (
                <span className="nav-badge">{item.badge}</span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        {!collapsed && (
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            <div><strong>NEXATHON 2026</strong></div>
            <div>Evidence-Aware Traffic AI</div>
          </div>
        )}
      </div>
    </aside>
  );
};
