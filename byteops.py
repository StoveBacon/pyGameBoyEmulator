# Basic type aliases to help with type checking
uint8 = int
uint16 = int


def unsigned_16(high: uint8, low: uint8) -> uint16:
    """Makes a 16-bit unsigned int from two 8-bit unsigned ints."""
    return ((high << 8) | low) & 0xFFFF
