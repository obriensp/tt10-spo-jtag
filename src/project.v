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
  reg [3:0] counter;
  always @(posedge clk or negedge rst_n) begin
    if (~rst_n)
      counter <= 4'b0;
    else
      counter <= counter + 1;
  end

  wire output_mode = ui_in[0];
  wire [3:0] input_value = ui_in[4:1];
  wire [3:0] display_value = output_mode ? input_value : counter;

  seven_segment seg(
    .value(display_value),
    .segments(uo_out[6:0])
  );

  assign uo_out[7] = 1'b0;
  assign uio_out = 0;
  assign uio_oe  = 0;

  // List all unused inputs to prevent warnings
  wire _unused = &{ena, 1'b0};

endmodule
