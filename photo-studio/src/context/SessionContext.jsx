// Глобальное состояние сессии съёмки: выбранный товар, выбранный файл и
// последний полученный обработанный image_url. Контекст не сериализуется —
// данные живут только до перезагрузки страницы.

import { createContext, useContext, useMemo, useState } from 'react';

const SessionContext = createContext(null);

export function SessionProvider({ children }) {
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [processedImageUrl, setProcessedImageUrl] = useState(null);

  const value = useMemo(
    () => ({
      selectedProduct,
      setSelectedProduct,
      selectedFile,
      setSelectedFile,
      processedImageUrl,
      setProcessedImageUrl,
      reset: () => {
        setSelectedProduct(null);
        setSelectedFile(null);
        setProcessedImageUrl(null);
      },
    }),
    [selectedProduct, selectedFile, processedImageUrl]
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error('useSession must be used inside <SessionProvider>');
  }
  return ctx;
}
