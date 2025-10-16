from rest_framework import serializers
from cms.models.product import Product, ProductOption, ProductVariant, ProductVariantImage, Collection, ProductLinkVariant, ProductPriceHistory, ProductVariantCustomField, ProductSizeChartValue, ComboProduct, ComboProductItem  
from cms.models.product_image import ProductImage
from cms.models.category import Category, Brand
from cms.models.facility import Facility, Cluster, FacilityInventory
from cms.models.setting import CustomField, SizeChart, SizeMeasurement, AttributeValue
import requests


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

# class SubcategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Subcategory
#         fields = ['id', 'name']

# class SubsubcategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Subsubcategory
#         fields = ['id', 'name']

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']


class SizeChartValueSerializer(serializers.Serializer):
    """Serializer for size chart values input/output"""
    size_id = serializers.IntegerField(read_only=True)
    size = serializers.CharField()  # Size value like "M", "L", "XL"
    measurements = serializers.DictField()  # {"Chest": "36", "Waist": "32"}


class ProductSizeChartSerializer(serializers.Serializer):
    """Serializer for complete size chart data"""
    size_chart_values = SizeChartValueSerializer(many=True, required=False)

# class ProductImageViewSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = ProductImage
#         fields = ['id','image','priority','alt_text','is_primary']

class ProductVariantImageSerializer(serializers.ModelSerializer):
    # id = serializers.IntegerField(required=False)  # Allow ID for updates, not required for creation
    class Meta:
        model = ProductVariantImage
        fields = ['id', 'image', 'priority', 'alt_text', 'is_primary', 'is_active']
    extra_kwargs = {
            'id': {'read_only': True}  # ID should NEVER be writable
        }

class ProductVariantViewSerializer(serializers.ModelSerializer):
    images = ProductVariantImageSerializer(many=True, required=False)
    custom_fields = serializers.JSONField(required=False)
    combo_details = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'slug', 'sku', 'description', 'tags', 'base_price', 'mrp', 'selling_price', 'margin', 'return_days',
            'ean_number', 'ran_number', 'hsn_code', 'tax', 'cgst', 'sgst', 'igst', 'cess', 'weight', 'net_qty', 'packaging_type', 'is_pack','pack_qty','pack_variant',
            'product_dimensions', 'package_dimensions', 'shelf_life', 'uom', 'attributes', 'is_active', 'is_b2b_enable', 'is_pp_enable',
            'is_visible', 'is_published', 'is_rejected', 'is_combo', 'combo_details', 'images','custom_fields', 'threshold', 'threshold_wac'
        ]

    def get_combo_details(self, obj):
        """Get combo details if this variant is a combo product"""
        return obj.combo_details

    def to_representation(self, instance):
        """Customize output representation"""
        data = super().to_representation(instance)

        # Override custom_fields for output
        if hasattr(instance, 'id') and instance.id:
            data['custom_fields'] = [
                {
                    'field_id': cv.custom_field.id,
                    'section': cv.custom_field.section.id if cv.custom_field.section else None,
                    'section_name': cv.custom_field.section.name if cv.custom_field.section else None,
                    'field_name': cv.custom_field.name,
                    'field_label': cv.custom_field.label,
                    'field_type': cv.custom_field.field_type,
                    'value': cv.value
                }
                for cv in instance.custom_field_values.select_related('custom_field').all()
            ]

            # Add size chart values for output
            from cms.views.product import get_product_size_chart_values
            size_chart_data = get_product_size_chart_values(instance)
            data['size_chart_values'] = size_chart_data.get('size_chart_values', [])
        else:
            data['custom_fields'] = []
            data['size_chart_values'] = []

        return data

class ProductCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ['id','name']

class ProductLinkVariantViewSerializer(serializers.ModelSerializer):
    linked_variant = ProductVariantViewSerializer(read_only=True)  # Serialize the related ProductVariant
    class Meta:
        model = ProductLinkVariant
        fields = ['id', 'product','linked_variant']  # Include the linked variant details, not just the ID

class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ['id', 'name', 'facility_type', 'city', 'state', 'country',]

class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cluster
        fields = ['id', 'name']
        
class ProductOptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)  # Allow ID for updates, not required for creation
    class Meta:
        model = ProductOption
        fields = ['id', 'name', 'position', 'values', 'is_active']

class ProductListSerializer(serializers.ModelSerializer):
    category     = CategorySerializer(read_only=True)
    # subcategory  = SubcategorySerializer(read_only=True)
    # subsubcategory = SubsubcategorySerializer(read_only=True)
    brand        = BrandSerializer(read_only=True)

    options         = ProductOptionSerializer(many=True, required=False)
    # product_images  = ProductImageViewSerializer(many=True, required=False)
    variants        = serializers.SerializerMethodField()
    collections     = ProductCollectionSerializer(many=True, required=False)
    linked_variants = ProductLinkVariantViewSerializer(many=True,read_only=True)

    assigned_facilities = serializers.SerializerMethodField()
    assigned_clusters = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()
    created_by_details = serializers.SerializerMethodField()
    updated_by_details = serializers.SerializerMethodField()

    category_tree = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id','name','sku','tags','description','category','brand','is_active','is_published',
            'variants','options','collections','linked_variants',
            'assigned_facilities', 'assigned_clusters', 'category_tree', 'created_by', 'updated_by',
            'creation_date', 'updation_date', 'created_by_details', 'updated_by_details'
        ]

    def get_category_tree(self, obj):
        # Traverse up the category tree from the assigned category
        tree = []
        category = obj.category
        while category:
            tree.insert(0, {'id': category.id, 'name': category.name})
            category = category.parent
        return tree

    def get_variants(self, obj):
        """Return variants based on request context"""
        # Check if we're filtering for rejected variants
        request = self.context.get('request')
        if request and request.query_params.get('rejected') == 'true':
            # Show only rejected variants when specifically requested
            variants = obj.variants.filter(is_rejected=True)
        else:
            # Default: show only non-rejected variants
            variants = obj.variants.filter(is_rejected=False)

        return ProductVariantViewSerializer(variants, many=True).data

    def get_assigned_facilities(self, obj):
        # Use prefetched data to avoid additional queries
        facilities = set()
        for variant in obj.variants.all():
            for inventory in variant.facility_inventories.all():
                facilities.add(inventory.facility)
        return FacilitySerializer(list(facilities), many=True).data

    def get_assigned_clusters(self, obj):
        # Use prefetched data to avoid additional queries
        clusters = set()
        for variant in obj.variants.all():
            for inventory in variant.facility_inventories.all():
                for cluster in inventory.facility.clusters.all():
                    clusters.add(cluster)
        return ClusterSerializer(list(clusters), many=True).data

    def get_created_by(self, obj):
        # Use prefetched data
        return obj.created_by.id if obj.created_by else 1

    def get_updated_by(self, obj):
        # Use prefetched data
        return obj.updated_by.id if obj.updated_by else 1

    def get_created_by_details(self, obj):
        # Use prefetched data to avoid additional queries
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'username': obj.created_by.username,
                'full_name': f"{obj.created_by.first_name} {obj.created_by.last_name}".strip() or obj.created_by.username,
                'email': obj.created_by.email,
                'created_at': obj.creation_date.isoformat() if obj.creation_date else None
            }
        else:
            # Return default admin details without database query
            return {
                'id': 1,
                'username': 'admin',
                'full_name': 'System Administrator',
                'email': 'admin@system.com',
                'created_at': obj.creation_date.isoformat() if obj.creation_date else None
            }

    def get_updated_by_details(self, obj):
        # Use prefetched data to avoid additional queries
        if obj.updated_by:
            return {
                'id': obj.updated_by.id,
                'username': obj.updated_by.username,
                'full_name': f"{obj.updated_by.first_name} {obj.updated_by.last_name}".strip() or obj.updated_by.username,
                'email': obj.updated_by.email,
                'updated_at': obj.updation_date.isoformat() if obj.updation_date else None
            }
        else:
            # Return default admin details without database query
            return {
                'id': 1,
                'username': 'admin',
                'full_name': 'System Administrator',
                'email': 'admin@system.com',
                'updated_at': obj.updation_date.isoformat() if obj.updation_date else None
            }
        
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id','image','priority','alt_text','is_primary']
        

class ProductVariantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)  # Allow ID for updates, not required for creation
    sku = serializers.CharField(required=False, allow_blank=True, allow_null=True)  # SKU is optional for creation
    images = ProductVariantImageSerializer(many=True, required=False)  # Added variant images
    link = serializers.CharField(required=False, write_only=True)
    custom_fields = serializers.JSONField(required=False)
    size_chart_values = SizeChartValueSerializer(many=True, required=False, write_only=True)
    class Meta:
        model = ProductVariant
        fields = [
            'id','name','description','tags','base_price','mrp','selling_price','margin','return_days',
            'ean_number','ran_number','hsn_code', 'tax','cgst', 'sgst', 'igst', 'cess', 'weight','net_qty','packaging_type',
            'is_pack','pack_qty','pack_variant','product_dimensions','package_dimensions','shelf_life','uom','attributes',
            'is_active','is_b2b_enable','is_pp_enable','is_visible','is_published','is_rejected','sku','images','link',
            'custom_fields','size_chart_values','threshold','threshold_wac'
        ]
        
    def to_representation(self, instance):
        """Customize output representation"""
        data = super().to_representation(instance)
        
        # Override custom_fields for output
        if hasattr(instance, 'id') and instance.id:
            data['custom_fields'] = [
                {
                    'field_id': cv.custom_field.id,
                    'field_name': cv.custom_field.name,
                    'field_label': cv.custom_field.label,
                    'field_type': cv.custom_field.field_type,
                    'value': cv.value
                }
                for cv in instance.custom_field_values.select_related('custom_field').all()
            ]

            # Add size chart values for output
            from cms.views.product import get_product_size_chart_values
            size_chart_data = get_product_size_chart_values(instance)
            data['size_chart_values'] = size_chart_data.get('size_chart_values', [])
        else:
            data['custom_fields'] = []
            data['size_chart_values'] = []

        return data
    
    def validate_custom_fields(self, value):
        """Validate custom fields input"""
        if not isinstance(value, list):
            raise serializers.ValidationError("custom_fields must be a list")
        
        for field_data in value:
            if not isinstance(field_data, dict):
                raise serializers.ValidationError("Each custom field must be an object")
            
            if 'field_id' not in field_data:
                raise serializers.ValidationError("field_id is required for custom fields")
            
            # Validate field exists
            try:
                CustomField.objects.get(id=field_data['field_id'], is_active=True)
            except CustomField.DoesNotExist:
                raise serializers.ValidationError(f"Custom field with ID {field_data['field_id']} does not exist or is inactive")

        return value

    def validate_attributes(self, value):
        """Validate attributes field"""
        if value is None:
            return value

        if not isinstance(value, dict):
            raise serializers.ValidationError("attributes must be a dictionary")

        # Validate that all keys and values are strings
        for key, val in value.items():
            if not isinstance(key, str):
                raise serializers.ValidationError("All attribute keys must be strings")
            if not isinstance(val, str):
                raise serializers.ValidationError("All attribute values must be strings")

        return value


class ProductDetailSerializer(serializers.ModelSerializer):
    category        = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    # subcategory    = serializers.PrimaryKeyRelatedField(queryset=Subcategory.objects.all(), required=False, allow_null=True)
    # subsubcategory = serializers.PrimaryKeyRelatedField(queryset=Subsubcategory.objects.all(), required=False, allow_null=True)
    brand           = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), required=False, allow_null=True)
    options         = ProductOptionSerializer(many=True, required=False)
    # product_images  = ProductImageSerializer(many=True, required=False)
    variants        = ProductVariantSerializer(many=True, required=False)
    facilities      = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)
    collections     = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)
    linked_variants = serializers.ListField(child=serializers.IntegerField(), required=False, write_only=True)

    class Meta:
        model = Product
        fields = [
            'id','name','sku','description','tags','category','brand','is_active','is_published',
            'image','options','variants','facilities', 'collections', 'linked_variants'
        ]

    def validate(self, attrs):
        """Validate shelf life requirements based on category"""
        category = attrs.get('category')
        variants = attrs.get('variants', [])

        if category and category.shelf_life_required:
            # Check if any variant is missing shelf_life
            for i, variant_data in enumerate(variants):
                shelf_life = variant_data.get('shelf_life')
                if not shelf_life:
                    variant_name = variant_data.get('name', f'Variant {i+1}')
                    raise serializers.ValidationError({
                        'variants': f"Shelf life date is required for variant '{variant_name}' because category '{category.name}' requires shelf life tracking."
                    })

        return attrs


