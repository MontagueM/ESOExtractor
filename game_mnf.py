import gf
import zlib
from ctypes import cdll, c_char_p, create_string_buffer
import os


class OodleDecompressor:
    """
    Oodle decompression implementation.
    Requires Windows and the external Oodle library.
    """

    def __init__(self, library_path: str) -> None:
        """
        Initialize instance and try to load the library.
        """
        if not os.path.exists(library_path):
            raise Exception("Could not open Oodle DLL, make sure it is configured correctly.")

        try:
            self.handle = cdll.LoadLibrary(library_path)
        except OSError as e:
            raise Exception(
                "Could not load Oodle DLL, requires Windows and 64bit python to run."
            ) from e

    def decompress(self, payload: bytes, output_size: int) -> bytes:
        """
        Decompress the payload using the given size.
        """
        output = create_string_buffer(output_size)
        self.handle.OodleLZ_Decompress(
            c_char_p(payload), len(payload), output, output_size,
            0, 0, 0, None, None, None, None, None, None, 3)
        return output.raw


class MnfBlock:
    def __init__(self):
        self.type = None
        self.data = []
        self.record1a_count = None
        self.record1b_count = None
        self.record23_count = None


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
    block3 = None
    if block_type == 0:
        read_block_0(fb)
        block_type = gf.get_uint32(fb.read(2), 0, le=False)

    if block_type == 3:
        block3 = read_block_3(fb)
    else:
        raise Exception("Incorrect block type read")
    return block3


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
    block3 = MnfBlock()
    unk1 = gf.get_uint32(fb.read(4), 0)
    block3.record1a_count = gf.get_uint32(fb.read(4), 0, le=False)
    block3.record1b_count = gf.get_uint32(fb.read(4), 0, le=False)
    block3.record23_count = gf.get_uint32(fb.read(4), 0, le=False)
    data_count = 3
    q = fb.tell()
    for i in range(data_count):
        decomp_size = gf.get_uint32(fb.read(4), 0, le=False)
        comp_size = gf.get_uint32(fb.read(4), 0, le=False)
        comp_data = fb.read(comp_size)
        decomp_data = zlib.decompress(comp_data)
        block3.data.append(decomp_data)
        # with open(f"test_out/{i}.bin", "wb") as f:
        #     f.write(decomp_data)
    return block3


def read_block_3_f(f, offset):
    block3 = MnfBlock()
    unk1 = gf.get_uint32(f, offset)
    block3.record1a_count = gf.get_uint32(f, offset+4)
    block3.record1b_count = gf.get_uint32(f, offset+8)
    block3.record23_count = gf.get_uint32(f, offset+0xC)
    data_count = 3
    for i in range(data_count):
        decomp_size = gf.get_uint32(f, offset+0x10)
        comp_size = gf.get_uint32(f, offset+0x14)
        decomp_data = zlib.decompress(f[offset+0x18:offset+0x18+comp_size])
        block3.data.append(decomp_data)
        offset += comp_size + 8
    return block3, offset+0x10


class TableEntry:
    def __init__(self):
        self.Index = None
        self.ID1 = None
        self.FileIndex = None
        self.Unk1 = None
        self.Size = None
        self.CompressedSize = None
        self.Hash = None
        self.Offset = None
        self.CompressType = None
        self.ArchiveIndex = None
        self.Unk2 = None
        self.ZosftEntry = None


