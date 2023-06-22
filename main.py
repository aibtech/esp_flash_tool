import sys
import csv

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

import requests

from command import EspCommand

# -------------------------------------------------------------------------------- #

MAX_DEVICE = 20

# https://www.w3.org/TR/SVG11/types.html#ColorKeywords
IGNORE_COLOR = "darkgray"
PENDING_COLOR = "azure"
SUCCESS_COLOR = "chartreuse"
FAILED_COLOR = "darkred"

FLASH_BAUDRATE = ["115200", "460800", "921600", "1500000", "1152000"]
ESP_TYPE = ["ESP32", "ESP32C3"]
BIN_PATH = ["bins/esp32", "bins/esp32c3"]

# -------------------------------------------------------------------------------- #

class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('gui/main.ui', self)
        self.show()
        self.esp = EspCommand()
        self.dialog = QtWidgets.QMessageBox()
        self.dialog.setIcon(QMessageBox.Warning)
        self.dialog.setStandardButtons(QMessageBox.Ok)

        # Timers
        self.erase_timer = QTimer()
        self.erase_timer.timeout.connect(self.erase_device)
        self.flash_timer = QTimer()
        self.flash_timer.timeout.connect(self.flash_device)

        # Add list of serial ports to combo boxes
        self.refresh_serial_ports()
        self.comboBoxRate.addItems(FLASH_BAUDRATE)
        self.comboBoxRate.setCurrentText("1500000")
        self.comboBoxRate.currentTextChanged.connect(self.on_baudrate_changed)

        self.comboBoxEspType.addItems(ESP_TYPE)
        self.comboBoxEspType.setCurrentText("ESP32C3")
        self.comboBoxEspType.currentTextChanged.connect(self.on_esp_type_changed)

        # Adding action to the buttons
        self.pushButtonErase.clicked.connect(self.button_erase_clicked)
        self.pushButtonFlash.clicked.connect(self.button_flash_clicked)
        self.pushButtonPath.clicked.connect(self.button_path_clicked)
        self.actionExport_CSV.triggered.connect(self.export_clicked)

        # Process
        self.finished = True
        self.device_id = 0
        self.infos = []

    def __check_valid_input(self):
        if len(self.lineEditPrefix.text()) < 2:
            self.dialog.setText("Prefix length should be larger than 1")
            self.dialog.exec_()
            return False
        try:
            _ = int(self.lineEditDeviceID.text())
        except:
            return False

        if len(self.lineEditDeviceID.text()) != 5:
            self.dialog.setText("Device length should be 5")
            self.dialog.exec_()
            return False
        if len(self.lineEditPath.text()) < 2 or not self.lineEditPath.text().endswith('.bin'):
            self.dialog.setText("Firmware is invalid")
            self.dialog.exec_()
            return False
        return True 

    def on_baudrate_changed(self, value):
        print("Set baudrate to " + value)
        self.refresh_serial_ports()

    def on_esp_type_changed(self, value):
        print("Change ESP type to " + value)
        self.refresh_serial_ports()

    # -------------------------------------------------------------------------------- #

    # Erase selected devices
    def erase_device(self):
        id = self.device_id
        print("Device " + str(id))
        checkbox = self.findChild(QCheckBox, "checkBoxDevice" + str(id))
        com_port = self.findChild(QComboBox, "comboBoxCom" + str(id))
        status = self.findChild(QPushButton, "pushButtonStatus" + str(id))

        try:
            if checkbox.checkState() and len(com_port.currentText()) > 2:
                print("Start erase " + com_port.currentText())
                if self.esp.erase_flash(com_port.currentText(), self.comboBoxRate.currentText()):
                    status.setStyleSheet("background-color : " + SUCCESS_COLOR)
                else:
                    status.setStyleSheet("background-color : " + FAILED_COLOR)
            else:
                status.setStyleSheet("background-color : " + IGNORE_COLOR)
        except Exception as err:
            print(err)

        self.device_id += 1
        if self.device_id > MAX_DEVICE:
            # Finish flashing
            print("Finish")
            self.finished = True
            self.erase_timer.stop()
            self.labelProcess.setText("IDLE")

    # Flash selected devices
    def flash_device(self):
        id = self.device_id
        print("Device " + str(id))
        checkbox = self.findChild(QCheckBox, "checkBoxDevice" + str(id))
        com_port = self.findChild(QComboBox, "comboBoxCom" + str(id))
        status = self.findChild(QPushButton, "pushButtonStatus" + str(id))

        try:
            if checkbox.checkState() and len(com_port.currentText()) > 2:
                print("Start flash " + com_port.currentText())
                if self.esp.flash(com_port.currentText(), self.comboBoxRate.currentText(), self.lineEditPath.text(), BIN_PATH[self.comboBoxEspType.currentIndex()]):
                    mac = self.esp.get_mac(com_port.currentText())
                    print(mac)
                    if mac is not None:
                        device_id = self.lineEditPrefix.text() + self.lineEditDeviceID.text()
                        self.infos.append([mac, device_id])
                        status.setStyleSheet("background-color : " + SUCCESS_COLOR)
                        self.send_to_server(mac, device_id)
                        self.increase_device_id()
                else:
                    status.setStyleSheet("background-color : " + FAILED_COLOR)
            else:
                status.setStyleSheet("background-color : " + IGNORE_COLOR)
        except Exception as err:
            print(err)

        self.device_id += 1

        if self.device_id > MAX_DEVICE:
            # Finish flashing
            print("Finish")
            self.finished = True
            self.flash_timer.stop()
            self.labelProcess.setText("IDLE")

    # -------------------------------------------------------------------------------- #

    def send_to_server(self, mac, device_id):
        url = "https://lzduznsi2d.execute-api.ap-southeast-1.amazonaws.com/default/deviceRegister-staging" 
        headers = { 
            'x-api-key': '7bWIVg3Yrx6JMSEfNlrIQ7IHHSP9MLnE46GrpBIV', 
            'Content-Type': 'application/json' 
        }
        data = "{\"name\": \"Unknown\", \"deviceID\": \"" + device_id + "\", \"macAddress\": \""+ mac + "\", \"deviceType\": \"Unknown\"}"
        rsp = requests.post(url, headers=headers, data=data)
        print(rsp)

    def increase_device_id(self):
        number = int(self.lineEditDeviceID.text())
        number += 1
        self.lineEditDeviceID.setText("{:05d}".format(number))
        new_id = self.lineEditPrefix.text() + self.lineEditDeviceID.text()
        self.esp.create_config_nvs(new_id)

    def refresh_status(self):
        for i in range(0, MAX_DEVICE):
            status = self.findChild(QPushButton, "pushButtonStatus" + str(i + 1))
            status.setStyleSheet("background-color : " + PENDING_COLOR)

    # List of serial ports
    def refresh_serial_ports(self):
        ports = self.esp.serial_ports()
        for i in range(MAX_DEVICE):
            com_port = self.findChild(QComboBox, "comboBoxCom" + str(i + 1))
            current_port = com_port.currentText()
            com_port.clear()
            com_port.addItem(" ")     # First empty element
            com_port.addItems(ports)

            # Keep the last port
            for port in ports:
                if port == current_port:
                    com_port.setCurrentText(port)

    def button_erase_clicked(self):
        if self.finished:
            self.labelProcess.setText("Running")
            self.finished = False
            self.device_id = 1
            self.refresh_status()
            self.erase_timer.start(20)

    def button_path_clicked(self):
        fname = QFileDialog.getOpenFileName(self, "Open file", "", "Firmware Files (*.bin)")
        if fname:
            self.lineEditPath.setText(str(fname[0]))

    def button_flash_clicked(self):
        if not self.__check_valid_input():
            return

        if self.finished:
            # Create nvs file
            device_id = self.lineEditPrefix.text() + self.lineEditDeviceID.text()
            self.esp.create_config_nvs(device_id)
            self.labelProcess.setText("Running")

            self.finished = False
            self.device_id = 1
            self.refresh_status()
            self.flash_timer.start(20)

    def export_clicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getSaveFileName(self,"QFileDialog.getSaveFileName()","","CSV Files (*.csv)", options=options)
        if file_name:
            if not file_name.endswith(".csv"):
                file_name += ".csv"

            # Open the file in the write mode
            with open(file_name, 'w+', encoding='UTF8') as f:
                writer = csv.writer(f)
                writer.writerow(["No.", "MAC", "Device ID"])
                for i in range(0, len(self.infos)):
                    row = [str(i + 1), self.infos[i][0], self.infos[i][1]]
                    writer.writerow(row)

# -------------------------------------------------------------------------------- #

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Ui()
    app.exec_()