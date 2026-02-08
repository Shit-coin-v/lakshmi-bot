import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class TelegramLinkChoiceScreen extends StatelessWidget {
  const TelegramLinkChoiceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Привязка Telegram"),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const SizedBox(height: 40),
            const Icon(Icons.telegram, size: 80, color: Color(0xFF0088cc)),
            const SizedBox(height: 24),
            const Text(
              "У вас есть аккаунт\nв нашем Telegram-боте?",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            const Text(
              "Если да — отсканируйте QR-код из бота,\nчтобы перенести бонусы и историю заказов.",
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 40),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: () => context.push('/link-telegram-scan'),
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text("Да, отсканировать QR"),
              ),
            ),
            const SizedBox(height: 16),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: () => context.push('/generate-qr'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.grey.shade300,
                  foregroundColor: Colors.black87,
                ),
                child: const Text("Нет, продолжить без Telegram"),
              ),
            ),
            const SizedBox(height: 16),

            TextButton(
              onPressed: () => context.go('/home'),
              child: const Text(
                "Пропустить",
                style: TextStyle(color: Colors.grey),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
