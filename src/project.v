/*
 * Copyright (c) 2025 Sean Patrick O'Brien
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

module tt_um_obriensp_jtag (
  input  wire [7:0] ui_in,    // Dedicated inputs
  output wire [7:0] uo_out,   // Dedicated outputs
  input  wire [7:0] uio_in,   // IOs: Input path
  output wire [7:0] uio_out,  // IOs: Output path
  output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
  input  wire       ena,      // always 1 when the design is powered, so you can ignore it
  input  wire       clk,      // clock
  input  wire       rst_n     // reset_n - low to reset
);

  localparam INSTR_IDCODE = 4'd0,
             INSTR_SAMPLE = 4'd1,
             INSTR_EXTEST = 4'd2,
             INSTR_INTEST = 4'd3,
             INSTR_CLAMP  = 4'd4;

  localparam W_IR     = 4,
             W_IDCODE = 32,
             W_BSR    = 26,
             W_MAX    = 32;

  wire tdo_oe;
  wire tck;
  wire reset;
  wire [W_IR-1:0] ir;
  reg bypass;
  wire tdi;
  wire tdo;
  wire runtest;
  wire capture;
  wire shift;
  wire update;
  jtag_tap_sm #(
    .IR_LENGTH(W_IR),
    .INIT_IR(INSTR_IDCODE)
  ) tap_sm(
    .tck_i(uio_in[4]),
    .trst_ni(rst_n),
    .tms_i(uio_in[5]),
    .tdi_i(uio_in[6]),
    .tdo_o(uio_out[7]),
    .tdo_oe_o(uio_oe[7]),

    .tck_o(tck),
    .reset_o(reset),
    .ir_o(ir),
    .bypass_i(bypass),
    .tdi_o(tdi),
    .tdo_i(tdo),
    .runtest_o(runtest),
    .capture_o(capture),
    .shift_o(shift),
    .update_o(update)
  );

  assign uio_out[6:4] = 3'b0;
  assign uio_oe[6:4]  = 3'b0;

  // bypass
  always @(*) begin
    case (ir)
      INSTR_IDCODE: bypass = 1'b0;
      INSTR_SAMPLE: bypass = 1'b0;
      INSTR_EXTEST: bypass = 1'b0;
      INSTR_INTEST: bypass = 1'b0;
      INSTR_CLAMP:  bypass = 1'b1;
      default:      bypass = 1'b1;
    endcase
  end

  // data register capture
  reg [W_MAX-1:0] capture_value;
  always @(*) begin
    case (ir)
      INSTR_IDCODE: capture_value = {{W_MAX-W_IDCODE{1'b0}}, 4'd3, 16'd42, 11'h77E, 1'b1};
      INSTR_SAMPLE: capture_value = {{W_MAX-W_BSR{1'b0}}, bsr_capture_value};
      INSTR_EXTEST: capture_value = {{W_MAX-W_BSR{1'b0}}, bsr_capture_value};
      INSTR_INTEST: capture_value = {{W_MAX-W_BSR{1'b0}}, bsr_capture_value};
      default:      capture_value = {W_MAX{1'b0}};
    endcase
  end

  // shift register
  reg [W_MAX-1:0] shift_q;
  always @(posedge tck or posedge reset) begin
    if (reset)
      shift_q <= {W_MAX{1'b0}};
    else if (capture)
      shift_q <= capture_value;
    else if (shift) begin
      case (ir)
        INSTR_IDCODE: shift_q <= {{W_MAX-W_IDCODE{1'b0}}, tdi, shift_q[W_IDCODE-1:1]};
        INSTR_SAMPLE: shift_q <= {   {W_MAX-W_BSR{1'b0}}, tdi, shift_q[W_BSR-1:1]};
        INSTR_EXTEST: shift_q <= {   {W_MAX-W_BSR{1'b0}}, tdi, shift_q[W_BSR-1:1]};
        INSTR_INTEST: shift_q <= {   {W_MAX-W_BSR{1'b0}}, tdi, shift_q[W_BSR-1:1]};
        default:      shift_q <= {       {W_MAX-2{1'b0}}, tdi, shift_q[1]};
      endcase
    end
  end

  assign tdo = shift_q[0];

  // Boundary Scan Register
  wire [W_BSR-1:0] bsr_capture_value;
  wire  [4:0] sys_leds;
  wire  [2:0] sys_buttons;
  wire  [7:0] sys_p1b;

  wire [7:0] sys_ui_in;
  wire [7:0] sys_uo_out;
  wire [3:0] sys_uio_in;
  wire [3:0] sys_uio_out;
  wire [3:0] sys_uio_oe;
  boundary_scan_register bsr(
    .tck_i(tck),
    .reset_i(reset),
    .ir_sample_preload_i(ir == INSTR_SAMPLE),
    .ir_extest_i(ir == INSTR_EXTEST),
    .ir_intest_i(ir == INSTR_INTEST),
    .ir_clamp_i(ir == INSTR_CLAMP),
    .capture_data_o(bsr_capture_value),
    .update_data_i(shift_q[W_BSR-1:0]),
    .update_i(update),
    .sys_ui_in_o(sys_ui_in),
    .sys_uo_out_i(sys_uo_out),
    .sys_uio_in_o(sys_uio_in),
    .sys_uio_out_i(sys_uio_out),
    .sys_uio_oe_i(sys_uio_oe),
    .pin_ui_in_i(ui_in),
    .pin_uo_out_o(uo_out),
    .pin_uio_in_i(uio_in[3:0]),
    .pin_uio_out_o(uio_out[3:0]),
    .pin_uio_oe_o(uio_oe[3:0])
  );
  
  inner_project inner(
    .ui_in(sys_ui_in),
    .uo_out(sys_uo_out),
    .uio_in(sys_uio_in),
    .uio_out(sys_uio_out),
    .uio_oe(sys_uio_oe),
    .ena(ena),
    .clk(clk),
    .rst_n(rst_n)
  );

endmodule
