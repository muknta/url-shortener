# Generated manually to rename creat_date → created_date, fix auto_now → auto_now_add, add index

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("urlapp", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="surl",
            old_name="creat_date",
            new_name="created_date",
        ),
        migrations.AlterField(
            model_name="surl",
            name="created_date",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddIndex(
            model_name="surl",
            index=models.Index(
                fields=["-visit_count", "-created_date"],
                name="urlapp_surl_visit_c_74c517_idx",
            ),
        ),
    ]
