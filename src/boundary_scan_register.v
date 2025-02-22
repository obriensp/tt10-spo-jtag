/*
 * Copyright (c) 2025 Sean Patrick O'Brien
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

module boundary_scan_register(
  input  wire        tck_i,
  input  wire        reset_i,

  input  wire        ir_sample_preload_i,
  input  wire        ir_extest_i,
  input  wire        ir_intest_i,
  input  wire        ir_clamp_i,

  output wire [25:0] capture_data_o,
  input  wire [25:0] update_data_i,
  input  wire        update_i,

  output wire  [7:0] sys_ui_in_o,
  inout  wire  [7:0] sys_uo_out_i,
  output wire  [3:0] sys_uio_in_o,
  input  wire  [3:0] sys_uio_out_i,
  input  wire  [3:0] sys_uio_oe_i,

  input  wire  [7:0] pin_ui_in_i,
  output wire  [7:0] pin_uo_out_o,
  input  wire  [3:0] pin_uio_in_i,
  output wire  [3:0] pin_uio_out_o,
  output wire  [3:0] pin_uio_oe_o
);

  reg [25:0] values;


  // use negative edge-triggered flops
  // 8.8.1 Rule D.2: "[output pins] shall change only on the falling edge of TCK in the Update-DR controller state"
  always @(negedge tck_i or posedge reset_i) begin
    if (reset_i)
      values <= 26'b0;
    else if (update_i && (ir_sample_preload_i || ir_extest_i || ir_intest_i))
      values <= update_data_i;
  end

  wire control_output = ir_extest_i || ir_intest_i || ir_clamp_i;
  wire control_input  = ir_intest_i;

  assign capture_data_o = {
    ir_extest_i ? 8'b0 : sys_uo_out_i,
    ir_extest_i ? 4'b0 : sys_uio_out_i, // FIXME: bidir
    ir_extest_i ? 4'b0 : sys_uio_oe_i,
    ir_intest_i ? 8'b0 : pin_ui_in_i,
    2'b11 // FIXME: rst_n and clk
  };

  assign pin_uo_out_o  = control_output ? values[25:18] : sys_uo_out_i;
  assign pin_uio_out_o = control_output ? values[17:14] : sys_uio_out_i;
  assign pin_uio_oe_o  = control_output ? values[13:10] : sys_uio_oe_i;

  assign sys_ui_in_o  = control_input ? values[9:2]   : pin_ui_in_i;
  assign sys_uio_in_o = control_input ? values[17:14] : pin_uio_in_i;

endmodule
