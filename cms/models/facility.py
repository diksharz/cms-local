from django.db import models
from .models import TenantModel, BaseModel
from .product import ProductVariant
from .master import Tax
from django.core.exceptions import ValidationError
from .category import Category


class Cluster(BaseModel):
    name        = models.CharField(max_length=255)
    latitude    = models.TextField(blank=True, null=True)
    longitude   = models.TextField(blank=True, null=True)
    region      = models.CharField(max_length=255, blank=True, null=True)
    facilities  = models.ManyToManyField('Facility', related_name='clusters', blank=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table = 'clusters'
        unique_together = ('name',)

    def __str__(self):
        return self.name



class Facility(TenantModel):

    FACILITY_TYPES = [
        ('store', 'Store'),
        ('warehouse', 'Warehouse'),
    ]

    managers        = models.ManyToManyField('user.User', blank=True, related_name='managed_facilities')
    facility_type   = models.CharField(max_length=100, choices=FACILITY_TYPES)
    name            = models.CharField(max_length=255)
    address         = models.CharField(max_length=255)
    city            = models.CharField(max_length=100)
    state           = models.CharField(max_length=100)
    country         = models.CharField(max_length=100)
    pincode         = models.CharField(max_length=100)
    email           = models.CharField(max_length=100, blank=True, null=True)
    phone_number    = models.CharField(max_length=15, blank=True, null=True)
    customer_care   = models.CharField(max_length=20, blank=True, null=True)
    cin_no          = models.TextField(blank=True, null=True)
    gstn_no         = models.TextField(blank=True, null=True)
    fssai_no        = models.TextField(blank=True, null=True)
    latitude        = models.CharField(max_length=100, blank=True, null=True)
    longitude       = models.CharField(max_length=100, blank=True, null=True)
    servicable_area = models.TextField(default=list, blank=True, null=True)
    is_active       = models.BooleanField(default=True)

    class Meta:
        db_table = 'facilities'
        unique_together = ('name',)

    def __str__(self):
        return self.name
    
    def clean(self):
        super().clean()
        # Only validate if the object already exists (has a pk)
        if self.pk and self.managers.exists():
            for manager in self.managers.all():
                if Facility.objects.exclude(id=self.id).filter(managers=manager).exists():
                    raise ValidationError(f"{manager} is already assigned to another facility.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class GeoMapping(BaseModel):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='geo_mappings')
    center_coords = models.TextField(blank=True, null=True)
    coordinates = models.TextField(default=list)
    address = models.TextField(blank=True, null=True)
    fencing_names = models.TextField(default=dict,blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'geo_mappings'

    def __str__(self):
        return f"{self.facility.name} - {self.center_coords}"

class FacilityInventory(BaseModel):

    facility        = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='facility_inventories')
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='facility_inventories')
    stock           = models.IntegerField(default=0)
    tax             = models.ForeignKey(Tax, on_delete=models.CASCADE, blank=True, null=True)
    base_price      = models.FloatField(default=0.0)
    mrp             = models.FloatField(default=0.0)
    selling_price   = models.FloatField(default=0.0)
    cust_discount   = models.FloatField(blank=True, null=True)
    max_purchase_limit      = models.IntegerField(blank=True, null=True)
    outofstock_threshold    = models.IntegerField(blank=True, null=True)
    status          = models.CharField(max_length=100, blank=True, null=True)
    is_active       = models.BooleanField(default=True)

    class Meta:
        db_table = 'facility_inventories'
        unique_together = ('facility', 'product_variant')

    def save(self, *args, **kwargs):
        # If mrp or selling_price is not provided, set them to 0
        if self.mrp is None:
            self.mrp = ProductVariant.objects.get(id=self.product_variant.id).mrp or 0.0
        if self.base_price is None:
            self.base_price = ProductVariant.objects.get(id=self.product_variant.id).base_price or 0.0
        if self.selling_price is None:
            self.selling_price = ProductVariant.objects.get(id=self.product_variant.id).selling_price or 0.0

        # Calculate cust_discount if it's not already set
        if self.cust_discount is None:
            self.cust_discount = int(self.mrp - self.selling_price)  # Calculate discount

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.facility.name} - {self.product_variant.name}"

class FacilityCategorys(BaseModel):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='facility_categorys')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='facility_main_categories', null=True, blank=True)
    sub_category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='facility_sub_categories', null=True, blank=True)
    sub_sub_category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='facility_sub_sub_categories', null=True, blank=True)
    discount_upto = models.FloatField(default=0.0)
    status = models.BooleanField(default=True)
    arrange = models.BooleanField(default=False)
    is_b2b_enabled = models.BooleanField(default=False)
    is_top_offer_categoty = models.BooleanField(default=False)
    discount_percentsge_off = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'facility_categorys'
        unique_together = ('facility', 'category', 'sub_category', 'sub_sub_category')

    def __str__(self):
        category_name = self.category.name if self.category else 'No Category'
        return f"{self.facility.name} - {category_name}"
    
class FacilityStaff(BaseModel):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='facility_staff')
    staff = models.ForeignKey('user.Staff', on_delete=models.CASCADE, related_name='facility_staff')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'facility_staff'
        unique_together = ('facility', 'staff')

    def __str__(self):
        return f"{self.staff.user} - {self.facility.name}"


class FacilityManager(BaseModel):
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='facility_managers')
    user = models.ForeignKey('user.User', on_delete=models.CASCADE, related_name='facility_managers')
    phone = models.CharField(max_length=25, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'facility_managers'
        unique_together = ('facility', 'user')

    def __str__(self):
        return f"{self.user} - {self.facility.name}"