from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from django.apps import apps
from django.core.management import BaseCommand, CommandError, call_command


@dataclass(frozen=True)
class FixtureItem:
    path: Path
    group: str
    priority: int


def natural_key(s: str):
    # "01_ing.json" < "2_ing.json" < "10_ing.json"
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


class Command(BaseCommand):
    help = "Load all JSON fixtures from recipe_manager/fixtures recursively in dependency-safe order."

    GROUP_PRIORITY = {
        "cuisines": 10,
        "ingredients": 20,
        "recipes": 30,
        "recipe_ingredients": 40,
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            default="recipe_manager",
            help="Django app label that contains fixtures directory (default: recipe_manager).",
        )
        parser.add_argument(
            "--fixtures-dir",
            default="fixtures",
            help="Fixtures directory name inside the app (default: fixtures).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be loaded, without loading.",
        )

    def handle(self, *args, **options):
        app_label: str = options["app"]
        fixtures_dir_name: str = options["fixtures_dir"]
        dry_run: bool = options["dry_run"]
        verbosity: int = options["verbosity"]

        try:
            app_config = apps.get_app_config(app_label)
        except LookupError as e:
            raise CommandError(f"App '{app_label}' not found. Check INSTALLED_APPS.") from e

        fixtures_root = Path(app_config.path) / fixtures_dir_name
        if not fixtures_root.exists():
            raise CommandError(f"Fixtures directory not found: {fixtures_root}")

        items = list(self._collect_fixtures(fixtures_root))
        if not items:
            self.stdout.write(self.style.WARNING(f"No .json fixtures found under: {fixtures_root}"))
            return

        items.sort(key=lambda x: (x.priority, natural_key(x.path.name)))

        self.stdout.write(self.style.MIGRATE_HEADING("Fixtures load plan:"))
        for it in items:
            self.stdout.write(f"- [{it.group}] {it.path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run mode: nothing loaded."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("Loading fixtures..."))
        for it in items:
            self.stdout.write(f"-> loaddata {it.path}")
            call_command("loaddata", str(it.path), verbosity=verbosity)

        self.stdout.write(self.style.SUCCESS("All fixtures loaded successfully."))

    def _collect_fixtures(self, fixtures_root: Path) -> Iterable[FixtureItem]:
        for path in fixtures_root.rglob("*.json"):
            if not path.is_file():
                continue

            group = path.parent.name

            priority = self.GROUP_PRIORITY.get(group, 999)

            yield FixtureItem(path=path.resolve(), group=group, priority=priority)
