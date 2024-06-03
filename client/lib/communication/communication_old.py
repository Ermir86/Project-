
# Desccription: This file contains the communictaion module which is used int the client.py file to send and receive messages from the server.

import serial as uart
from client.lib.security.security import hmac_hash


class evt_handler:
    def send_data(self, data: bytes):
        raise NotImplementedError(
            "The send method must be implemented by subclasses")

    def receive_data(self, size: int) -> bytes:
        raise NotImplementedError(
            "The receive method must be implemented by subclasses")

    def close_connection(self):
        raise NotImplementedError(
            "The close method must be implemented by subclasses")


class SerialCommunication(evt_handler):
    def __init__(self, baudrate, port):
        self.baudrate = baudrate
        self.port = port
        self.ser = None

    def open_connection(self):
        if self.ser is None or not self.ser.is_open:
            self.ser = uart.Serial(self.port, self.baudrate, timeout=1)
        else:
            if self.ser.is_open:
                raise ConnectionError("Port is already open")

    def close_connection(self):
        if self.ser and self.ser.is_open:
            self.ser.write(b"close")
            self.ser.close()

    def is_connected(self):
        return self.ser is not None and self.ser.is_open

    def establish_connection(self):
        try:
            self.open_connection()
            return True, "Connection successfully established."
        except Exception as e:
            return False, str(e)
