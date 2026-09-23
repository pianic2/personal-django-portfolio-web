from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.api import APIField
from wagtail.images import get_image_model_string
from wagtail.models import Locale, Orderable, Page, Site


def _writable_api_fields(*names: str) -> list[APIField]:
    return [APIField(name, writable=True) for name in names]


class LocalizedPageMixin(models.Model):
    """Shared fields for locale-owned editorial pages."""

    stable_id = models.SlugField(
        max_length=100,
        help_text="Stable editorial identifier shared by all locale translations.",
    )
    localized_locale = models.ForeignKey(
        "wagtailcore.Locale",
        on_delete=models.PROTECT,
        editable=False,
        related_name="+",
        help_text="Database-localized locale key used for stable-id uniqueness.",
    )

    class Meta:
        abstract = True

    def clean(self) -> None:
        super().clean()
        if self.locale_id and self.stable_id:
            duplicate = (
                self.__class__.objects.filter(locale_id=self.locale_id, stable_id=self.stable_id)
                .exclude(pk=self.pk)
                .exists()
            )
            if duplicate:
                raise ValidationError(
                    {"stable_id": "This stable ID is already used in this locale."}
                )

    def save(self, *args, **kwargs):
        clean = kwargs.pop("clean", True)
        if not self.locale_id:
            self.locale_id = self.get_parent().locale_id
        self.localized_locale_id = self.locale_id
        if clean:
            self.full_clean()
        return super().save(*args, **kwargs)


class BlogIndexPage(LocalizedPageMixin, Page):
    """Locale-owned Wagtail container for editable blog posts."""

    parent_page_types: list[str] = ["wagtailcore.Page"]
    subpage_types: list[str] = ["portfolio.BlogPostPage"]
    api_fields = _writable_api_fields("stable_id")
    content_panels = Page.content_panels + [FieldPanel("stable_id")]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["localized_locale", "stable_id"],
                name="unique_blog_index_locale_stable_id",
            )
        ]


class BlogPostPage(LocalizedPageMixin, Page):
    """Minimal Wagtail-native blog post with API-friendly body and media."""

    excerpt = models.TextField()
    publication_date = models.DateField(default=timezone.localdate)
    body = models.TextField()
    featured_image = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="blog_posts",
    )

    parent_page_types: list[str] = ["portfolio.BlogIndexPage"]
    subpage_types: list[str] = []
    api_fields = _writable_api_fields(
        "stable_id", "excerpt", "publication_date", "body", "featured_image"
    )
    content_panels = Page.content_panels + [
        FieldPanel("stable_id"),
        FieldPanel("excerpt"),
        FieldPanel("publication_date"),
        FieldPanel("body"),
        FieldPanel("featured_image"),
    ]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["localized_locale", "stable_id"],
                name="unique_blog_post_locale_stable_id",
            )
        ]


class Capability(models.Model):
    class Category(models.TextChoices):
        FRONTEND = "frontend", "Frontend"
        BACKEND = "backend", "Backend"
        ARCHITECTURE = "architecture", "Architecture"
        DELIVERY = "delivery", "Delivery"
        QUALITY = "quality", "Quality"
        SECURITY = "security", "Security"
        PRODUCT = "product", "Product"
        EMBEDDED = "embedded", "Embedded"

    stable_id = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=30, choices=Category.choices)

    panels = [FieldPanel("stable_id"), FieldPanel("category")]

    class Meta:
        ordering = ["stable_id"]

    def __str__(self) -> str:
        return self.stable_id


class CapabilityTranslation(models.Model):
    capability = models.ForeignKey(
        Capability, on_delete=models.CASCADE, related_name="translations"
    )
    locale = models.ForeignKey("wagtailcore.Locale", on_delete=models.CASCADE)
    label = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    panels = [
        FieldPanel("capability"),
        FieldPanel("locale"),
        FieldPanel("label"),
        FieldPanel("description"),
    ]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["capability", "locale"], name="unique_capability_translation_locale"
            )
        ]


class ProfilePage(LocalizedPageMixin, Page):
    hero_eyebrow = models.CharField(max_length=120)
    hero_description = models.TextField()
    highlights_label = models.CharField(max_length=120)
    closing_title = models.CharField(max_length=255)
    closing_description = models.TextField()

    parent_page_types: list[str] = ["wagtailcore.Page"]
    subpage_types: list[str] = []
    api_fields = _writable_api_fields(
        "stable_id",
        "hero_eyebrow",
        "hero_description",
        "highlights_label",
        "closing_title",
        "closing_description",
        "sections",
        "useful_links",
    )
    content_panels = Page.content_panels + [
        FieldPanel("stable_id"),
        MultiFieldPanel(
            [FieldPanel("hero_eyebrow"), FieldPanel("hero_description")],
            heading="Hero",
        ),
        FieldPanel("highlights_label"),
        MultiFieldPanel(
            [FieldPanel("closing_title"), FieldPanel("closing_description")],
            heading="Closing",
        ),
        InlinePanel("sections", label="Profile sections"),
        InlinePanel("useful_links", label="Useful links"),
    ]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["localized_locale", "stable_id"],
                name="unique_profile_locale_stable_id",
            )
        ]

