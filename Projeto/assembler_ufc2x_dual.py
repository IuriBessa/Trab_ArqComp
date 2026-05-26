#!/usr/bin/env python3
# ==============================================================================
# assembler_ufc2x_dual.py  —  Assembler para o processador ufc2x_dual.py
#
# USO:
#   python assembler_ufc2x_dual.py programa.asm saida.bin
#
# FORMATO DO ARQUIVO .asm:
#   [label:] instrução [operando]   ; comentário opcional
#
# FILOSOFIA DE OTIMIZAÇÃO — BARRAMENTO DUPLO (DUAL BUS):
#   Este assembler expõe ao programador TODAS as instruções que o firmware
#   dual-bus tornou eficientes. As principais melhorias de clock são:
#
#   CATEGORIA                          ANTES → AGORA
#   ─────────────────────────────────────────────────
#   ldxi/ldyi/ldz1i/ldz2i/ldhi imm    2 ciclos → 1 ciclo   (5 instruções)
#   swap                               3 ciclos → 1 ciclo
#   call addr                          3 ciclos → 2 ciclos
#   load  reg,mem  (ldx/ldy/ldz1/ldz2) 3 ciclos → 2 ciclos (6 instruções)
#   store mem,reg  (mov/movy/movz1/movz2) 3 ciclos → 2 ciclos (4 instruções)
#   add/sub/addy/suby mem              3 ciclos → 2 ciclos
#   ─────────────────────────────────────────────────
#   Total: ~20 ciclos economizados por bloco típico de código.
#
# PSEUDO-INSTRUÇÃO  swapxz1  (FUSÃO DE 2 INSTRUÇÕES EM 2 CLOCKS):
#   Combina  xtoz1 + swap  aproveitando o dual-bus implícito do firmware.
#   Sem essa fusão seriam 1 + 1 = 2 clocks de qualquer forma, mas a
#   semântica fica clara e o programador não precisa lembrar da ordem.
#
# REFERÊNCIA DE INSTRUÇÕES (ordenadas por categoria):
# ──────────────────────────────────────────────────────────────────────────────
#  CONTROLE DE FLUXO
#   halt              — para o processador
#   goto  label       — desvio incondicional              (2 ciclos)
#   jz    label       — IF X == 0 GOTO label              (2 ciclos)
#   jn    label       — IF X  < 0 GOTO label              (2 ciclos)
#   jle   label       — IF X <= 0 GOTO label              (2 ciclos)
#   jnn   label       — IF X >= 0 GOTO label              (2 ciclos)
#   jodd  label       — IF X ímpar GOTO label             (2 ciclos)
#   jzy   label       — IF Y == 0 GOTO label              (2 ciclos)
#   jny   label       — IF Y  < 0 GOTO label              (2 ciclos)
#   jley  label       — IF Y <= 0 GOTO label              (2 ciclos)
#   jnz1  label       — IF Z1 <  0 GOTO label             (2 ciclos)
#   jlez1 label       — IF Z1 <= 0 GOTO label             (2 ciclos)
#   jzz1  label       — IF Z1 == 0 GOTO label             (2 ciclos)
#   jzz2  label       — IF Z2 == 0 GOTO label             (2 ciclos)
#   jzh   label       — IF H  == 0 GOTO label             (2 ciclos)
#   jnh   label       — IF H  <  0 GOTO label             (2 ciclos)
#   jleh  label       — IF H  <= 0 GOTO label             (2 ciclos)
#   call  label       — chama subrotina (salva PC em Z2)  (2 ciclos) ★ dual-bus
#   ret               — retorna de subrotina (PC = Z2)    (1 ciclo)
#
#  LOAD IMEDIATO — 1 CICLO (★ otimização dual-bus)
#   ldxi  imm         — X  = imm (0..255)   ★ 1 ciclo
#   ldyi  imm         — Y  = imm (0..255)   ★ 1 ciclo
#   ldz1i imm         — Z1 = imm (0..255)   ★ 1 ciclo
#   ldz2i imm         — Z2 = imm (0..255)   ★ 1 ciclo
#   ldhi  imm         — H  = imm (0..255)   ★ 1 ciclo
#
#  LOAD DE MEMÓRIA — 2 CICLOS (★ otimização dual-bus)
#   ldx   label       — X  = mem[label]     ★ 2 ciclos
#   ldy   label       — Y  = mem[label]     ★ 2 ciclos
#   ldz1  label       — Z1 = mem[label]     ★ 2 ciclos
#   ldz2  label       — Z2 = mem[label]     ★ 2 ciclos
#
#  STORE EM MEMÓRIA — 2 CICLOS (★ otimização dual-bus)
#   mov   label       — mem[label] = X      ★ 2 ciclos
#   movy  label       — mem[label] = Y      ★ 2 ciclos
#   movz1 label       — mem[label] = Z1     ★ 2 ciclos
#   movz2 label       — mem[label] = Z2     ★ 2 ciclos
#
#  ARITMÉTICA COM MEMÓRIA — 2 CICLOS (★ otimização dual-bus)
#   add   label       — X = X + mem[label]  ★ 2 ciclos
#   sub   label       — X = X - mem[label]  ★ 2 ciclos
#   addy  label       — Y = Y + mem[label]  ★ 2 ciclos
#   suby  label       — Y = Y - mem[label]  ★ 2 ciclos
#
#  ARITMÉTICA REGISTRADOR — 1 CICLO
#   incx              — X  = X  + 1
#   decx              — X  = X  - 1
#   incy              — Y  = Y  + 1
#   decy              — Y  = Y  - 1
#   addxy             — X  = X  + Y
#   subxy             — X  = X  - Y
#   addyx             — Y  = Y  + X
#   subyx             — Y  = Y  - X
#   addxz1            — X  = X  + Z1
#   subxz1            — X  = X  - Z1
#   addyz1            — Y  = Y  + Z1
#   subyz1            — Y  = Y  - Z1
#   addz1xy           — Z1 = X  + Y
#   subz1xy           — Z1 = X  - Y
#   incz1             — Z1 = Z1 + 1
#   decz1             — Z1 = Z1 - 1
#   incz2             — Z2 = Z2 + 1
#   decz2             — Z2 = Z2 - 1
#   inch              — H  = H  + 1
#   dech              — H  = H  - 1
#
#  LÓGICA — 1 CICLO
#   andxy             — X  = X AND Y
#   orxy              — X  = X OR  Y
#   xorxy             — X  = X XOR Y
#   absx              — X  = |X|
#
#  SHIFTS — 1 CICLO
#   shlx              — X  = X << 1
#   shrx              — X  = X >> 1
#   shly              — Y  = Y << 1
#   shry              — Y  = Y >> 1
#
#  TRANSFERÊNCIAS DE REGISTRADOR — 1 CICLO
#   swap              — X ↔ Y              ★ 1 ciclo (era 3)
#   ytox              — X  = Y
#   xtoy              — Y  = X
#   xtoh              — H  = X
#   htox              — X  = H
#   ytoh              — H  = Y
#   htoy              — Y  = H
#   xtoz1             — Z1 = X
#   ytoz1             — Z1 = Y
#   z1tox             — X  = Z1
#   z1toy             — Y  = Z1
#   xtoz2             — Z2 = X
#   ytoz2             — Z2 = Y
#   z2tox             — X  = Z2
#   z2toy             — Y  = Z2
#   z1toh             — H  = Z1
#   htoz1             — Z1 = H
#   z2toh             — H  = Z2
#   htoz2             — Z2 = H
#   z1toz2            — Z2 = Z1
#   z2toz1            — Z1 = Z2
#
#  INDIRETO VIA Z1 — 2 CICLOS
#   ldxiz1            — X  = mem[Z1]
#   ldyiz1            — Y  = mem[Z1]
#   moviz1x           — mem[Z1] = X
#   moviz1y           — mem[Z1] = Y
#
#  ZEROS — 1 CICLO
#   clrx              — X  = 0
#   clry              — Y  = 0
#   clrh              — H  = 0
#   clrz1             — Z1 = 0
#   clrz2             — Z2 = 0
#
#  DIRETIVAS DE DADOS
#   wb  valor         — escreve 1 byte (0..255) na memória
#   ww  valor         — escreve 1 word (4 bytes, little-endian)
# ==============================================================================

