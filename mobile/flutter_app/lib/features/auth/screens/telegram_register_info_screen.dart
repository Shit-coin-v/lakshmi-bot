import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/api_client.dart';

class TelegramRegisterInfoScreen extends StatelessWidget {
  const TelegramRegisterInfoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Регистрация через Telegram"),
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
              "Как зарегистрироваться через бот",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 24),

            _buildStep(1, "Откройте нашего Telegram-бота"),
            const SizedBox(height: 12),
            _buildStep(2, "Нажмите /start и пройдите регистрацию"),
            const SizedBox(height: 12),
            _buildStep(3, 'Нажмите «Показать QR-код» в боте'),
            const SizedBox(height: 12),
            _buildStep(4, "Сохраните QR-код в галерею телефона"),
            const SizedBox(height: 12),
            _buildStep(5, "Вернитесь в приложение и загрузите QR"),

            const SizedBox(height: 40),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: () => launchUrl(
                  Uri.parse('https://t.me/${ApiClient.botUsername}'),
                  mode: LaunchMode.externalApplication,
                ),
                icon: const Icon(Icons.open_in_new),
                label: const Text("Открыть Telegram-бот"),
              ),
            ),
            const SizedBox(height: 16),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: () => context.push('/qr-auth'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.grey.shade300,
                  foregroundColor: Colors.black87,
                ),
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text("У меня есть QR — загрузить"),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static Widget _buildStep(int number, String text) {
    return Row(
      children: [
        CircleAvatar(
          radius: 14,
          child: Text('$number'),
        ),
        const SizedBox(width: 12),
        Expanded(child: Text(text)),
      ],
    );
  }
}
