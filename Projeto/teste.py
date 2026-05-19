# processador.py  (UFC2X — revisão com 5 optimizações)
# Dependência: memoria.py (inalterado)
import memoria
from array import array

# ==============================================================================
# LAYOUT DO MIR — 38 bits (cabe em uint64):
#
#  [37]     SAVE_FLAGS (1b)   — 0 = ALU opera mas NÃO atualiza N/Z
#  [36:28]  NEXT_ADDR  (9b)
#  [27:25]  JAM        (3b)
#  [24:17]  ALU        (8b)  — bits[7:6]=shift, bits[5:0]=operação
#  [16:9]   WRITE_REGS (8b)  — expandido de 6→8 bits (Z1, Z2)
#  [8:6]    MEM        (3b)
#  [5:3]    BUS_A      (3b)
#  [2:0]    BUS_B      (3b)
#
# BUS_A (bits[5:3]): 000=H  001=MDR  010=PC  011=MBR  100=X  101=Y  110=Z1  111=Z2
# BUS_B (bits[2:0]): 000=MDR 001=PC  010=MBR 011=X    100=Y  101=Z1 110=Z2  111=0
#
# WRITE_REGS (bits[16:9]):
#   bit7=MAR  bit6=MDR  bit5=PC  bit4=X  bit3=Y  bit2=H  bit1=Z1  bit0=Z2
#
# JAM:  000=NOP  001=JAMZ(se Z=1)  010=JAMN(se N=1)  011=JAMNZ(se N|Z=1)
#       100=JAMBR(→MBR)  101=JAMNOTZ(se Z=0)  110=JAMNOTN(se N=0)
#
# ALU (bits[5:0] após remover shift):
#   011000=A   010100=B   011010=~A  101100=~B
#   111100=A+B 111101=A+B+1  111001=A+1  110101=B+1
#   111111=B-A 110110=B-1    111011=-A
#   001100=A&B 011100=A|B    010000=0    110001=1  110010=-1
#   000001=A&1 (NOVO)  000010=A^B (NOVO)  000011=|A| (NOVO)
# ==============================================================================

# ── Seletores BUS_A ──────────────────────────────────────────────────────────
BA_H   = 0b000
BA_MDR = 0b001
BA_PC  = 0b010
BA_MBR = 0b011
BA_X   = 0b100
BA_Y   = 0b101
BA_Z1  = 0b110
BA_Z2  = 0b111

# ── Seletores BUS_B ──────────────────────────────────────────────────────────
BB_MDR = 0b000
BB_PC  = 0b001
BB_MBR = 0b010
BB_X   = 0b011
BB_Y   = 0b100
BB_Z1  = 0b101
BB_Z2  = 0b110
BB_0   = 0b111

# ── Bits WRITE_REGS ──────────────────────────────────────────────────────────
WR_MAR = 0b10000000
WR_MDR = 0b01000000
WR_PC  = 0b00100000
WR_X   = 0b00010000
WR_Y   = 0b00001000
WR_H   = 0b00000100
WR_Z1  = 0b00000010  # NOVO
WR_Z2  = 0b00000001  # NOVO

# ── Bits MEM ─────────────────────────────────────────────────────────────────
MEM_FETCH = 0b001
MEM_READ  = 0b010
MEM_WRITE = 0b100

# ── Códigos JAM ──────────────────────────────────────────────────────────────
JAM_NONE  = 0b000
JAM_Z     = 0b001   # pula se Z=1
JAM_N     = 0b010   # pula se N=1
JAM_NZ    = 0b011   # pula se N=1 ou Z=1
JAM_MBR   = 0b100   # despacha para MBR (fetch/goto)
JAM_NOTZ  = 0b101   # pula se Z=0  (NOVO — "se resultado ≠ 0")
JAM_NOTN  = 0b110   # pula se N=0  (NOVO)

