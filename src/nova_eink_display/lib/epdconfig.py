# *****************************************************************************
# * | File        :   epdconfig.py
# * | Author      :   Waveshare team
# * | Function    :   Hardware underlying interface
# * | Info        :
# * ----------------
# * | This version:   V1.2
# * | Date        :   2022-10-29
# * | Info        :
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
# https://github.com/waveshareteam/e-Paper/blob/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd/epdconfig.py
#

import logging
import spidev # type: ignore
import time
from typing import List
from gpiozero import LED, Button # type: ignore

logger = logging.getLogger(__name__)

RST_PIN  = 17
DC_PIN   = 25
# CS_PIN   = 8
BUSY_PIN = 24
PWR_PIN  = 18

class RaspberryPi:
    def __init__(self) -> None:
        self.SPI = spidev.SpiDev()
        self._spi_is_open = False

        self.pin_rst     = LED(RST_PIN)
        self.pin_dc      = LED(DC_PIN)
        # self.pin_cs      = LED(self.CS_PIN)
        self.pin_pwr     = LED(PWR_PIN)
        self.pin_busy    = Button(BUSY_PIN, pull_up=False)

    def digital_write(self, pin: int, value: int) -> None:
        if pin == RST_PIN:
            self.pin_rst.value = value
        elif pin == DC_PIN:
            self.pin_dc.value = value
        elif pin == PWR_PIN:
            self.pin_pwr.value = value
        # elif pin == CS_PIN:
        #     self.pin_cs.value = value

    def digital_read(self, pin: int) -> int:
        if pin == BUSY_PIN:
            return self.pin_busy.value
        if pin == RST_PIN:
            return self.pin_rst.value
        if pin == DC_PIN:
            return self.pin_dc.value
        if pin == PWR_PIN:
            return self.pin_pwr.value
        # if pin == CS_PIN:
        #     return self.pin_cs.value
        return 0

    def delay_ms(self, delaytime: int) -> None:
        time.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data: List[int]) -> None:
        self.SPI.writebytes(data)

    def spi_writebyte2(self, data: List[int]) -> None:
        self.SPI.writebytes2(data)

    def module_init(self) -> int:
        self.pin_pwr.on()

        if not self._spi_is_open:
            self.SPI.open(0, 0)
            self.SPI.max_speed_hz = 4000000
            self.SPI.mode = 0b00
            self._spi_is_open = True
            logger.debug("[EPDCONFIG] SPI initialized")

        return 0

    def module_exit(self) -> None:
        logger.debug("[EPDCONFIG] Shutting down SPI and powering off display")

        if self._spi_is_open:
            self.SPI.close()
            self._spi_is_open = False

        self.pin_rst.off()
        self.pin_dc.off()
        self.pin_pwr.off()

hw = RaspberryPi()

digital_write  = hw.digital_write
digital_read   = hw.digital_read
delay_ms       = hw.delay_ms
spi_writebyte  = hw.spi_writebyte
spi_writebyte2 = hw.spi_writebyte2
module_init    = hw.module_init
module_exit    = hw.module_exit
