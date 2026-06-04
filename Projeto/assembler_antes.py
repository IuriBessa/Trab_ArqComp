#!/usr/bin/env python3
# ==============================================================================
# assembler_ufc2x_dual.py  -  Assembler para o processador ufc2x_dual.py
#
# USO:
#   python assembler_ufc2x_dual.py programa.asm saida.bin
#
# FORMATO .asm:
#   [label:] instrução [operando]   ; comentário opcional
# ==============================================================================

import sys

# -- SEM OPERANDO (1 byte) ----------------------------------------------------
no_op_instructions = {
    'halt'    : 0xFF,
    'ret'     : 105,
    'incx'    : 16,  'decx'    : 17,
    'incy'    : 33,  'decy'    : 34,
    'addxy'   : 45,  'subxy'   : 46,
    'addyx'   : 47,  'subyx'   : 78,
    'addxz1'  : 125, 'subxz1'  : 126,
    'addyz1'  : 127, 'subyz1'  : 137,
    'addz1xy' : 158, 'subz1xy' : 159,
    'incz1'   : 84,  'decz1'   : 83,
    'incz2'   : 91,  'decz2'   : 90,
    'inch'    : 88,  'dech'    : 89,
    'andxy'   : 64,  'orxy'    : 65,
    'xorxy'   : 79,  'absx'    : 80,
    'shlx'    : 31,  'shrx'    : 32,
    'shly'    : 49,  'shry'    : 50,
    'shrx8'   : 165, 'shry8'   : 166,   # X >>= 8 / Y >>= 8 (extracao de byte)
    'swap'    : 48,
    'mulxy'   : 162,                  # X = X * Y   (destroi Y e H)
    'divxy'   : 163,                  # X = X // Y  (destroi H; Y > 0)
    'modxy'   : 164,                  # X = X % Y   (Y > 0)
    'ytox'    : 20,  'xtoy'    : 21,
    'xtoh'    : 53,  'htox'    : 54,
    'ytoh'    : 55,  'htoy'    : 56,
    'xtoz1'   : 68,  'ytoz1'   : 69,
    'z1tox'   : 70,  'z1toy'   : 71,
    'xtoz2'   : 72,  'ytoz2'   : 73,
    'z2tox'   : 74,  'z2toy'   : 75,
    'z1toh'   : 117, 'htoz1'   : 116,
    'z2toh'   : 119, 'htoz2'   : 118,
    'z1toz2'  : 120, 'z2toz1'  : 121,
    'ldxiz1'  : 140, 'ldyiz1'  : 142,
    'moviz1x' : 144, 'moviz1y' : 146,
    'clrx'    : 41,  'clry'    : 42,
    'clrh'    : 94,  'clrz1'   : 95,  'clrz2' : 96,
}

# -- COM ENDEREÇO DE MEMÓRIA (2 bytes: opcode + word_addr) --------------------
mem_instructions = {
    'mov'   : 6,     # mem[addr] = X
    'movy'  : 22,    # mem[addr] = Y
    'movz1' : 97,    # mem[addr] = Z1
    'movz2' : 122,   # mem[addr] = Z2
    'add'   : 2,     # X = X + mem[addr]
    'sub'   : 13,    # X = X - mem[addr]
    'addy'  : 25,    # Y = Y + mem[addr]
    'suby'  : 61,    # Y = Y - mem[addr]
    'ldx'   : 40,    # X  = mem[addr]
    'ldy'   : 28,    # Y  = mem[addr]
    'ldz1'  : 148,   # Z1 = mem[addr]
    'ldz2'  : 151,   # Z2 = mem[addr]
}

# -- SALTOS (2 bytes: opcode + byte_addr) -------------------------------------
jmp_instructions = {
    'goto'  : 9,
    'jz'    : 11,   'jn'    : 18,   'jle'   : 43,   'jnn'   : 100,
    'jodd'  : 76,   'jzy'   : 35,   'jny'   : 59,   'jley'  : 57,
    'jnz1'  : 106,  'jlez1' : 108,  'jzz1'  : 85,   'jzz2'  : 92,
    'jzh'   : 110,  'jnh'   : 112,  'jleh'  : 114,
    'call'  : 102,
}

# -- IMEDIATOS (2 bytes: opcode + imm) ----------------------------------------
imm_instructions = {
    'ldxi'  : 66,   'ldyi'  : 67,
    'ldz1i' : 87,   'ldz2i' : 154,  'ldhi' : 156,
    'andxi' : 160,                  # X = X AND imm
}

all_keywords = (
    set(no_op_instructions) | set(mem_instructions) |
    set(jmp_instructions)   | set(imm_instructions) |
    {'wb', 'ww'}
)

