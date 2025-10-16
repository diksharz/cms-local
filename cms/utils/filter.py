
from django_filters import rest_framework as filters
from ..models.facility import Facility
from ..models.product import ProductVariant, Product
from cms.models.facility import Facility, Cluster, FacilityInventory
from cms.models.category import Category, Brand
from cms.models.product import Collection, ComboProduct
from user.models import User

class ProductFilter(filters.FilterSet):
    status     = filters.BooleanFilter(field_name='is_active')
    sku        = filters.CharFilter(field_name='sku', lookup_expr='icontains')
    rejected   = filters.BooleanFilter(method='filter_by_variant_rejected')
    def filter_by_variant_rejected(self, queryset, name, value):
        # Filter products based on variant rejection status
        from cms.models.product import ProductVariant
        from django.db import models
        if value:
            # Show products that have at least one rejected variant
            variant_ids = ProductVariant.objects.filter(is_rejected=True).values_list('product_id', flat=True)
            return queryset.filter(id__in=variant_ids).distinct()
        else:
            # Show products that have non-rejected variants OR have no variants at all
            # Get products with rejected variants only (to exclude them)
            products_with_only_rejected = ProductVariant.objects.filter(
                is_rejected=True
            ).values('product_id').annotate(
                total_variants=models.Count('id'),
                rejected_variants=models.Count('id', filter=models.Q(is_rejected=True))
            ).filter(
                total_variants=models.F('rejected_variants')
            ).values_list('product_id', flat=True)

            # Return products that are NOT in the "only rejected variants" list
            return queryset.exclude(id__in=products_with_only_rejected)
    category   = filters.NumberFilter(method='filter_by_category_tree')
    def filter_by_category_tree(self, queryset, name, value):
        # Filter products where the assigned category or any parent matches the value
        from cms.models.category import Category
        # Get all descendant categories (including the selected one)
        def get_descendants(cat_id):
            descendants = set([cat_id])
            children = Category.objects.filter(parent_id=cat_id).values_list('id', flat=True)
            for child_id in children:
                descendants |= get_descendants(child_id)
            return descendants

        # Accept both parent and leaf category ids
        category_ids = get_descendants(value)
        # Also include products directly assigned to this category
        return queryset.filter(category_id__in=category_ids)
    # subcategory = filters.NumberFilter(field_name='subcategory__id')
    # subsubcategory = filters.NumberFilter(field_name='subsubcategory__id')
    brand      = filters.NumberFilter(field_name='brand__id')
    collection = filters.NumberFilter(field_name='collections__id')
    facility = filters.NumberFilter(method='filter_by_facility')
    cluster = filters.NumberFilter(method='filter_by_cluster')

    def filter_by_facility(self, queryset, name, value):
        # Get product IDs for variants stocked in the given facility
        product_ids = FacilityInventory.objects.filter(
            facility_id=value
        ).values_list('product_variant__product_id', flat=True)
        return queryset.filter(id__in=product_ids).distinct()
    
    def filter_by_cluster(self, queryset, name, value):
        # Get facilities in the given cluster
        facility_ids = Cluster.objects.get(id=value).facilities.values_list('id', flat=True)
        # Get variant ids available in those facilities
        product_variant_ids = FacilityInventory.objects.filter(
            facility_id__in=facility_ids
        ).values_list('product_variant__product_id', flat=True)
        # Filter products that have variants present in the facilities of the cluster
        return queryset.filter(id__in=product_variant_ids).distinct()

    class Meta:
        model  = Product
        fields = ['status', 'sku', 'rejected', 'category', 'brand', 'collection', 'cluster', 'facility']


