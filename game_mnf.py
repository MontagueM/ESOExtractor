import gf
import zlib


def read_header(fb):
    mnf_magic = fb.read(4)
    if mnf_magic != b"\x4D\x45\x53\x32":
        TypeError("Incorrect data file given")
    version = fb.read(2)
    if version != 3:
        TypeError("Incorrect version given")
    data_file_count = gf.get_uint16(fb.read(2), 0)
    fb.seek(data_file_count*2, 1)
    q = fb.tell()
    unk1 = fb.read(4)
    data_length = gf.get_uint32(fb.read(4), 0)
    block_type = gf.get_uint32(fb.read(2), 0, le=False)
    if block_type == 0:
        read_block_0(fb)
        block_type = gf.get_uint32(fb.read(2), 0, le=False)

    if block_type == 3:
        read_block_3(fb)
    else:
        raise Exception("Incorrect block type read")



# block 0 does not get read anywhere, so can be ignored
def read_block_0(fb):
    print("Block 0 found, skipping...")
    unk1 = fb.read(2)
    data_count = 2
    # NOT ZLIB COMPRESSION
    # SOMETHING ELSE
    for i in range(data_count):
        comp_size = gf.get_uint32(fb.read(4), 0, le=False)
        fb.seek(comp_size, 1)


def read_block_3(fb):
    unk1 = gf.get_uint32(fb.read(4), 0)
    record1a_count = gf.get_uint32(fb.read(4), 0, le=False)
    record1b_count = gf.get_uint32(fb.read(4), 0, le=False)
    record23_count = gf.get_uint32(fb.read(4), 0, le=False)
    data_count = 3
    q = fb.tell()
    for i in range(data_count):
        decomp_size = gf.get_uint32(fb.read(4), 0, le=False)
        comp_size = gf.get_uint32(fb.read(4), 0, le=False)
        comp_data = fb.read(comp_size)
        decom_data = zlib.decompress(comp_data)
        with open(f"test_out/{i}.bin", "wb") as f:
            f.write(decom_data)


def main():
    path1 = "F:/Other Games/Zenimax Online/The Elder Scrolls Online/game/client/game.mnf"
    path2 = "F:/Other Games/Zenimax Online/The Elder Scrolls Online/depot/eso.mnf"
    fb = open(path2, "rb")
    fb.seek(0, 2)
    file_size = fb.tell()
    fb.seek(0, 0)
    read_header(fb)


main()
