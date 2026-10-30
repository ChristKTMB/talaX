import pytest

from talax import Context, FileInfo, IntegrityAssessment, IntegrityVerdict, Metadata


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
            explanation="Manufacturer maker notes are present.",
        ),
    )
