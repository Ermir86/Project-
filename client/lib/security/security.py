# Author: Oliver Joisten
# Description: This file contains the security module which is used in the client.py file to encrypt and decrypt messages.

from mbedtls import pk, hmac, hashlib, cipher

RSA_SIZE = 256
EXPONENT = 65537
SECRET_KEY = b"Fj2-;wu3Ur=ARl2!Tqi6IuKM3nG]8z1+"

# HMAC setup
HMAC_KEY = hashlib.sha256()
HMAC_KEY.update(SECRET_KEY)
HMAC_KEY = HMAC_KEY.digest()
hmac_hash = hmac.new(HMAC_KEY, digestmod="SHA256")

# RSA setup
rsa = pk.RSA()
rsa.generate(RSA_SIZE * 8, EXPONENT)


def initialize_rsa():
    rsa.generate(RSA_SIZE * 8, EXPONENT)
    return rsa


def get_hmac_key():
    return HMAC_KEY


def create_aes(buffer):
    return cipher.AES.new(buffer[24:56], cipher.MODE_CBC, buffer[8:24])


def export_public_key(rsa):
    return rsa.export_public_key()


def decrypt_rsa(rsa, buffer):
    return rsa.decrypt(buffer)


def sign_rsa(rsa, HMAC_KEY):
    return rsa.sign(HMAC_KEY, "SHA256")


def encrypt_rsa(rsa, buffer):
    return rsa.encrypt(buffer)


def send_data(self, buf: bytes):
    if self.ser and self.ser.is_open:
        hmac_hash.update(buf)
        buf += hmac_hash.digest()
        print(f"Sending data (length {len(buf)}): {buf.hex()}")
        written = self.ser.write(buf)
        if len(buf) != written:
            print(
                f"Connection Error: Only {written} bytes written out of {len(buf)}")
            self.close_connection()
            return False, None
        self.ser.flush()
        print("Data flushed.")
        return True, buf
    else:
        if self.ser is None:
            raise ConnectionError("Serial port is not open")


def receive_data(self, size: int) -> bytes:
    if self.ser and self.ser.is_open:
        buffer = self.ser.read(size + hmac_hash.digest_size)
        print(f"Received raw data (length {len(buffer)}): {buffer.hex()}")
        hmac_hash.update(buffer[0:size])
        buff = buffer[size:size + hmac_hash.digest_size]
        dig = hmac_hash.digest()
        print("b", buff.hex())
        print("d", dig.hex())
        if buff != dig:
            print("Hash Error")
            self.close_connection()
            return bytes()
        return buffer[0:size]
    else:
        if self.ser is None:
            raise ConnectionError("Serial port is not open")
