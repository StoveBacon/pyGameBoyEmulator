class RegisterMap:
    def __init__(self,
                 reg: dict[str,int],
                 mem,
                 name,
                 is_immediate=True):
        self.reg = reg
        self.mem = mem
        self.name = name
        self.is_immediate = is_immediate

    @property
    def value(self):
        if self.is_immediate:
            return self.reg[self.name]
        else:
            # Last page indirect read
            return self.mem[self.reg[self.name] + 0xFF00]

    @value.setter
    def value(self, new_value):
        if self.is_immediate:
            self.reg[self.name] = new_value
        else:
            # Last page indirect write
            self.mem[self.reg[self.name] + 0xFF00] = new_value

class SplitRegisterMap(RegisterMap):
    def __init__(self, *args, increment=None, decrement=None):
        super().__init__(*args)
        self.high = self.name[0]
        self.low = self.name[1]
        self.offset = None
        if increment or decrement:
            self.offset = 1 if increment else -1

    @property
    def _reg_value(self):
        return (self.reg[self.high] << 8) + self.reg[self.low]

    @property
    def value(self):
        reg_value = self._reg_value
        if self.is_immediate:
            return reg_value
        else:
            if self.offset:
                self.value = reg_value + self.offset
            return self.mem[reg_value]

    @value.setter
    def value(self, new_value):
        if self.is_immediate:
            self.reg[self.high] = new_value >> 8
            self.reg[self.low] = new_value & 0xFF
        else:
            self.mem[self._reg_value] = new_value

class DirectRegisterMap(RegisterMap):
    def __init__(self, *args, bytes=None):
        super().__init__(*args)
        if bytes is None:
            raise TypeError
        self.bytes = bytes
        self.offset = 0xFF00 if bytes == 1 else 0

    @property
    def value(self):
        dir_value = self.mem[self.reg["PC"]]
        self.reg["PC"] += 1
        if self.bytes == 2:
            dir_value += self.mem[self.reg["PC"]] << 8
            self.reg["PC"] += 1
        if self.is_immediate:
            return dir_value
        else:
            return self.mem[dir_value + self.offset]

    @value.set
    def value(self, new_value):
        self.mem[self.value] = new_value
