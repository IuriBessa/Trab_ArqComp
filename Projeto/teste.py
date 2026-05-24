# ufc2x.py
# chama o arquivo de memoria para que seja possivel a leitura
import memory 
from array import array


MPC = 0 #diz qual instrução i está sendo executada agora como firmware[i].
MIR = 0 #recebe o conteudo que a microinstrução apontou e guarda p levar p ula
 
#MDR é linkado com MAR e MBR comm PC
MAR = 0 #endereço i que se quer escrever ou ler algo na memoria
MDR = 0 #depois de ler o valor esperado vem pra cá, ou se coloca aqui o valor antes de escrever trabalha com words
PC = 0 #guarda o ENDEREÇO de onde foram escritas as instruções a serem feitas
MBR = 0 #Usado para ler as macroinstruçoes(so trabalha com bytes) 
X = 0 #Registrador principal para cálculos, onde os resultados ficam
Y = 0 #segundo acumulador, espelho de X para operações que precisam de dois valores simultaneos
H = 0 #registrador temporario, "rascunho p contas c 2 valores"
Z1 = 0
Z2 = 0

N = 0  #indicadores de estado
Z = 1

BUS_A = 0 #entrada A da ALU, selecionada pelos bits 5..3 do MIR
BUS_B = 0 #entrada B da ALU, selecionada pelos bits 2..0 do MIR
BUS_C = 0 #carrega o resultado que vai p os registradores

firmware = array('Q',[0]) * 512  #cria um espaço que guarda as microinstruções (64 bits, usa 35)

# ==============================================================================
# LAYOUT DO MIR (35 bits):
# 0_000000000_000_00000000_00000000_000_000_000
# [37] SAVE_FLAGS (1b) [36:28] NEXT_ADDR (9b) | [27:25] JAM (3b) | [24:17] ALU (8b) [16:9] WRITE_REGS (8b) | [8:6] MEM (3b) | [5:3] BUS_A (3b) | [2:0] BUS_B (3b)
#
# BUS_A seletores (bits 5..3): 000=H  001=MDR 010=PC 011=MBR 100=X 101=Y 110=Z1 111=Z2
# BUS_B seletores (bits 2..0): 000=MDR 001=PC 010=MBR 011=X 100=Y 101=Z1 110=Z2 111=0
# ==============================================================================

# 0: INIT/FETCH — BUS_C = PC+1; PC=BUS_C; FETCH; GOTO MBR
# BUS_A=PC(010), BUS_B=PC(001), ALU=B+1(00110101), WRITE=PC(001000), MEM=FETCH(001), JAM=MBR(100)
firmware[0] = 0b1_000000000_100_00110101_00100000_001_010_001

# 2: X = X + mem[address] — 3 ciclos
# Ciclo 2: PC=PC+1; FETCH; GOTO 3
firmware[2] = 0b0_000000011_000_00110101_00100000_001_010_001
# Ciclo 3: MAR=MBR; READ; GOTO 4 — BUS_B=MBR(010), ALU=B(00010100), WRITE=MAR(100000), MEM=READ(010)
firmware[3] = 0b0_000000100_000_00010100_10000000_010_000_010
# Ciclo 4: X = MDR + X; GOTO 0 — BUS_A=MDR(001), BUS_B=X(011), ALU=A+B(00111100), WRITE=X(000100)
firmware[4] = 0b1_000000000_000_00111100_00010000_000_001_011

# 6: memory[address] = X — 3 ciclos
# Ciclo 6: PC=PC+1; FETCH; GOTO 7
firmware[6] = 0b0_000000111_000_00110101_00100000_001_010_001
# Ciclo 7: MAR=MBR; GOTO 8
firmware[7] = 0b0_000001000_000_00010100_10000000_000_000_010
# Ciclo 8: MDR=X; WRITE_WORD; GOTO 0
firmware[8] = 0b0_000000000_000_00010100_01000000_100_000_011

# 9: GOTO address — 2 ciclos
# Ciclo 9: PC=PC+1; FETCH; GOTO 10
firmware[9] = 0b0_000001010_000_00110101_00100000_001_010_001
# Ciclo 10: PC=MBR; FETCH; GOTO MBR
firmware[10] = 0b0_000000000_100_00010100_00100000_001_000_010

# 11: IF X == 0 GOTO address
# Ciclo 11: BUS_C=X; se Z=1 GOTO 268, senão GOTO 12
firmware[11] = 0b1_000001100_001_00010100_00000000_000_000_011
# Ciclo 12 (Z=0): PC=PC+1; GOTO 0 (descarta byte de endereço)
firmware[12] = 0b0_000000000_000_00110101_00100000_000_010_001
# Ciclo 268 (Z=1): GOTO 9 — CORRIGIDO: ALU=B explícita
firmware[268] = 0b0_000001001_000_00010100_00000000_000_000_000

