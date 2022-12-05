import os
import shutil
from zipfile import ZipFile
import subprocess
import libarchive



def create_workdir(workdir):  # create workdir
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    os.mkdir(workdir)
    workdir = os.path.abspath(workdir)
    return workdir


class BootPatcher:
    magisk_apk: str
    calling_dir: str
    workdir: str
    bootimg: str
    outbootimg: str
    my_env: dict


    def __init__(self, bootimg,outbootimg="outboot.img",workdir="tmp", magisk_apk="Magisk-v25.2.apk"):
        if not os.path.exists(bootimg):
            raise FileNotFoundError(bootimg)
        if not os.path.exists(magisk_apk):
            raise FileNotFoundError(magisk_apk)

        self.magisk_apk = os.path.abspath(magisk_apk)
        self.bootimg = os.path.abspath(bootimg)
        self.outbootimg = os.path.abspath(outbootimg)

        self.calling_dir = os.getcwd()
        self.workdir = create_workdir(workdir)
        self.extractedFiles = self.workdir + "/extracted"

    def extract_files(self):
        zip = ZipFile(self.magisk_apk, "r")
        zip.extractall(self.extractedFiles)
        zip.close()

    def copy_files(self):
        shutil.copy(self.extractedFiles+"/lib/x86/libmagiskboot.so", self.workdir+"/magiskboot")
        os.chmod(self.workdir+"/magiskboot",0o755)
        shutil.copy(self.extractedFiles+"/lib/armeabi-v7a/libmagisk32.so", self.workdir+"/magisk32")
        os.chmod(self.workdir+"/magisk32",0o755)
        shutil.copy(self.extractedFiles+"/lib/arm64-v8a/libmagisk64.so", self.workdir+"/magisk64")
        os.chmod(self.workdir+"/magisk64",0o755)
        shutil.copy(self.extractedFiles+"/lib/arm64-v8a/libmagiskinit.so", self.workdir+"/magiskinit")
        os.chmod(self.workdir+"/magiskinit",0o755)

    def unpack(self):
        try:
            subprocess.check_call([self.workdir+"/magiskboot", "unpack", self.bootimg])
        except subprocess.CalledProcessError:
            print("Error unpacikng, unsupported image format")
            exit(1)

    def repack(self):
        subprocess.check_call([self.workdir + "/magiskboot", "repack", self.bootimg, self.outbootimg], env=self.my_env)

    def create_config(self):
        self.my_env = {}
        self.my_env["KEEPVERITY"] = "true"
        self.my_env["KEEPFORCEENCRYPT"] = "true"
        self.my_env["PATCHVBMETAFLAG"] = "false"
        self.my_env["RECOVERYMODE"] = "false"


    def custom_patch(self):
        pass

    def get_config(self):

        a = libarchive.Archive('ramdisk.cpio')
        for entry in a:
            if entry.isfile() and "backup" not in entry.pathname:
                print(entry)
                print(entry.read())
        a.close()

        subprocess.run([self.workdir + "/magiskboot", "cpio", "ramdisk.cpio"])
        pass

    def run(self):
        # prepare environment
        self.extract_files()
        self.copy_files()
        os.chdir(self.workdir)

        self.unpack()

        # self.create_config()
        self.get_config()

        self.custom_patch()

        self.repack()

        os.chdir(self.calling_dir)

def main():
    patcher = BootPatcher("magisk.img")
    patcher.run()


if __name__ == "__main__":
    main()
