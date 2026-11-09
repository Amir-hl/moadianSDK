
"""Create signed and encrypted invoice packets."""

from uuid import uuid4

from tax_collect_data.contracts.crypto import Encryptor, Serializer, Signatory
from tax_collect_data.models import InvoiceDto, PacketDto, PacketHeaderDto


class PacketService:
    def __init__(
        self,
        client_id: str,
        signatory: Signatory,
        encryptor: Encryptor,
        serializer: Serializer,
    ) -> None:
        self._client_id = client_id
        self._signatory = signatory
        self._encryptor = encryptor
        self._serializer = serializer

    def create_invoice_packet(self, invoice: InvoiceDto) -> PacketDto:
        if invoice is None:
            raise ValueError("invoice cannot be null")

        serialized_invoice = self._serializer.serialize(invoice)
        signed_invoice = self._signatory.sign(serialized_invoice)
        encrypted_invoice = self._encryptor.encrypt(signed_invoice)

        return PacketDto(
            Payload=encrypted_invoice,
            Header=PacketHeaderDto(
                RequestTraceId=str(uuid4()),
                FiscalId=self._client_id,
            ),
        )
