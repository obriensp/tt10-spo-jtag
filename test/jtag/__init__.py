# SPDX-FileCopyrightText: © 2025 Sean Patrick O'Brien
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, First, RisingEdge, with_timeout, Timer
import logging
from .state import State
from .state_map import StateMap


class JTAG:
    def __init__(self, tck, tms, tdi, tdo, speed=6e6, initial_state=None, *args, **kwargs):
        self.log = logging.getLogger(f'cocotb.{tck._path}')
        self.tck = tck
        self.tms = tms
        self.tdi = tdi
        self.tdo = tdo

        self.tck.value = 0
        self.tms.value = 0
        self.tdi.value = 0

        self._tap_state = initial_state
        self._state_map = StateMap()
        self._half_cycle = Timer(int(1e9 / speed / 2), 'ns')
        self.log.info(f'Starting JTAG')

        super().__init__(*args, **kwargs)

    async def ensure_reset(self):
        self.tms.value = 1

        for i in range(5):
            await self._half_cycle
            self.tck.value = 1
            await self._half_cycle
            self.tck.value = 0

        self._tap_state = State.RESET

    async def _pulse_tck(self):
        await self._half_cycle
        self.tck.value = 1
        await self._half_cycle
        self.tck.value = 0

    async def _move_to_state(self, state):
        assert self._tap_state

        avoid = [] if self._tap_state == State.RESET else [State.RESET]
        path = self._state_map.shortest_path(self._tap_state, state, avoid=avoid)
        assert path, f'No path between {self._tap_state} and {state}'

        for node, tms in path:
            self.tms.value = tms
            await self._half_cycle
            self.tck.value = 1
            await self._half_cycle
            self.tck.value = 0

        self._tap_state = state

    async def _shift(self, bits, is_data):
        await self._move_to_state(State.SHIFT_DR if is_data else State.SHIFT_IR)

        # shift in bits, end in EXIT1_*R
        bit_count = len(bits)
        result_str = ''
        for i, bit in enumerate(bits):
            is_last = i == bit_count - 1
            self.tms.value = 1 if is_last else 0
            self.tdi.value = bit
            await self._pulse_tck()
            result_str = self.tdo.value.binstr + result_str

        self._tap_state = State.EXIT1_DR if is_data else State.EXIT1_IR
        await self._move_to_state(State.SELECT_DR)

        return cocotb.binary.BinaryValue(value=result_str, n_bits=bit_count, bigEndian=False)

    async def shift_ir(self, bits):
        return await self._shift(bits, is_data=False)

    async def shift_dr(self, bits):
        return await self._shift(bits, is_data=True)

    async def runtest(self, cycles=1):
        await self._move_to_state(State.RUNTEST)

        self.tms.value = 0
        for i in range(cycles - 1):
            await self._pulse_tck()

        await self._move_to_state(State.SELECT_DR)

