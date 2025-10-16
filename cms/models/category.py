from django.db import models
from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.dispatch import receiver
from .models import TenantModel, BaseModel, ImageStorage
from cms.utils.image_processing import process_webp_images, cleanup_images, cleanup_old_images

class Category(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    # parent = parent id (self reference)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    rank = models.PositiveIntegerField(default=0)
    shelf_life_required = models.BooleanField(
        default=False,
        help_text="Whether products in this category require shelf life date"
    )

    class Meta:
        db_table = 'categories'
        ordering = ['name']
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        # return self.name
        return f"{self.parent.name} / {self.name}" if self.parent_id else self.name



# class Subcategory(BaseModel):
#     name = models.CharField(max_length=100)
#     description = models.TextField(blank=True, null=True)
#     category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
#     image = models.TextField(blank=True, null=True)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         db_table = 'subcategories'
#         ordering = ['category__name', 'name']
#         verbose_name_plural = 'Subcategories'
    
#     def __str__(self):
#         return f"{self.name} - {self.category.name}"


# class Subsubcategory(BaseModel):
#     name = models.CharField(max_length=100)
#     description = models.TextField(blank=True, null=True)
#     category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subsubcategories')
#     subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name='subsubcategories')
#     image = models.TextField(blank=True, null=True)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         db_table = 'subsubcategories'
#         ordering = ['name']
#         verbose_name_plural = 'Subsubcategories'
    
#     def __str__(self):
#         return f"{self.name} - {self.subcategory.name} - {self.category.name}"


class Brand(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'brands'
        ordering = ['name']
        verbose_name_plural = 'Brands'
    
    def __str__(self):
        return self.name