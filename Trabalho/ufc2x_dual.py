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
Z1  = 0       #Registradores auxiliares criados para ajudar a não precisar acessar direto a memória
Z2  = 0

N = 0         #Verifica se o numero é negativo
Z = 1         #Verifica se não é 0

BUS_A  = 0
BUS_B  = 0
BUS_C  = 0
BUS_A2 = 0    #Barramentos criados para a ALU dupla
BUS_B2 = 0
BUS_C2 = 0

#Criação do array dos firmwares. Usa-se o Q para aguentar numeros maiores

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
ALU2_AND1 = 0b00000001   # A & 1   (testa a paridade na ALU2)
ALU2_AaB  = 0b00001100   # A & B   (Porta AND imediato do X e MBR)
ALU2_Bshl = 0b01010100   # B << 1  (shift left na ALU2, faz divisão)
ALU2_Ashl = 0b01011000   # A << 1  (shift left de H na ALU2, faz divisão)
ALU2_Ashr = 0b10011000   # A >> 1  (shift right de H na ALU2, multiplica por 2)
ALU2_MUL  = 0b00000101   # A * B                       (multiplica chamando a função)
ALU2_DIV  = 0b00000110   # A // B                      (divide chamando a função criada)
ALU2_MOD  = 0b00000111   # A % B                       (resto chamando a função criada)
ALU2_BEXT = 0b00001000   # (A >> 8*(B&3)) & 0xFF       (byte extract)
ALU2_BINS = 0b00001001   # (A << 8) | (B & 0xFF)       (byte pack/append)


#código da ALU2 que extrai as instruções que ela deve trabalhar

def _dual(alu2=ALU2_B, a2=A2_MBR, b2=B2_MBR, w2=W2_NONE, sf2=0):
    return ((sf2 << 63) | (alu2 << 55) | (a2 << 52) | (b2 << 49) | (w2 << 46))


# Com a ALU dupla o ciclo de avaliações faz tudo de uma vez:
#   ALU1: PC++ e FETCH do byte de endereco (MBR = addr-alvo)
#   ALU2: avalia o registrador testado com sf2=1 -> escreve flags N/Z
#   JAM:  usa as flags da ALU2 para escolher o proximo microendereco

#   NT_SLOT  (nao-tomado): PC++ (descarta o byte de endereco), FETCH, despacha
#   TK_SLOT  (tomado)    : PC = MBR (alvo), FETCH, despacha

NT_SLOT = 180
TK_SLOT = NT_SLOT | 0x100   # 436

def _branch(jam, alu2, a2=0, b2=0):
    # ALU1 = PC+1 (BUS_A=PC, BUS_B=PC) ; WRITE=PC ; MEM=FETCH ; NEXT=NT_SLOT
    base = ((NT_SLOT << 28) | (jam << 25) | (0b00110101 << 17)
            | (0b00100000 << 9) | (0b001 << 6) | (0b010 << 3) | 0b001)
    return base | _dual(alu2, a2, b2, W2_NONE, sf2=1)

#==================================================
# Layout do MIR com seus 64 bits.
#==================================================
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
#======================================
# Ordem de execucao:
#======================================
#   1) snapshot regs
#   2) ALU1 
#   3) FETCH  
#   4) ALU2 avalia (snapshot de X/Y/H/Z1/Z2/PC/MDR + MBR pós-FETCH) e escreve
#   5) READ   (usa MAR pós-ALU2)
#   6) WRITE  (usa MAR e MDR pós-ALU2)
#   7) next_instruction




# [0] init/fetch
firmware[0] = 0b1_000000000_100_00110101_00100000_001_010_001

