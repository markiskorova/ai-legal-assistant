# Generated manually to align models with MVP Step 7 persistence needs.

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0001_initial"),
        ("review", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReviewRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(default="completed", max_length=20)),
                ("llm_model", models.CharField(blank=True, max_length=50, null=True)),
                ("prompt_rev", models.CharField(blank=True, max_length=200, null=True)),
                ("error", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="review_runs",
                        to="documents.document",
                    ),
                ),
            ],
        ),
        migrations.RenameField(
            model_name="finding",
            old_name="risk",
            new_name="severity",
        ),
        migrations.AddField(
            model_name="finding",
            name="run",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="findings",
                to="review.reviewrun",
            ),
        ),
        migrations.AlterField(
            model_name="finding",
            name="clause_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="finding",
            name="clause_heading",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="finding",
            name="clause_body",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="finding",
            name="explanation",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="finding",
            name="rule_code",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="finding",
            name="model",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="finding",
            name="confidence",
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name="finding",
            name="prompt_rev",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]
