import serial

class Communication:
    def __init__(self, cominfo: str):
        info = cominfo.split(':')
        self.__con = serial.Serial(info[0], int(info[1]))

    def connect(self) -> bool:
        if not self.__con.is_open:
            self.__con.open()
        return self.__con.is_open

    def disconnect(self):
            self.__con.close()

    def send(self, data: bytes) -> bool:
        status = False
        if self.__con.is_open:
            self.__con.reset_output_buffer()
            status = (len(data) == self.__con.write(data))
        return status

    def receive(self, size: int) -> bytes:
        buffer = b''
        if self.__con.is_open:
            self.__con.reset_input_buffer()
            buffer = self.__con.read(size)
        return buffer
    
    def __del__(self):
        self.disconnect()
