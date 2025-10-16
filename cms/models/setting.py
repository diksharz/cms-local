# models.py

from django.db import models
from .models import TenantModel, BaseModel
from django.core.exceptions import ValidationError
from cms.models.category import Category


# Attribute model - defines attribute names like "Size", "Color", etc.
class Attribute(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    rank = models.PositiveIntegerField(default=0)
    ATTRIBUTE_TYPES = [
        ('select', 'Select (Single Choice)'),
        ('multiselect', 'Multi Select'),
        ('text', 'Text Input'),
    ]
    attribute_type = models.CharField(
        max_length=20, 
        choices=ATTRIBUTE_TYPES, 
        default='select'
    )

    class Meta:
        db_table = 'attributes'
        ordering = ['rank', 'name']
        verbose_name_plural = 'Attributes'

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip().title()


# AttributeValue model - stores values for each attribute
class AttributeValue(BaseModel):
    attribute = models.ForeignKey(
        Attribute, 
        on_delete=models.CASCADE, 
        related_name='values'
    )
    value = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    rank = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'attribute_values'
        ordering = ['rank', 'value']
        unique_together = ['attribute', 'value']
        verbose_name_plural = 'Attribute Values'

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"

    def clean(self):
        super().clean()
        if self.value:
            self.value = self.value.strip()


# ProductType model - configuration that links categories to attributes
class ProductType(BaseModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='product_types'
    )
    attributes = models.ManyToManyField(
        Attribute,
        through='ProductTypeAttribute',
        related_name='product_types',
        blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'product_types'
        unique_together = ['category']
        verbose_name_plural = 'Product Types'

    def __str__(self):
        return f"{self.category.name} - {self.id}"


# Intermediate model to store specific attribute values per product type
class ProductTypeAttribute(BaseModel):
    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.CASCADE,
        related_name='product_type_attributes'
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='product_type_attributes'
    )
    attribute_values = models.ManyToManyField(
        AttributeValue,
        related_name='product_type_attributes',
        blank=True,
        help_text="Specific attribute values allowed for this product type. If empty, all values are allowed."
    )

    class Meta:
        db_table = 'product_type_attributes'
        unique_together = ['product_type', 'attribute']
        verbose_name_plural = 'Product Type Attributes'

    def __str__(self):
        return f"{self.product_type.category.name} - {self.attribute.name}"


class SizeChart(BaseModel):
    """
    Size Chart configuration for different categories
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='size_charts'
    )
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='size_charts'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'size_charts'
        unique_together = ['category']  # One size chart per category
        ordering = ['name']
        verbose_name_plural = 'Size Charts'
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class SizeMeasurement(BaseModel):
    """
    Individual measurements for a size chart (Chest, Brand, Size, etc.)
    """
    size_chart = models.ForeignKey(
        SizeChart,
        on_delete=models.CASCADE,
        related_name='measurements'
    )
    name = models.CharField(max_length=50)  # Chest, Brand, Size, Shoulder, etc.
    unit = models.CharField(max_length=20, default='inches')  # inches, cm, etc.
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    rank = models.PositiveIntegerField(default=0)  # Display order
    
    class Meta:
        db_table = 'size_measurements'
        unique_together = ['size_chart', 'name']
        ordering = ['rank', 'name']
        verbose_name_plural = 'Size Measurements'
    
    def __str__(self):
        return f"{self.size_chart.name} - {self.name}"
    
    
# Custom Tabs, Sections, and Fields for Product Detail Page
class CustomTab(BaseModel):
    """
    Custom Tab for Product Detail Page
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='tabs'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    rank = models.PositiveIntegerField(default=0)  # Display order

    class Meta:
        db_table = 'custom_tabs'
        ordering = ['rank', 'name']
        verbose_name_plural = 'Custom Tabs'

    def __str__(self):
        return self.name
    
class CustomSection(BaseModel):
    """
    Custom Section within a Tab
    """
    tabs = models.ManyToManyField(
        CustomTab,
        related_name='sections',
        blank=True
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_collapsed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    rank = models.PositiveIntegerField(default=0)  # Display order

    class Meta:
        db_table = 'custom_sections'
        ordering = ['rank', 'name']
        verbose_name_plural = 'Custom Sections'

    def __str__(self):
        tab_names = ', '.join([tab.name for tab in self.tabs.all()])
        return f"{tab_names} - {self.name}" if tab_names else self.name
    
class CustomField(BaseModel):
    """
    Custom Field within a Section
    """
    section = models.ForeignKey(
        CustomSection,
        on_delete=models.CASCADE,
        related_name='fields'
    )
    FIELD_TYPES = [
        ('text', 'Text'),
        ('textarea', 'Textarea'),
        ('richtext', 'Rich Text'),
        ('number', 'Number'),
        ('decimal', 'Decimal'),
        ('image', 'Image'),
        ('file', 'File'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
        ('time', 'Time'),
        ('boolean', 'Yes/No'),
        ('select', 'Dropdown'),
        ('multiselect', 'Multi Select'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkboxes'),
    ]
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=100)  # Display label for users
    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPES,
        default='text'
    )
    placeholder = models.CharField(max_length=200, blank=True, null=True)
    help_text = models.TextField(blank=True, null=True)
    default_value = models.TextField(blank=True, null=True)
    options = models.JSONField(default=list, blank=True, null=True)  # Store option1, option2, etc. for select fields
    is_required = models.BooleanField(default=False)
    min_length = models.PositiveIntegerField(blank=True, null=True)
    max_length = models.PositiveIntegerField(blank=True, null=True)
    width_class = models.CharField(max_length=20, default='col-12')  # Bootstrap classes
    is_active = models.BooleanField(default=True)
    rank = models.PositiveIntegerField(default=0)  # Display order

    class Meta:
        db_table = 'custom_fields'
        ordering = ['rank', 'name']
        verbose_name_plural = 'Custom Fields'

    def __str__(self):
        return f"{self.section.name} - {self.name}"
    