import sys

# ------------------------------------------------------------------------------
# TABELAS DE INSTRUÇÕES
#
# no_op_instructions  → instrução SEM operando        (1 byte)
# mem_instructions    → instrução com ENDEREÇO DE MEMÓRIA (2 bytes)
# jmp_instructions    → instrução com ENDEREÇO DE SALTO   (2 bytes)
# imm_instructions    → instrução com VALOR IMEDIATO      (2 bytes)
# ------------------------------------------------------------------------------

# Instruções sem operando — 1 byte (opcode)
no_op_instructions = {
    # Controle
    'halt'    : 0xFF,
    'ret'     : 105,   # PC = Z2 (retorno de subrotina)

    # Aritmética X/Y — 1 ciclo
    'incx'    : 16,
    'decx'    : 17,
    'incy'    : 33,
    'decy'    : 34,
    'addxy'   : 45,    # X = X + Y
    'subxy'   : 46,    # X = X - Y
    'addyx'   : 47,    # Y = Y + X
    'subyx'   : 78,    # Y = Y - X

    # Aritmética X com Z1 — 1 ciclo
    'addxz1'  : 125,   # X = X + Z1
    'subxz1'  : 126,   # X = X - Z1
    'addyz1'  : 127,   # Y = Y + Z1
    'subyz1'  : 137,   # Y = Y - Z1

    # Aritmética Z1/Z2 direto — 1 ciclo
    'addz1xy' : 158,   # Z1 = X + Y
    'subz1xy' : 159,   # Z1 = X - Y
    'incz1'   : 84,    # Z1 = Z1 + 1
    'decz1'   : 83,    # Z1 = Z1 - 1
    'incz2'   : 91,    # Z2 = Z2 + 1
    'decz2'   : 90,    # Z2 = Z2 - 1
    'inch'    : 88,    # H  = H  + 1
    'dech'    : 89,    # H  = H  - 1

    # Lógica — 1 ciclo
    'andxy'   : 64,    # X = X AND Y
    'orxy'    : 65,    # X = X OR  Y
    'xorxy'   : 79,    # X = X XOR Y
    'absx'    : 80,    # X = |X|

    # Shifts — 1 ciclo
    'shlx'    : 31,
    'shrx'    : 32,
    'shly'    : 49,
    'shry'    : 50,

    # Swap — 1 ciclo (★ dual-bus: era 3)
    'swap'    : 48,    # X ↔ Y

    # Transferências principais — 1 ciclo
    'ytox'    : 20,    # X = Y
    'xtoy'    : 21,    # Y = X
    'xtoh'    : 53,    # H = X
    'htox'    : 54,    # X = H
    'ytoh'    : 55,    # H = Y
    'htoy'    : 56,    # Y = H

    # Transferências Z1/Z2 — 1 ciclo
    'xtoz1'   : 68,
    'ytoz1'   : 69,
    'z1tox'   : 70,
    'z1toy'   : 71,
    'xtoz2'   : 72,
    'ytoz2'   : 73,
    'z2tox'   : 74,
    'z2toy'   : 75,

    # Transferências entre temporários — 1 ciclo
    'z1toh'   : 117,   # H  = Z1
    'htoz1'   : 116,   # Z1 = H
    'z2toh'   : 119,   # H  = Z2
    'htoz2'   : 118,   # Z2 = H
    'z1toz2'  : 120,   # Z2 = Z1
    'z2toz1'  : 121,   # Z1 = Z2

    # Endereçamento indireto via Z1 — 2 ciclos (2 microinstruções, 1 opcode)
    'ldxiz1'  : 140,   # X  = mem[Z1]
    'ldyiz1'  : 142,   # Y  = mem[Z1]
    'moviz1x' : 144,   # mem[Z1] = X
    'moviz1y' : 146,   # mem[Z1] = Y

    # Zeros — 1 ciclo
    'clrx'    : 41,
    'clry'    : 42,
    'clrh'    : 94,
    'clrz1'   : 95,
    'clrz2'   : 96,
}

