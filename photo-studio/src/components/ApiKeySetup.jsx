import { useState } from 'react';
import { BRAND, RADIUS, SHADOW } from '../theme.js';

// Полноэкранный экран первичной настройки X-Api-Key.
// Показывается, пока в localStorage нет валидного ключа.
export default function ApiKeySetup({ onSave }) {
  const [value, setValue] = useState('');

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    onSave(trimmed);
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
        background: BRAND.bg,
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          width: '100%',
          maxWidth: 380,
          background: BRAND.surface,
          borderRadius: RADIUS.xl,
          boxShadow: SHADOW.card,
          padding: 24,
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: RADIUS.lg,
            background: BRAND.greenSoft,
            color: BRAND.greenDark,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 28,
            fontWeight: 700,
            margin: '0 auto 12px',
          }}
        >
          L
        </div>
        <h1 style={{ fontSize: 20, fontWeight: 700, textAlign: 'center', margin: '0 0 8px' }}>
          Lakshmi Photo Studio
        </h1>
        <p style={{ fontSize: 14, color: BRAND.muted, textAlign: 'center', margin: '0 0 20px' }}>
          Введите ключ доступа сотрудника. Ключ выдаёт администратор магазина.
        </p>
        <label
          htmlFor="api-key"
          style={{ display: 'block', fontSize: 13, color: BRAND.text, marginBottom: 6 }}
        >
          X-Api-Key
        </label>
        <input
          id="api-key"
          type="password"
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Вставьте ключ"
          style={{
            width: '100%',
            padding: '12px 14px',
            fontSize: 15,
            border: `1px solid ${BRAND.border}`,
            borderRadius: RADIUS.md,
            outline: 'none',
            marginBottom: 16,
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          }}
        />
        <button
          type="submit"
          disabled={!value.trim()}
          style={{
            width: '100%',
            padding: '14px',
            background: BRAND.green,
            color: BRAND.white,
            fontSize: 15,
            fontWeight: 600,
            borderRadius: RADIUS.md,
          }}
        >
          Сохранить ключ
        </button>
      </form>
    </div>
  );
}
