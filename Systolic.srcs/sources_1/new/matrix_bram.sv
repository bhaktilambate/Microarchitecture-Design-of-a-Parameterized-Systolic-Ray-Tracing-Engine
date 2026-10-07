`timescale 1ns / 1ps

module matrix_bram #(
    parameter int DATA_WIDTH = 8,
    parameter int ADDR_WIDTH = 4,
    parameter int DEPTH      = 16
)(
    input  logic                    clk,
    input  logic                    we,      // Write Enable (1 = Write, 0 = Read)
    input  logic [ADDR_WIDTH-1:0]   addr,    // Memory Address pointer
    input  logic [DATA_WIDTH-1:0]   din,     // Input data to write
    output logic [DATA_WIDTH-1:0]   dout     // Output data read out
);

    // Core Memory Array Declaration
    logic [DATA_WIDTH-1:0] ram [DEPTH-1:0];

    always_ff @(posedge clk) begin
        if (we) begin
            ram[addr] <= din;
        end
        dout <= ram[addr]; // Synchronous read behavior
    end

endmodule
