import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { BRAND, RADIUS, SHADOW } from '../theme.js';
import { useSession } from '../context/SessionContext.jsx';

const TIPS = [
  'Держите товар по центру',
  'Больше света, избегайте бликов',
  'Не обрезайте упаковку',
  'Лучше нейтральный фон',
];

// Экран 2 — Камера или загрузка из галереи.
export default function CameraPage() {
  const navigate = useNavigate();
  const { selectedProduct, setSelectedFile } = useSession();
  const cameraInputRef = useRef(null);
  const galleryInputRef = useRef(null);

  // Если сотрудник попал на /camera без выбранного товара — отправляем его обратно.
  useEffect(() => {
    if (!selectedProduct) navigate('/', { replace: true });
  }, [selectedProduct, navigate]);

  if (!selectedProduct) return null;

  function handleFile(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    setSelectedFile(file);
    navigate('/preview');
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: BRAND.bg,
      }}
    >
      <header
        style={{
          padding: '12px 16px',
          background: BRAND.surface,
          borderBottom: `1px solid ${BRAND.border}`,
        }}
      >
        <button
          type="button"
          onClick={() => navigate(-1)}
          aria-label="Назад"
          style={{
            color: BRAND.muted,
            fontSize: 14,
            fontWeight: 500,
            marginBottom: 6,
          }}
        >
          ← Назад
        </button>
        <h2 style={{ fontSize: 17, fontWeight: 700, margin: '4px 0 2px' }}>
          {selectedProduct.name}
        </h2>
        <div style={{ fontSize: 12, color: BRAND.muted, display: 'flex', gap: 12 }}>
          {selectedProduct.product_code && (
            <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
              {selectedProduct.product_code}
            </span>
          )}
          {selectedProduct.category && <span>{selectedProduct.category}</span>}
        </div>
      </header>

      <div style={{ flex: 1, padding: 16, display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            background: BRAND.greenSoft,
            color: BRAND.greenDark,
            borderRadius: RADIUS.lg,
            padding: '12px 14px',
            fontSize: 13,
            fontWeight: 500,
            marginBottom: 14,
          }}
        >
          AI выправит фон — снимайте как есть.
        </div>

        <div
          aria-hidden="true"
          style={{
            position: 'relative',
            aspectRatio: '1 / 1',
            borderRadius: RADIUS.xl,
            border: `2px dashed ${BRAND.greenLight}`,
            background: BRAND.surface,
            marginBottom: 14,
            overflow: 'hidden',
          }}
        >
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            width="100%"
            height="100%"
            style={{ position: 'absolute', inset: 0 }}
          >
            <line x1="33.33" y1="0" x2="33.33" y2="100" stroke={BRAND.greenLight} strokeWidth="0.4" />
            <line x1="66.66" y1="0" x2="66.66" y2="100" stroke={BRAND.greenLight} strokeWidth="0.4" />
            <line x1="0" y1="33.33" x2="100" y2="33.33" stroke={BRAND.greenLight} strokeWidth="0.4" />
            <line x1="0" y1="66.66" x2="100" y2="66.66" stroke={BRAND.greenLight} strokeWidth="0.4" />
          </svg>
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: BRAND.muted,
              fontSize: 13,
              padding: 16,
              textAlign: 'center',
            }}
          >
            Кадр 1:1, товар по центру
          </div>
        </div>

        <ul
          style={{
            listStyle: 'none',
            padding: 0,
            margin: '0 0 16px',
            background: BRAND.surface,
            borderRadius: RADIUS.lg,
            boxShadow: SHADOW.card,
          }}
        >
          {TIPS.map((tip) => (
            <li
              key={tip}
              style={{
                padding: '10px 14px',
                fontSize: 13,
                color: BRAND.muted,
                borderBottom: `1px solid ${BRAND.border}`,
              }}
            >
              · {tip}
            </li>
          ))}
        </ul>

        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFile}
          style={{ display: 'none' }}
        />
        <input
          ref={galleryInputRef}
          type="file"
          accept="image/*"
          onChange={handleFile}
          style={{ display: 'none' }}
        />

        <button
          type="button"
          onClick={() => cameraInputRef.current?.click()}
          style={{
            padding: '16px',
            background: BRAND.green,
            color: BRAND.white,
            fontSize: 16,
            fontWeight: 600,
            borderRadius: RADIUS.lg,
            marginBottom: 8,
          }}
        >
          Сделать фото
        </button>
        <button
          type="button"
          onClick={() => galleryInputRef.current?.click()}
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
          Загрузить из галереи
        </button>
      </div>
    </div>
  );
}
