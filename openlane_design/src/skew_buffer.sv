`timescale 1ns / 1ps

module skew_buffer #(
    parameter int DATA_WIDTH = 8,
    parameter int DELAY_CYCLES = 3
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic [DATA_WIDTH-1:0]   din,
    output logic [DATA_WIDTH-1:0]   dout
);

    // 100% Synthesizable ASIC Shift Register Pipeline Array
    logic [DELAY_CYCLES:0][DATA_WIDTH-1:0] shift_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_reg <= '0;
        end else begin
            shift_reg[0] <= din;
            for (int i = 0; i < DELAY_CYCLES; i++) begin
                shift_reg[i+1] <= shift_reg[i];
            end
        end
    end

    // Assign output based on the parameter delay requirement configuration
    assign dout = shift_reg[DELAY_CYCLES];

endmodule