# 13: X = X - mem[address] — 3 ciclos
# Ciclo 13: PC=PC+1; FETCH; GOTO 14
firmware[13] = 0b0_000001110_000_00110101_00100000_001_010_001
# Ciclo 14: MAR=MBR; READ; GOTO 15
firmware[14] = 0b0_000001111_000_00010100_10000000_010_000_010
# Ciclo 15: X = X - MDR (B-A = X-MDR); GOTO 0
# BUS_A=MDR(001), BUS_B=X(011), ALU=B-A(00111111), WRITE=X(000100)
firmware[15] = 0b1_000000000_000_00111111_00010000_000_001_011

# 16: X = X + 1 — 1 ciclo
# BUS_B=X(011), ALU=B+1(00110101), WRITE=X(000100)
firmware[16] = 0b1_000000000_000_00110101_00010000_000_000_011

# 17: X = X - 1 — 1 ciclo
# BUS_B=X(011), ALU=B-1(00110110), WRITE=X(000100)
firmware[17] = 0b1_000000000_000_00110110_00010000_000_000_011

# 18: IF X < 0 GOTO address — 2 ou 3 ciclos
# Ciclo 18: BUS_C=X; se N=1 GOTO 274 (=18|256), senão GOTO 19
firmware[18] =  0b1_000010011_010_00010100_00000000_000_000_011
# Ciclo 19 (N=0): PC=PC+1; GOTO 0 (descarta byte de endereço)
firmware[19] =  0b0_000000000_000_00110101_00100000_000_010_001
# Ciclo 275 (N=1): GOTO 9 (executa o desvio)
firmware[275] = 0b0_000001001_000_00010100_00000000_000_000_000

# 20: Y = X — 1 ciclo
# BUS_B=X(011), ALU=B(00010100), WRITE=Y(000010)
firmware[20] = 0b1_000000000_000_00010100_00001000_000_000_011

# 21: X = Y — 1 ciclo
# BUS_B=Y(100), ALU=B(00010100), WRITE=X(000100)
firmware[21] = 0b1_000000000_000_00010100_00010000_000_000_100

# 22: mem[address] = Y — 3 ciclos
# Ciclo 22: PC=PC+1; FETCH; GOTO 23
firmware[22] = 0b0_000010111_000_00110101_00100000_001_010_001
# Ciclo 23: MAR=MBR; GOTO 24
firmware[23] = 0b0_000011000_000_00010100_10000000_000_000_010
# Ciclo 24: MDR=Y; WRITE_WORD; GOTO 0
firmware[24] = 0b0_000000000_000_00010100_01000000_100_000_100

# 25: Y = Y + mem[address] — 3 ciclos
# Ciclo 25: PC=PC+1; FETCH; GOTO 26
firmware[25] = 0b0_000011010_000_00110101_00100000_001_010_001
# Ciclo 26: MAR=MBR; READ; GOTO 27
firmware[26] = 0b0_000011011_000_00010100_10000000_010_000_010
# Ciclo 27: Y = MDR + Y; GOTO 0 — BUS_A=MDR(001), BUS_B=Y(100), ALU=A+B(00111100), WRITE=Y(000010)
firmware[27] = 0b1_000000000_000_00111100_00001000_000_001_100

# 28: Y = mem[address] — 3 ciclos
# Ciclo 28: PC=PC+1; FETCH; GOTO 29
firmware[28] = 0b0_000011101_000_00110101_00100000_001_010_001
# Ciclo 29: MAR=MBR; READ; GOTO 30
firmware[29] = 0b0_000011110_000_00010100_10000000_010_000_010
# Ciclo 30: Y=MDR; GOTO 0 — BUS_B=MDR(000), ALU=B(00010100), WRITE=Y(000010)
firmware[30] = 0b1_000000000_000_00010100_00001000_000_000_000

# 31: X = X << 1 (X * 2) — 1 ciclo
# BUS_B=X(011), ALU=shift<<1+B(01_010100), WRITE=X(000100)
firmware[31] = 0b1_000000000_000_01010100_00010000_000_000_011

# 32: X = X >> 1 (X / 2) — 1 ciclo
# BUS_B=X(011), ALU=shift>>1+B(10_010100), WRITE=X(000100)
firmware[32] = 0b1_000000000_000_10010100_00010000_000_000_011

# 33: Y = Y + 1 — 1 ciclo
# BUS_B=Y(100), ALU=B+1(00110101), WRITE=Y(000010)
firmware[33] = 0b1_000000000_000_00110101_00001000_000_000_100

# 34: Y = Y - 1 — 1 ciclo
# BUS_B=Y(100), ALU=B-1(00110110), WRITE=Y(000010)
firmware[34] = 0b1_000000000_000_00110110_00001000_000_000_100

