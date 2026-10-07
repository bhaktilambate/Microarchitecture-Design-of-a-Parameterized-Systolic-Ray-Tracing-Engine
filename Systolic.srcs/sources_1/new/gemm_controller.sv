`timescale 1ns / 1ps

module gemm_controller #(
    parameter int ADDR_WIDTH = 4,
    parameter int MAX_COUNT  = 8
)(
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    start,      // Starts the computation
    output logic                    ready,      // Engine is idle and ready
    output logic                    clr_acc,    // Resets PEs accumulators
    output logic [ADDR_WIDTH-1:0]   mem_addr,   // Memory pointer to drive BRAMs
    output logic                    valid_out   // Signals matrix C calculation is valid
);

    // State definitions using structured enumerated types
    typedef enum logic [1:0] {
        ST_IDLE  = 2'b00,
        ST_CLEAR = 2'b01,
        ST_RUN   = 2'b10,
        ST_DONE  = 2'b11
    } state_t;

    state_t current_state, next_state;
    logic [ADDR_WIDTH-1:0] counter_reg;

    // Sequential State Transition
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            current_state <= ST_IDLE;
            counter_reg   <= '0;
        end else begin
            current_state <= next_state;
            if (current_state == ST_RUN) begin
                counter_reg <= counter_reg + 1;
            end else begin
                counter_reg <= '0;
            end
        end
    end

    // Combinational Logic for Output Generation
    always_comb begin
        next_state = current_state;
        ready      = 1'b0;
        clr_acc    = 1'b0;
        valid_out  = 1'b0;
        mem_addr   = counter_reg;

        case (current_state)
            ST_IDLE: begin
                ready = 1'b1;
                if (start) next_state = ST_CLEAR;
            end
            
            ST_CLEAR: begin
                clr_acc    = 1'b1;
                next_state = ST_RUN;
            end
            
            ST_RUN: begin
                if (counter_reg == (MAX_COUNT - 1)) begin
                    next_state = ST_DONE;
                end
            end
            
            ST_DONE: begin
                valid_out  = 1'b1;
                next_state = ST_IDLE;
            end
            
            default: next_state = ST_IDLE;
        endcase
    end

endmodule
