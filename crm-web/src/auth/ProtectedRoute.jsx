import { Navigate, useLocation } from 'react-router-dom';
import { Splash } from '../components/Splash.jsx';
import { useAuthContext } from './AuthProvider.jsx';

export function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuthContext();
  const location = useLocation();
  if (isLoading) return <Splash />;
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

export default ProtectedRoute;