# 35: IF Y == 0 GOTO address — 2 ou 3 ciclos
# Ciclo 35: testa Y; se Z=1 GOTO 291 (=35|256), senão GOTO 36
firmware[35]  = 0b1_000100100_001_00010100_00000000_000_000_100
# Ciclo 36 (Z=0): PC=PC+1; GOTO 0 (descarta byte de endereço)
firmware[36]  = 0b0_000000000_000_00110101_00100000_000_010_001
# Ciclo 292 (Z=1): GOTO 9
firmware[292] = 0b0_000001001_000_00010100_00000000_000_000_000

# 40: X = mem[addr] — 3 ciclos
# Ciclo 40: PC=PC+1; FETCH; GOTO 128
firmware[40]  = 0b0_010000000_000_00110101_00100000_001_010_001
# Ciclo 128: MAR=MBR + READ (fundidos); GOTO 129
firmware[128] = 0b0_010000001_000_00010100_10000000_010_000_010
# Ciclo 129: X=MDR; GOTO 0
firmware[129] = 0b1_000000000_000_00010100_00010000_000_000_000

# 41: X = 0 — 1 ciclo
# ALU=0(00010000), WRITE=X(000100)
firmware[41] = 0b1_000000000_000_00010000_00010000_000_000_000

# 42: Y = 0 — 1 ciclo
# ALU=0(00010000), WRITE=Y(000010)
firmware[42] = 0b1_000000000_000_00010000_00001000_000_000_000

# 43: IF X <= 0 GOTO address — 2 ou 3 ciclos
# JAM=011 (N|Z): desvia se X<0 OU X==0
# Ciclo 43: testa X; se N|Z GOTO 299 (=43|256), senão GOTO 132
firmware[43]  = 0b1_010000100_011_00010100_00000000_000_000_011
# Ciclo 132 (X>0): PC=PC+1; GOTO 0 (descarta byte de endereço)
firmware[132] = 0b0_000000000_000_00110101_00100000_000_010_001
# Ciclo 388 (X<=0): GOTO 9
firmware[388] = 0b0_000001001_000_00010100_00000000_000_000_000

# 45: X = X + Y — 1 ciclo
# BUS_A=X(100), BUS_B=Y(100)... conflito de seletor B!
# BUS_B não tem X e Y ao mesmo tempo. Usar A=Y, B=X (A+B comutativo)
# BUS_A=Y(101), BUS_B=X(011), ALU=A+B(00111100), WRITE=X(000100)
firmware[45] = 0b1_000000000_000_00111100_00010000_000_101_011

# 46: X = X - Y — 1 ciclo
# B-A = X-Y: BUS_A=Y(101), BUS_B=X(011), ALU=B-A(00111111), WRITE=X(000100)
firmware[46] = 0b1_000000000_000_00111111_00010000_000_101_011

# 47: Y = X + Y — 1 ciclo
# BUS_A=Y(101), BUS_B=X(011), ALU=A+B(00111100), WRITE=Y(000010)
firmware[47] = 0b1_000000000_000_00111100_00001000_000_101_011

# 48: SWAP X, Y — 1 opcode, 3 microciclos internos
# microciclo 48: H = X; GOTO 130
firmware[48]  = 0b0_010000010_000_00010100_00000100_000_000_011
# microciclo 130: X = Y; GOTO 131
firmware[130] = 0b0_010000011_000_00010100_00010000_000_000_100
# microciclo 131: Y = H (ALU=A, A=H); GOTO 0
firmware[131] = 0b1_000000000_000_00011000_00001000_000_000_000

# 49: Y = Y << 1 (Y * 2) — 1 ciclo
# BUS_B=Y(100), ALU=shift<<1+B(01_010100), WRITE=Y(000010)
firmware[49] = 0b1_000000000_000_01010100_00001000_000_000_100

# 50: Y = Y >> 1 (Y / 2) — 1 ciclo
# BUS_B=Y(100), ALU=shift>>1+B(10_010100), WRITE=Y(000010)
firmware[50] = 0b1_000000000_000_10010100_00001000_000_000_100

# 53: H = X - 1 ciclo
firmware[53] = 0b0_000000000_000_00010100_00000100_000_000_011

# 54: X = H - 1 ciclo
firmware[54] = 0b1_000000000_000_00011000_00010000_000_000_000

# 55: H = Y - 1 ciclo
firmware[55] = 0b0_000000000_000_00010100_00000100_000_000_100

# 56: Y = H - 1 ciclo 
firmware[56] = 0b1_000000000_000_00011000_00001000_000_000_000

# 57: IF Y <= 0 GOTO addr - 3 ciclos
firmware[57] = 0b1_000111010_011_00010100_00000000_000_000_100
firmware[58] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[314] = 0b0_000001001_000_00010100_00000000_000_000_000

