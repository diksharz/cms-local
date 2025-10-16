from django.db import models
from .models import BaseModel


class Tax(BaseModel):
    name            = models.CharField(max_length=100)  # Name of the tax (e.g., "GST 18%")
    percentage      = models.DecimalField(max_digits=5, decimal_places=2)  # The total tax percentage (e.g., 18.00 for 18%)
    cgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # CGST percentage
    sgst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # SGST percentage
    igst_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # IGST percentage
    cess_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # Cess percentage (e.g., for luxury goods or sin goods)
    description     = models.TextField(blank=True, null=True)  # Optional description of the tax
    is_active       = models.BooleanField(default=True)

    
    def __str__(self):
        return f"{self.name} - {self.percentage}%"

    class Meta:
        db_table = 'taxes'
        verbose_name = "Tax"
        verbose_name_plural = "Taxes"