"""
After Effects FFX Effect Generator
Generates After Effects FFX preset files from control definitions.
"""

import struct
import tempfile
import os
import uuid
from typing import List, Dict, Any, Optional


def hex_to_bytes(hex_str: str) -> bytes:
    """Convert hex string to bytes."""
    if len(hex_str) % 2 != 0:
        hex_str = "0" + hex_str
    return bytes.fromhex(hex_str)


def zero_pairs(num: int) -> str:
    """Generate zero pairs for padding."""
    return "00" * num


def pad(num: str, length: int) -> str:
    """Pad string with leading zeros to specified length."""
    zeros = "0" * length
    return (zeros + str(num))[-length:]


def pad2(num: str) -> str:
    """Pad to 2 characters."""
    return ("00" + str(num))[-2:]


def pad4(num: str) -> str:
    """Pad to 4 characters."""
    return ("0000" + str(num))[-4:]


def pad_end(num: str, length: int) -> str:
    """Pad string with leading zeros to specified length."""
    return num.ljust(length, '0')


def pack_ieee754_32(value: float) -> str:
    return struct.pack(">f", float(value)).hex()


def pack_ieee754_64(value: float) -> str:
    return struct.pack(">d", float(value)).hex()


def decimal_to_twos_complement_hex(decimal: int, size: int = 8) -> str:
    """Convert decimal to hex with two's complement for negatives."""
    hexadecimal = hex(abs(decimal))[2:].zfill(size)
    if decimal >= 0:
        return hexadecimal
    return hex(4294967296 - int(hexadecimal, 16))[2:]


def fraction_to_hex(num: float) -> str:
    """Convert fractional part to hex."""
    out = ""
    limit = 0
    while num != 0:
        all_val = num * 16
        i = int(all_val)
        num = all_val - i
        out += hex(i)[2:]
        limit += 1
        if limit > 10:
            break
    return out


