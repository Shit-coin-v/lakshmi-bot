import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import PhotoStatusBadge from '../../src/components/PhotoStatusBadge.jsx';
import { PHOTO_STATUS } from '../../src/utils/photoStatus.js';

describe('<PhotoStatusBadge />', () => {
  it('рисует "Готово" для READY', () => {
    render(<PhotoStatusBadge status={PHOTO_STATUS.READY} />);
    expect(screen.getByText('Готово')).toBeInTheDocument();
  });

  it('рисует "Нет фото" для MISSING', () => {
    render(<PhotoStatusBadge status={PHOTO_STATUS.MISSING} />);
    expect(screen.getByText('Нет фото')).toBeInTheDocument();
  });

  it('по умолчанию считает товар без фото', () => {
    render(<PhotoStatusBadge status="unknown" />);
    expect(screen.getByText('Нет фото')).toBeInTheDocument();
  });
});
