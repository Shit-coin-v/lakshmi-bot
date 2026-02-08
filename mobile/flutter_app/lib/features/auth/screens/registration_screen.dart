import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../main.dart';
import '../providers/auth_provider.dart';

class RegistrationScreen extends ConsumerStatefulWidget {
  const RegistrationScreen({super.key});

  @override
  ConsumerState<RegistrationScreen> createState() => _RegistrationScreenState();
}

class _RegistrationScreenState extends ConsumerState<RegistrationScreen> {
  final _fullNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _termsAccepted = false;
  bool _loading = false;
  String? _error;
  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  @override
  void dispose() {
    _fullNameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    final fullName = _fullNameController.text.trim();
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final confirmPassword = _confirmPasswordController.text;

    if (fullName.isEmpty || email.isEmpty || password.isEmpty) {
      setState(() => _error = 'Заполните все обязательные поля');
      return;
    }

    if (password != confirmPassword) {
      setState(() => _error = 'Пароли не совпадают');
      return;
    }

    if (password.length < 8) {
      setState(() => _error = 'Пароль должен быть не менее 8 символов');
      return;
    }

    if (!_termsAccepted) {
      setState(() => _error = 'Необходимо принять условия');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      await ref.read(authProvider.notifier).register(
            email: email,
            password: password,
            fullName: fullName,
          );
      if (mounted) {
        context.go('/verify-email', extra: email);
      }
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

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

            if (_error != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(_error!, style: TextStyle(color: Colors.red.shade700)),
              ),
              const SizedBox(height: 16),
            ],

            _buildLabel("Полное имя"),
            TextField(
              controller: _fullNameController,
              decoration: const InputDecoration(hintText: "Введите ваше полное имя"),
            ),

            const SizedBox(height: 16),
            _buildLabel("Электронная почта"),
            TextField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(hintText: "Введите вашу почту"),
            ),

            const SizedBox(height: 16),
            _buildLabel("Пароль"),
            TextField(
              controller: _passwordController,
              obscureText: _obscurePassword,
              decoration: InputDecoration(
                hintText: "Минимум 8 символов",
                suffixIcon: IconButton(
                  icon: Icon(_obscurePassword ? Icons.visibility_off : Icons.visibility),
                  onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                ),
              ),
            ),

            const SizedBox(height: 16),
            _buildLabel("Подтвердите пароль"),
            TextField(
              controller: _confirmPasswordController,
              obscureText: _obscureConfirm,
              decoration: InputDecoration(
                hintText: "Подтвердите ваш пароль",
                suffixIcon: IconButton(
                  icon: Icon(_obscureConfirm ? Icons.visibility_off : Icons.visibility),
                  onPressed: () => setState(() => _obscureConfirm = !_obscureConfirm),
                ),
              ),
            ),

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
                      ],
                    ),
                  ),
                )
              ],
            ),

            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _loading ? null : _register,
              child: _loading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text("Создать аккаунт"),
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
