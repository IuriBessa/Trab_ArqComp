import sys

# ==============================================================================
# assembler_teste.py  —  Assembler para o processador definido em teste.py
#
# USO:
#   python assembler_teste.py programa.asm saida.bin
#
# FORMATO DO ARQUIVO .asm:
#   [label:] instrução [operando]   ; comentário opcional
#
# Igual ao assembler_ufc2x.py, mas com as instruções extras suportadas pelo
# teste.py (registradores Z1/Z2, imediatos, novos saltos, lógicas, etc.).
# ==============================================================================

# ------------------------------------------------------------------------------
# TABELA DE INSTRUÇÕES
#
# no_op_instructions  → instrução SEM operando        (1 byte)
# mem_instructions    → instrução com ENDEREÇO DE MEMÓRIA (2 bytes)
# jmp_instructions    → instrução com ENDEREÇO DE SALTO   (2 bytes)
# imm_instructions    → instrução com VALOR IMEDIATO de 1 byte (2 bytes)
# ------------------------------------------------------------------------------

# Instruções sem operando — apenas emitem 1 byte (o opcode)
no_op_instructions = {
    'halt'  : 0xFF,
    'incx'  : 16,
    'decx'  : 17,
    'incy'  : 33,
    'decy'  : 34,
    'ytox'  : 20,
    'xtoy'  : 21,
    'shlx'  : 31,
    'shrx'  : 32,
    'shly'  : 49,
    'shry'  : 50,
    'addxy' : 45,
    'subxy' : 46,
    'addyx' : 47,
    'swap'  : 48,
    'clrx'  : 41,
    'clry'  : 42,
    # Novos em teste.py
    'xtoh'  : 53,   # H = X
    'htox'  : 54,   # X = H
    'ytoh'  : 55,   # H = Y
    'htoy'  : 56,   # Y = H
    'andxy' : 64,   # X = X AND Y
    'orxy'  : 65,   # X = X OR  Y
    'xtoz1' : 68,   # Z1 = X
    'ytoz1' : 69,   # Z1 = Y
    'z1tox' : 70,   # X  = Z1
    'z1toy' : 71,   # Y  = Z1
    'xtoz2' : 72,   # Z2 = X
    'ytoz2' : 73,   # Z2 = Y
    'z2tox' : 74,   # X  = Z2
    'z2toy' : 75,   # Y  = Z2
    'subyx' : 78,   # Y = Y - X
    'xorxy' : 79,   # X = X XOR Y
    'absx'  : 80,   # X = |X|
}

# Instruções com endereço de MEMÓRIA — emitem 2 bytes: [opcode, word_addr]
mem_instructions = {
    'add'   : 2,
    'sub'   : 13,
    'mov'   : 6,
    'ldx'   : 40,
    'addy'  : 25,
    'ldy'   : 28,
    'movy'  : 22,
    # Novos em teste.py
    'suby'  : 61,   # Y = Y - mem[addr]
}

# Instruções com endereço de SALTO — emitem 2 bytes: [opcode, byte_addr]
jmp_instructions = {
    'goto'  : 9,
    'jz'    : 11,
    'jn'    : 18,
    'jzy'   : 35,
    'jle'   : 43,
    # Novos em teste.py
    'jley'  : 57,   # IF Y <= 0 GOTO addr
    'jny'   : 59,   # IF Y <  0 GOTO addr
    'jodd'  : 76,   # IF X ímpar GOTO addr
}

# Instruções com VALOR IMEDIATO — emitem 2 bytes: [opcode, imm_byte (0..255)]
imm_instructions = {
    'ldxi'  : 66,   # X = imm
    'ldyi'  : 67,   # Y = imm
}

# Todas as palavras-chave reservadas
all_keywords = (set(no_op_instructions) | set(mem_instructions) |
                set(jmp_instructions)   | set(imm_instructions) |
                {'wb', 'ww'})

# ------------------------------------------------------------------------------
# Estado global
# ------------------------------------------------------------------------------
lines     = []
lines_bin = []
names     = []

# ------------------------------------------------------------------------------
# Funções auxiliares
# ------------------------------------------------------------------------------

def is_instruction(tok):
    return tok in all_keywords

def is_name(tok):
    return any(n[0] == tok for n in names)