# ── Operações ALU (campo de 8 bits) ──────────────────────────────────────────
ALU_A       = 0b00011000
ALU_B       = 0b00010100
ALU_NOT_A   = 0b00011010
ALU_NOT_B   = 0b00101100
ALU_A_B     = 0b00111100   # A+B
ALU_A_B_1   = 0b00111101   # A+B+1
ALU_A_1     = 0b00111001   # A+1
ALU_B_1     = 0b00110101   # B+1
ALU_B_A     = 0b00111111   # B-A
ALU_B_1M    = 0b00110110   # B-1
ALU_NEG_A   = 0b00111011   # -A
ALU_AND     = 0b00001100   # A&B
ALU_OR      = 0b00011100   # A|B
ALU_ZERO    = 0b00010000   # 0
ALU_ONE     = 0b00110001   # 1
ALU_NEG1    = 0b00110010   # -1
ALU_SHL_B   = 0b01010100   # B<<1
ALU_SHR_B   = 0b10010100   # B>>1
# ── Novas operações (bits[5:0] livres) ───────────────────────────────────────
ALU_A_AND_1 = 0b00000001   # A & 1  → testa bit 0 (NOVO)
ALU_XOR     = 0b00000010   # A ^ B            (NOVO)
ALU_ABS_A   = 0b00000011   # |A|              (NOVO)

# ==============================================================================
# Helper: constrói uma microinstrução de 38 bits
# ==============================================================================
def make_micro(next_addr=0, jam=JAM_NONE, alu=ALU_B,
               write_regs=0, mem=0, bus_a=BA_H, bus_b=BB_MDR,
               save_flags=1):
    return (
        ((save_flags  &      1) << 37) |
        ((next_addr   & 0x1FF) << 28) |
        ((jam         &  0b111) << 25) |
        ((alu         &   0xFF) << 17) |
        ((write_regs  &   0xFF) <<  9) |
        ((mem         &  0b111) <<  6) |
        ((bus_a       &  0b111) <<  3) |
         (bus_b       &  0b111)
    )

# ==============================================================================
# Registradores
# ==============================================================================
MPC = 0
MIR = 0
MAR = 0
MDR = 0
PC  = 0
MBR = 0
X   = 0
Y   = 0
H   = 0
Z1  = 0   # NOVO — registrador de propósito geral 1
Z2  = 0   # NOVO — registrador de propósito geral 2

N = 0
Z = 1

BUS_A = 0
BUS_B = 0
BUS_C = 0

# ==============================================================================
# Firmware  (512 entradas × 64 bits)
# ==============================================================================
firmware = array('Q', [0]) * 512

# ── 0: FETCH/INIT — PC=PC+1; MBR=mem[PC]; GOTO MBR ─────────────────────────
firmware[0] = make_micro(0, JAM_MBR, ALU_B_1, WR_PC, MEM_FETCH, BA_PC, BB_PC)

# ── 2: X = X + mem[addr]  (3 ciclos) ────────────────────────────────────────
firmware[2] = make_micro(3,   JAM_NONE, ALU_B_1, WR_PC,  MEM_FETCH, BA_PC,  BB_PC,  save_flags=0)
firmware[3] = make_micro(4,   JAM_NONE, ALU_B,   WR_MAR, MEM_READ,  BA_H,   BB_MBR, save_flags=0)
firmware[4] = make_micro(0,   JAM_NONE, ALU_A_B, WR_X,   0,         BA_MDR, BB_X)

# ── 6: mem[addr] = X  (3 ciclos) ────────────────────────────────────────────
firmware[6] = make_micro(7,   JAM_NONE, ALU_B_1, WR_PC,  MEM_FETCH, BA_PC,  BB_PC,  save_flags=0)
firmware[7] = make_micro(8,   JAM_NONE, ALU_B,   WR_MAR, 0,         BA_H,   BB_MBR, save_flags=0)
firmware[8] = make_micro(0,   JAM_NONE, ALU_B,   WR_MDR, MEM_WRITE, BA_H,   BB_X,   save_flags=0)

# ── 9: GOTO addr  (2 ciclos) ────────────────────────────────────────────────
firmware[9]  = make_micro(10,  JAM_NONE, ALU_B_1, WR_PC,  MEM_FETCH, BA_PC,  BB_PC,  save_flags=0)
firmware[10] = make_micro(0,   JAM_MBR,  ALU_B,   WR_PC,  MEM_FETCH, BA_H,   BB_MBR, save_flags=0)

