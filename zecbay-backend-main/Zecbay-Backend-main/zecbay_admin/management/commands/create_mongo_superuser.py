# zecbay_admin/management/commands/create_mongo_superuser.py

from django.core.management.base import BaseCommand
from zecbay_admin.models import MongoUser

class Command(BaseCommand):
    help = 'Create a superuser for MongoDB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', type=str, help='Username for the superuser'
        )
        parser.add_argument(
            '--password', type=str, help='Password for the superuser'
        )

    def handle(self, *args, **kwargs):
        username = kwargs['username']
        password = kwargs['password']

        if MongoUser.objects(username=username):
            self.stdout.write(self.style.ERROR(f"User '{username}' already exists"))
            return

        # Create the superuser
        user = MongoUser(username=username, password=password, is_superuser=True, is_staff=True)
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully"))
