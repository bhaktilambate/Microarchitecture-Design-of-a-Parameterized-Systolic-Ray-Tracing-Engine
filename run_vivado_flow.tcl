# Vivado Automated Compilation Recipe for Custom N=5 Execution
reset_run synth_1
reset_run impl_1

# Launch Live Behavioral Logic Waveform Simulation
launch_simulation
run all

# Launch Full Automation Synthesis and Physical Device Routing
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1

# Automatically open the finished physical chip layout canvas view
open_run impl_1