# ── 11: IF X == 0 GOTO addr ─────────────────────────────────────────────────
# Z=1 → GOTO 268; Z=0 → descarta byte (12)
firmware[11]  = make_micro(12,  JAM_Z,    ALU_B,   0,      0,         BA_H,   BB_X)
firmware[12]  = make_micro(0,   JAM_NONE, ALU_B_1, WR_PC,  0,         BA_PC,  BB_PC,  save_flags=0)
firmware[268] = make_micro(9,   JAM_NONE, ALU_B,   0,      0,         BA_H,   BB_MDR, save_flags=0)

# ── 13: X = X - mem[addr]  (3 ciclos) ───────────────────────────────────────
firmware[13] = make_micro(14,  JAM_NONE, ALU_B_1, WR_PC,  MEM_FETCH, BA_PC,  BB_PC,  save_flags=0)
firmware[14] = make_micro(15,  JAM_NONE, ALU_B,   WR_MAR, MEM_READ,  BA_H,   BB_MBR, save_flags=0)
firmware[15] = make_micro(0,   JAM_NONE, ALU_B_A, WR_X,   0,         BA_MDR, BB_X)

# ── 16: X = X + 1 ───────────────────────────────────────────────────────────
firmware[16] = make_micro(0, JAM_NONE, ALU_B_1,  WR_X, 0, BA_H, BB_X)

# ── 17: X = X - 1 ───────────────────────────────────────────────────────────
firmware[17] = make_micro(0, JAM_NONE, ALU_B_1M, WR_X, 0, BA_H, BB_X)

# ── 18: IF X < 0 GOTO addr ──────────────────────────────────────────────────
# N=1 → GOTO 275; N=0 → descarta byte (19)
firmware[18]  = make_micro(19,  JAM_N,    ALU_B,   0,     0,  BA_H, BB_X)
firmware[19]  = make_micro(0,   JAM_NONE, ALU_B_1, WR_PC, 0,  BA_PC, BB_PC, save_flags=0)
firmware[275] = make_micro(9,   JAM_NONE, ALU_B,   0,     0,  BA_H,  BB_MDR, save_flags=0)

# ── 20: Y = X ───────────────────────────────────────────────────────────────
firmware[20] = make_micro(0, JAM_NONE, ALU_B, WR_Y, 0, BA_H, BB_X)

# ── 21: X = Y ───────────────────────────────────────────────────────────────
firmware[21] = make_micro(0, JAM_NONE, ALU_B, WR_X, 0, BA_H, BB_Y)

# ── 22: mem[addr] = Y  (3 ciclos) ───────────────────────────────────────────
firmware[22] = make_micro(23,  JAM_NONE, ALU_B_1, WR_PC,  MEM_FETCH, BA_PC, BB_PC,  save_flags=0)
firmware[23] = make_micro(24,  JAM_NONE, ALU_B,   WR_MAR, 0,         BA_H,  BB_MBR, save_flags=0)
firmware[24] = make_micro(0,   JAM_NONE, ALU_B,   WR_MDR, MEM_WRITE, BA_H,  BB_Y,   save_flags=0)

# ── 25: Y = Y + mem[addr]  (3 ciclos) ───────────────────────────────────────
firmware[25] = make_micro(26,  JAM_NONE, ALU_B_1, WR_PC,  MEM_FETCH, BA_PC,  BB_PC,  save_flags=0)
firmware[26] = make_micro(27,  JAM_NONE, ALU_B,   WR_MAR, MEM_READ,  BA_H,   BB_MBR, save_flags=0)
firmware[27] = make_micro(0,   JAM_NONE, ALU_A_B, WR_Y,   0,         BA_MDR, BB_Y)

# ── 28: Y = mem[addr]  (3 ciclos) ───────────────────────────────────────────
firmware[28] = make_micro(29,  JAM_NONE, ALU_B_1, WR_PC,  MEM_FETCH, BA_PC, BB_PC,  save_flags=0)
firmware[29] = make_micro(30,  JAM_NONE, ALU_B,   WR_MAR, MEM_READ,  BA_H,  BB_MBR, save_flags=0)
firmware[30] = make_micro(0,   JAM_NONE, ALU_B,   WR_Y,   0,         BA_H,  BB_MDR)

# ── 31: X = X << 1 ──────────────────────────────────────────────────────────
firmware[31] = make_micro(0, JAM_NONE, ALU_SHL_B, WR_X, 0, BA_H, BB_X)

