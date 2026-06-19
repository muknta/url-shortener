from django.db import migrations


def forward(apps, schema_editor):
    ShortLink = apps.get_model("urlapp", "ShortLink")
    ShortLink.objects.filter(author__isnull=True).update(is_public=True)


def backward(apps, schema_editor):
    pass  # no-op: is_public column is dropped by reversing migration 0002


class Migration(migrations.Migration):

    dependencies = [
        ("urlapp", "0002_add_is_public_deleted_at_partial_unique"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