class ProductVariantFilter(filters.FilterSet):
    category       = filters.NumberFilter(field_name='product__category__id')
    brand          = filters.NumberFilter(field_name='product__brand__id')
    product        = filters.NumberFilter(field_name='product__id')
    # subcategory    = filters.NumberFilter(field_name='product__subcategory__id')
    # subsubcategory = filters.NumberFilter(field_name='product__subsubcategory__id')
    collection     = filters.NumberFilter(field_name='product__collections__id')
    facility = filters.NumberFilter(method='filter_by_facility')
    cluster = filters.NumberFilter(method='filter_by_cluster')
    is_active = filters.BooleanFilter(field_name='is_active')
    is_b2b_enable = filters.BooleanFilter(field_name='is_b2b_enable')
    is_pp_enable = filters.BooleanFilter(field_name='is_pp_enable')
    is_visible = filters.BooleanFilter(field_name='is_visible')
    is_published = filters.BooleanFilter(field_name='is_published')
    is_rejected = filters.BooleanFilter(field_name='is_rejected')
    is_combo = filters.BooleanFilter(field_name='is_combo')
    sku = filters.CharFilter(field_name='sku', lookup_expr='icontains')

    # Attribute filtering
    attribute_key = filters.CharFilter(method='filter_by_attribute_key')
    attribute_value = filters.CharFilter(method='filter_by_attribute_value')
    attributes = filters.CharFilter(method='filter_by_attributes')

    def filter_by_facility(self, queryset, name, value):
        # Get product IDs for variants stocked in the given facility
        variant_ids = FacilityInventory.objects.filter(
            facility_id=value
        ).values_list('product_variant_id', flat=True)
        return queryset.filter(id__in=variant_ids).distinct()
    
    def filter_by_cluster(self, queryset, name, value):
        facility_ids = Cluster.objects.get(id=value).facilities.values_list('id', flat=True)
        # Get the product variant IDs stocked in these facilities
        variant_ids = FacilityInventory.objects.filter(
            facility_id__in=facility_ids
        ).values_list('product_variant_id', flat=True)
        return queryset.filter(id__in=variant_ids).distinct()

    def filter_by_attribute_key(self, queryset, name, value):
        """Filter variants that have a specific attribute key"""
        return queryset.filter(attributes__has_key=value)

    def filter_by_attribute_value(self, queryset, name, value):
        """Filter variants that have any attribute with a specific value"""
        from django.db.models import Q
        q = Q()
        # Search for the value in any attribute
        q |= Q(attributes__has_key='Size', attributes__Size__icontains=value)
        q |= Q(attributes__has_key='Color', attributes__Color__icontains=value)
        q |= Q(attributes__has_key='Brand', attributes__Brand__icontains=value)
        return queryset.filter(q).distinct()

    def filter_by_attributes(self, queryset, name, value):
        """Filter variants by attribute key:value pair (format: 'Size:M' or 'Color:Red')"""
        try:
            if ':' in value:
                key, val = value.split(':', 1)
                return queryset.filter(attributes__contains={key.strip(): val.strip()})
            else:
                # If no colon, search in all attribute values
                from django.db.models import Q
                q = Q()
                # Search for value in any attribute key or value
                for variant in queryset:
                    if variant.attributes:
                        for attr_key, attr_val in variant.attributes.items():
                            if value.lower() in attr_key.lower() or value.lower() in attr_val.lower():
                                q |= Q(id=variant.id)
                return queryset.filter(q)
        except (ValueError, AttributeError):
            return queryset.none()

    class Meta:
        model  = ProductVariant
        fields = ['category', 'brand', 'collection', 'cluster', 'facility', 'is_active', 'is_b2b_enable', 'is_pp_enable', 'is_visible', 'is_published', 'is_rejected', 'is_combo', 'sku', 'attribute_key', 'attribute_value', 'attributes']


class ComboProductFilter(filters.FilterSet):
    """Filter for combo products"""
    # Basic filters
    status = filters.BooleanFilter(field_name='is_active')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    description = filters.CharFilter(field_name='description', lookup_expr='icontains')

    # Combo variant filters
    combo_variant_sku = filters.CharFilter(field_name='combo_variant__sku', lookup_expr='icontains')
    combo_variant_name = filters.CharFilter(field_name='combo_variant__name', lookup_expr='icontains')

    # Product filters (through combo_variant)
    product = filters.NumberFilter(field_name='combo_variant__product__id')
    product_name = filters.CharFilter(field_name='combo_variant__product__name', lookup_expr='icontains')
    category = filters.NumberFilter(field_name='combo_variant__product__category__id')
    brand = filters.NumberFilter(field_name='combo_variant__product__brand__id')

    # Combo variant status filters
    variant_is_active = filters.BooleanFilter(field_name='combo_variant__is_active')
    variant_is_published = filters.BooleanFilter(field_name='combo_variant__is_published')

    # Date filters
    created_after = filters.DateTimeFilter(field_name='creation_date', lookup_expr='gte')
    created_before = filters.DateTimeFilter(field_name='creation_date', lookup_expr='lte')
    updated_after = filters.DateTimeFilter(field_name='updation_date', lookup_expr='gte')
    updated_before = filters.DateTimeFilter(field_name='updation_date', lookup_expr='lte')

    # Contains specific variant
    contains_variant = filters.NumberFilter(method='filter_contains_variant')

    def filter_contains_variant(self, queryset, name, value):
        """Filter combos that contain a specific variant"""
        return queryset.filter(combo_items__product_variant__id=value, combo_items__is_active=True).distinct()

    class Meta:
        model = ComboProduct
        fields = ['status', 'name', 'description', 'combo_variant_sku', 'combo_variant_name',
                  'product', 'product_name', 'category', 'brand', 'variant_is_active',
                  'variant_is_published', 'contains_variant']


