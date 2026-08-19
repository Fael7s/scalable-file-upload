import pytest

from app.config import get_settings
from app.services.s3_service import S3Service
from tests.conftest import s3_keys

settings = get_settings()

PROBE_KEY = "probe.txt"


@pytest.mark.asyncio
async def test_fixture_bucket_is_the_one_the_application_writes_to(s3):
    # S3Service resolves its bucket from the settings at construction time. If
    # the fixture ever created a different bucket the S3 assertions across the
    # suite would read an empty mock while the application wrote elsewhere, so
    # every one of them would still pass against a broken application.
    assert S3Service().bucket == settings.S3_BUCKET_NAME
    s3.head_bucket(Bucket=settings.S3_BUCKET_NAME)

    assert s3_keys(s3) == []
    s3.put_object(Bucket=settings.S3_BUCKET_NAME, Key=PROBE_KEY, Body=b"probe")
    assert s3.get_object(
        Bucket=settings.S3_BUCKET_NAME, Key=PROBE_KEY
    )["Body"].read() == b"probe"


@pytest.mark.asyncio
async def test_fixture_bucket_starts_empty_for_each_test(s3):
    # This test and the one above both assert an empty bucket on entry and then
    # write the same key, so whichever order they run in the second one only
    # sees an empty listing if the mock_aws context is torn down per test.
    assert s3_keys(s3) == []
    s3.put_object(Bucket=settings.S3_BUCKET_NAME, Key=PROBE_KEY, Body=b"probe")
    assert s3_keys(s3) == [PROBE_KEY]
