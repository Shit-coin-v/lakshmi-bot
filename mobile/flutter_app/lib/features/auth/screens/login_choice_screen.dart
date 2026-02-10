import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class LoginChoiceScreen extends StatelessWidget {
  const LoginChoiceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Вход"),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const SizedBox(height: 40),
            const Icon(Icons.login, size: 80, color: Color(0xFF4CAF50)),
            const SizedBox(height: 24),
            const Text(
              "Выберите способ входа",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),
            const Text(
              "Через Email или Telegram-бот",
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 40),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: () => context.push('/login'),
                icon: const Icon(Icons.email),
                label: const Text("Через Email"),
              ),
            ),
            const SizedBox(height: 16),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: () => context.push('/qr-auth'),
                icon: const Icon(Icons.qr_code, color: Color(0xFF0088cc)),
                label: const Text("Через Telegram QR"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
