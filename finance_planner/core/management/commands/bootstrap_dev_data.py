from django.core.management.base import BaseCommand

from core.bootstrap import bootstrap_dev_data


class Command(BaseCommand):
    help = "Flushes the database and loads development bootstrap data."

    def handle(self, *args, **options):
        bootstrap_dev_data()
        self.stdout.write("Database bootstrapped successfully")
