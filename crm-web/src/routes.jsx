import { Navigate } from 'react-router-dom';
import RfmScreen from './screens/RfmScreen.jsx';
import CatalogScreen from './screens/CatalogScreen.jsx';
import AnalyticsScreen from './screens/AnalyticsScreen.jsx';
import NotFoundScreen from './screens/NotFoundScreen.jsx';
import DashboardScreen from './screens/DashboardScreen.jsx';
import ClientsScreen from './screens/ClientsScreen.jsx';
import ClientDetailScreen from './screens/ClientDetailScreen.jsx';
import OrdersScreen from './screens/OrdersScreen.jsx';
import CampaignsScreen from './screens/CampaignsScreen.jsx';
import BroadcastsScreen from './screens/BroadcastsScreen.jsx';
import CategoriesScreen from './screens/CategoriesScreen.jsx';
import CategoryDetailScreen from './screens/CategoryDetailScreen.jsx';
import AbcXyzScreen from './screens/AbcXyzScreen.jsx';

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
  { path: '/dashboard',         element: <DashboardScreen /> },
  { path: '/clients',           element: <ClientsScreen /> },
  { path: '/clients/:id',       element: <ClientDetailScreen /> },
  { path: '/orders',            element: <OrdersScreen /> },
  { path: '/campaigns',         element: <CampaignsScreen /> },
  { path: '/rfm',               element: <RfmScreen /> },
  { path: '/broadcasts',        element: <BroadcastsScreen /> },
  { path: '/catalog',           element: <CatalogScreen /> },
  { path: '/categories',        element: <CategoriesScreen /> },
  { path: '/categories/:slug',  element: <CategoryDetailScreen /> },
  { path: '/abc-xyz',           element: <AbcXyzScreen /> },
  { path: '/analytics',         element: <AnalyticsScreen /> },
];

export const ROOT_REDIRECT = <Navigate to="/dashboard" replace />;
export const NOT_FOUND_ELEMENT = <NotFoundScreen />;
