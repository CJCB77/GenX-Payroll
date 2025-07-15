"""
Create a custom user model
"""
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin
)
from django.db import models


class OdooUserManager(BaseUserManager):
    def create_user(self, username, odoo_user_id, password=None, **extra_fields):
        if not username:
            raise ValueError("Users must have a username and odoo_user_id")
        
        #Regular users need odoo_user_id, but superusers don't
        if not extra_fields.get("is_superuser") and not odoo_user_id:
            raise ValueError("Regular users must have an odoo_user_id")
        
        user = self.model(
            username=username,
            odoo_user_id=odoo_user_id,
            **extra_fields
        )
        # Set unusable password just for regular users
        if password and (extra_fields.get("is_superuser") or extra_fields.get("is_staff")):
            user.set_password(password)
        else:
            user.set_unusable_password() # For regular users

        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        if not password:
            raise ValueError("Superuser must have a password")
        
        return self.create_user(
            username, 
            odoo_user_id=None, 
            password=password, 
            **extra_fields
        )

class User(AbstractBaseUser, PermissionsMixin):
    odoo_user_id = models.IntegerField(unique=True, null=True, blank=True)
    username = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(max_length=255, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    objects = OdooUserManager()

    def __str__(self):
        return self.username
