import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../main.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              // Logo Placeholder
              Container(
                height: 120,
                width: 120,
                decoration: BoxDecoration(
                  color: kLightGreen,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.eco, size: 60, color: kPrimaryGreen),
              ),
              const SizedBox(height: 30),

              // 👇 ВОТ ЗДЕСЬ ИЗМЕНЕНИЯ
              Text.rich(
                TextSpan(
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: Colors.black87, // Основной цвет (черный)
                  ),
                  children: const [
                    TextSpan(text: "Добро пожаловать в\n"), // Первая часть
                    TextSpan(
                      text: "Лакшми маркет", // Вторая часть
                      style: TextStyle(
                        color: kPrimaryGreen, // Делаем зеленым
                      ),
                    ),
                  ],
                ),
                textAlign: TextAlign.center,
              ),

              // -----------------------
              const Spacer(),

              // Register Button (Dark Green)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => context.push('/register-choice'),
                  child: const Text("Зарегистрироваться"),
                ),
              ),
              const SizedBox(height: 12),

              // Login Button (Light Green)
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => context.push('/login-choice'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: kLightGreen,
                    foregroundColor: Colors.black87,
                  ),
                  child: const Text("Войти"),
                ),
              ),
              const SizedBox(height: 12),

              // QR Login Button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => context.push('/qr-auth'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.grey.shade300,
                    foregroundColor: Colors.black87,
                  ),
                  child: const Text("Войти по QR-боту"),
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}
