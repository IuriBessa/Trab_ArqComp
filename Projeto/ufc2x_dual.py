# ufc2x_dual.py
# Versão com BARRAMENTO DUPLO (Dual Bus) completo.
#
# ==============================================================================
# MUDANÇAS GERAIS DESTA VERSÃO
# ==============================================================================
#
# 1. NOVO LAYOUT DO MIR (64 bits, todos utilizados):
#
#    ANTES (38 bits usados, 26 bits desperdiçados):
#    [37] SAVE_FLAGS | [36:28] NEXT_ADDR | [27:25] JAM | [24:17] ALU |
#    [16:9] WRITE | [8:6] MEM | [5:3] BUS_A | [2:0] BUS_B
#
#    AGORA (64 bits, dois barramentos independentes):
#    [63]    SAVE_FLAGS2  — salva flags da ALU2
#    [62:55] ALU2         — operação da segunda ALU (mesmo encoding da ALU1)
#    [54:52] BUS_A2       — entrada A da ALU2 (mesmo encoding de BUS_A1)
#    [51:49] BUS_B2       — entrada B da ALU2 (mesmo encoding de BUS_B1)
#    [48:46] WRITE2       — destino do resultado da ALU2 (encoding de 3 bits, abaixo)
#    [45:38] reservado    — livre para expansão futura
#    [37]    SAVE_FLAGS1  — salva flags da ALU1 (inalterado)
#    [36:28] NEXT_ADDR    — endereço da próxima microinstrução (inalterado)
#    [27:25] JAM          — controle de desvio condicional (inalterado)
#    [24:17] ALU1         — operação da primeira ALU (inalterado)
#    [16:9]  WRITE1       — destino do resultado da ALU1, 8 bits (inalterado)
#    [8:6]   MEM          — controle de memória (inalterado)
#    [5:3]   BUS_A1       — entrada A da ALU1 (inalterado)
#    [2:0]   BUS_B1       — entrada B da ALU1 (inalterado)
#
# 2. WRITE2 encoding (3 bits — registradores de dados + MAR + PC para fusões):
#    000 = nenhum  001 = X  010 = Y  011 = H
#    100 = Z1      101 = Z2  110 = MAR  111 = PC
#
# 3. ORDEM DE EXECUÇÃO EM step() — CRÍTICA PARA O DUAL BUS:
#    a) read_regs1 + alu1 + write_regs1  → ALU1 executa com registradores originais
#    b) memory_io                         → FETCH/READ/WRITE (MBR atualizado aqui)
#    c) read_regs2 + alu2 + write_regs2  → ALU2 lê MBR JÁ ATUALIZADO pelo FETCH
#    d) next_instruction                  → decide próximo MPC
#
#    Esta ordem é o que permite que ALU2 leia MBR no MESMO ciclo que ALU1 faz FETCH,
#    viabilizando a fusão de "PC=PC+1+FETCH" com "REG=MBR" em um único microciclo.
#
# 4. GANHOS DE CICLOS (resumo):
#    - X/Y/Z1/Z2/H = imediato:  2 ciclos → 1 ciclo  (5 instruções)
#    - SWAP X,Y:                 3 ciclos → 1 ciclo
#    - CALL:                     3 ciclos → 2 ciclos
#    - Todos os loads  (REG=mem[addr]):   3 ciclos → 2 ciclos  (6 instruções)
#    - Todos os stores (mem[addr]=REG):   3 ciclos → 2 ciclos  (4 instruções)
#    Total: ~20 slots de firmware liberados para novos opcodes futuros.
#
# 5. SLOTS LIBERADOS PELAS OTIMIZAÇÕES (agora livres para novos opcodes):
#    3, 7, 14, 23, 26, 29, 98, 103, 123, 128, 130, 131, 133, 135, 136,
#    149, 152, 155, 157, 173
#
# 6. COMPATIBILIDADE: Todos os firmwares inalterados continuam funcionando
#    corretamente pois os bits 46..63 valem zero neles → ALU2 inativa (WRITE2=000).
#
# ==============================================================================

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

# ==============================================================================
# CONSTANTES AUXILIARES PARA MONTAR OS BITS DA ALU2 / BUS_A2 / BUS_B2 / WRITE2
# Facilitam a leitura e evitam erros ao compor microinstruções dual-bus.
# ==============================================================================

# WRITE2 (bits 48:46) — destino do resultado da ALU2
W2_NONE = 0b000  # não escreve
W2_X    = 0b001
W2_Y    = 0b010
W2_H    = 0b011
W2_Z1   = 0b100
W2_Z2   = 0b101
W2_MAR  = 0b110
W2_PC   = 0b111

# BUS_A2 (bits 54:52) — mesmo encoding de BUS_A1
# 000=H 001=MDR 010=PC 011=MBR 100=X 101=Y 110=Z1 111=Z2
A2_H   = 0b000
A2_MDR = 0b001
A2_PC  = 0b010
A2_MBR = 0b011
A2_X   = 0b100
A2_Y   = 0b101
A2_Z1  = 0b110
A2_Z2  = 0b111

# BUS_B2 (bits 51:49) — mesmo encoding de BUS_B1
# 000=MDR 001=PC 010=MBR 011=X 100=Y 101=Z1 110=Z2 111=0
B2_MDR = 0b000
B2_PC  = 0b001
B2_MBR = 0b010
B2_X   = 0b011
B2_Y   = 0b100
B2_Z1  = 0b101
B2_Z2  = 0b110
B2_0   = 0b111

