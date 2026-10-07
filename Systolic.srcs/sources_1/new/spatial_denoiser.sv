`timescale 1ns / 1ps

module spatial_denoiser #(
    parameter int N          = 4,
    parameter int ACC_WIDTH  = 24,
    parameter int OUT_WIDTH  = 8
)(
    input  logic                               clk,
    input  logic                               rst_n,
    input  logic                               valid_in,
    input  logic [N-1:0][N-1:0][ACC_WIDTH-1:0] matrix_c_in,
    output logic                               valid_out,
    output logic [N-1:0][N-1:0][OUT_WIDTH-1:0] denoised_matrix_out
);

    // Compute denoising and quantization combinational logic blocks
    logic [N-1:0][N-1:0][OUT_WIDTH-1:0] next_denoised_matrix;

    always_comb begin
        next_denoised_matrix = '0;
        for (int r = 0; r < N; r++) begin
            for (int c = 0; c < N; c++) begin
                // 1. Denoising/ReLU: Clip negative accumulator noise to 0
                if (matrix_c_in[r][c][ACC_WIDTH-1] == 1'b1) begin
                    next_denoised_matrix[r][c] = '0;
                end
                // 2. Quantization: Clip values exceeding 8-bit maximum (255)
                else if (matrix_c_in[r][c] > 24'd255) begin
                    next_denoised_matrix[r][c] = 8'hFF;
                end
                // 3. Normal Pass: Compress safely to standard 8-bit space
                else begin
                    next_denoised_matrix[r][c] = matrix_c_in[r][c][OUT_WIDTH-1:0];
                end
            end
        end
    end

    // Sequential clean pipeline register stage
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            denoised_matrix_out <= '0;
            valid_out           <= 1'b0;
        end else begin
            valid_out           <= valid_in;
            denoised_matrix_out <= next_denoised_matrix;
        end
    end

endmodule