# ── 32: X = X >> 1 ──────────────────────────────────────────────────────────
firmware[32] = make_micro(0, JAM_NONE, ALU_SHR_B, WR_X, 0, BA_H, BB_X)

# ── 33: Y = Y + 1 ───────────────────────────────────────────────────────────
firmware[33] = make_micro(0, JAM_NONE, ALU_B_1,  WR_Y, 0, BA_H, BB_Y)

# ── 34: Y = Y - 1 ───────────────────────────────────────────────────────────
firmware[34] = make_micro(0, JAM_NONE, ALU_B_1M, WR_Y, 0, BA_H, BB_Y)

# ── 35: IF Y == 0 GOTO addr ─────────────────────────────────────────────────
# Z=1 → GOTO 292; Z=0 → descarta byte (36)
firmware[35]  = make_micro(36,  JAM_Z,    ALU_B,   0,     0,  BA_H,  BB_Y)
firmware[36]  = make_micro(0,   JAM_NONE, ALU_B_1, WR_PC, 0,  BA_PC, BB_PC, save_flags=0)
firmware[292] = make_micro(9,   JAM_NONE, ALU_B,   0,     0,  BA_H,  BB_MDR, save_flags=0)

# ── 40: X = mem[addr]  (via 128-129) ────────────────────────────────────────
firmware[40]  = make_micro(128, JAM_NONE, ALU_B_1, WR_PC,  MEM_FETCH, BA_PC, BB_PC,  save_flags=0)
firmware[128] = make_micro(129, JAM_NONE, ALU_B,   WR_MAR, MEM_READ,  BA_H,  BB_MBR, save_flags=0)
firmware[129] = make_micro(0,   JAM_NONE, ALU_B,   WR_X,   0,         BA_H,  BB_MDR)

# ── 41: X = 0 ───────────────────────────────────────────────────────────────
firmware[41] = make_micro(0, JAM_NONE, ALU_ZERO, WR_X, 0)

# ── 42: Y = 0 ───────────────────────────────────────────────────────────────
firmware[42] = make_micro(0, JAM_NONE, ALU_ZERO, WR_Y, 0)

# ── 43: IF X <= 0 GOTO addr ─────────────────────────────────────────────────
# N|Z=1 → GOTO 388; outro → descarta byte (132)
firmware[43]  = make_micro(132, JAM_NZ,   ALU_B,   0,     0,  BA_H,  BB_X)
firmware[132] = make_micro(0,   JAM_NONE, ALU_B_1, WR_PC, 0,  BA_PC, BB_PC, save_flags=0)
firmware[388] = make_micro(9,   JAM_NONE, ALU_B,   0,     0,  BA_H,  BB_MDR, save_flags=0)

# ── 45: X = X + Y ───────────────────────────────────────────────────────────
firmware[45] = make_micro(0, JAM_NONE, ALU_A_B, WR_X, 0, BA_Y, BB_X)

# ── 46: X = X - Y  (B-A = X-Y) ──────────────────────────────────────────────
firmware[46] = make_micro(0, JAM_NONE, ALU_B_A, WR_X, 0, BA_Y, BB_X)

# ── 47: Y = X + Y ───────────────────────────────────────────────────────────
firmware[47] = make_micro(0, JAM_NONE, ALU_A_B, WR_Y, 0, BA_Y, BB_X)

# ── 48: SWAP X, Y  (3 microciclos internos) ─────────────────────────────────
firmware[48]  = make_micro(130, JAM_NONE, ALU_B, WR_H, 0, BA_H, BB_X,  save_flags=0)  # H=X
firmware[130] = make_micro(131, JAM_NONE, ALU_B, WR_X, 0, BA_H, BB_Y,  save_flags=0)  # X=Y
firmware[131] = make_micro(0,   JAM_NONE, ALU_A, WR_Y, 0, BA_H, BB_MDR)               # Y=H

# ── 49: Y = Y << 1 ──────────────────────────────────────────────────────────
firmware[49] = make_micro(0, JAM_NONE, ALU_SHL_B, WR_Y, 0, BA_H, BB_Y)

# ── 50: Y = Y >> 1 ──────────────────────────────────────────────────────────
firmware[50] = make_micro(0, JAM_NONE, ALU_SHR_B, WR_Y, 0, BA_H, BB_Y)

