import gf
import zlib
from ctypes import cdll, c_char_p, create_string_buffer
import os
import pkg_db


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
        with open(f"eso/mnf_{i}.bin", "wb") as f:
            f.write(decomp_data)
    return block3


def read_block_3_f(f, offset):
    block3 = MnfBlock()
    unk1 = gf.get_uint32(f, offset)
    block3.record1a_count = gf.get_uint32(f, offset+4)
    block3.record1b_count = gf.get_uint32(f, offset+8)
    block3.record23_count = gf.get_uint32(f, offset+0xC)
    if block3.record23_count == 0:
        return None, offset
    data_count = 3
    for i in range(data_count):
        decomp_size = gf.get_uint32(f, offset+0x10)
        comp_size = gf.get_uint32(f, offset+0x14)
        decomp_data = zlib.decompress(f[offset+0x18:offset+0x18+comp_size])
        block3.data.append(decomp_data)
        offset += comp_size + 8
        with open(f"eso/zosft_{i}_{offset}.bin", "wb") as qq:
            qq.write(decomp_data)
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
        self.FileID = None


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
            entry.FileID = gf.get_uint64(block3.data[1], offset2)
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
    pkg_db.save_mnf_table(m_FileTable, "eso.mnf" in path)
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
    if zosft_data[:5] != b"\x5A\x4F\x53\x46\x54":
        raise Exception("ZOSFT file is invalid")
    # Reading header
    record_count = gf.get_uint32(zosft_data, 0xF)
    # Reading block data
    blocks = []
    offset = 0x13
    for i in range(3):
        block_type = gf.get_uint16(zosft_data, offset)
        block, offset = read_block_3_f(zosft_data, offset+2)
        if block:
            blocks.append(block)
        else:
            offset += 0x10
    # Reading file data
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
    pkg_db.save_zosft_table(filetable, "eso.mnf" in path)
    return file_index_map


def read_data_file(entry: TableEntry):
    f = open(path.split('.')[0] + f"{gf.fill_hex_with_zeros(str(entry.ArchiveIndex), 4)}.dat", "rb")
    file_size = f.seek(0, 2)
    if entry.Offset + entry.CompressedSize > file_size:
        return None
    f.seek(entry.Offset, 0)
    raw_data = f.read(entry.CompressedSize)
    decomp_data = None
    if entry.CompressType == 0:
        if raw_data[:2] == b"\x8C\x06" or raw_data[:2] == b"\xCC\x0A" or raw_data[:2] == b"\xCC\x06" or raw_data[:2] == b"\x8C\x0A":
            decompressor = OodleDecompressor('I:/oo2core_8_win64.dll')
            decomp_data = decompressor.decompress(raw_data, entry.Size)
        elif raw_data[:2] == b"\x78\x9C":
            decomp_data = zlib.decompress(raw_data)
        else:
            decomp_data = raw_data
    elif entry.CompressType == 1:
        decomp_data = zlib.decompress(raw_data)
    elif entry.CompressType == 2:
        print("Implement snappy compress")
    else:
        print("Unk compression")
    return decomp_data


# Only for game data, uses a different format
def read_game_data_file(entry: TableEntry):
    f = open(path.split('.')[0] + f"{gf.fill_hex_with_zeros(str(entry.ArchiveIndex), 4)}.dat", "rb")
    t = f.seek(entry.Offset, 0)

    comp_data = f.read(entry.CompressedSize)
    if comp_data[:2] != b"\x8C\x06" and comp_data[:2] != b"\xCC\x0A" and comp_data[:2] != b"\xCC\x06" and comp_data[:2] != b"\x8C\x0A":
        #trying zlib
        if comp_data[:2] == b"\x78\x9C":
            decomp_data = zlib.decompress(comp_data)
        else:
            raise Exception("game fail wrong head")
    else:
        decompressor = OodleDecompressor('I:/oo2core_8_win64.dll')
        decomp_data = decompressor.decompress(comp_data, entry.Size)
    if decomp_data[:5] == b"\x5A\x4F\x53\x46\x54":
        return decomp_data, f
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
            if e == None:
                a = 0
        else:
            continue
        e.UserData += 1
        x.ZosftEntry = e


