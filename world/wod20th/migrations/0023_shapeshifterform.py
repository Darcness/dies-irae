# Generated by Django 4.2.13 on 2024-08-10 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wod20th", "0022_stat_default"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShapeshifterForm",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("shifter_type", models.CharField(max_length=50)),
                ("description", models.TextField(blank=True)),
                ("stat_modifiers", models.JSONField(blank=True, default=dict)),
                ("rage_cost", models.PositiveIntegerField(default=0)),
                ("difficulty", models.PositiveIntegerField(default=6)),
                ("lock_string", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "Shapeshifter Form",
                "verbose_name_plural": "Shapeshifter Forms",
                "ordering": ["shifter_type", "name"],
            },
        ),
    ]