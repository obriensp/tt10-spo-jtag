# SPDX-FileCopyrightText: © 2025 Sean Patrick O'Brien
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer
from enum import Enum
from jtag import JTAG
import os

is_gate_level = os.environ.get('GATES') == 'yes'

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
    return JTAG(tck=dut.uio_in[4],
                tms=dut.uio_in[5],
                tdi=dut.uio_in[6],
                tdo=dut.uio_out[7],
                tdo_oe=dut.uio_oe[7])


@cocotb.test()
async def test_inner_project(dut):
    await reset_dut(dut)

    inner = None if is_gate_level else dut.user_project.inner

    # test counter display; run for 32 cycles to test overflow of 4-bit counter
    dut._log.info('Testing counter')
    for i in range(32):
        await ClockCycles(dut.clk, 1)
        expected_counter = i % 16

        if not is_gate_level:
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

    tap = None if is_gate_level else dut.user_project.tap_sm

    # test all 16 possible IR values
    for ir in range(16):
        captured = await jtag.shift_ir(BinaryValue(value=ir, n_bits=4, bigEndian=False))
        assert (captured.integer & 0x3) == 0x1

        if not is_gate_level:
            assert tap.ir_q.value == ir


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

    # NOTE: slice indices for dut.uio_out.value and dut.uio_oe.value are confusing here.
    # cocotb seems to reverse the endianness between handles and their values, but handles don't support slice indexing

    # test all 256 output combinations
    for pattern in range(256):
        await jtag.shift_dr(BinaryValue(value=(pattern << 18), n_bits=W_BSR, bigEndian=False))
        assert dut.uo_out.value == pattern
    
        # verify uio outputs are disabled
        assert dut.uio_oe.value[4:7] == 0

    # enable and test output drivers
    for pattern in range(16):
        await jtag.shift_dr(BinaryValue(value=(((pattern << 4) | 0xF) << 10), n_bits=W_BSR, bigEndian=False))
        assert dut.uio_out.value[4:7] == pattern
    
        # verify uio outputs are enabled
        assert dut.uio_oe.value[4:7] == 0xF
    
    # disable output drivers and test uio inputs
    zeros_bsr = BinaryValue(value=0, n_bits=W_BSR, bigEndian=False)
    await jtag.shift_dr(zeros_bsr)

    for pattern in range(16):
        pv = BinaryValue(value=pattern, n_bits=4, bigEndian=False)
        for i in range(4):
            dut.uio_in[i].value = pv[i].integer

        captured = await jtag.shift_dr(zeros_bsr)
        assert captured[17:14] == pattern
    
        # verify uio outputs are disabled
        assert dut.uio_oe.value[4:7] == 0



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

    # NOTE: slice indices for dut.uio_out.value and dut.uio_oe.value are confusing here.
    # cocotb seems to reverse the endianness between handles and their values, but handles don't support slice indexing

    # test that output pins are all zero
    assert dut.uo_out.value == 0
    assert dut.uio_out.value[4:7] == 0
    assert dut.uio_oe.value[4:7] == 0

    # drive values onto the output pins
    await jtag.shift_dr(BinaryValue(value=0xFFFF << 10, n_bits=W_BSR, bigEndian=False))

    # test that output pins are all ones
    assert dut.uo_out.value == 0xFF
    assert dut.uio_out.value[4:7] == 0xF
    assert dut.uio_oe.value[4:7] == 0xF

    # zero out boundary scan register
    await jtag.shift_dr(BinaryValue(value=0, n_bits=W_BSR, bigEndian=False))

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
    uo_test_value = 0x55
    uio_test_value = 0xA
    bsr = (uo_test_value << 18) | (uio_test_value << 14) | (0xF << 10)
    await jtag.shift_dr(BinaryValue(value=bsr, n_bits=W_BSR, bigEndian=False))

    # set IR to CLAMP
    await jtag.shift_ir(Instruction.CLAMP.value)

    # test that shifting only introduces 1 bit of delay
    pattern = BinaryValue(value=0xFEEDFACE, n_bits=32, bigEndian=False)
    captured = await jtag.shift_dr(pattern)
    assert captured == pattern[30:0] << 1

    # NOTE: slice indices for dut.uio_out.value and dut.uio_oe.value are confusing here.
    # cocotb seems to reverse the endianness between handles and their values, but handles don't support slice indexing
    
    # test that uo has expected value
    assert dut.uo_out.value == uo_test_value
    assert dut.uio_out.value[4:7] == uio_test_value
    assert dut.uio_oe.value[4:7] == 0xF
