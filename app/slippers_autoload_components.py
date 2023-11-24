from pathlib import Path

from django.conf import settings
from slippers.templatetags.slippers import register_components

SLIPPERS_SUBDIR = "components"


def find_slipper_dirs():
    dirs = []
    from django.template import engines

    for backend in engines.all():
        for loader in backend.engine.template_loaders:
            if not hasattr(loader, "get_dirs"):
                continue
            for templates_dir in loader.get_dirs():
                templates_path = Path(templates_dir)
                slippers_dir = templates_path / SLIPPERS_SUBDIR
                if slippers_dir.exists():
                    dirs.append(templates_path)
    return dirs


def register_dir_components(dir, templates_path):
    register_components(
        {
            template.stem: str(template.relative_to(templates_path))
            for template in dir.glob("*.html")
        }
    )


def register():
    """
    Register discovered slippers components.
    """
    import os

    from django.template import engines

    dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
    template_dirs = [dir_path / "templates"]
    # template_dirs = find_slipper_dirs()

    slippers_dirs = []

    for templates_dir in template_dirs:
        print("Registering slippers components from", templates_dir / SLIPPERS_SUBDIR)
        if templates_dir.exists():
            templates_path = Path(templates_dir)
            slippers_dir = templates_path / SLIPPERS_SUBDIR
            register_dir_components(slippers_dir, templates_path)
            slippers_dirs.append(slippers_dir)

    if settings.DEBUG:
        # To support autoreload for `manage.py runserver`, also add a watch so that
        # we re-run this code if new slippers templates are added

        from django.dispatch import receiver
        from django.utils.autoreload import autoreload_started, file_changed

        @receiver(autoreload_started, dispatch_uid="watch_slippers_dirs")
        def watch_slippers_dirs(sender, **kwargs):
            for path in slippers_dirs:
                sender.watch_dir(path, "*.html")

        @receiver(file_changed, dispatch_uid="slippers_template_changed")
        def template_changed(sender, file_path, **kwargs):
            path = Path(file_path)
            if path.exists() and path.is_dir():
                # This happens when new html files are created, re-run registration
                register()
