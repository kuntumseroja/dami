import {
  Content,
  Header,
  HeaderName,
  SideNav,
  SideNavItems,
  SideNavLink,
} from '@carbon/react';
import {
  Dashboard as DashboardIcon,
  DocumentTasks,
  Compare,
  Scales,
  DecisionTree,
  CloudLogging,
} from '@carbon/icons-react';
import { NavLink, Route as RouterRoute, Routes, useLocation } from 'react-router-dom';

import Dashboard from './pages/Dashboard';
import Drafting from './pages/Drafting';
import Consistency from './pages/Consistency';
import ReviewPanel from './pages/ReviewPanel';
import Routing from './pages/Routing';
import Audit from './pages/Audit';

const NAV = [
  { to: '/', label: 'Dashboard', icon: DashboardIcon },
  { to: '/drafting', label: 'NOTA Drafting', icon: DocumentTasks },
  { to: '/consistency', label: 'Consistency Checker', icon: Compare },
  { to: '/review-panel', label: 'Review Panel', icon: Scales },
  { to: '/routing', label: 'SOP Routing', icon: DecisionTree },
  { to: '/audit', label: 'Audit Trail', icon: CloudLogging },
];

export default function App() {
  const location = useLocation();
  return (
    <>
      <Header aria-label="DAM Governance Intelligence">
        <HeaderName prefix="Danantara">DAM Governance Intelligence</HeaderName>
      </Header>
      <SideNav isFixedNav expanded aria-label="Side navigation">
        <SideNavItems>
          {NAV.map(({ to, label, icon: Icon }) => (
            <SideNavLink
              key={to}
              renderIcon={Icon}
              as={NavLink}
              to={to}
              isActive={location.pathname === to}
            >
              {label}
            </SideNavLink>
          ))}
        </SideNavItems>
        <div className="dam-account">
          <span className="dam-account__avatar">DA</span>
          <div>
            <div className="dam-account__name">DAM Analyst</div>
            <div className="dam-account__role">Danantara · Reviewer</div>
          </div>
        </div>
      </SideNav>
      <Content style={{ marginLeft: '16rem', background: 'transparent' }}>
        <Routes>
          <RouterRoute path="/" element={<Dashboard />} />
          <RouterRoute path="/drafting" element={<Drafting />} />
          <RouterRoute path="/drafting/:caseId" element={<Drafting />} />
          <RouterRoute path="/consistency" element={<Consistency />} />
          <RouterRoute path="/review-panel" element={<ReviewPanel />} />
          <RouterRoute path="/review-panel/:caseId" element={<ReviewPanel />} />
          <RouterRoute path="/routing" element={<Routing />} />
          <RouterRoute path="/audit" element={<Audit />} />
        </Routes>
      </Content>
    </>
  );
}
