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

N = 0  #indicadores de estado
Z = 1

BUS_A = 0 #entrada A da ALU, selecionada pelos bits 5..3 do MIR
BUS_B = 0 #entrada B da ALU, selecionada pelos bits 2..0 do MIR
BUS_C = 0 #carrega o resultado que vai p os registradores

firmware = array('Q',[0]) * 512  #cria um espaço que guarda as microinstruções (64 bits, usa 35)

# ==============================================================================
# LAYOUT DO MIR (35 bits):
# 000000000_000_00000000_000000_000_000_000
# [34:26] NEXT_ADDR (9b) | [25:23] JAM (3b) | [22:15] ALU (8b) [14:9] WRITE_REGS (6b) | [8:6] MEM (3b) | [5:3] BUS_A (3b) | [2:0] BUS_B (3b)
#
# BUS_A seletores (bits 5..3): 000=H  001=MDR 010=PC 011=MBR 100=X 101=Y 11x=0
# BUS_B seletores (bits 2..0): 000=MDR 001=PC 010=MBR 011=X 100=Y 1xx=0
# ==============================================================================

# 0: INIT/FETCH — BUS_C = PC+1; PC=BUS_C; FETCH; GOTO MBR
# BUS_A=PC(010), BUS_B=PC(001), ALU=B+1(00110101), WRITE=PC(001000), MEM=FETCH(001), JAM=MBR(100)
firmware[0] = 0b000000000_100_00110101_001000_001_010_001

# 2: X = X + mem[address] — 3 ciclos
# Ciclo 2: PC=PC+1; FETCH; GOTO 3
firmware[2] = 0b000000011_000_00110101_001000_001_010_001
# Ciclo 3: MAR=MBR; READ; GOTO 4 — BUS_B=MBR(010), ALU=B(00010100), WRITE=MAR(100000), MEM=READ(010)
firmware[3] = 0b000000100_000_00010100_100000_010_000_010
# Ciclo 4: X = MDR + X; GOTO 0 — BUS_A=MDR(001), BUS_B=X(011), ALU=A+B(00111100), WRITE=X(000100)
firmware[4] = 0b000000000_000_00111100_000100_000_001_011

# 6: memory[address] = X — 3 ciclos
# Ciclo 6: PC=PC+1; FETCH; GOTO 7
firmware[6] = 0b000000111_000_00110101_001000_001_010_001
# Ciclo 7: MAR=MBR; GOTO 8
firmware[7] = 0b000001000_000_00010100_100000_000_000_010
# Ciclo 8: MDR=X; WRITE_WORD; GOTO 0
firmware[8] = 0b000000000_000_00010100_010000_100_000_011

# 9: GOTO address — 2 ciclos
# Ciclo 9: PC=PC+1; FETCH; GOTO 10
firmware[9]  = 0b000001010_000_00110101_001000_001_010_001
# Ciclo 10: PC=MBR; FETCH; GOTO MBR
firmware[10] = 0b000000000_100_00010100_001000_001_000_010

# 11: IF X == 0 GOTO address
# Ciclo 11: BUS_C=X; se Z=1 GOTO 268, senão GOTO 12
firmware[11] =  0b000001100_001_00010100_000000_000_000_011
# Ciclo 12 (Z=0): PC=PC+1; GOTO 0 (descarta byte de endereço)
firmware[12] =  0b000000000_000_00110101_001000_000_010_001
# Ciclo 268 (Z=1): GOTO 9 — CORRIGIDO: ALU=B explícita
firmware[268] = 0b000001001_000_00010100_000000_000_000_000

# 13: X = X - mem[address] — 3 ciclos
# Ciclo 13: PC=PC+1; FETCH; GOTO 14
firmware[13] = 0b000001110_000_00110101_001000_001_010_001
# Ciclo 14: MAR=MBR; READ; GOTO 15
firmware[14] = 0b000001111_000_00010100_100000_010_000_010
# Ciclo 15: X = X - MDR (B-A = X-MDR); GOTO 0
# BUS_A=MDR(001), BUS_B=X(011), ALU=B-A(00111111), WRITE=X(000100)
firmware[15] = 0b000000000_000_00111111_000100_000_001_011

# 16: X = X + 1 — 1 ciclo
# BUS_B=X(011), ALU=B+1(00110101), WRITE=X(000100)
firmware[16] = 0b000000000_000_00110101_000100_000_000_011

# 17: X = X - 1 — 1 ciclo
# BUS_B=X(011), ALU=B-1(00110110), WRITE=X(000100)
firmware[17] = 0b000000000_000_00110110_000100_000_000_011

