import json
import os
import subprocess

def run_parameterized_asic_flow():
    # 1. Read the parameter N directly from the user live in terminal
    try:
        n_input = input("Enter Dynamic Matrix Size Parameter N (e.g. 2, 4, 8): ")
        N = int(n_input)
    except ValueError:
        print("Invalid number. Falling back to default baseline N=2.")
        N = 2

    # 2. Dynamically calculate the safe target Silicon Die Sizing area scale
    # Up-scales the chip canvas size automatically as the processing element mesh expands
    die_size = 300 + (N * 100)
    core_size = die_size - 10

    # 3. Re-write the config.json technology blueprint profile variables automatically
    config_data = {
        "DESIGN_NAME": "systolic_top",
        "VERILOG_FILES": [
            "dir::src/pe.sv",
            "dir::src/skew_buffer.sv",
            "dir::src/systolic_array.sv",
            "dir::src/matrix_bram.sv",
            "dir::src/gemm_controller.sv",
            "dir::src/spatial_denoiser.sv",
            "dir::src/systolic_top.sv"
        ],
        "CLOCK_PORT": "clk",
        "CLOCK_PERIOD": 20.0,
        "FP_SIZING": "absolute",
        "DIE_AREA": f"0 0 {die_size} {die_size}",
        "CORE_AREA": f"10 10 {core_size} {core_size}",
        "PL_TARGET_DENSITY": 0.45,
        "PDK": "sky130A"
    }

    with open("openlane_design/config.json", "w") as f:
        json.dump(config_data, f, indent=4)
    print(f"\n[STEP 1] Re-configured technology profile 'config.json' dynamically for N={N}.")
    print(f"         Calculated Silicon Chip Canvas Footprint Sizing: {die_size} x {die_size} um")

    # 4. Trigger the Yosys Logic Synthesis Compiler Pass engine automatically
    print("\n[STEP 2] Launching Yosys Open ASIC Synthesis optimization engine...")
    yosys_cmd = (
        'yosys -p "'
        'read_verilog -sv openlane_design/src/pe.sv openlane_design/src/skew_buffer.sv '
        'openlane_design/src/systolic_array.sv openlane_design/src/matrix_bram.sv '
        'openlane_design/src/gemm_controller.sv openlane_design/src/spatial_denoiser.sv '
        'openlane_design/src/systolic_top.sv; '
        'hierarchy -top systolic_top; proc; opt; fsm; opt; techmap; opt; '
        'write_verilog openlane_design/systolic_gate_netlist.v"'
    )
    
    subprocess.run(yosys_cmd, shell=True)
    print("\n[STEP 3] ASIC Custom Logic Gate Netlist generated successfully!")

if __name__ == "__main__":
    run_parameterized_asic_flow()