class FFXGenerator:
    """Generates FFX preset files."""
    
    def __init__(self, control_name: str, match_name: str, controls: List[Dict[str, Any]]):
        self.control_name = control_name
        self.match_name = match_name
        self.controls = controls
        self.ffx_data = self.build_ffx_binary(control_name, match_name, controls)
    
    def build_match_name_entry(self, index: str, matchname: Optional[str] = None) -> bytes:
        """Create a match name entry."""
        if matchname is None:
            matchname = self.match_name
        
        if index != "-1":
            mn_len = len(matchname) + 1 + len(index)
            result = matchname + "-" + index
            padding = hex_to_bytes(zero_pairs(40 - mn_len))
            return result.encode('latin-1') + padding
        else:
            padding = hex_to_bytes(zero_pairs(40 - len(matchname)))
            return matchname.encode('latin-1') + padding
    
    def build_label_entry(self, text: str) -> bytes:
        """Create a label name entry."""
        name_bytes = hex_to_bytes(hex(len(text) + 1)[2:].zfill(2))
        name_bytes += text.encode('latin-1')
        if len(text) % 2 == 0:
            name_bytes += hex_to_bytes("0000")
        else:
            name_bytes += hex_to_bytes("00")
        return name_bytes
    
    def build_control_header(self, index: str) -> bytes:
        """Create a control header."""
        header = hex_to_bytes("28")
        header += self.build_match_name_entry(index)
        header += hex_to_bytes("706172640000009400000000000000")
        header += hex_to_bytes("00")
        header += hex_to_bytes("00000000000000")
        return header
    
    def build_list_block_header(self, index: str) -> bytes:
        """Create a list block header."""
        header = hex_to_bytes("28")
        header += self.build_match_name_entry(index)
        header += hex_to_bytes("4C495354")
        return header
    
    def build_first_control_record(self, index: str, first: bool, last: bool) -> tuple:
        """Create the first control record."""
        record_prefix = hex_to_bytes("28")
        record_suffix_hex = "706172640000009400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002000000000000000E0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000FFFFFFFF00000000000000000000000000000000"
        if not last:
            record_suffix_hex += "74646D6E000000"
        record_suffix = hex_to_bytes(record_suffix_hex)
        control_record = record_prefix + self.build_match_name_entry(index) + record_suffix
        
        list_signature = "4C495354"
        metadata_prefix = "746462737464736200000004000000037464736E000000"
        encoded_label = "010000"
        metadata_template = "746462340000007CDB9900010001000000010000000002583F1A36E2EB1C432D3FF00000000000003FF00000000000003FF00000000000003FF00000000000000000000404C0C0C0FFC0C0C0000000008000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000063646174000000280000000000000000000000000000000000000000000000000000000000000000000000000000000074647069000000040000000E"
        chunk_terminator = "74646D6E000000"
        
        data_payload = hex_to_bytes(metadata_prefix) + hex_to_bytes(encoded_label) + hex_to_bytes(metadata_template)
        payload_length_hex = pad(hex(len(data_payload))[2:], 8)
        
        control_data_block = hex_to_bytes("28") + self.build_match_name_entry(index) + hex_to_bytes(list_signature)
        control_data_block += hex_to_bytes(payload_length_hex) + data_payload + hex_to_bytes(chunk_terminator)
        
        return (control_record, control_data_block)
    
    def build_boundary_record(self, index: str, first: bool, last: bool, control_name: str) -> tuple:
        """Create an empty item."""
        record_prefix = hex_to_bytes("28")
        record_suffix_hex = "7061726400000094000000000000000000000000000000"
        record_suffix_hex += "00" if first else "0E"
        record_suffix_hex += "000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        if not last:
            record_suffix_hex += "74646D6E000000"
        record_suffix = hex_to_bytes(record_suffix_hex)
        control_record = record_prefix + self.build_match_name_entry(index) + record_suffix
        
        list_signature = "4C495354"
        metadata_prefix = "746462737464736200000004000000017464736E000000"
        encoded_label = self.build_label_entry(control_name)
        metadata_template = "746462340000007CBD990001000100000001000400005DA800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000063646174000000280000000000000000000000000000000000000000000000000000000000000000000000000000000074647069000000040000000E"
        chunk_terminator = "74646D6E000000"
        
        data_payload = hex_to_bytes(metadata_prefix) + encoded_label + hex_to_bytes(metadata_template)
        payload_length_hex = pad(hex(len(data_payload))[2:], 8)
        
        control_data_block = hex_to_bytes("28") + self.build_match_name_entry(index) + hex_to_bytes(list_signature)
        control_data_block += hex_to_bytes(payload_length_hex) + data_payload + hex_to_bytes(chunk_terminator)
        
        return (control_record, control_data_block)
    
    def build_slider_record(self, index: str, last: bool, text: str, min_val: float, max_val: float,
                           s_min: float, s_max: float, default_value: float, precision: int,
                           percent: bool, pixel: bool, keys: bool, hold: bool, invisible: bool) -> tuple:
        """Create a slider control item."""
        control_record = hex_to_bytes("28")
        control_record += self.build_match_name_entry(index)
        control_record += hex_to_bytes("7061726400000094000000000000")
        control_record += hex_to_bytes("02" if invisible else "00")
        control_record += hex_to_bytes("00")
        control_record += hex_to_bytes("00000000000000")
        control_record += hex_to_bytes("0A")
        control_record += text.encode('latin-1')
        control_record += hex_to_bytes(zero_pairs(35 - len(text)))
        control_record += hex_to_bytes("00" if keys else "02")
        control_record += hex_to_bytes(zero_pairs(52))
        control_record += hex_to_bytes(pack_ieee754_32(min_val))
        control_record += hex_to_bytes(pack_ieee754_32(max_val))
        control_record += hex_to_bytes(pack_ieee754_32(s_min))
        control_record += hex_to_bytes(pack_ieee754_32(s_max))
        control_record += hex_to_bytes(pack_ieee754_32(default_value))
        control_record += hex_to_bytes("000" + str(precision))
        
        if percent and pixel:
            s_option = "0003"
        elif percent:
            s_option = "0001"
        elif pixel:
            s_option = "0002"
        else:
            s_option = "0000"
        control_record += hex_to_bytes(s_option)
        control_record += hex_to_bytes(zero_pairs(20))
        if not last:
            control_record += hex_to_bytes("74646D6E000000")
        
        # Part 2
        control_data_block = hex_to_bytes("28")
        control_data_block += self.build_match_name_entry(index)
        control_data_block += hex_to_bytes("4C495354")
        
        data_payload = hex_to_bytes("746462737464736200000004000000")
        data_payload += hex_to_bytes("03" if invisible else "01")
        data_payload += hex_to_bytes("7464736E000000")
        data_payload += hex_to_bytes(hex(len(text) + 1)[2:].zfill(2))
        data_payload += text.encode('latin-1')
        data_payload += hex_to_bytes("0000") if len(text) % 2 == 0 else hex_to_bytes("00")
        data_payload += hex_to_bytes("746462340000007CBD99000100010000000100")
        data_payload += hex_to_bytes("04" if hold else "FF")
        data_payload += hex_to_bytes("00005DA80000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006364617400000028")
        data_payload += hex_to_bytes(pad_end(pack_ieee754_64(default_value), 80))
        data_payload += hex_to_bytes("7464756D000000")
        data_payload += hex_to_bytes("08")
        data_payload += hex_to_bytes(pack_ieee754_64(s_min))
        data_payload += hex_to_bytes("7464754D000000")
        data_payload += hex_to_bytes("08")
        data_payload += hex_to_bytes(pack_ieee754_64(s_max))
        
        control_records = pad(hex(len(data_payload))[2:], 8)
        control_data_block += hex_to_bytes(control_records)
        control_data_block += data_payload
        control_data_block += hex_to_bytes("74646D6E000000")
        
        return (control_record, control_data_block)
    
    def build_angle_record(self, index: str, last: bool, text: str, total_degrees: float,
                          keys: bool, hold: bool) -> tuple:
        """Create an angle control item."""
        control_record = self.build_control_header(index)
        control_record += hex_to_bytes("03")
        control_record += text.encode('latin-1')
        control_record += hex_to_bytes(zero_pairs(35 - len(text)))
        control_record += hex_to_bytes("00" if keys else "02")
        control_record += hex_to_bytes(zero_pairs(8))
        
        split = str(total_degrees).split(".")
        int_part = int(split[0])
        
        if len(split) > 1 and float("0." + split[1]) != 0 and int_part < 0:
            int_part = int_part - 1
            split[1] = str(1 - float("0." + split[1]))[2:]
        
        if int_part < 0:
            control_record += hex_to_bytes(pad4(hex(int_part & 0xFFFFFFFF)[2:]))
        else:
            control_record += hex_to_bytes(pad4(hex(int_part)[2:]))
        
        if len(split) > 1 and split[1]:
            hex_frac = fraction_to_hex(float("0." + split[1]))
            hex_frac = hex_frac.ljust(14, '0')
        else:
            hex_frac = "00000000000000"
        
        control_record += hex_to_bytes(hex_frac)
        control_record += hex_to_bytes(zero_pairs(79))
        if not last:
            control_record += hex_to_bytes("74646D6E000000")
        
        # Part 2
        control_data_block = self.build_list_block_header(index)
        data_payload = hex_to_bytes("746462737464736200000004000000017464736E000000")
        data_payload += self.build_label_entry(text)
        data_payload += hex_to_bytes("746462340000007CBD99000100010000000100")
        data_payload += hex_to_bytes("04" if hold else "FF")
        data_payload += hex_to_bytes("00005DA80000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006364617400000028")
        data_payload += hex_to_bytes(pack_ieee754_64(total_degrees))
        data_payload += hex_to_bytes(zero_pairs(32))
        
        control_records = pad(hex(len(data_payload))[2:], 8)
        control_data_block += hex_to_bytes(control_records)
        control_data_block += data_payload
        control_data_block += hex_to_bytes("74646D6E000000")
        
        return (control_record, control_data_block)
    
    def build_checkbox_record(self, index: str, last: bool, label_text: str, option_label: str,
                                 checked: bool, keys: bool, hold: bool, invisible: bool) -> tuple:
        """Create a checkbox control item."""
        control_record = self.build_control_header(index)
        control_record += hex_to_bytes("04")
        control_record += label_text.encode('latin-1')
        control_record += hex_to_bytes(zero_pairs(35 - len(label_text)))
        control_record += hex_to_bytes("00" if keys else "02")
        control_record += hex_to_bytes(zero_pairs(7))
        control_record += hex_to_bytes("0001" if checked else "0000")
        control_record += hex_to_bytes(zero_pairs(87))
        control_record += hex_to_bytes("70646E6D000000")
        control_record += self.build_label_entry(option_label)
        if not last:
            control_record += hex_to_bytes("74646D6E000000")
        
        # Part 2
        control_data_block = self.build_list_block_header(index)
        data_payload = hex_to_bytes("746462737464736200000004000000")
        data_payload += hex_to_bytes("03" if invisible else "01")
        data_payload += hex_to_bytes("7464736E000000")
        data_payload += self.build_label_entry(label_text)
        data_payload += hex_to_bytes("746462340000007CDB99000100010000000100")
        data_payload += hex_to_bytes("04" if hold else "FF")
        data_payload += hex_to_bytes("00005DA83F1A36E2EB1C432D3FF00000000000003FF00000000000003FF00000000000003FF000000000000000000004040000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006364617400000028")
        if checked:
            data_payload += hex_to_bytes("3FF0" + zero_pairs(38))
        else:
            data_payload += hex_to_bytes(zero_pairs(40))
        
        control_records = pad(hex(len(data_payload))[2:], 8)
        control_data_block += hex_to_bytes(control_records)
        control_data_block += data_payload
        control_data_block += hex_to_bytes("74646D6E000000")
        
        return (control_record, control_data_block)
    
    def build_color_record(self, index: str, last: bool, text: str, red: int, green: int, blue: int,
                          keys: bool, hold: bool, invisible: bool) -> tuple:
        """Create a color control item."""
        control_record = self.build_control_header(index)
        control_record += hex_to_bytes("05")
        control_record += text.encode('latin-1')
        control_record += hex_to_bytes(zero_pairs(35 - len(text)))
        control_record += hex_to_bytes("00" if keys else "02")
        control_record += hex_to_bytes(zero_pairs(6))
        control_record += hex_to_bytes("FF")
        control_record += hex_to_bytes("FF")
        control_record += hex_to_bytes("FF")
        control_record += hex_to_bytes(pad2(hex(min(red, 255))[2:]))
        control_record += hex_to_bytes(pad2(hex(min(green, 255))[2:]))
        control_record += hex_to_bytes(pad2(hex(min(blue, 255))[2:]))
        control_record += hex_to_bytes(zero_pairs(84))
        if not last:
            control_record += hex_to_bytes("74646D6E000000")
        
        # Part 2
        control_data_block = self.build_list_block_header(index)
        data_payload = hex_to_bytes("746462737464736200000004000000")
        data_payload += hex_to_bytes("03" if invisible else "01")
        data_payload += hex_to_bytes("7464736E000000")
        data_payload += self.build_label_entry(text)
        data_payload += hex_to_bytes("746462340000007CBD990004000700010002FF")
        data_payload += hex_to_bytes("04" if hold else "FF")
        data_payload += hex_to_bytes("00005DA80000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006364617400000060")
        data_payload += hex_to_bytes(pack_ieee754_64(255))
        data_payload += hex_to_bytes(pack_ieee754_64(red))
        data_payload += hex_to_bytes(pack_ieee754_64(green))
        data_payload += hex_to_bytes(pack_ieee754_64(blue))
        data_payload += hex_to_bytes(zero_pairs(64))
        
        control_records = pad(hex(len(data_payload))[2:], 8)
        control_data_block += hex_to_bytes(control_records)
        control_data_block += data_payload
        control_data_block += hex_to_bytes("74646D6E000000")
        
        return (control_record, control_data_block)
    
    def build_layer_record(self, index: str, last: bool, text: str, self_layer: bool,
                          keys: bool, hold: bool, invisible: bool) -> tuple:
        """Create a layer control item."""
        control_record = self.build_control_header(index)
        control_record += hex_to_bytes("00")
        control_record += text.encode('latin-1')
        control_record += hex_to_bytes(zero_pairs(35 - len(text)))
        control_record += hex_to_bytes("00" if keys else "02")
        control_record += hex_to_bytes(zero_pairs(76))
        if self_layer:
            control_record += hex_to_bytes("FFFFFFFF" + zero_pairs(16))
        else:
            control_record += hex_to_bytes(zero_pairs(20))
        if not last:
            control_record += hex_to_bytes("74646D6E000000")
        
        # Part 2
        control_data_block = self.build_list_block_header(index)
        data_payload = hex_to_bytes("746462737464736200000004000000")
        data_payload += hex_to_bytes("03" if invisible else "01")
        data_payload += hex_to_bytes("7464736E000000")
        data_payload += self.build_label_entry(text)
        data_payload += hex_to_bytes("746462340000007CDB99000100010000000100")
        data_payload += hex_to_bytes("04" if hold else "FF")
        data_payload += hex_to_bytes("00005DA83F1A36E2EB1C432D3FF00000000000003FF00000000000003FF00000000000003FF000000000000000000004040000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006364617400000028")
        data_payload += hex_to_bytes(zero_pairs(40))
        if self_layer:
            data_payload += hex_to_bytes("74647069000000040000000E")
        else:
            data_payload += hex_to_bytes("746470690000000400000000")
        
        control_records = pad(hex(len(data_payload))[2:], 8)
        control_data_block += hex_to_bytes(control_records)
        control_data_block += data_payload
        control_data_block += hex_to_bytes("74646D6E000000")
        
        return (control_record, control_data_block)
    
    def build_point2d_record(self, index: str, last: bool, text: str, x_percent: float, y_percent: float,
                          keys: bool, hold: bool, invisible: bool) -> tuple:
        """Create a point control item."""
        control_record = self.build_control_header(index)
        control_record += hex_to_bytes("06")
        control_record += text.encode('latin-1')
        control_record += hex_to_bytes(zero_pairs(35 - len(text)))
        control_record += hex_to_bytes("00" if keys else "02")
        control_record += hex_to_bytes(zero_pairs(4))
        control_record += hex_to_bytes(pad(hex(int(65536 * x_percent))[2:], 8))
        control_record += hex_to_bytes(pad(hex(int(65536 * y_percent))[2:], 8))
        control_record += hex_to_bytes(zero_pairs(4))
        control_record += hex_to_bytes(decimal_to_twos_complement_hex(int(x_percent * 100 * 65536)))
        control_record += hex_to_bytes(decimal_to_twos_complement_hex(int(y_percent * 100 * 65536)))
        control_record += hex_to_bytes(zero_pairs(72))
        if not last:
            control_record += hex_to_bytes("74646D6E000000")
        
        # Part 2
        control_data_block = self.build_list_block_header(index)
        data_payload = hex_to_bytes("746462737464736200000004000000")
        data_payload += hex_to_bytes("03" if invisible else "01")
        data_payload += hex_to_bytes("7464736E000000")
        data_payload += self.build_label_entry(text)
        data_payload += hex_to_bytes("746462340000007CDB990002000F0003FFFFFF")
        data_payload += hex_to_bytes("04" if hold else "FF")
        data_payload += hex_to_bytes("00005DA83D9B7CDFD9D7BDBC3FF00000000000003FF00000000000003FF00000000000003FF000000000000000000004060000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000006364617400000030")
        # Using 0 for width/height since we don't have layer context
        data_payload += hex_to_bytes(pack_ieee754_64(0))
        data_payload += hex_to_bytes(pack_ieee754_64(0))
        data_payload += hex_to_bytes(zero_pairs(32))
        
        control_records = pad(hex(len(data_payload))[2:], 8)
        control_data_block += hex_to_bytes(control_records)
        control_data_block += data_payload
        control_data_block += hex_to_bytes("74646D6E000000")
        
        return (control_record, control_data_block)
    
    def build_point3d_record(self, index: str, last: bool, text: str, x_percent: float, y_percent: float,
                              z_percent: float, keys: bool, hold: bool, invisible: bool) -> tuple:
        """Create a 3D point control item."""
        control_record = self.build_control_header(index)
        control_record += hex_to_bytes("12")
        control_record += text.encode('latin-1')
        control_record += hex_to_bytes(zero_pairs(35 - len(text)))
        control_record += hex_to_bytes("00" if keys else "02")
        control_record += hex_to_bytes(zero_pairs(4))
        control_record += hex_to_bytes(pack_ieee754_64(x_percent))
        control_record += hex_to_bytes(pack_ieee754_64(y_percent))
        control_record += hex_to_bytes(pack_ieee754_64(z_percent))
        control_record += hex_to_bytes(pack_ieee754_64(x_percent * 100))
        control_record += hex_to_bytes(pack_ieee754_64(y_percent * 100))
        control_record += hex_to_bytes(pack_ieee754_64(z_percent * 100))
        control_record += hex_to_bytes(zero_pairs(44))
        if not last:
            control_record += hex_to_bytes("74646D6E000000")
        
        # Part 2
        control_data_block = self.build_list_block_header(index)
        data_payload = hex_to_bytes("746462737464736200000004000000")
        data_payload += hex_to_bytes("03" if invisible else "01")
        data_payload += hex_to_bytes("7464736E000000")
        data_payload += self.build_label_entry(text)
        data_payload += hex_to_bytes("746462340000007CDB990003000F0003FFFFFF")
        data_payload += hex_to_bytes("04" if hold else "FF")
        data_payload += hex_to_bytes("00005DA83D9B7CDFD9D7BDBC3FF00000000000003FF00000000000003FF00000000000003FF000000000000000000008090000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000000000000000000000000000006364617400000048")
        data_payload += hex_to_bytes(pack_ieee754_64(0))
        data_payload += hex_to_bytes(pack_ieee754_64(0))
        data_payload += hex_to_bytes(pack_ieee754_64(0))
        data_payload += hex_to_bytes(zero_pairs(48))
        
        control_records = pad(hex(len(data_payload))[2:], 8)
        control_data_block += hex_to_bytes(control_records)
        control_data_block += data_payload
        control_data_block += hex_to_bytes("74646D6E000000")
        
        return (control_record, control_data_block)
    
    def build_dropdown_record(self, index: str, last: bool, text: str, option_list_text: str, default_value: int,
                          keys: bool, hold: bool, invisible: bool) -> tuple:
        """Create a dropdown control item."""
        default_value = int(default_value)
        control_record = self.build_control_header(index)
        control_record += hex_to_bytes("07")
        control_record += text.encode('latin-1')
        control_record += hex_to_bytes(zero_pairs(35 - len(text)))
        control_record += hex_to_bytes("00" if keys else "02")
        control_record += hex_to_bytes(zero_pairs(6))
        control_record += hex_to_bytes(pad4(hex(default_value)[2:]))
        control_record += hex_to_bytes(pad4(hex(3)[2:]))
        control_record += hex_to_bytes(pad4(hex(default_value)[2:]))
        control_record += hex_to_bytes(zero_pairs(84))
        control_record += hex_to_bytes("70646E6D000000")
        control_record += self.build_label_entry(option_list_text)
        if not last:
            control_record += hex_to_bytes("74646D6E000000")
        
        # Part 2
        control_data_block = self.build_list_block_header(index)
        data_payload = hex_to_bytes("746462737464736200000004000000")
        data_payload += hex_to_bytes("03" if invisible else "01")
        data_payload += hex_to_bytes("7464736E000000")
        data_payload += self.build_label_entry(text)
        data_payload += hex_to_bytes("746462340000007CDB99000100010000000100")
        data_payload += hex_to_bytes("04" if hold else "FF")
        data_payload += hex_to_bytes("00005DA83F1A36E2EB1C432D3FF00000000000003FF00000000000003FF00000000000003FF000000000000000000004040000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000006364617400000028")
        data_payload += hex_to_bytes(pack_ieee754_64(default_value))
        data_payload += hex_to_bytes(zero_pairs(32))
        
        control_records = pad(hex(len(data_payload))[2:], 8)
        control_data_block += hex_to_bytes(control_records)
        control_data_block += data_payload
        control_data_block += hex_to_bytes("74646D6E000000")
        
        return (control_record, control_data_block)
    
    def build_text_record(self, index: str, text: str, dim: bool, invisible: bool) -> tuple:
        """Create a text/group/label item."""
        control_record = hex_to_bytes("28")
        control_record += self.build_match_name_entry(index)
        control_record += hex_to_bytes("706172640000009400000000000000")
        control_record += hex_to_bytes("20" if dim else "00")
        control_record += hex_to_bytes("00000000000000")
        control_record += hex_to_bytes("0D")
        control_record += text.encode('latin-1')
        control_record += hex_to_bytes(zero_pairs(132 - len(text)))
        control_record += hex_to_bytes("74646D6E000000")
        
        # Part 2
        control_data_block = hex_to_bytes("28")
        control_data_block += self.build_match_name_entry(index)
        control_data_block += hex_to_bytes("4C495354")
        
        data_payload = hex_to_bytes("746462737464736200000004000000")
        data_payload += hex_to_bytes("03" if invisible else "01")
        data_payload += hex_to_bytes("7464736E000000")
        data_payload += hex_to_bytes(hex(len(text) + 1)[2:].zfill(2))
        data_payload += text.encode('latin-1')
        data_payload += hex_to_bytes("0000") if len(text) % 2 == 0 else hex_to_bytes("00")
        data_payload += hex_to_bytes("746462340000007CBD990001000100000001000400005DA8000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000636461740000002800000000000000000000000000000000000000000000000000000000000000000000000000000000")
        
        control_records = hex(len(data_payload))[2:].zfill(8)
        control_data_block += hex_to_bytes(control_records)
        control_data_block += data_payload
        control_data_block += hex_to_bytes("74646D6E000000")
        
        return (control_record, control_data_block)
    
    def build_ffx_binary(self, control_name: str, match_name: str, controls: List[Dict[str, Any]]) -> bytes:
        """Create the complete FFX file."""
        self.match_name = f"{match_name}-{str(uuid.uuid4())[:4].upper()}"
        
        file_array = []
        file_array.append(hex_to_bytes("52494658"))
        remain1_idx = len(file_array)
        file_array.append(hex_to_bytes("00000000"))
        file_array.append(hex_to_bytes("466146586865616400000010000000030000004400000001010000004C495354"))
        remain2_idx = len(file_array)
        file_array.append(hex_to_bytes("00000000"))
        file_array.append(hex_to_bytes("626573636265736F0000003800000001000000010000000000005DA8001DF8520000000000640064006400643FF00000000000003FF000000000000000000000FFFFFFFF4C495354"))
        file_array.append(hex_to_bytes("000000AC7464737074646F7400000004FFFFFFFF7464706C00000004000000024C495354"))
        file_array.append(hex_to_bytes("00000040746473697464697800000004FFFFFFFF74646D6E000000"))
        file_array.append(hex_to_bytes("2841444245204566666563742050617261646500000000000000000000000000000000000000000000"))
        file_array.append(hex_to_bytes("4C495354000000407464736974646978000000040000000074646D6E000000"))
        file_array.append(hex_to_bytes("28"))
        file_array.append(self.build_match_name_entry("-1", self.match_name))
        file_array.append(hex_to_bytes("7464736E000000"))
        file_array.append(self.build_label_entry(control_name))
        file_array.append(hex_to_bytes("4C495354000000"))
        file_array.append(hex_to_bytes("647464737074646F7400000004FFFFFFFF7464706C00000004000000014C49535400000040746473697464697800000004FFFFFFFF74646D6E000000284144424520456E64206F6620706174682073656E74696E656C000000000000000000000000000000"))
        file_array.append(hex_to_bytes("4C495354"))
        remain3_idx = len(file_array)
        file_array.append(hex_to_bytes("00000000"))
        file_array.append(hex_to_bytes("73737063666E616D000000"))
        file_array.append(hex_to_bytes("30000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"))
        file_array.append(hex_to_bytes("4C495354"))
        remain4_idx = len(file_array)
        file_array.append(hex_to_bytes("00000000"))
        file_array.append(hex_to_bytes("706172547061726E00000004000000"))
        
        control_index = 0
        control_records = []
        control_records.append(self.build_first_control_record(pad4(str(control_index)), True, False))
        control_index += 1
        
        for i, control_def in enumerate(controls):
            is_last_control = (i + 1) == len(controls)
            control_type = control_def.get("type", "")
            
            if control_type == "slider":
                control_records.append(self.build_slider_record(
                    pad4(str(control_index)), is_last_control, control_def["name"],
                    control_def.get("valid_min", 0), control_def.get("valid_max", 100),
                    control_def.get("slider_min", 0), control_def.get("slider_max", 100),
                    control_def.get("default_value", 0), control_def.get("precision", 1),
                    control_def.get("percent", False), control_def.get("pixel", False),
                    control_def.get("keyframes", True), control_def.get("hold", False),
                    control_def.get("invisible", False)
                ))
            elif control_type == "angle":
                control_records.append(self.build_angle_record(
                    pad4(str(control_index)), is_last_control, control_def["name"],
                    control_def.get("default_value", 0),
                    control_def.get("keyframes", True), control_def.get("hold", False)
                ))
            elif control_type == "color":
                control_records.append(self.build_color_record(
                    pad4(str(control_index)), is_last_control, control_def["name"],
                    control_def.get("red", 255), control_def.get("green", 255), control_def.get("blue", 255),
                    control_def.get("keyframes", True), control_def.get("hold", False),
                    control_def.get("invisible", False)
                ))
            elif control_type == "layer":
                control_records.append(self.build_layer_record(
                    pad4(str(control_index)), is_last_control, control_def["name"],
                    control_def.get("default_value", False),
                    control_def.get("keyframes", True), control_def.get("hold", False),
                    control_def.get("invisible", False)
                ))
            elif control_type == "point":
                control_records.append(self.build_point2d_record(
                    pad4(str(control_index)), is_last_control, control_def["name"],
                    control_def.get("percentX", 50), control_def.get("percentY", 50),
                    control_def.get("keyframes", True), control_def.get("hold", False),
                    control_def.get("invisible", False)
                ))
            elif control_type == "point3d":
                control_records.append(self.build_point3d_record(
                    pad4(str(control_index)), is_last_control, control_def["name"],
                    control_def.get("percentX", 50), control_def.get("percentY", 50), control_def.get("percentZ", 0),
                    control_def.get("keyframes", True), control_def.get("hold", False),
                    control_def.get("invisible", False)
                ))
            elif control_type == "dropdown":
                control_records.append(self.build_dropdown_record(
                    pad4(str(control_index)), is_last_control, control_def["name"],
                    control_def.get("content", "Option1|Option2"),
                    control_def.get("default_value", 1),
                    control_def.get("keyframes", True), control_def.get("hold", False),
                    control_def.get("invisible", False)
                ))
            elif control_type == "group":
                control_records.append(self.build_text_record(
                    pad4(str(control_index)), control_def["name"],
                    False, control_def.get("invisible", False)
                ))
            elif control_type == "checkbox":
                control_records.append(self.build_checkbox_record(
                    pad4(str(control_index)), is_last_control, control_def["name"],
                    control_def.get("label", ""),
                    control_def.get("default_value", False),
                    control_def.get("keyframes", True), control_def.get("hold", False),
                    control_def.get("invisible", False)
                ))
            elif control_type == "label":
                control_records.append(self.build_text_record(
                    pad4(str(control_index)), control_def["name"],
                    control_def.get("dim", False), control_def.get("invisible", False)
                ))
            elif control_type == "text":
                control_records.append(self.build_text_record(
                    pad4(str(control_index)), control_def["name"],
                    control_def.get("dim", False), False
                ))
                control_index += 1
                control_records.append(self.build_boundary_record(
                    pad4(str(control_index)), False, is_last_control, control_name
                ))
            elif control_type in ("endgroup", "endLabel"):
                control_records.append(self.build_boundary_record(
                    pad4(str(control_index)), False, is_last_control, control_name
                ))
            
            control_index += 1
        
        file_array.append(hex_to_bytes(pad2(hex(control_index)[2:]) + "74646D6E000000"))
        
        for item in control_records:
            file_array.append(item[0])
        
        par_tparn_end_idx = len(file_array)
        file_array.append(hex_to_bytes("4C495354"))
        remain5_idx = len(file_array)
        file_array.append(hex_to_bytes("00000000"))
        file_array.append(hex_to_bytes("746467707464736200000004000000017464736E"))
        file_array.append(hex_to_bytes("000000"))
        file_array.append(self.build_label_entry(control_name))
        file_array.append(hex_to_bytes("74646D6E000000"))
        
        for item in control_records:
            file_array.append(item[1])
        
        file_array.append(hex_to_bytes("28414442452047726F757020456E640000000000000000000000000000000000000000000000000000"))
        
        # Calculate lengths
        def patch_chunk_size(array_index: int):
            length = sum(len(b) for b in file_array[array_index:])
            hex_length = hex(length)[2:].zfill(8)
            file_array[array_index - 1] = hex_to_bytes(hex_length)
        
        def patch_chunk_span(h_start: int, h_end: int):
            length = sum(len(b) for b in file_array[h_start:h_end - 1])
            hex_length = hex(length)[2:].zfill(8)
            file_array[h_start - 1] = hex_to_bytes(hex_length)
        
        patch_chunk_size(remain1_idx + 1)
        patch_chunk_size(remain2_idx + 1)
        patch_chunk_size(remain3_idx + 1)
        patch_chunk_span(remain4_idx + 1, par_tparn_end_idx + 1)
        patch_chunk_size(remain5_idx + 1)
        
        return b"".join(file_array)