lines     = []
lines_bin = []
names     = []
label_defs = set()   # nomes explicitamente declarados com ':'


def is_instruction(tok):
    if tok in label_defs:
        return False
    return tok in all_keywords

def is_name(tok):
    return isinstance(tok, str) and any(n[0] == tok for n in names)

def get_name_byte(tok):
    for name in names:
        if name[0] == tok:
            return name[1]
    return None


def encode_no_op(inst):
    return [no_op_instructions[inst]]

def encode_mem(inst, ops):
    if not ops or not is_name(ops[0]):
        return []
    return [mem_instructions[inst], ops[0]]

def encode_jmp(inst, ops):
    if not ops or not is_name(ops[0]):
        return []
    return [jmp_instructions[inst], ops[0]]

def encode_imm(inst, ops):
    if not ops:
        return []
    try:
        val = int(ops[0], 0) & 0xFF
    except (ValueError, TypeError):
        return []
    return [imm_instructions[inst], val]

def encode_wb(ops):
    if not ops:
        return []
    try:
        val = int(ops[0], 0)
    except (ValueError, TypeError):
        return []
    if not (0 <= val <= 255):
        return []
    return [val]

def encode_ww(ops):
    if not ops:
        return []
    try:
        val = int(ops[0], 0) & 0xFFFFFFFF
    except (ValueError, TypeError):
        return []
    return [val & 0xFF, (val>>8)&0xFF, (val>>16)&0xFF, (val>>24)&0xFF]

def encode_instruction(inst, ops):
    if inst in no_op_instructions : return encode_no_op(inst)
    if inst in mem_instructions   : return encode_mem(inst, ops)
    if inst in jmp_instructions   : return encode_jmp(inst, ops)
    if inst in imm_instructions   : return encode_imm(inst, ops)
    if inst == 'wb'               : return encode_wb(ops)
    if inst == 'ww'               : return encode_ww(ops)
    return []


def line_to_bin_step1(line):
    if is_instruction(line[0]):
        return encode_instruction(line[0], line[1:])
    elif len(line) > 1 and is_instruction(line[1]):
        return encode_instruction(line[1], line[2:])
    elif len(line) == 1 and not is_instruction(line[0]):
        return ['__label__']
    return []

def lines_to_bin_step1():
    ok = True
    for i, line in enumerate(lines):
        lb = line_to_bin_step1(line)
        if lb == []:
            print(f"[ERRO] Sintaxe inválida na linha {i+1}: {' '.join(line)}")
            ok = False
        lines_bin.append(lb)
    return ok


def find_names():
    for k, line in enumerate(lines):
        if not is_instruction(line[0]):
            names.append((line[0], k))


def count_bytes(line_number):
    byte = 1
    for i in range(line_number):
        lb = lines_bin[i]
        if lb != ['__label__']:
            byte += len(lb)
    return byte

def resolve_names():
    for i in range(len(names)):
        names[i] = (names[i][0], count_bytes(names[i][1]))

    for line in lines_bin:
        if line == ['__label__']:
            continue
        for i in range(len(line)):
            if is_name(line[i]):
                byte_addr = get_name_byte(line[i])
                opcode    = line[i - 1]
                if opcode in mem_instructions.values():
                    line[i] = byte_addr // 4
                else:
                    line[i] = byte_addr


def main():
    if len(sys.argv) < 3:
        print("Uso: python assembler_ufc2x_dual.py entrada.asm saida.bin")
        sys.exit(1)

    try:
        fsrc = open(sys.argv[1], 'r', encoding='utf-8')
    except FileNotFoundError:
        print(f"[ERRO] Arquivo não encontrado: {sys.argv[1]}")
        sys.exit(1)

    for raw_line in fsrc:
        text   = raw_line.split(';')[0]
        tokens = text.replace('\n','').replace(',','').lower().split()
        if tokens and tokens[0].endswith(':'):
            tokens[0] = tokens[0][:-1]
            label_defs.add(tokens[0])
        if tokens:
            lines.append(tokens)
    fsrc.close()

    find_names()
    if not lines_to_bin_step1():
        sys.exit(1)
    resolve_names()

    byte_arr = bytearray([0])
    for line in lines_bin:
        if line == ['__label__']:
            continue
        for b in line:
            byte_arr.append(b & 0xFF)

    try:
        with open(sys.argv[2], 'wb') as fdst:
            fdst.write(byte_arr)
        print(f"[OK] {len(byte_arr)} bytes gravados em '{sys.argv[2]}'")
        print(f"     {len(lines)} linhas  |  {len(names)} labels definidos")
    except IOError as e:
        print(f"[ERRO] Não foi possível gravar: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()