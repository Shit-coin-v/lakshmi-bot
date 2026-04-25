// Глобальный setup vitest: расширяет matchers + чистит DOM между тестами.
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
});

beforeEach(() => {
  // Сбрасываем localStorage между тестами, чтобы X-Api-Key и счётчик дня
  // не текли из соседнего теста.
  localStorage.clear();
});
