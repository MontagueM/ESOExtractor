import sqlite3 as sq
import gf


def drop_table(pkg_str_to_drop):
    global c
    c.execute(f'DROP TABLE IF EXISTS {pkg_str_to_drop}')


def save_mnf_table(file_table, b_is_eso):
    con = sq.connect(f'MNF.db')
    c = con.cursor()
    if b_is_eso:
        name = "eso"
    else:
        name = "game"
    c.execute(f'DROP TABLE IF EXISTS {name}')
    entries = [(x.Index, (gf.get_flipped_hex(gf.fill_hex_with_zeros(hex(x.FileID)[2:], 16), 16).upper()), x.FileIndex, x.ID1, x.Unk1, x.Size, x.CompressedSize, x.Hash, x.Offset, x.CompressType, x.ArchiveIndex, x.Unk2) for x in file_table]
    c.execute(f'CREATE TABLE IF NOT EXISTS {name} ( Indexx INTEGER, FileID TEXT, FileIndex INTEGER, ID1 INTEGER, Unk1 INTEGER, Size INTEGER, CompressedSize INTEGER, Hash INTEGER, Offset INTEGER, CompressType INTEGER, ArchiveIndex INTEGER, Unk2 INTEGER)')
    c.executemany(f'INSERT INTO {name} (Indexx, FileID, FileIndex, ID1, Unk1, Size, CompressedSize, Hash, Offset, CompressType, ArchiveIndex, Unk2) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
              entries)
    con.commit()
    print(f"Added {len(entries)} entries to MNF db")


def save_zosft_table(file_table, b_is_eso):
    con = sq.connect(f'ZOSFT.db')
    c = con.cursor()
    if b_is_eso:
        name = "eso"
    else:
        name = "game"
    c.execute(f'DROP TABLE IF EXISTS {name}')
    entries = [(x.FileIndex, x.FileName, x.FilenameOffset, x.FileID, x.UserData, x.Index, x.Index11, x.Index13, x.Index21) for x in file_table]
    c.execute(f'CREATE TABLE IF NOT EXISTS {name} (FileIndex INTEGER, FileName TEXT, FilenameOffset INTEGER, FileID INTEGER, UserData INTEGER, Indexx INTEGER, Index11 INTEGER, Index13 INTEGER, Index21 INTEGER)')
    c.executemany(f'INSERT INTO {name} (FileIndex, FileName, FilenameOffset, FileID, UserData, Indexx, Index11, Index13, Index21) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?);',
              entries)
    con.commit()
    print(f"Added {len(entries)} entries to ZOSFT db")
