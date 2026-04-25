import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ApiKeySetup from '../../src/components/ApiKeySetup.jsx';

describe('<ApiKeySetup />', () => {
  it('блокирует кнопку при пустом ключе', () => {
    render(<ApiKeySetup onSave={() => {}} />);
    expect(screen.getByRole('button', { name: /Сохранить ключ/ })).toBeDisabled();
  });

  it('отдаёт обрезанный ключ через onSave при сабмите', async () => {
    const onSave = vi.fn();
    render(<ApiKeySetup onSave={onSave} />);

    await userEvent.type(screen.getByLabelText('X-Api-Key'), '  abcd1234  ');
    await userEvent.click(screen.getByRole('button', { name: /Сохранить ключ/ }));

    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith('abcd1234');
  });

  it('не вызывает onSave если введены только пробелы', async () => {
    const onSave = vi.fn();
    render(<ApiKeySetup onSave={onSave} />);

    await userEvent.type(screen.getByLabelText('X-Api-Key'), '   ');
    // Кнопка остаётся disabled — submit не пройдёт.
    expect(screen.getByRole('button', { name: /Сохранить ключ/ })).toBeDisabled();
    expect(onSave).not.toHaveBeenCalled();
  });
});
