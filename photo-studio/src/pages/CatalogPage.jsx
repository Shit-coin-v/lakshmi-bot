import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BRAND, RADIUS } from '../theme.js';
import SearchBar from '../components/SearchBar.jsx';
import CategoryFilter from '../components/CategoryFilter.jsx';
import PhotoStatusFilter from '../components/PhotoStatusFilter.jsx';
import ProductCard from '../components/ProductCard.jsx';
import ProgressDay from '../components/ProgressDay.jsx';
import Spinner from '../components/Spinner.jsx';
import useProducts from '../hooks/useProducts.js';
import useCategories from '../hooks/useCategories.js';
import useDailyProgress from '../hooks/useDailyProgress.js';
import useApiKey from '../hooks/useApiKey.js';
import { useSession } from '../context/SessionContext.jsx';
import { getPhotoStatus, PHOTO_STATUS } from '../utils/photoStatus.js';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

// Экран 1 — Каталог. Точка входа сотрудника.
export default function CatalogPage() {
  const navigate = useNavigate();
  const { setSelectedProduct } = useSession();
  const { count: dailyDone } = useDailyProgress();
  const { clear: clearApiKey } = useApiKey();

  function handleChangeKey() {
    if (window.confirm('Сменить ключ доступа? Текущая сессия будет сброшена.')) {
      clearApiKey();
      window.location.reload();
    }
  }

  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [categoryId, setCategoryId] = useState(null);
  const [photoStatus, setPhotoStatus] = useState('all');

  // Дебаунс поискового ввода — backend получает запрос только после паузы.
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchInput.trim()), 350);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { categories } = useCategories();
  const { items, total, loading, error, loadMore, reload } = useProducts({
    search: debouncedSearch,
    categoryId,
  });

  // Локальная фильтрация: статус фото и дополнительный поиск по SKU.
  const filtered = useMemo(() => {
    let out = items;
    if (photoStatus !== 'all') {
      out = out.filter((p) => getPhotoStatus(p) === photoStatus);
    }
    const q = searchInput.trim().toLowerCase();
    if (q) {
      out = out.filter(
        (p) =>
          (p.product_code || '').toLowerCase().includes(q) ||
          (p.name || '').toLowerCase().includes(q)
      );
    }
    return out;
  }, [items, photoStatus, searchInput]);

  const totalMissing = useMemo(
    () => items.filter((p) => getPhotoStatus(p) === PHOTO_STATUS.MISSING).length,
    [items]
  );

  function handleSelect(product) {
    setSelectedProduct(product);
    navigate('/camera');
  }

  return (
    <div style={{ padding: '12px 16px 80px' }}>
      <header
        style={{
          marginBottom: 12,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 8,
        }}
      >
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: '8px 0 4px' }}>Каталог товаров</h1>
          <p style={{ fontSize: 13, color: BRAND.muted, margin: 0 }}>
            {loading && items.length === 0
              ? 'Загружаем…'
              : `Показано: ${filtered.length}${total ? ` из ${total}` : ''}`}
          </p>
        </div>
        <button
          type="button"
          onClick={handleChangeKey}
          aria-label="Сменить ключ доступа"
          style={{
            marginTop: 8,
            padding: '6px 10px',
            background: BRAND.surface,
            color: BRAND.muted,
            border: `1px solid ${BRAND.border}`,
            borderRadius: RADIUS.md,
            fontSize: 12,
            fontWeight: 500,
            whiteSpace: 'nowrap',
          }}
        >
          Сменить ключ
        </button>
      </header>

      <ProgressDay done={dailyDone} totalMissing={totalMissing} />

      <SearchBar value={searchInput} onChange={setSearchInput} />

      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <CategoryFilter categories={categories} value={categoryId} onChange={setCategoryId} />
      </div>

      <div style={{ marginBottom: 14 }}>
        <PhotoStatusFilter value={photoStatus} onChange={setPhotoStatus} />
      </div>

      {error && (
        <div
          style={{
            padding: 12,
            border: `1px solid ${BRAND.danger}`,
            borderRadius: RADIUS.md,
            color: BRAND.danger,
            fontSize: 13,
            marginBottom: 12,
          }}
        >
          Не удалось загрузить каталог.{' '}
          <button
            type="button"
            onClick={reload}
            style={{ color: BRAND.danger, textDecoration: 'underline', fontWeight: 600 }}
          >
            Повторить
          </button>
        </div>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 10,
        }}
      >
        {filtered.map((p) => (
          <ProductCard key={p.id} product={p} onSelect={handleSelect} apiBaseUrl={API_BASE} />
        ))}
      </div>

      {!loading && filtered.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            color: BRAND.muted,
            fontSize: 14,
            padding: '40px 12px',
          }}
        >
          Ничего не найдено по выбранным фильтрам.
        </div>
      )}

      {items.length < total && (
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <button
            type="button"
            onClick={loadMore}
            disabled={loading}
            style={{
              padding: '10px 20px',
              background: BRAND.surface,
              color: BRAND.text,
              border: `1px solid ${BRAND.border}`,
              borderRadius: RADIUS.md,
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {loading ? <Spinner size={16} /> : 'Загрузить ещё'}
          </button>
        </div>
      )}
    </div>
  );
}
