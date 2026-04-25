import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BRAND, RADIUS, SHADOW } from '../theme.js';
import Spinner from '../components/Spinner.jsx';
import { useSession } from '../context/SessionContext.jsx';
import { describeUploadError, uploadProductImage } from '../api/products.js';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const STAGES = [
  { id: 'upload', label: 'Загрузка фото' },
  { id: 'process', label: 'AI-обработка' },
  { id: 'done', label: 'Готово' },
];

// Экран 3 — Превью RAW + запуск обработки + до/после.
export default function PreviewPage() {
  const navigate = useNavigate();
  const { selectedProduct, selectedFile, setProcessedImageUrl } = useSession();
  const [stage, setStage] = useState('idle'); // idle | upload | process | done | error
  const [error, setError] = useState(null);
  const [processedUrl, setProcessedUrl] = useState(null);

  // Защита от прямого захода на /preview без выбранных данных.
  useEffect(() => {
    if (!selectedProduct) navigate('/', { replace: true });
    else if (!selectedFile) navigate('/camera', { replace: true });
  }, [selectedProduct, selectedFile, navigate]);

  // RAW → blob URL для предпросмотра.
  const rawUrl = useMemo(() => {
    if (!selectedFile) return null;
    return URL.createObjectURL(selectedFile);
  }, [selectedFile]);

  useEffect(() => {
    return () => {
      if (rawUrl) URL.revokeObjectURL(rawUrl);
    };
  }, [rawUrl]);

  if (!selectedProduct || !selectedFile) return null;

  async function handleAccept() {
    setError(null);
    setStage('upload');
    try {
      const result = await uploadProductImage(selectedProduct.id, selectedFile, (e) => {
        if (e?.loaded && e?.total && e.loaded >= e.total) {
          setStage('process');
        }
      });
      const url = result.image_url
        ? result.image_url.startsWith('http')
          ? result.image_url
          : `${API_BASE}${result.image_url}`
        : null;
      setProcessedUrl(url);
      setProcessedImageUrl(url);
      setStage('done');
      // Небольшая пауза, чтобы сотрудник увидел "до/после".
      setTimeout(() => navigate('/success'), 1200);
    } catch (err) {
      setError(describeUploadError(err));
      setStage('error');
    }
  }

  const isBusy = stage === 'upload' || stage === 'process';

  return (
    <div style={{ minHeight: '100vh', background: BRAND.bg, paddingBottom: 24 }}>
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
          disabled={isBusy}
          aria-label="Назад"
          style={{ color: BRAND.muted, fontSize: 14, fontWeight: 500 }}
        >
          ← Назад
        </button>
        <h2 style={{ fontSize: 17, fontWeight: 700, margin: '4px 0 2px' }}>
          {selectedProduct.name}
        </h2>
        {selectedProduct.product_code && (
          <div
            style={{
              fontSize: 12,
              color: BRAND.muted,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            }}
          >
            {selectedProduct.product_code}
          </div>
        )}
      </header>

      <div style={{ padding: 16 }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: stage === 'done' && processedUrl ? '1fr 1fr' : '1fr',
            gap: 10,
            marginBottom: 16,
          }}
        >
          <figure style={{ margin: 0 }}>
            <figcaption
              style={{ fontSize: 12, color: BRAND.muted, marginBottom: 6, textAlign: 'center' }}
            >
              Исходное
            </figcaption>
            <img
              src={rawUrl}
              alt="Исходное фото"
              style={{
                width: '100%',
                aspectRatio: '1 / 1',
                objectFit: 'cover',
                borderRadius: RADIUS.lg,
                boxShadow: SHADOW.card,
              }}
            />
          </figure>
          {stage === 'done' && processedUrl && (
            <figure style={{ margin: 0 }}>
              <figcaption
                style={{
                  fontSize: 12,
                  color: BRAND.greenDark,
                  marginBottom: 6,
                  textAlign: 'center',
                  fontWeight: 600,
                }}
              >
                После AI
              </figcaption>
              <img
                src={processedUrl}
                alt="Обработанное фото"
                style={{
                  width: '100%',
                  aspectRatio: '1 / 1',
                  objectFit: 'cover',
                  borderRadius: RADIUS.lg,
                  boxShadow: SHADOW.card,
                }}
              />
            </figure>
          )}
        </div>

        {(isBusy || stage === 'done') && (
          <ol
            style={{
              listStyle: 'none',
              padding: 14,
              margin: '0 0 16px',
              background: BRAND.surface,
              borderRadius: RADIUS.lg,
              boxShadow: SHADOW.card,
              fontSize: 13,
            }}
          >
            {STAGES.map((s) => {
              const reached =
                (s.id === 'upload' && (stage === 'upload' || stage === 'process' || stage === 'done')) ||
                (s.id === 'process' && (stage === 'process' || stage === 'done')) ||
                (s.id === 'done' && stage === 'done');
              const active =
                (s.id === 'upload' && stage === 'upload') ||
                (s.id === 'process' && stage === 'process') ||
                (s.id === 'done' && stage === 'done');
              return (
                <li
                  key={s.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '6px 0',
                    color: reached ? BRAND.text : BRAND.muted,
                    fontWeight: active ? 600 : 400,
                  }}
                >
                  <span
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: '50%',
                      background: reached ? BRAND.green : BRAND.greenSoft,
                      color: BRAND.white,
                      fontSize: 11,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {reached ? '✓' : ''}
                  </span>
                  {s.label}
                  {active && stage !== 'done' && <Spinner size={14} />}
                </li>
              );
            })}
          </ol>
        )}

        {error && (
          <div
            role="alert"
            style={{
              padding: 12,
              border: `1px solid ${BRAND.danger}`,
              borderRadius: RADIUS.md,
              color: BRAND.danger,
              fontSize: 13,
              marginBottom: 16,
              background: BRAND.surface,
            }}
          >
            {error}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <button
            type="button"
            onClick={handleAccept}
            disabled={isBusy || stage === 'done'}
            style={{
              padding: '16px',
              background: BRAND.green,
              color: BRAND.white,
              fontSize: 16,
              fontWeight: 600,
              borderRadius: RADIUS.lg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
            }}
          >
            {isBusy ? <Spinner size={18} color={BRAND.white} /> : null}
            {stage === 'done' ? 'Готово' : isBusy ? 'Обработка…' : 'Принять'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/camera')}
            disabled={isBusy}
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
