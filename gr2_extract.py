import gf
import fbx
import pyfbx


"""
https://github.com/Norbyte/lslib/blob/master/LSLib/Granny/GR2/Reader.cs

We're gonna use this a bit but we can't reproduce fully as its insane
Instead focusing on
- getting out indices
- getting out verts

thats it.
"""


class Header:
    def __init__(self):
        self.magic32 = -1
        self.file_format = -1
        self.total_file_size = -1
        self.crc32 = -1
        self.header_size = -1
        self.section_count = -1
        self.unk1 = -1
        self.unk2 = -1


class Section:
    def __init__(self, parent):
        self.parent = parent
        self.compression_flag = -1
        self.offset = -1
        self.decomp_length = -1
        self.comp_length = -1
        self.alignment = -1
        self.first16bit = -1
        self.first8bit = -1
        self.relocations_offset = -1
        self.relocations_count = -1
        self.marshalling_offset = -1
        self.marshalling_count = -1
        self.marshallings = []
        self.relocations = []
        self.mesh = False

    def read_relocations(self):
        self.parent.fb.seek(self.relocations_offset, 0)
        for i in range(self.relocations_count):
            reloc = RelocationData()
            reloc.offset_in_section = gf.get_uint32(self.parent.fb.read(4), 0)
            reloc.section_ref = gf.get_uint32(self.parent.fb.read(4), 0)
            reloc.section_ref_offset = gf.get_uint32(self.parent.fb.read(4), 0)
            reloc.fixup_address = self.parent.sections[reloc.section_ref].offset + reloc.section_ref_offset
            self.relocations.append(reloc)

    def read_marshalls(self):
        self.parent.fb.seek(self.marshalling_offset, 0)
        for i in range(self.marshalling_count):
            marsh = Marshall()
            marsh.count = gf.get_uint32(self.parent.fb.read(4), 0)
            marsh.offset_in_section = gf.get_uint32(self.parent.fb.read(4), 0)
            marsh.sector_ref = gf.get_uint32(self.parent.fb.read(4), 0)
            marsh.section_ref_offset = gf.get_uint32(self.parent.fb.read(4), 0)
            marsh.offset = self.parent.sections[marsh.sector_ref].offset + marsh.section_ref_offset
            self.marshallings.append(marsh)


class RelocationData:
    def __init__(self):
        self.offset_in_section = -1
        self.section_ref = -1
        self.section_ref_offset = -1
        self.fixup_address = -1


class Marshall:
    def __init__(self):
        self.count = -1
        self.offset_in_section = -1
        self.sector_ref = -1
        self.section_ref_offset = -1
        self.offset = -1
        self.data = b''

