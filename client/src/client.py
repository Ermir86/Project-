
# Desccription: This file contains the client class which is used to connect to the server and send messages to it.
# It also contains the main function which is used to start the client.

from client.lib.gui.gui import GUI
import tkinter as tk


def main():
    root = tk.Tk()
    app = GUI(root=root)
    app.mainloop()


if __name__ == "__main__":
    main()
