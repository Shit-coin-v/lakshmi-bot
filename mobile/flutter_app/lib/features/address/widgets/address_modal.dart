import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';
import '../models/address_model.dart';
import '../providers/address_provider.dart';

class AddressModal extends ConsumerStatefulWidget {
  final AddressModel? addressToEdit;

  const AddressModal({super.key, this.addressToEdit});

  @override
  ConsumerState<AddressModal> createState() => _AddressModalState();
}

class _AddressModalState extends ConsumerState<AddressModal> {
  late TextEditingController _addressController;
  late TextEditingController _aptController;
  late TextEditingController _entranceController;
  late TextEditingController _floorController;
  late TextEditingController _intercomController;
  late TextEditingController _commentController;

  String _selectedLabel = 'Дом';

  @override
  void initState() {
    super.initState();
    final a = widget.addressToEdit;
    _addressController = TextEditingController(text: a?.fullAddress ?? '');
    _aptController = TextEditingController(text: a?.apartment ?? '');
    _entranceController = TextEditingController(text: a?.entrance ?? '');
    _floorController = TextEditingController(text: a?.floor ?? '');
    _intercomController = TextEditingController(text: a?.intercom ?? '');
    _commentController = TextEditingController(text: a?.comment ?? '');

    if (a != null) _selectedLabel = a.label;
  }

  @override
  Widget build(BuildContext context) {
    final keyboardHeight = MediaQuery.of(context).viewInsets.bottom;

    return Material(
      type: MaterialType.transparency,
      child: Container(
        padding: EdgeInsets.fromLTRB(16, 24, 16, 24 + keyboardHeight),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.addressToEdit == null ? 'Новый адрес' : 'Редактирование',
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 20),

              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    _CategoryChip(
                      label: 'Дом',
                      icon: Icons.home,
                      isSelected: _selectedLabel == 'Дом',
                      onTap: () => setState(() => _selectedLabel = 'Дом'),
                    ),
                    const SizedBox(width: 10),
                    _CategoryChip(
                      label: 'Работа',
                      icon: Icons.work,
                      isSelected: _selectedLabel == 'Работа',
                      onTap: () => setState(() => _selectedLabel = 'Работа'),
                    ),
                    const SizedBox(width: 10),
                    _CategoryChip(
                      label: 'Другое',
                      icon: Icons.location_on,
                      isSelected: _selectedLabel == 'Другое',
                      onTap: () => setState(() => _selectedLabel = 'Другое'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              _buildTextField(
                label: 'Улица, дом',
                controller: _addressController,
                icon: Icons.location_on_outlined,
              ),
              const SizedBox(height: 12),

              Row(
                children: [
                  Expanded(
                    child: _buildTextField(
                      label: 'Кв./Офис',
                      controller: _aptController,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildTextField(
                      label: 'Подъезд',
                      controller: _entranceController,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _buildTextField(
                      label: 'Этаж',
                      controller: _floorController,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              _buildTextField(
                label: 'Код домофона',
                controller: _intercomController,
                icon: Icons.dialpad,
              ),
              const SizedBox(height: 12),

              _buildTextField(
                label: 'Комментарий курьеру',
                controller: _commentController,
                maxLines: 3,
              ),

              const SizedBox(height: 24),

              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _saveAddress,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF4CAF50),
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: const Text(
                    'Сохранить адрес',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTextField({
    required String label,
    required TextEditingController controller,
    IconData? icon,
    int maxLines = 1,
  }) {
    return TextField(
      controller: controller,
      maxLines: maxLines,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: icon != null ? Icon(icon, color: Colors.grey) : null,
        filled: true,
        fillColor: Colors.grey[100],
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 12,
        ),
      ),
    );
  }

  void _saveAddress() {
    if (_addressController.text.isEmpty) return;

    final newAddress = AddressModel(
      // Используем uuid, если пакет подключен, иначе можно DateTime.now().toString()
      id: widget.addressToEdit?.id ?? const Uuid().v4(),
      fullAddress: _addressController.text,
      apartment: _aptController.text,
      entrance: _entranceController.text,
      floor: _floorController.text,
      intercom: _intercomController.text,
      comment: _commentController.text,
      label: _selectedLabel,
    );

    if (widget.addressToEdit != null) {
      ref.read(addressProvider.notifier).updateAddress(newAddress);
    } else {
      ref.read(addressProvider.notifier).addAddress(newAddress);
    }

    Navigator.pop(context);
  }
}

class _CategoryChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;

  const _CategoryChip({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF4CAF50) : Colors.grey[100],
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: isSelected ? Colors.transparent : Colors.grey[300]!,
          ),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              size: 18,
              color: isSelected ? Colors.white : Colors.black54,
            ),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: isSelected ? Colors.white : Colors.black87,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

void showAddressModal(BuildContext context, [AddressModel? address]) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (context) => AddressModal(addressToEdit: address),
  );
}
