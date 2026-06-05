# *****************************************************************************
# * | File        :   epd2in9_V2.py
# * | Author      :   Waveshare team
# * | Function    :   Electronic paper driver
# * | Info        :
# * ----------------
# * | This version:   V1.1
# * | Date        :   2022-08-9
# * | Info        :   python demo
# -----------------------------------------------------------------------------
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# -----------------------------------------------------------------------------
#
# Refactored for readability

import logging
from typing import List, Optional
from PIL import Image
from . import epdconfig

logger = logging.getLogger(__name__)

EPD_WIDTH  = 128
EPD_HEIGHT = 296

GRAY1 = 0xFF # White
GRAY2 = 0xC0 # Light Gray
GRAY3 = 0x80 # Dark Gray
GRAY4 = 0x00 # Blackest

CMD_SW_RESET              = 0x12
CMD_DRIVER_OUTPUT_CTRL    = 0x01
CMD_DATA_ENTRY_MODE       = 0x11
CMD_SET_RAM_X_START_END   = 0x44
CMD_SET_RAM_Y_START_END   = 0x45
CMD_SET_RAM_X_ADDR        = 0x4E
CMD_SET_RAM_Y_ADDR        = 0x4F
CMD_DISPLAY_UPDATE_CTRL   = 0x21
CMD_DISPLAY_UPDATE_CTRL_2 = 0x22
CMD_MASTER_ACTIVATION     = 0x20
CMD_WRITE_RAM             = 0x24
CMD_WRITE_RAM_2           = 0x26
CMD_DEEP_SLEEP            = 0x10

WF_PARTIAL_2IN9 = [
    0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x80, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x40, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x22, 0x22, 0x22, 0x22, 0x22, 0x22, 0x00, 0x00, 0x00,
    0x22, 0x17, 0x41, 0xB0, 0x32, 0x36,
]

WS_20_30 = [
    0x80, 0x66, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00,
    0x10, 0x66, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00,
    0x80, 0x66, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00,
    0x10, 0x66, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x14, 0x08, 0x00, 0x00, 0x00, 0x00, 0x02,
    0x0A, 0x0A, 0x00, 0x0A, 0x0A, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x14, 0x08, 0x00, 0x01, 0x00, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x44, 0x44, 0x44, 0x44, 0x44, 0x44, 0x00, 0x00, 0x00,
    0x22, 0x17, 0x41, 0x00, 0x32, 0x36,
]

Gray4_LUT = [
    0x00, 0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x20, 0x60, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x28, 0x60, 0x14, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x2A, 0x60, 0x15, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x02, 0x00, 0x05, 0x14, 0x00, 0x00,
    0x1E, 0x1E, 0x00, 0x00, 0x00, 0x00, 0x01,
    0x00, 0x02, 0x00, 0x05, 0x14, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x24, 0x22, 0x22, 0x22, 0x23, 0x32, 0x00, 0x00, 0x00,
    0x22, 0x17, 0x41, 0xAE, 0x32, 0x28,
]

WF_FULL = [
    0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x90, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x60, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x19, 0x19, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x24, 0x42, 0x22, 0x22, 0x23, 0x32, 0x00, 0x00, 0x00,
    0x22, 0x17, 0x41, 0xAE, 0x32, 0x38,
]

