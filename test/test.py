# SPDX-FileCopyrightText: © 2025 Sean Patrick O'Brien
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer
from jtag import JTAG

from enum import Enum


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


W_IR = 4
W_BSR = 26

class Instruction(Enum):
    IDCODE = BinaryValue(value=0,  n_bits=W_IR, bigEndian=False)
    SAMPLE = BinaryValue(value=1,  n_bits=W_IR, bigEndian=False)
    EXTEST = BinaryValue(value=2,  n_bits=W_IR, bigEndian=False)
    INTEST = BinaryValue(value=3,  n_bits=W_IR, bigEndian=False)
    CLAMP  = BinaryValue(value=4,  n_bits=W_IR, bigEndian=False)
    BYPASS = BinaryValue(value=15, n_bits=W_IR, bigEndian=False)


async def reset_dut(dut):
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


def create_jtag(dut):
    return JTAG(dut.uio_in[4], dut.uio_in[5], dut.uio_in[6], dut.uio_out[7])


@cocotb.test()
async def test_inner_project(dut):
    await reset_dut(dut)

    inner = dut.user_project.inner

    # test counter display; run for 32 cycles to test overflow of 4-bit counter
    dut._log.info('Testing counter')
    for i in range(32):
        await ClockCycles(dut.clk, 1)
        expected_counter = i % 16

        # check the counter register
        assert inner.counter.value == expected_counter

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


@cocotb.test()
async def test_ir(dut):
    await reset_dut(dut)

    jtag = create_jtag(dut)
    await jtag.ensure_reset()

    tap = dut.user_project.tap_sm

    # test all 16 possible IR values
    for ir in range(16):
        captured = await jtag.shift_ir(BinaryValue(value=ir, n_bits=4, bigEndian=False))
        assert tap.ir_q.value == ir
        assert (captured.integer & 0x3) == 0x1


@cocotb.test()
async def test_idcode(dut):
    await reset_dut(dut)

    jtag = create_jtag(dut)
    await jtag.ensure_reset()

    # after reset, IR should be IDCODE
    captured = await jtag.shift_dr(BinaryValue(value=0, n_bits=32, bigEndian=False))
    assert captured.integer == 0x3002AEFD


@cocotb.test()
async def test_bypass(dut):
    await reset_dut(dut)

    jtag = create_jtag(dut)
    await jtag.ensure_reset()

    # set IR to BYPASS
    await jtag.shift_ir(Instruction.BYPASS.value)

    # test that shifting only introduces 1 bit of delay
    pattern = BinaryValue(value=0xFEEDFACE, n_bits=32, bigEndian=False)
    captured = await jtag.shift_dr(pattern)
    assert captured == pattern[30:0] << 1


@cocotb.test()
async def test_sample(dut):
    await reset_dut(dut)

    jtag = create_jtag(dut)
    await jtag.ensure_reset()

    # set IR to SAMPLE/PRELOAD
    await jtag.shift_ir(Instruction.SAMPLE.value)

    # test all 256 input combination values
    for pattern in range(256):
        dut.ui_in.value = pattern
        captured = await jtag.shift_dr(BinaryValue(value=0, n_bits=W_BSR, bigEndian=False))
        assert captured[9:2] == pattern


@cocotb.test()
async def test_extest(dut):
    await reset_dut(dut)

    jtag = create_jtag(dut)
    await jtag.ensure_reset()

    # set IR to EXTEST
    await jtag.shift_ir(Instruction.EXTEST.value)

    # test all 256 output combinations
    for pattern in range(256):
        await jtag.shift_dr(BinaryValue(value=(pattern << 18), n_bits=W_BSR, bigEndian=False))
        assert dut.uo_out.value == pattern
    
    # FIXME: test uio


@cocotb.test()
async def test_intest(dut):
    await reset_dut(dut)

    jtag = create_jtag(dut)
    await jtag.ensure_reset()

    # set IR to SAMPLE/PRELOAD
    await jtag.shift_ir(Instruction.SAMPLE.value)

    # zero out boundary scan register
    await jtag.shift_dr(BinaryValue(value=0, n_bits=W_BSR, bigEndian=False))

    # set IR to INTEST
    await jtag.shift_ir(Instruction.INTEST.value)

    # test that output pins are all zero
    assert dut.uo_out.value == 0
    assert dut.uio_out.value == 0
    assert dut.uio_oe.value == 0

    # test that changes to the input portion of the BSR show up in the output (seven segment) portion, but *not* in the actual output pins
    expected_segment = None
    for pattern in range(17):
        captured = await jtag.shift_dr(BinaryValue(value=((pattern << 1 | 1) << 2), n_bits=W_BSR, bigEndian=False))
        decoded = segments_map[captured[25:18].integer]
        assert dut.uo_out.value == 0
        if expected_segment is not None:
            assert decoded == expected_segment
        expected_segment = pattern


@cocotb.test()
async def test_clamp(dut):
    await reset_dut(dut)

    jtag = create_jtag(dut)
    await jtag.ensure_reset()

    # set IR to SAMPLE/PRELOAD
    await jtag.shift_ir(Instruction.SAMPLE.value)

    # update boundary scan register
    test_value = 0x55
    await jtag.shift_dr(BinaryValue(value=(test_value << 18), n_bits=W_BSR, bigEndian=False))

    # set IR to CLAMP
    await jtag.shift_ir(Instruction.CLAMP.value)

    # test that shifting only introduces 1 bit of delay
    pattern = BinaryValue(value=0xFEEDFACE, n_bits=32, bigEndian=False)
    captured = await jtag.shift_dr(pattern)
    assert captured == pattern[30:0] << 1

    # test that P1B has expected value
    assert dut.uo_out.value == test_value