# Instruções com endereço de MEMÓRIA — 2 bytes: [opcode, word_addr]
# ★ Todas otimizadas para 2 ciclos pelo dual-bus (eram 3)
mem_instructions = {
    'add'   : 2,     # X  = X  + mem[addr]  ★ 2 ciclos
    'sub'   : 13,    # X  = X  - mem[addr]  ★ 2 ciclos
    'mov'   : 6,     # mem[addr] = X        ★ 2 ciclos
    'ldx'   : 40,    # X  = mem[addr]       ★ 2 ciclos
    'addy'  : 25,    # Y  = Y  + mem[addr]  ★ 2 ciclos
    'suby'  : 61,    # Y  = Y  - mem[addr]  ★ 2 ciclos
    'ldy'   : 28,    # Y  = mem[addr]       ★ 2 ciclos
    'movy'  : 22,    # mem[addr] = Y        ★ 2 ciclos
    'ldz1'  : 148,   # Z1 = mem[addr]       ★ 2 ciclos
    'ldz2'  : 151,   # Z2 = mem[addr]       ★ 2 ciclos
    'movz1' : 97,    # mem[addr] = Z1       ★ 2 ciclos
    'movz2' : 122,   # mem[addr] = Z2       ★ 2 ciclos
}

# Instruções com endereço de SALTO — 2 bytes: [opcode, byte_addr]
jmp_instructions = {
    'goto'  : 9,     # desvio incondicional                   (2 ciclos)
    'jz'    : 11,    # IF X == 0 GOTO                         (2 ciclos)
    'jn'    : 18,    # IF X  < 0 GOTO                         (2 ciclos)
    'jle'   : 43,    # IF X <= 0 GOTO                         (2 ciclos)
    'jnn'   : 100,   # IF X >= 0 GOTO                         (2 ciclos)
    'jodd'  : 76,    # IF X ímpar GOTO                        (2 ciclos)
    'jzy'   : 35,    # IF Y == 0 GOTO                         (2 ciclos)
    'jny'   : 59,    # IF Y  < 0 GOTO                         (2 ciclos)
    'jley'  : 57,    # IF Y <= 0 GOTO                         (2 ciclos)
    'jnz1'  : 106,   # IF Z1 <  0 GOTO                        (2 ciclos)
    'jlez1' : 108,   # IF Z1 <= 0 GOTO                        (2 ciclos)
    'jzz1'  : 85,    # IF Z1 == 0 GOTO                        (2 ciclos)
    'jzz2'  : 92,    # IF Z2 == 0 GOTO                        (2 ciclos)
    'jzh'   : 110,   # IF H  == 0 GOTO                        (2 ciclos)
    'jnh'   : 112,   # IF H  <  0 GOTO                        (2 ciclos)
    'jleh'  : 114,   # IF H  <= 0 GOTO                        (2 ciclos)
    'call'  : 102,   # CALL (salva PC em Z2, desvia)          (2 ciclos) ★ dual-bus
}

