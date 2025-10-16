from rest_framework import serializers
from cms.views import facility
from user.models import User
from cms.models.facility import Cluster, Facility, FacilityInventory
from cms.models.product import Product, ProductVariant
from cms.models.product_image import ProductImage
from cms.models.category import Category, Brand


class ClusterFacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ['id', 'name', 'facility_type']

class ClusterListSerializer(serializers.ModelSerializer):
    facilities = ClusterFacilitySerializer(many=True, read_only=True)

    class Meta:
        model = Cluster
        fields = '__all__'

class ClusterSerializer(serializers.ModelSerializer):
    # facilities = ClusterFacilitySerializer(many=True, read_only=True)
    # facilities = serializers.PrimaryKeyRelatedField(queryset=Facility.objects.all(), many=True)

    class Meta:
        model = Cluster
        fields = '__all__'

class FaciltyClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cluster
        fields = ['id', 'name', 'region','is_active']

class FacilitySerializer(serializers.ModelSerializer):
    manager_names = serializers.SerializerMethodField()
    clusters = FaciltyClusterSerializer(many=True, read_only=True)
    managers = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), required=False)

    class Meta:
        model = Facility
        fields = [
            'id', 'name', 'facility_type', 'address', 'city', 'state', 'country', 'pincode',
            'email', 'phone_number', 'customer_care', 'cin_no', 'gstn_no', 'fssai_no',
            'latitude', 'longitude', 'servicable_area', 'is_active', 'managers', 'manager_names',
            'clusters', 'creation_date', 'updation_date'
         ]

    def get_manager_names(self, obj):
        """Returns the usernames of the managers."""
        return [user.username for user in obj.managers.all()]

class ProductVariantSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)  # Get product name

    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'product_name']

class FacilityInventorySerializer(serializers.ModelSerializer):
    product_variant_details = ProductVariantSerializer(source='product_variant', read_only=True)

    class Meta:
        model = FacilityInventory
        fields = [
            'id', 'facility', 'product_variant', 'stock', 'base_price','mrp','selling_price','cust_discount',
            'tax', 'max_purchase_limit','outofstock_threshold','status', 'is_active','product_variant_details'
        ]




class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']
        
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id','image','priority','alt_text','is_primary']

class ProductVariantViewSerializer(serializers.ModelSerializer):
    base_price = serializers.SerializerMethodField()
    mrp = serializers.SerializerMethodField()
    selling_price = serializers.SerializerMethodField()
    cust_discount = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    tax = serializers.SerializerMethodField()
    max_purchase_limit = serializers.SerializerMethodField()
    outofstock_threshold = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    combo_details = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = [
            'id', 'name', 'slug', 'sku', 'description', 'tags', 'base_price', 'mrp', 'selling_price', 'stock', 'cust_discount',
            'tax', 'max_purchase_limit', 'outofstock_threshold', 'ean_number', 'ran_number', 'hsn_code',
            'weight', 'net_qty', 'packaging_type', 'is_active', 'is_online', 'is_offline', 'in_app', 'status', 'is_combo', 'combo_details'
        ]

    def _get_facility_inventory(self, obj):
        """Fetch inventory data for the variant specific to the facility"""
        facility_ids = self.context.get("facility_scope", [])
        if not facility_ids:
            return None
        return obj.facility_inventories.filter(facility_id__in=facility_ids).first()
    
    def get_base_price(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.base_price if inv else None
    
    def get_mrp(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.mrp if inv else None

    def get_selling_price(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.selling_price if inv else None

    def get_stock(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.stock if inv else None

    def get_cust_discount(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.cust_discount if inv else None

    def get_tax(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.tax if inv else None

    def get_max_purchase_limit(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.max_purchase_limit if inv else None

    def get_outofstock_threshold(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.outofstock_threshold if inv else None

    def get_status(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.status if inv else None

    def get_is_active(self, obj):
        inv = self._get_facility_inventory(obj)
        return inv.is_active if inv else None

    def get_combo_details(self, obj):
        """Get combo details if this variant is a combo product"""
        return obj.combo_details


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    product_images = ProductImageSerializer(many=True, read_only=True)
    variants = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'tags', 'description', 'category','brand', 
            'is_active', 'is_published', 'product_images', 'variants'
        ]

    def get_variants(self, instance):
        assigned = getattr(instance, 'assigned_variants', None)
        if not assigned:
            # No facility scope or none assigned -> show nothing
            return []
        return ProductVariantViewSerializer(assigned, many=True, context=self.context).data 


class FacilityInventoryItemSerializer(serializers.ModelSerializer):
    facility_id = serializers.IntegerField(required=False)
    product_variant_id = serializers.IntegerField(required=True)

    class Meta:
        model = FacilityInventory
        fields = [
            "facility_id", "product_variant_id",
            "base_price", "mrp", "selling_price", "stock", "cust_discount",
            "max_purchase_limit", "outofstock_threshold",
            "status", "is_active", "tax_id",
        ]
