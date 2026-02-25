extension Validators on String {
  bool get isValidEmail =>
      RegExp(r'^[\w.\+\-]+@[\w\-]+\.[\w.\-]+$').hasMatch(this);

  bool get isValidPhone =>
      RegExp(r'^[\+]?[0-9\s\-\(\)]{7,15}$').hasMatch(this);
}
