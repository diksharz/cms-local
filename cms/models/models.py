from django.db import models
from django.core.files.storage import FileSystemStorage
import os
from django.conf import settings

class BaseModel(models.Model):
    id = models.AutoField(primary_key=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    updation_date = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class TenantModel(BaseModel):
    created_by = models.ForeignKey('user.User', related_name="%(class)s_created_by", null=True, blank=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey('user.User', related_name="%(class)s_updated_by", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        abstract = True
        unique_together = ('id')



class ImageStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None):
        # Set the location and base_url dynamically if not provided
        self.location = location or settings.MEDIA_ROOT
        self.base_url = base_url or settings.MEDIA_URL
        super().__init__(location=self.location, base_url=self.base_url)

    def get_available_name(self, name, max_length=None):
        """
        This method can be overridden to customize the file name.
        If you want to make sure files have unique names, you can append a timestamp or a UUID.
        """
        return super().get_available_name(name, max_length)

    def _save(self, name, content):
        """
        This method is used to customize the folder name where the file is stored.
        For example, you can store images in different folders based on the model name or field value.
        """
        # Assuming we want to save images in the following pattern: `<model_name>/<category_name>/image.jpg`
        folder_name = self.get_folder_name(name)
        path = os.path.join(self.location, folder_name)

        # Ensure the folder exists
        if not os.path.exists(path):
            os.makedirs(path)
        
        # Save the file
        name = os.path.join(folder_name, name)
        return super()._save(name, content)

    def get_folder_name(self, name):
        """
        This method defines how to dynamically get a folder name based on the model or some logic.
        Example: 
        - If saving a Category image, it can save under 'Category/<category_name>/'
        - If saving a Subcategory image, it can save under 'Subcategory/<subcategory_name>/'
        """
        # Extract model name or some attribute to define the folder path
        model_name = self.get_model_name(name)  # You can use logic here
        folder_name = model_name.lower()  # Just an example of folder naming convention
        
        return folder_name

    def get_model_name(self, name):
        """
        You can use this method to extract the model name or logic based on your needs
        (e.g., Category, Subcategory, Brand, etc.).
        """
        # In your case, you can customize this method to return the appropriate folder name based on the model.
        # Example based on name (You can modify based on your actual use case)
        if "category" in name.lower():
            return "Category"
        elif "subcategory" in name.lower():
            return "Subcategory"
        elif "brand" in name.lower():
            return "Brand"
        else:
            return "General"  # Default folder if the logic doesn't match