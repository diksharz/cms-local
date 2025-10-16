from django.contrib import admin
from .models.category import Category, Brand
from .models.facility import Facility, Cluster, FacilityInventory
from .models.product import Language, Product, ProductDetail, ProductVariant, ProductVariantImage, Collection, ComboProduct, ComboProductItem
from .models.product_image import ProductImage
from .models.setting import Attribute, AttributeValue, ProductType, ProductTypeAttribute, CustomTab, CustomSection, CustomField
from .models.master import Tax
from django.utils.html import format_html


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ('name', 'percentage', 'cgst_percentage', 'sgst_percentage', 'igst_percentage', 'is_active')
    search_fields = ('name', 'percentage', 'is_active')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'percentage', 'cgst_percentage', 'sgst_percentage', 'igst_percentage', 'cess_percentage', 'is_active')
        }),
    )

@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'latitude', 'longitude', 'is_active')
    search_fields = ('name', 'region')
    list_filter = ('region', 'is_active')
    filter_horizontal = ('facilities',) 

@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ('name', 'facility_type', 'address', 'city', 'state', 'get_assigned_clusters', 'is_active')
    search_fields = ('name', 'address', 'city', 'state')
    list_filter = ('facility_type', 'is_active', 'city')

    def get_assigned_clusters(self, obj):
        # This will return a comma-separated string of cluster names assigned to the facility
        return ", ".join([cluster.name for cluster in obj.clusters.all()])
    get_assigned_clusters.short_description = "Clusters"
 

@admin.register(FacilityInventory)
class FacilityInventoryAdmin(admin.ModelAdmin):
    list_display = ('facility', 'product_variant', 'stock', 'base_price', 'mrp', 'selling_price', 'cust_discount', 'is_active')
    search_fields = ('facility__name', 'product_variant__name')  # You can search by the manager's username

    # Include manager field in the admin form
    fieldsets = (
        (None, {
            'fields': ('facility', 'product_variant', 'stock', 'tax', 'base_price', 'mrp', 'selling_price', 'cust_discount', 'max_purchase_limit', 'outofstock_threshold', 'status', 'is_active')
        }),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'has_image')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    readonly_fields = ('creation_date', 'updation_date')
    autocomplete_fields = ("parent",)

    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Parent ID', {
            'fields': ('parent',),
            'description': 'Select a parent category for this category.'
        }),
        ('Images', {
            'fields': ('image',),
            'description': 'Upload an image file (stored with original filename, WebP versions generated automatically) OR provide a direct URL.'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('creation_date', 'updation_date'),
            'classes': ('collapse',)
        }),
    )

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = 'Has Image'


# @admin.register(Subcategory)
# class SubcategoryAdmin(admin.ModelAdmin):
#     list_display = ('name', 'category', 'is_active', 'has_image')
#     list_filter = ('category', 'is_active')
#     search_fields = ('name', 'description')
#     readonly_fields = ('creation_date', 'updation_date')

#     fieldsets = (
#         (None, {
#             'fields': ('name', 'description', 'category')
#         }),
#         ('Images', {
#             'fields': ('image',),
#             'description': 'Upload an image file (stored with original filename, WebP versions generated automatically) OR provide a direct URL.'
#         }),
#         ('Status', {
#             'fields': ('is_active',)
#         }),
#         ('Timestamps', {
#             'fields': ('creation_date', 'updation_date'),
#             'classes': ('collapse',)
#         }),
#     )

#     def has_image(self, obj):
#         return bool(obj.image)
#     has_image.boolean = True
#     has_image.short_description = 'Has Image'

# @admin.register(Subsubcategory)
# class SubsubcategoryAdmin(admin.ModelAdmin):
#     list_display = ('name', 'category', 'subcategory', 'is_active', 'has_image')
#     list_filter = ('category', 'is_active')
#     search_fields = ('name', 'description')
#     readonly_fields = ('creation_date', 'updation_date')

