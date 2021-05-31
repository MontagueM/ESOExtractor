import os
import numpy as np
import struct


def fill_hex_with_zeros(s, desired_length):
    return ("0"*desired_length + s)[-desired_length:]


def get_hex_data(direc):
    t = open(direc, 'rb')
    h = t.read().hex().upper()
    return h


def get_flipped_hex(h, length):
    if length % 2 != 0:
        print("Flipped hex length is not even.")
        return None
    return "".join(reversed([h[:length][i:i + 2] for i in range(0, length, 2)]))


def get_file_from_hash(hsh):
    hsh = get_flipped_hex(hsh, 8)
    first_int = int(hsh, 16)
    one = first_int - 2155872256
    first_hex = hex(int(np.floor(one/8192)))
    second_hex = hex(first_int % 8192)
    return f'{fill_hex_with_zeros(first_hex[2:], 4)}-{fill_hex_with_zeros(second_hex[2:], 4)}'.upper()


def get_hash_from_file(file):
    pkg = file.replace(".bin", "").upper()

    firsthex_int = int(pkg[:4], 16)
    secondhex_int = int(pkg[5:], 16)

    one = firsthex_int*8192
    two = hex(one + secondhex_int + 2155872256)
    return get_flipped_hex(two[2:], 8).upper()


def get_pkg_name(file):
    if not file:
        print(f'{file} is invalid.')
        return None
    pkg_id = file.split('-')[0]
    for folder in os.listdir('I:/d2_output_3_2_0_1/'):
        if pkg_id.lower() in folder.lower():
            pkg_name = folder
            break
    else:
        if '0100-' in file:
            return 'ui_startup_unp1'
        elif '0101-' in file:
            return 'ui_bootflow_unp1'
        # print(f'Could not find folder for {file}. File is likely not a model or folder does not exist.')
        return None
    return pkg_name


def get_uint32(fb, offset, le=True):
    if le:
        return int.from_bytes(fb[offset:offset+4], byteorder='little')
    return int.from_bytes(fb[offset:offset + 4], byteorder='big')


def get_uint64(fb, offset, le=True):
    if le:
        return int.from_bytes(fb[offset:offset+8], byteorder='little')
    return int.from_bytes(fb[offset:offset + 8], byteorder='big')


def get_uint16(fb, offset, le=True):
    if le:
        return int.from_bytes(fb[offset:offset+2], byteorder='little')
    return int.from_bytes(fb[offset:offset+2], byteorder='big')


def get_int32(fb, offset):
    return int.from_bytes(fb[offset:offset+4], byteorder='little', signed=True)


def get_int16(fb, offset):
    return int.from_bytes(fb[offset:offset+2], byteorder='little', signed=True)


def get_float16(fb, offset):
    flt = int.from_bytes(fb[offset:offset+2], 'little', signed=True)
    flt = flt / (2 ** 15 - 1)
    return flt


def get_float32(fb, offset):
    return struct.unpack('f', fb[offset:offset+4])[0]


def mkdir(path):
    try:
        os.mkdir(path)
    except FileExistsError:
        pass


def get_relative_offset(fb, offset):
    return int.from_bytes(fb[offset:offset + 4], byteorder='little') + offset


def offset_to_string(fb, offset):
    string = ''
    k = 0
    while True:
        char = fb[offset + k]
        if char == 0:
            break
        else:
            string += chr(char)
            k += 1
        if k > 1000:
            raise TypeError('Offset given is not string offset, infinite parse detected')
    return string


def get_flipped_bin(h, length):
    if length % 2 != 0:
        print("Flipped bin length is not even.")
        return None
    return h[:length][::-1]
