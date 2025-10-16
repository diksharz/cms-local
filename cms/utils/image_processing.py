from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from cms.models.models import ImageStorage
import os


def convert_to_webp(image_file, target_sizes):
    original_img = Image.open(image_file)

    if original_img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', original_img.size, (255, 255, 255))
        if original_img.mode == 'P':
            original_img = original_img.convert('RGBA')
        background.paste(original_img, mask=original_img.split()[-1] if original_img.mode == 'RGBA' else None)
        original_img = background
    elif original_img.mode != 'RGB':
        original_img = original_img.convert('RGB')

    webp_images = []

    for size in target_sizes:
        target_width, target_height = size
        img = original_img.copy()

        img_ratio = img.width / img.height
        target_ratio = target_width / target_height

        if img_ratio > target_ratio:
            new_height = target_height
            new_width = int(new_height * img_ratio)
        else:
            new_width = target_width
            new_height = int(new_width / img_ratio)

        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height
        img = img.crop((left, top, right, bottom))

        webp_io = BytesIO()
        img.save(webp_io, format='WEBP', quality=85, optimize=True)
        webp_io.seek(0)
        webp_images.append(webp_io)

    return webp_images

def process_webp_images(instance, model_type, target_sizes):
    image_field = getattr(instance, 'thumbnail_image', None) or getattr(instance, 'image', None)
    if not image_field:
        return

    try:
        storage = ImageStorage()
        original_image_file = storage.open(image_field.name)
        webp_images = convert_to_webp(original_image_file, target_sizes)

        if model_type in ['Category', 'Subcategory', 'Product']:
            # For Category, Subcategory, and Product models
            name = getattr(instance, 'code', None) or getattr(instance, 'sku', None)
            if not name:
                raise ValueError(f"No code or sku found for {model_type} instance")

            webp_200_path = f"{model_type}/{name}_200.webp"
            webp_300_path = f"{model_type}/{name}_300.webp"
            storage.save(webp_200_path, ContentFile(webp_images[0].getvalue()))
            storage.save(webp_300_path, ContentFile(webp_images[1].getvalue()))

        elif model_type == 'ProductImages':
            # For ProductImage model
            if not hasattr(instance, 'product') or not hasattr(instance, 'priority'):
                raise ValueError(f"ProductImage instance missing product or priority")

            sku = instance.product.sku
            priority = instance.priority

            webp_500_path = f"ProductImages/{sku}_{priority}_500.webp"
            webp_600_path = f"ProductImages/{sku}_{priority}_600.webp"
            webp_800_path = f"ProductImages/{sku}_{priority}_800.webp"

            storage.save(webp_500_path, ContentFile(webp_images[0].getvalue()))
            storage.save(webp_600_path, ContentFile(webp_images[1].getvalue()))
            storage.save(webp_800_path, ContentFile(webp_images[2].getvalue()))

    except Exception as e:
        identifier = getattr(instance, 'code', None) or getattr(instance, 'sku', None) or str(instance.id)
        print(f"Error processing WebP images for {model_type} {identifier}: {e}")


def cleanup_images(instance, model_type=None):
    try:
        storage = ImageStorage()
        identifier = getattr(instance, 'code', None) or getattr(instance, 'sku', None) or str(instance.id)
        if model_type != 'ProductImages':
            code_or_sku = getattr(instance, 'code', None) or getattr(instance, 'sku', None)
            if code_or_sku:
                for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                    original_path = f"{model_type}/{code_or_sku}{ext}"
                    try:
                        storage.delete(original_path)
                    except:
                        pass
                webp_paths = [
                    f"{model_type}/{code_or_sku}_200.webp",
                    f"{model_type}/{code_or_sku}_300.webp"
                ]
        else:
            if hasattr(instance, 'product') and hasattr(instance, 'priority'):
                sku = instance.product.sku
                priority = instance.priority
                for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                    original_path = f"ProductImages/{sku}_{priority}{ext}"
                    try:
                        storage.delete(original_path)
                    except:
                        pass
                webp_paths = [
                    f"ProductImages/{sku}_{priority}_500.webp",
                    f"ProductImages/{sku}_{priority}_600.webp",
                    f"ProductImages/{sku}_{priority}_800.webp"
                ]
            else:
                webp_paths = []

        for webp_path in webp_paths:
            try:
                storage.delete(webp_path)
            except:
                pass

    except Exception as e:
        print(f"Could not delete images for {identifier}: {e}")


def cleanup_old_images(old_instance, new_instance, model_type=None):
    old_image_field = getattr(old_instance, 'thumbnail_image', None) or getattr(old_instance, 'image', None)
    new_image_field = getattr(new_instance, 'thumbnail_image', None) or getattr(new_instance, 'image', None)

    if old_image_field and (
        not new_image_field or
        old_image_field.name != new_image_field.name
    ):
        try:
            old_image_field.delete(save=False)
            cleanup_images(old_instance, model_type)
        except Exception as e:
            print(f"Warning: Could not delete old image: {e}")
