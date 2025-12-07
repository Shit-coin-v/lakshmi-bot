import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../../main.dart';

class RegistrationScreen extends StatefulWidget {
  const RegistrationScreen({super.key});

  @override
  State<RegistrationScreen> createState() => _RegistrationScreenState();
}

class _RegistrationScreenState extends State<RegistrationScreen> {
  bool _termsAccepted = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Создать аккаунт", style: TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text("Введите ваши данные, чтобы начать.", textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 30),
            
            _buildLabel("Полное имя"),
            const TextField(decoration: InputDecoration(hintText: "Введите ваше полное имя")),
            
            const SizedBox(height: 16),
            _buildLabel("Электронная почта"),
            const TextField(decoration: InputDecoration(hintText: "Введите вашу почту")),

            const SizedBox(height: 16),
            _buildLabel("Пароль"),
            const TextField(obscureText: true, decoration: InputDecoration(hintText: "Введите ваш пароль", suffixIcon: Icon(Icons.visibility_off))),

            const SizedBox(height: 16),
            _buildLabel("Подтвердите пароль"),
            const TextField(obscureText: true, decoration: InputDecoration(hintText: "Подтвердите ваш пароль", suffixIcon: Icon(Icons.visibility_off))),

            const SizedBox(height: 20),
            Row(
              children: [
                Checkbox(
                  value: _termsAccepted, 
                  activeColor: kPrimaryGreen,
                  onChanged: (v) => setState(() => _termsAccepted = v!),
                ),
                const Expanded(
                  child: Text.rich(
                    TextSpan(
                      text: "Создавая аккаунт, вы соглашаетесь с нашими ",
                      style: TextStyle(fontSize: 12),
                      children: [
                         TextSpan(text: "Условиями обслуживания", style: TextStyle(color: kPrimaryGreen, fontWeight: FontWeight.bold)),
                         TextSpan(text: " и "),
                         TextSpan(text: "Политикой конфиденциальности", style: TextStyle(color: kPrimaryGreen, fontWeight: FontWeight.bold)),
                         TextSpan(text: "."),
                      ]
                    )
                  ),
                )
              ],
            ),

            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () => context.go('/home'),
              child: const Text("Создать аккаунт"),
            ),

            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Text("Уже есть аккаунт? "),
                GestureDetector(
                  onTap: () => context.go('/login'),
                  child: const Text("Войти", style: TextStyle(color: kPrimaryGreen, fontWeight: FontWeight.bold)),
                )
              ],
            )
          ],
        ),
      ),
    );
  }

  Widget _buildLabel(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8.0),
      child: Text(text, style: const TextStyle(fontWeight: FontWeight.w500)),
    );
  }
}