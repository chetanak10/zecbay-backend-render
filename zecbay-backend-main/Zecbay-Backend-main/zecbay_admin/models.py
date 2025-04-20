# zecbay_admin/models.py

from mongoengine import Document, StringField
from django.contrib.auth.hashers import make_password, check_password

class AdminUser(Document):
    username = StringField(required=True, unique=True)
    password = StringField(required=True)  # Stored as a hashed password

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.username
