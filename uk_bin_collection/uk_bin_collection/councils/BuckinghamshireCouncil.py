import json
from dataclasses import asdict, dataclass
from typing import Literal

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from uk_bin_collection.uk_bin_collection.common import check_uprn
from uk_bin_collection.uk_bin_collection.get_bin_data import AbstractGetBinDataClass

key_hex = "F57E76482EE3DC3336495DEDEEF3962671B054FE353E815145E29C5689F72FEC"
iv_hex = "2CBF4FC35C69B82362D393A4F0B9971A"


@dataclass
class BucksInput:
    P_CLIENT_ID: Literal[152]
    P_COUNCIL_ID: Literal[34505]
    P_LANG_CODE: Literal["EN"]
    P_UPRN: str


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def encode_body(self, bucks_input: BucksInput):
        key = bytes.fromhex(key_hex)
        iv = bytes.fromhex(iv_hex)

        json_data = json.dumps(asdict(bucks_input))
        data_bytes = json_data.encode("utf-8")

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data_bytes) + padder.finalize()

        backend = default_backend()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        return ciphertext.hex()

    def decode_response(self, hex_input: str):

        key = bytes.fromhex(key_hex)
        iv = bytes.fromhex(iv_hex)
        ciphertext = bytes.fromhex(hex_input)

        backend = default_backend()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        plaintext_bytes = unpadder.update(decrypted_padded) + unpadder.finalize()
        plaintext = plaintext_bytes.decode("utf-8")

        return json.loads(plaintext)

    def parse_data(self, _: str, **kwargs) -> dict:
        try:
            user_uprn: str = kwargs.get("uprn") or ""
            check_uprn(user_uprn)
            bucks_input = BucksInput(
                P_CLIENT_ID=152, P_COUNCIL_ID=34505, P_LANG_CODE="EN", P_UPRN=user_uprn
            )

            encoded_input = self.encode_body(bucks_input)

            session = requests.Session()
            response = session.post(
                "https://itouchvision.app/portal/itouchvision/kmbd/collectionDay",
                data=encoded_input,
            )

            output = response.text

            decoded_bins = self.decode_response(output)
            data: dict[str, list[dict[str, str]]] = {}
            data["bins"] = list(
                map(
                    lambda a: {
                        "type": a["binType"],
                        "collectionDate": a["collectionDay"].replace("-", "/"),
                    },
                    decoded_bins["collectionDay"],
                )
            )

        except Exception as e:
            # Here you can log the exception if needed
            print(f"An error occurred: {e}")
            # Optionally, re-raise the exception if you want it to propagate
            raise
        return data
