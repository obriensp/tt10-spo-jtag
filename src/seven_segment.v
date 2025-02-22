/*
 * Copyright (c) 2025 Sean Patrick O'Brien
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none
`timescale 1ns / 1ps

module seven_segment(
  input  wire [3:0] value,
  output wire [6:0] segments
);

  reg [6:0] seg;
  always @(*) begin
    case (value)
    4'h0: seg = 7'b0111111;
    4'h1: seg = 7'b0000110;
    4'h2: seg = 7'b1011011;
    4'h3: seg = 7'b1001111;
    4'h4: seg = 7'b1100110;
    4'h5: seg = 7'b1101101;
    4'h6: seg = 7'b1111101;
    4'h7: seg = 7'b0000111;
    4'h8: seg = 7'b1111111;
    4'h9: seg = 7'b1101111;
    4'hA: seg = 7'b1110111;
    4'hB: seg = 7'b1111100;
    4'hC: seg = 7'b0111001;
    4'hD: seg = 7'b1011110;
    4'hE: seg = 7'b1111001;
    4'hF: seg = 7'b1110001;
    endcase
  end

  assign segments = seg;

endmodule
