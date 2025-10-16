from django.db import models
# from django.core.files.base import ContentFile
# from django.db.models.signals import pre_delete, pre_save, post_save
# from django.dispatch import receiver
from .models import TenantModel, BaseModel, ImageStorage
# from cms.utils.image_processing import convert_to_webp, process_webp_images, cleanup_images, cleanup_old_images
from .product import Product


class ProductImage(BaseModel):
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='product_images'
    )
    priority    = models.PositiveIntegerField(default=1)
    image       = models.TextField()
    alt_text    = models.CharField(max_length=255, blank=True, null=True)
    is_primary  = models.BooleanField(default=False)

    class Meta:
        db_table = 'product_images'
        ordering = ['priority', 'id']
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def __str__(self):
        return f"{self.product.name} - Image {self.priority}"

    @property
    def processed_image_filename(self):
        """Return the processed image filename for admin display"""
        try:
            if self.product and self.product.sku and self.priority:
                return f"{self.product.sku}_{self.priority}.webp"
        except:
            pass
        return "Not processed yet"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_product_image_urls()

    def _update_product_image_urls(self):
        try:
            images = ProductImage.objects.filter(product=self.product).order_by('priority')
            image_urls = [img.image.url for img in images if img.image]
            Product.objects.filter(pk=self.product.pk).update(image_url=image_urls)
        except Exception as e:
            print(f"Warning: Could not update product image URLs: {e}")

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        try:
            images = ProductImage.objects.filter(product=product).order_by('priority')
            image_urls = [img.image.url for img in images if img.image]
            from cms.models.product import Product
        except Exception as e:
            print(f"Warning: Could not update product image URLs after deletion: {e}")


# @receiver(post_save, sender=ProductImage)
# def process_product_image_async(sender, instance, created, **kwargs):
#     if instance.image and hasattr(instance.image, 'name'):
#         process_webp_images(instance, 'ProductImages', [(500, 500), (600, 600), (800, 800)])


# @receiver(pre_delete, sender=ProductImage)
# def delete_product_image_on_delete(sender, instance, **kwargs):
#     if instance.image:
#         try:
#             instance.image.delete(save=False)
#             print(f"Deleted product image: {instance.image.name}")
#         except Exception as e:
#             print(f"Warning: Could not delete product image file: {e}")
#     cleanup_images(instance, 'ProductImages')


# @receiver(pre_save, sender=ProductImage)
# def delete_old_product_image_on_change(sender, instance, **kwargs):
#     if not instance.pk:
#         return
#     try:
#         old_instance = ProductImage.objects.get(pk=instance.pk)
#     except ProductImage.DoesNotExist:
#         return
#     cleanup_old_images(old_instance, instance, 'ProductImages')
