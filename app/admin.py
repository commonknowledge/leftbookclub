from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from app import models


class UserResource(resources.ModelResource):
    class Meta:
        model = models.User

    def before_import_row(self, row, *args, **kwargs):
        row.pop("id", None)

        algo_prefix = "bcrypt$"
        if "password" in row and algo_prefix not in row["password"]:
            row["password"] = algo_prefix + row["password"]

        if "username" not in row:
            row["username"] = row["email"]

        return row


@admin.register(models.User)
class CustomUserAdmin(UserAdmin, ImportExportModelAdmin):
    resource_class = UserResource