def get_name_byte(tok):
    for name in names:
        if name[0] == tok:
            return name[1]
    return None

# ------------------------------------------------------------------------------
# Codificadores por tipo
# ------------------------------------------------------------------------------

def encode_no_op(inst):
    return [no_op_instructions[inst]]

def encode_mem(inst, ops):
    if len(ops) < 1:
        return []
    if not is_name(ops[0]):
        return []
    return [mem_instructions[inst], ops[0]]

def encode_jmp(inst, ops):
    if len(ops) < 1:
        return []
    if not is_name(ops[0]):
        return []
    return [jmp_instructions[inst], ops[0]]

def encode_imm(inst, ops):
    """Instrução com imediato: [opcode, byte_imm]"""
    if not ops or not ops[0].lstrip('-').isnumeric():
        return []
    val = int(ops[0]) & 0xFF
    return [imm_instructions[inst], val]

def encode_wb(ops):
    if not ops or not ops[0].lstrip('-').isnumeric():
        return []
    val = int(ops[0])
    if not (0 <= val <= 255):
        return []
    return [val]

def encode_ww(ops):
    if not ops or not ops[0].lstrip('-').isnumeric():
        return []
    val = int(ops[0]) & 0xFFFFFFFF
    return [
        val & 0xFF,
        (val >> 8)  & 0xFF,
        (val >> 16) & 0xFF,
        (val >> 24) & 0xFF,
    ]

def encode_instruction(inst, ops):
    if inst in no_op_instructions:
        return encode_no_op(inst)
    elif inst in mem_instructions:
        return encode_mem(inst, ops)
    elif inst in jmp_instructions:
        return encode_jmp(inst, ops)
    elif inst in imm_instructions:
        return encode_imm(inst, ops)
    elif inst == 'wb':
        return encode_wb(ops)
    elif inst == 'ww':
        return encode_ww(ops)
    return []

# ------------------------------------------------------------------------------
# Passo 1: codificação sem resolução de nomes
# ------------------------------------------------------------------------------

def line_to_bin_step1(line):
    if is_instruction(line[0]):
        return encode_instruction(line[0], line[1:])
    elif len(line) > 1 and is_instruction(line[1]):
        return encode_instruction(line[1], line[2:])
    return []

def lines_to_bin_step1():
    for i, line in enumerate(lines):
        lb = line_to_bin_step1(line)
        if lb == []:
            print(f"[ERRO] Sintaxe inválida na linha {i+1}: {' '.join(line)}")
            return False
        lines_bin.append(lb)
    return True

# ------------------------------------------------------------------------------
# Descoberta de labels
# ------------------------------------------------------------------------------

def find_names():
    for k, line in enumerate(lines):
        if not is_instruction(line[0]):
            names.append((line[0], k))

# ------------------------------------------------------------------------------
# Passo 2: resolução de endereços
# ------------------------------------------------------------------------------

def count_bytes(line_number):
    byte = 1
    for i in range(line_number):
        byte += len(lines_bin[i])
    return byte

def resolve_names():
    for i in range(len(names)):
        names[i] = (names[i][0], count_bytes(names[i][1]))

    for line in lines_bin:
        for i in range(len(line)):
            if is_name(line[i]):
                byte_addr = get_name_byte(line[i])
                opcode    = line[i - 1]

                # Memória usa word address; salto usa byte address.
                if opcode in mem_instructions.values():
                    line[i] = byte_addr // 4
                else:
                    line[i] = byte_addr

# ------------------------------------------------------------------------------
# Leitura do arquivo fonte
# ------------------------------------------------------------------------------

fsrc = open(str(sys.argv[1]), 'r')

for raw_line in fsrc:
    text = raw_line.split(';')[0]
    tokens = text.replace('\n', '').replace(',', '').lower().split()
    if tokens and tokens[0].endswith(':'):
        tokens[0] = tokens[0][:-1]
    if tokens:
        lines.append(tokens)

fsrc.close()

# ------------------------------------------------------------------------------
# Pipeline de montagem
# ------------------------------------------------------------------------------

find_names()

if lines_to_bin_step1():
    resolve_names()

    byte_arr = [0]
    for line in lines_bin:
        for b in line:
            byte_arr.append(b)

    fdst = open(str(sys.argv[2]), 'wb')
    fdst.write(bytearray(byte_arr))
    fdst.close()
