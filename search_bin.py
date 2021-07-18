import os
import binascii
direc = "P:/ESO/Tools/Extractor/eso/"
a = "04000200211D0040"
if ' ' in a:
    a = a.replace(' ', '')
print(a)
a = binascii.unhexlify(a)
for folder in os.listdir(direc):
    print(folder)
    if "." in folder:# or "10" not in folder:
        continue
    for file in os.listdir(direc + folder):
        if '.bin' not in file:
            continue
        fb = open(f'{direc}/{folder}/{file}', 'rb').read()
        if a in fb:
            print(f"Found  in {file}\n")