# 59: IF Y < 0 GOTO addr - 3 ciclos
firmware[59] = 0b1_000111100_010_00010100_00000000_000_000_100
firmware[60] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[316] = 0b0_000001001_000_00010100_00000000_000_000_000

# 61: Y = Y - mem[addr] — 3 ciclos
firmware[61] = 0b0_010000101_000_00110101_00100000_001_010_001
firmware[133] = 0b0_010000110_000_00010100_10000000_010_000_010
firmware[134] = 0b1_000000000_000_00111111_00001000_000_001_100

# 64: X = X AND Y — 1 ciclo
firmware[64] = 0b1_000000000_000_00001100_00010000_000_101_011

# 65: X = X OR Y — 1 ciclo
firmware[65] = 0b1_000000000_000_00011100_00010000_000_101_011

# 66: X = immediate — 2 ciclos
firmware[66] = 0b0_010000111_000_00110101_00100000_001_010_001
firmware[135] = 0b1_000000000_000_00010100_00010000_000_000_010

# 67: Y = immediate — 2 ciclos
firmware[67] = 0b0_010001000_000_00110101_00100000_001_010_001
firmware[136] = 0b1_000000000_000_00010100_00001000_000_000_010

# 68-75 Registradores Z1 e Z2 
firmware[68] = 0b0_000000000_000_00010100_00000010_000_000_011 # Z1 = X
firmware[69] = 0b0_000000000_000_00010100_00000010_000_000_100 # Z1 = Y
firmware[70] = 0b1_000000000_000_00010100_00010000_000_000_101 # X = Z1
firmware[71] = 0b1_000000000_000_00010100_00001000_000_000_101 # Y = Z1
firmware[72] = 0b0_000000000_000_00010100_00000001_000_000_011 # Z2 = X
firmware[73] = 0b0_000000000_000_00010100_00000001_000_000_100 # Z2 = Y
firmware[74] = 0b1_000000000_000_00010100_00010000_000_000_110 # X = Z2
firmware[75] = 0b1_000000000_000_00010100_00001000_000_000_110 # Y = Z2

# 76: IF X = odd goto addr - 2-3 ciclos
firmware[76] = 0b1_001001101_101_00000001_00000000_000_100_000
firmware[77] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[333] = 0b0_000001001_000_00010100_00000000_000_000_000

# 78: Y = Y - X — 1 ciclo
firmware[78] = 0b1_000000000_000_00111111_00001000_000_100_100

# 79: X = X xor Y — 1 ciclo
firmware[79] = 0b1_000000000_000_00000010_00010000_000_101_011

# 80: X = |X| — 1 ciclo
firmware[80] = 0b1_000000000_000_00000011_00010000_000_100_000


# 83: Z1 = Z1 - 1 — 1 ciclo
firmware[83] = 0b1_000000000_000_00110110_00000010_000_000_101

# 84: Z1 = Z1 + 1 — 1 ciclo
firmware[84] = 0b1_000000000_000_00110101_00000010_000_000_101

# 85: IF Z1 == 0 GOTO address — 3 ciclos
# NEXT_ADDR=86, JAM_Z=001 → when Z=1: MPC = 86|256 = 342  (era 341, bug corrigido)
firmware[85]  = 0b1_001010110_001_00010100_00000000_000_000_101
firmware[86]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[342] = 0b0_000001001_000_00010100_00000000_000_000_000

# 87: Z1 = immediate — 2 ciclos
firmware[87]  = 0b0_010101101_000_00110101_00100000_001_010_001
firmware[173] = 0b1_000000000_000_00010100_00000010_000_000_010


# ==============================================================================
# PRIORIDADE 1 — Aritmética direta em H e Z2
# ==============================================================================

# 88: H = H + 1 — 1 ciclo
# BUS_A=H(000), ALU=A+1(00111001), WRITE=H(00000100), save_flags=1
firmware[88] = 0b1_000000000_000_00111001_00000100_000_000_000

# 89: H = H - 1 — 1 ciclo
# BUS_A=H(000), ALU=A-1(00111010) [novo op], WRITE=H(00000100), save_flags=1
# NOTA: H só existe em BUS_A (não em BUS_B), portanto é necessário A-1 na ALU
firmware[89] = 0b1_000000000_000_00111010_00000100_000_000_000

# 90: Z2 = Z2 - 1 — 1 ciclo
# BUS_B=Z2(110), ALU=B-1(00110110), WRITE=Z2(00000001), save_flags=1
firmware[90] = 0b1_000000000_000_00110110_00000001_000_000_110

# 91: Z2 = Z2 + 1 — 1 ciclo
# BUS_B=Z2(110), ALU=B+1(00110101), WRITE=Z2(00000001), save_flags=1
firmware[91] = 0b1_000000000_000_00110101_00000001_000_000_110

