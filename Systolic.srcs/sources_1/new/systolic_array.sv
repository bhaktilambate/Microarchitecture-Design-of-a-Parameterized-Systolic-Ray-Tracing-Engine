`timescale 1ns / 1ps

module systolic_array #(
    parameter int N          = 4, 
    parameter int DATA_WIDTH = 8,
    parameter int ACC_WIDTH  = 24
)(
    input  logic                               clk,
    input  logic                               rst_n,
    input  logic                               clr_acc,
    input  logic [N-1:0][DATA_WIDTH-1:0]       raw_in_a, 
    input  logic [N-1:0][DATA_WIDTH-1:0]       raw_in_b, 
    output logic [N-1:0][N-1:0][ACC_WIDTH-1:0] array_out_c 
);

    logic [N-1:0][DATA_WIDTH-1:0] skewed_in_a;
    logic [N-1:0][DATA_WIDTH-1:0] skewed_in_b;

    generate
        for (genvar r = 0; r < N; r++) begin : skew_a
            skew_buffer #(
                .DATA_WIDTH(DATA_WIDTH),
                .DELAY_CYCLES(r)
            ) sb_a (
                .clk(clk),
                .rst_n(rst_n),
                .din(raw_in_a[r]),
                .dout(skewed_in_a[r])
            );
        end
    endgenerate

    generate
        for (genvar c = 0; c < N; c++) begin : skew_b
            skew_buffer #(
                .DATA_WIDTH(DATA_WIDTH),
                .DELAY_CYCLES(c)
            ) sb_b (
                .clk(clk),
                .rst_n(rst_n),
                .din(raw_in_b[c]),
                .dout(skewed_in_b[c])
            );
        end
    endgenerate

    logic [N-1:0][N:0][DATA_WIDTH-1:0] horizontal_wires;
    logic [N:0][N-1:0][DATA_WIDTH-1:0] vertical_wires;

    generate
        for (genvar i = 0; i < N; i++) begin : bind_edges
            assign horizontal_wires[i][0] = skewed_in_a[i];
            assign vertical_wires[0][i]   = skewed_in_b[i];
        end
    endgenerate

    generate
        for (genvar row = 0; row < N; row++) begin : row_loop
            for (genvar col = 0; col < N; col++) begin : col_loop
                pe #(
                    .DATA_WIDTH(DATA_WIDTH),
                    .ACC_WIDTH(ACC_WIDTH)
                ) pe_node (
                    .clk(clk),
                    .rst_n(rst_n),
                    .clr_acc(clr_acc),
                    .in_a(horizontal_wires[row][col]),
                    .in_b(vertical_wires[row][col]),
                    .out_a(horizontal_wires[row][col+1]),
                    .out_b(vertical_wires[row+1][col]),
                    .out_c(array_out_c[row][col])
                );
            end
        end
    endgenerate

endmodule
