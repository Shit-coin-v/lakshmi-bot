// Hook слежения за состоянием сети — для OfflineBanner и решения, можно ли
// сейчас отправлять фото. В MVP только индикация; offline-очередь снимков
// не реализована, но архитектурно расширяема.

import { useEffect, useState } from 'react';

export default function useNetworkStatus() {
  const [online, setOnline] = useState(() =>
    typeof navigator === 'undefined' ? true : navigator.onLine
  );

  useEffect(() => {
    function handleOnline() {
      setOnline(true);
    }
    function handleOffline() {
      setOnline(false);
    }
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return online;
}
