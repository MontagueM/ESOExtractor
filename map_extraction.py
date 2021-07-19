import gf
import pkg_db
import gr2_extract
import pyfbx
import fbx
import numpy as np


class Model:
    def __init__(self):
        self.euler_rot = []
        self.position = []
        self.ref = ""
        self.path = ""


def extract_map(file_path):
    fb = open(file_path, "rb").read()
    count = gf.get_uint32(fb, 0x4)

    # Reading data
    models = []
    for i in range(0x8, 0x8+count*0x60, 0x60):
        model = Model()
        model.euler_rot = [gf.get_float32(fb, i+0x10+j*4) for j in range(3)]
        model.position = [gf.get_float32(fb, i+0x1C+j*4) for j in range(3)]
        model.ref = fb[i+0x44:i+0x44+8].hex().upper()
        if model.ref in fileid_path_map.keys():
            model.path = fileid_path_map[model.ref] + ".gr2"
        else:
            print("Model missing...")
        models.append(model)

    # Extracting models and appending to a single thing like my static map stuff
    fbx_model = pyfbx.Model()
    for i, m in enumerate(models):
        print(f"{i+1}/{len(models)}   {round(i*100/len(models), 1)}%")
        # Extract as usual
        if not m.path:
            continue
        gr2 = gr2_extract.GR2(m.path, override_model=fbx_model)
        fbxmeshes = gr2.extract(mesh_only=True, save=False)
        euler_rot_deg = [x*180/np.pi for x in m.euler_rot]
        translation = m.position
        if not fbxmeshes:
            continue
        for fbxmesh in fbxmeshes:
            node = fbx.FbxNode.Create(fbx_model.scene, m.path.split('/')[-1])
            node.SetNodeAttribute(fbxmesh)
            node.SetGeometricRotation(fbx.FbxNode.eSourcePivot, fbx.FbxVector4(euler_rot_deg[0], euler_rot_deg[1], euler_rot_deg[2]))
            node.SetGeometricTranslation(fbx.FbxNode.eSourcePivot,
                                              fbx.FbxVector4(translation[0], translation[1], translation[2]))
            node.SetGeometricScaling(fbx.FbxNode.eSourcePivot,
                                          fbx.FbxVector4(1, 1, 1))
            node.LclScaling.Set(fbx.FbxDouble3(100, 100, 100))
            fbx_model.scene.GetRootNode().AddChild(node)
    fbx_model.export(save_path=f"maps/{file_path.split('/')[-1]}.fbx", ascii_format=False)
    print(f"Written map out to maps/{file_path.split('/')[-1]}.fbx")
    a = 0


if __name__ == "__main__":
    base_path = "P:/ESO/Tools/Extractor/eso"
    pkg_db.start_mnf_connection()
    fileid_path_map = {x[0]: f"{base_path}/{gf.fill_hex_with_zeros(str(x[1]), 4)}/{gf.fill_hex_with_zeros(str(x[2]), 8)}" for x in
                     pkg_db.get_entries_from_mnf('FileID, ArchiveIndex, Indexx')}

    extract_map(base_path + "/0076/00754523.bin")