# 92: IF Z2 == 0 GOTO address — 3 ciclos
# NEXT_ADDR=93, JAM_Z=001 → when Z=1: MPC = 93|256 = 349
# BUS_B=Z2(110), ALU=B(00010100), WRITE=none, save_flags=1
firmware[92]  = 0b1_001011101_001_00010100_00000000_000_000_110
firmware[93]  = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[349] = 0b0_000001001_000_00010100_00000000_000_000_000

# ==============================================================================
# PRIORIDADE 2 — Zeros diretos para H, Z1 e Z2
# ==============================================================================

# 94: H = 0 — 1 ciclo
# ALU=0(00010000), WRITE=H(00000100), save_flags=1
firmware[94] = 0b1_000000000_000_00010000_00000100_000_000_000

# 95: Z1 = 0 — 1 ciclo
# ALU=0(00010000), WRITE=Z1(00000010), save_flags=1
firmware[95] = 0b1_000000000_000_00010000_00000010_000_000_000

# 96: Z2 = 0 — 1 ciclo
# ALU=0(00010000), WRITE=Z2(00000001), save_flags=1
firmware[96] = 0b1_000000000_000_00010000_00000001_000_000_000

# ==============================================================================
# PRIORIDADE 3 — mem[addr] = Z1 (padrão idêntico ao opcode 6 / opcode 22)
# ==============================================================================

# 97: mem[address] = Z1 — 3 ciclos
# Ciclo 97: PC=PC+1; FETCH; GOTO 98
firmware[97]  = 0b0_001100010_000_00110101_00100000_001_010_001
# Ciclo 98: MAR=MBR; GOTO 99
firmware[98]  = 0b0_001100011_000_00010100_10000000_000_000_010
# Ciclo 99: MDR=Z1; WRITE_WORD; GOTO 0 — BUS_B=Z1(101), ALU=B, WRITE=MDR(01000000), MEM=WRITE(100)
firmware[99]  = 0b0_000000000_000_00010100_01000000_100_000_101

# ==============================================================================
# PRIORIDADE 4 — IF X >= 0 GOTO (complemento do IF X < 0, JAM=110 = inverted N)
# ==============================================================================

# 100: IF X >= 0 GOTO address — 3 ciclos
# Desvia quando N=0 (X >= 0): NEXT_ADDR=101, JAM=110 → MPC = 101|(1-N)<<8
# Se X>=0 (N=0): MPC = 101|256 = 357 → toma o desvio
# Se X< 0 (N=1): MPC = 101|0   = 101 → descarta endereço
firmware[100] = 0b1_001100101_110_00010100_00000000_000_000_011
firmware[101] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[357] = 0b0_000001001_000_00010100_00000000_000_000_000
firmware[255] = 0b0_000000000_000_00000000_00000000_000_000_000

# ==============================================================================
# PRIORIDADE 5 — CALL / RET com registrador de link (Z2)
#
# Convenção: Z2 guarda o endereço de retorno após CALL.
# Para chamadas aninhadas, salve Z2 na memória antes do CALL interno
# e restaure após o RET. Para FUP de 1 nível (ex: main→multiply), Z2 é livre.
# Esta abordagem é análoga ao "branch-and-link" de processadores RISC (ARM LR).
# RET custa apenas 1 microciclo — o menor CALL/RET possível nesta arquitetura.
# ==============================================================================

# 102: CALL address — 3 ciclos
# Ciclo 102: PC=PC+1; FETCH; GOTO 103  (busca o byte do endereço-alvo em MBR, PC aponta ao retorno)
firmware[102] = 0b0_001100111_000_00110101_00100000_001_010_001
# Ciclo 103: Z2 = PC  (salva endereço de retorno no registrador de link)
# BUS_B=PC(001), ALU=B(00010100), WRITE=Z2(00000001), save=0, GOTO 104
firmware[103] = 0b0_001101000_000_00010100_00000001_000_000_001
# Ciclo 104: PC = MBR; FETCH; GOTO MBR  (desvia para o alvo e despacha)
# BUS_B=MBR(010), ALU=B, WRITE=PC(00100000), MEM=FETCH(001), JAM=MBR(100)
firmware[104] = 0b0_000000000_100_00010100_00100000_001_000_010

# 105: RET — 1 ciclo
# PC = Z2; FETCH; GOTO MBR  (restaura PC do registrador de link e despacha)
# BUS_B=Z2(110), ALU=B, WRITE=PC(00100000), MEM=FETCH(001), JAM=MBR(100), save=0
firmware[105] = 0b0_000000000_100_00010100_00100000_001_000_110

# ==============================================================================
# DESVIOS CONDICIONAIS EM Z1 E H  (gap crítico do documento original)
# ==============================================================================

