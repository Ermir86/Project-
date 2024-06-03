import serial as uart

BAUDRATE = 115200


class SerialCommunication:
    def __init__(self, port, baudrate=BAUDRATE):
        self.ser = None
        self.port = port
        self.baudrate = baudrate

    def open_connection(self):
        self.ser = uart.Serial(self.port, self.baudrate, timeout=1)

    def send_data(self, data: bytes) -> None:
        if self.ser and self.ser.is_open:
            self.ser.write(data)
            print(f"Sent data: {len(data)} bytes to {self.ser.port}")
            return data
        return b''

    def receive_data(self, size: int) -> bytes:
        if self.ser and self.ser.is_open:
            data = self.ser.read(size)
            print(f"Received data: {len(data)} bytes from {self.ser.port}")
            return data
        return b''

    def close_connection(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Closed connection to {self.ser.port}")

    def is_connected(self) -> bool:
        return self.ser is not None and self.ser.is_open