#     fieldsets = (
#         (None, {
#             'fields': ('name', 'description', 'category', 'subcategory')
#         }),
#         ('Images', {
#             'fields': ('image',),
#             'description': 'Upload an image file (stored with original filename, WebP versions generated automatically) OR provide a direct URL.'
#         }),
#         ('Status', {
#             'fields': ('is_active',)
#         }),
#         ('Timestamps', {
#             'fields': ('creation_date', 'updation_date'),
#             'classes': ('collapse',)
#         }),
#     )

#     def has_image(self, obj):
#         return bool(obj.image)
#     has_image.boolean = True
#     has_image.short_description = 'Has Image'


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'has_image')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    readonly_fields = ('creation_date', 'updation_date')

    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('Images', {
            'fields': ('image',),
            'description': 'Upload an image file (stored with original filename, WebP versions generated automatically) OR provide a direct URL.'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('creation_date', 'updation_date'),
            'classes': ('collapse',)
        }),
    )

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = 'Has Image'

class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name',)

admin.site.register(Language, LanguageAdmin)

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1  # How many empty variant fields to show by default in the admin



class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'is_active', 'is_published', 'facility_ids_display')
    search_fields = ('name', 'category__name', 'brand__name')
    list_filter = ('is_active', 'is_published', 'category', 'brand')
    inlines = [ProductVariantInline]  # Add variants and images inline

    def facility_ids_display(self, obj):
        """Displays a list of facility names associated with the product."""
        facilities = Facility.objects.filter(facility_inventories__product_variant__product=obj)
        return ", ".join([facility.name for facility in facilities])
    facility_ids_display.short_description = 'Associated Facilities'

    def save_model(self, request, obj, form, change):
        # Save the Product instance first
        super().save_model(request, obj, form, change)


class ProductDetailAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'description', 'tags', 'image')

admin.site.register(ProductDetail, ProductDetailAdmin)

class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'slug', 'base_price', 'mrp', 'selling_price', 'is_active', 'product', 'attributes_display', 'facility_ids_display')
    search_fields = ('name', 'sku', 'product__name')
    list_filter = ('is_active', 'product')

    fieldsets = (
        ('Basic Information', {
            'fields': ('product', 'name', 'sku', 'description', 'tags')
        }),
        ('Pricing', {
            'fields': ('base_price', 'mrp', 'selling_price')
        }),
        ('Product Details', {
            'fields': ('ean_number', 'ran_number', 'hsn_code', 'tax', 'weight', 'net_qty', 'packaging_type')
        }),
        ('Attributes', {
            'fields': ('attributes',),
            'description': 'Store variant attributes like {"Size":"M", "Color":"Red"}'
        }),
        ('Packaging', {
            'fields': ('is_pack', 'pack_qty', 'pack_variant')
        }),
        ('Dimensions & Shelf Life', {
            'fields': ('product_dimensions', 'package_dimensions', 'shelf_life')
        }),
        ('Status', {
            'fields': ('is_active', 'is_b2b_enable', 'is_pp_enable', 'is_visible', 'is_published', 'is_rejected')
        }),
    )

    def product(self, obj):
        return obj.product.name
    product.short_description = 'Product Name'

    def attributes_display(self, obj):
        """Display attributes as formatted string"""
        if obj.attributes and isinstance(obj.attributes, dict):
            attr_pairs = [f"{key}: {value}" for key, value in obj.attributes.items()]
            return "; ".join(attr_pairs) if attr_pairs else "No attributes"
        return "No attributes"
    attributes_display.short_description = 'Attributes'

    def facility_ids_display(self, obj):
        """Displays a list of facilities associated with the variant."""
        facilities = Facility.objects.filter(facility_inventories__product_variant=obj)
        return ", ".join([facility.name for facility in facilities])
    facility_ids_display.short_description = 'Associated Facilities'


class ProductVariantImageAdmin(admin.ModelAdmin):
    list_display = ('product_variant', 'priority', 'is_primary', 'image', 'alt_text')
    search_fields = ('product_variant__name', 'alt_text')
    list_filter = ('product_variant', 'is_primary', 'priority')


# Register models in the admin interface
admin.site.register(Product, ProductAdmin)
admin.site.register(ProductVariant, ProductVariantAdmin)
admin.site.register(ProductVariantImage, ProductVariantImageAdmin)