# 106: IF Z1 < 0 GOTO address — 3 ciclos
# NEXT=107, JAM=010(N), BUS_B=Z1(101) → N=1: 107|256=363
firmware[106] = 0b1_001101011_010_00010100_00000000_000_000_101
firmware[107] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[363] = 0b0_000001001_000_00010100_00000000_000_000_000

# 108: IF Z1 <= 0 GOTO address — 3 ciclos
# NEXT=109, JAM=011(N|Z), BUS_B=Z1(101) → N|Z=1: 109|256=365
firmware[108] = 0b1_001101101_011_00010100_00000000_000_000_101
firmware[109] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[365] = 0b0_000001001_000_00010100_00000000_000_000_000

# 110: IF H == 0 GOTO address — 3 ciclos
# H só existe em BUS_A → usa ALU=A(011000) em vez de ALU=B
# NEXT=111, JAM=001(Z), BUS_A=H(000) → Z=1: 111|256=367
firmware[110] = 0b1_001101111_001_00011000_00000000_000_000_000
firmware[111] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[367] = 0b0_000001001_000_00010100_00000000_000_000_000

# 112: IF H < 0 GOTO address — 3 ciclos
# NEXT=113, JAM=010(N), BUS_A=H(000), ALU=A → N=1: 113|256=369
firmware[112] = 0b1_001110001_010_00011000_00000000_000_000_000
firmware[113] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[369] = 0b0_000001001_000_00010100_00000000_000_000_000

# 114: IF H <= 0 GOTO address — 3 ciclos
# NEXT=115, JAM=011(N|Z), BUS_A=H(000), ALU=A → N|Z=1: 115|256=371
firmware[114] = 0b1_001110011_011_00011000_00000000_000_000_000
firmware[115] = 0b0_000000000_000_00110101_00100000_000_010_001
firmware[371] = 0b0_000001001_000_00010100_00000000_000_000_000

# ==============================================================================
# TRANSFERÊNCIAS DIRETAS ENTRE REGISTRADORES TEMPORÁRIOS
# Eliminam o desvio obrigatório por X ou Y (-2 ciclos cada)
# ==============================================================================

# 116: Z1 = H — 1 ciclo   (BUS_A=H(000), ALU=A(011000), WRITE=Z1(00000010))
firmware[116] = 0b0_000000000_000_00011000_00000010_000_000_000

# 117: H = Z1 — 1 ciclo   (BUS_B=Z1(101), ALU=B(00010100), WRITE=H(00000100))
firmware[117] = 0b0_000000000_000_00010100_00000100_000_000_101

# 118: Z2 = H — 1 ciclo   (BUS_A=H(000), ALU=A(011000), WRITE=Z2(00000001))
firmware[118] = 0b0_000000000_000_00011000_00000001_000_000_000

# 119: H = Z2 — 1 ciclo   (BUS_B=Z2(110), ALU=B(00010100), WRITE=H(00000100))
firmware[119] = 0b0_000000000_000_00010100_00000100_000_000_110

# 120: Z2 = Z1 — 1 ciclo   (BUS_B=Z1(101), ALU=B, WRITE=Z2(00000001))
firmware[120] = 0b0_000000000_000_00010100_00000001_000_000_101

# 121: Z1 = Z2 — 1 ciclo   (BUS_B=Z2(110), ALU=B, WRITE=Z1(00000010))
firmware[121] = 0b0_000000000_000_00010100_00000010_000_000_110

# ==============================================================================
# ESCRITA NA MEMÓRIA COM Z2 E ARITMÉTICA DIRETA COM Z1
# ==============================================================================

# 122: mem[address] = Z2 — 3 ciclos  (simétrico ao opcode 97 para Z1)
firmware[122] = 0b0_001111011_000_00110101_00100000_001_010_001  # GOTO 123
firmware[123] = 0b0_001111100_000_00010100_10000000_000_000_010  # MAR=MBR; GOTO 124
# MDR=Z2; WRITE_WORD; GOTO 0 — BUS_B=Z2(110), WRITE=MDR(01000000), MEM=WRITE(100)
firmware[124] = 0b0_000000000_000_00010100_01000000_100_000_110

# 125: X = X + Z1 — 1 ciclo   (BUS_A=Z1(110), BUS_B=X(011), ALU=A+B, WRITE=X)
firmware[125] = 0b1_000000000_000_00111100_00010000_000_110_011

# 126: X = X - Z1 — 1 ciclo   (B-A = X-Z1: BUS_A=Z1(110), BUS_B=X(011), ALU=B-A, WRITE=X)
firmware[126] = 0b1_000000000_000_00111111_00010000_000_110_011

# 127: Y = Y + Z1 — 1 ciclo   (BUS_A=Z1(110), BUS_B=Y(100), ALU=A+B, WRITE=Y)
firmware[127] = 0b1_000000000_000_00111100_00001000_000_110_100

