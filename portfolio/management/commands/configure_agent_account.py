from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from wagtail.images import get_image_model
from wagtail.models import (
    APIToken,
    Collection,
    GroupCollectionPermission,
    GroupPagePermission,
    Page,
    Site,
)

from portfolio.models import BlogIndexPage, BlogPostPage, ProfilePage, ProjectPage

GROUP_NAME = "Portfolio content agent"
DEFAULT_USERNAME = "portfolio-agent"
COLLECTION_NAME = "Portfolio agent content"


class Command(BaseCommand):
    help = "Create or reconcile the least-privilege portfolio content API account."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=DEFAULT_USERNAME)

    def handle(self, *args, **options):
        username = options["username"]
        User = get_user_model()
        user, created = User.objects.get_or_create(
            **{User.USERNAME_FIELD: username},
            defaults={"is_active": True, "is_staff": False, "is_superuser": False},
        )
        if user.is_superuser or user.is_staff:
            raise CommandError("The service account must be non-staff and non-superuser.")
        user.set_unusable_password()
        user.save(update_fields=["password"])
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.save(update_fields=["is_active", "is_staff", "is_superuser"])

        group, _ = Group.objects.get_or_create(name=GROUP_NAME)
        if group.user_set.exclude(pk=user.pk).exists():
            raise CommandError(
                f"The reserved group {GROUP_NAME!r} is assigned to another user."
            )

        # Reconcile this reserved service identity and group to an explicit allowlist.
        user.groups.set([group])
        user.user_permissions.clear()
        group.permissions.clear()
        GroupPagePermission.objects.filter(group=group).delete()
        GroupCollectionPermission.objects.filter(group=group).delete()

        page_ct = ContentType.objects.get_for_model(Page)
        image_model = get_image_model()
        image_ct = ContentType.objects.get_for_model(image_model)
        site_root = Site.objects.get(is_default_site=True).root_page
        root_collection = Collection.get_root_nodes().get()
        content_collection = root_collection.get_children().filter(name=COLLECTION_NAME).first()
        if content_collection is None:
            content_collection = root_collection.add_child(
                instance=Collection(name=COLLECTION_NAME)
            )

        content_tree_roots = {site_root}
        for model in (ProfilePage, ProjectPage, BlogIndexPage, BlogPostPage):
            for page in model.objects.all():
                tree_root = page.get_ancestors(inclusive=True).filter(depth=2).first()
                if tree_root is not None:
                    content_tree_roots.add(tree_root)

        for page in content_tree_roots:
            for codename in ("add_page", "change_page"):
                permission = Permission.objects.get(content_type=page_ct, codename=codename)
                GroupPagePermission.objects.create(
                    group=group, page=page, permission=permission
                )

        for codename in ("add_image", "change_image", "choose_image"):
            permission = Permission.objects.get(content_type=image_ct, codename=codename)
            GroupCollectionPermission.objects.create(
                group=group, collection=content_collection, permission=permission
            )

        # A Wagtail API token is provisioned separately by a site administrator;
        # the service identity receives no token-management permission.
        if user.has_perm(f"wagtailcore.add_{APIToken._meta.model_name}"):
            raise CommandError("The service account must not manage API tokens.")

        state = "created" if created else "reconciled"
        self.stdout.write(self.style.SUCCESS(f"Service account {username!r} {state}."))
