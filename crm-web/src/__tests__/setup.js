import '@testing-library/jest-dom';

// Заглушка fetch для тестов, не использующих MSW (большинство сейчас).
// Возвращает 401 на любой запрос — AuthProvider увидит unauth, тесты с
// прямым импортом фикстур увидят /login или Splash. Полная переработка
// под MSW — Task 28.
if (!globalThis.fetch || !globalThis.fetch._isStub) {
  const stub = async () => new Response(null, { status: 401 });
  stub._isStub = true;
  globalThis.fetch = stub;
}
