"""Create signed and encrypted invoice packets."""

from uuid import uuid4

from tax_collect_data.crypto.jwe_encryptor import JweEncryptor
from tax_collect_data.crypto.jws_signatory import JwsSignatory
from tax_collect_data.models import InvoiceDto, PacketDto, PacketHeaderDto
from tax_collect_data.serialization import serialize


class PacketService:
    def __init__(self, client_id: str, signatory: JwsSignatory, encryptor: JweEncryptor) -> None:
        self._client_id = client_id
        self._signatory = signatory
        self._encryptor = encryptor

    def create_invoice_packet(self, invoice: InvoiceDto) -> PacketDto:
        if invoice is None:
            raise ValueError("invoice cannot be null")
        signed_invoice = self._signatory.sign(serialize(invoice))
        encrypted_invoice = self._encryptor.encrypt(signed_invoice)
        return PacketDto(
            Payload=encrypted_invoice,
            Header=PacketHeaderDto(RequestTraceId=str(uuid4()), FiscalId=self._client_id),
        )
