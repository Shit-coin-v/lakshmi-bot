import { BRAND, RADIUS } from '../theme.js';
import { PHOTO_STATUS, getPhotoStatusLabel } from '../utils/photoStatus.js';

// Бейдж статуса фото товара (готово / нет фото).
const COLORS = {
  [PHOTO_STATUS.READY]: { bg: BRAND.greenSoft, fg: BRAND.greenDark },
  [PHOTO_STATUS.MISSING]: { bg: '#FDECEA', fg: BRAND.danger },
};

export default function PhotoStatusBadge({ status }) {
  const palette = COLORS[status] || COLORS[PHOTO_STATUS.MISSING];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 8px',
        borderRadius: RADIUS.sm,
        background: palette.bg,
        color: palette.fg,
        fontSize: 11,
        fontWeight: 600,
        lineHeight: '16px',
      }}
    >
      {getPhotoStatusLabel(status)}
    </span>
  );
}
