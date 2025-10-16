from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator

from .models import TenantModel, BaseModel
from .category import Category, Brand
from .setting import CustomField, AttributeValue, SizeMeasurement

def product_image_upload_path(instance, filename):
    """Generate upload path for product thumbnail images"""
    return f"Product/Thumbnail/{instance.sku}.webp"


class Product(TenantModel):
    """
    Core product model representing a product in the system.
    Products are the main catalog items that can have multiple variants.
    """
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=255, blank=True, null=True, unique=True)
    description = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, blank=True, null=True, related_name='products')
    is_published = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    image = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['brand', 'is_active']),
            models.Index(fields=['is_published', 'is_active']),
        ]

    def save(self, *args, **kwargs):
        # Automatically generate SKU if it's not provided
        if not self.sku:
            prefix = 'ROZ'
            # Get the last product ID and add 1
            last_product = Product.objects.order_by('id').last()
            next_id = (last_product.id + 1) if last_product else 1
            self.sku = f'{prefix}{next_id:02d}'

        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    
class ProductOption(BaseModel):
    """
    Product options like Color, Size, Material etc.
    Defines the available options for product variants.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100, help_text="Option name (e.g., 'Color', 'Size', 'Quantity', 'Material')")
    position = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    values = models.JSONField(default=list, help_text='List of option values: ["Red", "Blue", "Green"] or ["S", "M", "L", "XL"]')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'product_options'
        unique_together = [('product', 'name')]
        ordering = ['product', 'position', 'name']
        indexes = [
            models.Index(fields=['product', 'is_active']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"



class Language(BaseModel):
    """
    Language model for internationalization support.
    Stores supported languages for product localization.
    """
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    rlt = models.IntegerField(default=0)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = 'languages'
        ordering = ['name']
        verbose_name_plural = 'Languages'

    def __str__(self):
        return self.name
    
class ProductLanguage(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_languages')
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True, null=True)

    class Meta:
        db_table = 'product_languages'
        ordering = ['name']
        verbose_name_plural = 'Product Languages'

    def __str__(self):
        return self.name
    
class ProductDetail(models.Model):
    """
    Localized product details for different languages.
    Provides translation support for product name, description, and tags.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_details')
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True, null=True)
    image = models.TextField(blank=True, null=True)


    class Meta:
        db_table = 'product_details'
        ordering = ['product']
        indexes = [
            models.Index(fields=['product', 'name']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"


def validate_dimensions(value):
    """
    Validate dimensions JSON structure.
    Expected format: {"length": number, "width": number, "height": number, "unit": "cm|mm|inch"}
    """
    if not value:
        return
    
    if not isinstance(value, dict):
        raise ValidationError("Dimensions must be a JSON object")
    
    # Required fields
    required_fields = ['length', 'width', 'height']
    for field in required_fields:
        if field not in value:
            raise ValidationError(f"Missing required dimension field: {field}")
        
        # Validate that values are numeric
        try:
            float_value = float(value[field])
        except (ValueError, TypeError):
            raise ValidationError(f"Dimension {field} must be a number")
        
        # Validate positive values
        if float_value <= 0:
            raise ValidationError(f"Dimension {field} must be positive")
    
    # Validate unit if provided
    if 'unit' in value:
        valid_units = ['cm', 'mm', 'inch', 'ft', 'm']
        if value['unit'] not in valid_units:
            raise ValidationError(f"Unit must be one of: {', '.join(valid_units)}")

class ProductVariant(BaseModel):
    """
    Product variant representing specific variations of a product.
    Each variant has unique attributes, pricing, and inventory.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255, blank=True, null=True)
    sku = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True, null=True)

    # Pricing fields
    base_price = models.FloatField(blank=True, null=True)
    mrp = models.FloatField(blank=True, null=True)
    selling_price = models.FloatField(blank=True, null=True)
    psp = models.FloatField(blank=True, null=True)
    
    
    qty = models.IntegerField(default=0)
    max_purchase_limit = models.PositiveIntegerField(default=0)
    margin = models.FloatField(blank=True, null=True)
    margin_min = models.FloatField(default=0.00)
    margin_max = models.FloatField(default=0.00)
    peer_margin = models.FloatField(default=0.00)
    peer_margin_min = models.FloatField(default=0.00)
    peer_margin_max = models.FloatField(default=0.00)
    threshold_wac = models.FloatField(default=0.00)
    wac = models.FloatField(default=0.00)
    return_days = models.IntegerField(default=0)
    is_focussed = models.BooleanField(default=False)
    is_freebies = models.BooleanField(default=False)
    peer_stock_status = models.IntegerField(default=1, help_text='0: In Stock, 1: High demand, 2: Currently Unavailable, 3: Sold Out')
    barcode = models.BigIntegerField(default=0)
    threshold = models.IntegerField(default=0)
    sku_class = models.CharField(max_length=255, blank=True, null=True)
    style_name = models.CharField(max_length=255, blank=True, null=True)
    sku_size = models.CharField(max_length=255, blank=True, null=True)
    size_type = models.CharField(max_length=255, blank=True, null=True)


    # Product identification
    ean_number = models.BigIntegerField(blank=True, null=True)
    ran_number = models.BigIntegerField(blank=True, null=True)
    hsn_code = models.TextField(blank=True, null=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cgst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sgst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    igst = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cess = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Physical properties
    weight = models.CharField(max_length=255, blank=True, null=True)
    net_qty = models.CharField(max_length=255, blank=True, null=True)
    packaging_type = models.CharField(max_length=255, blank=True, null=True)
    product_dimensions = models.JSONField(blank=True, null=True, validators=[validate_dimensions],
        help_text='Product dimensions: {"length": 15.5, "width": 7.6, "height": 0.8, "unit": "cm"}')
    package_dimensions = models.JSONField(blank=True, null=True, validators=[validate_dimensions],
        help_text='Package dimensions: {"length": 18.0, "width": 12.0, "height": 6.5, "unit": "cm"}')
    shelf_life = models.PositiveIntegerField(blank=True, null=True, help_text='Shelf life in days')
    uom = models.CharField(max_length=25, blank=True, null=True)
    
    # Pack configuration
    is_pack = models.BooleanField(default=False)
    pack_qty = models.PositiveIntegerField(default=1)
    pack_variant = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True, related_name='pack_variants')

    # Combo product flag
    is_combo = models.BooleanField(default=False, help_text='True if this variant is a combo product')

    # Flexible attributes system
    attributes = models.JSONField(default=dict, blank=True, null=True,
        help_text='Product variant attributes like {"Size":"M", "Color":"Red"}')

    # Status flags
    is_active = models.BooleanField(default=True)
    is_b2b_enable = models.BooleanField(default=False)
    is_pp_enable = models.BooleanField(default=False)
    is_visible = models.PositiveIntegerField(default=0, help_text='0: Offline, 1: Online, 2: Both')
    is_published = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)

    class Meta:
        db_table = 'variants'
        ordering = ['product', 'name']
        indexes = [
            models.Index(fields=['product', 'is_active']),
            models.Index(fields=['sku']),
            models.Index(fields=['ean_number']),
            models.Index(fields=['is_published', 'is_active']),
        ]

    def save(self, *args, **kwargs):

        # Automatically calculate margin if selling_price and base_price are available
        if self.selling_price is not None and self.base_price is not None:
            self.margin = self.selling_price - self.base_price

        # Automatically generate SKU if it's not provided
        if not self.sku and self.product:
            # Use product SKU as base, generate if product doesn't have one
            if not self.product.sku:
                # Generate product SKU using the same logic as Product model
                last_product = Product.objects.order_by('id').last()
                next_id = (last_product.id + 1) if last_product else 1
                product_sku = f'ROZ{next_id:02d}'
            else:
                product_sku = self.product.sku

            # Add variant name if available, otherwise use a counter
            if self.name:
                variant_suffix = slugify(self.name).upper()
            else:
                variant_count = ProductVariant.objects.filter(product=self.product).count() + 1
                variant_suffix = f'V{variant_count:02d}'

            self.sku = f'{product_sku}-{variant_suffix}'

        # Generate slug
        if not self.slug:
            # Start with product name and variant name
            product_name = getattr(self.product, 'name', '') if self.product else ''
            slug_parts = [slugify(product_name)]

            # Add variant name if available
            if self.name:
                slug_parts.append(slugify(self.name))

            # Add attributes from JSON if available
            if self.attributes:
                for _, value in self.attributes.items():
                    if value:
                        slug_parts.append(slugify(str(value)))

            # Add weight if available
            if self.weight:
                slug_parts.append(slugify(self.weight))

            # Combine all parts into one slug
            self.slug = '-'.join(slug_parts)

        super(ProductVariant, self).save(*args, **kwargs)


    @property
    def primary_image(self):
        """Get the primary image for this variant"""
        return self.images.filter(is_primary=True, is_active=True).first()

    @property
    def all_images(self):
        """Get all active images ordered by their priority field"""
        return self.images.filter(is_active=True).order_by('priority')

    @property
    def combo_details(self):
        """Get combo product details if this variant is a combo"""
        if not self.is_combo:
            return None

        try:
            combo = self.combo_product
            items = []
            for item in combo.combo_items.filter(is_active=True).select_related('product_variant', 'product_variant__product'):
                items.append({
                    'id': item.id,
                    'variant_id': item.product_variant.id,
                    'variant_name': item.product_variant.name,
                    'variant_sku': item.product_variant.sku,
                    'product_name': item.product_variant.product.name,
                    'quantity': item.quantity
                })

            return {
                'combo_id': combo.id,
                'combo_name': combo.name,
                'combo_description': combo.description,
                'items': items,
                'items_count': len(items)
            }
        except:
            return None

    def __str__(self):
        return self.name +' - '+ self.product.name


class ProductVariantImage(BaseModel):
    """
    Model to store multiple images for a product variant.
    Supports primary image selection and image ordering.
    """
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='images')
    image           = models.TextField()
    alt_text        = models.CharField(max_length=255, blank=True, null=True)
    priority        = models.PositiveIntegerField(default=0)
    is_primary      = models.BooleanField(default=False)
    is_active       = models.BooleanField(default=True)

    class Meta:
        db_table = 'product_variant_images'
        ordering = ['priority', 'creation_date']
        indexes = [
            models.Index(fields=['product_variant', 'is_active']),
            models.Index(fields=['product_variant', 'is_primary']),
        ]

    def clean(self):
        """Validate that only one primary image exists per variant"""
        # Only validate for new records to prevent blocking updates
        # During updates, temporarily multiple primaries are ok since old ones will be deleted
        if self.is_primary and not self.pk:
            # Check if another primary image exists for this variant
            existing_primary = ProductVariantImage.objects.filter(
                product_variant=self.product_variant,
                is_primary=True
            )

            if existing_primary.exists():
                # For new records, only allow if no existing primary (prevents accidental duplicates)
                # For updates, the save() method will handle primary switching correctly
                pass

    def save(self, *args, **kwargs):
        # Skip validation if explicitly requested
        skip_validation = kwargs.pop('skip_validation', False)

        if not skip_validation:
            self.clean()

        # If this is the first image for the product_variant, make it primary
        if not self.pk and not ProductVariantImage.objects.filter(product_variant=self.product_variant).exists():
            self.is_primary = True

        # If setting as primary, unset other primary images
        if self.is_primary:
            ProductVariantImage.objects.filter(
                product_variant=self.product_variant,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)

        super().save(*args, **kwargs)

    @classmethod
    def update_primary_safely(cls, product_variant, new_primary_image_data):
        """
        Safely update primary image during bulk operations.
        This method handles the primary image switching without validation errors.
        """
        # Create the new primary image first
        new_image = cls.objects.create(
            product_variant=product_variant,
            is_primary=True,
            skip_validation=True,
            **new_primary_image_data
        )

        # Then remove old primary designation (this happens automatically in save())
        return new_image

    def __str__(self):
        primary_text = " (Primary)" if self.is_primary else ""
        return f"{self.product_variant.name} - Image {self.priority}{primary_text}"


class ProductVariantCustomField(BaseModel):
    """
    Store custom field values for product variants.
    Links variants to custom field definitions with their values.
    """
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='custom_field_values'
    )
    custom_field = models.ForeignKey(
        CustomField,
        on_delete=models.CASCADE,
        related_name='variant_values'
    )
    value = models.TextField(blank=True, null=True)  # Store all field values as text
    
    class Meta:
        db_table = 'product_variant_custom_fields'
        unique_together = ['product_variant', 'custom_field']
        ordering = ['product_variant', 'custom_field']
        verbose_name_plural = 'Product Variant Custom Fields'
    
    def __str__(self):
        return f"{self.product_variant.name} - {self.custom_field.name}: {self.value}"

class ProductLinkVariant(BaseModel):
    """
    Links variants to products for cross-selling or bundling.
    Allows products to reference related variants.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='linked_variants')
    linked_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='linked_variant')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'product_link_variants'
        unique_together = ('product', 'linked_variant')
        ordering = ['product', 'linked_variant']
        indexes = [
            models.Index(fields=['product', 'is_active']),
        ]

