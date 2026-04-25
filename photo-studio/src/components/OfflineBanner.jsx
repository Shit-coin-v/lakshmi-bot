import { BRAND } from '../theme.js';

// Баннер «Нет сети». Не блокирует UI, но предупреждает пользователя,
// что отправка фото сейчас невозможна.
export default function OfflineBanner({ visible }) {
  if (!visible) return null;
  return (
    <div
      role="status"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 50,
        background: BRAND.amber,
        color: BRAND.text,
        padding: '8px 14px',
        fontSize: 13,
        fontWeight: 600,
        textAlign: 'center',
      }}
    >
      Нет сети — фото можно сделать, отправка возобновится после подключения.
    </div>
  );
}