# 18: IF X < 0 GOTO address — 2 ou 3 ciclos
# Ciclo 18: BUS_C=X; se N=1 GOTO 274 (=18|256), senão GOTO 19
firmware[18] =  0b000010011_010_00010100_000000_000_000_011
# Ciclo 19 (N=0): PC=PC+1; GOTO 0 (descarta byte de endereço)
firmware[19] =  0b000000000_000_00110101_001000_000_010_001
# Ciclo 275 (N=1): GOTO 9 (executa o desvio)
firmware[275] = 0b000001001_000_00010100_000000_000_000_000

# 20: Y = X — 1 ciclo
# BUS_B=X(011), ALU=B(00010100), WRITE=Y(000010)
firmware[20] = 0b000000000_000_00010100_000010_000_000_011

# 21: X = Y — 1 ciclo
# BUS_B=Y(100), ALU=B(00010100), WRITE=X(000100)
firmware[21] = 0b000000000_000_00010100_000100_000_000_100

# 22: mem[address] = Y — 3 ciclos
# Ciclo 22: PC=PC+1; FETCH; GOTO 23
firmware[22] = 0b000010111_000_00110101_001000_001_010_001
# Ciclo 23: MAR=MBR; GOTO 24
firmware[23] = 0b000011000_000_00010100_100000_000_000_010
# Ciclo 24: MDR=Y; WRITE_WORD; GOTO 0
firmware[24] = 0b000000000_000_00010100_010000_100_000_100

# 25: Y = Y + mem[address] — 3 ciclos
# Ciclo 25: PC=PC+1; FETCH; GOTO 26
firmware[25] = 0b000011010_000_00110101_001000_001_010_001
# Ciclo 26: MAR=MBR; READ; GOTO 27
firmware[26] = 0b000011011_000_00010100_100000_010_000_010
# Ciclo 27: Y = MDR + Y; GOTO 0 — BUS_A=MDR(001), BUS_B=Y(100), ALU=A+B(00111100), WRITE=Y(000010)
firmware[27] = 0b000000000_000_00111100_000010_000_001_100

# 28: Y = mem[address] — 3 ciclos
# Ciclo 28: PC=PC+1; FETCH; GOTO 29
firmware[28] = 0b000011101_000_00110101_001000_001_010_001
# Ciclo 29: MAR=MBR; READ; GOTO 30
firmware[29] = 0b000011110_000_00010100_100000_010_000_010
# Ciclo 30: Y=MDR; GOTO 0 — BUS_B=MDR(000), ALU=B(00010100), WRITE=Y(000010)
firmware[30] = 0b000000000_000_00010100_000010_000_000_000

# 31: X = X << 1 (X * 2) — 1 ciclo
# BUS_B=X(011), ALU=shift<<1+B(01_010100), WRITE=X(000100)
firmware[31] = 0b000000000_000_01010100_000100_000_000_011

# 32: X = X >> 1 (X / 2) — 1 ciclo
# BUS_B=X(011), ALU=shift>>1+B(10_010100), WRITE=X(000100)
firmware[32] = 0b000000000_000_10010100_000100_000_000_011

# 33: Y = Y + 1 — 1 ciclo
# BUS_B=Y(100), ALU=B+1(00110101), WRITE=Y(000010)
firmware[33] = 0b000000000_000_00110101_000010_000_000_100

# 34: Y = Y - 1 — 1 ciclo
# BUS_B=Y(100), ALU=B-1(00110110), WRITE=Y(000010)
firmware[34] = 0b000000000_000_00110110_000010_000_000_100

# 35: IF Y == 0 GOTO address — 2 ou 3 ciclos
# Ciclo 35: testa Y; se Z=1 GOTO 291 (=35|256), senão GOTO 36
firmware[35]  = 0b000100100_001_00010100_000000_000_000_100
# Ciclo 36 (Z=0): PC=PC+1; GOTO 0 (descarta byte de endereço)
firmware[36]  = 0b000000000_000_00110101_001000_000_010_001
# Ciclo 292 (Z=1): GOTO 9
firmware[292] = 0b000001001_000_00010100_000000_000_000_000

# 40: X = mem[addr] — 3 ciclos
# Ciclo 40: PC=PC+1; FETCH; GOTO 128
firmware[40]  = 0b010000000_000_00110101_001000_001_010_001
# Ciclo 128: MAR=MBR + READ (fundidos); GOTO 129
firmware[128] = 0b010000001_000_00010100_100000_010_000_010
# Ciclo 129: X=MDR; GOTO 0
firmware[129] = 0b000000000_000_00010100_000100_000_000_000

# 41: X = 0 — 1 ciclo
# ALU=0(00010000), WRITE=X(000100)
firmware[41] = 0b000000000_000_00010000_000100_000_000_000

# 42: Y = 0 — 1 ciclo
# ALU=0(00010000), WRITE=Y(000010)
firmware[42] = 0b000000000_000_00010000_000010_000_000_000