def extract_files(file_table):
    q = "game"
    if "eso.mnf" in path:
        q = "eso"
    ignore1 = 0
    ignore2 = 0
    for i, x in enumerate(file_table):
        # if x.ArchiveIndex > 5:
        #     continue
        if i % 100 == 0:
            print(f"Subfile {i}/{len(file_table)}")
        # Reading data
        # if not x.ZosftEntry:
        #     ignore1 += 1
        #     continue
        if q == "game":
            data, _ = read_game_data_file(x)
        else:
            data = read_data_file(x)
        if not data:
            ignore2 += 1
            continue
        # Saving file
        if not x.ZosftEntry:
            x.ZosftEntry = FileTableEntry()
            extension = guess_extension(data)
            x.ZosftEntry.FileName = f"{gf.fill_hex_with_zeros(str(x.ArchiveIndex), 4)}/{gf.fill_hex_with_zeros(str(x.Index), 8)}.{extension}"
            os.makedirs(f"{q}/{gf.fill_hex_with_zeros(str(x.ArchiveIndex), 4)}/", exist_ok=True)
        else:
            savename = x.ZosftEntry.FileName.split('/')[-1]
            savedir = x.ZosftEntry.FileName[:-len(savename)]
            os.makedirs(f"{q}/" + savedir, exist_ok=True)
            if x.ZosftEntry.FileName == "":
                extension = guess_extension(data)
                x.ZosftEntry.FileName = f"{gf.fill_hex_with_zeros(str(x.ArchiveIndex), 4)}/{gf.fill_hex_with_zeros(str(x.Index), 8)}.{extension}"
                os.makedirs(f"{q}/{gf.fill_hex_with_zeros(str(x.ArchiveIndex), 4)}/", exist_ok=True)
        with open(f"{q}/" + x.ZosftEntry.FileName, "wb") as f:
            f.write(data)
        a = 0
    print(ignore1, ignore2)


def guess_extension(data):
    if data[:3] == b"DDS":
        return "dds"
    elif data[:8] == b"\x00\x01\x00\x00\x00\x0E\x00\x80" or data[:4] == b"OTTO" or data[11:11+5] == b"POS/2":
        return "ttf"
    elif data[:7] == b"\x1E\x0D\x0B\xCD\xCE\xFA\x11":
        return "hk"
    elif data[:4] == b"\x29\xDE\x6C\xC0" or data[:4] == b"\xE5\x9B\x49\x5E" or data[:4] == b"\x29\x75\x31\x82"\
    or data[:4] == b"\x0E\x11\x95\xB5" or data[:4] == b"\x0E\x74\xA2\x0A" or data[:4] == b"\xE5\x2F\x4A\xE1"\
    or data[:4] == b"\x31\x95\xD4\xE3" or data[:4] == b"\x31\xC2\x4E\x7C":
        return "gr2"
    elif data[:4] == b"\x1E\x0D\xB0\xCA":
        return "hkx"
    elif data[:4] == b"\xFA\xFA\xEB\xEB":
        return "EsoFileData"
    elif data[:4] == b"\xFB\xFB\xEC\xEC":
        return "EsoIdData"
    elif data[:4] == b"\x00\x00\x00\x02":
        return "EsoIdData"
    elif data[:3] == b"\xEF\xBB\xBF":
        return "txt"
    elif data[:3] == b"xV4":
        return "xv4"
    elif data[:5] == b"__ffx":
        return "ffx"
    elif data[:4] == b"RIFF":
        return "riff"
    elif data[:2] == b"; " or data[len(data)-4:len(data)] == b".lua":
        return "txt"
    elif data[0] == b"#" or data[:2] == b"//" or data[:3] == b"\r\n#" or data[:2] == b"/*":
        return "fx"
    elif data[:2] == b"--" or data[:5] == b"local" or data[:7] == b"function":
        return "lua"
    elif data[0] == b"<":
        return "xml"
    elif data[:5] == b"ZOSFT":
        return "zosft"
    elif data[len(data)-5:len(data)-2] == b"end" or data[len(data)-3:len(data)] == b"end" or\
        data[len(data)-7:len(data)-4] == b"end" or data[len(data)-2:len(data)] == b"\r":
        return "lua"
    elif data[:4] == b"BKHD":
        return "bnk"
    else:
        return "bin"

bpath = "F:/Other Games/Zenimax Online/The Elder Scrolls Online/"
path1 = "/game/client/game.mnf"
path2 = "/depot/eso.mnf"
path = bpath + path1
def main():
    fb = open(path, "rb")
    fb.seek(0, 2)
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
