import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class RegistrationChoiceScreen extends StatelessWidget {
  const RegistrationChoiceScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Регистрация"),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const SizedBox(height: 40),
            const Icon(Icons.person_add, size: 80, color: Color(0xFF4CAF50)),
            const SizedBox(height: 24),
            const Text(
              "Выберите способ регистрации",
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
                onPressed: () => context.push('/register'),
                icon: const Icon(Icons.email),
                label: const Text("Через Email"),
              ),
            ),
            const SizedBox(height: 16),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: () => context.push('/register-telegram'),
                icon: const Icon(Icons.telegram, color: Color(0xFF0088cc)),
                label: const Text("Через Telegram-бот"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