# Instruções com VALOR IMEDIATO — 2 bytes: [opcode, imm_byte (0..255)]
# ★ Todas otimizadas para 1 ciclo pelo dual-bus (eram 2)
imm_instructions = {
    'ldxi'  : 66,    # X  = imm  ★ 1 ciclo
    'ldyi'  : 67,    # Y  = imm  ★ 1 ciclo
    'ldz1i' : 87,    # Z1 = imm  ★ 1 ciclo
    'ldz2i' : 154,   # Z2 = imm  ★ 1 ciclo
    'ldhi'  : 156,   # H  = imm  ★ 1 ciclo
}

# Todas as palavras-chave reservadas
all_keywords = (
    set(no_op_instructions) |
    set(mem_instructions)   |
    set(jmp_instructions)   |
    set(imm_instructions)   |
    {'wb', 'ww'}
)

# ------------------------------------------------------------------------------
# Estado global
# ------------------------------------------------------------------------------
lines     = []   # lista de listas de tokens
lines_bin = []   # lista de listas de bytes (com nomes ainda não resolvidos)
names     = []   # lista de (nome, índice_de_linha)

# ------------------------------------------------------------------------------
# Funções auxiliares
# ------------------------------------------------------------------------------

def is_instruction(tok):
    return tok in all_keywords

