import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BRAND, RADIUS, SHADOW } from '../theme.js';
import { useSession } from '../context/SessionContext.jsx';
import useDailyProgress from '../hooks/useDailyProgress.js';

// Экран 5 — Сохранено. Инкрементирует счётчик дня и предлагает следующий товар.
export default function SuccessPage() {
  const navigate = useNavigate();
  const { selectedProduct, processedImageUrl, reset } = useSession();
  const { count, increment } = useDailyProgress();

  // Засчитываем успешный кадр ровно один раз — при монтировании.
  useEffect(() => {
    if (selectedProduct && processedImageUrl) increment();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleNext() {
    reset();
    // Переходим обратно в каталог; фильтр "нет фото" сотрудник выбирает сам,
    // чтобы видеть актуальные товары без снимка.
    navigate('/');
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: BRAND.bg,
        display: 'flex',
        flexDirection: 'column',
        padding: 20,
      }}
    >
      <div
        style={{
          background: BRAND.surface,
          borderRadius: RADIUS.xl,
          boxShadow: SHADOW.card,
          padding: 24,
          textAlign: 'center',
          marginTop: 32,
        }}
      >
        <div
          aria-hidden="true"
          style={{
            width: 72,
            height: 72,
            borderRadius: '50%',
            background: BRAND.greenSoft,
            color: BRAND.greenDark,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 12px',
          }}
        >
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </div>
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: '0 0 6px' }}>Фото сохранено</h1>
        <p style={{ fontSize: 14, color: BRAND.muted, margin: '0 0 16px' }}>
          Товар появится в каталоге доставки.
        </p>

        {processedImageUrl && (
          <img
            src={processedImageUrl}
            alt={selectedProduct?.name || 'Обработанное фото'}
            style={{
              width: '100%',
              maxWidth: 240,
              aspectRatio: '1 / 1',
              objectFit: 'cover',
              borderRadius: RADIUS.lg,
              margin: '0 auto 14px',
            }}
          />
        )}

        <div
          style={{
            background: BRAND.greenSoft,
            color: BRAND.greenDark,
            borderRadius: RADIUS.md,
            padding: '8px 12px',
            fontSize: 13,
            fontWeight: 600,
            display: 'inline-block',
            marginBottom: 20,
          }}
        >
          Сегодня обработано: {count}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button
            type="button"
            onClick={handleNext}
            style={{
              padding: '16px',
              background: BRAND.green,
              color: BRAND.white,
              fontSize: 16,
              fontWeight: 600,
              borderRadius: RADIUS.lg,
            }}
          >
            Следующий товар
          </button>
          <button
            type="button"
            onClick={() => navigate('/form')}
            style={{
              padding: '14px',
              background: BRAND.surface,
              color: BRAND.text,
              border: `1px solid ${BRAND.border}`,
              fontSize: 15,
              fontWeight: 500,
              borderRadius: RADIUS.lg,
            }}
          >
            Открыть товар
          </button>
        </div>
      </div>
    </div>
  );
}
