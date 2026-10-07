import os
import re

def run_dynamic_vivado_pipeline():
    # 1. Take the dynamic matrix parameter N live from the user terminal prompt
    try:
        user_in = input("Enter Parameter N for Matrix Scale (e.g. 2, 3, 4, 8): ")
        N = int(user_in)
    except ValueError:
        print("Invalid number format. Defaulting to baseline N=2.")
        N = 2

    print(f"\n[STEP 1] Re-configuring hardware parameters for N = {N}...")

    # 2. Dynamically overwrite the parameter boundaries inside systolic_top.sv
    top_path = "openlane_design/src/systolic_top.sv"
    if os.path.exists(top_path):
        with open(top_path, 'r') as f:
            content = f.read()
        # Find parameter int N and change its value
        updated_content = re.sub(r'parameter\s+int\s+N\s*=\s*\d+', f'parameter int N          = {N}', content)
        with open(top_path, 'w') as f:
            f.write(updated_content)
        print("         Successfully updated 'systolic_top.sv' parameter boundaries.")

    # 3. Create an automated Tcl Execution Recipe File for Vivado
    tcl_commands = f"""
# Vivado Automated Compilation Recipe for Custom N={N} Execution
open_project [get_projects]
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
"""
    
    with open("run_vivado_flow.tcl", "w") as f:
        f.write(tcl_commands)
    print("[STEP 2] Generated Tcl compilation orchestration script 'run_vivado_flow.tcl'.")

    # 4. Prompt the user to trigger the batch script run step
    print(f"\n========================================================================")
    print(f" READY TO RUN: Execute the line below inside your Vivado Tcl Console:   ")
    print(f"========================================================================")
    print(f" source run_vivado_flow.tcl")
    print(f"========================================================================")

if __name__ == "__main__":
    run_dynamic_vivado_pipeline()
