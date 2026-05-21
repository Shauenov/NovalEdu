from app.core.constants import BUCKET_AVATARS, BUCKET_NEWS, BUCKET_UNIVERSITIES
from app.modules.news.schemas import NewsOut
from app.modules.universities.schemas import UniversityOut
from app.modules.users.schemas import UserOut
from app.storage.minio_client import get_public_url, resolve_public_url


class _Row:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_resolve_public_url_keeps_existing_url():
    value = "https://cdn.example.com/image.png"

    assert resolve_public_url(BUCKET_NEWS, value) == value


def test_resolve_public_url_builds_public_url_from_object_key():
    key = "abc/def/image.png"

    assert resolve_public_url(BUCKET_AVATARS, key) == get_public_url(BUCKET_AVATARS, key)


def test_user_news_and_university_outputs_normalize_image_fields():
    user = UserOut.model_validate(
        _Row(
            id="11111111-1111-1111-1111-111111111111",
            email="a@example.com",
            full_name="A",
            role="student",
            is_active=True,
            avatar_url="avatars/a.png",
            created_at="2026-05-16T00:00:00Z",
        )
    )
    news = NewsOut.model_validate(
        _Row(
            id="22222222-2222-2222-2222-222222222222",
            title="Title",
            body="Body",
            cover_url="news/covers/b.png",
            category="general",
            event_date=None,
            external_url=None,
            is_published=True,
            author_id="33333333-3333-3333-3333-333333333333",
            views_count=0,
            created_at="2026-05-16T00:00:00Z",
            updated_at="2026-05-16T00:00:00Z",
        )
    )
    university = UniversityOut.model_validate(
        _Row(
            id="44444444-4444-4444-4444-444444444444",
            name="University",
            country="Kazakhstan",
            city=None,
            logo_url="universities/u/logo.png",
            cover_image_url="universities/u/cover.png",
            website_url=None,
            description=None,
            acceptance_rate=None,
            total_students=None,
            international_pct=None,
            qs_ranking=None,
            the_ranking=None,
            language_of_instr=None,
            is_published=True,
            last_verified_at=None,
            created_at="2026-05-16T00:00:00Z",
            updated_at="2026-05-16T00:00:00Z",
        )
    )

    assert user.avatar_url == get_public_url(BUCKET_AVATARS, "avatars/a.png")
    assert news.cover_url == get_public_url(BUCKET_NEWS, "news/covers/b.png")
    assert university.logo_url == get_public_url(BUCKET_UNIVERSITIES, "universities/u/logo.png")
    assert university.cover_image_url == get_public_url(BUCKET_UNIVERSITIES, "universities/u/cover.png")