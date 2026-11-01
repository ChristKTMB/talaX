import pytest

from talax import Context, FileInfo, IntegrityAssessment, IntegrityVerdict, Metadata
from talax.i18n import Message

# Any valid message, for tests that only need a well-formed result.
OK = Message("real_format.consistent", {"real": "JPEG"})


@pytest.fixture
def ctx() -> Context:
    return Context(
        file=FileInfo(
            sha256="0" * 64,
            size=1024,
            declared_format="image/jpeg",
            real_format="image/jpeg",
        ),
        metadata=Metadata({"EXIF:Make": "Apple"}),
        integrity=IntegrityAssessment(
            verdict=IntegrityVerdict.ORIGINAL,
            message=Message("integrity.no_metadata_other"),
        ),
    )
