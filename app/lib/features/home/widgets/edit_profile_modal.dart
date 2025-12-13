import 'package:flutter/material.dart';

class EditProfileModal extends StatefulWidget {
  final String title; // "Редактирование ФИО" или "Номер телефона"
  final String initialValue; // Текущее значение (например "Иванов...")
  final TextInputType inputType; // Текст или цифры
  final Function(String) onSave; // Функция, которая вернет новое значение

  const EditProfileModal({
    super.key,
    required this.title,
    required this.initialValue,
    required this.onSave,
    this.inputType = TextInputType.text,
  });

  @override
  State<EditProfileModal> createState() => _EditProfileModalState();
}

class _EditProfileModalState extends State<EditProfileModal> {
  late TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialValue);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Отступ для клавиатуры
    final bottomPadding = MediaQuery.of(context).viewInsets.bottom;

    return Container(
      padding: EdgeInsets.fromLTRB(20, 24, 20, 24 + bottomPadding),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                widget.title,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              IconButton(
                onPressed: () => Navigator.pop(context),
                icon: const Icon(Icons.close, color: Colors.grey),
              ),
            ],
          ),
          const SizedBox(height: 16),

          TextField(
            controller: _controller,
            keyboardType: widget.inputType,
            autofocus: true, // Сразу открываем клавиатуру
            decoration: InputDecoration(
              filled: true,
              fillColor: Colors.grey[100],
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
              // Добавляем иконку очистки
              suffixIcon: IconButton(
                icon: const Icon(Icons.clear, color: Colors.grey),
                onPressed: _controller.clear,
              ),
            ),
          ),

          const SizedBox(height: 24),

          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () {
                widget.onSave(_controller.text);
                Navigator.pop(context);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF4CAF50),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: const Text(
                'Сохранить',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Функция-помощник для вызова
void showEditProfileModal({
  required BuildContext context,
  required String title,
  required String initialValue,
  required Function(String) onSave,
  TextInputType inputType = TextInputType.text,
}) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true, // Важно для клавиатуры
    backgroundColor: Colors.transparent,
    builder: (context) => EditProfileModal(
      title: title,
      initialValue: initialValue,
      onSave: onSave,
      inputType: inputType,
    ),
  );
}