# ALU2 operations (bits 62:55) — mesmo encoding da ALU1
ALU2_B     = 0b00010100  # passa BUS_B2
ALU2_A     = 0b00011000  # passa BUS_A2
ALU2_ZERO  = 0b00010000  # saída = 0
ALU2_ApB   = 0b00111100  # A2 + B2
ALU2_BmA   = 0b00111111  # B2 - A2
ALU2_Bp1   = 0b00110101  # B2 + 1
ALU2_Bm1   = 0b00110110  # B2 - 1
ALU2_Ap1   = 0b00111001  # A2 + 1


def _dual(alu2=ALU2_B, a2=A2_MBR, b2=B2_MBR, w2=W2_NONE, sf2=0):
    """
    Retorna os bits 46..63 para compor uma microinstrução dual-bus.
    Uso: firmware[N] = base_mir | _dual(alu2, a2, b2, w2, sf2)

    Parâmetros:
      alu2 : código ALU2 (8 bits, bits 62:55)
      a2   : seletor BUS_A2 (3 bits, bits 54:52)
      b2   : seletor BUS_B2 (3 bits, bits 51:49)
      w2   : destino WRITE2  (3 bits, bits 48:46)
      sf2  : SAVE_FLAGS2     (1 bit,  bit  63)
    """
    return (
        (sf2  << 63) |
        (alu2 << 55) |
        (a2   << 52) |
        (b2   << 49) |
        (w2   << 46)
    )

# ==============================================================================
# LAYOUT DO MIR — PARTE BAIXA (bits 0..37, inalterada):
# [37] SAVE_FLAGS1 | [36:28] NEXT_ADDR | [27:25] JAM | [24:17] ALU1
# [16:9] WRITE1    | [8:6]   MEM       | [5:3]  BUS_A1 | [2:0] BUS_B1
#
# BUS_A1 seletores (bits 5:3): 000=H  001=MDR 010=PC 011=MBR 100=X 101=Y 110=Z1 111=Z2
# BUS_B1 seletores (bits 2:0): 000=MDR 001=PC  010=MBR 011=X  100=Y  101=Z1 110=Z2 111=0
# ==============================================================================

# ------------------------------------------------------------------------------
# OPCODE 0: INIT/FETCH — PC = PC+1; FETCH; GOTO MBR
# INALTERADO — não há segunda operação útil aqui.
# BUS_A1=PC(010), BUS_B1=PC(001), ALU1=B+1, WRITE1=PC, MEM=FETCH, JAM=MBR(100)
# ------------------------------------------------------------------------------
firmware[0] = 0b1_000000000_100_00110101_00100000_001_010_001


# ==============================================================================
# OPCODE 2: X = X + mem[address]
#
# ANTES (3 ciclos):
#   [2] PC=PC+1; FETCH; GOTO 3
#   [3] MAR=MBR; READ; GOTO 4          ← ciclo agora ELIMINADO
#   [4] X = MDR + X
#
# AGORA (2 ciclos) — DUAL BUS:
#   [2] ALU1: PC=PC+1, FETCH, WRITE=PC   |  ALU2: MAR=MBR (lê MBR pós-FETCH); GOTO 4
#   [4] X = MDR + X
#
# MUDANÇA: ciclo [3] eliminado. ALU2 escreve MAR=MBR no mesmo ciclo que ALU1 faz FETCH.
# Slot 3 fica LIVRE.
# ==============================================================================

# [2] DUAL: ALU1=PC+1+FETCH+WRITE_PC  |  ALU2=MAR=MBR(pós-fetch)
firmware[2] = (
    0b0_000000100_000_00110101_00100000_001_010_001  # base: GOTO 4, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)         # ALU2: MAR = MBR
)
# [3] SLOT LIVRE — era "MAR=MBR; READ; GOTO 4"
# firmware[3] = 0b0_000000100_000_00010100_10000000_010_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 2 (MAR=MBR) e READ movido para ciclo 4.

# [4] X = MDR + X; READ ativado aqui; GOTO 0
# BUS_A1=MDR(001), BUS_B1=X(011), ALU1=A+B, WRITE1=X, MEM=READ(010)
# MUDANÇA: MEM=READ(010) adicionado aqui pois MAR já foi carregado no ciclo 2.
firmware[4] = 0b1_000000000_000_00111100_00010000_010_001_011


# ==============================================================================
# OPCODE 6: memory[address] = X
#
# ANTES (3 ciclos):
#   [6]  PC=PC+1; FETCH; GOTO 7
#   [7]  MAR=MBR; GOTO 8               ← ciclo agora ELIMINADO
#   [8]  MDR=X; WRITE_WORD; GOTO 0
#
# AGORA (2 ciclos) — DUAL BUS:
#   [6]  ALU1: PC=PC+1, FETCH  |  ALU2: MAR=MBR (pós-fetch); GOTO 8
#   [8]  MDR=X; WRITE_WORD; GOTO 0
#
# MUDANÇA: ciclo [7] eliminado. Slot 7 fica LIVRE.
# ==============================================================================

