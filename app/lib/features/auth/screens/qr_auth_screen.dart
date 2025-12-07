import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';

class QrAuthScreen extends ConsumerStatefulWidget {
  const QrAuthScreen({super.key});

  @override
  ConsumerState<QrAuthScreen> createState() => _QrAuthScreenState();
}

class _QrAuthScreenState extends ConsumerState<QrAuthScreen> {
  bool _isLoading = false;
  final TextEditingController _debugController = TextEditingController(
    text: "12345",
  ); // Для теста

  Future<void> _handleLogin() async {
    setState(() => _isLoading = true);

    // ВРЕМЕННО: Берем текст из поля ввода, так как сканер на Linux сложен
    // Когда будет телефон - сюда вернем image_picker
    final qrCodeString = _debugController.text;

    try {
      // Вызываем наш провайдер
      await ref.read(authProvider.notifier).login(qrCodeString);

      if (mounted) {
        // Если успеха - идем на главную
        context.go('/home');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Ошибка входа: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Вход по QR")),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.qr_code_scanner, size: 100, color: Colors.green),
            const SizedBox(height: 20),
            const Text(
              "Введите QR-код вручную (Тест для Linux)",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 20),

            // Поле для ручного ввода (для тестов на компе)
            TextField(
              controller: _debugController,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: 'Код из QR',
              ),
            ),
            const SizedBox(height: 20),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _handleLogin,
                style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                child: _isLoading
                    ? const CircularProgressIndicator(color: Colors.white)
                    : const Text(
                        "Войти",
                        style: TextStyle(color: Colors.white),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