class ProductViewSerializer(serializers.ModelSerializer):
    category     = CategorySerializer(read_only=True)
    brand        = BrandSerializer(read_only=True)

    # product_images  = ProductImageViewSerializer(many=True, required=False)
    variants        = serializers.SerializerMethodField()
    category_tree = serializers.SerializerMethodField()
    created_by_details = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'category', 'category_tree', 'brand', 'variants', 'is_active', 'is_published', 'created_by_details']

    def get_category_tree(self, obj):
        # Traverse up the category tree from the assigned category
        tree = []
        category = obj.category
        while category:
            tree.insert(0, {'id': category.id, 'name': category.name})
            category = category.parent
        return tree

    def get_variants(self, obj):
        """Return variants based on request context"""
        # Check if we're filtering for rejected variants
        request = self.context.get('request')
        if request and request.query_params.get('rejected') == 'true':
            # Show only rejected variants when specifically requested
            variants = obj.variants.filter(is_rejected=True)
        else:
            # Default: show only non-rejected variants
            variants = obj.variants.filter(is_rejected=False)

        return ProductVariantViewSerializer(variants, many=True).data

    def get_created_by_details(self, obj):
        # Use prefetched data to avoid additional queries
        if obj.created_by:
            return {
                'username': obj.created_by.username,
                'email': obj.created_by.email,
            }
        else:
            # Return default admin details without database query
            return {
                'username': 'admin',
                'email': 'admin@system.com',
            }

    # def get_updated_by_details(self, obj):
    #     # Use prefetched data to avoid additional queries
    #     if obj.updated_by:
    #         return {
    #             'username': obj.updated_by.username,
    #             'email': obj.updated_by.email,
    #         }
    #     else:
    #         # Return default admin details without database query
    #         return {
    #             'username': 'admin',
    #             'email': 'admin@system.com',
    #         }
    
class CollectionListSerializer(serializers.ModelSerializer):
    products = ProductViewSerializer(many=True, required=False)
    facilities = FacilitySerializer(many=True, required=False)
    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'products', 'facilities', 'image', 'is_active',
                  'start_date', 'end_date', 'creation_date', 'updation_date']

class CollectionSerializer(serializers.ModelSerializer):
    # products = CollectionProductSerializer(many=True, required=False)
    products = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), many=True)
    facilities = serializers.PrimaryKeyRelatedField(queryset=Facility.objects.all(), many=True, required=False)
    class Meta:
        model = Collection
        fields = ['id', 'name', 'description', 'products', 'facilities', 'image', 'is_active',
                  'start_date', 'end_date', 'creation_date', 'updation_date']


class ComboProductItemSerializer(serializers.ModelSerializer):
    """Serializer for combo product items"""
    product_variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    product_variant_sku = serializers.CharField(source='product_variant.sku', read_only=True)
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)

    class Meta:
        model = ComboProductItem
        fields = ['id', 'product_variant', 'product_variant_name', 'product_variant_sku', 'product_name', 'quantity', 'is_active']
        read_only_fields = ['id']


class ComboProductListSerializer(serializers.ModelSerializer):
    """Serializer for listing combo products with full details including pricing"""
    combo_variant_name = serializers.CharField(source='combo_variant.name', read_only=True)
    combo_variant_sku = serializers.CharField(source='combo_variant.sku', read_only=True)
    combo_items = ComboProductItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()

    # Pricing fields from combo_variant
    base_price = serializers.DecimalField(source='combo_variant.base_price', max_digits=10, decimal_places=2, read_only=True)
    mrp = serializers.DecimalField(source='combo_variant.mrp', max_digits=10, decimal_places=2, read_only=True)
    selling_price = serializers.DecimalField(source='combo_variant.selling_price', max_digits=10, decimal_places=2, read_only=True)

    # Tax fields from combo_variant
    tax = serializers.DecimalField(source='combo_variant.tax', max_digits=10, decimal_places=2, read_only=True)
    cgst = serializers.DecimalField(source='combo_variant.cgst', max_digits=10, decimal_places=2, read_only=True)
    sgst = serializers.DecimalField(source='combo_variant.sgst', max_digits=10, decimal_places=2, read_only=True)
    igst = serializers.DecimalField(source='combo_variant.igst', max_digits=10, decimal_places=2, read_only=True)
    cess = serializers.DecimalField(source='combo_variant.cess', max_digits=10, decimal_places=2, read_only=True)

    # Additional variant fields
    hsn_code = serializers.CharField(source='combo_variant.hsn_code', read_only=True, allow_null=True)
    weight = serializers.CharField(source='combo_variant.weight', read_only=True, allow_null=True)
    packaging_type = serializers.CharField(source='combo_variant.packaging_type', read_only=True, allow_null=True)
    shelf_life = serializers.IntegerField(source='combo_variant.shelf_life', read_only=True, allow_null=True)

    # Variant status fields
    variant_is_active = serializers.BooleanField(source='combo_variant.is_active', read_only=True)
    variant_is_published = serializers.BooleanField(source='combo_variant.is_published', read_only=True)

    class Meta:
        model = ComboProduct
        fields = ['id', 'combo_variant', 'combo_variant_name', 'combo_variant_sku', 'name', 'description',
                  'base_price', 'mrp', 'selling_price', 'tax', 'cgst', 'sgst', 'igst', 'cess',
                  'hsn_code', 'weight', 'packaging_type', 'shelf_life',
                  'variant_is_active', 'variant_is_published',
                  'combo_items', 'items_count', 'is_active', 'creation_date', 'updation_date']

    def get_items_count(self, obj):
        return obj.combo_items.filter(is_active=True).count()


class ComboProductCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating combo products"""
    combo_items = ComboProductItemSerializer(many=True)

    # Optional fields for creating a new variant
    product_id = serializers.IntegerField(write_only=True, required=False, help_text="Product ID to create variant for (optional)")
    variant_name = serializers.CharField(write_only=True, required=False, help_text="Name for new variant (required if product_id provided)")
    variant_data = serializers.JSONField(write_only=True, required=False, help_text="Additional variant fields like base_price, mrp, etc.")

    # Variant pricing fields for update
    base_price = serializers.FloatField(write_only=True, required=False, help_text="Variant base price")
    mrp = serializers.FloatField(write_only=True, required=False, help_text="Variant MRP")
    selling_price = serializers.FloatField(write_only=True, required=False, help_text="Variant selling price")

    # Variant tax fields
    tax = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True, required=False)
    cgst = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True, required=False)
    sgst = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True, required=False)
    igst = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True, required=False)
    cess = serializers.DecimalField(max_digits=10, decimal_places=2, write_only=True, required=False)

    # Variant identification fields
    ean_number = serializers.IntegerField(write_only=True, required=False)
    ran_number = serializers.IntegerField(write_only=True, required=False)
    hsn_code = serializers.CharField(write_only=True, required=False)

    # Variant physical properties
    weight = serializers.CharField(write_only=True, required=False)
    net_qty = serializers.CharField(write_only=True, required=False)
    packaging_type = serializers.CharField(write_only=True, required=False)
    product_dimensions = serializers.JSONField(write_only=True, required=False)
    package_dimensions = serializers.JSONField(write_only=True, required=False)
    shelf_life = serializers.IntegerField(write_only=True, required=False)
    uom = serializers.CharField(write_only=True, required=False)

    # Variant status fields
    is_published = serializers.BooleanField(write_only=True, required=False)
    is_visible = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = ComboProduct
        fields = ['id', 'combo_variant', 'product_id', 'variant_name', 'variant_data', 'name', 'description', 'combo_items', 'is_active',
                  'base_price', 'mrp', 'selling_price', 'tax', 'cgst', 'sgst', 'igst', 'cess',
                  'ean_number', 'ran_number', 'hsn_code', 'weight', 'net_qty', 'packaging_type',
                  'product_dimensions', 'package_dimensions', 'shelf_life', 'uom', 'is_published', 'is_visible']
        read_only_fields = ['id']
        extra_kwargs = {
            'combo_variant': {'required': False, 'allow_null': True}
        }

    def validate_combo_items(self, value):
        """Validate that combo has at least 2 items"""
        if len(value) < 2:
            raise serializers.ValidationError("A combo product must have at least 2 items")

        # Check for duplicate variants
        variant_ids = [item['product_variant'].id for item in value]
        if len(variant_ids) != len(set(variant_ids)):
            raise serializers.ValidationError("Cannot add the same variant multiple times")

        return value

    def validate(self, data):
        """Additional validation"""
        product_id = data.get('product_id')
        variant_name = data.get('variant_name')
        combo_variant = data.get('combo_variant')
        combo_items = data.get('combo_items', [])

        # If product_id is provided, variant_name is required
        if product_id and not variant_name:
            raise serializers.ValidationError({
                "variant_name": "variant_name is required when product_id is provided"
            })

        # Must provide either combo_variant OR product_id
        if not combo_variant and not product_id:
            raise serializers.ValidationError({
                "combo_variant": "Either combo_variant or product_id must be provided"
            })

        # Cannot provide both
        if combo_variant and product_id:
            raise serializers.ValidationError({
                "combo_variant": "Cannot provide both combo_variant and product_id. Use one or the other."
            })

        # Validate product exists if product_id provided
        if product_id:
            try:
                Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                raise serializers.ValidationError({
                    "product_id": f"Product with id {product_id} not found"
                })

        # Validate combo variant if provided
        if combo_variant:
            # Ensure combo variant is not included in its own items
            for item in combo_items:
                if item['product_variant'] == combo_variant:
                    raise serializers.ValidationError("Combo variant cannot be included in its own items")

        # Ensure no combo products are added as items
        for item in combo_items:
            if item['product_variant'].is_combo:
                raise serializers.ValidationError(f"Cannot add combo product '{item['product_variant'].name}' as an item")

        return data

    def create(self, validated_data):
        combo_items_data = validated_data.pop('combo_items')
        product_id = validated_data.pop('product_id', None)
        variant_name = validated_data.pop('variant_name', None)
        variant_data = validated_data.pop('variant_data', {})

        # Create variant if product_id is provided
        if product_id:
            product = Product.objects.get(id=product_id)

            # Create the variant
            combo_variant = ProductVariant.objects.create(
                product=product,
                name=variant_name,
                is_combo=True,
                **variant_data
            )
            validated_data['combo_variant'] = combo_variant

        # Create the combo product
        combo_product = ComboProduct.objects.create(**validated_data)

        # Create combo items
        for item_data in combo_items_data:
            ComboProductItem.objects.create(combo=combo_product, **item_data)

        return combo_product

    def update(self, instance, validated_data):
        combo_items_data = validated_data.pop('combo_items', None)

        # Extract variant-specific fields
        variant_fields = {}
        variant_field_names = [
            'base_price', 'mrp', 'selling_price', 'tax', 'cgst', 'sgst', 'igst', 'cess',
            'ean_number', 'ran_number', 'hsn_code', 'weight', 'net_qty', 'packaging_type',
            'product_dimensions', 'package_dimensions', 'shelf_life', 'uom', 'is_published', 'is_visible'
        ]

        for field in variant_field_names:
            if field in validated_data:
                variant_fields[field] = validated_data.pop(field)

        # Update combo product fields
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.combo_variant = validated_data.get('combo_variant', instance.combo_variant)
        instance.save()

        # Update combo variant fields if provided
        if variant_fields and instance.combo_variant:
            for field, value in variant_fields.items():
                setattr(instance.combo_variant, field, value)
            instance.combo_variant.save()

        # Update combo items if provided
        if combo_items_data is not None:
            # Delete existing items
            instance.combo_items.all().delete()

            # Create new items
            for item_data in combo_items_data:
                ComboProductItem.objects.create(combo=instance, **item_data)

        return instance


class ProductVariantListSerializer(serializers.ModelSerializer):
    product = ProductViewSerializer(many=False, required=False)
    combo_details = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = '__all__'

    def get_combo_details(self, obj):
        """Get combo details if this variant is a combo product"""
        return obj.combo_details



class ProductStatusUpdateSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()  # Only accepts True or False


## Bulk Product Create Serializer(For Excel Upload)
# SINGLE-ITEM SERIALIZER – no longer error on duplicate name
class SingleProductSerializer(serializers.ModelSerializer):
    category       = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    # subcategory    = serializers.PrimaryKeyRelatedField(queryset=Subcategory.objects.all())
    # subsubcategory = serializers.PrimaryKeyRelatedField(queryset=Subsubcategory.objects.all())
    brand          = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), required=False, allow_null=True)

    # product_images = ProductImageSerializer(many=True, required=False)
    variants       = ProductVariantSerializer(many=True, required=False)
    # collections    = serializers.ListField(
    #     child=serializers.IntegerField(), required=False, write_only=True
    # )

    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'description', 'tags',
            'category', 'brand',
            'is_active', 'is_published',
            'image', 'variants',
            # 'collections',
        ]

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])

        # create the product
        product = Product.objects.create(**validated_data)

        for var in variants_data:
            ProductVariant.objects.create(product=product, **var)

        return product


# BULK VALIDATION – reuse the above for many=True
class BulkProductSerializer(SingleProductSerializer):
    class Meta(SingleProductSerializer.Meta):
        list_serializer_class = serializers.ListSerializer  # standard list


# SMART BRAND PRODUCT SERIALIZER - Single brand field that accepts ID or name
class NullableIntegerField(serializers.IntegerField):
    """Custom field that handles empty strings by converting them to None"""
    def to_internal_value(self, data):
        if data == '' or data is None:
            return None
        return super().to_internal_value(data)

class ProductVariantCreateSerializer(serializers.ModelSerializer):
    """Variant serializer specifically for creation - SKU is optional and auto-generated"""
    id = serializers.IntegerField(required=False)
    sku = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    ean_number = NullableIntegerField(required=False, allow_null=True)
    ran_number = NullableIntegerField(required=False, allow_null=True)
    images = ProductVariantImageSerializer(many=True, required=False)
    link = serializers.CharField(required=False, write_only=True)
    custom_fields = serializers.JSONField(required=False)
    size_chart_values = SizeChartValueSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = ProductVariant
        fields = [
            'id','name','description','tags','base_price','mrp','selling_price','margin','return_days',
            'ean_number','ran_number','hsn_code', 'tax','cgst', 'sgst', 'igst', 'cess', 'weight','net_qty','packaging_type',
            'is_pack','pack_qty','pack_variant','product_dimensions','package_dimensions','shelf_life','uom','attributes',
            'is_active','is_b2b_enable','is_pp_enable','is_visible','is_published','is_rejected','sku','images','link',
            'custom_fields','size_chart_values'
        ]
        extra_kwargs = {
            'sku': {'required': False, 'allow_blank': True, 'allow_null': True},
        }


class SmartBrandProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())

    # Single brand field that accepts ID or name
    brand = serializers.CharField(max_length=255, required=False, allow_blank=True)

    variants = ProductVariantCreateSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'description', 'tags',
            'category', 'brand',
            'is_active', 'is_published',
            'image', 'variants',
        ]

    def validate_brand(self, value):
        print(f"Brand validation - Input value: {repr(value)}")
        
        if not value or value.strip() == '':
            print("Brand validation - Empty value, returning None")
            return None
            
        # Check if value is numeric (ID)
        if value.isdigit():
            try:
                brand = Brand.objects.get(id=int(value))
                print(f"Brand validation - Found by ID: {brand.name}")
                return brand
            except Brand.DoesNotExist:
                print(f"Brand validation - ID {value} not found, returning None")
                return None
        else:
            # Value is text (name), try to find by name (case-insensitive)
            try:
                brand = Brand.objects.get(name__iexact=value.strip())
                print(f"Brand validation - Found by name: {brand.name}")
                return brand
            except Brand.DoesNotExist:
                print(f"Brand validation - Name '{value}' not found, returning None")
                return None

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        validated_data.pop('id', None)

        import os
        GS1_API_URL = os.environ.get("GS1_API_URL", "https://api.gs1datakart.org/console/retailer/products")
        GS1_API_TOKEN = os.environ.get("GS1_API_TOKEN", "")

        failed_products = []
        product = None
        try:
            product = Product.objects.create(**validated_data)
        except Exception as e:
            failed_products.append({
                'data': validated_data,
                'error': str(e)
            })

        ean_rejected_products = []
        created_variants = []
        failed_variants = []
        has_ean_validation_failures = False

        if product:
            for var in variants_data:
                var.pop('id', None)

                # Handle attributes mapping for color, size, etc.
                attributes = {}
                if 'color' in var:
                    attributes['color'] = var.pop('color')
                if 'size' in var:
                    attributes['size'] = var.pop('size')

                # Handle attributes array format and convert to dict
                existing_attrs = var.get('attributes', {})
                if isinstance(existing_attrs, list):
                    # Convert array format to dict format
                    converted_attrs = {}
                    for attr in existing_attrs:
                        if isinstance(attr, dict) and 'attribute_id' in attr and 'value' in attr:
                            # You might want to get the attribute name from the ID
                            # For now, just use the value as key
                            converted_attrs[f"attr_{attr['attribute_id']}"] = attr['value']
                    var['attributes'] = converted_attrs
                elif isinstance(existing_attrs, dict):
                    # Already in dict format, merge with color/size if any
                    existing_attrs.update(attributes)
                    var['attributes'] = existing_attrs
                else:
                    var['attributes'] = attributes

                # Handle images - remove as it's not a direct field
                var.pop('images', None)
                
                # Handle size chart data - capture before removing
                size_chart_values = var.pop('size_chart_values', None)
                var.pop('size_chart_data', None)
                print(f"DEBUG: Captured size_chart_values for variant: {size_chart_values}")
                
                # Handle empty strings for numeric fields - convert to None
                if var.get('ean_number') == '' or var.get('ean_number') is None:
                    var['ean_number'] = None
                if var.get('ran_number') == '' or var.get('ran_number') is None:
                    var['ran_number'] = None

                ean_number = var.get('ean_number')
                ran_number = var.get('ran_number')

                # Determine which number to validate (prioritize EAN over RAN)
                validation_number = ean_number if ean_number else ran_number

                if validation_number:
                    # Check if EAN/RAN already exists in database
                    if ean_number:
                        existing_variant = ProductVariant.objects.filter(ean_number=ean_number).first()
                        if existing_variant:
                            print(f"EAN {ean_number} already exists in product variant: {existing_variant.name} (ID: {existing_variant.id})")
                            var['is_rejected'] = True
                            var['rejection_reason'] = f'EAN {ean_number} already exists in another product'
                            ean_rejected_products.append(var)
                            has_ean_validation_failures = True
                            # Skip GS1 validation if duplicate found
                            validation_number = None

                    if ran_number and not ean_number:
                        existing_variant = ProductVariant.objects.filter(ran_number=ran_number).first()
                        if existing_variant:
                            print(f"RAN {ran_number} already exists in product variant: {existing_variant.name} (ID: {existing_variant.id})")
                            var['is_rejected'] = True
                            var['rejection_reason'] = f'RAN {ran_number} already exists in another product'
                            ean_rejected_products.append(var)
                            has_ean_validation_failures = True
                            # Skip GS1 validation if duplicate found
                            validation_number = None

                    # Validate with GS1 API if not duplicate
                    if validation_number:
                        try:
                            import json
                            gtin_param = json.dumps([validation_number])
                            response = requests.get(
                                GS1_API_URL,
                                params={'gtin': gtin_param, 'status': 'published'},
                                headers={'Authorization': f'Bearer {GS1_API_TOKEN}'}
                            )
                            data = response.json()
                            number_type = 'EAN' if ean_number else 'RAN'
                            print(f'RESPONSE FROM GS1 for {number_type} {validation_number}:', data)

                            if data.get('status') and data.get('items'):
                                item = data['items'][0]
                                var['hsn_code'] = item.get('hs_code')

                                # Map tax breakdown fields from GS1 response
                                cgst_value = float(item.get('cgst', 0)) if item.get('cgst') else 0.0
                                sgst_value = float(item.get('sgst', 0)) if item.get('sgst') else 0.0
                                igst_value = float(item.get('igst', 0)) if item.get('igst') else 0.0

                                var['cgst'] = cgst_value
                                var['sgst'] = sgst_value
                                var['igst'] = igst_value
                                var['cess'] = 0.0  # Default as GS1 doesn't provide cess

                                # Calculate total tax (IGST for inter-state, CGST+SGST for intra-state)
                                total_tax = igst_value if igst_value > 0 else (cgst_value + sgst_value)
                                var['tax'] = total_tax

                                var['is_rejected'] = False
                                var['is_active'] = False
                            else:
                                var['is_rejected'] = True
                                var['rejection_reason'] = f'{number_type} {validation_number} not found in GS1 database'
                                ean_rejected_products.append(var)
                                has_ean_validation_failures = True
                        except Exception as e:
                            number_type = 'EAN' if ean_number else 'RAN'
                            print(f"GS1 API error for {number_type} {validation_number}: {e}")
                            var['is_rejected'] = True
                            var['rejection_reason'] = f'GS1 API validation failed for {number_type} {validation_number}'
                            ean_rejected_products.append(var)
                            has_ean_validation_failures = True
                try:
                    print(f"Creating variant with data: {var}")
                    created_variant = ProductVariant.objects.create(product=product, **var)
                    created_variants.append(created_variant)
                    print(f"Successfully created variant: {created_variant.name} (ID: {created_variant.id})")
                    
                    # Handle size chart values if they were provided
                    if size_chart_values:
                        print(f"Size chart values found for variant {created_variant.name}: {size_chart_values}")
                        from cms.views.product import handle_product_size_chart
                        try:
                            handle_product_size_chart(created_variant, {'size_chart_values': size_chart_values})
                            print(f"Successfully processed size chart values for variant: {created_variant.name}")
                        except Exception as e:
                            print(f"Error processing size chart values for variant {created_variant.name}: {str(e)}")
                    else:
                        print(f"No size chart values found for variant: {created_variant.name}")
                    
                except Exception as e:
                    print(f"Failed to create variant: {str(e)}")
                    print(f"Variant data: {var}")
                    failed_variants.append({
                        'data': var,
                        'error': str(e)
                    })

            # Set product as inactive if any EAN validation failed
            if has_ean_validation_failures:
                product.is_active = False
                product.save()
                print(f"Product '{product.name}' set to inactive due to EAN validation failures")

        return {
            'product': product,
            'ean_rejected_products': ean_rejected_products,
            'failed_products': failed_products,
            'failed_variants': failed_variants
        }


class ProductExportSerializer(serializers.ModelSerializer):
    # Product-level fields
    product_id            = serializers.IntegerField(source='product.id')
    product_title         = serializers.CharField(source='product.name')
    product_sku           = serializers.CharField(source='product.sku', default='')
    product_description   = serializers.CharField(source='product.description', default='')
    product_status        = serializers.SerializerMethodField()
    product_published     = serializers.SerializerMethodField()
    product_thumbnail     = serializers.CharField(source='product.image', default='')
    product_weight        = serializers.SerializerMethodField()

    # Category and brand info
    product_category      = serializers.CharField(source='product.category.name')
    product_category_id   = serializers.IntegerField(source='product.category.id')
    product_brand         = serializers.CharField(source='product.brand.name', default='', allow_null=True)
    product_brand_id      = serializers.IntegerField(source='product.brand.id', default=None, allow_null=True)
    product_collections   = serializers.SerializerMethodField()
    product_tags          = serializers.SerializerMethodField()

    # Variant-level fields
    variant_id            = serializers.IntegerField(source='id')
    variant_title         = serializers.CharField(source='name')
    variant_sku           = serializers.CharField(source='sku')
    variant_ean           = serializers.CharField(source='ean_number', default='')
    variant_ran           = serializers.CharField(source='ran_number', default='')
    variant_hsn_code      = serializers.CharField(source='hsn_code', default='')
    variant_tax           = serializers.DecimalField(source='tax', max_digits=10, decimal_places=2, default=0.00)
    variant_cgst          = serializers.DecimalField(source='cgst', max_digits=10, decimal_places=2, default=0.00)
    variant_sgst          = serializers.DecimalField(source='sgst', max_digits=10, decimal_places=2, default=0.00)
    variant_igst          = serializers.DecimalField(source='igst', max_digits=10, decimal_places=2, default=0.00)
    variant_cess          = serializers.DecimalField(source='cess', max_digits=10, decimal_places=2, default=0.00)
    variant_uom           = serializers.CharField(source='uom', default='')
    variant_net_qty       = serializers.CharField(source='net_qty', default='')
    variant_weight        = serializers.DecimalField(source='weight', max_digits=10, decimal_places=2, default=None, allow_null=True)
    variant_base_price    = serializers.DecimalField(source='base_price', max_digits=10, decimal_places=2)
    variant_mrp           = serializers.DecimalField(source='mrp', max_digits=10, decimal_places=2)
    variant_selling_price = serializers.DecimalField(source='selling_price', max_digits=10, decimal_places=2)
    variant_is_pack       = serializers.BooleanField(source='is_pack')
    variant_pack_qty      = serializers.IntegerField(source='pack_qty', default=1)
    variant_packaging_type = serializers.CharField(source='packaging_type', default='')
    variant_dimensions    = serializers.SerializerMethodField()
    variant_attributes    = serializers.SerializerMethodField()
    variant_status        = serializers.SerializerMethodField()
    variant_b2b_enable    = serializers.BooleanField(source='is_b2b_enable')
    variant_pp_enable     = serializers.BooleanField(source='is_pp_enable')
    variant_visible       = serializers.BooleanField(source='is_visible')
    variant_published     = serializers.BooleanField(source='is_published')
    variant_rejected      = serializers.BooleanField(source='is_rejected')

    # Images and inventory
    variant_images_count  = serializers.SerializerMethodField()
    variant_primary_image = serializers.SerializerMethodField()

    # Custom fields and size chart
    variant_custom_fields = serializers.SerializerMethodField()
    variant_size_chart    = serializers.SerializerMethodField()

    # Dates
    created_date          = serializers.DateTimeField(source='product.creation_date', format='%Y-%m-%d %H:%M:%S')
    updated_date          = serializers.DateTimeField(source='product.updation_date', format='%Y-%m-%d %H:%M:%S')

    class Meta:
        model = ProductVariant
        fields = [
            'product_id', 'product_title', 'product_sku', 'product_description', 'product_status', 'product_published',
            'product_thumbnail', 'product_weight', 'product_category', 'product_category_id',
            'product_brand', 'product_brand_id', 'product_collections', 'product_tags',
            'variant_id', 'variant_title', 'variant_sku', 'variant_ean', 'variant_ran', 'variant_hsn_code',
            'variant_tax', 'variant_cgst', 'variant_sgst', 'variant_igst', 'variant_cess', 'variant_uom', 'variant_net_qty', 'variant_weight',
            'variant_base_price', 'variant_mrp', 'variant_selling_price', 'variant_is_pack',
            'variant_pack_qty', 'variant_packaging_type', 'variant_dimensions', 'variant_attributes', 'variant_status',
            'variant_b2b_enable', 'variant_pp_enable', 'variant_visible', 'variant_published',
            'variant_rejected', 'variant_images_count', 'variant_primary_image',
            'variant_custom_fields', 'variant_size_chart', 'created_date', 'updated_date'
        ]

    def get_product_status(self, obj):
        return 'Active' if obj.product.is_active else 'Inactive'

    def get_product_published(self, obj):
        return 'Published' if obj.product.is_published else 'Draft'

    def get_product_weight(self, obj):
        return getattr(obj.product, 'weight', '')

    def get_product_collections(self, obj):
        return ", ".join([c.name for c in obj.product.collections.all()])

    def get_product_tags(self, obj):
        tags = getattr(obj.product, 'tags', None)
        return ', '.join(tags) if isinstance(tags, (list, tuple)) else (tags or '')

    def get_variant_dimensions(self, obj):
        """Format product dimensions as readable string"""
        dimensions = getattr(obj, 'product_dimensions', None)
        if isinstance(dimensions, dict):
            length = dimensions.get('length', '')
            width = dimensions.get('width', '')
            height = dimensions.get('height', '')
            unit = dimensions.get('unit', 'cm')
            if length and width and height:
                return f"{length}×{width}×{height} {unit}"
        return ''

    def get_variant_attributes(self, obj):
        """Format attributes as readable string"""
        attributes = getattr(obj, 'attributes', None)
        if isinstance(attributes, dict) and attributes:
            attr_pairs = [f"{key}: {value}" for key, value in attributes.items()]
            return "; ".join(attr_pairs)
        return ''

    def get_variant_status(self, obj):
        return 'Active' if obj.is_active else 'Inactive'

    def get_variant_images_count(self, obj):
        return obj.images.filter(is_active=True).count()

    def get_variant_primary_image(self, obj):
        primary_image = obj.images.filter(is_primary=True, is_active=True).first()
        return primary_image.image if primary_image else ''

    def get_variant_custom_fields(self, obj):
        """Format custom fields as readable string"""
        custom_fields = obj.custom_field_values.select_related('custom_field').all()
        if custom_fields:
            fields_data = []
            for cf in custom_fields:
                fields_data.append(f"{cf.custom_field.label}: {cf.value}")
            return "; ".join(fields_data)
        return ''

    def get_variant_size_chart(self, obj):
        """Format size chart data as readable string"""
        try:
            from cms.views.product import get_product_size_chart_values
            size_chart_data = get_product_size_chart_values(obj)
            size_values = size_chart_data.get('size_chart_values', [])

            if size_values:
                chart_data = []
                for size_info in size_values:
                    size = size_info.get('size', '')
                    measurements = size_info.get('measurements', {})
                    if measurements:
                        measurement_str = ", ".join([f"{k}: {v}" for k, v in measurements.items()])
                        chart_data.append(f"{size} ({measurement_str})")
                return "; ".join(chart_data)
        except:
            pass
        return ''


# New serializer for products with cluster pricing
class ClusterPricingSerializer(serializers.ModelSerializer):
    """Serializer for cluster pricing information"""
    class Meta:
        model = Cluster
        fields = ['id', 'name', 'region']


class ProductWithClusterPricingSerializer(serializers.ModelSerializer):
    """Serializer for products with cluster pricing information"""
    base_price = serializers.SerializerMethodField()
    clusters = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name',  'base_price', 'clusters'
        ]
    
    def get_base_price(self, obj):
        """Get the base price from the first active variant"""
        first_variant = obj.variants.filter(is_active=True).first()
        if first_variant:
            return first_variant.base_price
        return None
    
    def get_clusters(self, obj):
        """Get cluster pricing information for this product"""
        # Get all clusters
        all_clusters = Cluster.objects.filter(is_active=True)
        cluster_data = []
        
        # Get all variants for this product
        product_variants = obj.variants.filter(is_active=True)
        
        for cluster in all_clusters:
            # Get facilities in this cluster (include inactive facilities too)
            cluster_facilities = cluster.facilities.all()
            
            # Check if any variant of this product has inventory in this cluster
            facility_inventories = FacilityInventory.objects.filter(
                facility__in=cluster_facilities,
                product_variant__in=product_variants,
                is_active=True
            )
            
            if facility_inventories.exists():
                # Get the first inventory record for pricing
                inventory = facility_inventories.first()
                # Use variant base_price for base_price, inventory selling_price for selling_price
                variant_base_price = inventory.product_variant.base_price if inventory.product_variant else None
                actual_selling_price = inventory.selling_price if inventory.selling_price and inventory.selling_price > 0 else variant_base_price
                
                cluster_info = {
                    'cluster_id': cluster.id,
                    'cluster_name': cluster.name,
                    'region': cluster.region,
                    'base_price': variant_base_price,  # Always use variant's base_price
                    'selling_price': actual_selling_price  # Use inventory's selling_price
                }
            else:
                # No pricing available for this product in this cluster
                cluster_info = {
                    'cluster_id': cluster.id,
                    'cluster_name': cluster.name,
                    'region': cluster.region,
                    'base_price': None,
                    'selling_price': None
                }
            
            cluster_data.append(cluster_info)
        
        return cluster_data


# Serializer for product with facility pricing
class ProductWithFacilityPricingSerializer(serializers.ModelSerializer):
    """
    Serializer for products with facility pricing information.
    Shows all facilities where the product is available with their pricing.
    """
    base_price = serializers.SerializerMethodField()
    facilities = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'base_price', 'facilities'
        ]
    
    def get_base_price(self, obj):
        """Get the base price from the first active variant"""
        first_variant = obj.variants.filter(is_active=True).first()
        return first_variant.base_price if first_variant else None
    
    def get_facilities(self, obj):
        """Get facility pricing information for this product - shows all facilities with null if not available"""
        # Get all facilities
        all_facilities = Facility.objects.filter(is_active=True)
        
        # Get all variants for this product
        product_variants = obj.variants.filter(is_active=True)
        
        # Get facility inventories for this product's variants
        facility_inventories = FacilityInventory.objects.filter(
            product_variant__in=product_variants,
            is_active=True
        ).select_related('facility', 'product_variant')
        
        # Create a dictionary for quick lookup of inventory data by facility_id
        inventory_lookup = {}
        for inventory in facility_inventories:
            facility_id = inventory.facility.id
            if facility_id not in inventory_lookup:
                inventory_lookup[facility_id] = []
            inventory_lookup[facility_id].append(inventory)
        
        facilities_data = []
        for facility in all_facilities:
            # Check if this product is available in this facility
            if facility.id in inventory_lookup:
                # Product is available in this facility
                inventories = inventory_lookup[facility.id]
                
                # Get cluster information for this facility
                clusters = facility.clusters.all()
                cluster_info = None
                if clusters.exists():
                    cluster = clusters.first()
                    cluster_info = {
                        'cluster_id': cluster.id,
                        'cluster_name': cluster.name,
                        'cluster_region': cluster.region
                    }
                
                # For now, show the first variant's data (you can modify this logic as needed)
                inventory = inventories[0]
                variant = inventory.product_variant
                
                # Use variant base_price for base_price, inventory selling_price for selling_price
                variant_base_price = variant.base_price if variant else None
                actual_selling_price = inventory.selling_price if inventory.selling_price and inventory.selling_price > 0 else variant_base_price
                
                facility_data = {
                    'facility_id': facility.id,
                    'facility_name': facility.name,
                    'is_active': facility.is_active,
                    'city': facility.city,
                    'base_price': variant_base_price,  # Always show variant's base_price
                    'selling_price': actual_selling_price  # Show inventory's selling_price
                }
            else:
                # Product is NOT available in this facility - return null values
                clusters = facility.clusters.all()
                cluster_info = None
                if clusters.exists():
                    cluster = clusters.first()
                    cluster_info = {
                        'cluster_id': cluster.id,
                        'cluster_name': cluster.name,
                        'cluster_region': cluster.region
                    }
                
                facility_data = {
                    'facility_id': facility.id,
                    'facility_name': facility.name,
                    'is_active': facility.is_active,
                    'city': facility.city,
                    'base_price': None,
                    'selling_price': None
                }
            
            facilities_data.append(facility_data)
        
        return facilities_data


# Serializer for cluster price update
class ClusterPriceUpdateSerializer(serializers.Serializer):
    """Serializer for updating cluster-specific pricing"""
    cluster_id = serializers.IntegerField()
    margin = serializers.FloatField(help_text="Margin percentage (-10 to +10)")
    
    def validate_cluster_id(self, value):
        """Validate that cluster exists and is active"""
        from cms.models.facility import Cluster
        if not Cluster.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Cluster not found or inactive")
        return value
    
    def validate_percentage_change(self, value):
        """Validate percentage change is reasonable"""
        # if value < -100:
        #     raise serializers.ValidationError("Margin cannot be less than -100%")
        if value > 1000:
            raise serializers.ValidationError("Margin cannot be more than 1000%")
        return value

# Serializer for price history
class ProductPriceHistorySerializer(serializers.ModelSerializer):
    """Serializer for product price history"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    cluster_name = serializers.CharField(source='cluster.name', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    user_name = serializers.SerializerMethodField()
    base_price_difference = serializers.ReadOnlyField()
    selling_price_difference = serializers.ReadOnlyField()
    
    class Meta:
        model = ProductPriceHistory
        fields = [
            'id', 'product', 'product_name', 'product_variant', 'variant_name',
            'cluster', 'cluster_name', 'facility', 'facility_name', 'user', 'user_name',
            'old_price', 'new_price', 'old_csp', 'new_csp', 'percentage_change',
            'base_price_difference', 'selling_price_difference', 'change_type', 'change_reason',
            'creation_date', 'updation_date'
        ]
        read_only_fields = ['id', 'creation_date', 'updation_date']
    
    def get_user_name(self, obj):
        """Get user name or return 'System' if no user"""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}" if obj.user.first_name else obj.user.username
        return "System"