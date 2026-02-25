import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:google_mlkit_barcode_scanning/google_mlkit_barcode_scanning.dart';
import '../services/auth_service.dart';

class LinkTelegramScanScreen extends ConsumerStatefulWidget {
  const LinkTelegramScanScreen({super.key});

  @override
  ConsumerState<LinkTelegramScanScreen> createState() =>
      _LinkTelegramScanScreenState();
}

class _LinkTelegramScanScreenState
    extends ConsumerState<LinkTelegramScanScreen> {
  bool _isLoading = false;
  final ImagePicker _picker = ImagePicker();
  final TextEditingController _codeController = TextEditingController();

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _linkByTelegramId(String rawValue) async {
    final telegramId = int.tryParse(rawValue.trim());
    if (telegramId == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('QR-код не содержит Telegram ID'),
            backgroundColor: Colors.red,
          ),
        );
      }
      return;
    }

    setState(() => _isLoading = true);
    try {
      final result =
          await ref.read(authServiceProvider).linkTelegramByQr(telegramId);

      if (mounted) {
        final bonuses = result['bonuses'] ?? '0';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Telegram привязан! Бонусы: $bonuses'),
            backgroundColor: Colors.green,
          ),
        );
        context.go('/home');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content:
                Text(e.toString().replaceFirst('Exception: ', '')),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _pickQrFromGallery() async {
    if (_isLoading) return;

    final XFile? file = await _picker.pickImage(source: ImageSource.gallery);
    if (file == null) return;

    setState(() => _isLoading = true);

    final scanner = BarcodeScanner(formats: [BarcodeFormat.qrCode]);
    try {
      final inputImage = InputImage.fromFilePath(file.path);
      final barcodes = await scanner.processImage(inputImage);

      final String? raw = barcodes
          .map((b) => b.rawValue)
          .whereType<String>()
          .map((v) => v.trim())
          .where((v) => v.isNotEmpty)
          .firstOrNull;

      if (raw == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('QR-код на фото не найден'),
              backgroundColor: Colors.red,
            ),
          );
        }
        return;
      }

      _codeController.text = raw;

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('QR распознан'),
            backgroundColor: Colors.green,
          ),
        );
      }

      await _linkByTelegramId(raw);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Ошибка распознавания QR: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      await scanner.close();
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _handleManualLink() async {
    final code = _codeController.text.trim();
    if (code.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Введите Telegram ID из QR'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    await _linkByTelegramId(code);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Сканировать QR бота"),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const SizedBox(height: 20),
            const Icon(Icons.qr_code_scanner, size: 80, color: Colors.green),
            const SizedBox(height: 16),
            const Text(
              "Откройте QR-код в Telegram-боте\nи выберите его из галереи",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 24),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton.icon(
                onPressed: _isLoading ? null : _pickQrFromGallery,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.black87,
                ),
                icon: const Icon(Icons.photo_library, color: Colors.white),
                label: _isLoading
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(color: Colors.white),
                      )
                    : const Text(
                        "Выбрать QR из галереи",
                        style: TextStyle(color: Colors.white),
                      ),
              ),
            ),

            const SizedBox(height: 24),

            TextField(
              controller: _codeController,
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                labelText: 'Введите Telegram ID из QR',
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 12),

            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _handleManualLink,
                style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                child: _isLoading
                    ? const CircularProgressIndicator(color: Colors.white)
                    : const Text(
                        "Привязать",
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
