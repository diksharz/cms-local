import os
import time
from io import BytesIO
from PIL import Image

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser


class UploadImagesView(APIView):
    """
    POST /api/uploads/images/
    - multipart/form-data
    - field: images (repeatable) [also accepts 'files' or 'image']
    Saves each file as WEBP under: media/<epoch_ms>_<slug>.webp
    Returns: {"files":[{"name","key","url"}], "errors":[...]}
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # ---- input files ----
        files = (
            request.FILES.getlist("images")
            or request.FILES.getlist("files")
            or request.FILES.getlist("image")
        )
        if not files:
            return Response({"detail": "No files provided. Use field 'images'."}, status=status.HTTP_400_BAD_REQUEST)

        results, errors = [], []

        for file_obj in files:
            try:
                # names
                original_name = file_obj.name
                name_no_ext, _ = os.path.splitext(original_name)
                slug = slugify(name_no_ext) or "image"
                ts_ms = int(time.time() * 1000)
                webp_key = f"{ts_ms}_{slug}.webp"  # final S3 key will be: media/<ts>_<slug>.webp

                # ---- convert to WEBP ----
                img = Image.open(file_obj)
                # keep alpha if present; otherwise RGB
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")

                buf = BytesIO()
                img.save(buf, format="WEBP", quality=85)
                buf.seek(0)

                # ---- save with proper Content-Type ----
                content = ContentFile(buf.getvalue())
                content.name = webp_key
                # critical: set content_type so S3 stores Content-Type: image/webp
                content.content_type = "image/webp"

                saved_key = default_storage.save(webp_key, content)  # -> media/<ts>_<slug>.webp
                url = default_storage.url(saved_key)

                results.append({"name": original_name, "file_path": f"media/{saved_key}", "url": url})

            except Exception as e:
                errors.append({"name": getattr(file_obj, "name", "unknown"), "error": str(e)})

        return Response(
            {"files": results} if not errors else {"files": results, "errors": errors},
            status=status.HTTP_201_CREATED if results else status.HTTP_400_BAD_REQUEST,
        )
