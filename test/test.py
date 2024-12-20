# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import os
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

N = 128
ND8 = N // 8

SERIAL_WEIGHTS = True
WAIT_REGISTER_INPUTS_OUTPUTS = 3

async def set_weights(dut, weights, n=N):
    if SERIAL_WEIGHTS:
        for i in range(n):
            dut.uio_in.value = weights
            await ClockCycles(dut.clk, 1)
    else:
        dut.uio_in.value = 1
        for i in range(n//4):
            dut.ui_in.value = weights | (weights << 2) | (weights << 4) | (weights << 6)
            await ClockCycles(dut.clk, 1)
        dut.uio_in.value = 0

async def execute(dut, input):
    dut.ui_in.value = input
    await ClockCycles(dut.clk, WAIT_REGISTER_INPUTS_OUTPUTS)

def get_output(dut):
    value = dut.out.value.integer
    value &= 0xFFFF  # Mask to 16 bits
    if value & 0x8000:
        value -= 0x10000
    return value

async def test_popcount(dut, popcount, bits):
    def population_count(n: int) -> int:
        count = 0
        while n:
            count += n & 1
            n >>= 1
        return count
    def set_every_2nd_bit(n):
        v = 0
        for k in range(bits//2):
            v = (v << 2) | 1
        return v
    def set_rightmost_bits(n):
        return (1 << n) - 1 # Generate a bitmask with the N rightmost bits set

    dut._log.info("Validate low 12 bit")
    for i in range(0xFFF):
        popcount.data.value = i
        await ClockCycles(dut.clk, 1)
        assert popcount.count.value == population_count(i)

    dut._log.info("Validate in 8-bit chunks")
    for j in range(bits//8):
        for i in range(0xFF):
            popcount.data.value = i << (j*8)
            await ClockCycles(dut.clk, 1)
            assert popcount.count.value == population_count(i)

    dut._log.info("Checker patterns")
    v = set_every_2nd_bit(bits)
    for i in range(bits):
        popcount.data.value = v
        await ClockCycles(dut.clk, 1)
        assert popcount.count.value == population_count(v)
        v >>= 1

    v = set_every_2nd_bit(bits)
    for i in range(bits):
        popcount.data.value = v
        await ClockCycles(dut.clk, 1)
        assert popcount.count.value == population_count(v)
        v &= ~(1 << i)

    dut._log.info("Fill pattern")
    for j in range(bits-1):
        v = set_rightmost_bits(j)
        for i in range(bits):
            popcount.data.value = v
            await ClockCycles(dut.clk, 1)
            assert popcount.count.value == population_count(v)
            v >>= 1

@cocotb.test()
async def test_pop32(dut):
    if os.getenv('GATES'):
        dut._log.info("Skipping in GATE mode")
        return

    dut._log.info("Start")
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    await ClockCycles(dut.clk, 1)

    await test_popcount(dut, dut.test_pop32, 32)

@cocotb.test()
async def test_pop64(dut):
    if os.getenv('GATES'):
        dut._log.info("Skipping in GATE mode")
        return

    dut._log.info("Start")
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    await ClockCycles(dut.clk, 1)

    await test_popcount(dut, dut.test_pop64, 64)

@cocotb.test()
async def test_pop128(dut):
    if os.getenv('GATES'):
        dut._log.info("Skipping in GATE mode")
        return

    dut._log.info("Start")
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    await ClockCycles(dut.clk, 1)

    await test_popcount(dut, dut.test_pop128, 128)

@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    # reset weights
    dut.ui_in.value = 0
    await ClockCycles(dut.clk, 128)

    dut._log.info("Test project behavior")

    input = 1

    await set_weights(dut, 0b00)
    await execute(dut, input)
    assert get_output(dut) == ND8

    await set_weights(dut, 0b01)
    await execute(dut, input)
    assert get_output(dut) == 0

    await set_weights(dut, 0b10)
    await execute(dut, input)
    assert get_output(dut) == -ND8

    await set_weights(dut, 0b11)
    await execute(dut, input)
    assert get_output(dut) == 0


    input = 0

    await set_weights(dut, 0b00)
    await execute(dut, input)
    assert get_output(dut) == 0

    await set_weights(dut, 0b01)
    await execute(dut, input)
    assert get_output(dut) == 0

    await set_weights(dut, 0b10)
    await execute(dut, input)
    assert get_output(dut) == 0

    await set_weights(dut, 0b11)
    await execute(dut, input)
    assert get_output(dut) == 0


    input = 0b11

    await set_weights(dut, 0b00)
    await execute(dut, input)
    assert get_output(dut) == 2*ND8

    await set_weights(dut, 0b01)
    await execute(dut, input)
    assert get_output(dut) == 0

    await set_weights(dut, 0b10)
    await execute(dut, input)
    assert get_output(dut) == -2*ND8


    def set_rightmost_bits(n):
        return (1 << n) - 1 # Generate a bitmask with the N rightmost bits set
    
    K = 8
    input = set_rightmost_bits(K)

    await set_weights(dut, 0b00)
    await execute(dut, input)
    assert get_output(dut) == K*ND8

    await set_weights(dut, 0b01)
    await execute(dut, input)
    assert get_output(dut) == 0

    await set_weights(dut, 0b10)
    await execute(dut, input)
    assert get_output(dut) == -K*ND8
