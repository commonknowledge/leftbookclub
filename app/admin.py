import pycountry
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from app import models


class UserResource(resources.ModelResource):
    class Meta:
        model = models.User

    algo_prefix = "bcrypt$"

    def before_import_row(self, row, *args, **kwargs):
        if "id" in row:
            row["old_id"] = row["id"]
            row.pop("id", None)

        if "password" in row and self.algo_prefix not in row["password"]:
            row["password"] = self.algo_prefix + row["password"]

        if "username" not in row:
            row["username"] = row["email"]

        if "country" in row:
            countries = pycountry.countries.search_fuzzy(str(row["country"]))
            if len(countries) > 0:
                row["country"] = countries[0].alpha_2
            else:
                row.pop("country", None)

        return row


@admin.register(models.User)
class CustomUserAdmin(UserAdmin, ImportExportModelAdmin):
    resource_class = UserResource


from import_export.fields import Field


class LegacyGiftResource(resources.ModelResource):
    class Meta:
        model = models.LegacyGifts


@admin.register(models.LegacyGifts)
class CustomLegacyGiftAdmin(ImportExportModelAdmin, admin.ModelAdmin):
    resource_class = LegacyGiftResource
