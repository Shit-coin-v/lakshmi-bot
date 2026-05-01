import { Routes, Route, useLocation, matchPath } from 'react-router-dom';
import { Sidebar } from './components/Sidebar.jsx';
import { TopBar } from './components/TopBar.jsx';
import { ROUTES, ROOT_REDIRECT, NOT_FOUND_ELEMENT, SCREEN_TITLES } from './routes.jsx';
import dashboard from './fixtures/dashboard.js';

function findMeta(pathname) {
  for (const key of Object.keys(SCREEN_TITLES)) {
    if (matchPath(key, pathname)) return SCREEN_TITLES[key];
  }
  return { title: '', breadcrumbs: [] };
}

export default function App() {
  const location = useLocation();
  const meta = findMeta(location.pathname);
  const badges = { newOrders: dashboard.newOrdersBadge ?? 0 };

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <Sidebar badges={badges} />
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <TopBar title={meta.title} breadcrumbs={meta.breadcrumbs} primaryAction={meta.primaryAction} />
        <div style={{ flex: 1, padding: 24, overflow: 'auto' }}>
          <Routes>
            <Route path="/" element={ROOT_REDIRECT} />
            {ROUTES.map((r) => (
              <Route key={r.path} path={r.path} element={r.element} />
            ))}
            <Route path="*" element={NOT_FOUND_ELEMENT} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
