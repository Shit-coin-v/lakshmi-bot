import { NavLink } from 'react-router-dom';
import { Icon } from './Icon.jsx';
import lakshmiGlyph from '../assets/lakshmi-glyph.svg';

export const NAV_ITEMS = [
  { id: 'dashboard',  label: 'Дашборд',     icon: 'layout-dashboard', path: '/dashboard' },
  { id: 'clients',    label: 'Клиенты',     icon: 'users',            path: '/clients' },
  { id: 'orders',     label: 'Заказы',      icon: 'package',          path: '/orders', badgeKey: 'newOrders' },
  { id: 'campaigns',  label: 'Кампании',    icon: 'megaphone',        path: '/campaigns' },
  { id: 'rfm',        label: 'RFM-сегменты',icon: 'pie-chart',        path: '/rfm' },
  { id: 'broadcasts', label: 'Рассылки',    icon: 'send',             path: '/broadcasts' },
  { id: 'catalog',    label: 'Каталог',     icon: 'boxes',            path: '/catalog' },
  { id: 'categories', label: 'Категории',   icon: 'layers',           path: '/categories' },
  { id: 'abc_xyz',    label: 'ABC / XYZ',   icon: 'grid-3x3',         path: '/abc-xyz' },
  { id: 'analytics',  label: 'Аналитика',   icon: 'bar-chart-3',      path: '/analytics' },
];

export function Sidebar({ badges = {} }) {
  return (
    <aside style={{
      width: 'var(--sidebar-w)',
      background: 'var(--surface-sidebar)',
      color: 'var(--fg-on-dark)',
      display: 'flex', flexDirection: 'column',
      flexShrink: 0,
      transition: 'width var(--dur-standard) var(--ease-standard)',
    }}>
      <div style={{ height: 'var(--topbar-h)', display: 'flex', alignItems: 'center', padding: '0 16px', gap: 10, borderBottom: '1px solid var(--border-subtle)' }}>
        <img src={lakshmiGlyph} width="28" height="28" alt="" style={{ borderRadius: 6 }} />
        <span style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>
          Lakshmi <span style={{ color: 'var(--fg-on-dark-muted)', fontWeight: 500 }}>CRM</span>
        </span>
      </div>
      <nav style={{ padding: 8, display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
        {NAV_ITEMS.map((item) => {
          const badge = item.badgeKey ? badges[item.badgeKey] : undefined;
          return (
            <NavLink
              key={item.id}
              to={item.path}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '8px 10px', borderRadius: 8,
                background: isActive ? 'var(--surface-sidebar-hover)' : 'transparent',
                color: isActive ? '#FFFFFF' : 'var(--fg-on-dark)',
                textDecoration: 'none', fontSize: 14, fontWeight: 500,
                borderLeft: isActive ? '2px solid var(--accent-600)' : '2px solid transparent',
                paddingLeft: 10,
              })}
            >
              <Icon name={item.icon} size={18} />
              <span style={{ flex: 1 }}>{item.label}</span>
              {badge ? (
                <span style={{
                  background: 'var(--accent-600)', color: '#FFFFFF',
                  fontSize: 11, fontWeight: 600, padding: '2px 6px', borderRadius: 999, minWidth: 20, textAlign: 'center',
                }}>{badge}</span>
              ) : null}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}

export default Sidebar;
