from core.bootstrap import Bootstraper
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Flushes the database and loads development bootstrap data."

    def handle(self, *args, **options):
        Bootstraper().bootstrap()
        self.stdout.write("Database bootstrapped successfully")
