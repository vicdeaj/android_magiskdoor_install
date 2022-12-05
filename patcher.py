import os
import shutil
from zipfile import ZipFile
import subprocess


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
        subprocess.check_call([self.workdir + "/magiskboot", "repack", self.bootimg, self.outbootimg])

    def create_config(self):
        config_file = open("config","w")
        config_file.write("KEEPVERITY=false\n")
        config_file.write("KEEPFORCEENCRYPT=true\n")
        config_file.write("PATCHVBMETAFLAG==false\n")
        config_file.write("RECOVERYMODE=false\n")
        # config_file.write("SHA1={}\n".format())
        config_file.close()

    def compress_magisk(self):
        subprocess.check_call([self.workdir + "/magiskboot", "compress=xz", "magisk32","magisk32.xz"])
        subprocess.check_call([self.workdir + "/magiskboot", "compress=xz", "magisk64","magisk64.xz"])


    def magisk_patch_ramdisk(self):
        self.create_config()
        self.compress_magisk()

        subprocess.check_call([self.workdir + "/magiskboot", "cpio", "ramdisk.cpio",
                                          "add 0750 init magiskinit",
                                          "mkdir 0750 overlay.d",
                                          "mkdir 0750 overlay.d/sbin",
                                          "add 0644 overlay.d/sbin/magisk32.xz magisk32.xz",
                                          "add 0644 overlay.d/sbin/magisk64.xz magisk64.xz",
                                          "patch"
                                          ])

    def magisk_patch_bin(self):
        for dt in ["dtb", "kernel_dtb"]:
            if os.path.exists(dt):
                subprocess.run([self.workdir + "/magiskboot","dtb", dt, "patch"])

        # Force kernel to load rootfs
        # skip_initramfs -> want_initramfs
        subprocess.check_call([self.workdir + "/magiskboot", "hexpatch", "kernel", "736B69705F696E697472616D667300", "736B69705F696E697472616D667300"])

    def custom_patch(self):
        pass

    def run(self):
        # prepare environment
        self.extract_files()
        self.copy_files()
        os.chdir(self.workdir)

        # patch boot
        self.unpack()
        self.magisk_patch_ramdisk()
        self.magisk_patch_bin()

        self.custom_patch()

        self.repack()

        os.chdir(self.calling_dir)

def main():
    patcher = BootPatcher("boot.img")
    patcher.run()


if __name__ == "__main__":
    main()