def parse_table(block3):
    m_FileTable = []
    MNF_BLOCK1_RECORDSIZE = 4
    MNF_BLOCK2_RECORDSIZE = 8
    MNF_BLOCK3_RECORDSIZE = 20
    offset1 = 0
    offset2 = 0
    offset3 = 0
    for i in range(block3.record23_count):
        entry = TableEntry()
        entry.Index = i
        if offset1 + MNF_BLOCK1_RECORDSIZE <= len(block3.data[0]):
            while offset1 + MNF_BLOCK1_RECORDSIZE <= len(block3.data[0]) and block3.data[0][offset1+3] != 0x80:
                offset1 += MNF_BLOCK1_RECORDSIZE
            entry.ID1 = gf.get_uint32(block3.data[0], offset1)
            offset1 += MNF_BLOCK1_RECORDSIZE

        if offset2 + MNF_BLOCK2_RECORDSIZE <= len(block3.data[1]):
            entry.FileIndex = gf.get_uint32(block3.data[1], offset2)
            entry.Unk1 = gf.get_uint32(block3.data[1], offset2+4)
            offset2 += MNF_BLOCK2_RECORDSIZE

        if offset3 + MNF_BLOCK3_RECORDSIZE <= len(block3.data[2]):
            entry.Size = gf.get_uint32(block3.data[2], offset3)
            entry.CompressedSize = gf.get_uint32(block3.data[2], offset3+4)
            entry.Hash = gf.get_uint32(block3.data[2], offset3+8)
            entry.Offset = gf.get_uint32(block3.data[2], offset3+12)
            entry.CompressType = block3.data[2][offset3+16]
            entry.ArchiveIndex = block3.data[2][offset3+17]
            entry.Unk2 = gf.get_uint16(block3.data[2], offset3+18)
            offset3 += MNF_BLOCK3_RECORDSIZE

            # Header version 3
            tmp = entry.CompressType
            entry.CompressType = entry.ArchiveIndex
            entry.ArchiveIndex = tmp

        m_FileTable.append(entry)
    return m_FileTable


def create_file_maps(file_table):
    file_hash_map = {}
    file_index_map = {}
    file_internal_index_map = {}
    for x in file_table:
        file_hash_map[x.Hash] = x
        file_index_map[x.FileIndex] = x
        file_internal_index_map[x.Index] = x
    return file_hash_map, file_index_map, file_internal_index_map


def find_zosft_entry(path, file_index_map):
    if "eso.mnf" in path:
        if 0x00FFFFFF in file_index_map.keys():
            return file_index_map[0x00FFFFFF]
        else:
            raise Exception("Support the other ZOSFT for eso.mnf")
    elif "game.mnf" in path:
        if 0 in file_index_map.keys():
            return file_index_map[0]
        else:
            raise Exception("Support the other ZOSFT for game.mnf")
    return ""


class File:
    def __init__(self, entry):
        self.entry = entry
        self.data = None


class FileTableEntry:
    def __init__(self):
        self.Index = None
        self.Index11 = None
        self.Index13 = None
        self.Index21 = None
        self.FileIndex = None
        self.FilenameOffset = None
        self.FileID = None
        self.FileName = None
        self.UserData = None


def load_zosft_file(entry):
    zosft_data, f = read_game_data_file(entry)
    # Reading header
    record_count = gf.get_uint32(zosft_data, 0xF)
    # Reading block data
    blocks = []
    offset = 0x13
    for i in range(2):
        block_type = gf.get_uint16(zosft_data, offset)
        block, offset = read_block_3_f(zosft_data, offset+2)
        blocks.append(block)
    # Reading file data
    offset += 0x12
    file_names_length = gf.get_uint32(zosft_data, offset)
    offset += 4
    filenames = {}
    string = ''
    i = 0
    start_offset = 0
    while i < file_names_length:
        char = zosft_data[offset+i]
        if char == 0:
            i += 1
            filenames[start_offset] = string
            string = ''
            start_offset = i
        else:
            string += chr(char)
            i += 1

    # Creating file table
    offset11 = 0
    offset13 = 0
    offset21 = 0
    offset23 = 0
    MNF_BLOCK1_RECORDSIZE = 4
    filetable = []
    for i in range(record_count):
        ft_entry = FileTableEntry()
        ft_entry.UserData = 0
        ft_entry.Index = i
        if offset11 < len(blocks[0].data[0]):
            ft_entry.Index11 = gf.get_uint32(blocks[0].data[0], offset11)
            while offset11 + MNF_BLOCK1_RECORDSIZE <= len(blocks[0].data[0]) and blocks[0].data[0][offset11 + 3] != 0x80:
                offset11 += MNF_BLOCK1_RECORDSIZE
            ft_entry.Index11 = gf.get_uint32(blocks[0].data[0], offset11)
            offset11 += MNF_BLOCK1_RECORDSIZE

        if offset13 < len(blocks[0].data[2]):
            ft_entry.Index13 = gf.get_uint32(blocks[0].data[2], offset13)
            offset13 += MNF_BLOCK1_RECORDSIZE

        if offset21 < len(blocks[1].data[0]):
            ft_entry.Index21 = gf.get_uint32(blocks[1].data[0], offset11)
            while offset21 + MNF_BLOCK1_RECORDSIZE <= len(blocks[1].data[0]) and blocks[1].data[0][offset11 + 3] != 0x80:
                offset21 += MNF_BLOCK1_RECORDSIZE
            ft_entry.Index21 = gf.get_uint32(blocks[1].data[0], offset11)
            offset21 += MNF_BLOCK1_RECORDSIZE

        if offset23 < len(blocks[1].data[2]):
            ft_entry.FileIndex = gf.get_uint32(blocks[1].data[2], offset23)
            offset23 += MNF_BLOCK1_RECORDSIZE

            ft_entry.FilenameOffset = gf.get_uint32(blocks[1].data[2], offset23)
            offset23 += MNF_BLOCK1_RECORDSIZE

            ft_entry.FileID = gf.get_uint32(blocks[1].data[2], offset23)
            offset23 += MNF_BLOCK1_RECORDSIZE*2

            if ft_entry.FilenameOffset in filenames.keys():
                ft_entry.FileName = filenames[ft_entry.FilenameOffset]
            else:
                ft_entry.FileName = ""
        filetable.append(ft_entry)

    file_index_map = {}
    for x in filetable:
        file_index_map[x.FileIndex] = x
    a = 0
    return file_index_map