# [2] X = X + mem[addr] 
firmware[2] = (0b0_000000100_000_00110101_00100000_011_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[4] = 0b1_000000000_000_00111100_00010000_000_001_011

# [6] mem[addr] = X 
firmware[6] = (0b0_000001000_000_00110101_00100000_001_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[8] = 0b0_000000000_000_00010100_01000000_100_000_011

# [9] GOTO addr 
firmware[9]  = 0b0_000001010_000_00110101_00100000_001_010_001
firmware[10] = 0b0_000000000_100_00010100_00100000_001_000_010

# slots compartilhados pelos desvios condicionais de 2 microciclos 
# NT_SLOT (180): ramo NAO-tomado -> PC++ (descarta byte de endereco), FETCH, despacha
firmware[NT_SLOT] = 0b0_000000000_100_00110101_00100000_001_010_001
# TK_SLOT (436): ramo TOMADO -> PC = MBR (endereco-alvo), FETCH, despacha
firmware[TK_SLOT] = 0b0_000000000_100_00010100_00100000_001_000_010

# [11]: IF X == 0 GOTO addr
firmware[11] = _branch(0b001, ALU2_B, b2=B2_X)

# [13]: X = X - mem[addr] 
firmware[13] = (0b0_000001111_000_00110101_00100000_011_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[15] = 0b1_000000000_000_00111111_00010000_000_001_011

# [16]: Incrementa X ou Decrementa X
firmware[16] = 0b1_000000000_000_00110101_00010000_000_000_011
firmware[17] = 0b1_000000000_000_00110110_00010000_000_000_011

# [18] IF X < 0 GOTO addr 
firmware[18] = _branch(0b010, ALU2_B, b2=B2_X)

# [20] Deixa X e Y com valor de X, SWAP que foi feito errado, mas os opcodes estão sequênciais, não quis apagar
firmware[20] = 0b1_000000000_000_00010100_00001000_000_000_011
firmware[21] = 0b1_000000000_000_00010100_00010000_000_000_100

# [22]: mem[addr] = Y 
firmware[22] = (0b0_000011000_000_00110101_00100000_001_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[24] = 0b0_000000000_000_00010100_01000000_100_000_100

# [25]: Y = Y + mem[addr] 
firmware[25] = (0b0_000011011_000_00110101_00100000_011_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[27] = 0b1_000000000_000_00111100_00001000_000_001_100

# [28]: Y = mem[addr] 
firmware[28] = (0b0_000011110_000_00110101_00100000_011_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[30] = 0b1_000000000_000_00010100_00001000_000_000_000

# [31]: Shifts no X
firmware[31] = 0b1_000000000_000_01010100_00010000_000_000_011
firmware[32] = 0b1_000000000_000_10010100_00010000_000_000_011
firmware[33] = 0b1_000000000_000_00110101_00001000_000_000_100
firmware[34] = 0b1_000000000_000_00110110_00001000_000_000_100

# [35]: IF Y == 0 GOTO addr 
firmware[35] = _branch(0b001, ALU2_B, b2=B2_Y)

# [40]: X = mem[addr] 
firmware[40] = (0b0_010000001_000_00110101_00100000_011_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[129] = 0b1_000000000_000_00010100_00010000_000_000_000

# [41]: Limpa X e Limpa Y
firmware[41] = 0b1_000000000_000_00010000_00010000_000_000_000
firmware[42] = 0b1_000000000_000_00010000_00001000_000_000_000

# [43]: IF X <= 0 GOTO addr 
firmware[43] = _branch(0b011, ALU2_B, b2=B2_X)

# [45]: X = X + Y
firmware[45] = 0b1_000000000_000_00111100_00010000_000_101_011

# [46]: X = X - Y
firmware[46] = 0b1_000000000_000_00111111_00010000_000_101_011

# [47]: Y = X + Y 
firmware[47] = 0b1_000000000_000_00111100_00001000_000_101_011

# [48]: SWAP X , Y
firmware[48] = (0b1_000000000_000_00010100_00010000_000_000_100 | _dual(ALU2_B, A2_MBR, B2_X, W2_Y))

# [49]: Shifts direita e esquerda no Y
firmware[49] = 0b1_000000000_000_01010100_00001000_000_000_100
firmware[50] = 0b1_000000000_000_10010100_00001000_000_000_100

# [53]: Operações com H
firmware[53] = 0b0_000000000_000_00010100_00000100_000_000_011
firmware[54] = 0b1_000000000_000_00011000_00010000_000_000_000
firmware[55] = 0b0_000000000_000_00010100_00000100_000_000_100
firmware[56] = 0b1_000000000_000_00011000_00001000_000_000_000

# [57]: IF Y <= 0 
firmware[57] = _branch(0b011, ALU2_B, b2=B2_Y)

# [59]: IF Y < 0 GOTO addr
firmware[59] = _branch(0b010, ALU2_B, b2=B2_Y)

# [61]: Y = Y - mem[addr] 
firmware[61] = (0b0_010000110_000_00110101_00100000_011_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[134] = 0b1_000000000_000_00111111_00001000_000_001_100

# [64]: X = X e Y  ,   [65] : X = X ou Y
firmware[64] = 0b1_000000000_000_00001100_00010000_000_101_011
firmware[65] = 0b1_000000000_000_00011100_00010000_000_101_011

# [66]: X = imm 
firmware[66] = (0b0_000000000_000_00110101_00100000_001_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_X, sf2=1))

# [67]: Y = imm 
firmware[67] = (0b0_000000000_000_00110101_00100000_001_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_Y, sf2=1))

# [68 - 75]: Mexem com X, Y, Z1 e Z2  e mudam os valores entre si
firmware[68] = 0b0_000000000_000_00010100_00000010_000_000_011
firmware[69] = 0b0_000000000_000_00010100_00000010_000_000_100
firmware[70] = 0b1_000000000_000_00010100_00010000_000_000_101
firmware[71] = 0b1_000000000_000_00010100_00001000_000_000_101
firmware[72] = 0b0_000000000_000_00010100_00000001_000_000_011
firmware[73] = 0b0_000000000_000_00010100_00000001_000_000_100
firmware[74] = 0b1_000000000_000_00010100_00010000_000_000_110
firmware[75] = 0b1_000000000_000_00010100_00001000_000_000_110

# [76]: IF X odd GOTO addr 
firmware[76] = _branch(0b101, ALU2_AND1, a2=A2_X)

# [78]: Y = Y - X
firmware[78] = 0b1_000000000_000_00111111_00001000_000_100_100

# [79]: X = X xou Y
firmware[79] = 0b1_000000000_000_00000010_00010000_000_101_011

# [80]: X = |X|
firmware[80] = 0b1_000000000_000_00000011_00010000_000_100_000

# [83  e   84]: Z1 = Z1 + 1   ,  Z1 = Z1 - 1
firmware[83] = 0b1_000000000_000_00110110_00000010_000_000_101
firmware[84] = 0b1_000000000_000_00110101_00000010_000_000_101

# [85]: IF Z1 == 0 GOTO addr 
firmware[85] = _branch(0b001, ALU2_B, b2=B2_Z1)

# [87]: Z1 = imm 
firmware[87] = (0b0_000000000_000_00110101_00100000_001_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_Z1))

# Operações básicas para H e Z2
firmware[88] = 0b1_000000000_000_00111001_00000100_000_000_000
firmware[89] = 0b1_000000000_000_00111010_00000100_000_000_000
firmware[90] = 0b1_000000000_000_00110110_00000001_000_000_110
firmware[91] = 0b1_000000000_000_00110101_00000001_000_000_110

# [92]: IF Z2 == 0 GOTO addr 
firmware[92] = _branch(0b001, ALU2_B, b2=B2_Z2)

# Zerar H, Z1 e Z2
firmware[94] = 0b1_000000000_000_00010000_00000100_000_000_000
firmware[95] = 0b1_000000000_000_00010000_00000010_000_000_000
firmware[96] = 0b1_000000000_000_00010000_00000001_000_000_000

# [97]: mem[addr] = Z1 
firmware[97] = (0b0_001100011_000_00110101_00100000_001_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[99] = 0b0_000000000_000_00010100_01000000_100_000_101

# [100]: IF X >= 0 GOTO addr 
firmware[100] = _branch(0b110, ALU2_B, b2=B2_X)

#==============================
# Implementação do CALL e RET que serve para uso em sub-rotinas (funções). Essa implementação só aguenta uma subtina por vez porque não usa pilha
#==============================

#Call
firmware[102] = (0b0_001101000_000_00110101_00100000_001_010_001 | _dual(ALU2_Bp1, A2_MBR, B2_PC, W2_Z2))
firmware[104] = 0b0_000000000_100_00010100_00100000_001_000_010

#Ret
firmware[105] = 0b0_000000000_000_00010100_00100000_000_000_110


# [106 ,  108]: IF Z1 < 0  ,  IF Z1 <= 0 
firmware[106] = _branch(0b010, ALU2_B, b2=B2_Z1)
firmware[108] = _branch(0b011, ALU2_B, b2=B2_Z1)

# [110   ,   112,    114]: IF H == 0 ,  IF H < 0   ,  IF H <= 0  
firmware[110] = _branch(0b001, ALU2_A, a2=A2_H)
firmware[112] = _branch(0b010, ALU2_A, a2=A2_H)
firmware[114] = _branch(0b011, ALU2_A, a2=A2_H)

# [116 -  121]: Opcodes de movimentação entre os registradores.
firmware[116] = 0b0_000000000_000_00011000_00000010_000_000_000  # Z1 = H
firmware[117] = 0b0_000000000_000_00010100_00000100_000_000_101  # H = Z1
firmware[118] = 0b0_000000000_000_00011000_00000001_000_000_000  # Z2 = H
firmware[119] = 0b0_000000000_000_00010100_00000100_000_000_110  # H = Z2
firmware[120] = 0b0_000000000_000_00010100_00000001_000_000_101  # Z2 = Z1
firmware[121] = 0b0_000000000_000_00010100_00000010_000_000_110  # Z1 = Z2

# [122]: mem[addr] = Z2 
firmware[122] = (0b0_001111100_000_00110101_00100000_001_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[124] = 0b0_000000000_000_00010100_01000000_100_000_110

# Mexendo com Z1, X e Y
firmware[125] = 0b1_000000000_000_00111100_00010000_000_110_011  # X = X + Z1
firmware[126] = 0b1_000000000_000_00111111_00010000_000_110_011  # X = X - Z1
firmware[127] = 0b1_000000000_000_00111100_00001000_000_110_100  # Y = Y + Z1
firmware[137] = 0b1_000000000_000_00111111_00001000_000_110_100  # Y = Y - Z1

# Acessando a memória por Z1 e colocando nela também
firmware[140] = 0b0_010001101_000_00010100_10000000_010_000_101 # X = mem[Z1]
firmware[141] = 0b1_000000000_000_00010100_00010000_000_000_000

firmware[142] = 0b0_010001111_000_00010100_10000000_010_000_101 # Y = mem[Z1]
firmware[143] = 0b1_000000000_000_00010100_00001000_000_000_000 

firmware[144] = 0b0_010010001_000_00010100_10000000_000_000_101
firmware[145] = 0b0_000000000_000_00010100_01000000_100_000_011 # mem[Z1] = X

firmware[146] = 0b0_010010011_000_00010100_10000000_000_000_101 # mem[Z1] = Y
firmware[147] = 0b0_000000000_000_00010100_01000000_100_000_100

# [148]: Z1 = mem[addr] 
firmware[148] = (0b0_010010110_000_00110101_00100000_011_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[150] = 0b1_000000000_000_00010100_00000010_000_000_000

# [151]: Z2 = mem[addr] 
firmware[151] = (0b0_010011001_000_00110101_00100000_011_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_MAR))
firmware[153] = 0b1_000000000_000_00010100_00000001_000_000_000

# [154]: Z2 = imm 
firmware[154] = (0b0_000000000_000_00110101_00100000_001_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_Z2))

# [156]: H = imm 
firmware[156] = (0b0_000000000_000_00110101_00100000_001_010_001 | _dual(ALU2_B, A2_MBR, B2_MBR, W2_H))

# Fazendo operações com X e Y e colocando o valor em Z1
firmware[158] = 0b1_000000000_000_00111100_00000010_000_101_011 # Z1 = X + Y
firmware[159] = 0b1_000000000_000_00111111_00000010_000_101_011 # Z1 = X - Y


# [160]: X = X AND imm  
firmware[160] = (0b0_000000000_000_00110101_00100000_001_010_001 | _dual(ALU2_AaB, A2_X, B2_MBR, W2_X, sf2=1))


#===================================================================
#Implementação do Shift and Add, imita o código abaixo com opcodes
# ==================================================================
#H = 0;
#while (X != 0){
#    if (X & 1)
#        H = H + Y;
#    X = X >> 1;
#    Y = Y << 1;
#}
#X = H;
#===================================================================

firmware[162] = 0b0_011001000_000_00010000_00000100_000_000_000   # H = 0 ; goto 200
# 200: if X == 0 -> fim (457) ; senao testa LSB (201)
firmware[200] = 0b1_011001001_001_00010100_00000000_000_000_011
# 201: if X impar -> soma (459) ; senao so desloca (203)
firmware[201] = 0b1_011001011_101_00000001_00000000_000_100_000
# 459 (=201|256): H = H + Y ; goto 203
firmware[459] = 0b0_011001011_000_00111100_00000100_000_000_100
# 203: X = X >> 1 (ALU1)  ||  Y = Y << 1 (ALU2) ; goto 200
firmware[203] = (0b0_011001000_000_10010100_00010000_000_000_011 | _dual(ALU2_Bshl, A2_MBR, B2_Y, W2_Y))
# 457 (=200|256): X = H (resultado) ; goto 0
firmware[457] = 0b0_000000000_000_00011000_00010000_000_000_000

#FIM DO SHIFT AND ADD



# [165, 166]:   X = X >> 8   ,    Y = Y >> 8  
firmware[165] = 0b1_000000000_000_00000100_00010000_000_000_011   
firmware[166] = 0b1_000000000_000_00000100_00001000_000_000_100   

# ============================================================================
# DIVISAO BINARIA SEM USAR / 
# Isso faz:
# quociente = dividendo / divisor
# A ideia é igual a divisão normal.
# Em vez de procurar múltiplos decimais do divisor,procuramos múltiplos em potências de 2.

# Algoritmo "escala-sobe / escala-desce" (long division binaria):
#   R = N(=X) ; M = D(=Y) ; P = 1(=H) ; [div] Q = 0(=Z1)
#   sobe : enquanto M <= R: M<<=1 ; P<<=1            (ate M passar de R)
#   recua: M>>=1 ; P>>=1                              (maior D<<k <= R)
#   desce: para cada nivel: se R>=M: R-=M (e Q+=P) ; M>>=1 ; P>>=1
# Cada fase faz O(log N) iteracoes; a ALU2 desloca P no MESMO ciclo em que a
# ALU1 desloca M, e soma Q no MESMO ciclo da subtracao de R (#4/#9 paralelismo).
# PRE-CONDICOES: Y > 0 e dividendo X < 2^31 (evita overflow no escalonamento).

# [163]: X = X // Y  
firmware[163] = (0b0_011111010_000_00110001_00000100_000_000_000  | _dual(ALU2_ZERO, A2_H, B2_MDR, W2_Z1))  # P=1 (H) || Q=0 (Z1) ; goto 250
firmware[250] = 0b1_011111011_010_00111111_00000000_000_101_011   # R-M ; R<D -> 507 ; senao 251
firmware[251] = 0b1_011111100_010_00111111_00000000_000_101_011   # R-M ; M>R -> 508 ; senao 252
firmware[252] = (0b0_011111011_000_01010100_00001000_000_000_100 | _dual(ALU2_Ashl, A2_H, B2_MDR, W2_H))   # M=M<<1 || P=P<<1 ; goto 251
firmware[508] = (0b0_011111101_000_10010100_00001000_000_000_100  | _dual(ALU2_Ashr, A2_H, B2_MDR, W2_H))  # recua: M=M>>1 || P=P>>1 ; goto 253
firmware[253] = 0b1_011111110_010_00111111_00000000_000_101_011   # R-M ; R<M -> 510 ; senao 254
firmware[254] = (0b0_011111000_000_00111111_00010000_000_101_011  | _dual(ALU2_ApB, A2_H, B2_Z1, W2_Z1))   # R=R-M || Q=Q+P ; goto 248
firmware[510] = 0b0_011111000_000_00010100_00000000_000_000_011   # pula subtracao ; goto 248
firmware[248] = 0b1_011111001_001_00111010_00000000_000_000_000   # P-1 ; P==1 -> 505 ; senao 249
firmware[249] = (0b0_011111101_000_10010100_00001000_000_000_100 | _dual(ALU2_Ashr, A2_H, B2_MDR, W2_H))   # M=M>>1 || P=P>>1 ; goto 253
firmware[507] = 0b0_000000000_000_00010100_00010000_000_000_101   # X = Q (Z1) ; goto 0
firmware[505] = 0b0_000000000_000_00010100_00010000_000_000_101   # X = Q (Z1) ; goto 0

# [164]: X = X % Y  
firmware[164] = 0b0_011110000_000_00110001_00000100_000_000_000   # P=1 (H) ; goto 240
firmware[240] = 0b1_011110001_010_00111111_00000000_000_101_011   # R-M ; R<D -> 497 ; senao 241
firmware[241] = 0b1_011110010_010_00111111_00000000_000_101_011   # R-M ; M>R -> 498 ; senao 242
firmware[242] = (0b0_011110001_000_01010100_00001000_000_000_100 | _dual(ALU2_Ashl, A2_H, B2_MDR, W2_H))  # M=M<<1 || P=P<<1 ; goto 241
firmware[498] = (0b0_011110100_000_10010100_00001000_000_000_100 | _dual(ALU2_Ashr, A2_H, B2_MDR, W2_H))  # recua: M=M>>1 || P=P>>1 ; goto 244
firmware[244] = 0b1_011110101_010_00111111_00000000_000_101_011   # R-M ; R<M -> 501 ; senao 245
firmware[245] = 0b0_011110110_000_00111111_00010000_000_101_011   # R=R-M ; goto 246
firmware[501] = 0b0_011110110_000_00010100_00000000_000_000_011   # pula subtracao ; goto 246
firmware[246] = 0b1_011110111_001_00111010_00000000_000_000_000   # P-1 ; P==1 -> 503 ; senao 247
firmware[247] = (0b0_011110100_000_10010100_00001000_000_000_100 | _dual(ALU2_Ashr, A2_H, B2_MDR, W2_H))   # M=M>>1 || P=P>>1 ; goto 244
firmware[497] = 0b0_000000000_000_00010100_00010000_000_000_011   # X = R (ja em X) ; goto 0
firmware[503] = 0b0_000000000_000_00010100_00010000_000_000_011   # X = R (ja em X) ; goto 0
firmware[255] = 0b0_000000000_000_00000000_00000000_000_000_000

# ============================================================================
# OPCODES "HARDWARE" DE 1 MICROCICLO  (combinadores na ALU — #3, #8, #12)
# ----------------------------------------------------------------------------
# Substituem os loops O(log N) por combinadores de 1 ciclo. Os opcodes antigos
# 162 (mul), 163 (div) e 164 (mod) sao mantidos intactos. Diferente deles, estes
# NAO destroem Y nem usam Z1/Z2: a ALU1 le X e Y e escreve so X.
# Semantica unsigned de 32 bits; divisao por 0 retorna 0.

# ---- opcode 167: X = X * Y  (multiplicador combinacional) ----
firmware[167] = 0b1_000000000_000_00000101_00010000_000_100_100

# ---- opcode 168: X = X // Y  (divisor combinacional; Y > 0) ----
firmware[168] = 0b1_000000000_000_00000110_00010000_000_100_100

# ---- opcode 169: X = X % Y  (resto combinacional; Y > 0) ----
firmware[169] = 0b1_000000000_000_00000111_00010000_000_100_100

# ---- opcode 170: X = X // Y  E  H = X % Y  no MESMO microciclo (ALU dupla) ----
# ALU1 escreve o quociente em X; a ALU2 usa o SNAPSHOT de X/Y pre-ALU1 para o
# resto, logo H = X_orig % Y_orig (e nao quociente % Y). Y preservado.
firmware[170] = (
    0b1_000000000_000_00000110_00010000_000_100_100
    | _dual(ALU2_MOD, A2_X, B2_Y, W2_H)
)

# ============================================================================
# BYTE LANES — BEXT / BINS  (extracao/empacotamento de bytes — #13)
# ----------------------------------------------------------------------------
# bextx/bexty imm : extraem o byte de indice imm (0..3) de X/Y em 1 microciclo,
#   substituindo a sequencia shrx8 + andxi 0xFF e permitindo qualquer posicao.
#   A ALU1 faz PC++/FETCH (MBR=imm) enquanto a ALU2 calcula (reg >> 8*imm)&0xFF.
# bpackx : anexa o byte baixo de Y a X -> X = (X<<8) | (Y & 0xFF). Primitiva de
#   empacotamento (inverso do bext): zera, e para cada byte faz bpackx.

# [171]: X = byte[imm] de X  =  (X >> 8*imm) & 0xFF 
firmware[171] = (0b0_000000000_000_00110101_00100000_001_010_001 | _dual(ALU2_BEXT, A2_X, B2_MBR, W2_X, sf2=1))
# [172]: Y = byte[imm] de Y  =  (Y >> 8*imm) & 0xFF 
firmware[172] = (0b0_000000000_000_00110101_00100000_001_010_001 | _dual(ALU2_BEXT, A2_Y, B2_MBR, W2_Y, sf2=1))
# [173]: X = (X << 8) | (Y & 0xFF)  (empacota byte de Y em X) 
firmware[173] = 0b1_000000000_000_00001001_00010000_000_100_100

# ============================================================================
# OPCODES DE OTIMIZACAO (acumulo e compare-and-swap em registradores)
# ============================================================================
# [174]: Z1 = Z1 + X  
firmware[174] = 0b1_000000000_000_00111100_00000010_000_110_011

# [175]: IF X <= Y GOTO addr   
# A ALU2 calcula X - Y e o JAM usa (N|Z): salto tomado se X <= Y. Permite
# compare-and-swap em registradores (jlexy + swap) sem passar pela memoria.
firmware[175] = _branch(0b011, ALU2_BmA, a2=A2_Y, b2=B2_X)

# [176]: IF X < Y GOTO addr  
# Limite de laco em 1 instrucao (ex.: quot < d) sem destruir X; substitui o
# par subxy + jn (5 µc -> 3 µc) e preserva o quociente.
firmware[176] = _branch(0b010, ALU2_BmA, a2=A2_Y, b2=B2_X)

# [177]: X = ordena os 4 bytes de X (rede combinacional) 
# Sorting network de 4 elementos em hardware (min/max branchless). Menor no MSB.
firmware[177] = 0b1_000000000_000_00001010_00010000_000_100_000

# [178]: X = produto escalar bytewise de X e Y 
# 4 multiplicadores de 8 bits + somador (MAC) em hardware combinacional.
firmware[178] = 0b1_000000000_000_00001011_00010000_000_100_100

# [179]: X = Z1 // Y , H = Z1 % Y  (divmod com dividendo em Z1) 
# Evita o 'z1tox' antes do divmod no laco
firmware[179] = (0b1_000000000_000_00000110_00010000_000_110_100 | _dual(ALU2_MOD, A2_Z1, B2_Y, W2_H))
# [181]: X = Z2 // Y , H = Z2 % Y  (divmod com dividendo em Z2) 
# (180 = NT_SLOT, reservado.)
firmware[181] = (0b1_000000000_000_00000110_00010000_000_111_100 | _dual(ALU2_MOD, A2_Z2, B2_Y, W2_H))

# ============================================================================
# Funções do processador.
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


# ============================================================================
# COMBINADORES DE MUL / DIV 
# Modelam o hardware: o multiplicador e um array de 32 somadores de produtos
# parciais; o divisor sao 32 estagios de divisao restauradora desenrolados.
# ============================================================================
def _mul32(a, b):
    # Soma dos produtos parciais: para cada bit i de b, soma (a<<i) mascarado.
    # -((b>>i)&1) vale 0 (bit zero) ou -1 (= todos-1, bit um), funcionando como
    # mascara AND. So usa +, deslocamentos, AND e negacao unaria.
    a &= 0xFFFFFFFF
    b &= 0xFFFFFFFF
    p  = (a       ) & -( b        & 1)
    p += (a <<  1) & -((b >>  1) & 1)
    p += (a <<  2) & -((b >>  2) & 1)
    p += (a <<  3) & -((b >>  3) & 1)
    p += (a <<  4) & -((b >>  4) & 1)
    p += (a <<  5) & -((b >>  5) & 1)
    p += (a <<  6) & -((b >>  6) & 1)
    p += (a <<  7) & -((b >>  7) & 1)
    p += (a <<  8) & -((b >>  8) & 1)
    p += (a <<  9) & -((b >>  9) & 1)
    p += (a << 10) & -((b >> 10) & 1)
    p += (a << 11) & -((b >> 11) & 1)
    p += (a << 12) & -((b >> 12) & 1)
    p += (a << 13) & -((b >> 13) & 1)
    p += (a << 14) & -((b >> 14) & 1)
    p += (a << 15) & -((b >> 15) & 1)
    p += (a << 16) & -((b >> 16) & 1)
    p += (a << 17) & -((b >> 17) & 1)
    p += (a << 18) & -((b >> 18) & 1)
    p += (a << 19) & -((b >> 19) & 1)
    p += (a << 20) & -((b >> 20) & 1)
    p += (a << 21) & -((b >> 21) & 1)
    p += (a << 22) & -((b >> 22) & 1)
    p += (a << 23) & -((b >> 23) & 1)
    p += (a << 24) & -((b >> 24) & 1)
    p += (a << 25) & -((b >> 25) & 1)
    p += (a << 26) & -((b >> 26) & 1)
    p += (a << 27) & -((b >> 27) & 1)
    p += (a << 28) & -((b >> 28) & 1)
    p += (a << 29) & -((b >> 29) & 1)
    p += (a << 30) & -((b >> 30) & 1)
    p += (a << 31) & -((b >> 31) & 1)
    return p & 0xFFFFFFFF


def _divstep(q, r, bit, b):
    # Um estagio da divisao restauradora. O emprestimo de (r-b) e detectado pelo
    # bit de sinal evitando o operador '<'.
    r  = (r << 1) | bit
    bf = ((r - b) >> 40) & 1        # 1 => houve emprestimo (r < b)
    r  = r if bf else r - b        # so subtrai quando NAO houve emprestimo
    q  = (q << 1) | (1 - bf)       # bit do quociente = NAO emprestimo
    return q, r


def _divmod32(a, b):
    # Divisor combinacional: 32 estagios desenrolados. Retorna (quociente, resto).
    a &= 0xFFFFFFFF
    b &= 0xFFFFFFFF
    if b == 0:
        return 0, 0                 # guarda divisao por zero
    q = 0
    r = 0
    q, r = _divstep(q, r, (a >> 31) & 1, b)
    q, r = _divstep(q, r, (a >> 30) & 1, b)
    q, r = _divstep(q, r, (a >> 29) & 1, b)
    q, r = _divstep(q, r, (a >> 28) & 1, b)
    q, r = _divstep(q, r, (a >> 27) & 1, b)
    q, r = _divstep(q, r, (a >> 26) & 1, b)
    q, r = _divstep(q, r, (a >> 25) & 1, b)
    q, r = _divstep(q, r, (a >> 24) & 1, b)
    q, r = _divstep(q, r, (a >> 23) & 1, b)
    q, r = _divstep(q, r, (a >> 22) & 1, b)
    q, r = _divstep(q, r, (a >> 21) & 1, b)
    q, r = _divstep(q, r, (a >> 20) & 1, b)
    q, r = _divstep(q, r, (a >> 19) & 1, b)
    q, r = _divstep(q, r, (a >> 18) & 1, b)
    q, r = _divstep(q, r, (a >> 17) & 1, b)
    q, r = _divstep(q, r, (a >> 16) & 1, b)
    q, r = _divstep(q, r, (a >> 15) & 1, b)
    q, r = _divstep(q, r, (a >> 14) & 1, b)
    q, r = _divstep(q, r, (a >> 13) & 1, b)
    q, r = _divstep(q, r, (a >> 12) & 1, b)
    q, r = _divstep(q, r, (a >> 11) & 1, b)
    q, r = _divstep(q, r, (a >> 10) & 1, b)
    q, r = _divstep(q, r, (a >>  9) & 1, b)
    q, r = _divstep(q, r, (a >>  8) & 1, b)
    q, r = _divstep(q, r, (a >>  7) & 1, b)
    q, r = _divstep(q, r, (a >>  6) & 1, b)
    q, r = _divstep(q, r, (a >>  5) & 1, b)
    q, r = _divstep(q, r, (a >>  4) & 1, b)
    q, r = _divstep(q, r, (a >>  3) & 1, b)
    q, r = _divstep(q, r, (a >>  2) & 1, b)
    q, r = _divstep(q, r, (a >>  1) & 1, b)
    q, r = _divstep(q, r, (a      ) & 1, b)
    return q & 0xFFFFFFFF, r & 0xFFFFFFFF


# ============================================================================
# MIN/MAX branchless e combinadores de byte (ordenacao e produto escalar).
# Sem laco, sem '*'/'/'/'%', sem relacionais: o sinal de (a-b) escolhe o menor.
# ============================================================================
def _mn(a, b):
    d = a - b
    m = d >> 40                 # 0 se a>=b ; -1 (todos-1) se a<b
    return (b + (d & m)) & 0xFF
def _mx(a, b):
    d = a - b
    m = d >> 40
    return (a - (d & m)) & 0xFF

def _bsort4(w):
    # Rede de ordenacao combinacional de 4 bytes (5 comparadores), crescente,
    # com o MENOR no byte mais significativo.
    b0 =  w        & 0xFF
    b1 = (w >> 8)  & 0xFF
    b2 = (w >> 16) & 0xFF
    b3 = (w >> 24) & 0xFF
    t = _mn(b0, b1); b1 = _mx(b0, b1); b0 = t
    t = _mn(b2, b3); b3 = _mx(b2, b3); b2 = t
    t = _mn(b0, b2); b2 = _mx(b0, b2); b0 = t
    t = _mn(b1, b3); b3 = _mx(b1, b3); b1 = t
    t = _mn(b1, b2); b2 = _mx(b1, b2); b1 = t
    return ((b0 << 24) | (b1 << 16) | (b2 << 8) | b3) & 0xFFFFFFFF

def _dot4(a, b):
    # Produto escalar bytewise (4 multiplicadores + somador): usa _mul32.
    s  = _mul32( a        & 0xFF,  b        & 0xFF)
    s += _mul32((a >>  8) & 0xFF, (b >>  8) & 0xFF)
    s += _mul32((a >> 16) & 0xFF, (b >> 16) & 0xFF)
    s += _mul32((a >> 24) & 0xFF, (b >> 24) & 0xFF)
    return s & 0xFFFFFFFF


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
    elif control_bits == 0b000100: o = (b & 0xFFFFFFFF) >> 8   # B >> 8 (extracao de byte)
    elif control_bits == 0b000101: o = _mul32(a, b)            # MUL  (combinacional)
    elif control_bits == 0b000110: o = _divmod32(a, b)[0]      # DIV  (combinacional, unsigned)
    elif control_bits == 0b000111: o = _divmod32(a, b)[1]      # MOD  (combinacional, unsigned)
    elif control_bits == 0b001000: o = (a >> ((b & 3) << 3)) & 0xFF  # BEXT (byte de indice b)
    elif control_bits == 0b001001: o = (a << 8) | (b & 0xFF)        # BINS (anexa byte baixo de b)
    elif control_bits == 0b001010: o = _bsort4(a)             # BSORT (ordena 4 bytes de a)
    elif control_bits == 0b001011: o = _dot4(a, b)           # DOT (produto escalar bytewise)
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
    if not (w2 == W2_NONE and alu2_ctrl == 0):
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
