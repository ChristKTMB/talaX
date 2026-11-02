"""Proof that a C2PA trust list is really applied.

The c2pa library ignores unknown settings without a word, so a misspelt or
renamed key would leave every signer "untrusted" and nothing would say so.
Here a certificate authority is made on the spot, an image is signed with it,
and the image must be trusted exactly when that authority is given as anchor.
"""

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

import c2pa
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from PIL import Image

from talax import Context, FileInfo, IntegrityAssessment, IntegrityVerdict, Metadata
from talax.i18n import Message
from talax.model import C2paReport, State
from talax.provenance import read_c2pa
from talax.signals.c2pa_credentials import C2paCredentials


@dataclass(frozen=True)
class Authority:
    root_pem: str
    signed: Path


def _name(cn: str) -> x509.Name:
    return x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, cn),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Tala X test"),
        ]
    )


def _root(cn: str) -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
    key = ec.generate_private_key(ec.SECP256R1())
    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(_name(cn))
        .issuer_name(_name(cn))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return cert, key


def _signer(
    root: x509.Certificate, root_key: ec.EllipticCurvePrivateKey
) -> tuple[x509.Certificate, ec.EllipticCurvePrivateKey]:
    key = ec.generate_private_key(ec.SECP256R1())
    now = dt.datetime.now(dt.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(_name("Tala X test signer"))
        .issuer_name(root.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()),
            critical=False,
        )
        .sign(root_key, hashes.SHA256())
    )
    return cert, key


def _pem(cert: x509.Certificate) -> str:
    return cert.public_bytes(serialization.Encoding.PEM).decode()


@pytest.fixture(scope="module")
def authority(tmp_path_factory: pytest.TempPathFactory) -> Authority:
    root, root_key = _root("Tala X test root")
    leaf, leaf_key = _signer(root, root_key)
    key_pem = leaf_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    folder = tmp_path_factory.mktemp("c2pa")
    source, signed = folder / "source.jpg", folder / "signed.jpg"
    Image.new("RGB", (64, 48), (10, 120, 200)).save(source)
    manifest = {
        "claim_generator_info": [{"name": "talax-test", "version": "1"}],
        "title": "test",
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": "http://cv.iptc.org/newscodes/"
                            "digitalsourcetype/digitalCapture",
                        }
                    ]
                },
            }
        ],
    }
    signer = c2pa.Signer.from_info(
        c2pa.C2paSignerInfo(
            alg=c2pa.C2paSigningAlg.ES256,
            sign_cert=(_pem(leaf) + _pem(root)).encode(),
            private_key=key_pem,
            ta_url=None,
        )
    )
    with (
        c2pa.Builder(json.dumps(manifest)) as builder,
        source.open("rb") as src,
        signed.open("w+b") as dst,
    ):
        builder.sign(signer, "image/jpeg", src, dst)
    return Authority(root_pem=_pem(root), signed=signed)


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
    other, _ = _root("Someone else")
    report = read_c2pa(authority.signed, trust_anchors=_pem(other))
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
