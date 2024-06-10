import tkinter as tk
from tkinter import ttk
from cmmnctn import Communication
from mbedtls import pk, hmac, hashlib, cipher

class Client(tk.Tk):

    __RSA_SIZE = 256
    __EXPONENT = 65537
    __SESSION_ID: bytes
    __SECRET_KEY = b"Fj2-;wu3Ur=ARl2!Tqi6IuKM3nG]8z1+"

    __CLOSE = 0
    __GET_TEMP = 1
    __TOGGLE_LED = 2

    __STATUS_OKAY = 0
    __STATUS_ERROR = 1

    STATUS_OKAY = 0
    STATUS_ERROR = 1
    STATUS_EXPIRED = 2
    STATUS_HASH_ERROR = 3
    STATUS_BAD_REQUEST = 4
    STATUS_INVALID_SESSION = 5
    STATUS_CONNECTION_ERROR = 6

    def __init__(self) -> None:
        super().__init__()
        self.__SESSION_ID = bytes([0] * 8)        
        self.title("Client")
        self.geometry("800x600")
        self.wm_attributes('-topmost', 1)
        self.resizable(width=False, height=False)

        ttk.Label(self, text="Serial Port: ", font=("Arial", 13)
                  ).place(x=10, y=15, width=110, height=30)
        
        self.__port = ttk.Combobox(state="readonly")
        temp = []
        import serial.tools.list_ports
        prts = serial.tools.list_ports.comports()
        for name, desc, hwid in sorted(prts):
            temp.append(name)
        self.__port["values"] = temp
        self.__port.place(x = 110, y = 15, width=150, height=30)
        self.__port.bind("<<ComboboxSelected>>", lambda e: self.__port_selected())
        self.__port.current()

        self.__session = tk.Button(text="Establish Session", command=self.__session_clicked)
        self.__session.place(x=280, y=15, width=150, height=30)
        self.__session.configure(state="disabled")

        self.__temperature = tk.Button(text="Get Temperature", command=self.__temperature_clicked)
        self.__temperature.place(x=450, y=15, width=150, height=30)
        self.__temperature.configure(state="disabled")

        self.__toggle = tk.Button(text="Toggle LED", command=self.__toggle_clicked)
        self.__toggle.place(x=620, y=15, width=150, height=30)
        self.__toggle.configure(state="disabled")

        ttk.Label(self, text="Log: ", font=("Arial", 13)).place(x=10, y=60, width=110, height=30)

        self.__clear = tk.Label(text="Clear", font=("Arial", 13), cursor="hand2", fg="blue")
        self.__clear.bind("<Button-1>", lambda e: self.__clear_clicked())
        self.__clear.place(x=700, y=60, width=100, height=30)

        self.__log = tk.Text(font=("Arial", 11), bg="black", fg="white", padx=5, pady=5)
        self.__log.place(x=10, y=90, width=780, height=500)
        self.__log.configure(state="disabled")

        self.__SESSION_ID = bytes(8 * [0])
    #init
    def __initialize(self):
        if not self.__com.connect():
            print("Faild to connect")
            exit(1)
        
        self.__hmac = hashlib.sha256()
        self.__hmac.update(self.__SECRET_KEY)
        self.__hmac = self.__hmac.digest()
        self.__hmac = hmac.new(self.__hmac, digestmod="SHA256")

        self.__clientRSA = pk.RSA()
        self.__clientRSA.generate(self.__RSA_SIZE * 8, self.__EXPONENT)
    # change_key
    def __handshake(self):
        if not self.__send(self.__clientRSA.export_public_key()):
            print("1) Faild to exchange keys")
            exit(1)

        buffer = self.__receive(2 * self.__RSA_SIZE)
        if 0 == len(buffer): 
            print("2) Faild to exchange keys")
            exit(1)

        server_pk = self.__clientRSA.decrypt(buffer[0:self.__RSA_SIZE])
        server_pk += self.__clientRSA.decrypt(buffer[self.__RSA_SIZE:2 * self.__RSA_SIZE])
        self.__serverRSA = pk.RSA().from_DER(server_pk)

        del self.__clientRSA
        self.__clientRSA = pk.RSA()
        self.__clientRSA.generate(self.__RSA_SIZE * 8, self.__EXPONENT)

        buffer = self.__clientRSA.export_public_key() + self.__clientRSA.sign(self.__SECRET_KEY, "SHA256")
        buffer = self.__serverRSA.encrypt(buffer[0:184]) + self.__serverRSA.encrypt(buffer[184:368]) + self.__serverRSA.encrypt(buffer[368:550])

        if not self.__send(buffer):
            print("3) Faild to exchange keys")
            exit(1)

        buffer = self.__receive(self.__RSA_SIZE)
        if 0 == len(buffer): 
            print("4) Faild to exchange keys")
            exit(1)
        
        if b"DONE" != self.__clientRSA.decrypt(buffer):
            print("5) Faild to exchange keys")
            exit(1)        

    def __port_selected(self):
        self.__com = Communication("{0}:115200".format(self.__port.get()))
        self.__session.configure(state="normal")

    def __display(self, text:str):
        self.__log.configure(state="normal")
        self.__log.insert(tk.END, text + '\n')
        self.__log.configure(state="disabled")

    def __clear_clicked(self):
        self.__log.configure(state="normal")
        self.__log.delete('1.0', tk.END)
        self.__log.configure(state="disabled")

    def __temperature_clicked(self):

        status = Client.STATUS_INVALID_SESSION

        if 0 != int.from_bytes(self.__SESSION_ID, 'little'):
            buffer = bytes([self.__GET_TEMP]) + self.__SESSION_ID
            plen = cipher.AES.block_size - (len(buffer) % cipher.AES.block_size)
            buffer = self.__AES.encrypt(buffer + bytes([len(buffer)] * plen))

            if self.__send(buffer):
                buffer = self.__receive(cipher.AES.block_size)
                if 0 == len(buffer):
                    status = Client.STATUS_CONNECTION_ERROR
                else:
                    buffer = self.__AES.decrypt(buffer)
                    self.__display(("Temperature: "+str(buffer[1:6],"utf-8")+"°C"))
                    
                    if buffer[0] == Client.__STATUS_OKAY:
                        status = buffer[0]
                    else:
                        self.__display("An error occurred "+("STATUS EXPIRED" if buffer[0] == 2 else "STATUS BAD REQUEST") +" !")
            else:
                status = Client.STATUS_CONNECTION_ERROR

            if status == Client.STATUS_CONNECTION_ERROR or status == Client.STATUS_EXPIRED:
                self.__SESSION_ID = bytes([0] * 8)
    
    def __session_close(self) -> int:
        status = Client.__STATUS_ERROR

        buffer = bytes([self.__CLOSE]) + self.__SESSION_ID
        plen = cipher.AES.block_size - (len(buffer) % cipher.AES.block_size)
        buffer = self.__AES.encrypt(buffer + bytes([len(buffer)] * plen))

        if self.__send(buffer):
            buffer = self.__receive(cipher.AES.block_size)
            if len(buffer) > 0:
                self.__session['text'] = "Establish Session"
                self.__temperature.configure(state="disabled")
                self.__toggle.configure(state="disabled")
                buffer = self.__AES.decrypt(buffer)
                if len(buffer) > 1:
                    status = buffer[0]
                    self.__SESSION_ID = bytes([0] * 8)
                    self.__com.disconnect()
        else:
            status = Client.STATUS_CONNECTION_ERROR
        return status

    def __receive(self, length: int) -> bytes:
        buffer = self.__com.receive(length + self.__hmac.digest_size)
        self.__hmac.update(buffer[0:length])
        if buffer[length:length + self.__hmac.digest_size] != self.__hmac.digest():
            buffer = b''
        else:
            buffer = buffer[0:length]

        return buffer
    
    def __send(self, buf: bytes) -> bool:
        self.__hmac.update(buf)
        buf += self.__hmac.digest()
        return self.__com.send(buf)



    def __session_establish(self) -> int:
        self.__initialize()
        self.__handshake()

        status = Client.__STATUS_OKAY
        self.__SESSION_ID = bytes(8 * [0])

        if not self.__com.connect():
            status =  Client.STATUS_CONNECTION_ERROR
        else:
            buffer = self.__clientRSA.sign(Client.__SECRET_KEY, "SHA256")
            buffer = self.__serverRSA.encrypt(buffer[0:Client.__RSA_SIZE//2]) + self.__serverRSA.encrypt(buffer[Client.__RSA_SIZE//2:Client.__RSA_SIZE]) 

        if self.__send(buffer):
            buffer = self.__receive(self.__RSA_SIZE)
            if 0 == len(buffer):
                status = Client.STATUS_CONNECTION_ERROR
            if status == Client.__STATUS_OKAY:
                buffer = self.__clientRSA.decrypt(buffer)
                self.__SESSION_ID = buffer[0:8]
                if 0 == int.from_bytes(self.__SESSION_ID, 'little'):
                    status = Client.STATUS_ERROR
                else:
                    self.__AES = cipher.AES.new(buffer[24:56], cipher.MODE_CBC, buffer[8:24])
                self.__session['text'] = "Close Session"
                self.__temperature.configure(state="normal")
                self.__toggle.configure(state="normal")
        return status

    def __session_clicked(self):
        if 0 == int.from_bytes(self.__SESSION_ID, 'little'):
            status = self.__session_establish()
            self.__display("Establish Session: " + ("Done" if status == Client.__STATUS_OKAY else "Failed"))
        else:
            status = self.__session_close()
            self.__display("Close Session: " + ("Done" if status == Client.__STATUS_OKAY else "Failed"))

    def __toggle_clicked(self):
        if 0 != int.from_bytes(self.__SESSION_ID, 'little'):
            buffer = bytes([self.__TOGGLE_LED]) + self.__SESSION_ID
            plen = cipher.AES.block_size - (len(buffer) % cipher.AES.block_size)
            buffer = self.__AES.encrypt(buffer + bytes([len(buffer)] * plen))

            if self.__send(buffer):
                buffer = self.__receive(cipher.AES.block_size)
                if len(buffer) == 0:
                    self.__display("Failed to receive")
                else:
                    buffer = self.__AES.decrypt(buffer)
                    if buffer[0] == Client.__STATUS_OKAY:
                        self.__display("LED State:" + ("On" if buffer[1:3] == b"on" else "Off"))
                    else:
                        self.__display("An error occurred "+("STATUS EXPIRED" if buffer[0] == 2 else "STATUS BAD REQUEST") +" !")
            else:
                self.__display("Failed to send")

if __name__ == "__main__":
    client = Client()
    client.mainloop()

    