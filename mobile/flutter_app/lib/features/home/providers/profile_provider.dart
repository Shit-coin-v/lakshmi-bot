import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/models/user_model.dart';
import '../services/profile_service.dart';

// This provider loads and watches the user profile
final profileProvider = AsyncNotifierProvider<ProfileNotifier, UserModel>(() {
  return ProfileNotifier();
});

class ProfileNotifier extends AsyncNotifier<UserModel> {
  @override
  Future<UserModel> build() async {
    return ref.read(profileServiceProvider).getProfile();
  }

  // Method for updating text data (name, phone, email)
  Future<void> updateData({
    String? name,
    String? phone,
    String? email,
    bool? newsletterEnabled,
    bool? promoEnabled,
    bool? newsEnabled,
    bool? generalEnabled,
    bool? orderStatusEnabled,
  }) async {
    state = const AsyncValue.loading();
    try {
      await ref.read(profileServiceProvider).updateProfile(
        fullName: name,
        phone: phone,
        email: email,
        newsletterEnabled: newsletterEnabled,
        promoEnabled: promoEnabled,
        newsEnabled: newsEnabled,
        generalEnabled: generalEnabled,
        orderStatusEnabled: orderStatusEnabled,
      );

      // 2. Refresh data locally (re-fetch from server)
      final newUser = await ref.read(profileServiceProvider).getProfile();
      state = AsyncValue.data(newUser);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  // Avatar upload method
  Future<void> uploadUserAvatar(File file) async {
    // Could show loading, but better to keep old avatar while uploading
    // state = const AsyncValue.loading();

    try {
      // 1. Upload file via service
      await ref.read(profileServiceProvider).uploadAvatar(file);

      // 2. Fetch updated profile (with new image URL)
      final newUser = await ref.read(profileServiceProvider).getProfile();
      state = AsyncValue.data(newUser);
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }
}
