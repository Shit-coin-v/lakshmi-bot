import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProductCard from '../../src/components/ProductCard.jsx';

const baseProduct = {
  id: 1,
  product_code: 'MLK-032',
  name: 'Молоко 3.2%',
  price: '89.00',
  category: 'Молочка',
  stock: 42,
  image_url: null,
};

describe('<ProductCard />', () => {
  it('показывает имя, SKU, цену и остаток', () => {
    render(<ProductCard product={baseProduct} onSelect={() => {}} apiBaseUrl="" />);

    expect(screen.getByText('Молоко 3.2%')).toBeInTheDocument();
    expect(screen.getByText('MLK-032')).toBeInTheDocument();
    expect(screen.getByText(/89\s*₽/)).toBeInTheDocument();
    expect(screen.getByText('ост. 42')).toBeInTheDocument();
  });

  it('показывает плейсхолдер "Нет фото", когда image_url пустой', () => {
    render(<ProductCard product={baseProduct} onSelect={() => {}} apiBaseUrl="" />);
    // Лейбл встречается дважды (бейдж и плейсхолдер фото) — оба валидны.
    const matches = screen.getAllByText('Нет фото');
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('строит абсолютный URL из image_url + apiBaseUrl', () => {
    render(
      <ProductCard
        product={{ ...baseProduct, image_url: '/media/products/x.png' }}
        onSelect={() => {}}
        apiBaseUrl="http://localhost:8000"
      />
    );

    const img = screen.getByAltText('Молоко 3.2%');
    expect(img).toHaveAttribute('src', 'http://localhost:8000/media/products/x.png');
  });

  it('не модифицирует абсолютный URL', () => {
    render(
      <ProductCard
        product={{ ...baseProduct, image_url: 'https://cdn.example.com/x.png' }}
        onSelect={() => {}}
        apiBaseUrl="http://localhost:8000"
      />
    );

    const img = screen.getByAltText('Молоко 3.2%');
    expect(img).toHaveAttribute('src', 'https://cdn.example.com/x.png');
  });

  it('вызывает onSelect с товаром при клике', async () => {
    const onSelect = vi.fn();
    render(<ProductCard product={baseProduct} onSelect={onSelect} apiBaseUrl="" />);

    await userEvent.click(screen.getByRole('button'));

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(baseProduct);
  });
});
