`timescale 1ns / 1ps

module systolic_top #(
    parameter int N          = 2,
    parameter int DATA_WIDTH = 8,
    parameter int ACC_WIDTH  = 24,
    parameter int ADDR_WIDTH = 4,
    parameter int DEPTH      = 16
)(
    input  logic                                clk,
    input  logic                                rst_n,
    input  logic                                start,
    // BRAM loading interfaces
    input  logic [N-1:0]                        we_a,
    input  logic [N-1:0]                        we_b,
    input  logic [ADDR_WIDTH-1:0]               ext_addr,
    input  logic [N-1:0][DATA_WIDTH-1:0]        ext_din_a,
    input  logic [N-1:0][DATA_WIDTH-1:0]        ext_din_b,
    // Status and final cleaned outputs
    output logic                                ready,
    output logic                                valid_out,
    output logic [N-1:0][N-1:0][DATA_WIDTH-1:0] denoised_matrix_out
);

    // Internal control signals
    logic                  clr_acc;
    logic                  ctrl_valid_out;
    logic [ADDR_WIDTH-1:0] ctrl_mem_addr;
    logic [ADDR_WIDTH-1:0] active_addr;

    // Internal packed routing networks
    logic [N-1:0][DATA_WIDTH-1:0]       bram_out_a;
    logic [N-1:0][DATA_WIDTH-1:0]       bram_out_b;
    logic [N-1:0][N-1:0][ACC_WIDTH-1:0] raw_matrix_c;

    assign active_addr = ready ? ext_addr : ctrl_mem_addr;

    // 1. FSM controller
    gemm_controller #(
        .ADDR_WIDTH(ADDR_WIDTH),
        .MAX_COUNT(8)
    ) central_ctrl (
        .clk       (clk),
        .rst_n     (rst_n),
        .start     (start),
        .ready     (ready),
        .clr_acc   (clr_acc),
        .mem_addr  (ctrl_mem_addr),
        .valid_out (ctrl_valid_out)
    );

    // 2. Block RAM banks for matrix A
    for (genvar i = 0; i < N; i++) begin : bram_bank_a
        matrix_bram #(
            .DATA_WIDTH(DATA_WIDTH),
            .ADDR_WIDTH(ADDR_WIDTH),
            .DEPTH(DEPTH)
        ) mem_a (
            .clk  (clk),
            .we   (ready ? we_a[i] : 1'b0),
            .addr (active_addr),
            .din  (ext_din_a[i]),
            .dout (bram_out_a[i])
        );
    end

    // 3. Block RAM banks for matrix B
    for (genvar j = 0; j < N; j++) begin : bram_bank_b
        matrix_bram #(
            .DATA_WIDTH(DATA_WIDTH),
            .ADDR_WIDTH(ADDR_WIDTH),
            .DEPTH(DEPTH)
        ) mem_b (
            .clk  (clk),
            .we   (ready ? we_b[j] : 1'b0),
            .addr (active_addr),
            .din  (ext_din_b[j]),
            .dout (bram_out_b[j])
        );
    end

    // 4. Core systolic computing engine
    systolic_array #(
        .N(N),
        .DATA_WIDTH(DATA_WIDTH),
        .ACC_WIDTH(ACC_WIDTH)
    ) computing_core (
        .clk         (clk),
        .rst_n       (rst_n),
        .clr_acc     (clr_acc),
        .raw_in_a    (bram_out_a),
        .raw_in_b    (bram_out_b),
        .array_out_c (raw_matrix_c)
    );

    // 5. Stage 3: spatial denoiser and quantizer output stage
    spatial_denoiser #(
        .N(N),
        .ACC_WIDTH(ACC_WIDTH),
        .OUT_WIDTH(DATA_WIDTH)
    ) output_filter (
        .clk                 (clk),
        .rst_n               (rst_n),
        .valid_in            (ctrl_valid_out),
        .matrix_c_in         (raw_matrix_c),
        .valid_out           (valid_out),
        .denoised_matrix_out (denoised_matrix_out)
    );

endmodule