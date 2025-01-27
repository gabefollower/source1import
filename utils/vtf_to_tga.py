import sys, os, re
import subprocess
import threading, multiprocessing
import shutil
from pathlib import Path
import shared.base_utils2 as sh

# https://developer.valvesoftware.com/wiki/VTF2TGA
# Runs vtf2tga.exe on every vtf file
# Same thing as `VTFCmd.exe -folder "<dir>\materials\*.vtf" -recurse`


sh.importing = Path("materials")

OVERWRITE = False
IGNORE_WORLD_CUBEMAPS = True

MULTITHREAD = True

currentDir = Path(__file__).parent #os.getcwd()

IN_EXT = ".vtf"
VTEX_PARAMS_EXT = ".txt"

OUT_EXT_LIST = [
    '.tga',     # LDR
    '.pfm',     # HDR
]

OUT_NAME_ENDS = [
    "",     # default
    "up",   # CUBEMAP FACE UP (+ dn, lf, rt, ft, bk)
    "000",  # GIF FRAME 0 (+ 001, 002, 003, ...)
    "_z000",# DEPTH SLICE 0 (+ _z001, _z002, _z003, ...)
    #"sph", # SPHEREMAP (Redundant)

    #"bk",   # CUBEMAP up face
    #"dn",   # CUBEMAP dn face
    #"ft",   # CUBEMAP ft face
    #"lf",   # CUBEMAP lf face
    #"rt",   # CUBEMAP rt face
    #"up",   # CUBEMAP up face
]

def OutputList(path: Path, with_suffix = False):
    """ Return list with all the possible output names
    """ 
    for name in OUT_NAME_ENDS:
        outPath = Path(path.parent) / Path(path.stem + name)
        if not with_suffix: yield outPath
        for ext in OUT_EXT_LIST:
            yield Path(str(outPath) + ext) #.with_suffix(ext)

# if there is one, force skybox vtfs to run on the 2nd row executable __very specific__ 
FORCE_SKYBOX_2ND_VTF2TGA = True

# Add your vtf2tga.exe here. Accepts full (C:/) and relative paths (./). Priority is top to bottom
PATHS_VTF2TGA = [
    r"./shared/bin/vtf2tga/2013/vtf2tga.exe",
    r"./shared/bin/vtf2tga/csgo/vtf2tga.exe", # FORCE_SKYBOX_2ND_VTF2TGA
    r"C:\Program Files (x86)\Steam\steamapps\common\Team Fortress 2\bin\vtf2tga.exe",
    #r"C:\Program Files (x86)\Steam\steamapps\common\Source SDK Base 2013 Multiplayer\bin\vtf2tga.exe",
    #r"D:\Games\steamapps\common\Team Fortress 2\bin\vtf2tga.exe",
    #r"./shared/bin/vtf2tga/tf2/vtf2tga.exe",
    #r"./shared/bin/vtf2tga/hl2/vtf2tga.exe",
]
tags = []

for i, path in enumerate(PATHS_VTF2TGA):
    path = Path(path)
    if not path.is_absolute():
        path = currentDir / path

    if path.is_file():
        print("+ Using:", path)
        PATHS_VTF2TGA [i] = path
        tags.append( [ part for part in path.parts[::-1] if part not in ("vtf2tga.exe", "bin") ] [0])
    else:
        print("~ Invalid vtf2tga path:", path)
        PATHS_VTF2TGA [i] = None

if not any(PATHS_VTF2TGA):
    print(f"Cannot continue without a valid vtf2tga.exe. Please open {currentDir.name} and verify your paths.")
    quit(-1)

erroredFileList = []
totalFiles = 0
MAX_THREADS = min(multiprocessing.cpu_count() + 2, 10)
semaphore = multiprocessing.BoundedSemaphore(value=MAX_THREADS)

