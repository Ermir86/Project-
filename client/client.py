import tkinter as tk
from tkinter import ttk
from cmmnctn import Communication

class Client(tk.Tk):
    __STATUS_OKAY = 0
    __STATUS_ERROR = 1

    __SESSION_CLOSE = 0
    __SESSION_GET_TEMP = 1
    __SESSION_TOGGLE_LED = 2
    __SESSION_ESTABLISH = 5

    def __init__(self, *args, **kwargs) -> None:
        tk.Tk.__init__(self, *args, **kwargs)
        
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
        pass
    
    def __session_close(self) -> int:
        status = Client.__STATUS_ERROR
        self.__SESSION_ID = bytes(8 * [0])
        if self.__com.send(bytes([Client.__SESSION_CLOSE])):
            buffer = self.__com.receive(1)
            if len(buffer) > 0:
                status = buffer[0]
                self.__session['text'] = "Establish Session"
                self.__temperature.configure(state="disabled")
                self.__toggle.configure(state="disabled")
        return status

    def __session_establish(self) -> int:
        status = Client.__STATUS_ERROR
        self.__SESSION_ID = bytes(8 * [0])
        if self.__com.send(bytes([Client.__SESSION_ESTABLISH])):
            buffer = self.__com.receive(9)
            if len(buffer) > 0:
                status = buffer[0]
                if buffer[0] == Client.__STATUS_OKAY:
                    self.__SESSION_ID = buffer[1:9]
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
        if self.__com.send(bytes([Client.__SESSION_TOGGLE_LED])):
            buffer = self.__com.receive(2)
            if len(buffer) == 0:
                self.__display("Failed to receive")
            elif buffer[0] == Client.__STATUS_OKAY:
                self.__display("LED State:" + ("On" if buffer[1] == 1 else "Off"))
            else:
                self.__display("An error occurred")
        else:
            self.__display("Failed to send")

if __name__ == "__main__":
    client = Client()
    client.mainloop()

    