`timescale 1ns / 1ps

module pe #(
    parameter int DATA_WIDTH = 8,
    parameter int ACC_WIDTH  = 24
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    clr_acc, 
    input  logic [DATA_WIDTH-1:0]   in_a,    
    input  logic [DATA_WIDTH-1:0]   in_b,    
    output logic [DATA_WIDTH-1:0]   out_a,   
    output logic [DATA_WIDTH-1:0]   out_b,   
    output logic [ACC_WIDTH-1:0]    out_c    
);

    logic [ACC_WIDTH-1:0] acc_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            acc_reg <= '0;
            out_a   <= '0;
            out_b   <= '0;
        end else begin
            out_a <= in_a; 
            out_b <= in_b;
            
            if (clr_acc) begin
                acc_reg <= '0;
            end else begin
                acc_reg <= acc_reg + (in_a * in_b);
            end
        end
    end

    assign out_c = acc_reg;

endmodule
