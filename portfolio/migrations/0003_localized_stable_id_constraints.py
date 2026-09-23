import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Count

LOCALIZED_MODELS = (
    ("BlogIndexPage", "unique_blog_index_locale_stable_id"),
    ("BlogPostPage", "unique_blog_post_locale_stable_id"),
    ("ProfilePage", "unique_profile_locale_stable_id"),
    ("ProjectPage", "unique_project_locale_stable_id"),
)


def reject_existing_duplicates(apps, schema_editor):
    """Refuse to add constraints while preserving every existing duplicate row."""
    for model_name, _constraint_name in LOCALIZED_MODELS:
        model = apps.get_model("portfolio", model_name)
        duplicates = list(
            model.objects.values("localized_locale_id", "stable_id")
            .annotate(row_count=Count("id"))
            .filter(row_count__gt=1)
            .order_by("locale_id", "stable_id")
        )
        if duplicates:
            details = ", ".join(
                f"locale_id={row['localized_locale_id']!r}, stable_id={row['stable_id']!r}, "
                f"rows={row['row_count']}"
                for row in duplicates
            )
            raise RuntimeError(
                f"Cannot add localized stable-id uniqueness for {model_name}; "
                f"resolve existing duplicates without deleting data: {details}"
            )


def populate_localized_locale(apps, schema_editor):
    for model_name, _constraint_name in LOCALIZED_MODELS:
        model = apps.get_model("portfolio", model_name)
        for page in model.objects.select_related("page_ptr").iterator():
            page.localized_locale_id = page.page_ptr.locale_id
            page.save(update_fields=["localized_locale"])


class Migration(migrations.Migration):
    dependencies = [("portfolio", "0002_blogindexpage_blogpostpage")]

    operations = [
        migrations.AddField(
            model_name="blogindexpage",
            name="localized_locale",
            field=models.ForeignKey(
                editable=False,
                help_text="Database-localized locale key used for stable-id uniqueness.",
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AddField(
            model_name="blogpostpage",
            name="localized_locale",
            field=models.ForeignKey(
                editable=False,
                help_text="Database-localized locale key used for stable-id uniqueness.",
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AddField(
            model_name="profilepage",
            name="localized_locale",
            field=models.ForeignKey(
                editable=False,
                help_text="Database-localized locale key used for stable-id uniqueness.",
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AddField(
            model_name="projectpage",
            name="localized_locale",
            field=models.ForeignKey(
                editable=False,
                help_text="Database-localized locale key used for stable-id uniqueness.",
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.RunPython(populate_localized_locale, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="blogindexpage",
            name="localized_locale",
            field=models.ForeignKey(
                editable=False,
                help_text="Database-localized locale key used for stable-id uniqueness.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AlterField(
            model_name="blogpostpage",
            name="localized_locale",
            field=models.ForeignKey(
                editable=False,
                help_text="Database-localized locale key used for stable-id uniqueness.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AlterField(
            model_name="profilepage",
            name="localized_locale",
            field=models.ForeignKey(
                editable=False,
                help_text="Database-localized locale key used for stable-id uniqueness.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.AlterField(
            model_name="projectpage",
            name="localized_locale",
            field=models.ForeignKey(
                editable=False,
                help_text="Database-localized locale key used for stable-id uniqueness.",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="wagtailcore.locale",
            ),
        ),
        migrations.RunPython(reject_existing_duplicates, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="blogindexpage",
            constraint=models.UniqueConstraint(
                fields=("localized_locale", "stable_id"), name="unique_blog_index_locale_stable_id"
            ),
        ),
        migrations.AddConstraint(
            model_name="blogpostpage",
            constraint=models.UniqueConstraint(
                fields=("localized_locale", "stable_id"), name="unique_blog_post_locale_stable_id"
            ),
        ),
        migrations.AddConstraint(
            model_name="profilepage",
            constraint=models.UniqueConstraint(
                fields=("localized_locale", "stable_id"), name="unique_profile_locale_stable_id"
            ),
        ),
        migrations.AddConstraint(
            model_name="projectpage",
            constraint=models.UniqueConstraint(
                fields=("localized_locale", "stable_id"), name="unique_project_locale_stable_id"
            ),
        ),
    ]