class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'image', 'is_active', 'facilities_count')

    search_fields = ('name', 'description')

    filter_horizontal = ('products', 'facilities')

    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'products', 'facilities'),
        }),
    )

    def facilities_count(self, obj):
        """Display count of facilities assigned to this collection"""
        count = obj.facilities.count()
        return f"{count} facilities"
    facilities_count.short_description = 'Facilities'

admin.site.register(Collection, CollectionAdmin)


class ComboProductItemInline(admin.TabularInline):
    model = ComboProductItem
    extra = 1
    fields = ['product_variant', 'quantity', 'is_active']
    raw_id_fields = ['product_variant']


@admin.register(ComboProduct)
class ComboProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'combo_variant', 'get_combo_sku', 'get_items_count', 'is_active', 'creation_date')
    search_fields = ('name', 'combo_variant__name', 'combo_variant__sku')
    list_filter = ('is_active', 'creation_date')
    raw_id_fields = ['combo_variant']
    inlines = [ComboProductItemInline]

    fieldsets = (
        (None, {
            'fields': ('combo_variant', 'name', 'description', 'is_active')
        }),
    )

    def get_combo_sku(self, obj):
        """Display the SKU of the combo variant"""
        return obj.combo_variant.sku if obj.combo_variant else '-'
    get_combo_sku.short_description = 'Combo SKU'

    def get_items_count(self, obj):
        """Display count of items in the combo"""
        count = obj.combo_items.filter(is_active=True).count()
        return f"{count} items"
    get_items_count.short_description = 'Items'


@admin.register(ComboProductItem)
class ComboProductItemAdmin(admin.ModelAdmin):
    list_display = ('combo', 'product_variant', 'quantity', 'is_active')
    search_fields = ('combo__name', 'product_variant__name', 'product_variant__sku')
    list_filter = ('is_active',)
    raw_id_fields = ['combo', 'product_variant']


class AttributeValueInline(admin.TabularInline):
    model = AttributeValue
    extra = 1
    fields = ['value', 'rank', 'is_active']
    ordering = ['rank', 'value']


@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ['name', 'attribute_type', 'is_required', 'is_active', 'values_count', 'rank']
    list_filter = ['attribute_type', 'is_required', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['rank', 'name']
    list_editable = ['rank', 'is_active', 'is_required']
    inlines = [AttributeValueInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'attribute_type')
        }),
        ('Configuration', {
            'fields': ('is_required', 'is_active', 'rank')
        }),
    )

    def values_count(self, obj):
        count = obj.values.filter(is_active=True).count()
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if count > 0 else 'red',
            count
        )
    values_count.short_description = 'Active Values'


@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ['attribute', 'value', 'rank', 'is_active']
    list_filter = ['attribute', 'is_active']
    search_fields = ['value', 'attribute__name']
    ordering = ['attribute__name', 'rank', 'value']
    list_editable = ['rank', 'is_active']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('attribute')


class ProductTypeAttributeInline(admin.TabularInline):
    model = ProductTypeAttribute
    extra = 1
    fields = ['attribute', 'attribute_values']
    filter_horizontal = ['attribute_values']
    ordering = ['attribute__name']


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ['category', 'attributes_count', 'is_active']
    list_filter = ['category', 'is_active', 'category__parent']
    search_fields = ['category__name']
    ordering = ['category__name', 'is_active']
    inlines = [ProductTypeAttributeInline]

    fieldsets = (
        (None, {
            'fields': ('category',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def attributes_count(self, obj):
        count = obj.attributes.filter(is_active=True).count()
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if count > 0 else 'red',
            count
        )
    attributes_count.short_description = 'Active Attributes'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


# Custom admin actions
@admin.action(description='Activate selected items')
def make_active(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} items were successfully activated.')

@admin.action(description='Deactivate selected items')
def make_inactive(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} items were successfully deactivated.')

# Add actions to all relevant admin classes
AttributeAdmin.actions = [make_active, make_inactive]
AttributeValueAdmin.actions = [make_active, make_inactive]
ProductTypeAdmin.actions = [make_active, make_inactive]


# 
class CustomSectionInline(admin.TabularInline):
    model = CustomSection.tabs.through
    extra = 1
    fields = ['customsection', 'customtab']
    ordering = ['customsection', 'customtab']


class CustomFieldInline(admin.TabularInline):
    model = CustomField
    extra = 1
    fields = ['name', 'label', 'field_type', 'is_required', 'is_active', 'rank']
    ordering = ['rank', 'name']


@admin.register(CustomTab)
class CustomTabAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'sections_count', 'is_active', 'rank']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'description', 'category__name']
    ordering = ['category', 'rank', 'name']
    # inlines = [CustomSectionInline]  # Remove inline for ManyToMany
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'description')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'rank')
        }),
    )
    
    def sections_count(self, obj):
        count = obj.sections.count()
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if count > 0 else 'red',
            count
        )
    sections_count.short_description = 'Sections'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category').prefetch_related('sections')


