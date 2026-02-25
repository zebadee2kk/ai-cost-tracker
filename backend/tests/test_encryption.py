import pytest
from utils.encryption import encrypt_api_key, decrypt_api_key


def test_roundtrip():
    key = "sk-test-1234567890abcdef"
    assert decrypt_api_key(encrypt_api_key(key)) == key


def test_different_plaintexts_produce_different_ciphertexts():
    c1 = encrypt_api_key("key-one")
    c2 = encrypt_api_key("key-two")
    assert c1 != c2


def test_decrypt_wrong_data_raises():
    with pytest.raises(ValueError):
        decrypt_api_key("not-valid-ciphertext")


def test_empty_string_roundtrip():
    assert decrypt_api_key(encrypt_api_key("")) == ""
