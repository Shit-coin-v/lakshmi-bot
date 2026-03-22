import 'package:flutter_test/flutter_test.dart';
import 'package:lakshmi_market/features/catalog/models/category_node.dart';

void main() {
  group('CategoryNode', () {
    test('fromJson parses all fields', () {
      final json = {
        'id': 1,
        'name': 'Молочные продукты',
        'parent_id': null,
        'has_children': true,
      };

      final node = CategoryNode.fromJson(json);

      expect(node.id, 1);
      expect(node.name, 'Молочные продукты');
      expect(node.parentId, isNull);
      expect(node.hasChildren, isTrue);
      expect(node.isLeaf, isFalse);
    });

    test('fromJson with parent_id', () {
      final json = {
        'id': 5,
        'name': 'Кефир',
        'parent_id': 1,
        'has_children': false,
      };

      final node = CategoryNode.fromJson(json);

      expect(node.id, 5);
      expect(node.parentId, 1);
      expect(node.hasChildren, isFalse);
      expect(node.isLeaf, isTrue);
    });

    test('fromJson defaults name to empty string when null', () {
      final json = {
        'id': 10,
        'name': null,
        'parent_id': null,
        'has_children': false,
      };

      final node = CategoryNode.fromJson(json);

      expect(node.name, '');
    });

    test('fromJson defaults has_children to false when missing', () {
      final json = {
        'id': 20,
        'name': 'Test',
      };

      final node = CategoryNode.fromJson(json);

      expect(node.hasChildren, isFalse);
      expect(node.isLeaf, isTrue);
    });

    test('isLeaf is inverse of hasChildren', () {
      final withChildren = CategoryNode(id: 1, name: 'A', hasChildren: true);
      final withoutChildren = CategoryNode(id: 2, name: 'B', hasChildren: false);

      expect(withChildren.isLeaf, isFalse);
      expect(withoutChildren.isLeaf, isTrue);
    });
  });
}
