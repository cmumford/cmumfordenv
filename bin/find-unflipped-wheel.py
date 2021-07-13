#!/usr/bin/python

from winreg import *

# Print all registry values with FlipFlopWheel=0

root_path = r"SYSTEM\CurrentControlSet\Enum\HID"
aReg = ConnectRegistry(None, HKEY_LOCAL_MACHINE)

hids_key = OpenKey(aReg, root_path)
for hid_idx in range(1024):
    try:
        hid_name = EnumKey(hids_key, hid_idx)
        hid_key = OpenKey(hids_key, hid_name)

        for vid_idx in range(1024):
            try:
                vid_name = EnumKey(hid_key, vid_idx)
                vid_key = OpenKey(hid_key, vid_name)
                device_parameters_key = OpenKey(vid_key, 'Device Parameters')
                val = QueryValueEx(device_parameters_key, 'FlipFlopWheel')
                if (not val[0]):
                    print("{0}\\{1}".format(hid_name, vid_name))
            except EnvironmentError:
                break
    except EnvironmentError:
        break
