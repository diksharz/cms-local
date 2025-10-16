from rest_framework import serializers
from cms.models.category import Category, Brand


# class SubcategorySubsubcategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Subsubcategory  # Assuming you have a Subsubcategory model
#         fields = ['id', 'name', 'description']

# class CategorySubcategorySerializer(serializers.ModelSerializer):
#     subsubcategories = SubcategorySubsubcategorySerializer(many=True, read_only=True)  # Nested subsubcategories

#     class Meta:
#         model = Subcategory
#         fields = ['id', 'name', 'description', 'subsubcategories']

class CategoryListSerializer(serializers.ModelSerializer):
    # subcategories = CategorySubcategorySerializer(many=True, read_only=True)  # Nested subcategories
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parent', 'image', 'is_active', 'rank', 'shelf_life_required']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parent', 'image', 'is_active', 'rank', 'shelf_life_required']

# class SubcategorySerializer(serializers.ModelSerializer):
#     category_name = serializers.CharField(source='category.name', read_only=True)

#     class Meta:
#         model = Subcategory
#         fields = ['id', 'name', 'description', 'category', 'category_name', 'image', 'is_active']

# class SubsubcategorySerializer(serializers.ModelSerializer):
#     category_name = serializers.CharField(source='category.name', read_only=True)
#     subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
#     class Meta:
#         model = Subsubcategory
#         fields = ['id', 'name', 'description', 'category', 'category_name','subcategory', 'subcategory_name', 'image', 'is_active']

class BrandSerializer(serializers.ModelSerializer):
    variant_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'description', 'image', 'is_active', 'variant_count']


class CategoryShelfLifeBulkUpdateSerializer(serializers.Serializer):
    categories = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of categories with their shelf life requirements"
    )

    def validate_categories(self, value):
        validated_categories = []
        category_ids = set()

        for category_data in value:
            if 'id' not in category_data:
                raise serializers.ValidationError("Each category must have an 'id' field")

            category_id = category_data['id']

            # Check for duplicate IDs
            if category_id in category_ids:
                raise serializers.ValidationError(f"Duplicate category ID: {category_id}")
            category_ids.add(category_id)

            # Validate category exists
            try:
                Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError(f"Category with ID {category_id} does not exist")

            # Validate shelf_life_required field
            shelf_life_required = category_data.get('shelf_life_required', False)
            if not isinstance(shelf_life_required, bool):
                raise serializers.ValidationError(f"shelf_life_required must be a boolean for category {category_id}")

            validated_categories.append({
                'id': category_id,
                'shelf_life_required': shelf_life_required
            })

        return validated_categories

    def save(self):
        categories_data = self.validated_data['categories']
        updated_categories = []

        for category_data in categories_data:
            category = Category.objects.get(id=category_data['id'])
            category.shelf_life_required = category_data['shelf_life_required']
            category.save(update_fields=['shelf_life_required'])
            updated_categories.append(category)

        return updated_categories