# 137: Y = Y - Z1 — 1 ciclo   (B-A = Y-Z1: BUS_A=Z1(110), BUS_B=Y(100), ALU=B-A, WRITE=Y)
firmware[137] = 0b1_000000000_000_00111111_00001000_000_110_100

# ==============================================================================
# ENDEREÇAMENTO INDIRETO VIA Z1  (essencial para arrays e ordenação)
# Permite tratar Z1 como ponteiro — habilita bubble sort, busca linear, etc.
# ==============================================================================

# 140: X = mem[Z1] — 2 ciclos  (MAR=Z1, READ, X=MDR)
# BUS_B=Z1(101), ALU=B, WRITE=MAR(10000000), MEM=READ(010), GOTO 141
firmware[140] = 0b0_010001101_000_00010100_10000000_010_000_101
# X=MDR; GOTO 0   BUS_B=MDR(000), WRITE=X(00010000), save=1
firmware[141] = 0b1_000000000_000_00010100_00010000_000_000_000

# 142: Y = mem[Z1] — 2 ciclos
firmware[142] = 0b0_010001111_000_00010100_10000000_010_000_101
firmware[143] = 0b1_000000000_000_00010100_00001000_000_000_000  # Y=MDR

# 144: mem[Z1] = X — 2 ciclos  (MAR=Z1, MDR=X, WRITE)
firmware[144] = 0b0_010010001_000_00010100_10000000_000_000_101  # MAR=Z1; GOTO 145
# MDR=X; WRITE_WORD; GOTO 0   BUS_B=X(011), WRITE=MDR(01000000), MEM=WRITE(100)
firmware[145] = 0b0_000000000_000_00010100_01000000_100_000_011

# 146: mem[Z1] = Y — 2 ciclos
firmware[146] = 0b0_010010011_000_00010100_10000000_000_000_101  # MAR=Z1; GOTO 147
firmware[147] = 0b0_000000000_000_00010100_01000000_100_000_100  # MDR=Y; WRITE

# ==============================================================================
# CARGA DIRETA NOS REGISTRADORES TEMPORÁRIOS
# ==============================================================================

# 148: Z1 = mem[addr] — 3 ciclos
firmware[148] = 0b0_010010101_000_00110101_00100000_001_010_001  # FETCH; GOTO 149
firmware[149] = 0b0_010010110_000_00010100_10000000_010_000_010  # MAR=MBR; READ; GOTO 150
firmware[150] = 0b1_000000000_000_00010100_00000010_000_000_000  # Z1=MDR; GOTO 0

# 151: Z2 = mem[addr] — 3 ciclos
firmware[151] = 0b0_010011000_000_00110101_00100000_001_010_001  # FETCH; GOTO 152
firmware[152] = 0b0_010011001_000_00010100_10000000_010_000_010  # MAR=MBR; READ; GOTO 153
firmware[153] = 0b1_000000000_000_00010100_00000001_000_000_000  # Z2=MDR; GOTO 0

# 154: Z2 = immediate — 2 ciclos  (simétrico ao opcode 87 para Z1)
firmware[154] = 0b0_010011011_000_00110101_00100000_001_010_001  # FETCH; GOTO 155
firmware[155] = 0b1_000000000_000_00010100_00000001_000_000_010  # Z2=MBR; GOTO 0

# 156: H = immediate — 2 ciclos
firmware[156] = 0b0_010011101_000_00110101_00100000_001_010_001  # FETCH; GOTO 157
firmware[157] = 0b0_000000000_000_00010100_00000100_000_000_010  # H=MBR; GOTO 0

# ==============================================================================
# CÁLCULO DIRETO EM Z1  (preserva X e Y intactos durante contas intermediárias)
# ==============================================================================

# 158: Z1 = X + Y — 1 ciclo   (BUS_A=Y(101), BUS_B=X(011), ALU=A+B, WRITE=Z1)
firmware[158] = 0b1_000000000_000_00111100_00000010_000_101_011

# 159: Z1 = X - Y — 1 ciclo   (B-A = X-Y: BUS_A=Y(101), BUS_B=X(011), ALU=B-A, WRITE=Z1)
firmware[159] = 0b1_000000000_000_00111111_00000010_000_101_011

def read_regs(reg_num):
   global MDR, PC, MBR, X, Y, H, BUS_A, BUS_B, Z1, Z2
   
   reg_numB = reg_num & 0b111
   reg_numA = (reg_num >> 3) & 0b111

   if reg_numA == 0:
      BUS_A = H
   elif reg_numA == 1:
      BUS_A = MDR
   elif reg_numA == 2:
      BUS_A = PC
   elif reg_numA == 3:
      BUS_A = MBR
   elif reg_numA == 4:
      BUS_A = X
   elif reg_numA == 5:
      BUS_A = Y
   elif reg_numA == 6:
      BUS_A = Z1
   elif reg_numA == 7:
      BUS_A = Z2
   
   if reg_numB == 0:
      BUS_B = MDR
   elif reg_numB == 1:
      BUS_B = PC
   elif reg_numB == 2:
      BUS_B = MBR
   elif reg_numB == 3:
      BUS_B = X
   elif reg_numB == 4:
      BUS_B = Y
   elif reg_numB == 5:
      BUS_B = Z1
   elif reg_numB == 6:
      BUS_B = Z2
   else:
      BUS_B = 0

