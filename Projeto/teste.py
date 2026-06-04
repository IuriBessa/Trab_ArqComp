import memory
from array import array

MPC = 0
MIR = 0

MAR = 0
MDR = 0
PC  = 0
MBR = 0
X   = 0
Y   = 0
H   = 0
Z1  = 0
Z2  = 0

N = 0
Z = 1

BUS_A  = 0
BUS_B  = 0
BUS_C  = 0
BUS_A2 = 0
BUS_B2 = 0
BUS_C2 = 0

firmware = array('Q', [0]) * 512

# WRITE2 (bits 48:46)
W2_NONE = 0b000
W2_X    = 0b001
W2_Y    = 0b010
W2_H    = 0b011
W2_Z1   = 0b100
W2_Z2   = 0b101
W2_MAR  = 0b110
W2_PC   = 0b111

# BUS_A2 (bits 54:52)
A2_H, A2_MDR, A2_PC, A2_MBR, A2_X, A2_Y, A2_Z1, A2_Z2 = 0,1,2,3,4,5,6,7

# BUS_B2 (bits 51:49)
B2_MDR, B2_PC, B2_MBR, B2_X, B2_Y, B2_Z1, B2_Z2, B2_0 = 0,1,2,3,4,5,6,7

# ALU2 ops (mesmo encoding da ALU1)
ALU2_B    = 0b00010100
ALU2_A    = 0b00011000
ALU2_ZERO = 0b00010000
ALU2_ApB  = 0b00111100
ALU2_BmA  = 0b00111111
ALU2_Bp1  = 0b00110101
ALU2_Bm1  = 0b00110110
ALU2_Ap1  = 0b00111001


def _dual(alu2=ALU2_B, a2=A2_MBR, b2=B2_MBR, w2=W2_NONE, sf2=0):
    return ((sf2 << 63) | (alu2 << 55) | (a2 << 52) | (b2 << 49) | (w2 << 46))


# ============================================================================
# FIRMWARE
# ----------------------------------------------------------------------------
# Layout do MIR (64 bits):
# [63]    SAVE_FLAGS2
# [62:55] ALU2
# [54:52] BUS_A2
# [51:49] BUS_B2
# [48:46] WRITE2
# [45:38] reservado
# [37]    SAVE_FLAGS1
# [36:28] NEXT_ADDR
# [27:25] JAM
# [24:17] ALU1
# [16:9]  WRITE1
# [8:6]   MEM (bit0=FETCH, bit1=READ, bit2=WRITE)
# [5:3]   BUS_A1
# [2:0]   BUS_B1
#
# Ordem de execução em step():
#   1) snapshot regs
#   2) ALU1 avalia e escreve
#   3) FETCH  (usa PC pós-ALU1)
#   4) ALU2 avalia (snapshot de X/Y/H/Z1/Z2/PC/MDR + MBR pós-FETCH) e escreve
#   5) READ   (usa MAR pós-ALU2)
#   6) WRITE  (usa MAR e MDR pós-ALU2)
#   7) next_instruction
# ============================================================================

# [0] init/fetch
firmware[0] = 0b1_000000000_100_00110101_00100000_001_010_001