def generate_ffx_file(control_name: str, match_name: str, controls: List[Dict[str, Any]], 
                 output_path: Optional[str] = None) -> str:
    """
    Generate an FFX preset file.
    
    Args:
        control_name: Display name for the effect
        match_name: Internal match name for the effect
        controls: List of control definitions
        output_path: Optional output path. If None, saves to temp folder.
    
    Returns:
        Path to the generated FFX file
    """
    generator = FFXGenerator(control_name, match_name, controls)
    ffx_data = generator.ffx_data
    
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), "GeneratedProcEffect.ffx")
    
    with open(output_path, "wb") as f:
        f.write(ffx_data)
    
    return output_path


# Example usage
if __name__ == "__main__":
    max_layers = 5

    controls = []

    # Distance / strength (per layer level)
    controls.append({
        "type": "slider",
        "name": "Max Distance",
        "default_value": 200.0,
        "valid_min": 0.0,
        "valid_max": 10000.0,
        "slider_min": 0.0,
        "slider_max": 10000.0,
        "precision": 1,
        "percent": False,
        "pixel": False,
        "keyframes": True,
        "hold": False,
        "invisible": False,
    })

    for level in range(1, max_layers + 1):
        controls.append({
            "type": "slider",
            "name": f"Strength L{level}",
            "default_value": 100.0,
            "valid_min": 0.0,
            "valid_max": 1000.0,
            "slider_min": 0.0,
            "slider_max": 1000.0,
            "precision": 1,
            "percent": True,
            "pixel": False,
            "keyframes": True,
            "hold": False,
            "invisible": False,
        })

    # Time remap set
    controls.append({
        "type": "slider",
        "name": "Max Distance Time",
        "default_value": 200.0,
        "valid_min": 0.0,
        "valid_max": 10000.0,
        "slider_min": 0.0,
        "slider_max": 10000.0,
        "precision": 1,
        "percent": False,
        "pixel": False,
        "keyframes": True,
        "hold": False,
        "invisible": False,
    })

    for level in range(1, max_layers + 1):
        controls.append({
            "type": "slider",
            "name": f"Strength Time L{level}",
            "default_value": 100.0,
            "valid_min": 0.0,
            "valid_max": 1000.0,
            "slider_min": 0.0,
            "slider_max": 1000.0,
            "precision": 1,
            "percent": True,
            "pixel": False,
            "keyframes": True,
            "hold": False,
            "invisible": False,
        })

    # Time window
    controls.append({
        "type": "slider",
        "name": "Time Start",
        "default_value": 0.0,
        "valid_min": 0.0,
        "valid_max": 300.0,
        "slider_min": 0.0,
        "slider_max": 300.0,
        "precision": 2,
        "percent": False,
        "pixel": False,
        "keyframes": True,
        "hold": False,
        "invisible": False,
    })
    controls.append({
        "type": "slider",
        "name": "Time End",
        "default_value": 5.0,
        "valid_min": 0.0,
        "valid_max": 300.0,
        "slider_min": 0.0,
        "slider_max": 300.0,
        "precision": 2,
        "percent": False,
        "pixel": False,
        "keyframes": True,
        "hold": False,
        "invisible": False,
    })

    # Scale / rotation strengths
    for level in range(1, max_layers + 1):
        controls.append({
            "type": "slider",
            "name": f"Scale Strength L{level}",
            "default_value": 50.0,
            "valid_min": 0.0,
            "valid_max": 1000.0,
            "slider_min": 0.0,
            "slider_max": 1000.0,
            "precision": 1,
            "percent": True,
            "pixel": False,
            "keyframes": True,
            "hold": False,
            "invisible": False,
        })

    # --- GENERATE FFX FILE FROM CONTROLS ---
    control_name = "Proximity Master"
    match_name = "Pseudo/ProximityMaster"

    ffx_path = generate_ffx_file(
        control_name=control_name,
        match_name=match_name,
        controls=controls,
    )
    
    print(f"FFX saved to: {ffx_path}")