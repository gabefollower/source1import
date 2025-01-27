import shared.base_utils2 as sh

SHOULD_OVERWRITE = False

#@sh.s1import('.vmdl')
#def ImportMDLtoVMDL(mdl_path, vmdl_path, move_s1_assets = False):
def ImportMDLtoVMDL(mdl_path, move_s1_assets = False):

    vmdl_path = sh.output(mdl_path, '.vmdl')

    with open(vmdl_path, 'w') as out:
        out.write("<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:generic:version{7412167c-06e9-4698-aff2-e63eb59037e7} -->\n{\r\n")
        out.write(f"\tm_sMDLFilename = \"{mdl_path.local.as_posix()}\"\r\n")
        out.write("}\r\n")
    
    print('+ Generated', vmdl_path.local)
    return vmdl_path

if __name__ == "__main__":
    print('Source 2 VMDL Generator!')

    mdl_files = sh.collect('models', '.mdl', '.vmdl', SHOULD_OVERWRITE)

    for mdl in mdl_files:
        ImportMDLtoVMDL(mdl)
    
    print("Looks like we are done!")
