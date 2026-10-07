`timescale 1ns / 1ps

module skew_buffer #(
    parameter int DATA_WIDTH = 8,
    parameter int DELAY_CYCLES = 0
)(
    input  logic                   clk,
    input  logic                   rst_n,
    input  logic [DATA_WIDTH-1:0]  din,
    output logic [DATA_WIDTH-1:0]  dout
);

    if (DELAY_CYCLES == 0) begin : no_delay
        assign dout = din;
    end else begin : delay_chain
        logic [DELAY_CYCLES-1:0][DATA_WIDTH-1:0] shift_reg;

        always_ff @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                shift_reg <= '0;
            end else begin
                shift_reg[0] <= din;
                for (int i = 1; i < DELAY_CYCLES; i++) begin
                    shift_reg[i] <= shift_reg[i-1];
                end
            end
        end

        assign dout = shift_reg[DELAY_CYCLES-1];
    end

endmodule
