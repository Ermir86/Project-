import serial as uart
from mbedtls import pk, hmac, hashlib, cipher

RSA_SIZE = 256
EXPONENT = 65537
SECRET_KEY = b"Fj2-;wu3Ur=ARl2!Tqi6IuKM3nG]8z1+"

HMAC_KEY = hashlib.sha256()
HMAC_KEY.update(SECRET_KEY)
HMAC_KEY = HMAC_KEY.digest()
hmac_hash = hmac.new(HMAC_KEY, digestmod="SHA256")

SERIAL_PORT = '/dev/ttyUSB0'
SERIAL_BAUDRATE = 115200
comm = uart.Serial(SERIAL_PORT, SERIAL_BAUDRATE)


def send_data(buf: bytes):
    hmac_hash.update(buf)
    buf += hmac_hash.digest()
    if len(buf) != comm.write(buf):
        print("Connection Error")
        stop_connection()
        exit(1)


def receive_data(size: int) -> bytes:
    buffer = comm.read(size + hmac_hash.digest_size)
    hmac_hash.update(buffer[0:size])
    buff = buffer[size:size + hmac_hash.digest_size]
    dig = hmac_hash.digest()
    # Debugging print statements
    print("b", buff.hex())
    print("d", dig.hex())
    if buff != dig:
        print("Hash Error")
        stop_connection()
        exit(1)

    return buffer[0:size]


def stop_connection():
    comm.write(b"close")
    comm.close()


rsa = pk.RSA()
rsa.generate(RSA_SIZE * 8, EXPONENT)
send_data(rsa.export_public_key())

buffer = receive_data(2 * RSA_SIZE)


public_key_server = rsa.decrypt(buffer[0:RSA_SIZE])
public_key_server += rsa.decrypt(buffer[RSA_SIZE:2 * RSA_SIZE])
server_rsa = pk.RSA().from_DER(public_key_server)

del rsa
rsa = pk.RSA()
rsa.generate(RSA_SIZE * 8, EXPONENT)

buffer = rsa.export_public_key() + rsa.sign(HMAC_KEY, "SHA256")
buffer = server_rsa.encrypt(buffer[0:184]) + server_rsa.encrypt(
    buffer[184:368]) + server_rsa.encrypt(buffer[368:550])
send_data(buffer)

buffer = receive_data(RSA_SIZE)


if b"OKAY" == rsa.decrypt(buffer):
    try:
        buffer = rsa.sign(HMAC_KEY, "SHA256")
        buffer = server_rsa.encrypt(
            buffer[0:RSA_SIZE//2]) + server_rsa.encrypt(buffer[RSA_SIZE//2:RSA_SIZE])
        send_data(buffer)

        buffer = receive_data(RSA_SIZE)
        buffer = rsa.decrypt(buffer)
        SESSION_ID = buffer[0:8]

        aes = cipher.AES.new(buffer[24:56], cipher.MODE_CBC, buffer[8:24])

        try:
            # Temperature request
            request = bytes([0x54])
            buffer = request + SESSION_ID
            plen = cipher.AES.block_size - \
                (len(buffer) % cipher.AES.block_size)
            buffer = aes.encrypt(buffer + bytes([len(buffer)] * plen))
            send_data(buffer)

            buffer = receive_data(cipher.AES.block_size)
            buffer = aes.decrypt(buffer)
            if buffer[0] == 0x10:
                print(buffer[1:6].decode("ASCII"))
                # print("Temperature: ", buffer[1:6].decode("ASCII") + "°C")
            else:
                print("Command not found!")
                print(buffer[0])
        except ValueError:
            print("Invalid input. Please try again.")

    except Exception as e:
        stop_connection()
        print(e)
