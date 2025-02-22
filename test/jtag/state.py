# SPDX-FileCopyrightText: © 2025 Sean Patrick O'Brien
# SPDX-License-Identifier: Apache-2.0

from enum import Enum

class State(Enum):
    RESET=0
    RUNTEST=1
    SELECT_DR=2
    CAPTURE_DR=3
    SHIFT_DR=4
    EXIT1_DR=5
    PAUSE_DR=6
    EXIT2_DR=7
    UPDATE_DR=8
    SELECT_IR=9
    CAPTURE_IR=10
    SHIFT_IR=11
    EXIT1_IR=12
    PAUSE_IR=13
    EXIT2_IR=14
    UPDATE_IR=15
