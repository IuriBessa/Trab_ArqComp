import sys

# ==============================================================================
# assembler_ufc2x.py  —  Assembler para o processador ufc2x (processador.py)
#
# USO:
#   python assembler_ufc2x.py programa.asm saida.bin
#
# FORMATO DO ARQUIVO .asm:
#   [label:] instrução [operando]   ; comentário opcional
#
# EXEMPLO:
#   inicio: clrx                    ; X = 0
#           ldx valor               ; X = mem[valor]
#           jz  fim                 ; se X==0, pula
#           decx
#           goto inicio
#   fim:    halt
#   valor:  ww 42                   ; declara palavra de 32 bits = 42
# ==============================================================================

# ------------------------------------------------------------------------------
# TABELA DE INSTRUÇÕES
#
# Para ADICIONAR uma nova instrução ao processador, basta inserir uma entrada
# no dicionário correto abaixo, de acordo com o tipo de operando:
#
#   no_op_instructions  → instrução SEM operando        (ex: halt, incx)
#   mem_instructions    → instrução com ENDEREÇO DE MEMÓRIA (ex: ldx, add)
#   jmp_instructions    → instrução com ENDEREÇO DE SALTO   (ex: goto, jz)
#
# O valor de cada entrada é o opcode (número da linha no firmware).
# ------------------------------------------------------------------------------

# Instruções sem operando — apenas emitem 1 byte (o opcode)
no_op_instructions = {
    'halt'  : 0xFF,   # para execução
    'incx'  : 16,     # X = X + 1
    'decx'  : 17,     # X = X - 1
    'incy'  : 33,     # Y = Y + 1
    'decy'  : 34,     # Y = Y - 1
    'ytox'  : 20,     # Y = X
    'xtoy'  : 21,     # X = Y
    'shlx'  : 31,     # X = X << 1  (X * 2)
    'shrx'  : 32,     # X = X >> 1  (X / 2)
    'shly'  : 49,     # Y = Y << 1  (Y * 2)
    'shry'  : 50,     # Y = Y >> 1  (Y / 2)
    'addxy' : 45,     # X = X + Y
    'subxy' : 46,     # X = X - Y
    'addyx' : 47,     # Y = X + Y
    'swap'  : 48,     # troca X <-> Y
    'clrx'  : 41,     # X = 0
    'clry'  : 42,     # Y = 0
}

# Instruções com endereço de MEMÓRIA — emitem 2 bytes: [opcode, word_addr]
# word_addr = byte_addr // 4  (memória endereçada por words de 32 bits)
mem_instructions = {
    'add'   : 2,      # X = X + mem[addr]
    'sub'   : 13,     # X = X - mem[addr]
    'mov'   : 6,      # mem[addr] = X  (store X)
    'ldx'   : 40,     # X = mem[addr]  (load X)
    'addy'  : 25,     # Y = Y + mem[addr]
    'ldy'   : 28,     # Y = mem[addr]  (load Y)
    'movy'  : 22,     # mem[addr] = Y  (store Y)
}

# Instruções com endereço de SALTO — emitem 2 bytes: [opcode, byte_addr]
# byte_addr = endereço absoluto em bytes no binário
jmp_instructions = {
    'goto'  : 9,      # PC = addr  (salto incondicional)
    'jz'    : 11,     # se X == 0, PC = addr
    'jn'    : 18,     # se X < 0,  PC = addr
    'jzy'   : 35,     # se Y == 0, PC = addr
    'jle'   : 43,     # se X <= 0, PC = addr
}

# Todas as palavras-chave reservadas
all_keywords = (set(no_op_instructions) | set(mem_instructions) |
                set(jmp_instructions) | {'wb', 'ww'})

# ------------------------------------------------------------------------------
# Estado global
# ------------------------------------------------------------------------------
lines     = []   # linhas tokenizadas
lines_bin = []   # bytes de cada linha (labels ainda como strings)
names     = []   # lista de (nome_label, índice_linha)

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
    """Instrução com endereço de memória: [opcode, label_placeholder]"""
    if len(ops) < 1:
        return []
    if not is_name(ops[0]):
        return []
    return [mem_instructions[inst], ops[0]]   # ops[0] é resolvido depois

def encode_jmp(inst, ops):
    """Instrução de salto: [opcode, label_placeholder]"""
    if len(ops) < 1:
        return []
    if not is_name(ops[0]):
        return []
    return [jmp_instructions[inst], ops[0]]   # ops[0] é resolvido depois

def encode_wb(ops):
    """wb <valor 0-255>: emite 1 byte cru"""
    if not ops or not ops[0].lstrip('-').isnumeric():
        return []
    val = int(ops[0])
    if not (0 <= val <= 255):
        return []
    return [val]

def encode_ww(ops):
    """ww <valor 0..2^32-1>: emite 4 bytes em little-endian"""
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
            names.append((line[0], k))   # (nome, índice de linha)

# ------------------------------------------------------------------------------
# Passo 2: resolução de endereços reais
# ------------------------------------------------------------------------------

def count_bytes(line_number):
    """Retorna o byte offset da linha no binário final (começa em 1, pois byte 0 é reservado)."""
    byte = 1
    for i in range(line_number):
        byte += len(lines_bin[i])
    return byte

def resolve_names():
    # Converte índices de linha em offsets de bytes
    for i in range(len(names)):
        names[i] = (names[i][0], count_bytes(names[i][1]))

    # Substitui strings de label pelos endereços numéricos
    for line in lines_bin:
        for i in range(len(line)):
            if is_name(line[i]):
                byte_addr = get_name_byte(line[i])
                opcode    = line[i - 1]

                # -------------------------------------------------------
                # REGRA DE ENDEREÇAMENTO — importante para novas instruções
                #
                # Instruções de MEMÓRIA (read/write_word via MAR):
                #   MAR = MBR → read_word(MAR) usa endereço de word
                #   Portanto: word_addr = byte_addr // 4
                #
                # Instruções de SALTO (PC = MBR):
                #   PC é byte address → usa byte_addr direto
                # -------------------------------------------------------
                if opcode in mem_instructions.values():
                    line[i] = byte_addr // 4    # word address
                else:
                    line[i] = byte_addr         # byte address

# ------------------------------------------------------------------------------
# Leitura do arquivo fonte
# ------------------------------------------------------------------------------

fsrc = open(str(sys.argv[1]), 'r')

for raw_line in fsrc:
    # Remove comentários (tudo após ';')
    text = raw_line.split(';')[0]
    # Tokeniza
    tokens = text.replace('\n', '').replace(',', '').lower().split()
    # Remove ':' de labels (ex: "loop:" → "loop")
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

    byte_arr = [0]   # byte 0 reservado (PC inicial = 0 → aponta aqui, depois fetch vai para 1)
    for line in lines_bin:
        for b in line:
            byte_arr.append(b)

    fdst = open(str(sys.argv[2]), 'wb')
    fdst.write(bytearray(byte_arr))
    fdst.close()

    print(f"Montagem concluída: {len(byte_arr)} bytes → '{sys.argv[2]}'")
    if '--map' in sys.argv:
        print("\n--- Mapa de endereços ---")
        for nome, addr in names:
            print(f"  {nome:<15} byte={addr:3d}  word={addr//4:3d}")
