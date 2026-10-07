`timescale 1ns / 1ps

module tb_top;

    localparam int N          = 2;
    localparam int DATA_WIDTH = 8;
    localparam int ACC_WIDTH  = 24;
    localparam int ADDR_WIDTH = 4;
    localparam int DEPTH      = 16;

    logic                               clk;
    logic                               rst_n;
    logic                               start;
    logic [N-1:0]                       we_a;
    logic [N-1:0]                       we_b;
    logic [ADDR_WIDTH-1:0]              ext_addr;
    
    // Matched Packed Arrays
    logic [N-1:0][DATA_WIDTH-1:0]       ext_din_a;
    logic [N-1:0][DATA_WIDTH-1:0]       ext_din_b;
    logic [N-1:0][N-1:0][DATA_WIDTH-1:0] matrix_c_out;
    
    logic                               ready;
    logic                               valid_out;

    // Instantiate Unit Under Test (UUT)
    systolic_top #(
        .N(N),
        .DATA_WIDTH(DATA_WIDTH),
        .ACC_WIDTH(ACC_WIDTH),
        .ADDR_WIDTH(ADDR_WIDTH),
        .DEPTH(DEPTH)
    ) uut (
        .clk(clk),
        .rst_n(rst_n),
        .start(start),
        .we_a(we_a),
        .we_b(we_b),
        .ext_addr(ext_addr),
        .ext_din_a(ext_din_a),
        .ext_din_b(ext_din_b),
        .ready(ready),
        .valid_out(valid_out),
        .denoised_matrix_out(matrix_c_out)
    );

    // Continuous 50MHz Clock Generation
    always #10 clk = ~clk;

    initial begin
        // Reset states
        clk       = 0; 
        rst_n     = 0; 
        start     = 0;
        we_a      = '0; 
        we_b      = '0; 
        ext_addr  = '0;
        ext_din_a = '0;
        ext_din_b = '0;

        #40;
        rst_n = 1;
        #20;

        // --- STAGE A: Pre-Load Test Matrices Into BRAMs ---
        // Write Address 0
        ext_addr  = 4'd0;
        we_a      = 4'b1111; 
        we_b      = 4'b1111;
        ext_din_a = {8'd0, 8'd0, 8'd0, 8'd2}; 
        ext_din_b = {8'd0, 8'd0, 8'd0, 8'd3}; 
        #20;

        // Write Address 1
        ext_addr  = 4'd1;
        ext_din_a = {8'd0, 8'd0, 8'd1, 8'd4};
        ext_din_b = {8'd0, 8'd0, 8'd2, 8'd5};
        #20;

        // Turn off write enables
        we_a = '0; 
        we_b = '0;
        #40;

        // --- STAGE B: Fire FSM Execution ---
        start = 1;
        #20;
        start = 0;

        #300;
        $display("Simulation complete!");
        $finish;
    end

endmodule
