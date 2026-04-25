import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BRAND, RADIUS, SHADOW } from '../theme.js';
import { useSession } from '../context/SessionContext.jsx';
import { formatPrice, formatStock } from '../utils/format.js';

// Экран 4 — Карточка товара (read-only) с новым фото.
// В MVP без правок текстовых полей и без AI-описания.
export default function FormPage() {
  const navigate = useNavigate();
  const { selectedProduct, processedImageUrl } = useSession();

  useEffect(() => {
    if (!selectedProduct) navigate('/', { replace: true });
  }, [selectedProduct, navigate]);

  if (!selectedProduct) return null;

  const fields = [
    { label: 'ID', value: selectedProduct.id },
    { label: 'SKU', value: selectedProduct.product_code || '—' },
    { label: 'Категория', value: selectedProduct.category || '—' },
    { label: 'Цена', value: formatPrice(selectedProduct.price) },
    { label: 'Остаток', value: formatStock(selectedProduct.stock) },
  ];

  return (
    <div style={{ minHeight: '100vh', background: BRAND.bg, paddingBottom: 24 }}>
      <header
        style={{
          padding: '12px 16px',
          background: BRAND.surface,
          borderBottom: `1px solid ${BRAND.border}`,
        }}
      >
        <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Карточка товара</h2>
      </header>

      <div style={{ padding: 16 }}>
        {processedImageUrl && (
          <img
            src={processedImageUrl}
            alt={selectedProduct.name}
            style={{
              width: '100%',
              aspectRatio: '1 / 1',
              objectFit: 'cover',
              borderRadius: RADIUS.lg,
              boxShadow: SHADOW.card,
              marginBottom: 16,
            }}
          />
        )}

        <h3 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 12px' }}>
          {selectedProduct.name}
        </h3>

        <dl
          style={{
            background: BRAND.surface,
            borderRadius: RADIUS.lg,
            boxShadow: SHADOW.card,
            margin: 0,
            padding: '4px 0',
          }}
        >
          {fields.map((f) => (
            <div
              key={f.label}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                padding: '12px 16px',
                borderBottom: `1px solid ${BRAND.border}`,
              }}
            >
              <dt style={{ fontSize: 13, color: BRAND.muted }}>{f.label}</dt>
              <dd style={{ margin: 0, fontSize: 14, color: BRAND.text, fontWeight: 500 }}>
                {f.value}
              </dd>
            </div>
          ))}
        </dl>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
          <button
            type="button"
            onClick={() => navigate('/')}
            style={{
              padding: '14px',
              background: BRAND.green,
              color: BRAND.white,
              fontSize: 15,
              fontWeight: 600,
              borderRadius: RADIUS.lg,
            }}
          >
            К каталогу
          </button>
          <button
            type="button"
            onClick={() => navigate('/camera')}
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
            Переснять
          </button>
        </div>
      </div>
    </div>
  );
}
