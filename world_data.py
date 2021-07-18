import os

magic = b"\x0C\x00\xEF\xBE"
direc = "P:/ESO/Tools/Extractor/eso/"

dist = {}

for folder in os.listdir(direc):
    print(folder)
    if "." in folder:# or "10" not in folder:
        continue
    for file in os.listdir(direc + folder):
        if '.bin' not in file:
            continue
        fb = open(f'{direc}/{folder}/{file}', 'rb')
        fb_size = fb.seek(0, 2)
        fb.seek(0, 0)
        if fb.read(4) != magic:
            continue
        if folder not in dist.keys():
            dist[folder] = []
        dist[folder].append([file, fb_size])

a = 0