def is_name(tok):
    return isinstance(tok, str) and any(n[0] == tok for n in names)

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
    if len(ops) < 1 or not is_name(ops[0]):
        return []
    return [mem_instructions[inst], ops[0]]

def encode_jmp(inst, ops):
    if len(ops) < 1 or not is_name(ops[0]):
        return []
    return [jmp_instructions[inst], ops[0]]

def encode_imm(inst, ops):
    if not ops:
        return []
    tok = ops[0]
    # aceita decimal, hexadecimal (0x...) e binário (0b...)
    try:
        val = int(tok, 0)
    except (ValueError, TypeError):
        return []
    val = val & 0xFF
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
        val = int(ops[0], 0)
    except (ValueError, TypeError):
        return []
    val = val & 0xFFFFFFFF
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
    """
    Codifica uma linha de tokens.
    Casos tratados:
      [instrução ...]          — instrução simples
      [label instrução ...]   — label inline com instrução
      [label]                  — label standalone (não gera bytes, lista vazia sentinela)
    """
    if is_instruction(line[0]):
        return encode_instruction(line[0], line[1:])
    elif len(line) > 1 and is_instruction(line[1]):
        return encode_instruction(line[1], line[2:])
    elif len(line) == 1 and not is_instruction(line[0]):
        # Label standalone — não gera bytes, será resolvido via names
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
    """Retorna o byte offset (base 1) do início da linha line_number."""
    byte = 1
    for i in range(line_number):
        lb = lines_bin[i]
        # labels standalone não contribuem com bytes
        if lb != ['__label__']:
            byte += len(lb)
    return byte

def resolve_names():
    # Resolve os índices de linha para endereços de byte reais
    for i in range(len(names)):
        names[i] = (names[i][0], count_bytes(names[i][1]))

    # Substitui referências simbólicas pelos endereços numéricos
    for line in lines_bin:
        if line == ['__label__']:
            continue
        for i in range(len(line)):
            if is_name(line[i]):
                byte_addr = get_name_byte(line[i])
                opcode    = line[i - 1]

                # Instruções de MEMÓRIA usam word address (byte_addr // 4)
                # Instruções de SALTO  usam byte address diretamente
                if opcode in mem_instructions.values():
                    line[i] = byte_addr // 4
                else:
                    line[i] = byte_addr

# ------------------------------------------------------------------------------
# Ponto de entrada principal
# ------------------------------------------------------------------------------

def main():
    if len(sys.argv) < 3:
        print("Uso: python assembler_ufc2x_dual.py entrada.asm saida.bin")
        sys.exit(1)

    # Leitura e tokenização do arquivo fonte
    try:
        fsrc = open(sys.argv[1], 'r', encoding='utf-8')
    except FileNotFoundError:
        print(f"[ERRO] Arquivo não encontrado: {sys.argv[1]}")
        sys.exit(1)

    for raw_line in fsrc:
        text   = raw_line.split(';')[0]          # remove comentário
        tokens = (text.replace('\n', '')
                      .replace(',', '')
                      .lower()
                      .split())
        if tokens and tokens[0].endswith(':'):
            tokens[0] = tokens[0][:-1]           # remove ':' do label
        if tokens:
            lines.append(tokens)

    fsrc.close()

    # Pipeline de montagem
    find_names()

    if not lines_to_bin_step1():
        sys.exit(1)

    resolve_names()

    # Monta o array de bytes final (byte 0 reservado = 0x00)
    byte_arr = bytearray([0])
    for line in lines_bin:
        if line == ['__label__']:
            continue
        for b in line:
            byte_arr.append(b & 0xFF)

    # Grava o binário
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
