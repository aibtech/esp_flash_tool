import subprocess
import sys
import glob
import serial
from PyQt5 import QtCore
import csv

class EspCommand(QtCore.QObject):
    out_signal = QtCore.pyqtSignal(str)

    def __run_command(self, cmd, **kwargs):
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
        )
        return proc.stdout
    
    # Erase flash
    def erase_flash(self, port, baud):
        output = self.__run_command("esptool.py -b " + baud + " --p " + port + " erase_flash", cwd="./", shell=True)
        for line in output:
            if "Chip erase completed successfully" in line.decode():
                return True
        return False

    # FLash bootloader
    def flash_bootloader(self, port, baud, path="bins/bootloader.bin"):
        # ESP32 flash bootloader at 0x1000 while ESP32C3 is at 0x000
        if "esp32c3" in path:
            output = self.__run_command("esptool.py -b " + baud + " --p " + port + " write_flash 0x0000 " + path, cwd="./", shell=True)
        else:
            output = self.__run_command("esptool.py -b " + baud + " --p " + port + " write_flash 0x1000 " + path, cwd="./", shell=True)

        for line in output:
            if "Wrote" in line.decode() and "at 0x" in line.decode():
                return True
        return False

    # FLash partition
    def flash_partition(self, port, baud, path="bins/partition-table.bin"):
        output = self.__run_command("esptool.py -b " + baud + " --p " + port + " write_flash 0x8000 " + path, cwd="./", shell=True)
        for line in output:
            if "Wrote" in line.decode() and "at 0x00008000" in line.decode():
                return True
        return False

    # FLash ota_init
    def flash_ota_init(self, port, baud, path="bins/ota_data_initial.bin"):
        output = self.__run_command("esptool.py -b " + baud + " --p " + port + " write_flash 0xd000 " + path, cwd="./", shell=True)
        for line in output:
            if "Wrote" in line.decode() and "at 0x0000d000" in line.decode():
                return True
        return False

    # FLash firmware
    def flash_firmware(self, port, baud, path):
        output = self.__run_command("esptool.py -b " + baud + " --p " + port + " write_flash 0x10000 " + path, cwd="./", shell=True)
        for line in output:
            if "Wrote" in line.decode() and "at 0x00010000" in line.decode():
                return True
        return False

    # Flash nvs partition
    def flash_nvs(self, port, baud, path="bins/nvs.bin"):
        output = self.__run_command("esptool.py -b " + baud + " --p " + port + " write_flash 0x003e0000 " + path, cwd="./", shell=True)
        for line in output:
            if "Wrote" in line.decode() and "at 0x003e0000" in line.decode():
                return True
        return False

    # Flash firmware
    def flash(self, port, baud, firmware_path, bin_path):
        if not self.flash_bootloader(port, baud, bin_path + '/bootloader.bin'):
            print("flash_bootloader failed")
            return False
        if not self.flash_partition(port, baud, bin_path + '/partition-table.bin'):
            print("flash_partition failed")
            return False
        if not self.flash_ota_init(port, baud, bin_path + '/ota_data_initial.bin'):
            print("flash_ota_init failed")
            return False
        if not self.flash_firmware(port, baud, firmware_path):
            print("flash_firmware failed")
            return False
        if not self.flash_nvs(port, baud):
            print("flash_nvs failed")
            return False
        return True

    # Get MAC address
    def get_mac(self, port):
        output = self.__run_command("esptool.py --p " + port + " read_mac", cwd="./", shell=True)
        for line in output:
            if "MAC: " in line.decode():
                mac = line.decode().replace("\r\n", '')
                return mac[5:].replace(":", '').upper()
        return None

    # Create nvs.bin  for configuration
    def create_config_nvs(self, device_id):
        header = ['key', 'type', 'encoding', 'value']
        namespace = ['nvs_store', 'namespace', '', '']
        data = ['deviceid', 'data', 'string', device_id]
        print("Create nvs device id " + str(device_id))

        # Open the file in the write mode
        with open('./bins/nvs.csv', 'w+', encoding='UTF8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerow(namespace)
            writer.writerow(data)

        output = self.__run_command("python tools/nvs_partition_gen.py generate bins/nvs.csv bins/nvs.bin 0x4000", cwd="./", shell=True)
        for line in output:
            if "Created NVS binary" in line.decode():
                return True
        return False

    # Get all serial port
    def serial_ports(self):
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result