class FacilityFilter(filters.FilterSet):
    status     = filters.BooleanFilter(field_name='is_active')
    facility_type = filters.CharFilter(field_name='facility_type', lookup_expr='icontains')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    city = filters.CharFilter(field_name='city', lookup_expr='icontains')
    region = filters.CharFilter(field_name='region', lookup_expr='icontains')
    managers = filters.NumberFilter(field_name='managers__id')
    cluster = filters.NumberFilter(field_name='cluster__id')
    created_after = filters.DateFilter(field_name='creation_date__date', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='creation_date__date', lookup_expr='lte')

    class Meta:
        model  = Facility
        fields = ['status', 'facility_type', 'name', 'city', 'region', 'managers', 'cluster']


class ClusterFilter(filters.FilterSet):
    status = filters.BooleanFilter(field_name='is_active')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    region = filters.CharFilter(field_name='region', lookup_expr='icontains')
    facilities = filters.NumberFilter(field_name='facilities__id')
    created_after = filters.DateFilter(field_name='creation_date__date', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='creation_date__date', lookup_expr='lte')

    class Meta:
        model  = Cluster
        fields = ['status', 'name', 'region', 'facilities']


class UserFilter(filters.FilterSet):
    role = filters.CharFilter(field_name='role', lookup_expr='iexact')
    email = filters.CharFilter(field_name='email', lookup_expr='icontains')
    username = filters.CharFilter(field_name='username', lookup_expr='icontains')
    first_name = filters.CharFilter(field_name='first_name', lookup_expr='icontains')
    last_name = filters.CharFilter(field_name='last_name', lookup_expr='icontains')
    is_active = filters.BooleanFilter(field_name='is_active')
    is_staff = filters.BooleanFilter(field_name='is_staff')
    is_superuser = filters.BooleanFilter(field_name='is_superuser')
    date_joined_after = filters.DateTimeFilter(field_name='date_joined', lookup_expr='gte')
    date_joined_before = filters.DateTimeFilter(field_name='date_joined', lookup_expr='lte')

    def filter_role_in(self, queryset, name, value):
        # Filter by multiple roles (comma-separated)
        roles = [role.strip() for role in value.split(',') if role.strip()]
        return queryset.filter(role__in=roles)

    class Meta:
        model  = User
        fields = ['role', 'email', 'username', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser']


class BrandFilter(filters.FilterSet):
    status = filters.BooleanFilter(field_name='is_active')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    description = filters.CharFilter(field_name='description', lookup_expr='icontains')
    created_after = filters.DateFilter(field_name='creation_date__date', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='creation_date__date', lookup_expr='lte')

    class Meta:
        model  = Brand
        fields = ['status', 'name', 'description']


class CollectionFilter(filters.FilterSet):
    status = filters.BooleanFilter(field_name='is_active')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    description = filters.CharFilter(field_name='description', lookup_expr='icontains')
    products = filters.NumberFilter(field_name='products__id')
    facilities = filters.NumberFilter(field_name='facilities__id')
    created_after = filters.DateFilter(field_name='creation_date__date', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='creation_date__date', lookup_expr='lte')

    class Meta:
        model  = Collection
        fields = ['status', 'name', 'description', 'products', 'facilities']


class CategoryFilter(filters.FilterSet):
    status = filters.BooleanFilter(field_name='is_active')
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    description = filters.CharFilter(field_name='description', lookup_expr='icontains')
    parent = filters.NumberFilter(field_name='parent__id')
    parent_is_null = filters.BooleanFilter(field_name='parent__isnull')
    rank = filters.NumberFilter(field_name='rank')
    rank_gte = filters.NumberFilter(field_name='rank', lookup_expr='gte')
    rank_lte = filters.NumberFilter(field_name='rank', lookup_expr='lte')
    children = filters.NumberFilter(field_name='children__id')
    products = filters.NumberFilter(field_name='products__id')
    shelf_life_required = filters.BooleanFilter(field_name='shelf_life_required')
    created_after = filters.DateFilter(field_name='creation_date__date', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='creation_date__date', lookup_expr='lte')

    class Meta:
        model  = Category
        fields = ['status', 'name', 'description', 'parent', 'rank', 'children', 'products', 'shelf_life_required']