# ── 255: HALT ────────────────────────────────────────────────────────────────
firmware[255] = 0

# ==============================================================================
# NOVAS INSTRUÇÕES
# ==============================================================================

# ── 53: H = X  (save_flags=0 → preserva N/Z do teste anterior) ──────────────
firmware[53] = make_micro(0, JAM_NONE, ALU_B, WR_H, 0, BA_H, BB_X, save_flags=0)

# ── 54: X = H ────────────────────────────────────────────────────────────────
firmware[54] = make_micro(0, JAM_NONE, ALU_A, WR_X, 0, BA_H, BB_MDR)

# ── 55: H = Y  (save_flags=0) ────────────────────────────────────────────────
firmware[55] = make_micro(0, JAM_NONE, ALU_B, WR_H, 0, BA_H, BB_Y, save_flags=0)

# ── 56: Y = H ────────────────────────────────────────────────────────────────
firmware[56] = make_micro(0, JAM_NONE, ALU_A, WR_Y, 0, BA_H, BB_MDR)

# ── 57: IF Y <= 0 GOTO addr ─────────────────────────────────────────────────
# N|Z=1 → GOTO 314; N|Z=0 → descarta byte (58)
firmware[57]  = make_micro(58,  JAM_NZ,   ALU_B,   0,     0,  BA_H,  BB_Y)
firmware[58]  = make_micro(0,   JAM_NONE, ALU_B_1, WR_PC, 0,  BA_PC, BB_PC, save_flags=0)
firmware[314] = make_micro(9,   JAM_NONE, ALU_B,   0,     0,  BA_H,  BB_MDR, save_flags=0)

# ── 59: IF Y < 0 GOTO addr ──────────────────────────────────────────────────
# N=1 → GOTO 316; N=0 → descarta byte (60)
firmware[59]  = make_micro(60,  JAM_N,    ALU_B,   0,     0,  BA_H,  BB_Y)
firmware[60]  = make_micro(0,   JAM_NONE, ALU_B_1, WR_PC, 0,  BA_PC, BB_PC, save_flags=0)
firmware[316] = make_micro(9,   JAM_NONE, ALU_B,   0,     0,  BA_H,  BB_MDR, save_flags=0)

# ── 61: Y = Y - mem[addr]  (3 ciclos) ───────────────────────────────────────
firmware[61]  = make_micro(133, JAM_NONE, ALU_B_1, WR_PC,  MEM_FETCH, BA_PC,  BB_PC,  save_flags=0)
firmware[133] = make_micro(134, JAM_NONE, ALU_B,   WR_MAR, MEM_READ,  BA_H,   BB_MBR, save_flags=0)
firmware[134] = make_micro(0,   JAM_NONE, ALU_B_A, WR_Y,   0,         BA_MDR, BB_Y)

# ── 64: X = X AND Y ──────────────────────────────────────────────────────────
firmware[64] = make_micro(0, JAM_NONE, ALU_AND, WR_X, 0, BA_Y, BB_X)

# ── 65: X = X OR Y ───────────────────────────────────────────────────────────
firmware[65] = make_micro(0, JAM_NONE, ALU_OR,  WR_X, 0, BA_Y, BB_X)

# ── 66: X = imm  (2 ciclos — 1 ciclo a menos que X=mem[addr]) ───────────────
# Ciclo 66: PC++; FETCH → MBR recebe o byte imediato
# Ciclo 135: X = MBR
firmware[66]  = make_micro(135, JAM_NONE, ALU_B_1, WR_PC, MEM_FETCH, BA_PC, BB_PC,  save_flags=0)
firmware[135] = make_micro(0,   JAM_NONE, ALU_B,   WR_X,  0,         BA_H,  BB_MBR)

# ── 67: Y = imm  (2 ciclos) ──────────────────────────────────────────────────
firmware[67]  = make_micro(136, JAM_NONE, ALU_B_1, WR_PC, MEM_FETCH, BA_PC, BB_PC,  save_flags=0)
firmware[136] = make_micro(0,   JAM_NONE, ALU_B,   WR_Y,  0,         BA_H,  BB_MBR)

