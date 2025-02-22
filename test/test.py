# SPDX-FileCopyrightText: © 2025 Sean Patrick O'Brien
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer


segments_map = {
    63  : 0x0,
    6   : 0x1,
    91  : 0x2,
    79  : 0x3,
    102 : 0x4,
    109 : 0x5,
    125 : 0x6,
    7   : 0x7,
    127 : 0x8,
    111 : 0x9,
    119 : 0xA,
    124 : 0xB,
    57  : 0xC,
    94  : 0xD,
    121 : 0xE,
    113 : 0xF,
}

@cocotb.test()
async def test_inner_project(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0

    # 1 MHz clock
    clock = Clock(dut.clk, 1, units="us")
    cocotb.start_soon(clock.start())

    # reset
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rst_n.value = 1

    # test counter display; run for 32 cycles to test overflow of 4-bit counter
    dut._log.info('Testing counter')
    for i in range(32):
        await ClockCycles(dut.clk, 1)
        expected_counter = i % 16

        # check the counter register
        assert dut.user_project.counter.value == expected_counter

        # check the 7-segment output
        segments = BinaryValue(value=dut.uo_out.value.binstr, n_bits=8, bigEndian=False)
        decoded = segments_map[segments[6:0].integer]
        assert decoded == expected_counter
    
    # test manually controlling the display value
    dut._log.info('Testing manual display mode')
    for i in reversed(range(16)):
        dut.ui_in.value = BinaryValue(value=i << 1 | 1, n_bits=8, bigEndian=False)
        await Timer(1, units='ns')

        # check the 7-segment output
        segments = BinaryValue(value=dut.uo_out.value.binstr, n_bits=8, bigEndian=False)
        decoded = segments_map[segments[6:0].integer]
        assert decoded == i
