from lib.security.security import pk, hmac_hash, RSA_SIZE, EXPONENT
from lib.communication.communication import SerialCommunication


class Session:
    def __init__(self):
        self.connect_state = False
        self.comm = SerialCommunication()

    def session(self):
        return self.connect_state

    def toggle_led(self):
        if self.connect_state:
            self.send_request(b'0x49')
            return True
        return False

    def get_temp(self):
        if self.connect_state:
            self.send_request(b'0x54')
            return True
        return False

    def close_session(self):
        if self.connect_state:
            self.send_request(b'0x10')
            self.comm.close()
            self.connect_state = False

    def send_request(self, data: bytes):
        hmac_hash.update(data)
        data += hmac_hash.digest()
        written = self.comm.write(data)
        if len(data) != written:
            print(
                f"Connection Error: Only {written} bytes written out of {len(data)}")
            self.close_session()
            return False
        return True

    def receive_data(self, size: int) -> bytes:
        buffer = self.comm.read(size + hmac_hash.digest_size)
        hmac_hash.update(buffer[0:size])
        buff = buffer[size:size + hmac_hash.digest_size]
        dig = hmac_hash.digest()
        if buff != dig:
            print("Hash Error")
            self.close_session()
            return b''
        return buffer[0:size]


# Initialize session
session = Session()

# Generate RSA key pair for client
client_rsa = pk.RSA()
client_rsa.generate(RSA_SIZE * EXPONENT)

# Send the public key to the server
session.send_request(client_rsa.export_public_key())  # len249

# Receive the server's public key
buffer = session.receive_data(2 * RSA_SIZE)  # STOP

if buffer:
    SERVER_PUBLIC_KEY = client_rsa.decrypt(buffer[0:RSA_SIZE])
    SERVER_PUBLIC_KEY += client_rsa.decrypt(buffer[RSA_SIZE:2 * RSA_SIZE])
    server_rsa = pk.RSA().from_DER(SERVER_PUBLIC_KEY)

# Clean up client RSA key
del client_rsa