# ── 68-75: Registradores Z1 e Z2 ─────────────────────────────────────────────
firmware[68] = make_micro(0, JAM_NONE, ALU_B, WR_Z1, 0, BA_H, BB_X,  save_flags=0)  # Z1 = X
firmware[69] = make_micro(0, JAM_NONE, ALU_B, WR_Z1, 0, BA_H, BB_Y,  save_flags=0)  # Z1 = Y
firmware[70] = make_micro(0, JAM_NONE, ALU_B, WR_X,  0, BA_H, BB_Z1)                # X  = Z1
firmware[71] = make_micro(0, JAM_NONE, ALU_B, WR_Y,  0, BA_H, BB_Z1)                # Y  = Z1
firmware[72] = make_micro(0, JAM_NONE, ALU_B, WR_Z2, 0, BA_H, BB_X,  save_flags=0)  # Z2 = X
firmware[73] = make_micro(0, JAM_NONE, ALU_B, WR_Z2, 0, BA_H, BB_Y,  save_flags=0)  # Z2 = Y
firmware[74] = make_micro(0, JAM_NONE, ALU_B, WR_X,  0, BA_H, BB_Z2)                # X  = Z2
firmware[75] = make_micro(0, JAM_NONE, ALU_B, WR_Y,  0, BA_H, BB_Z2)                # Y  = Z2

# ── 76: IF X_ODD GOTO addr  (JAM_NOTZ: pula quando Z=0, i.e. X&1 ≠ 0) ──────
# X ímpar → Z=0 → 77|256=333 → GOTO 9
# X par   → Z=1 → 77           → descarta byte
firmware[76]  = make_micro(77,  JAM_NOTZ, ALU_A_AND_1, 0,     0,  BA_X,  BB_MDR)
firmware[77]  = make_micro(0,   JAM_NONE, ALU_B_1,     WR_PC, 0,  BA_PC, BB_PC,  save_flags=0)
firmware[333] = make_micro(9,   JAM_NONE, ALU_B,       0,     0,  BA_H,  BB_MDR, save_flags=0)

# ── 78: Y = Y - X  (B-A = Y-X) ───────────────────────────────────────────────
firmware[78] = make_micro(0, JAM_NONE, ALU_B_A, WR_Y, 0, BA_X, BB_Y)

# ── 79: X = X XOR Y ───────────────────────────────────────────────────────────
firmware[79] = make_micro(0, JAM_NONE, ALU_XOR,   WR_X, 0, BA_Y, BB_X)

# ── 80: X = |X|   (valor absoluto) ──────────────────────────────────────────
firmware[80] = make_micro(0, JAM_NONE, ALU_ABS_A, WR_X, 0, BA_X, BB_MDR)

# ==============================================================================
# Funções do núcleo
# ==============================================================================

def read_regs(reg_num):
    global MDR, PC, MBR, X, Y, H, Z1, Z2, BUS_A, BUS_B

    reg_numB = reg_num & 0b111
    reg_numA = (reg_num >> 3) & 0b111

    if   reg_numA == 0: BUS_A = H
    elif reg_numA == 1: BUS_A = MDR
    elif reg_numA == 2: BUS_A = PC
    elif reg_numA == 3: BUS_A = MBR
    elif reg_numA == 4: BUS_A = X
    elif reg_numA == 5: BUS_A = Y
    elif reg_numA == 6: BUS_A = Z1   # NOVO
    elif reg_numA == 7: BUS_A = Z2   # NOVO

    if   reg_numB == 0: BUS_B = MDR
    elif reg_numB == 1: BUS_B = PC
    elif reg_numB == 2: BUS_B = MBR
    elif reg_numB == 3: BUS_B = X
    elif reg_numB == 4: BUS_B = Y
    elif reg_numB == 5: BUS_B = Z1   # NOVO
    elif reg_numB == 6: BUS_B = Z2   # NOVO
    else:               BUS_B = 0


def write_regs(reg_bits):
    global MAR, MDR, PC, X, Y, H, Z1, Z2, BUS_C

    if reg_bits & WR_MAR: MAR = BUS_C
    if reg_bits & WR_MDR: MDR = BUS_C
    if reg_bits & WR_PC:  PC  = BUS_C
    if reg_bits & WR_X:   X   = BUS_C
    if reg_bits & WR_Y:   Y   = BUS_C
    if reg_bits & WR_H:   H   = BUS_C
    if reg_bits & WR_Z1:  Z1  = BUS_C   # NOVO
    if reg_bits & WR_Z2:  Z2  = BUS_C   # NOVO


