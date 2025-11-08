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
class NewportInput:
    P_CLIENT_ID: Literal[130]
    P_COUNCIL_ID: Literal[260]
    P_LANG_CODE: Literal["EN"]
    P_UPRN: str


class CouncilClass(AbstractGetBinDataClass):
    """
    Concrete classes have to implement all abstract operations of the
    base class. They can also override some operations with a default
    implementation.
    """

    def encode_body(self, newport_input: NewportInput):
        """
        Encrypt a NewportInput dataclass using AES-CBC and encode the resulting ciphertext as a hex string.
        
        Parameters:
            newport_input (NewportInput): Dataclass instance to serialize to JSON and encrypt. The instance is converted to a dict via `asdict()` before serialization.
        
        Returns:
            str: Hex-encoded AES-CBC ciphertext of the JSON-serialized input. Encryption uses the module-level `key_hex` and `iv_hex` values and applies PKCS#7 padding.
        """
        key = bytes.fromhex(key_hex)
        iv = bytes.fromhex(iv_hex)

        json_data = json.dumps(asdict(newport_input))
        data_bytes = json_data.encode("utf-8")

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data_bytes) + padder.finalize()

        backend = default_backend()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        return ciphertext.hex()

    def decode_response(self, hex_input: str):

        """
        Decrypts a hex-encoded AES-CBC ciphertext and returns the parsed JSON payload.
        
        Parameters:
            hex_input (str): Hex-encoded AES-CBC ciphertext to decrypt.
        
        Returns:
            The Python object produced by JSON decoding the decrypted UTF-8 plaintext (typically a dict).
        """
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
        """
        Fetch collection-day information for a given UPRN and return it as a normalized bins dictionary.
        
        Parameters:
            _: str
                Unused placeholder parameter kept for signature compatibility.
            kwargs:
                uprn (str): Unique Property Reference Number to query; this value is validated before use.
        
        Returns:
            dict: A dictionary with a "bins" key containing a list of mappings:
                - "type": the bin type string from the service response.
                - "collectionDate": the collection date formatted as MM/DD/YYYY.
        """
        try:
            user_uprn: str = kwargs.get("uprn") or ""
            check_uprn(user_uprn)
            newport_input = NewportInput(
                P_CLIENT_ID=130, P_COUNCIL_ID=260, P_LANG_CODE="EN", P_UPRN=user_uprn
            )

            encoded_input = self.encode_body(newport_input)

            session = requests.Session()
            response = session.post(
                "https://iweb.itouchvision.com/portal/itouchvision/kmbd/collectionDay",
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