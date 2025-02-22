read_sdc $::env(SCRIPTS_DIR)/base.sdc

# JTAG clock
create_clock [get_ports {uio_in[4]}] -name jtag_clk -period 10
set_clock_uncertainty $::env(CLOCK_UNCERTAINTY_CONSTRAINT) jtag_clk
set_clock_transition $::env(CLOCK_TRANSITION_CONSTRAINT) jtag_clk

set_false_path -from [get_clocks clk] -to [get_clocks jtag_clk]
set_false_path -from [get_clocks jtag_clk] -to [get_clocks clk]

set_propagated_clock [all_clocks]