# 43: IF X <= 0 GOTO address — 2 ou 3 ciclos
# JAM=011 (N|Z): desvia se X<0 OU X==0
# Ciclo 43: testa X; se N|Z GOTO 299 (=43|256), senão GOTO 132
firmware[43]  = 0b010000100_011_00010100_000000_000_000_011
# Ciclo 132 (X>0): PC=PC+1; GOTO 0 (descarta byte de endereço)
firmware[132] = 0b000000000_000_00110101_001000_000_010_001
# Ciclo 388 (X<=0): GOTO 9
firmware[388] = 0b000001001_000_00010100_000000_000_000_000

# 45: X = X + Y — 1 ciclo
# BUS_A=X(100), BUS_B=Y(100)... conflito de seletor B!
# BUS_B não tem X e Y ao mesmo tempo. Usar A=Y, B=X (A+B comutativo)
# BUS_A=Y(101), BUS_B=X(011), ALU=A+B(00111100), WRITE=X(000100)
firmware[45] = 0b000000000_000_00111100_000100_000_101_011

# 46: X = X - Y — 1 ciclo
# B-A = X-Y: BUS_A=Y(101), BUS_B=X(011), ALU=B-A(00111111), WRITE=X(000100)
firmware[46] = 0b000000000_000_00111111_000100_000_101_011

# 47: Y = X + Y — 1 ciclo
# BUS_A=Y(101), BUS_B=X(011), ALU=A+B(00111100), WRITE=Y(000010)
firmware[47] = 0b000000000_000_00111100_000010_000_101_011

# 48: SWAP X, Y — 1 opcode, 3 microciclos internos
# microciclo 48: H = X; GOTO 130
firmware[48]  = 0b010000010_000_00010100_000001_000_000_011
# microciclo 130: X = Y; GOTO 131
firmware[130] = 0b010000011_000_00010100_000100_000_000_100
# microciclo 131: Y = H (ALU=A, A=H); GOTO 0
firmware[131] = 0b000000000_000_00011000_000010_000_000_000

# 49: Y = Y << 1 (Y * 2) — 1 ciclo
# BUS_B=Y(100), ALU=shift<<1+B(01_010100), WRITE=Y(000010)
firmware[49] = 0b000000000_000_01010100_000010_000_000_100

# 50: Y = Y >> 1 (Y / 2) — 1 ciclo
# BUS_B=Y(100), ALU=shift>>1+B(10_010100), WRITE=Y(000010)
firmware[50] = 0b000000000_000_10010100_000010_000_000_100

# 255: HALT
firmware[255] = 0b00000000000000000000000000000000000

def read_regs(reg_num):
    global MDR, PC, MBR, X, Y, H, BUS_A, BUS_B
    
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
    else:
       BUS_A = 0
    
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
    else:
       BUS_B = 0

def write_regs(reg_bits):
    global MAR, MDR, PC, X, Y, H, BUS_C
    
    if reg_bits & 0b100000:
       MAR = BUS_C
    if reg_bits & 0b010000:
       MDR = BUS_C
    if reg_bits & 0b001000:
       PC = BUS_C
    if reg_bits & 0b000100:
       X = BUS_C
    if reg_bits & 0b000010:
       Y = BUS_C
    if reg_bits & 0b000001:
       H = BUS_C

def alu(control_bits):
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
   
    o = o & 0xFFFFFFFF

    # CORRIGIDO: shift aplicado ANTES das flags, N/Z refletem o valor final de BUS_C
    if shift_bits == 0b01:
       o = (o << 1) & 0xFFFFFFFF
    elif shift_bits == 0b10:
       o = o >> 1
    elif shift_bits == 0b11:
       o = (o << 8) & 0xFFFFFFFF

    if o == 0:
        N = 0
        Z = 1
    elif o & 0x80000000:    
        N = 1
        Z = 0
    else:
        N = 0
        Z = 0

    BUS_C = o
    
def next_instruction(nextadd, jam):
    global MPC
    
    if jam == 0b000:
        MPC = nextadd
        return
        
    if jam & 0b001:
        nextadd = nextadd | (Z << 8)
        
    if jam & 0b010:
        nextadd = nextadd | (N << 8)
        
    if jam & 0b100:
        nextadd = nextadd | MBR
        
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

   # CORRIGIDO: máscaras atualizadas para layout de 35 bits
   read_regs(MIR & 0b111111)
   alu((MIR >> 15) & 0xFF)
   write_regs((MIR >>  9) & 0b111111)
   memory_io((MIR >>  6) & 0b111)
   next_instruction((MIR >> 26) & 0x1FF,(MIR >> 23) & 0b111)
   
   return True