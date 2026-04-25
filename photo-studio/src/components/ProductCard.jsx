import { BRAND, RADIUS, SHADOW } from '../theme.js';
import PhotoStatusBadge from './PhotoStatusBadge.jsx';
import { formatPrice, formatStock } from '../utils/format.js';
import { getPhotoStatus } from '../utils/photoStatus.js';

// Карточка товара в каталоге. Минимум информации, крупная кнопка по всей
// площади — оптимизировано под палец на мобильном экране.
export default function ProductCard({ product, onSelect, apiBaseUrl }) {
  const status = getPhotoStatus(product);
  const imageUrl = product.image_url
    ? product.image_url.startsWith('http')
      ? product.image_url
      : `${apiBaseUrl}${product.image_url}`
    : null;

  return (
    <button
      type="button"
      onClick={() => onSelect(product)}
      style={{
        display: 'flex',
        flexDirection: 'column',
        textAlign: 'left',
        background: BRAND.surface,
        borderRadius: RADIUS.lg,
        boxShadow: SHADOW.card,
        overflow: 'hidden',
        width: '100%',
        border: 'none',
      }}
    >
      <div
        style={{
          aspectRatio: '1 / 1',
          width: '100%',
          background: BRAND.greenSoft,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={product.name}
            loading="lazy"
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <div
            aria-label="Нет фото"
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: BRAND.muted,
              fontSize: 12,
            }}
          >
            Нет фото
          </div>
        )}
        <div style={{ position: 'absolute', top: 8, left: 8 }}>
          <PhotoStatusBadge status={status} />
        </div>
      </div>
      <div style={{ padding: '10px 12px 12px' }}>
        <div
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: BRAND.text,
            display: '-webkit-box',
            WebkitLineClamp: 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
            minHeight: 36,
          }}
        >
          {product.name}
        </div>
        {product.product_code && (
          <div
            style={{
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
              fontSize: 11,
              color: BRAND.muted,
              marginTop: 4,
            }}
          >
            {product.product_code}
          </div>
        )}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            marginTop: 6,
          }}
        >
          <span style={{ fontSize: 15, fontWeight: 700, color: BRAND.text }}>
            {formatPrice(product.price)}
          </span>
          <span style={{ fontSize: 12, color: BRAND.muted }}>
            ост. {formatStock(product.stock)}
          </span>
        </div>
      </div>
    </button>
  );
}