class ProfileSection(Orderable):
    page = ParentalKey(ProfilePage, on_delete=models.CASCADE, related_name="sections")
    stable_id = models.SlugField(max_length=100)
    number = models.CharField(max_length=20)
    eyebrow = models.CharField(max_length=120)
    title = models.CharField(max_length=255)
    paragraphs = models.JSONField(default=list)
    highlights = models.JSONField(default=list)

    api_fields = _writable_api_fields(
        "stable_id", "number", "eyebrow", "title", "paragraphs", "highlights"
    )

    panels = [
        FieldPanel("stable_id"),
        FieldPanel("number"),
        FieldPanel("eyebrow"),
        FieldPanel("title"),
        FieldPanel("paragraphs"),
        FieldPanel("highlights"),
    ]


class ProfileUsefulLink(Orderable):
    page = ParentalKey(ProfilePage, on_delete=models.CASCADE, related_name="useful_links")
    stable_id = models.SlugField(max_length=100)
    label = models.CharField(max_length=160)
    description = models.TextField()
    url = models.URLField()
    cta_label = models.CharField(max_length=160)

    api_fields = _writable_api_fields("stable_id", "label", "description", "url", "cta_label")

    panels = [
        FieldPanel("stable_id"),
        FieldPanel("label"),
        FieldPanel("description"),
        FieldPanel("url"),
        FieldPanel("cta_label"),
    ]


class ProjectPage(LocalizedPageMixin, Page):
    class Origin(models.TextChoices):
        PERSONAL_LONG_TERM = "personal-long-term", "Personal long-term"
        ITS_TRAINING = "its-training", "ITS training"

    class VisualVariant(models.TextChoices):
        SIGNAL_YELLOW = "signal-yellow", "Signal yellow"
        STUDIO_PINK = "studio-pink", "Studio pink"
        ELECTRIC_CYAN = "electric-cyan", "Electric cyan"

    eyebrow = models.CharField(max_length=120)
    detail_eyebrow = models.CharField(max_length=120)
    cta_label = models.CharField(max_length=160)
    question = models.TextField()
    supporting_text = models.TextField()
    what_i_worked_on = models.TextField()
    future_improvement = models.TextField()
    origin_description = models.TextField(blank=True)
    narrative = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)
    origin = models.CharField(max_length=30, choices=Origin.choices)
    visual_variant = models.CharField(max_length=30, choices=VisualVariant.choices)
    featured = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    parent_page_types: list[str] = ["wagtailcore.Page"]
    subpage_types: list[str] = []
    api_fields = _writable_api_fields(
        "stable_id",
        "eyebrow",
        "detail_eyebrow",
        "cta_label",
        "question",
        "supporting_text",
        "what_i_worked_on",
        "future_improvement",
        "origin_description",
        "narrative",
        "metadata",
        "origin",
        "visual_variant",
        "featured",
        "display_order",
        "capabilities",
        "links",
        "assets",
        "evidence",
        "claims",
    )
    content_panels = Page.content_panels + [
        FieldPanel("stable_id"),
        FieldPanel("eyebrow"),
        FieldPanel("detail_eyebrow"),
        FieldPanel("cta_label"),
        FieldPanel("question"),
        FieldPanel("supporting_text"),
        FieldPanel("what_i_worked_on"),
        FieldPanel("future_improvement"),
        FieldPanel("origin_description"),
        FieldPanel("narrative"),
        FieldPanel("metadata"),
        MultiFieldPanel(
            [
                FieldPanel("origin"),
                FieldPanel("visual_variant"),
                FieldPanel("featured"),
                FieldPanel("display_order"),
            ],
            heading="Project identity and ordering",
        ),
        InlinePanel("capabilities", label="Capabilities"),
        InlinePanel("links", label="External links"),
        InlinePanel("assets", label="Assets"),
        InlinePanel("evidence", label="Evidence"),
        InlinePanel("claims", label="Claims"),
    ]

    class Meta:
        ordering = ["display_order", "stable_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["localized_locale", "stable_id"],
                name="unique_project_locale_stable_id",
            )
        ]