def read_game_data_file(entry):
    f = open(path.split('.')[0] + f"{gf.fill_hex_with_zeros(str(entry.ArchiveIndex), 4)}.dat", "rb")
    f.seek(entry.Offset, 0)
    comp_data = f.read(entry.CompressedSize)
    if comp_data[:2] != b"\x8C\x06" and comp_data[:2] != b"\xCC\x0A" and comp_data[:2] != b"\xCC\x06" and comp_data[:2] != b"\x8C\x0A":
        #trying zlib
        if comp_data[:2] == b"\x78\x9C":
            decomp_data = zlib.decompress(comp_data)
        else:
            raise Exception("zosft fail wrong head")
    else:
        decompressor = OodleDecompressor('I:/oo2core_8_win64.dll')
        decomp_data = decompressor.decompress(comp_data, entry.Size)
    header_offset1 = gf.get_uint16(decomp_data, 6, le=False) + 8
    # header_offset1 += 3
    header_offset2 = gf.get_uint32(decomp_data, header_offset1, le=False) + 4 + header_offset1
    f.seek(entry.Offset + header_offset2 + 11, 0)
    return decomp_data[header_offset2:], f


def link_to_zosft(file_table, zosft_file_index_map):
    for x in file_table:
        if "eso.mnf" in path and x.Unk1 != 0:
            continue
        if x.FileIndex in zosft_file_index_map.keys():
            e = zosft_file_index_map[x.FileIndex]
        else:
            continue
        e.UserData += 1
        x.ZosftEntry = e


def extract_files(file_table):
    for i, x in enumerate(file_table):
        if i % 100 == 0:
            print(f"Subfile {i}/{len(file_table)}")
        # Reading data
        data, _ = read_game_data_file(x)
        # Saving file
        if not x.ZosftEntry:
            continue
        savename = x.ZosftEntry.FileName.split('/')[-1]
        savedir = x.ZosftEntry.FileName[:-len(savename)]
        os.makedirs("test_out/" + savedir, exist_ok=True)
        with open("test_out/" + x.ZosftEntry.FileName, "wb") as f:
            f.write(data)
        a = 0

bpath = "F:/Other Games/Zenimax Online/The Elder Scrolls Online/"
path1 = "/game/client/game.mnf"
path2 = "/depot/eso.mnf"
path = bpath + path1
def main():
    fb = open(path, "rb")
    fb.seek(0, 2)
    file_size = fb.tell()
    fb.seek(0, 0)
    block3 = read_header(fb)
    if not block3:
        raise Exception("No block 3 found")
    file_table = parse_table(block3)
    file_hash_map, file_index_map, file_internal_index_map = create_file_maps(file_table)
    print("Loaded MNF files and table")
    print("Getting ZOSFT entry from MNF")
    zosft_entry = find_zosft_entry(path, file_index_map)
    zosft_file_index_map = load_zosft_file(zosft_entry)
    link_to_zosft(file_table, zosft_file_index_map)
    ## Duplicate protection?
    a = 0
    extract_files(file_table)
main()
