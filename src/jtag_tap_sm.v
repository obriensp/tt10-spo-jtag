`default_nettype none

module jtag_tap_sm #(
  parameter IR_LENGTH = 4,
  parameter INIT_IR = {IR_LENGTH{1'b0}}
)(
  input  wire       tck_i,
  input  wire       trst_ni,
  input  wire       tms_i,
  input  wire       tdi_i,
  output wire       tdo_o,
  output wire       tdo_oe_o,

  output wire       tck_o,
  output wire       reset_o,
  output wire [3:0] ir_o,     // contents of the IR
  input  wire       bypass_i, // high if ir_o is not handled by client
  output wire       tdi_o,    // TDI to client
  input  wire       tdo_i,    // TDO from client,
  output wire       runtest_o,
  output wire       capture_o,
  output wire       shift_o,
  output wire       update_o
);

  // State machine
  localparam STATE_RESET      = 0,
             STATE_IDLE       = 1,
             STATE_SELECT_DR  = 2,
             STATE_CAPTURE_DR = 3,
             STATE_SHIFT_DR   = 4,
             STATE_EXIT1_DR   = 5,
             STATE_PAUSE_DR   = 6,
             STATE_EXIT2_DR   = 7,
             STATE_UPDATE_DR  = 8,
             STATE_SELECT_IR  = 9,
             STATE_CAPTURE_IR = 10,
             STATE_SHIFT_IR   = 11,
             STATE_EXIT1_IR   = 12,
             STATE_PAUSE_IR   = 13,
             STATE_EXIT2_IR   = 14,
             STATE_UPDATE_IR  = 15;

  reg [3:0] state_q;
  reg [3:0] state_d;

  always @(posedge tck_i or negedge trst_ni) begin
    if (~trst_ni)
      state_q <= STATE_RESET;
    else
      state_q <= state_d;
  end

  always @(*) begin
    case (state_q)
      STATE_RESET: state_d      = tms_i ? STATE_RESET     : STATE_IDLE;
      STATE_IDLE:       state_d = tms_i ? STATE_SELECT_DR : STATE_IDLE;
      STATE_SELECT_DR:  state_d = tms_i ? STATE_SELECT_IR : STATE_CAPTURE_DR;
      STATE_CAPTURE_DR: state_d = tms_i ? STATE_EXIT1_DR  : STATE_SHIFT_DR;
      STATE_SHIFT_DR:   state_d = tms_i ? STATE_EXIT1_DR  : STATE_SHIFT_DR;
      STATE_EXIT1_DR:   state_d = tms_i ? STATE_UPDATE_DR : STATE_PAUSE_DR;
      STATE_PAUSE_DR:   state_d = tms_i ? STATE_EXIT2_DR  : STATE_PAUSE_DR;
      STATE_EXIT2_DR:   state_d = tms_i ? STATE_UPDATE_DR : STATE_SHIFT_DR;
      STATE_UPDATE_DR:  state_d = tms_i ? STATE_SELECT_DR : STATE_IDLE;
      STATE_SELECT_IR:  state_d = tms_i ? STATE_RESET     : STATE_CAPTURE_IR;
      STATE_CAPTURE_IR: state_d = tms_i ? STATE_EXIT1_IR  : STATE_SHIFT_IR;
      STATE_SHIFT_IR:   state_d = tms_i ? STATE_EXIT1_IR  : STATE_SHIFT_IR;
      STATE_EXIT1_IR:   state_d = tms_i ? STATE_UPDATE_IR : STATE_PAUSE_IR;
      STATE_PAUSE_IR:   state_d = tms_i ? STATE_EXIT2_IR  : STATE_PAUSE_IR;
      STATE_EXIT2_IR:   state_d = tms_i ? STATE_UPDATE_IR : STATE_SHIFT_IR;
      STATE_UPDATE_IR:  state_d = tms_i ? STATE_SELECT_DR : STATE_IDLE;
    endcase
  end

  // Instruction Register
  localparam INSTR_BYPASS = {IR_LENGTH{1'b1}};

  reg [3:0] ir_q;
  reg [3:0] ir_shift_q;
  always @(posedge tck_i or negedge trst_ni) begin
    if (~trst_ni)
      ir_q <= INIT_IR;
    else if (state_q == STATE_RESET)
      ir_q <= INIT_IR;
    else if (state_q == STATE_UPDATE_IR)
      ir_q <= ir_shift_q;
  end

  always @(posedge tck_i or negedge trst_ni) begin
    if (~trst_ni)
      ir_shift_q <= 4'b0;
    else if (state_q == STATE_RESET)
      ir_shift_q <= 4'b0;
    else if (state_q == STATE_CAPTURE_IR)
      ir_shift_q <= {ir_q[3:2], 2'b01};
    else if (state_q == STATE_SHIFT_IR)
      ir_shift_q <= {tdi_i, ir_shift_q[3:1]};
  end

  // BYPASS Register
  wire should_bypass = ir_q == INSTR_BYPASS || bypass_i;
  reg bypass_shift_q;
  always @(posedge tck_i or negedge trst_ni) begin
    if (~trst_ni)
      bypass_shift_q <= 1'b0;
    else if (state_q == STATE_RESET)
      bypass_shift_q <= 1'b0;
    else if (state_q == STATE_CAPTURE_DR && should_bypass)
      bypass_shift_q <= 1'b0;
    else if (state_q == STATE_SHIFT_DR && should_bypass)
      bypass_shift_q <= tdi_i;
  end

  // TDO Mux and Timing
  reg tdo_q;
  reg tdo_d;

  // tdo is updated on the falling edge of TCK
  always @(negedge tck_i or negedge trst_ni) begin
    if (~trst_ni)
      tdo_q <= 1'b0;
    else if (state_q == STATE_RESET)
      tdo_q <= 1'b0;
    else
      tdo_q <= tdo_d;
  end

  always @(*) begin
    if (state_q == STATE_SHIFT_IR)
      tdo_d = ir_shift_q[0];
    else if (state_q == STATE_SHIFT_DR)
      tdo_d = should_bypass ? bypass_shift_q : tdo_i;
    else
      tdo_d = 1'b0;
  end

  // register the reset output to prevent glitches
  reg reset_q;
  always @(posedge tck_i or negedge trst_ni) begin
    if (~trst_ni)
      reset_q <= 1'b1;
    else if (state_d == STATE_RESET)
      reset_q <= 1'b1;
    else
      reset_q <= 1'b0;
  end

  assign tdo_o     = tdo_q;
  assign tdo_oe_o  = state_q == STATE_SHIFT_IR || state_q == STATE_SHIFT_DR;

  assign tck_o     = tck_i;
  assign ir_o      = ir_q;
  assign tdi_o     = tdi_i;
  assign reset_o   = reset_q;
  assign runtest_o = state_q == STATE_IDLE;
  assign capture_o = state_q == STATE_CAPTURE_DR;
  assign shift_o   = state_q == STATE_SHIFT_DR;
  assign update_o  = state_q == STATE_UPDATE_DR;
endmodule
