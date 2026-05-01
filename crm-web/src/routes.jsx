import { Navigate } from 'react-router-dom';
import { Placeholder } from './components/Placeholder.jsx';
import RfmScreen from './screens/RfmScreen.jsx';
import CatalogScreen from './screens/CatalogScreen.jsx';
import AnalyticsScreen from './screens/AnalyticsScreen.jsx';
import NotFoundScreen from './screens/NotFoundScreen.jsx';

// Временные заглушки — заменяются в Tasks 10-18.
const TmpDashboard       = () => <Placeholder name="Дашборд" />;
const TmpClients         = () => <Placeholder name="Клиенты" />;
const TmpClientDetail    = () => <Placeholder name="Карточка клиента" />;
const TmpOrders          = () => <Placeholder name="Заказы" />;
const TmpCampaigns       = () => <Placeholder name="Кампании" />;
const TmpBroadcasts      = () => <Placeholder name="Рассылки" />;
const TmpCategories      = () => <Placeholder name="Категории" />;
const TmpCategoryDetail  = () => <Placeholder name="Категория" />;
const TmpAbcXyz          = () => <Placeholder name="ABC / XYZ" />;

export const SCREEN_TITLES = {
  '/dashboard':   { title: 'Дашборд',                     breadcrumbs: ['Lakshmi CRM'] },
  '/clients':     { title: 'Клиенты',                     breadcrumbs: ['Lakshmi CRM'], primaryAction: { label: 'Новый клиент', icon: 'plus' } },
  '/clients/:id': { title: 'Карточка клиента',            breadcrumbs: ['Клиенты'] },
  '/orders':      { title: 'Заказы доставки',             breadcrumbs: ['Lakshmi CRM'] },
  '/campaigns':   { title: 'Кампании',                    breadcrumbs: ['Lakshmi CRM'], primaryAction: { label: 'Создать кампанию', icon: 'plus' } },
  '/rfm':         { title: 'RFM-сегменты',                breadcrumbs: ['Lakshmi CRM'] },
  '/broadcasts':  { title: 'Рассылки',                    breadcrumbs: ['Lakshmi CRM'], primaryAction: { label: 'Новая рассылка', icon: 'plus' } },
  '/catalog':     { title: 'Каталог',                     breadcrumbs: ['Lakshmi CRM'] },
  '/categories':  { title: 'Категорийный менеджмент',     breadcrumbs: ['Lakshmi CRM'] },
  '/categories/:slug': { title: 'Категория',              breadcrumbs: ['Категории'] },
  '/abc-xyz':     { title: 'ABC / XYZ — весь ассортимент',breadcrumbs: ['Lakshmi CRM'] },
  '/analytics':   { title: 'Аналитика',                   breadcrumbs: ['Lakshmi CRM'] },
};

export const ROUTES = [
  { path: '/dashboard',         element: <TmpDashboard /> },
  { path: '/clients',           element: <TmpClients /> },
  { path: '/clients/:id',       element: <TmpClientDetail /> },
  { path: '/orders',            element: <TmpOrders /> },
  { path: '/campaigns',         element: <TmpCampaigns /> },
  { path: '/rfm',               element: <RfmScreen /> },
  { path: '/broadcasts',        element: <TmpBroadcasts /> },
  { path: '/catalog',           element: <CatalogScreen /> },
  { path: '/categories',        element: <TmpCategories /> },
  { path: '/categories/:slug',  element: <TmpCategoryDetail /> },
  { path: '/abc-xyz',           element: <TmpAbcXyz /> },
  { path: '/analytics',         element: <AnalyticsScreen /> },
];

export const ROOT_REDIRECT = <Navigate to="/dashboard" replace />;
export const NOT_FOUND_ELEMENT = <NotFoundScreen />;