def alu(control_bits, save_flags=1):
    """
    Executa a operação ALU.
    save_flags=0: opera normalmente mas NÃO atualiza N/Z (preserva flags do teste anterior).
    """
    global N, Z, BUS_A, BUS_B, BUS_C

    a = BUS_A
    b = BUS_B

    shift_bits   = (control_bits >> 6) & 0b11
    op           = control_bits & 0b00111111

    # ── Operações existentes ──────────────────────────────────────────────────
    if   op == 0b011000: o = a
    elif op == 0b010100: o = b
    elif op == 0b011010: o = ~a
    elif op == 0b101100: o = ~b
    elif op == 0b111100: o = a + b
    elif op == 0b111101: o = a + b + 1
    elif op == 0b111001: o = a + 1
    elif op == 0b110101: o = b + 1
    elif op == 0b111111: o = b - a
    elif op == 0b110110: o = b - 1
    elif op == 0b111011: o = -a
    elif op == 0b001100: o = a & b
    elif op == 0b011100: o = a | b
    elif op == 0b010000: o = 0
    elif op == 0b110001: o = 1
    elif op == 0b110010: o = -1
    # ── Novas operações ───────────────────────────────────────────────────────
    elif op == 0b000001: o = a & 1                                    # A & 1
    elif op == 0b000010: o = a ^ b                                    # A XOR B
    elif op == 0b000011:                                               # |A|
        o = a if not (a & 0x80000000) else (~a + 1) & 0xFFFFFFFF
    else:                o = 0

    o = o & 0xFFFFFFFF

    # Shift aplicado antes das flags (resultado final de BUS_C)
    if   shift_bits == 0b01: o = (o << 1) & 0xFFFFFFFF
    elif shift_bits == 0b10: o = o >> 1
    elif shift_bits == 0b11: o = (o << 8) & 0xFFFFFFFF

    # ── SAVE_FLAGS: só atualiza N/Z se permitido ──────────────────────────────
    if save_flags:
        if o == 0:
            N, Z = 0, 1
        elif o & 0x80000000:
            N, Z = 1, 0
        else:
            N, Z = 0, 0

    BUS_C = o


def next_instruction(nextadd, jam):
    """
    Calcula o próximo MPC com base no campo JAM e nas flags N/Z atuais.
    Adicionados: JAM_NOTZ (pula se Z=0) e JAM_NOTN (pula se N=0).
    """
    global MPC

    if   jam == JAM_NONE:  MPC = nextadd
    elif jam == JAM_Z:     MPC = nextadd | (Z << 8)
    elif jam == JAM_N:     MPC = nextadd | (N << 8)
    elif jam == JAM_NZ:    MPC = nextadd | ((N | Z) << 8)
    elif jam == JAM_MBR:   MPC = nextadd | MBR
    elif jam == JAM_NOTZ:  MPC = nextadd | ((1 - Z) << 8)   # NOVO
    elif jam == JAM_NOTN:  MPC = nextadd | ((1 - N) << 8)   # NOVO
    else:                  MPC = nextadd


def memory_io(mem_bits):
    global PC, MAR, MDR, MBR

    if mem_bits & MEM_FETCH: MBR = memoria.read_byte(PC)
    if mem_bits & MEM_READ:  MDR = memoria.read_word(MAR)
    if mem_bits & MEM_WRITE: memoria.write_word(MAR, MDR)


def step():
    global MIR, MPC

    MIR = firmware[MPC]
    if MIR == 0:
        return False

    save_flags = (MIR >> 37) & 1          # NOVO: bit 37

    read_regs(  MIR         & 0b111111)   # bits [5:0]
    alu(       (MIR >> 17)  & 0xFF,        # bits [24:17]
                save_flags)
    write_regs((MIR >>  9)  & 0xFF)       # bits [16:9]  (8 bits — NOVO)
    memory_io( (MIR >>  6)  & 0b111)      # bits [8:6]
    next_instruction(
               (MIR >> 28)  & 0x1FF,      # bits [36:28]
               (MIR >> 25)  & 0b111)      # bits [27:25]

    return True