__license__ = "MIT"
__copyright__ = "Copyright 2020, Konrad Mohrfeldt"

from functools import partial
from typing import Callable, Iterable, Union

from django.db import migrations
from django.db.migrations.state import StateApps
from django.db.models.base import ModelBase
from wagtail.blocks.stream_block import StreamValue

# From https://gist.github.com/kmohrf/3989eee63243f895396beffc61668e07
# See also https://github.com/wagtail/wagtail/issues/2110


def migrate_streamfield_name(
    model_resolver: Callable[[StateApps], ModelBase],
    attributes: Union[str, Iterable[str]],
    old_name: str,
    new_name: str,
) -> migrations.RunPython:
    """Creates a migration that converts the name used for a block inside a Wagtail StreamField.
    If you have a StreamField definition that looks like this:
        body = StreamField([
            ("paragraph", blocks.RichTextBlock()),
            ("custom_block", MyCustomBlock()),
        })
    and you want to change the name of "custom_block" to "custom_schmock" this will do the job.
    Example:
        migrate_streamfield_name(lambda apps: apps.get_model("my_app.MyModel"),
                                 "body", "custom_block", "custom_schmock")
    :param model_resolver: a callable that returns the Model class for which the migration should be executed
    :param attributes: the name (or an iterable of names) of the StreamField(s) attributes that should be migrated
    :param old_name: the name for the block type that was used until now ("custom_block" in the example)
    :param new_name: the name for the block type that should be used from now on ("custom_schmock" in the example)
    :return: Up- and down-migration for the model
    """

    def migrate(apps, schema_editor, old_name, new_name):
        db_alias = schema_editor.connection.alias
        Model = model_resolver(apps)
        objects = Model.objects.using(db_alias).all()
        for obj in objects:
            has_modified_model = False
            for attr in attributes:
                has_modified_attr = False
                migrated_stream_data = []
                attr_value = getattr(obj, attr)
                for data in attr_value.stream_data:
                    if data["type"] == old_name:
                        has_modified_model = has_modified_attr = True
                        migrated_stream_data.append(
                            {"type": new_name, "value": data["value"]}
                        )
                    else:
                        migrated_stream_data.append(data)
                if has_modified_attr:
                    new_data = StreamValue(
                        attr_value.stream_block, migrated_stream_data, is_lazy=True
                    )
                    setattr(obj, attr, new_data)
            if has_modified_model:
                obj.save()

    if isinstance(attributes, str):
        attributes = {attributes}
    return migrations.RunPython(
        code=partial(migrate, old_name=old_name, new_name=new_name),
        reverse_code=partial(migrate, old_name=new_name, new_name=old_name),
    )


def add_proxy_method(base_model, proxy_model, property_name):
    def accessor(self):
        self.__class__ = proxy_model
        return self

    base_model.add_to_class(property_name, accessor)
