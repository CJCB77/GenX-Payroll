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
    def create_user(self, username, odoo_user_id, **extra_fields):
        if not username or not odoo_user_id:
            raise ValueError("Users must have a username and odoo_user_id")
        
        user = self.model(
            username=username,
            odoo_user_id=odoo_user_id,
            **extra_fields
        )
        user.set_unusable_password()
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, odoo_user_id, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, odoo_user_id, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    odoo_user_id = models.IntegerField(unique=True)
    username = models.CharField(max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["odoo_user_id"]

    objects = OdooUserManager()

    def __str__(self):
        return self.username
