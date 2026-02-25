extension PriceFormatting on double {
  /// Formats price with ruble sign.
  /// Whole numbers: "100 ₽", fractional: "99.50 ₽"
  String formatPrice() {
    return truncateToDouble() == this
        ? '${toStringAsFixed(0)} \u20bd'
        : '${toStringAsFixed(2)} \u20bd';
  }
}