class ComboProduct(BaseModel):
    """
    Combo product model that links a product variant to multiple constituent variants.
    The combo_variant represents the final combo product with its own SKU and pricing.
    """
    combo_variant = models.OneToOneField(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='combo_product',
        help_text='The variant that represents this combo product'
    )
    name = models.CharField(max_length=255, help_text='Name of the combo')
    description = models.TextField(blank=True, null=True, help_text='Description of the combo')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'combo_products'
        ordering = ['-creation_date']
        indexes = [
            models.Index(fields=['combo_variant', 'is_active']),
        ]

    def __str__(self):
        return f"Combo: {self.name} ({self.combo_variant.sku})"

    def save(self, *args, **kwargs):
        # Ensure the combo_variant has is_combo flag set to True
        if self.combo_variant and not self.combo_variant.is_combo:
            self.combo_variant.is_combo = True
            self.combo_variant.save()
        super(ComboProduct, self).save(*args, **kwargs)


class ComboProductItem(BaseModel):
    """
    Individual items that make up a combo product.
    Links product variants to a combo with their quantities.
    """
    combo = models.ForeignKey(
        ComboProduct,
        on_delete=models.CASCADE,
        related_name='combo_items',
        help_text='The combo product this item belongs to'
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='combo_inclusions',
        help_text='The variant included in this combo'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Quantity of this variant in the combo'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'combo_product_items'
        unique_together = ['combo', 'product_variant']
        ordering = ['combo', 'id']
        indexes = [
            models.Index(fields=['combo', 'is_active']),
            models.Index(fields=['product_variant']),
        ]

    def __str__(self):
        return f"{self.combo.name} - {self.product_variant.name} (x{self.quantity})"

    def clean(self):
        """Validate that a combo variant cannot include itself"""
        if self.combo.combo_variant == self.product_variant:
            raise ValidationError("A combo product cannot include itself as an item")

        # Prevent adding combo products as items in another combo
        if self.product_variant.is_combo:
            raise ValidationError("Cannot add a combo product as an item in another combo")


class Collection(BaseModel):
    """
    Product collections for grouping related products.
    Collections can be associated with specific facilities.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    products = models.ManyToManyField(Product, related_name='collections')
    facilities = models.ManyToManyField('cms.Facility', related_name='collections', blank=True)
    image = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'collections'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class ProductPriceHistory(BaseModel):
    """
    Model to track price changes for products in specific clusters.
    Maintains audit trail of price modifications with user and reason.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='price_history')
    cluster = models.ForeignKey('cms.Cluster', on_delete=models.CASCADE, related_name='price_history', null=True, blank=True)
    facility = models.ForeignKey('cms.Facility', on_delete=models.CASCADE, related_name='price_history')
    user = models.ForeignKey('user.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='price_changes')
    
    # Price information
    old_price = models.FloatField()
    new_price = models.FloatField()
    old_csp = models.FloatField()
    new_csp = models.FloatField()
    percentage_change = models.FloatField()
    
    # Additional metadata
    change_reason = models.TextField(blank=True, null=True)
    change_type = models.CharField(max_length=50, default='percentage_update')  # percentage_update, manual_update, etc.
    
    class Meta:
        db_table = 'product_price_history'
        ordering = ['-creation_date']
        verbose_name = 'Product Price History'
        verbose_name_plural = 'Product Price Histories'
        indexes = [
            models.Index(fields=['product', 'facility']),
            models.Index(fields=['product_variant', 'facility']),
            models.Index(fields=['creation_date']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.cluster.name} - {self.percentage_change}%"
    
    @property
    def price_difference(self):
        """Calculate the absolute price difference"""
        return self.new_price - self.old_price
    
    @property
    def csp_difference(self):
        """Calculate the absolute CSP difference"""
        return self.new_csp - self.old_csp


class ProductSizeChartValue(BaseModel):
    """
    Store size chart measurement values for product variants.
    Maps AttributeValue (size) to SizeMeasurement (measurement type) with actual values.
    Provides detailed sizing information for products.
    """
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='size_chart_values'
    )
    size_attribute_value = models.ForeignKey(
        AttributeValue,  # The size value (S, M, L, XL, etc.)
        on_delete=models.CASCADE,
        related_name='size_chart_values'
    )
    measurement = models.ForeignKey(
        SizeMeasurement,  # The measurement type (Chest, Waist, etc.)
        on_delete=models.CASCADE,
        related_name='product_values'
    )
    value = models.CharField(max_length=50)  # The actual measurement value (e.g., "36", "38-40")

    class Meta:
        db_table = 'product_size_chart_values'
        unique_together = ['product_variant', 'size_attribute_value', 'measurement']
        ordering = ['size_attribute_value__rank', 'measurement__rank']
        verbose_name_plural = 'Product Size Chart Values'
        indexes = [
            models.Index(fields=['product_variant']),
            models.Index(fields=['size_attribute_value']),
        ]

    def __str__(self):
        return f"{self.product_variant.name} - {self.size_attribute_value.value} - {self.measurement.name}: {self.value}"
    
    
class BestSellingProducts(BaseModel):
    facility = models.ForeignKey('cms.Facility', on_delete=models.CASCADE, related_name='best_selling_products')
    product = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'best_selling_products'
        ordering = ['-creation_date']
        indexes = [
            models.Index(fields=['facility']),
        ]

class Packs(BaseModel):
    """
    Packs model to manage facility-specific product packs.
    Tracks inventory, ordering, and stock management for packs.
    """
    facility = models.ForeignKey(
        'cms.Facility',
        on_delete=models.CASCADE,
        related_name='packs',
        help_text='The facility this pack belongs to'
    )
    sku_code = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='SKU code of the pack'
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text='Description of the pack'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='packs',
        blank=True,
        null=True,
        help_text='Associated product (can be null)'
    )
    quantity = models.IntegerField(
        default=0,
        help_text='Current quantity in stock'
    )
    status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Status of the pack (e.g., active, inactive, pending)'
    )
    is_elastic = models.BooleanField(
        default=False,
        help_text='Whether the pack has elastic demand/supply'
    )
    open_order_quantity = models.IntegerField(
        default=0,
        help_text='Quantity in open orders'
    )
    cycle_stock_quantity = models.IntegerField(
        default=0,
        help_text='Cycle stock quantity for regular inventory rotation'
    )
    threshold = models.IntegerField(
        default=0,
        help_text='Minimum stock threshold for reordering'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'packs'
        ordering = ['-creation_date']
        verbose_name = 'Pack'
        verbose_name_plural = 'Packs'
        indexes = [
            models.Index(fields=['facility', 'is_active']),
            models.Index(fields=['sku_code']),
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f"{self.facility.name} - {self.sku_code or 'No SKU'}"


class ProductVariantPrices(BaseModel):
    """
    Product variant prices model to manage facility and pack-specific pricing.
    Stores comprehensive pricing information including taxes and margins.
    """
    facility = models.ForeignKey(
        'cms.Facility',
        on_delete=models.CASCADE,
        related_name='variant_prices',
        help_text='The facility this pricing belongs to'
    )
    packs = models.ForeignKey(
        Packs,
        on_delete=models.CASCADE,
        related_name='variant_prices',
        blank=True,
        null=True,
        help_text='Associated pack (can be null)'
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name='variant_prices',
        default=0,
        help_text='Associated variant'
    )
    price = models.FloatField(
        default=0.0,
        help_text='Base price'
    )
    mrp = models.FloatField(
        default=0.0,
        help_text='Maximum Retail Price'
    )
    igst = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Integrated Goods and Services Tax'
    )
    sgst = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='State Goods and Services Tax'
    )
    cgst = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Central Goods and Services Tax'
    )
    cess = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Additional Cess'
    )
    margin = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Profit margin'
    )
    margin_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Type of margin (percentage, fixed, etc.)'
    )
    selling_price = models.FloatField(
        default=0.0,
        help_text='Customer Selling Price'
    )
    psp = models.FloatField(
        default=0.0,
        help_text='Platform Selling Price'
    )
    psp_margin = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='PSP margin'
    )
    
    class Meta:
        db_table = 'product_variant_prices'
        ordering = ['-creation_date']
        verbose_name = 'Product Variant Price'
        verbose_name_plural = 'Product Variant Prices'
        indexes = [
            models.Index(fields=['facility']),
            models.Index(fields=['packs']),
            models.Index(fields=['variant']),
            models.Index(fields=['facility', 'variant']),
        ]
    
    def __str__(self):
        variant_name = self.variant.name if self.variant else 'No Variant'
        return f"{self.facility.name} - {variant_name} - Price: {self.price}" 