def write_regs(reg_bits):
   global MAR, MDR, PC, X, Y, H, BUS_C, Z1, Z2
   
   if reg_bits & 0b10000000:
      MAR = BUS_C
   if reg_bits & 0b01000000:
      MDR = BUS_C
   if reg_bits & 0b00100000:
      PC = BUS_C
   if reg_bits & 0b00010000:
      X = BUS_C
   if reg_bits & 0b00001000:
      Y = BUS_C
   if reg_bits & 0b00000100:
      H = BUS_C
   if reg_bits & 0b00000010:
      Z1 = BUS_C
   if reg_bits & 0b00000001:
      Z2 = BUS_C

def alu(control_bits, save_flags):
   global N, Z, BUS_A, BUS_B, BUS_C
   
   a = BUS_A
   b = BUS_B
   o = 0
   
   shift_bits = (control_bits >> 6) & 0b11
   control_bits = control_bits & 0b00111111
   
   if control_bits == 0b011000:
      o = a
   elif control_bits == 0b010100:
      o = b
   elif control_bits == 0b011010:
      o = ~a
   elif control_bits == 0b101100:
      o = ~b
   elif control_bits == 0b111100:
      o = a + b
   elif control_bits == 0b111101:
      o = a + b + 1
   elif control_bits == 0b111001:
      o = a + 1
   elif control_bits == 0b110101:
      o = b + 1
   elif control_bits == 0b111111:
      o = b - a
   elif control_bits == 0b110110:
      o = b - 1
   elif control_bits == 0b111011:
      o = -a
   elif control_bits == 0b001100:
      o = a & b
   elif control_bits == 0b011100:
      o = a | b
   elif control_bits == 0b010000:
      o = 0
   elif control_bits == 0b110001:
      o = 1
   elif control_bits == 0b110010:
      o = -1
   elif control_bits == 0b000001:
      o = a & 1                                    # A & 1
   elif control_bits == 0b000010:
      o = a ^ b                                    # A XOR B
   elif control_bits == 0b111010:                                               # A - 1  (necessário para H=H-1, pois H só existe em BUS_A)
      o = a - 1
   elif control_bits == 0b000011:                                               # |A|
      o = a
      if not (a & 0x80000000):
         o = a
      else:
         o = (~a + 1) & 0xFFFFFFFF

   o = o & 0xFFFFFFFF

   # CORRIGIDO: shift aplicado ANTES das flags, N/Z refletem o valor final de BUS_C
   if shift_bits == 0b01:
      o = (o << 1) & 0xFFFFFFFF
   elif shift_bits == 0b10:
      o = o >> 1
   elif shift_bits == 0b11:
      o = (o << 8) & 0xFFFFFFFF

   if save_flags:
      if o == 0:
         N = 0; Z = 1
      elif o & 0x80000000:
         N = 1; Z = 0
      else:
         N = 0; Z = 0

   BUS_C = o
    
def next_instruction(nextadd, jam):
   global MPC
   
   if jam == 0b000:
      MPC = nextadd
      return
   elif jam == 0b001:
      nextadd = nextadd | (Z << 8)
   elif jam == 0b010:
      nextadd = nextadd | (N << 8)
   elif jam == 0b011:
      nextadd = nextadd | ((N | Z) << 8)
   elif jam == 0b100:
      nextadd = nextadd | MBR
   elif jam == 0b101:
      nextadd = nextadd | ((1 - Z) << 8)
   elif jam == 0b110:
      nextadd = nextadd | ((1 - N) << 8)

   MPC = nextadd

def memory_io(mem_bits):
   global PC, MAR, MDR, MBR
   
   if mem_bits & 0b001:
      MBR = memory.read_byte(PC)
   if mem_bits & 0b010:
      MDR = memory.read_word(MAR)
   if mem_bits & 0b100:
      memory.write_word(MAR, MDR)

def step():
   global MIR, MPC
   
   MIR = firmware[MPC]
   
   if MIR == 0:
      return False

   save_flags = (MIR >> 37) & 0b1

   read_regs(MIR & 0b111111)
   alu((MIR >> 17) & 0xFF, save_flags)
   write_regs((MIR >>  9) & 0xFF)
   memory_io((MIR >>  6) & 0b111)
   next_instruction((MIR >> 28) & 0x1FF,(MIR >> 25) & 0b111)
   
   return True