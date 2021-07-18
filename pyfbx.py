import fbx
import sys

class Model:
    def __init__(self):
        self.manager = fbx.FbxManager.Create()
        if not self.manager:
            sys.exit(0)

        self.ios = fbx.FbxIOSettings.Create(self.manager, fbx.IOSROOT)
        self.exporter = fbx.FbxExporter.Create(self.manager, '')
        self.scene = fbx.FbxScene.Create(self.manager, '')

    def add(self, submesh, direc, b_shaders, b_unreal):
        node, mesh = self.create_mesh(submesh)

        if not mesh.GetLayer(0):
            mesh.CreateLayer()
        layer = mesh.GetLayer(0)

        if submesh.material:
            if submesh.diffuse:
                self.apply_diffuse(submesh.diffuse, f'{direc}/textures/{submesh.diffuse}.dds', node)
                node.SetShadingMode(fbx.FbxNode.eTextureShading)
            elif b_shaders:
                self.apply_shader(submesh, node)

        if submesh.vert_uv:
            self.create_uv(mesh, submesh, layer)
        if submesh.vert_col:
            self.add_vert_colours(mesh, submesh, layer)

        if not b_unreal:
            node.LclRotation.Set(fbx.FbxDouble3(-90, 180, 0))

        self.scene.GetRootNode().AddChild(node)

    def export(self, save_path=None, ascii_format=False):
        """Export the scene to an fbx file."""

        if not self.manager.GetIOSettings():
            self.ios = fbx.FbxIOSettings.Create(self.manager, fbx.IOSROOT)
            self.manager.SetIOSettings(self.ios)

        self.manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_MATERIAL, True)
        self.manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_TEXTURE, True)
        self.manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_EMBEDDED, False)
        self.manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_SHAPE, True)
        self.manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_GOBO, False)
        self.manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_ANIMATION, True)
        self.manager.GetIOSettings().SetBoolProp(fbx.EXP_FBX_GLOBAL_SETTINGS, True)
        if ascii_format:
            b_ascii = 1
        else:
            b_ascii = -1
        self.exporter.Initialize(save_path, b_ascii, self.manager.GetIOSettings())
        self.exporter.Export(self.scene)
        self.exporter.Destroy()

    def create_mesh(self, submesh):
        mesh = fbx.FbxMesh.Create(self.scene, submesh.name)
        controlpoints = [fbx.FbxVector4(-x[0]*100, x[2]*100, x[1]*100) for x in submesh.vert_pos]
        for i, p in enumerate(controlpoints):
            mesh.SetControlPointAt(p, i)
        for face in submesh.faces:
            mesh.BeginPolygon()
            mesh.AddPolygon(face[0])
            mesh.AddPolygon(face[1])
            mesh.AddPolygon(face[2])
            mesh.EndPolygon()
        node = fbx.FbxNode.Create(self.scene, submesh.name)
        node.SetNodeAttribute(mesh)
        return node, mesh

    def create_uv(self, mesh, submesh, layer):
        uvDiffuseLayerElement = fbx.FbxLayerElementUV.Create(mesh, f'diffuseUV {submesh.name}')
        uvDiffuseLayerElement.SetMappingMode(fbx.FbxLayerElement.eByControlPoint)
        uvDiffuseLayerElement.SetReferenceMode(fbx.FbxLayerElement.eDirect)
        for i, p in enumerate(submesh.vert_uv):
            uvDiffuseLayerElement.GetDirectArray().Add(fbx.FbxVector2(p[0], p[1]))
        layer.SetUVs(uvDiffuseLayerElement, fbx.FbxLayerElement.eTextureDiffuse)

    def add_vert_colours(self, mesh, submesh, layer):
        vertColourElement = fbx.FbxLayerElementVertexColor.Create(mesh, f'colour')
        vertColourElement.SetMappingMode(fbx.FbxLayerElement.eByControlPoint)
        vertColourElement.SetReferenceMode(fbx.FbxLayerElement.eDirect)
        for i, p in enumerate(submesh.vertex_colour):
            vertColourElement.GetDirectArray().Add(fbx.FbxColor(p[0], p[1], p[2], p[3]))
        layer.SetVertexColors(vertColourElement)

    def apply_diffuse(self, tex_name, tex_path, node):
        """Bad function that shouldn't be used as shaders should be, but meh"""
        lMaterialName = f'mat {tex_name}'
        lMaterial = fbx.FbxSurfacePhong.Create(self.scene, lMaterialName)
        lMaterial.DiffuseFactor.Set(1)
        lMaterial.ShadingModel.Set('Phong')
        node.AddMaterial(lMaterial)

        gTexture = fbx.FbxFileTexture.Create(self.scene, f'Diffuse Texture {tex_name}')
        lTexPath = tex_path
        gTexture.SetFileName(lTexPath)
        gTexture.SetRelativeFileName(lTexPath)
        gTexture.SetTextureUse(fbx.FbxFileTexture.eStandard)
        gTexture.SetMappingType(fbx.FbxFileTexture.eUV)
        gTexture.SetMaterialUse(fbx.FbxFileTexture.eModelMaterial)
        gTexture.SetSwapUV(False)
        gTexture.SetTranslation(0.0, 0.0)
        gTexture.SetScale(1.0, 1.0)
        gTexture.SetRotation(0.0, 0.0)

        if lMaterial:
            lMaterial.Diffuse.ConnectSrcObject(gTexture)
        else:
            raise RuntimeError('Material broken somewhere')