class EPD:
    def __init__(self) -> None:
        self.reset_pin = epdconfig.RST_PIN
        self.dc_pin    = epdconfig.DC_PIN
        self.busy_pin  = epdconfig.BUSY_PIN
        # self.cs_pin    = epdconfig.CS_PIN

        self.width  = EPD_WIDTH
        self.height = EPD_HEIGHT

        self.GRAY1 = GRAY1
        self.GRAY2 = GRAY2
        self.GRAY3 = GRAY3
        self.GRAY4 = GRAY4

    def reset(self) -> None:
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(50)
        epdconfig.digital_write(self.reset_pin, 0)
        epdconfig.delay_ms(2)
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(50)

    def send_command(self, command: int) -> None:
        epdconfig.digital_write(self.dc_pin, 0)
        # epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([command])
        # epdconfig.digital_write(self.cs_pin, 1)

    def send_data(self, data: int) -> None:
        epdconfig.digital_write(self.dc_pin, 1)
        # epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([data])
        # epdconfig.digital_write(self.cs_pin, 1)

    def send_data_array(self, data: List[int]) -> None:
        epdconfig.digital_write(self.dc_pin, 1)
        # epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte2(data)
        # epdconfig.digital_write(self.cs_pin, 1)

    def wait_until_idle(self) -> None:
        timeout = 0
        while(epdconfig.digital_read(self.busy_pin) == 1):
            epdconfig.delay_ms(10)
            timeout += 1
            if timeout > 400:
                logger.warning("HARDWARE TIMEOUT: e-Paper busy pin is unresponsive. Check GPIO connection!")
                break

    def TurnOnDisplay(self) -> None:
        self.send_command(CMD_DISPLAY_UPDATE_CTRL_2)
        self.send_data(0xc7)
        self.send_command(CMD_MASTER_ACTIVATION)
        self.wait_until_idle()

    def TurnOnDisplay_Partial(self) -> None:
        self.send_command(CMD_DISPLAY_UPDATE_CTRL_2)
        self.send_data(0x0F)
        self.send_command(CMD_MASTER_ACTIVATION)
        self.wait_until_idle()

    def set_lut(self, lut: List[int]) -> None:
        self.send_command(0x32)
        for i in range(153):
            self.send_data(lut[i])
        self.wait_until_idle()
        self.send_command(0x3F)
        self.send_data(lut[153])
        self.send_command(0x03)  # gate voltage
        self.send_data(lut[154])
        self.send_command(0x04)  # source voltage
        self.send_data(lut[155]) # VSH
        self.send_data(lut[156]) # VSH2
        self.send_data(lut[157]) # VSL
        self.send_command(0x2C)  # VCOM
        self.send_data(lut[158])

    def SetWindow(self, x_start: int, y_start: int, x_end: int, y_end: int) -> None:
        self.send_command(CMD_SET_RAM_X_START_END)
        self.send_data((x_start >> 3) & 0xFF)
        self.send_data((x_end >> 3) & 0xFF)
        self.send_command(CMD_SET_RAM_Y_START_END)
        self.send_data(y_start & 0xFF)
        self.send_data((y_start >> 8) & 0xFF)
        self.send_data(y_end & 0xFF)
        self.send_data((y_end >> 8) & 0xFF)

    def SetCursor(self, x: int, y: int) -> None:
        self.send_command(CMD_SET_RAM_X_ADDR)
        self.send_data(x & 0xFF)
        self.send_command(CMD_SET_RAM_Y_ADDR)
        self.send_data(y & 0xFF)
        self.send_data((y >> 8) & 0xFF)

    def init(self) -> int:
        if epdconfig.module_init() != 0:
            return -1
            
        self.reset()
        self.wait_until_idle()
        self.send_command(CMD_SW_RESET)
        self.wait_until_idle()

        self.send_command(CMD_DRIVER_OUTPUT_CTRL)
        self.send_data(0x27)
        self.send_data(0x01)
        self.send_data(0x00)
        self.send_command(CMD_DATA_ENTRY_MODE)
        self.send_data(0x03)
        self.SetWindow(0, 0, self.width-1, self.height-1)
        self.send_command(CMD_DISPLAY_UPDATE_CTRL)
        self.send_data(0x00)
        self.send_data(0x80)
        self.SetCursor(0, 0)
        self.wait_until_idle()
        self.set_lut(WS_20_30)
        return 0

    def init_Fast(self) -> int:
        if epdconfig.module_init() != 0:
            return -1

        self.reset()
        self.wait_until_idle()
        self.send_command(CMD_SW_RESET)
        self.wait_until_idle()

        self.send_command(CMD_DRIVER_OUTPUT_CTRL)
        self.send_data(0x27)
        self.send_data(0x01)
        self.send_data(0x00)
        self.send_command(CMD_DATA_ENTRY_MODE)
        self.send_data(0x03)
        self.SetWindow(0, 0, self.width-1, self.height-1)
        self.send_command(0x3C)
        self.send_data(0x05)
        self.send_command(CMD_DISPLAY_UPDATE_CTRL)
        self.send_data(0x00)
        self.send_data(0x80)
        self.SetCursor(0, 0)
        self.wait_until_idle()
        self.set_lut(WF_FULL)
        return 0

    def init_4Gray(self) -> int:
        if epdconfig.module_init() != 0:
            return -1

        self.reset()
        epdconfig.delay_ms(100)
        self.wait_until_idle()
        self.send_command(CMD_SW_RESET)
        self.wait_until_idle()
        
        self.send_command(CMD_DRIVER_OUTPUT_CTRL)
        self.send_data(0x27)
        self.send_data(0x01)
        self.send_data(0x00)
        self.send_command(CMD_DATA_ENTRY_MODE)
        self.send_data(0x03)
        self.SetWindow(8, 0, self.width, self.height - 1)
        self.send_command(0x3C)
        self.send_data(0x04)
        self.SetCursor(1, 0)
        self.wait_until_idle()
        self.set_lut(Gray4_LUT)
        return 0

    def getbuffer(self, image: Image.Image) -> List[int]:
        img_mono = image.convert('1')
        
        if img_mono.width == self.height and img_mono.height == self.width:
            img_mono = img_mono.transpose(Image.Transpose.ROTATE_90)
            
        return list(bytearray(img_mono.tobytes()))

    def getbuffer_4Gray(self, image: Image.Image) -> List[int]:
        buf = [0xFF] * (int(self.width / 4) * self.height)
        image_gray = image.convert('L')
        imwidth, imheight = image_gray.size
        pixels = image_gray.load()

        assert pixels is not None
        
        i = 0
        if imwidth == self.width and imheight == self.height:
            for y in range(imheight):
                for x in range(imwidth):
                    if pixels[x, y] == 0xC0: pixels[x, y] = 0x80
                    elif pixels[x, y] == 0x80: pixels[x, y] = 0x40
                    i += 1
                    if i % 4 == 0:
                        buf[int((x + (y * self.width))/4)] = ((pixels[x-3, y]&0xc0) | (pixels[x-2, y]&0xc0)>>2 | (pixels[x-1, y]&0xc0)>>4 | (pixels[x, y]&0xc0)>>6) # type: ignore
        elif imwidth == self.height and imheight == self.width:
            for x in range(imwidth):
                for y in range(imheight):
                    newx = y
                    newy = self.height - x - 1
                    if pixels[x, y] == 0xC0: pixels[x, y] = 0x80
                    elif pixels[x, y] == 0x80: pixels[x, y] = 0x40
                    i += 1
                    if i % 4 == 0:
                        buf[int((newx + (newy * self.width))/4)] = ((pixels[x, y-3]&0xc0) | (pixels[x, y-2]&0xc0)>>2 | (pixels[x, y-1]&0xc0)>>4 | (pixels[x, y]&0xc0)>>6) # type: ignore
        return buf

    def display(self, image_buffer: Optional[List[int]]) -> None:
        if image_buffer is None: return
        self.send_command(CMD_WRITE_RAM)
        self.send_data_array(image_buffer)
        self.TurnOnDisplay()

    def display_Base(self, image_buffer: Optional[List[int]]) -> None:
        if image_buffer is None: return

        self.send_command(CMD_WRITE_RAM)
        self.send_data_array(image_buffer)

        self.send_command(CMD_WRITE_RAM_2)
        self.send_data_array(image_buffer)

        self.TurnOnDisplay()

    def display_4Gray(self, image_buffer: Optional[List[int]]) -> None:
        if image_buffer is None: return

        self.send_command(CMD_WRITE_RAM)
        for i in range(4736):
            temp3 = 0
            for j in range(2):
                temp1 = image_buffer[i*2+j]
                for k in range(2):
                    temp2 = temp1 & 0xC0
                    if temp2 == 0xC0: temp3 |= 0x00
                    elif temp2 == 0x00: temp3 |= 0x01
                    elif temp2 == 0x80: temp3 |= 0x01
                    else: temp3 |= 0x00
                    temp3 <<= 1

                    temp1 <<= 2
                    temp2 = temp1 & 0xC0
                    if temp2 == 0xC0: temp3 |= 0x00
                    elif temp2 == 0x00: temp3 |= 0x01
                    elif temp2 == 0x80: temp3 |= 0x01
                    else: temp3 |= 0x00
                    if j != 1 or k != 1: temp3 <<= 1
                    temp1 <<= 2
            self.send_data(temp3)

        self.send_command(CMD_WRITE_RAM_2)
        for i in range(4736):
            temp3 = 0
            for j in range(2):
                temp1 = image_buffer[i*2+j]
                for k in range(2):
                    temp2 = temp1 & 0xC0
                    if temp2 == 0xC0: temp3 |= 0x00
                    elif temp2 == 0x00: temp3 |= 0x01
                    elif temp2 == 0x80: temp3 |= 0x00
                    else: temp3 |= 0x01
                    temp3 <<= 1
                    
                    temp1 <<= 2
                    temp2 = temp1 & 0xC0
                    if temp2 == 0xC0: temp3 |= 0x00
                    elif temp2 == 0x00: temp3 |= 0x01
                    elif temp2 == 0x80: temp3 |= 0x00
                    else: temp3 |= 0x01
                    if j != 1 or k != 1: temp3 <<= 1
                    temp1 <<= 2
            self.send_data(temp3)

        self.TurnOnDisplay()

    def display_Partial(self, image_buffer: Optional[List[int]]) -> None:
        if image_buffer is None: return
        self.reset()

        self.set_lut(WF_PARTIAL_2IN9)
        self.send_command(0x37)
        self.send_data_array([0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 0x00])

        self.send_command(0x3C)
        self.send_data(0x80)
        self.send_command(CMD_DISPLAY_UPDATE_CTRL_2)
        self.send_data(0xC0)
        self.send_command(CMD_MASTER_ACTIVATION)
        self.wait_until_idle()

        self.SetWindow(0, 0, self.width - 1, self.height - 1)
        self.SetCursor(0, 0)

        self.send_command(CMD_WRITE_RAM)
        self.send_data_array(image_buffer)
        self.TurnOnDisplay_Partial()

    def Clear(self, color: int = 0xFF) -> None:
        buf_size = int((self.width / 8) * self.height)
        
        self.send_command(CMD_WRITE_RAM)
        self.send_data_array([color] * buf_size)
        self.TurnOnDisplay()
        
        self.send_command(CMD_WRITE_RAM_2)
        self.send_data_array([color] * buf_size)
        self.TurnOnDisplay()

    def sleep(self) -> None:
        self.send_command(CMD_DEEP_SLEEP)
        self.send_data(0x01)
        epdconfig.delay_ms(2000)
        epdconfig.module_exit()