# ---- opcode 2: X = X + mem[addr] ----
firmware[2] = (
    0b0_000000100_000_00110101_00100000_011_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[4] = 0b1_000000000_000_00111100_00010000_000_001_011

# ---- opcode 6: mem[addr] = X ----
firmware[6] = (
    0b0_000001000_000_00110101_00100000_001_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[8] = 0b0_000000000_000_00010100_01000000_100_000_011

# ---- opcode 9: GOTO addr ----
firmware[9]  = 0b0_000001010_000_00110101_00100000_001_010_001
firmware[10] = 0b0_000000000_100_00010100_00100000_001_000_010

# ---- opcode 11: IF X == 0 GOTO addr ----
firmware[11]  = 0b1_000001100_001_00010100_00000000_000_000_011
firmware[12]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[268] = 0b0_000001001_000_00010100_00000000_000_000_000

# ---- opcode 13: X = X - mem[addr] ----
firmware[13] = (
    0b0_000001111_000_00110101_00100000_011_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[15] = 0b1_000000000_000_00111111_00010000_000_001_011

# ---- opcodes 16,17 ----
firmware[16] = 0b1_000000000_000_00110101_00010000_000_000_011
firmware[17] = 0b1_000000000_000_00110110_00010000_000_000_011

# ---- opcode 18: IF X < 0 GOTO addr ----
firmware[18]  = 0b1_000010011_010_00010100_00000000_000_000_011
firmware[19]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[275] = 0b0_000001001_000_00010100_00000000_000_000_000

# ---- opcodes 20,21 ----
firmware[20] = 0b1_000000000_000_00010100_00001000_000_000_011
firmware[21] = 0b1_000000000_000_00010100_00010000_000_000_100

# ---- opcode 22: mem[addr] = Y ----
firmware[22] = (
    0b0_000011000_000_00110101_00100000_001_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[24] = 0b0_000000000_000_00010100_01000000_100_000_100

# ---- opcode 25: Y = Y + mem[addr] ----
firmware[25] = (
    0b0_000011011_000_00110101_00100000_011_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[27] = 0b1_000000000_000_00111100_00001000_000_001_100

# ---- opcode 28: Y = mem[addr] ----
firmware[28] = (
    0b0_000011110_000_00110101_00100000_011_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[30] = 0b1_000000000_000_00010100_00001000_000_000_000

# ---- opcodes 31..34 ----
firmware[31] = 0b1_000000000_000_01010100_00010000_000_000_011
firmware[32] = 0b1_000000000_000_10010100_00010000_000_000_011
firmware[33] = 0b1_000000000_000_00110101_00001000_000_000_100
firmware[34] = 0b1_000000000_000_00110110_00001000_000_000_100

# ---- opcode 35: IF Y == 0 GOTO addr ----
firmware[35]  = 0b1_000100100_001_00010100_00000000_000_000_100
firmware[36]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[292] = 0b0_000001001_000_00010100_00000000_000_000_000

# ---- opcode 40: X = mem[addr] ----
firmware[40] = (
    0b0_010000001_000_00110101_00100000_011_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[129] = 0b1_000000000_000_00010100_00010000_000_000_000

# ---- opcodes 41,42 ----
firmware[41] = 0b1_000000000_000_00010000_00010000_000_000_000
firmware[42] = 0b1_000000000_000_00010000_00001000_000_000_000

# ---- opcode 43: IF X <= 0 GOTO addr ----
firmware[43]  = 0b1_010000100_011_00010100_00000000_000_000_011
firmware[132] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[388] = 0b0_000001001_000_00010100_00000000_000_000_000

# ---- opcodes 45..47 ----
firmware[45] = 0b1_000000000_000_00111100_00010000_000_101_011
firmware[46] = 0b1_000000000_000_00111111_00010000_000_101_011
firmware[47] = 0b1_000000000_000_00111100_00001000_000_101_011

# ---- opcode 48: SWAP X,Y (snapshot semantics) ----
firmware[48] = (
    0b1_000000000_000_00010100_00010000_000_000_100
    | _dual(ALU2_B, A2_MBR, B2_X, W2_Y)
)

# ---- opcodes 49,50 ----
firmware[49] = 0b1_000000000_000_01010100_00001000_000_000_100
firmware[50] = 0b1_000000000_000_10010100_00001000_000_000_100

# ---- opcodes 53..56 ----
firmware[53] = 0b0_000000000_000_00010100_00000100_000_000_011
firmware[54] = 0b1_000000000_000_00011000_00010000_000_000_000
firmware[55] = 0b0_000000000_000_00010100_00000100_000_000_100
firmware[56] = 0b1_000000000_000_00011000_00001000_000_000_000

# ---- opcodes 57..60 ----
firmware[57]  = 0b1_000111010_011_00010100_00000000_000_000_100
firmware[58]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[314] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[59]  = 0b1_000111100_010_00010100_00000000_000_000_100
firmware[60]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[316] = 0b0_000001001_000_00010100_00000000_000_000_000

# ---- opcode 61: Y = Y - mem[addr] ----
firmware[61] = (
    0b0_010000110_000_00110101_00100000_011_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[134] = 0b1_000000000_000_00111111_00001000_000_001_100

# ---- opcodes 64,65 ----
firmware[64] = 0b1_000000000_000_00001100_00010000_000_101_011
firmware[65] = 0b1_000000000_000_00011100_00010000_000_101_011

# ---- opcode 66: X = imm ----
firmware[66] = (
    0b0_000000000_000_00110101_00100000_001_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_X, sf2=1)
)

# ---- opcode 67: Y = imm ----
firmware[67] = (
    0b0_000000000_000_00110101_00100000_001_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_Y, sf2=1)
)

# ---- opcodes 68..75 ----
firmware[68] = 0b0_000000000_000_00010100_00000010_000_000_011
firmware[69] = 0b0_000000000_000_00010100_00000010_000_000_100
firmware[70] = 0b1_000000000_000_00010100_00010000_000_000_101
firmware[71] = 0b1_000000000_000_00010100_00001000_000_000_101
firmware[72] = 0b0_000000000_000_00010100_00000001_000_000_011
firmware[73] = 0b0_000000000_000_00010100_00000001_000_000_100
firmware[74] = 0b1_000000000_000_00010100_00010000_000_000_110
firmware[75] = 0b1_000000000_000_00010100_00001000_000_000_110

# ---- opcode 76: IF X odd GOTO addr ----
firmware[76]  = 0b1_001001101_101_00000001_00000000_000_100_000
firmware[77]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[333] = 0b0_000001001_000_00010100_00000000_000_000_000

# ---- opcodes 78..80 ----
firmware[78] = 0b1_000000000_000_00111111_00001000_000_100_100
firmware[79] = 0b1_000000000_000_00000010_00010000_000_101_011
firmware[80] = 0b1_000000000_000_00000011_00010000_000_100_000

# ---- opcodes 83,84 ----
firmware[83] = 0b1_000000000_000_00110110_00000010_000_000_101
firmware[84] = 0b1_000000000_000_00110101_00000010_000_000_101

# ---- opcode 85: IF Z1 == 0 GOTO addr ----
firmware[85]  = 0b1_001010110_001_00010100_00000000_000_000_101
firmware[86]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[342] = 0b0_000001001_000_00010100_00000000_000_000_000

# ---- opcode 87: Z1 = imm ----
firmware[87] = (
    0b0_000000000_000_00110101_00100000_001_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_Z1)
)

# ---- opcodes 88..91 ----
firmware[88] = 0b1_000000000_000_00111001_00000100_000_000_000
firmware[89] = 0b1_000000000_000_00111010_00000100_000_000_000
firmware[90] = 0b1_000000000_000_00110110_00000001_000_000_110
firmware[91] = 0b1_000000000_000_00110101_00000001_000_000_110

# ---- opcode 92: IF Z2 == 0 GOTO addr ----
firmware[92]  = 0b1_001011101_001_00010100_00000000_000_000_110
firmware[93]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[349] = 0b0_000001001_000_00010100_00000000_000_000_000

# ---- opcodes 94..96 ----
firmware[94] = 0b1_000000000_000_00010000_00000100_000_000_000
firmware[95] = 0b1_000000000_000_00010000_00000010_000_000_000
firmware[96] = 0b1_000000000_000_00010000_00000001_000_000_000

# ---- opcode 97: mem[addr] = Z1 ----
firmware[97] = (
    0b0_001100011_000_00110101_00100000_001_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[99] = 0b0_000000000_000_00010100_01000000_100_000_101

# ---- opcode 100: IF X >= 0 GOTO addr ----
firmware[100] = 0b1_001100101_110_00010100_00000000_000_000_011
firmware[101] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[357] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[255] = 0b0_000000000_000_00000000_00000000_000_000_000

# ---- opcode 102: CALL addr ----
# ALU1: PC++, FETCH MBR=addr ; ALU2: Z2 = PC_snap + 1 (= endereço do byte addr)
# Após RET, [0] fará PC++ saindo para o próximo opcode.
firmware[102] = (
    0b0_001101000_000_00110101_00100000_001_010_001
    | _dual(ALU2_Bp1, A2_MBR, B2_PC, W2_Z2)
)
firmware[104] = 0b0_000000000_100_00010100_00100000_001_000_010

# ---- opcode 105: RET ----
# PC = Z2 ; GOTO 0 (deixa [0] fazer PC++ e FETCH do próximo opcode)
firmware[105] = 0b0_000000000_000_00010100_00100000_000_000_110

# ---- opcodes 106..115 ----
firmware[106] = 0b1_001101011_010_00010100_00000000_000_000_101
firmware[107] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[363] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[108] = 0b1_001101101_011_00010100_00000000_000_000_101
firmware[109] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[365] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[110] = 0b1_001101111_001_00011000_00000000_000_000_000
firmware[111] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[367] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[112] = 0b1_001110001_010_00011000_00000000_000_000_000
firmware[113] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[369] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[114] = 0b1_001110011_011_00011000_00000000_000_000_000
firmware[115] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[371] = 0b0_000001001_000_00010100_00000000_000_000_000

# ---- opcodes 116..121 ----
firmware[116] = 0b0_000000000_000_00011000_00000010_000_000_000
firmware[117] = 0b0_000000000_000_00010100_00000100_000_000_101
firmware[118] = 0b0_000000000_000_00011000_00000001_000_000_000
firmware[119] = 0b0_000000000_000_00010100_00000100_000_000_110
firmware[120] = 0b0_000000000_000_00010100_00000001_000_000_101
firmware[121] = 0b0_000000000_000_00010100_00000010_000_000_110

# ---- opcode 122: mem[addr] = Z2 ----
firmware[122] = (
    0b0_001111100_000_00110101_00100000_001_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[124] = 0b0_000000000_000_00010100_01000000_100_000_110

# ---- opcodes 125..127, 137 ----
firmware[125] = 0b1_000000000_000_00111100_00010000_000_110_011
firmware[126] = 0b1_000000000_000_00111111_00010000_000_110_011
firmware[127] = 0b1_000000000_000_00111100_00001000_000_110_100
firmware[137] = 0b1_000000000_000_00111111_00001000_000_110_100

# ---- opcodes 140..147 ----
firmware[140] = 0b0_010001101_000_00010100_10000000_010_000_101
firmware[141] = 0b1_000000000_000_00010100_00010000_000_000_000
firmware[142] = 0b0_010001111_000_00010100_10000000_010_000_101
firmware[143] = 0b1_000000000_000_00010100_00001000_000_000_000
firmware[144] = 0b0_010010001_000_00010100_10000000_000_000_101
firmware[145] = 0b0_000000000_000_00010100_01000000_100_000_011
firmware[146] = 0b0_010010011_000_00010100_10000000_000_000_101
firmware[147] = 0b0_000000000_000_00010100_01000000_100_000_100

# ---- opcode 148: Z1 = mem[addr] ----
firmware[148] = (
    0b0_010010110_000_00110101_00100000_011_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[150] = 0b1_000000000_000_00010100_00000010_000_000_000

# ---- opcode 151: Z2 = mem[addr] ----
firmware[151] = (
    0b0_010011001_000_00110101_00100000_011_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
firmware[153] = 0b1_000000000_000_00010100_00000001_000_000_000

# ---- opcode 154: Z2 = imm ----
firmware[154] = (
    0b0_000000000_000_00110101_00100000_001_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_Z2)
)

# ---- opcode 156: H = imm ----
firmware[156] = (
    0b0_000000000_000_00110101_00100000_001_010_001
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_H)
)

# ---- opcodes 158,159 ----
firmware[158] = 0b1_000000000_000_00111100_00000010_000_101_011
firmware[159] = 0b1_000000000_000_00111111_00000010_000_101_011


# ============================================================================
# FUNÇÕES
# ============================================================================

def read_regs(bus_a_sel, bus_b_sel):
    global BUS_A, BUS_B
    reg_table_A = [H, MDR, PC, MBR, X, Y, Z1, Z2]
    reg_table_B = [MDR, PC, MBR, X, Y, Z1, Z2, 0]
    BUS_A = reg_table_A[bus_a_sel & 0b111]
    BUS_B = reg_table_B[bus_b_sel & 0b111]


def write_regs(reg_bits):
    global MAR, MDR, PC, X, Y, H, Z1, Z2
    if reg_bits & 0b10000000: MAR = BUS_C
    if reg_bits & 0b01000000: MDR = BUS_C
    if reg_bits & 0b00100000: PC  = BUS_C
    if reg_bits & 0b00010000: X   = BUS_C
    if reg_bits & 0b00001000: Y   = BUS_C
    if reg_bits & 0b00000100: H   = BUS_C
    if reg_bits & 0b00000010: Z1  = BUS_C
    if reg_bits & 0b00000001: Z2  = BUS_C


def write_regs2(w2, val):
    global X, Y, H, Z1, Z2, MAR, PC
    if   w2 == W2_X:   X   = val
    elif w2 == W2_Y:   Y   = val
    elif w2 == W2_H:   H   = val
    elif w2 == W2_Z1:  Z1  = val
    elif w2 == W2_Z2:  Z2  = val
    elif w2 == W2_MAR: MAR = val
    elif w2 == W2_PC:  PC  = val


def alu(control_bits, save_flags):
    global N, Z, BUS_C
    a, b = BUS_A, BUS_B
    o = 0
    shift_bits   = (control_bits >> 6) & 0b11
    control_bits =  control_bits & 0b00111111
    if   control_bits == 0b011000: o = a
    elif control_bits == 0b010100: o = b
    elif control_bits == 0b011010: o = ~a
    elif control_bits == 0b101100: o = ~b
    elif control_bits == 0b111100: o = a + b
    elif control_bits == 0b111101: o = a + b + 1
    elif control_bits == 0b111001: o = a + 1
    elif control_bits == 0b110101: o = b + 1
    elif control_bits == 0b111111: o = b - a
    elif control_bits == 0b110110: o = b - 1
    elif control_bits == 0b111011: o = -a
    elif control_bits == 0b001100: o = a & b
    elif control_bits == 0b011100: o = a | b
    elif control_bits == 0b010000: o = 0
    elif control_bits == 0b110001: o = 1
    elif control_bits == 0b110010: o = -1
    elif control_bits == 0b000001: o = a & 1
    elif control_bits == 0b000010: o = a ^ b
    elif control_bits == 0b111010: o = a - 1
    elif control_bits == 0b000011:
        o = a if not (a & 0x80000000) else (~a + 1) & 0xFFFFFFFF
    o = o & 0xFFFFFFFF
    if   shift_bits == 0b01: o = (o << 1) & 0xFFFFFFFF
    elif shift_bits == 0b10: o = o >> 1
    elif shift_bits == 0b11: o = (o << 8) & 0xFFFFFFFF
    if save_flags:
        if o == 0:             N = 0; Z = 1
        elif o & 0x80000000:   N = 1; Z = 0
        else:                  N = 0; Z = 0
    BUS_C = o


def next_instruction(nextadd, jam):
    global MPC
    if jam == 0b000:
        MPC = nextadd; return
    elif jam == 0b001: nextadd = nextadd | (Z << 8)
    elif jam == 0b010: nextadd = nextadd | (N << 8)
    elif jam == 0b011: nextadd = nextadd | ((N | Z) << 8)
    elif jam == 0b100: nextadd = nextadd | MBR
    elif jam == 0b101: nextadd = nextadd | ((1 - Z) << 8)
    elif jam == 0b110: nextadd = nextadd | ((1 - N) << 8)
    MPC = nextadd


def step():
    global MIR, MPC
    global X, Y, H, Z1, Z2, PC, MAR, MDR, MBR
    global BUS_A, BUS_B, BUS_C, BUS_C2

    MIR = firmware[MPC]
    if MIR == 0:
        return False

    sf1       = (MIR >> 37) & 0b1
    next_addr = (MIR >> 28) & 0x1FF
    jam       = (MIR >> 25) & 0b111
    alu1_ctrl = (MIR >> 17) & 0xFF
    write1    = (MIR >>  9) & 0xFF
    mem_bits  = (MIR >>  6) & 0b111
    bus_a1    = (MIR >>  3) & 0b111
    bus_b1    =  MIR        & 0b111

    w2        = (MIR >> 46) & 0b111
    bus_b2    = (MIR >> 49) & 0b111
    bus_a2    = (MIR >> 52) & 0b111
    alu2_ctrl = (MIR >> 55) & 0xFF
    sf2       = (MIR >> 63) & 0b1

    # Snapshot para ALU2 (preserva semântica pre-ALU1)
    snap_X, snap_Y, snap_H = X, Y, H
    snap_Z1, snap_Z2, snap_PC = Z1, Z2, PC
    snap_MDR = MDR

    # === ALU1 ===
    read_regs(bus_a1, bus_b1)
    alu(alu1_ctrl, sf1)
    write_regs(write1)

    # === FETCH (usa PC pós-ALU1) ===
    if mem_bits & 0b001:
        MBR = memory.read_byte(PC)

    # === ALU2 (snapshot dos regs + MBR pós-FETCH) ===
    if w2 != W2_NONE or alu2_ctrl != 0:
        cur_X, cur_Y, cur_H = X, Y, H
        cur_Z1, cur_Z2, cur_PC = Z1, Z2, PC
        cur_MDR = MDR
        X, Y, H = snap_X, snap_Y, snap_H
        Z1, Z2, PC = snap_Z1, snap_Z2, snap_PC
        MDR = snap_MDR

        saved_c = BUS_C
        read_regs(bus_a2, bus_b2)
        alu(alu2_ctrl, sf2)
        BUS_C2 = BUS_C
        BUS_C = saved_c

        X, Y, H = cur_X, cur_Y, cur_H
        Z1, Z2, PC = cur_Z1, cur_Z2, cur_PC
        MDR = cur_MDR

        write_regs2(w2, BUS_C2)

    # === READ (usa MAR pós-ALU2) ===
    if mem_bits & 0b010:
        MDR = memory.read_word(MAR)

    # === WRITE (usa MAR e MDR pós-ALU2) ===
    if mem_bits & 0b100:
        memory.write_word(MAR, MDR)

    next_instruction(next_addr, jam)
    return True
