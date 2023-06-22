# Tools
```
pip install esptool
pip install PyQT5
```

# Run command
```
python .\tools\nvs_partition_gen.py generate .\tools\nvs.csv .\tools\nvs.bin 0x4000
esptool.py --p COM16 write_flash 0x3E000 .\tools\nvs.bin

esptool.py -b 1500000 --p COM16 erase_flash
esptool.py -b 1500000 --p COM16 write_flash 0x0000 .\bins\bootloader.bin
esptool.py -b 1500000 --p COM16 write_flash 0x8000 .\bins\partition-table.bin
esptool.py -b 1500000 --p COM16 write_flash 0xd000 .\bins\ota_data_initial.bin
esptool.py -b 1500000 --p COM16 write_flash 0x10000 .\bins\firmware.bin
```

# Export exe
```
pyinstaller --windowed --onefile main.py
```