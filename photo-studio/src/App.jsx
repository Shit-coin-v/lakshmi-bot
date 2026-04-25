import { Navigate, Route, Routes } from 'react-router-dom';
import ApiKeySetup from './components/ApiKeySetup.jsx';
import OfflineBanner from './components/OfflineBanner.jsx';
import { SessionProvider } from './context/SessionContext.jsx';
import useApiKey from './hooks/useApiKey.js';
import useNetworkStatus from './hooks/useNetworkStatus.js';
import CatalogPage from './pages/CatalogPage.jsx';
import CameraPage from './pages/CameraPage.jsx';
import PreviewPage from './pages/PreviewPage.jsx';
import FormPage from './pages/FormPage.jsx';
import SuccessPage from './pages/SuccessPage.jsx';

export default function App() {
  const { apiKey, save } = useApiKey();
  const online = useNetworkStatus();

  if (!apiKey) {
    return <ApiKeySetup onSave={save} />;
  }

  return (
    <SessionProvider>
      <OfflineBanner visible={!online} />
      <Routes>
        <Route path="/" element={<CatalogPage />} />
        <Route path="/camera" element={<CameraPage />} />
        <Route path="/preview" element={<PreviewPage />} />
        <Route path="/form" element={<FormPage />} />
        <Route path="/success" element={<SuccessPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </SessionProvider>
  );
}
