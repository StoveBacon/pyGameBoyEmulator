from gb_types import uint8, uint16


class Memory:

    def __init__(self):
        pass

    def read(self, address: uint16) -> uint8:
        pass

    def write(self, address: uint16, content: uint8) -> None:
        pass