class ProjectCapability(Orderable):
    project = ParentalKey(ProjectPage, on_delete=models.CASCADE, related_name="capabilities")
    capability = models.ForeignKey(Capability, on_delete=models.PROTECT)

    api_fields = _writable_api_fields("capability")

    panels = [FieldPanel("capability")]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "capability"], name="unique_project_capability"
            )
        ]


class ProjectLink(Orderable):
    class Kind(models.TextChoices):
        REPOSITORY = "repository", "Repository"
        LIVE_DEMO = "live-demo", "Live demo"
        DOCUMENTATION = "documentation", "Documentation"
        JIRA = "jira", "Jira"
        OTHER = "other", "Other"

    project = ParentalKey(ProjectPage, on_delete=models.CASCADE, related_name="links")
    stable_id = models.SlugField(max_length=100)
    kind = models.CharField(max_length=30, choices=Kind.choices)
    label = models.CharField(max_length=160)
    accessibility_label = models.CharField(max_length=160, blank=True)
    url = models.URLField()

    api_fields = _writable_api_fields("stable_id", "kind", "label", "accessibility_label", "url")

    panels = [
        FieldPanel("stable_id"),
        FieldPanel("kind"),
        FieldPanel("label"),
        FieldPanel("accessibility_label"),
        FieldPanel("url"),
    ]


class ProjectAsset(Orderable):
    class Provenance(models.TextChoices):
        REPOSITORY = "repository", "Repository"
        PROJECT_SCREENSHOT = "project-screenshot", "Project screenshot"
        ORIGINAL = "original", "Original"
        GENERATED = "generated", "Generated"
        THIRD_PARTY = "third-party", "Third party"

    project = ParentalKey(ProjectPage, on_delete=models.CASCADE, related_name="assets")
    stable_id = models.SlugField(max_length=100)
    image = models.ForeignKey(
        get_image_model_string(), on_delete=models.PROTECT, related_name="portfolio_assets"
    )
    provenance = models.CharField(max_length=30, choices=Provenance.choices)
    credit = models.CharField(max_length=255, blank=True)
    alt = models.CharField(max_length=255, blank=True)
    decorative = models.BooleanField(default=False)

    api_fields = _writable_api_fields(
        "stable_id", "image", "provenance", "credit", "alt", "decorative"
    )

    panels = [
        FieldPanel("stable_id"),
        FieldPanel("image"),
        FieldPanel("provenance"),
        FieldPanel("credit"),
        FieldPanel("alt"),
        FieldPanel("decorative"),
    ]

    def clean(self) -> None:
        super().clean()
        if self.provenance == self.Provenance.THIRD_PARTY and not self.credit:
            raise ValidationError({"credit": "Third-party assets require a credit."})
        if not self.decorative and not self.alt:
            raise ValidationError({"alt": "Informative assets require alternative text."})
        if self.decorative and self.alt:
            raise ValidationError({"alt": "Decorative assets must have empty alternative text."})


class ProjectEvidence(Orderable):
    class EvidenceType(models.TextChoices):
        REPOSITORY = "repository", "Repository"
        PULL_REQUEST = "pull-request", "Pull request"
        DOCUMENTATION = "documentation", "Documentation"
        TEST = "test", "Test"
        DEMO = "demo", "Demo"
        SCREENSHOT = "screenshot", "Screenshot"
        REPORT = "report", "Report"

    project = ParentalKey(ProjectPage, on_delete=models.CASCADE, related_name="evidence")
    stable_id = models.SlugField(max_length=100)
    evidence_type = models.CharField(max_length=30, choices=EvidenceType.choices)
    url = models.URLField(blank=True)
    asset = models.ForeignKey(
        ProjectAsset,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evidence",
    )
    label = models.CharField(max_length=160)
    description = models.TextField()
    link_label = models.CharField(max_length=160, blank=True)

    api_fields = _writable_api_fields(
        "stable_id", "evidence_type", "url", "asset", "label", "description", "link_label"
    )

    panels = [
        FieldPanel("stable_id"),
        FieldPanel("evidence_type"),
        FieldPanel("url"),
        FieldPanel("asset"),
        FieldPanel("label"),
        FieldPanel("description"),
        FieldPanel("link_label"),
    ]

    def clean(self) -> None:
        super().clean()
        if not self.url and not self.asset_id:
            raise ValidationError("Evidence must reference either a URL or an asset.")


