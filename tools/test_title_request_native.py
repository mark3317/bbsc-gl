"""Execute native title/reload commands on fake memory, without starting the game.

Usage: python tools/test_title_request_native.py <analysis eboot.elf>
Game instructions are read locally; no game data is stored in this fixture.
Only character serialization is stubbed. Both native command bodies run intact.
"""
import ctypes
from pathlib import Path
import struct
import sys


data = Path(sys.argv[1]).read_bytes()
assert data[:4] == b'\x7fELF', 'Pass the analysis ELF, not a SELF container'
phoff = struct.unpack_from('<Q', data, 32)[0]
phsize, phcount = struct.unpack_from('<HH', data, 54)
segments = [struct.unpack_from('<IIQQQQQQ', data, phoff + n * phsize)
            for n in range(phcount)]


def read(address, size):
    for kind, flags, offset, virtual, physical, length, memsize, alignment in segments:
        if kind == 1 and virtual <= address and address + size <= virtual + length:
            return data[offset + address - virtual:offset + address - virtual + size]
    raise ValueError(hex(address))


title = read(0x0138BAF0, 0x4B)
reload = read(0x013CDE30, 0xFD)
assert title[0x3D:0x44] == bytes.fromhex('c7 40 08 02 00 00 00')
assert reload[0x15:0x19] == bytes.fromhex('c6 40 08 01')

kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
kernel.VirtualAlloc.restype = ctypes.c_void_p
kernel.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong]
kernel.FlushInstructionCache.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
image = kernel.VirtualAlloc(None, 0x6000000, 0x3000, 0x40)
assert image, ctypes.get_last_error()
buffers = []


def buffer(size):
    value = ctypes.create_string_buffer(size)
    buffers.append(value)
    return ctypes.addressof(value)


def put64(address, value):
    ctypes.c_uint64.from_address(address).value = value


try:
    world, eventman, request = buffer(0x1800), buffer(0x100), buffer(0x10)
    slots, slot, chrman = buffer(0x100), buffer(0x400), buffer(0x100)
    put64(image + 0x05556678, world)
    put64(image + 0x0553B108, eventman)
    put64(eventman + 0x10, request)
    put64(image + 0x0553B130, slots)
    put64(slots + 8, slot)
    put64(image + 0x0553E878, chrman)
    ctypes.c_uint8.from_address(world + 0x1592).value = 1  # host's own world
    ctypes.memmove(image + 0x0138BAF0, title, len(title))
    ctypes.memmove(image + 0x013CDE30, reload, len(reload))
    ctypes.memmove(image + 0x014CCD40, b'\xc3', 1)  # isolated character snapshot

    def command(offset):
        # Win64 -> guest SysV: preserve RDI/RSI and align the guest call stack.
        wrapper = (bytes.fromhex('57 56 48 83 ec 08 48 b8') +
                   struct.pack('<Q', image + offset) +
                   bytes.fromhex('ff d0 48 83 c4 08 5e 5f c3'))
        ctypes.memmove(image, wrapper, len(wrapper))
        kernel.FlushInstructionCache(ctypes.c_void_p(-1), image, 0x6000000)
        return ctypes.CFUNCTYPE(ctypes.c_uint32)(image)()

    command(0x0138BAF0)
    assert ctypes.c_int32.from_address(request + 8).value == 2
    assert ctypes.c_uint8.from_address(world + 8).value == 0
    # Reproduce the removed sequence. A pending title request does NOT prevent
    # the real StageTransition from arming an additional world reload.
    assert command(0x013CDE30) == 1
    assert ctypes.c_int32.from_address(request + 8).value == 2
    assert ctypes.c_uint8.from_address(world + 8).value == 1
    # Execute the actual StageFlow menu-exit branch, not a hand-written model.
    # Its +150 flag distinguishes the native System exit from a world reload.
    task, frame, menu = buffer(0x300), buffer(0x400), buffer(0x400)
    put64(image + 0x05556678, world)
    put64(image + 0x05562878, menu)
    start, end = 0x01940DBB, 0x01940E86
    ctypes.memmove(image + start, read(start, end-start), end-start)
    # Stop at either branch boundary before unrelated engine work.
    ctypes.memmove(image + 0x01940E16, b'\xc3', 1)
    ctypes.memmove(image + end, b'\xc3', 1)
    wrapper = (bytes.fromhex('55 41 55 48 83 ec 08 48 bd') + struct.pack('<Q', frame+0x200) +
               bytes.fromhex('49 bd') + struct.pack('<Q', task) +
               bytes.fromhex('48 b8') + struct.pack('<Q', image+start) +
               bytes.fromhex('ff d0 48 83 c4 08 41 5d 5d c3'))
    ctypes.memmove(image, wrapper, len(wrapper))
    for confirmed in (0,1):
        ctypes.c_int32.from_address(frame+0x200-0x160).value=confirmed
        ctypes.c_int32.from_address(frame+0x200-0x140).value=0
        ctypes.c_uint8.from_address(task+0x150).value=0
        ctypes.c_int32.from_address(world+0x154C).value=-1
        ctypes.c_int32.from_address(menu+0x250).value=confirmed
        kernel.FlushInstructionCache(ctypes.c_void_p(-1), image, 0x6000000)
        ctypes.CFUNCTYPE(None)(image)()
        assert ctypes.c_uint8.from_address(task+0x150).value==confirmed
        assert ctypes.c_int32.from_address(menu+0x250).value==0
    print('Native StageFlow: confirmed menu latch selects exit +150; title request alone omits it: PASS')
    print('Native title request alone: no reload; old title + StageTransition: world reload armed: PASS')
finally:
    kernel.VirtualFree(image, 0, 0x8000)