def ImportVTFtoTGA(vtfFile, force_2nd = False):
    semaphore.acquire()
    global totalFiles, erroredFileList

    for index, vtf2tga_exe in enumerate(PATHS_VTF2TGA):
        tag = tags[index]

        command = [vtf2tga_exe, "-i", vtfFile] #, "-o", fs.Output(vtfFile.parent)
        result = subprocess.run(command, stdout=subprocess.PIPE) #
        #print (result.stdout.decode("utf-8"))

        # if we are forcing on index 1, continue (don't break) even if index 0 got bCreated
        if (force_2nd and (index != 1)):
            continue
        
        # VTF2TGA reported success...
        if result.returncode == 0:

            bCreated = False
            for outPath in OutputList(vtfFile, True):
                if not outPath.is_file(): continue
                bCreated = True
                totalFiles +=1
                outImages: list[Path] = []

                for ttype in OUT_NAME_ENDS:
                    if not outPath.stem.endswith(ttype):
                        continue

                    if ttype == "": # default
                        if (outPath.stem == vtfFile.stem):
                            outImages.append(outPath)
                            print(f"[{tag}] Sucessfully created:", outPath.local)
                            break

                    elif ttype == 'up': # cubemap
                        for face in ('up', 'dn', 'lf', 'rt', 'bk', 'ft'):
                            nextPath = vtfFile.parent / Path(vtfFile.stem + face + outPath.suffix)
                            if nextPath.is_file():
                                outImages.append(nextPath)
                        faces = "[ " + ", ".join([str(path.stem[-2:]) for path in outImages ]) + " ]"
                        print(f"[{tag}] Sucessfully created: {outPath.local} {faces} cubemap faces")

                    else: # frame sequence & depth slice
                        for i in range(1000):
                            nextPath = vtfFile.parent / Path(vtfFile.stem + f"{i:03}" + outPath.suffix)
                            if nextPath.is_file():
                                outImages.append(nextPath)
                            else: break



                # shitty workaround to vtf2tga not being able to output properly
                for path in outImages:
                    movePath = sh.output(path)
                    os.makedirs(movePath.parent, exist_ok=True) #fs.MakeDir(movePath)
                    shutil.move(path, movePath)

            if not bCreated:
                print(f"[{tag}] uhm...?", vtfFile.local)

            break # Output file created. Onto the next VTF.

        #else: # VTF2TGA reported failure
        #    print(f"[{tag}] Something went wrong!", result.stdout)

        if not ((len(PATHS_VTF2TGA) > 1) and (index < (len(PATHS_VTF2TGA) - 1))):
            erroredFileList.append(vtfFile)

    semaphore.release()

# https://developer.valvesoftware.com/wiki/Vtex_compile_parameters
def txt_import(txtFile):
    transl_table = {
        "clamps": "clampu",
        "clampt": "clampv",
        "clampu": "clampw",
        "nocompress": "nocompress",
        "nolod": "nolod",
        "maxwidth": "maxres",
        "maxheight": "maxres",
        #"": "picmip0res",
        #"maxheight_360": "maxresmobile",
        #"maxwidth_360": "maxresmobile",
        "nomip": "nomip",
        "invertgreen": "legacy_source1_inverted_normal",
        #"": "brightness",
        #"": "brightness_offset",
    }

    # TODO: keyvalues
    with open(txtFile, 'r+') as fp:
        oldLines = fp.readlines()
        if "settings" in oldLines[0]: return
        fp.seek(0)
        fp.truncate()
        fp.write("\"settings\"\n{\n")
        for line in oldLines:
            key, value = re.split(r'\s', line, maxsplit=1)
            key, value = key.strip('"'), value.strip().strip('"')
            new_key = transl_table.get(key)
            if new_key is None:
                fp.write(f"\t// \"{key}\"\t\t\"{value}\"\n") # comment it
            else:
                fp.write(f"\t\"{new_key}\"\t\t\"{value}\"\n")
        fp.write("}")

 
def main():
    THREADS = []
    vtfFileList = sh.collect(sh.importing, IN_EXT, OUT_EXT_LIST, existing = OVERWRITE, outNameRule = OutputList)
    txtFileList = sh.collect(sh.importing, VTEX_PARAMS_EXT, VTEX_PARAMS_EXT, existing = True)

    for vtfFile in vtfFileList:
        if threading.active_count() > (multiprocessing.cpu_count()) *15:
            print("Chief, there's a prob with your multithread code")
        
        if IGNORE_WORLD_CUBEMAPS:
            s_vtfFile = str(vtfFile.name)
            numbers = sum(c.isdigit() for c in s_vtfFile)
            dashes = s_vtfFile.count('_') + s_vtfFile.count('-')
            if (numbers > 4) and (dashes >= 2) and (s_vtfFile.startswith('c')):
                #if fileName.lower().endswith('.hdr.vtf') or \
                #os.path.exists(fileName.lower().replace('.vtf', '.hdr.vtf')):
                continue

        force_2nd = False
        if(FORCE_SKYBOX_2ND_VTF2TGA and (len(PATHS_VTF2TGA) > 1) and ('skybox' in str(vtfFile))):
            force_2nd = True # 2nd exe outputs pfm files. use that for hdr skybox files

        if MULTITHREAD:
            semaphore.acquire()

            THREADS.append(threading.Thread(target=ImportVTFtoTGA,  args=(vtfFile, force_2nd)))
            startThread = THREADS[-1]
            startThread.start()
            semaphore.release()
        else:
            ImportVTFtoTGA(vtfFile, force_2nd)

    for unfinished_thread in THREADS:
        unfinished_thread.join() # wait for the final threads to finish

    for txtFile in txtFileList:
        print(f"Found vtex compile param file {txtFile}")
        #txt_import() blah blah

    for unfinished_thread in THREADS:
        unfinished_thread.join() # wait for the final threads to finish

    if erroredFileList:
        print("\tNo vtf2tga could export the following files:")

        for erroredFile in erroredFileList:
            print(erroredFile.local)

        print(f"\tTotal: {len(erroredFileList)} / {len(vtfFileList)}  |  " + "{:.2f}".format((len(erroredFileList)/len(vtfFileList)) * 100) + f" % Error rate\n")

    print("\n+ Looks like we are done.")

if __name__ == "__main__":
    main()