@admin.register(CustomSection)
class CustomSectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'tabs_list', 'fields_count', 'is_collapsed', 'is_active', 'rank']
    list_filter = ['is_collapsed', 'is_active']
    search_fields = ['name', 'description', 'tabs__name', 'tabs__category__name']
    ordering = ['rank', 'name']
    inlines = [CustomFieldInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'tabs')
        }),
        ('Display Settings', {
            'fields': ('is_collapsed', 'is_active', 'rank')
        }),
    )
    
    def tabs_list(self, obj):
        return ", ".join([tab.name for tab in obj.tabs.all()])
    tabs_list.short_description = 'Tabs'
    
    def fields_count(self, obj):
        count = obj.fields.count()
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if count > 0 else 'red',
            count
        )
    fields_count.short_description = 'Fields'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tab', 'tab__category').prefetch_related('fields')


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'label', 'section', 'section_tab', 'field_type', 
        'is_required', 'has_options', 'is_active', 'rank'
    ]
    list_filter = [
        'field_type', 'is_required', 'is_active',
    ]
    search_fields = [
        'name', 'label', 'help_text', 'section__name',
    ]
    ordering = ['section__rank', 'rank', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('section', 'name', 'label', 'field_type')
        }),
        ('Field Configuration', {
            'fields': ('placeholder', 'help_text', 'default_value', 'options')
        }),
        ('Validation', {
            'fields': ('is_required', 'min_length', 'max_length')
        }),
        ('Display Settings', {
            'fields': ('width_class', 'is_active', 'rank')
        }),
    )
    
    def section_tab(self, obj):
        return ", ".join([tab.name for tab in obj.section.tabs.all()])
    section_tab.short_description = 'Tabs'
    
    def has_options(self, obj):
        has_opts = obj.options and len(obj.options) > 0
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if has_opts else 'gray',
            'Yes' if has_opts else 'No'
        )
    has_options.short_description = 'Has Options'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'section', 'section__tab', 'section__tab__category'
        )
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'options':
            kwargs['help_text'] = 'JSON format: ["Option 1", "Option 2"] or [{"label": "Display", "value": "stored_value"}]'
        return super().formfield_for_dbfield(db_field, request, **kwargs)


# Optional: Create a custom admin action to duplicate tabs
@admin.action(description='Duplicate selected tabs')
def duplicate_tabs(modeladmin, request, queryset):
    for tab in queryset:
        # Create new tab
        new_tab = CustomTab.objects.create(
            category=tab.category,
            name=f"{tab.name} (Copy)",
            description=tab.description,
            is_active=False,  # Make copy inactive by default
            rank=tab.rank + 1
        )
        
        # Copy sections
        for section in tab.sections.all():
            new_section = CustomSection.objects.create(
                tab=new_tab,
                name=section.name,
                description=section.description,
                is_collapsed=section.is_collapsed,
                is_active=section.is_active,
                rank=section.rank
            )
            
            # Copy fields
            for field in section.fields.all():
                CustomField.objects.create(
                    section=new_section,
                    name=field.name,
                    label=field.label,
                    field_type=field.field_type,
                    placeholder=field.placeholder,
                    help_text=field.help_text,
                    default_value=field.default_value,
                    options=field.options,
                    is_required=field.is_required,
                    min_length=field.min_length,
                    max_length=field.max_length,
                    width_class=field.width_class,
                    is_active=field.is_active,
                    rank=field.rank
                )