# SPDX-FileCopyrightText: © 2025 Sean Patrick O'Brien
# SPDX-License-Identifier: Apache-2.0

from .state import State

class StateMap:
    def __init__(self, *args, **kwargs):
        self._incoming = dict()
        self._add_transition(State.RESET,      State.RESET,      tms=1)
        self._add_transition(State.RESET,      State.RUNTEST,    tms=0)
        self._add_transition(State.RUNTEST,    State.RUNTEST,    tms=0)
        self._add_transition(State.RUNTEST,    State.SELECT_DR,  tms=1)
        self._add_transition(State.SELECT_DR,  State.SELECT_IR,  tms=1)
        self._add_transition(State.SELECT_DR,  State.CAPTURE_DR, tms=0)
        self._add_transition(State.CAPTURE_DR, State.SHIFT_DR,   tms=0)
        self._add_transition(State.CAPTURE_DR, State.EXIT1_DR,   tms=1)
        self._add_transition(State.SHIFT_DR,   State.SHIFT_DR,   tms=0)
        self._add_transition(State.SHIFT_DR,   State.EXIT1_DR,   tms=1)
        self._add_transition(State.EXIT1_DR,   State.PAUSE_DR,   tms=0)
        self._add_transition(State.EXIT1_DR,   State.UPDATE_DR,  tms=1)
        self._add_transition(State.PAUSE_DR,   State.PAUSE_DR,   tms=0)
        self._add_transition(State.PAUSE_DR,   State.EXIT2_DR,   tms=1)
        self._add_transition(State.EXIT2_DR,   State.SHIFT_DR,   tms=0)
        self._add_transition(State.EXIT2_DR,   State.UPDATE_DR,  tms=1)
        self._add_transition(State.UPDATE_DR,  State.SELECT_DR,  tms=1)
        self._add_transition(State.UPDATE_DR,  State.RUNTEST,    tms=0)
        self._add_transition(State.SELECT_IR,  State.RESET,      tms=1)
        self._add_transition(State.SELECT_IR,  State.CAPTURE_IR, tms=0)
        self._add_transition(State.CAPTURE_IR, State.SHIFT_IR,   tms=0)
        self._add_transition(State.CAPTURE_IR, State.EXIT1_IR,   tms=1)
        self._add_transition(State.SHIFT_IR,   State.SHIFT_IR,   tms=0)
        self._add_transition(State.SHIFT_IR,   State.EXIT1_IR,   tms=1)
        self._add_transition(State.EXIT1_IR,   State.PAUSE_IR,   tms=0)
        self._add_transition(State.EXIT1_IR,   State.UPDATE_IR,  tms=1)
        self._add_transition(State.PAUSE_IR,   State.PAUSE_IR,   tms=0)
        self._add_transition(State.PAUSE_IR,   State.EXIT2_IR,   tms=1)
        self._add_transition(State.EXIT2_IR,   State.SHIFT_IR,   tms=0)
        self._add_transition(State.EXIT2_IR,   State.UPDATE_IR,  tms=1)
        self._add_transition(State.UPDATE_IR,  State.SELECT_DR,  tms=1)
        self._add_transition(State.UPDATE_IR,  State.RUNTEST,    tms=0)
        super().__init__(*args, **kwargs)

    def _add_transition(self, src, dest, tms):
        if not dest in self._incoming:
            self._incoming[dest] = []
        transitions = self._incoming[dest]
        transitions.append((src, tms))

    def _shortest_path_from(self, src, dest, visited, path, avoid):
        if src == dest:
            return path

        min_path = None

        for node, tms in self._incoming[dest]:
            if not node in visited and not node in avoid:
                new_visited = visited.copy()
                new_visited.add(node)
                new_path = path.copy()
                new_path.append((node, tms))
                result = self._shortest_path_from(src, node, new_visited, new_path, avoid)
                if result and (not min_path or len(result) < len(min_path)):
                    min_path = result

        return min_path


    def shortest_path(self, src, dest, avoid=[]):
        path = self._shortest_path_from(src, dest, visited=set(), path=[], avoid=avoid)
        return list(reversed(path)) if path is not None else None