# [6] DUAL: PC=PC+1+FETCH  |  MAR=MBR
firmware[6] = (
    0b0_000001000_000_00110101_00100000_001_010_001  # base: GOTO 8, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [7] SLOT LIVRE — era "MAR=MBR; GOTO 8"
# firmware[7] = 0b0_000001000_000_00010100_10000000_000_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 6.

# [8] MDR=X; WRITE_WORD; GOTO 0 — INALTERADO
firmware[8] = 0b0_000000000_000_00010100_01000000_100_000_011


# ==============================================================================
# OPCODE 9: GOTO address — INALTERADO (2 ciclos, não há ganho possível)
# ==============================================================================
firmware[9]  = 0b0_000001010_000_00110101_00100000_001_010_001
firmware[10] = 0b0_000000000_100_00010100_00100000_001_000_010


# ==============================================================================
# OPCODE 11: IF X == 0 GOTO address — INALTERADO
# O ciclo de teste e o JAM dependem do resultado da ALU1, e o ciclo 12 apenas
# descarta o byte de endereço — não há segunda operação útil.
# ==============================================================================
firmware[11]  = 0b1_000001100_001_00010100_00000000_000_000_011
firmware[12]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[268] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# OPCODE 13: X = X - mem[address]
#
# ANTES (3 ciclos):  [13] FETCH  [14] MAR=MBR;READ  [15] X=X-MDR
# AGORA (2 ciclos):  [13] FETCH+MAR=MBR(dual)       [15] READ+X=X-MDR
#
# MUDANÇA: ciclo [14] eliminado. Slot 14 fica LIVRE.
# ==============================================================================

# [13] DUAL: PC=PC+1+FETCH  |  MAR=MBR
firmware[13] = (
    0b0_000001111_000_00110101_00100000_001_010_001  # GOTO 15, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [14] SLOT LIVRE — era "MAR=MBR; READ; GOTO 15"
# firmware[14] = 0b0_000001111_000_00010100_10000000_010_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 13.

# [15] X = X - MDR; READ; GOTO 0
# BUS_A1=MDR(001), BUS_B1=X(011), ALU1=B-A, WRITE1=X, MEM=READ
firmware[15] = 0b1_000000000_000_00111111_00010000_010_001_011


# ==============================================================================
# OPCODES 16,17: X++ / X-- — INALTERADOS (1 ciclo, não há ganho)
# ==============================================================================
firmware[16] = 0b1_000000000_000_00110101_00010000_000_000_011
firmware[17] = 0b1_000000000_000_00110110_00010000_000_000_011


# ==============================================================================
# OPCODE 18: IF X < 0 GOTO address — INALTERADO
# ==============================================================================
firmware[18]  = 0b1_000010011_010_00010100_00000000_000_000_011
firmware[19]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[275] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# OPCODES 20,21: Y=X / X=Y — INALTERADOS (1 ciclo, não há ganho)
# ==============================================================================
firmware[20] = 0b1_000000000_000_00010100_00001000_000_000_011
firmware[21] = 0b1_000000000_000_00010100_00010000_000_000_100


# ==============================================================================
# OPCODE 22: memory[address] = Y
#
# ANTES (3 ciclos):  [22] FETCH  [23] MAR=MBR  [24] MDR=Y; WRITE
# AGORA (2 ciclos):  [22] FETCH+MAR=MBR(dual)  [24] MDR=Y; WRITE
#
# MUDANÇA: ciclo [23] eliminado. Slot 23 fica LIVRE.
# ==============================================================================

firmware[22] = (
    0b0_000011000_000_00110101_00100000_001_010_001  # GOTO 24, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [23] SLOT LIVRE — era "MAR=MBR; GOTO 24"
# firmware[23] = 0b0_000011000_000_00010100_10000000_000_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 22.

firmware[24] = 0b0_000000000_000_00010100_01000000_100_000_100  # INALTERADO


# ==============================================================================
# OPCODE 25: Y = Y + mem[address]
#
# ANTES (3 ciclos):  [25] FETCH  [26] MAR=MBR;READ  [27] Y=MDR+Y
# AGORA (2 ciclos):  [25] FETCH+MAR=MBR(dual)       [27] READ+Y=MDR+Y
#
# MUDANÇA: ciclo [26] eliminado. Slot 26 fica LIVRE.
# ==============================================================================

firmware[25] = (
    0b0_000011011_000_00110101_00100000_001_010_001  # GOTO 27, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [26] SLOT LIVRE — era "MAR=MBR; READ; GOTO 27"
# firmware[26] = 0b0_000011011_000_00010100_10000000_010_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 25.

# [27] Y = MDR + Y; READ; GOTO 0
firmware[27] = 0b1_000000000_000_00111100_00001000_010_001_100


# ==============================================================================
# OPCODE 28: Y = mem[address]
#
# ANTES (3 ciclos):  [28] FETCH  [29] MAR=MBR;READ  [30] Y=MDR
# AGORA (2 ciclos):  [28] FETCH+MAR=MBR(dual)       [30] READ+Y=MDR
#
# MUDANÇA: ciclo [29] eliminado. Slot 29 fica LIVRE.
# ==============================================================================

firmware[28] = (
    0b0_000011110_000_00110101_00100000_001_010_001  # GOTO 30, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [29] SLOT LIVRE — era "MAR=MBR; READ; GOTO 30"
# firmware[29] = 0b0_000011110_000_00010100_10000000_010_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 28.

# [30] Y=MDR; READ; GOTO 0
firmware[30] = 0b1_000000000_000_00010100_00001000_010_000_000


# ==============================================================================
# OPCODES 31,32,33,34: shifts e incrementos — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[31] = 0b1_000000000_000_01010100_00010000_000_000_011
firmware[32] = 0b1_000000000_000_10010100_00010000_000_000_011
firmware[33] = 0b1_000000000_000_00110101_00001000_000_000_100
firmware[34] = 0b1_000000000_000_00110110_00001000_000_000_100


# ==============================================================================
# OPCODE 35: IF Y == 0 GOTO address — INALTERADO
# ==============================================================================
firmware[35]  = 0b1_000100100_001_00010100_00000000_000_000_100
firmware[36]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[292] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# OPCODE 40: X = mem[addr]
#
# ANTES (3 ciclos):  [40] FETCH  [128] MAR=MBR;READ  [129] X=MDR
# AGORA (2 ciclos):  [40] FETCH+MAR=MBR(dual)        [129] READ+X=MDR
#
# MUDANÇA: ciclo [128] eliminado. Slot 128 fica LIVRE.
# NOTA: manteve GOTO 129 para preservar o slot final original.
# ==============================================================================

firmware[40] = (
    0b0_010000001_000_00110101_00100000_001_010_001  # GOTO 129, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [128] SLOT LIVRE — era "MAR=MBR; READ; GOTO 129"
# firmware[128] = 0b0_010000001_000_00010100_10000000_010_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 40.

# [129] X=MDR; READ; GOTO 0
firmware[129] = 0b1_000000000_000_00010100_00010000_010_000_000


# ==============================================================================
# OPCODES 41,42: X=0 / Y=0 — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[41] = 0b1_000000000_000_00010000_00010000_000_000_000
firmware[42] = 0b1_000000000_000_00010000_00001000_000_000_000


# ==============================================================================
# OPCODE 43: IF X <= 0 GOTO address — INALTERADO
# ==============================================================================
firmware[43]  = 0b1_010000100_011_00010100_00000000_000_000_011
firmware[132] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[388] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# OPCODES 45,46,47: operações X/Y — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[45] = 0b1_000000000_000_00111100_00010000_000_101_011
firmware[46] = 0b1_000000000_000_00111111_00010000_000_101_011
firmware[47] = 0b1_000000000_000_00111100_00001000_000_101_011


# ==============================================================================
# OPCODE 48: SWAP X, Y
#
# ANTES (3 ciclos):
#   [48]  H = X
#   [130] X = Y
#   [131] Y = H
#
# AGORA (1 ciclo) — DUAL BUS:
#   [48]  ALU1: X = Y  |  ALU2: Y = X
#   (Leitura de X e Y ocorre ANTES da escrita → sem hazard de dados)
#
# MUDANÇA: redução de 3→1 ciclo. Slots 130 e 131 ficam LIVRES.
# ==============================================================================

# [48] DUAL: X=Y (ALU1) | Y=X (ALU2) — simultaneamente, sem hazard
# ALU1: BUS_B1=Y(100), ALU1=B, WRITE1=X(00010000)
# ALU2: BUS_B2=X(011), ALU2=B, WRITE2=Y(010)
firmware[48] = (
    0b1_000000000_000_00010100_00010000_000_000_100  # ALU1: X=Y, GOTO 0
    | _dual(ALU2_B, A2_MBR, B2_X, W2_Y)             # ALU2: Y=X (BUS_B2=X)
)
# [130] SLOT LIVRE — era "X = Y; GOTO 131"
# firmware[130] = 0b0_010000011_000_00010100_00010000_000_000_100
# REMOVIDO: SWAP agora é 1 ciclo via dual bus.

# [131] SLOT LIVRE — era "Y = H; GOTO 0"
# firmware[131] = 0b1_000000000_000_00011000_00001000_000_000_000
# REMOVIDO: idem acima.


# ==============================================================================
# OPCODES 49,50: Y<<1 / Y>>1 — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[49] = 0b1_000000000_000_01010100_00001000_000_000_100
firmware[50] = 0b1_000000000_000_10010100_00001000_000_000_100


# ==============================================================================
# OPCODES 53,54,55,56: transferências H — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[53] = 0b0_000000000_000_00010100_00000100_000_000_011
firmware[54] = 0b1_000000000_000_00011000_00010000_000_000_000
firmware[55] = 0b0_000000000_000_00010100_00000100_000_000_100
firmware[56] = 0b1_000000000_000_00011000_00001000_000_000_000


# ==============================================================================
# OPCODES 57,58,59,60: condicionais Y — INALTERADOS
# ==============================================================================
firmware[57]  = 0b1_000111010_011_00010100_00000000_000_000_100
firmware[58]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[314] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[59]  = 0b1_000111100_010_00010100_00000000_000_000_100
firmware[60]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[316] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# OPCODE 61: Y = Y - mem[addr]
#
# ANTES (3 ciclos):  [61] FETCH  [133] MAR=MBR;READ  [134] Y=Y-MDR
# AGORA (2 ciclos):  [61] FETCH+MAR=MBR(dual)        [134] READ+Y=Y-MDR
#
# MUDANÇA: ciclo [133] eliminado. Slot 133 fica LIVRE.
# ==============================================================================

firmware[61] = (
    0b0_010000110_000_00110101_00100000_001_010_001  # GOTO 134, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [133] SLOT LIVRE — era "MAR=MBR; READ; GOTO 134"
# firmware[133] = 0b0_010000110_000_00010100_10000000_010_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 61.

# [134] Y = Y - MDR; READ; GOTO 0
# BUS_A1=MDR(001), BUS_B1=Y(100), ALU1=B-A, WRITE1=Y
firmware[134] = 0b1_000000000_000_00111111_00001000_010_001_100


# ==============================================================================
# OPCODES 64,65: AND / OR — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[64] = 0b1_000000000_000_00001100_00010000_000_101_011
firmware[65] = 0b1_000000000_000_00011100_00010000_000_101_011


# ==============================================================================
# OPCODE 66: X = immediate
#
# ANTES (2 ciclos):
#   [66]  PC=PC+1; FETCH; GOTO 135
#   [135] X = MBR
#
# AGORA (1 ciclo) — DUAL BUS:
#   [66]  ALU1: PC=PC+1, FETCH  |  ALU2: X = MBR (pós-fetch)
#
# MUDANÇA: redução de 2→1 ciclo. Slot 135 fica LIVRE.
# A ALU2 lê MBR APÓS o FETCH da ALU1 (graças à ordem de execução em step()).
# ==============================================================================

firmware[66] = (
    0b0_000000000_100_00110101_00100000_001_010_001  # PC=PC+1, FETCH, JAM=MBR(GOTO MBR)
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_X, sf2=1)   # ALU2: X=MBR, save_flags2=1
)
# [135] SLOT LIVRE — era "X = MBR"
# firmware[135] = 0b1_000000000_000_00010100_00010000_000_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 66.


# ==============================================================================
# OPCODE 67: Y = immediate
#
# ANTES (2 ciclos):  [67] FETCH  [136] Y=MBR
# AGORA (1 ciclo):   [67] FETCH+Y=MBR(dual)
#
# MUDANÇA: redução de 2→1 ciclo. Slot 136 fica LIVRE.
# ==============================================================================

firmware[67] = (
    0b0_000000000_100_00110101_00100000_001_010_001  # PC=PC+1, FETCH, JAM=MBR
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_Y, sf2=1)   # ALU2: Y=MBR, save_flags2=1
)
# [136] SLOT LIVRE — era "Y = MBR"
# firmware[136] = 0b1_000000000_000_00010100_00001000_000_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 67.


# ==============================================================================
# OPCODES 68-75: transferências Z1/Z2 — INALTERADOS (1 ciclo cada)
# ==============================================================================
firmware[68] = 0b0_000000000_000_00010100_00000010_000_000_011  # Z1 = X
firmware[69] = 0b0_000000000_000_00010100_00000010_000_000_100  # Z1 = Y
firmware[70] = 0b1_000000000_000_00010100_00010000_000_000_101  # X = Z1
firmware[71] = 0b1_000000000_000_00010100_00001000_000_000_101  # Y = Z1
firmware[72] = 0b0_000000000_000_00010100_00000001_000_000_011  # Z2 = X
firmware[73] = 0b0_000000000_000_00010100_00000001_000_000_100  # Z2 = Y
firmware[74] = 0b1_000000000_000_00010100_00010000_000_000_110  # X = Z2
firmware[75] = 0b1_000000000_000_00010100_00001000_000_000_110  # Y = Z2


# ==============================================================================
# OPCODE 76: IF X = odd GOTO addr — INALTERADO
# ==============================================================================
firmware[76]  = 0b1_001001101_101_00000001_00000000_000_100_000
firmware[77]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[333] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# OPCODES 78,79,80: Y-X, XOR, |X| — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[78] = 0b1_000000000_000_00111111_00001000_000_100_100
firmware[79] = 0b1_000000000_000_00000010_00010000_000_101_011
firmware[80] = 0b1_000000000_000_00000011_00010000_000_100_000


# ==============================================================================
# OPCODES 83,84: Z1--/Z1++ — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[83] = 0b1_000000000_000_00110110_00000010_000_000_101
firmware[84] = 0b1_000000000_000_00110101_00000010_000_000_101


# ==============================================================================
# OPCODE 85: IF Z1 == 0 GOTO address — INALTERADO
# ==============================================================================
firmware[85]  = 0b1_001010110_001_00010100_00000000_000_000_101
firmware[86]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[342] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# OPCODE 87: Z1 = immediate
#
# ANTES (2 ciclos):  [87] FETCH  [173] Z1=MBR
# AGORA (1 ciclo):   [87] FETCH+Z1=MBR(dual)
#
# MUDANÇA: redução de 2→1 ciclo. Slot 173 fica LIVRE.
# ==============================================================================

firmware[87] = (
    0b0_000000000_100_00110101_00100000_001_010_001  # PC=PC+1, FETCH, JAM=MBR
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_Z1)          # ALU2: Z1=MBR
)
# [173] SLOT LIVRE — era "Z1 = MBR"
# firmware[173] = 0b1_000000000_000_00010100_00000010_000_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 87.


# ==============================================================================
# PRIORIDADE 1 — Aritmética direta em H e Z2 — INALTERADOS (1 ciclo cada)
# ==============================================================================
firmware[88] = 0b1_000000000_000_00111001_00000100_000_000_000  # H = H+1
firmware[89] = 0b1_000000000_000_00111010_00000100_000_000_000  # H = H-1
firmware[90] = 0b1_000000000_000_00110110_00000001_000_000_110  # Z2 = Z2-1
firmware[91] = 0b1_000000000_000_00110101_00000001_000_000_110  # Z2 = Z2+1


# ==============================================================================
# OPCODE 92: IF Z2 == 0 GOTO address — INALTERADO
# ==============================================================================
firmware[92]  = 0b1_001011101_001_00010100_00000000_000_000_110
firmware[93]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[349] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# PRIORIDADE 2 — Zeros diretos — INALTERADOS (1 ciclo cada)
# ==============================================================================
firmware[94] = 0b1_000000000_000_00010000_00000100_000_000_000  # H  = 0
firmware[95] = 0b1_000000000_000_00010000_00000010_000_000_000  # Z1 = 0
firmware[96] = 0b1_000000000_000_00010000_00000001_000_000_000  # Z2 = 0


# ==============================================================================
# OPCODE 97: mem[address] = Z1
#
# ANTES (3 ciclos):  [97] FETCH  [98] MAR=MBR  [99] MDR=Z1; WRITE
# AGORA (2 ciclos):  [97] FETCH+MAR=MBR(dual)  [99] MDR=Z1; WRITE
#
# MUDANÇA: ciclo [98] eliminado. Slot 98 fica LIVRE.
# ==============================================================================

firmware[97] = (
    0b0_001100011_000_00110101_00100000_001_010_001  # GOTO 99, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [98] SLOT LIVRE — era "MAR=MBR; GOTO 99"
# firmware[98] = 0b0_001100011_000_00010100_10000000_000_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 97.

firmware[99] = 0b0_000000000_000_00010100_01000000_100_000_101  # INALTERADO


# ==============================================================================
# OPCODE 100: IF X >= 0 GOTO address — INALTERADO
# ==============================================================================
firmware[100] = 0b1_001100101_110_00010100_00000000_000_000_011
firmware[101] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[357] = 0b0_000001001_000_00010100_00000000_000_000_000

# HALT — INALTERADO
firmware[255] = 0b0_000000000_000_00000000_00000000_000_000_000


# ==============================================================================
# OPCODE 102: CALL address
#
# ANTES (3 ciclos):
#   [102] PC=PC+1; FETCH; GOTO 103
#   [103] Z2=PC   (salva endereço de retorno)       ← ELIMINADO
#   [104] PC=MBR; FETCH; GOTO MBR
#
# AGORA (2 ciclos) — DUAL BUS:
#   [102] ALU1: PC=PC+1, FETCH  |  ALU2: Z2=PC (salva retorno); GOTO 104
#   [104] PC=MBR; FETCH; GOTO MBR
#
# MUDANÇA: redução de 3→2 ciclos. Slot 103 fica LIVRE.
# DETALHE: Z2=PC usa o valor de PC ANTES do incremento? Não — ALU1 escreve PC=PC+1
# em write_regs1, DEPOIS ALU2 lê via read_regs2. Portanto Z2 recebe PC já incrementado,
# que é exatamente o endereço de retorno correto (próxima instrução após o CALL).
# ==============================================================================

firmware[102] = (
    0b0_001101000_000_00110101_00100000_001_010_001  # GOTO 104, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_PC, W2_Z2)           # ALU2: Z2=PC (pós-incremento)
)
# [103] SLOT LIVRE — era "Z2 = PC; GOTO 104"
# firmware[103] = 0b0_001101000_000_00010100_00000001_000_000_001
# REMOVIDO: absorvido pela ALU2 do ciclo 102.

firmware[104] = 0b0_000000000_100_00010100_00100000_001_000_010  # INALTERADO


# ==============================================================================
# OPCODE 105: RET — INALTERADO (1 ciclo, já mínimo possível)
# ==============================================================================
firmware[105] = 0b0_000000000_100_00010100_00100000_001_000_110


# ==============================================================================
# OPCODES 106,107,108,109: condicionais Z1 — INALTERADOS
# ==============================================================================
firmware[106] = 0b1_001101011_010_00010100_00000000_000_000_101
firmware[107] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[363] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[108] = 0b1_001101101_011_00010100_00000000_000_000_101
firmware[109] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[365] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# OPCODES 110,111,112,113,114,115: condicionais H — INALTERADOS
# ==============================================================================
firmware[110] = 0b1_001101111_001_00011000_00000000_000_000_000
firmware[111] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[367] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[112] = 0b1_001110001_010_00011000_00000000_000_000_000
firmware[113] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[369] = 0b0_000001001_000_00010100_00000000_000_000_000

firmware[114] = 0b1_001110011_011_00011000_00000000_000_000_000
firmware[115] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[371] = 0b0_000001001_000_00010100_00000000_000_000_000


# ==============================================================================
# OPCODES 116-121: transferências diretas entre temporários — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[116] = 0b0_000000000_000_00011000_00000010_000_000_000  # Z1 = H
firmware[117] = 0b0_000000000_000_00010100_00000100_000_000_101  # H  = Z1
firmware[118] = 0b0_000000000_000_00011000_00000001_000_000_000  # Z2 = H
firmware[119] = 0b0_000000000_000_00010100_00000100_000_000_110  # H  = Z2
firmware[120] = 0b0_000000000_000_00010100_00000001_000_000_101  # Z2 = Z1
firmware[121] = 0b0_000000000_000_00010100_00000010_000_000_110  # Z1 = Z2


# ==============================================================================
# OPCODE 122: mem[address] = Z2
#
# ANTES (3 ciclos):  [122] FETCH  [123] MAR=MBR  [124] MDR=Z2; WRITE
# AGORA (2 ciclos):  [122] FETCH+MAR=MBR(dual)   [124] MDR=Z2; WRITE
#
# MUDANÇA: ciclo [123] eliminado. Slot 123 fica LIVRE.
# ==============================================================================

firmware[122] = (
    0b0_001111100_000_00110101_00100000_001_010_001  # GOTO 124, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [123] SLOT LIVRE — era "MAR=MBR; GOTO 124"
# firmware[123] = 0b0_001111100_000_00010100_10000000_000_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 122.

firmware[124] = 0b0_000000000_000_00010100_01000000_100_000_110  # INALTERADO


# ==============================================================================
# OPCODES 125,126,127,137: aritmética X/Y com Z1 — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[125] = 0b1_000000000_000_00111100_00010000_000_110_011  # X = X+Z1
firmware[126] = 0b1_000000000_000_00111111_00010000_000_110_011  # X = X-Z1
firmware[127] = 0b1_000000000_000_00111100_00001000_000_110_100  # Y = Y+Z1
firmware[137] = 0b1_000000000_000_00111111_00001000_000_110_100  # Y = Y-Z1


# ==============================================================================
# OPCODES 140-147: endereçamento indireto via Z1 — INALTERADOS (2 ciclos)
# Já são 2 ciclos — não há ganho adicional pois READ não pode ser antecipado.
# ==============================================================================
firmware[140] = 0b0_010001101_000_00010100_10000000_010_000_101  # X=mem[Z1] c1
firmware[141] = 0b1_000000000_000_00010100_00010000_000_000_000  # X=mem[Z1] c2
firmware[142] = 0b0_010001111_000_00010100_10000000_010_000_101  # Y=mem[Z1] c1
firmware[143] = 0b1_000000000_000_00010100_00001000_000_000_000  # Y=mem[Z1] c2
firmware[144] = 0b0_010010001_000_00010100_10000000_000_000_101  # mem[Z1]=X c1
firmware[145] = 0b0_000000000_000_00010100_01000000_100_000_011  # mem[Z1]=X c2
firmware[146] = 0b0_010010011_000_00010100_10000000_000_000_101  # mem[Z1]=Y c1
firmware[147] = 0b0_000000000_000_00010100_01000000_100_000_100  # mem[Z1]=Y c2


# ==============================================================================
# OPCODE 148: Z1 = mem[addr]
#
# ANTES (3 ciclos):  [148] FETCH  [149] MAR=MBR;READ  [150] Z1=MDR
# AGORA (2 ciclos):  [148] FETCH+MAR=MBR(dual)        [150] READ+Z1=MDR
#
# MUDANÇA: ciclo [149] eliminado. Slot 149 fica LIVRE.
# ==============================================================================

firmware[148] = (
    0b0_010010110_000_00110101_00100000_001_010_001  # GOTO 150, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [149] SLOT LIVRE — era "MAR=MBR; READ; GOTO 150"
# firmware[149] = 0b0_010010110_000_00010100_10000000_010_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 148.

# [150] Z1=MDR; READ; GOTO 0
firmware[150] = 0b1_000000000_000_00010100_00000010_010_000_000


# ==============================================================================
# OPCODE 151: Z2 = mem[addr]
#
# ANTES (3 ciclos):  [151] FETCH  [152] MAR=MBR;READ  [153] Z2=MDR
# AGORA (2 ciclos):  [151] FETCH+MAR=MBR(dual)        [153] READ+Z2=MDR
#
# MUDANÇA: ciclo [152] eliminado. Slot 152 fica LIVRE.
# ==============================================================================

firmware[151] = (
    0b0_010011001_000_00110101_00100000_001_010_001  # GOTO 153, FETCH, PC=PC+1
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR)
)
# [152] SLOT LIVRE — era "MAR=MBR; READ; GOTO 153"
# firmware[152] = 0b0_010011001_000_00010100_10000000_010_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 151.

# [153] Z2=MDR; READ; GOTO 0
firmware[153] = 0b1_000000000_000_00010100_00000001_010_000_000


# ==============================================================================
# OPCODE 154: Z2 = immediate
#
# ANTES (2 ciclos):  [154] FETCH  [155] Z2=MBR
# AGORA (1 ciclo):   [154] FETCH+Z2=MBR(dual)
#
# MUDANÇA: redução de 2→1 ciclo. Slot 155 fica LIVRE.
# ==============================================================================

firmware[154] = (
    0b0_000000000_100_00110101_00100000_001_010_001  # PC=PC+1, FETCH, JAM=MBR
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_Z2)          # ALU2: Z2=MBR
)
# [155] SLOT LIVRE — era "Z2 = MBR"
# firmware[155] = 0b1_000000000_000_00010100_00000001_000_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 154.


# ==============================================================================
# OPCODE 156: H = immediate
#
# ANTES (2 ciclos):  [156] FETCH  [157] H=MBR
# AGORA (1 ciclo):   [156] FETCH+H=MBR(dual)
#
# MUDANÇA: redução de 2→1 ciclo. Slot 157 fica LIVRE.
# ==============================================================================

firmware[156] = (
    0b0_000000000_100_00110101_00100000_001_010_001  # PC=PC+1, FETCH, JAM=MBR
    | _dual(ALU2_B, A2_MBR, B2_MBR, W2_H)           # ALU2: H=MBR
)
# [157] SLOT LIVRE — era "H = MBR"
# firmware[157] = 0b0_000000000_000_00010100_00000100_000_000_010
# REMOVIDO: absorvido pela ALU2 do ciclo 156.


# ==============================================================================
# OPCODES 158,159: cálculo direto em Z1 — INALTERADOS (1 ciclo)
# ==============================================================================
firmware[158] = 0b1_000000000_000_00111100_00000010_000_101_011  # Z1 = X+Y
firmware[159] = 0b1_000000000_000_00111111_00000010_000_101_011  # Z1 = X-Y


# ==============================================================================
# FUNÇÕES DO PROCESSADOR
# ==============================================================================

def read_regs(bus_a_sel, bus_b_sel):
    """
    Carrega BUS_A e BUS_B de acordo com os seletores de 3 bits.
    Usada tanto para ALU1 (com bits 5:3 e 2:0 do MIR)
    quanto para ALU2 (com bits 54:52 e 51:49 do MIR).

    BUS_A seletores: 000=H 001=MDR 010=PC 011=MBR 100=X 101=Y 110=Z1 111=Z2
    BUS_B seletores: 000=MDR 001=PC 010=MBR 011=X 100=Y 101=Z1 110=Z2 111=0
    """
    global MDR, PC, MBR, X, Y, H, BUS_A, BUS_B, Z1, Z2

    reg_table_A = [H, MDR, PC, MBR, X, Y, Z1, Z2]
    reg_table_B = [MDR, PC, MBR, X, Y, Z1, Z2, 0]

    BUS_A = reg_table_A[bus_a_sel & 0b111]
    BUS_B = reg_table_B[bus_b_sel & 0b111]


def write_regs(reg_bits):
    """
    Escreve BUS_C nos registradores indicados pelos 8 bits de WRITE1.
    Inalterada — usada exclusivamente pela ALU1.
    """
    global MAR, MDR, PC, X, Y, H, BUS_C, Z1, Z2

    if reg_bits & 0b10000000: MAR = BUS_C
    if reg_bits & 0b01000000: MDR = BUS_C
    if reg_bits & 0b00100000: PC  = BUS_C
    if reg_bits & 0b00010000: X   = BUS_C
    if reg_bits & 0b00001000: Y   = BUS_C
    if reg_bits & 0b00000100: H   = BUS_C
    if reg_bits & 0b00000010: Z1  = BUS_C
    if reg_bits & 0b00000001: Z2  = BUS_C


def write_regs2(w2, val):
    """
    NOVO — escreve val no registrador indicado pelo código WRITE2 (3 bits).
    Usado exclusivamente pela ALU2.

    Encoding:
      000=nenhum  001=X  010=Y  011=H
      100=Z1      101=Z2  110=MAR  111=PC
    """
    global X, Y, H, Z1, Z2, MAR, PC

    if   w2 == W2_X:   X   = val
    elif w2 == W2_Y:   Y   = val
    elif w2 == W2_H:   H   = val
    elif w2 == W2_Z1:  Z1  = val
    elif w2 == W2_Z2:  Z2  = val
    elif w2 == W2_MAR: MAR = val
    elif w2 == W2_PC:  PC  = val
    # W2_NONE (000): não faz nada


def alu(control_bits, save_flags):
    """
    ALU — INALTERADA. Lê BUS_A e BUS_B, escreve resultado em BUS_C.
    Atualiza N e Z se save_flags=1.
    """
    global N, Z, BUS_A, BUS_B, BUS_C

    a = BUS_A
    b = BUS_B
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

    if shift_bits == 0b01: o = (o << 1) & 0xFFFFFFFF
    elif shift_bits == 0b10: o = o >> 1
    elif shift_bits == 0b11: o = (o << 8) & 0xFFFFFFFF

    if save_flags:
        if o == 0:             N = 0; Z = 1
        elif o & 0x80000000:   N = 1; Z = 0
        else:                  N = 0; Z = 0

    BUS_C = o


def next_instruction(nextadd, jam):
    """INALTERADA."""
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


def memory_io(mem_bits):
    """INALTERADA."""
    global PC, MAR, MDR, MBR

    if mem_bits & 0b001: MBR = memory.read_byte(PC)
    if mem_bits & 0b010: MDR = memory.read_word(MAR)
    if mem_bits & 0b100: memory.write_word(MAR, MDR)


def step():
    """
    MODIFICADA — implementa o dual bus com a ordem correta de execução:

    Fase 1 — ALU1 (com registradores originais, antes do MEM):
      a) read_regs  → carrega BUS_A, BUS_B para ALU1
      b) alu        → calcula BUS_C (resultado da ALU1)
      c) write_regs → escreve resultado da ALU1 (pode atualizar MAR para MEM)

    Fase 2 — MEM (usa MAR atualizado pela ALU1 se necessário):
      d) memory_io  → FETCH atualiza MBR; READ usa MAR; WRITE usa MAR+MDR

    Fase 3 — ALU2 (com registradores pós-ALU1 e MBR pós-FETCH):
      e) read_regs  → carrega BUS_A, BUS_B para ALU2 (lê MBR já atualizado!)
      f) alu        → calcula BUS_C2 (resultado da ALU2)
      g) write_regs2→ escreve resultado da ALU2

    Fase 4 — próximo endereço:
      h) next_instruction

    Esta ordem é a chave do dual bus: a ALU2 enxerga o MBR que acabou de ser
    carregado pelo FETCH da ALU1, permitindo "FETCH + REG=MBR" em 1 ciclo.
    """
    global MIR, MPC, BUS_A, BUS_B, BUS_C, BUS_A2, BUS_B2, BUS_C2

    MIR = firmware[MPC]
    if MIR == 0:
        return False

    # --- Decodifica campos ALU1 (bits herdados, inalterados) ---
    sf1       = (MIR >> 37) & 0b1
    next_addr = (MIR >> 28) & 0x1FF
    jam       = (MIR >> 25) & 0b111
    alu1_ctrl = (MIR >> 17) & 0xFF
    write1    = (MIR >>  9) & 0xFF
    mem_bits  = (MIR >>  6) & 0b111
    bus_a1    = (MIR >>  3) & 0b111
    bus_b1    =  MIR        & 0b111

    # --- Decodifica campos ALU2 (novos, bits 46..63) ---
    w2        = (MIR >> 46) & 0b111   # WRITE2
    bus_b2    = (MIR >> 49) & 0b111   # BUS_B2
    bus_a2    = (MIR >> 52) & 0b111   # BUS_A2
    alu2_ctrl = (MIR >> 55) & 0xFF    # ALU2
    sf2       = (MIR >> 63) & 0b1     # SAVE_FLAGS2

    # === FASE 1: ALU1 ===
    read_regs(bus_a1, bus_b1)
    alu(alu1_ctrl, sf1)
    write_regs(write1)

    # === FASE 2: MEM ===
    memory_io(mem_bits)

    # === FASE 3: ALU2 (somente se WRITE2 != NONE ou alu2_ctrl != 0) ===
    if w2 != W2_NONE or alu2_ctrl != 0:
        saved_c = BUS_C          # preserva BUS_C da ALU1 (next_instruction pode precisar)
        read_regs(bus_a2, bus_b2)
        alu(alu2_ctrl, sf2)
        BUS_C2 = BUS_C
        BUS_C  = saved_c         # restaura BUS_C da ALU1
        write_regs2(w2, BUS_C2)

    # === FASE 4: próximo MPC ===
    next_instruction(next_addr, jam)

    return True
