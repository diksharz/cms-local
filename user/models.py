from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from cms.models.models import BaseModel
from cms.models.facility import Facility

class User(AbstractUser):
    MASTER = 'master'
    MANAGER = 'manager'
    LISTING_TEAM = 'listing_team'
    ADMIN = 'admin'
    PARTNER = 'partner'
    STAFF = 'staff'
    USER_ROLES = [
        (MASTER, 'Master'),
        (MANAGER, 'Manager'),
        (LISTING_TEAM, 'Listing Team'),
        (STAFF, 'Staff'),
        (ADMIN, 'Admin'),
        (PARTNER, 'Partner'),
    ]

    role = models.CharField(
        max_length=20,
        choices=USER_ROLES,
        default=MANAGER,  # Default role is Manager
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        related_name='custom_user_set',  # Avoids clash with default User
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    

class Role(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    permissions = models.TextField(default=list, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'roles'
        ordering = ['name']
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.name
    
    
class Staff(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'staff'
        verbose_name_plural = 'Staff'

    def __str__(self):
        return self.name

class UserDetails(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_details')
    balance = models.FloatField(default=0)
    user_referral_code = models.CharField(max_length=255, blank=True, null=True)
    login_otp = models.IntegerField(default=0)
    login_otp_create = models.DateTimeField(blank=True, null=True)
    rzp_contact_id = models.CharField(max_length=255, blank=True, null=True)
    total_savings = models.FloatField(default=0)
    regerral_code = models.CharField(max_length=255, blank=True, null=True)
    total_freebie_saving = models.FloatField(default=0)
   
    class Meta:
        db_table = 'user_details'
        verbose_name_plural = 'User Details'

    def __str__(self):
        return self.user.username
    