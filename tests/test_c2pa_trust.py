"""Proof that a C2PA trust list is really applied.

The c2pa library ignores unknown settings without a word, so a misspelt or
renamed key would leave every signer "untrusted" and nothing would say so.
Here a certificate authority is made on the spot, an image is signed with it,
and the image must be trusted exactly when that authority is given as anchor.
"""

import hashlib
import shutil
from pathlib import Path

import pytest
import yaml
from cryptography import x509

from talax import Context, FileInfo, IntegrityAssessment, IntegrityVerdict, Metadata
from talax.analysis import analyze
from talax.i18n import Message
from talax.model import C2paReport, State
from talax.provenance import (
    TrustList,
    embedded_trust_list,
    load_trust_list,
    read_c2pa,
)
from talax.signals.c2pa_credentials import C2paCredentials
from tests.c2pa_authority import Authority, make_authority, make_root, pem

EMBEDDED = Path(__file__).resolve().parent.parent / "src" / "talax" / "data" / "c2pa"


@pytest.fixture(scope="module")
def authority(tmp_path_factory: pytest.TempPathFactory) -> Authority:
    return make_authority(tmp_path_factory.mktemp("c2pa"))


def _verdict(report: C2paReport) -> State:
    ctx = Context(
        file=FileInfo("0" * 64, 1, "image/jpeg", "image/jpeg"),
        metadata=Metadata({}),
        integrity=IntegrityAssessment(
            IntegrityVerdict.UNDETERMINED, Message("integrity.no_metadata_other")
        ),
        c2pa=report,
    )
    return C2paCredentials().evaluate(ctx).state


def test_signer_is_untrusted_without_anchors(authority: Authority) -> None:
    report = read_c2pa(authority.signed)
    assert report.state == "Valid"
    assert "signingCredential.untrusted" in report.codes
    assert _verdict(report) is State.TO_CHECK


def test_signer_is_trusted_when_its_root_is_an_anchor(authority: Authority) -> None:
    report = read_c2pa(authority.signed, trust_anchors=authority.root_pem)
    assert report.state == "Trusted"
    assert report.codes == ()
    assert _verdict(report) is State.CONSISTENT


def test_another_root_does_not_make_it_trusted(authority: Authority) -> None:
    other, _ = make_root("Someone else")
    report = read_c2pa(authority.signed, trust_anchors=pem(other))
    assert report.state == "Valid"
    assert "signingCredential.untrusted" in report.codes


def test_trusted_signer_does_not_hide_a_changed_image(
    authority: Authority, tmp_path: Path
) -> None:
    data = bytearray(authority.signed.read_bytes())
    data[-10] ^= 0xFF  # inside the image data, after the signature
    changed = tmp_path / "changed.jpg"
    changed.write_bytes(data)
    report = read_c2pa(changed, trust_anchors=authority.root_pem)
    assert "assertion.dataHash.mismatch" in report.codes
    assert _verdict(report) is State.TO_CHECK


def test_embedded_list_matches_its_record() -> None:
    record = yaml.safe_load((EMBEDDED / "source.yaml").read_text("utf-8"))
    data = (EMBEDDED / "C2PA-TRUST-LIST.pem").read_bytes()
    assert hashlib.sha256(data).hexdigest() == record["sha256"]
    certs = x509.load_pem_x509_certificates(data)
    assert len(certs) == record["certificates"] > 0
    assert all(
        c.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
        for c in certs
    )
    assert record["issued"] < record["next_update"]
    assert record["license"] == "CC-BY-4.0"


def test_altered_list_is_refused(tmp_path: Path) -> None:
    folder = tmp_path / "c2pa"
    shutil.copytree(EMBEDDED, folder)
    with (folder / "C2PA-TRUST-LIST.pem").open("ab") as f:
        f.write(b"\n")
    with pytest.raises(RuntimeError, match="does not match"):
        load_trust_list(folder)


def test_analysis_applies_the_embedded_list(
    authority: Authority, monkeypatch: pytest.MonkeyPatch
) -> None:
    def c2pa_state() -> State:
        result = next(
            r for r in analyze(authority.signed).results if r.signal_id == "c2pa"
        )
        return result.state

    # The official list does not trust a test authority...
    assert c2pa_state() is State.TO_CHECK
    # ...and what analyze() trusts is exactly what the embedded list says.
    ours = TrustList(authority.root_pem, "2026-01-01", "2027-01-01", "test")
    monkeypatch.setattr("talax.analysis.embedded_trust_list", lambda: ours)
    assert c2pa_state() is State.CONSISTENT


def test_embedded_list_is_read_once() -> None:
    assert embedded_trust_list() is embedded_trust_list()
