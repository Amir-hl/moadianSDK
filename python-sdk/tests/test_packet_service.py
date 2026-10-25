from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from datetime import datetime, timedelta, timezone

from tax_collect_data.crypto.jws_signatory import JwsSignatory
from tax_collect_data.crypto.packet_service import PacketService
from tax_collect_data.models import HeaderDto, InvoiceDto


class FakeEncryptor:
    def encrypt(self, text):
        assert text.count(".") == 2
        return "jwe-payload"


def test_packet_contains_fiscal_id_and_trace_id():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    service = PacketService("A111YO", JwsSignatory(cert, key), FakeEncryptor())
    packet = service.create_invoice_packet(
        InvoiceDto(Header=HeaderDto(taxid="TAX-1", indatim=123, ins=1))
    )
    assert packet.Payload == "jwe-payload"
    assert packet.Header.FiscalId == "A111YO"
    assert packet.Header.RequestTraceId
