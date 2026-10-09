# Microarchitecture Design of a Parameterized Systolic Ray Tracing Engine

## 💡 Project Overview

This project involves the microarchitecture design of a **parameterized systolic ray tracing engine**. Ray tracing is computationally expensive, so the design uses a **systolic array** of processing elements (PEs) to accelerate ray–primitive intersection through regular, pipelined, parallel dataflow. Developed using **Verilog HDL**, the engine is configurable, so array size and datapath width can be scaled to meet different performance and area targets.

<img width="882" height="837" alt="image" src="https://github.com/user-attachments/assets/f998c273-e17b-4d3b-b6e5-ea588113bb46" />

## Key Features

- **Parameterized Design:** Configurable array dimensions and data width without redesigning the core.
- **Systolic Dataflow:** Rays and scene data move rhythmically between neighbouring PEs, reducing memory bandwidth pressure.
- **Pipelined Intersection Datapath:** High throughput through deep pipelining of the ray–primitive intersection logic.
- **Modular RTL:** Reusable PE, control and buffer modules with testbenches.
- **Timing & Resource Analysis:** Frequency and utilization evaluated after synthesis.

## Architecture

The engine is built from a 2D grid of identical processing elements. Rays stream in from one side, scene/primitive data from another, and intersection results flow out at the end of the array.

```
                 Scene / Primitive Data
                   │      │      │
                   ▼      ▼      ▼
 Rays ──►  ┌──────┬──────┬──────┐
           │  PE  │  PE  │  PE  │ ──► Hit Results
 Rays ──►  ├──────┼──────┼──────┤
           │  PE  │  PE  │  PE  │ ──► Hit Results
 Rays ──►  ├──────┼──────┼──────┤
           │  PE  │  PE  │  PE  │ ──► Hit Results
           └──────┴──────┴──────┘
                   ▲
           Control Unit (FSM / scheduling)
```

### Main Blocks

| Block | Description |
| --- | --- |
| **Ray Input Buffer** | Stores incoming rays and feeds them into the array. |
| **Systolic Array** | Grid of PEs performing pipelined intersection computation. |
| **Processing Element (PE)** | Computes a partial intersection test and passes data to its neighbours each cycle. |
| **Control Unit** | Handles scheduling, handshaking and data synchronization. |
| **Output Stage** | Collects hit/miss results (and hit distance). |

### Parameters

| Parameter | Description | Default |
| --- | --- | --- |
| `ARRAY_ROWS` | Number of PE rows | `4` |
| `ARRAY_COLS` | Number of PE columns | `4` |
| `DATA_WIDTH` | Datapath bit-width | `32` |

*(Update block names and parameters to match your RTL.)*

## Tools & Environment

- **Language:** Verilog HDL
- **Synthesis & Simulation:** *(e.g. Xilinx Vivado)*
- **Target Hardware:** *(e.g. Spartan-7 FPGA, if applicable)*
## Conclusion

This project demonstrates how a parameterized systolic microarchitecture can accelerate ray tracing by trading additional hardware resources for higher throughput. Scaling the array increases parallelism and performance at the cost of area, giving designers a flexible knob to match their performance and resource budget.