class GR2:
    def __init__(self, file_path):
        self.header = Header()
        self.sections = []
        self.mesh_sections = []
        self.mesh_count = -1
        self.fb = open(file_path, "rb")
        self.meshes = []
        self.fbx_model = pyfbx.Model()
        self.name = file_path.split('/')[-1].split('.')[0]

    def get_header(self):
        self.header.magic32 = gf.get_uint32(self.fb.read(4), 0)
        if self.header.magic32 != 1581882341:
            raise TypeError("File provided is not ESO GR2")
        self.fb.seek(0x1C, 1)
        self.header.file_format = gf.get_uint32(self.fb.read(4), 0)
        if self.header.file_format != 7:
            raise TypeError("ESO GR2 given is not file version 7")
        self.header.total_file_size = gf.get_uint32(self.fb.read(4), 0)
        self.header.crc32 = gf.get_uint32(self.fb.read(4), 0)
        self.header.header_size = gf.get_uint32(self.fb.read(4), 0)
        self.header.section_count = gf.get_uint32(self.fb.read(4), 0)
        if self.header.section_count != 8:
            raise TypeError("Section != 8 found!")
        self.header.unk1 = gf.get_uint32(self.fb.read(4), 0)  # 6?
        self.header.unk2 = gf.get_uint32(self.fb.read(4), 0)

    def read_sections(self):
        section_offset = 0x68
        self.fb.seek(section_offset, 0)
        for i in range(self.header.section_count):
            section = Section(self)
            section.compression_flag = gf.get_uint32(self.fb.read(4), 0)
            if section.compression_flag != 0:
                raise Exception("Comp flag != 0")
            section.offset = gf.get_uint32(self.fb.read(4), 0)
            section.decomp_length = gf.get_uint32(self.fb.read(4), 0)
            section.comp_length = gf.get_uint32(self.fb.read(4), 0)
            section.alignment = gf.get_uint32(self.fb.read(4), 0)
            section.first16bit = gf.get_uint32(self.fb.read(4), 0)
            section.first8bit = gf.get_uint32(self.fb.read(4), 0)
            section.relocations_offset = gf.get_uint32(self.fb.read(4), 0)
            section.relocations_count = gf.get_uint32(self.fb.read(4), 0)
            section.marshalling_offset = gf.get_uint32(self.fb.read(4), 0)
            section.marshalling_count = gf.get_uint32(self.fb.read(4), 0)
            if section.relocations_count == 0 and section.marshalling_count != 0:
                section.mesh = True
            self.sections.append(section)

    def extract(self, mesh_only=True):
        self.get_header()
        self.read_sections()
        for section in self.sections:
            section.read_marshalls()
            section.read_relocations()
        if not mesh_only:
            raise Exception("Only mesh supported, do not use False for mesh_only")
        else:
            self.mesh_sections = [x for x in self.sections if x.mesh]
            self.mesh_count = sum([x.marshalling_count for x in self.mesh_sections])
            self.find_and_read_index_header()
            self.get_submeshes()
        self.export()
        a = 0

    def get_submeshes(self):
        # Identify section/marshalls for vertices and faces
        mesh_index = 0
        for i, section in enumerate(self.sections):
            if section.mesh:
                for j in range(section.marshalling_count):
                    m = self.meshes[mesh_index]
                    # TODO: there's an index system somewhere but idk where, its not 1:1
                    m.vertex_offset = section.offset
                    m.vertex_size = section.decomp_length
                    m.index_offset = self.sections[i+1].offset
                    m.index_size = self.sections[i+1].decomp_length
                    # self.meshes[mesh_index].bytes_per_vertex = int(m.vertex_size/m.vertex_count)
                    # self.meshes[mesh_index].bytes_per_index = int(m.index_size / m.index_count)
                    mesh_index += 1

        # debug
        for i, x in enumerate(self.sections[0].relocations):
            self.fb.seek(x.fixup_address, 0)
            if gf.get_uint32(self.fb.read(4), 0) == 10:
                a = 0

        # Process data
        for i, m in enumerate(self.meshes):
            for j, s in enumerate(m.submeshes):
                pass
                # self.faces = [x]

    def export(self):
        for i, m in enumerate(self.meshes):
            for j, s in enumerate(m.submeshes):
                mesh = self.create_mesh(s, f"{i}_{j}")
                node = fbx.FbxNode.Create(self.fbx_model.scene, f"{i}_{j}")
                node.SetNodeAttribute(mesh)
                node.LclScaling.Set(fbx.FbxDouble3(100, 100, 100))
                self.fbx_model.scene.GetRootNode().AddChild(node)
        self.fbx_model.export(save_path=f'models/{self.name}.fbx', ascii_format=False)
        print(f'Written models/{self.name}.fbx')

    def create_mesh(self, submesh, name):
        mesh = fbx.FbxMesh.Create(self.fbx_model.scene, name)
        controlpoints = [fbx.FbxVector4(x[0], x[1], x[2]) for x in submesh.vert_pos]
        for i, p in enumerate(controlpoints):
            mesh.SetControlPointAt(p, i)
        for face in submesh.faces:
            mesh.BeginPolygon()
            mesh.AddPolygon(face[0])
            mesh.AddPolygon(face[1])
            mesh.AddPolygon(face[2])
            mesh.EndPolygon()
        return mesh

    def find_and_read_index_header(self):
        reloc_index = 0
        relocations = self.sections[0].relocations
        for i, x in enumerate(relocations):
            self.fb.seek(x.fixup_address, 0)
            if gf.get_uint32(self.fb.read(4), 0) == 10:
                reloc_index = i
                break

        for i in range(self.mesh_count):
            mesh = Mesh()
            reloc_index += 1  # Type 10
            # Vertex offset
            mesh.vertex_offset = relocations[reloc_index].fixup_address
            mesh.vertex_section = relocations[reloc_index].section_ref
            reloc_index += 1
            # Vertex count
            self.fb.seek(relocations[reloc_index].fixup_address+8, 0)
            mesh.vertex_count = gf.get_uint32(self.fb.read(4), 0)
            reloc_index += 1
            self.meshes.append(mesh)
        reloc_index += 1  # Empty
        for mesh in self.meshes:
            # Parts definition
            part_def_offset = relocations[reloc_index].fixup_address
            reloc_index += 1
            # Index offset
            mesh.index_offset = relocations[reloc_index].fixup_address
            mesh.index_section = relocations[reloc_index].section_ref
            reloc_index += 1
            # Index count and part count
            self.fb.seek(relocations[reloc_index].fixup_address, 0)
            mesh.submesh_count = gf.get_uint32(self.fb.read(4), 0)
            self.fb.seek(8, 1)
            mesh.index_count = gf.get_uint32(self.fb.read(4), 0)
            reloc_index += 1
            # Processing data
            self.fb.seek(part_def_offset, 0)
            for j in range(mesh.submesh_count):
                submesh = Submesh()
                submesh.material_index = gf.get_uint32(self.fb.read(4), 0)
                submesh.index_offset = mesh.index_offset + gf.get_uint32(self.fb.read(4), 0)
                submesh.index_count = gf.get_uint32(self.fb.read(4), 0)
                mesh.submeshes.append(submesh)
        reloc_index += 1  # Empty

        # Getting strides
        counts = {}
        for mesh in self.meshes:
            if mesh.index_section not in counts.keys():
                counts[mesh.index_section] = 0
            counts[mesh.index_section] += mesh.index_count
            if mesh.vertex_section not in counts.keys():
                counts[mesh.vertex_section] = 0
            counts[mesh.vertex_section] += mesh.vertex_count
        section_bytes = {}
        for section, count in counts.items():
            section_bytes[section] = int(self.sections[section].decomp_length/count)
        for mesh in self.meshes:
            mesh.index_stride = section_bytes[mesh.index_section]
            mesh.vertex_stride = section_bytes[mesh.vertex_section]
        a = 0


class Mesh:
    def __init__(self):
        self.submesh_count = -1
        self.submeshes = []
        self.index_count = -1
        self.vertex_count = -1
        self.index_offset = -1
        self.vertex_offset = -1
        self.index_size = -1
        self.vertex_size = -1
        self.vertex_section = -1
        self.index_section = -1
        self.vertex_stride = -1
        self.index_stride = -1


class Submesh:
    def __init__(self):
        self.index_count = -1
        self.index_offset = -1
        self.material_index = -1
        self.vert_pos = []
        self.faces = []


def extract_gr2(path):
    gr2 = GR2(path)
    gr2.extract(mesh_only=True)
    a = 0


if __name__ == "__main__":
    base_path = "P:/ESO/Tools/Extractor/eso/0111"
    file_name = "00158583.gr2"
    extract_gr2(f"{base_path}/{file_name}")

    base_path = "P:/ESO/Tools/Extractor/eso/0110"
    file_name = "00153738.gr2"
    extract_gr2(f"{base_path}/{file_name}")