class ProjectClaim(Orderable):
    class Status(models.TextChoices):
        VERIFIED = "verified", "Verified"
        DEMONSTRATED = "demonstrated", "Demonstrated"
        DECLARED = "declared", "Declared"
        PLANNED = "planned", "Planned"

    project = ParentalKey(ProjectPage, on_delete=models.CASCADE, related_name="claims")
    stable_id = models.SlugField(max_length=100)
    text = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices)
    evidence = models.ManyToManyField(
        ProjectEvidence, through="ClaimEvidence", related_name="claims"
    )

    api_fields = _writable_api_fields("stable_id", "text", "status", "evidence")

    panels = [FieldPanel("stable_id"), FieldPanel("text"), FieldPanel("status")]

    def clean(self) -> None:
        super().clean()
        if self.status in {self.Status.VERIFIED, self.Status.DEMONSTRATED} and not self.pk:
            return
        if self.status == self.Status.PLANNED and self.pk and self.evidence.exists():
            raise ValidationError("Planned claims cannot reference evidence.")
        if (
            self.status in {self.Status.VERIFIED, self.Status.DEMONSTRATED}
            and self.pk
            and not self.evidence.exists()
        ):
            raise ValidationError("Verified and demonstrated claims require evidence.")


class ClaimEvidence(models.Model):
    claim = models.ForeignKey(
        ProjectClaim, on_delete=models.CASCADE, related_name="evidence_links"
    )
    evidence = models.ForeignKey(
        ProjectEvidence, on_delete=models.CASCADE, related_name="claim_links"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["claim", "evidence"], name="unique_claim_evidence")
        ]

    def clean(self) -> None:
        super().clean()
        if self.claim_id and self.evidence_id:
            if self.claim.project_id != self.evidence.project_id:
                raise ValidationError("Claim evidence must belong to the same project.")


def validate_portfolio_integrity() -> None:
    """Validate the imported bilingual portfolio as a complete domain dataset."""

    required_locales = {"it", "en"}
    errors: list[str] = []

    blog_variants = list(
        BlogIndexPage.objects.select_related("locale").filter(stable_id="blog")
    )
    if len(blog_variants) != 2 or {
        page.locale.language_code for page in blog_variants
    } != required_locales:
        errors.append("BlogIndex stable_id='blog' requires exactly one it and one en variant.")
    elif len({str(page.translation_key) for page in blog_variants}) != 1:
        errors.append("BlogIndex stable_id='blog' has conflicting translation families.")
    if len(blog_variants) == 2 and {
        page.locale.language_code for page in blog_variants
    } == required_locales:
        site_root = Site.objects.get(is_default_site=True).root_page
        localized_roots = {
            code: site_root.get_translation(
                Locale.objects.get(language_code=code)
            )
            for code in required_locales
        }
        parents = {}
        for page in blog_variants:
            code = page.locale.language_code
            parent = page.get_parent()
            parents[code] = parent
            if parent.locale_id != page.locale_id:
                errors.append(
                    f"BlogIndex stable_id='blog' {code} parent must use the same locale."
                )
            if parent.pk != localized_roots[code].pk:
                errors.append(
                    f"BlogIndex stable_id='blog' {code} must be under its localized site root."
                )
        if len({str(parent.translation_key) for parent in parents.values()}) != 1:
            errors.append(
                "BlogIndex stable_id='blog' parents have conflicting translation families."
            )

    for model, label in ((ProfilePage, "Profile"), (ProjectPage, "Project")):
        groups: dict[str, list[tuple[str, str]]] = {}
        for page in model.objects.select_related("locale"):
            groups.setdefault(page.stable_id, []).append(
                (page.locale.language_code, str(page.translation_key))
            )
        for stable_id, variants in groups.items():
            locales = [locale for locale, _ in variants]
            if set(locales) != required_locales or len(locales) != len(required_locales):
                errors.append(
                    f"{label} stable_id={stable_id!r} requires exactly one it and one en variant."
                )
            if len({translation_key for _, translation_key in variants}) != 1:
                errors.append(
                    f"{label} stable_id={stable_id!r} has conflicting translation families."
                )
        if model is ProfilePage and set(groups) != {"profile"}:
            errors.append("The imported dataset must contain Profile stable_id='profile'.")
        if model is ProjectPage and not groups:
            errors.append("The imported dataset must contain at least one Project.")

    for claim in ProjectClaim.objects.prefetch_related("evidence"):
        if claim.evidence.exclude(project_id=claim.project_id).exists():
            errors.append(
                f"Claim stable_id={claim.stable_id!r} references Evidence from another Project."
            )
        if claim.status in {ProjectClaim.Status.VERIFIED, ProjectClaim.Status.DEMONSTRATED}:
            if not claim.evidence.exists():
                errors.append(
                    f"Claim stable_id={claim.stable_id!r} requires at least one Evidence."
                )
        elif claim.status == ProjectClaim.Status.PLANNED and claim.evidence.exists():
            errors.append(f"Planned claim stable_id={claim.stable_id!r} cannot reference Evidence.")

    if errors:
        raise ValidationError({"portfolio": errors})
