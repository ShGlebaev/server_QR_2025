import socket
import asyncio

class DoorLock:
    def __init__(self, ip_door="10.10.22.6", port_door=9091, debug=False):
        self.ip_door = ip_door
        self.port_door = port_door
        self.debug = debug

    async def open_door(self):
        await self.send_message("open")

    async def disable_door(self):
        await self.send_message("disable_door")

    async def enable_door(self):
        await self.send_message("enable_door")

    async def send_message(self, message):
        if not self.debug:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.connect((self.ip_door, self.port_door))
                    sock.sendall(message.encode('utf-8'))
                    data = sock.recv(1024)
                    print(data.decode('utf-8'))
                    if data == message.encode('utf-8'):
                        print("Команда дошла успешно")
                    else:
                        print("Что-то пошло не так")
            except ConnectionRefusedError:
                print("Соединение с дверью не установлено")
        else:
            print(f"Команда отправленная на дверь: {message}")
