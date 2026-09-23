import json
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from PIL import Image as PILImage
from wagtail.images import get_image_model
from wagtail.models import (
    APIToken,
    Collection,
    GroupCollectionPermission,
    GroupPagePermission,
    Locale,
    Page,
    Site,
)
from wagtail.permissions import policy_registry

from .models import BlogIndexPage, BlogPostPage, ProfilePage, ProjectPage
from .test_support import ensure_localized_site_roots


def png_file(name="agent.png"):
    buffer = BytesIO()
    PILImage.new("RGB", (2, 2), color="white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class PortfolioAgentAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_localized_site_roots()
        call_command("import_portfolio", verbosity=0)

    def setUp(self):
        call_command("configure_agent_account", verbosity=0)
        self.user = get_user_model().objects.get(username="portfolio-agent")
        _token, self.token = APIToken.create_token(user=self.user, name="test token")
        self.authorization = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}
        self.root_page = Site.objects.get(is_default_site=True).root_page

    def test_account_is_non_admin_and_scoped_to_page_tree_and_media_collection(self):
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.has_usable_password())
        self.assertEqual(self.user.get_all_permissions(), set())
        self.assertFalse(self.user.has_perm("wagtailcore.add_apitoken"))
        self.assertFalse(self.user.has_perm("wagtailcore.delete_apitoken"))
        self.assertEqual(list(self.user.groups.values_list("name", flat=True)), [
            "Portfolio content agent",
        ])

        group = self.user.groups.get()
        page_permissions = list(
            GroupPagePermission.objects.filter(group=group)
            .select_related("page", "permission")
            .values_list("page_id", "permission__codename")
        )
        page_permissions.sort()
        content_tree_roots = {self.root_page.pk}
        for model in (ProfilePage, ProjectPage, BlogIndexPage, BlogPostPage):
            for page in model.objects.all():
                tree_root = page.get_ancestors(inclusive=True).filter(depth=2).first()
                if tree_root is not None:
                    content_tree_roots.add(tree_root.pk)
        self.assertEqual(
            page_permissions,
            sorted(
                (root_id, codename)
                for root_id in content_tree_roots
                for codename in ("add_page", "change_page")
            ),
        )
        self.assertFalse(any(code.startswith("publish_") for _, code in page_permissions))

        content_collection = Collection.objects.get(name="Portfolio agent content")
        collection_permissions = list(
            GroupCollectionPermission.objects.filter(group=group)
            .select_related("collection", "permission")
            .values_list("collection_id", "permission__codename")
        )
        collection_permissions.sort()
        self.assertEqual(
            collection_permissions,
            [
                (content_collection.pk, "add_image"),
                (content_collection.pk, "change_image"),
            ],
        )

        unrelated_collection = Collection.get_root_nodes().get().add_child(
            instance=Collection(name="Unrelated media")
        )
        Image = get_image_model()
        other_image = Image(
            title="Unrelated",
            file=png_file("unrelated.png"),
            collection=unrelated_collection,
        )
        self.addCleanup(lambda: other_image.file.delete(save=False))
        self.assertFalse(
            policy_registry.get_by_type(Image).user_has_permission_for_instance(
                self.user, "change", other_image
            )
        )

    def test_bearer_token_reads_and_writes_only_draft_revisions(self):
        whoami = self.client.get("/api/v3/whoami/", **self.authorization)
        self.assertEqual(whoami.status_code, 200, whoami.content)
        self.assertEqual(whoami.json()["user"]["username"], "portfolio-agent")
        locale = Locale.objects.get(language_code="en")
        profile = ProfilePage.objects.get(locale=locale, stable_id="profile")
        self.assertTrue(
            policy_registry.get_by_type(Page).user_has_permission_for_instance(
                self.user, "change", profile
            )
        )
        public_description = profile.hero_description

        stable_id_update = self.client.patch(
            f"/api/v3/pages/{profile.pk}/",
            data=json.dumps(
                {
                    "meta": {"type": "portfolio.ProfilePage"},
                    "stable_id": "changed-live-stable-id",
                }
            ),
            content_type="application/json",
            **self.authorization,
        )
        self.assertEqual(stable_id_update.status_code, 400, stable_id_update.content)
        profile.refresh_from_db()
        self.assertEqual(profile.stable_id, "profile")

        readable_draft = self.client.get(
            f"/api/v3/pages/{profile.pk}/?version=draft", **self.authorization
        )
        self.assertEqual(readable_draft.status_code, 200)
        self.assertEqual(readable_draft.json()["hero_description"], public_description)

        updated_description = "Service account draft update"
        updated = self.client.patch(
            f"/api/v3/pages/{profile.pk}/",
            data=json.dumps(
                {
                    "meta": {"type": "portfolio.ProfilePage"},
                    "hero_description": updated_description,
                }
            ),
            content_type="application/json",
            **self.authorization,
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        profile.refresh_from_db()
        self.assertEqual(profile.hero_description, public_description)

        draft = self.client.get(
            f"/api/v3/pages/{profile.pk}/?version=draft", **self.authorization
        )
        self.assertEqual(draft.status_code, 200)
        self.assertEqual(
            draft.json()["hero_description"],
            updated_description,
            profile.get_latest_revision().content,
        )
        public = self.client.get(f"/api/v3/pages/{profile.pk}/")
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.json()["hero_description"], public_description)

        new_page = self.client.post(
            "/api/v3/pages/",
            data=json.dumps(
                {
                    "meta": {
                        "parent_id": self.root_page.pk,
                        "type": "portfolio.BlogIndexPage",
                    },
                    "title": "Agent draft index",
                    "slug": "agent-draft-index",
                    "stable_id": "agent-draft-index",
                }
            ),
            content_type="application/json",
            **self.authorization,
        )
        self.assertEqual(new_page.status_code, 403, new_page.content)
        self.assertFalse(BlogIndexPage.objects.filter(slug="agent-draft-index").exists())

        publish = self.client.post(
            f"/api/v3/pages/{profile.pk}/actions/publish/",
            **self.authorization,
        )
        self.assertEqual(publish.status_code, 403)
        profile.refresh_from_db()
        self.assertEqual(profile.hero_description, public_description)

    def test_bearer_token_cannot_delete_one_locale_of_a_pair(self):
        profile = ProfilePage.objects.get(
            locale=Locale.objects.get(language_code="en"), stable_id="profile"
        )
        deletion = self.client.delete(
            f"/api/v3/pages/{profile.pk}/", **self.authorization
        )
        self.assertEqual(deletion.status_code, 403, deletion.content)
        self.assertTrue(ProfilePage.objects.filter(pk=profile.pk).exists())

    def test_bearer_token_can_create_and_update_media_only_in_agent_collection(self):
        response = self.client.post(
            reverse("wagtailapi_v3:create_image"),
            {"title": "Agent image", "file": png_file()},
            **self.authorization,
        )
        self.assertEqual(response.status_code, 201, response.content)
        image = get_image_model().objects.get(pk=response.json()["id"])
        self.addCleanup(lambda: image.file.delete(save=False))
        self.addCleanup(image.delete)
        collection = Collection.objects.get(name="Portfolio agent content")
        self.assertEqual(image.collection_id, collection.pk)

        update = self.client.patch(
            reverse("wagtailapi_v3:update_image", kwargs={"image_id": image.pk}),
            data=json.dumps({"title": "Updated agent image"}),
            content_type="application/json",
            **self.authorization,
        )
        self.assertEqual(update.status_code, 200, update.content)
        image.refresh_from_db()
        self.assertEqual(image.title, "Updated agent image")
