; ==============================================================================
; fatores_ou_divisores.asm
;
;   Recebe N (word 2) e escreve em word 1:
;     - se N par  : soma dos FATORES PRIMOS DISTINTOS de N
;                   ex.: 42 = 2*3*7 -> 2+3+7 = 12
;     - se N impar: soma dos DIVISORES PROPRIOS de N (todos os divisores < N)
;                   ex.: 21 -> 1+3+7 = 11
;
; Layout de memoria (o assembler insere o byte 0 = 0 automaticamente):
;   word 1 (bytes  4..7)  -> SAIDA
;   word 2 (bytes  8..11) -> ENTRADA N
;   word 3 (bytes 12..15) -> (nao usado)
;   word 4 (bytes 16..19) -> curn  (N corrente / scratch)
;   word 5 (bytes 20..23) -> quot  (quociente corrente / scratch)
;
; Registradores:
;   Z1 = acumulador (soma)
;   Z2 = d (candidato a divisor/fator)
;   X/Y/H = temporarios (H recebe o resto do divmod)
;
; Custo O(sqrt(N)) sem lacos infinitos. O limite do laco usa o quociente
; (d > N/d) em vez de d*d, evitando overflow de 32 bits.
; ==============================================================================

        goto main         ; bytes 1-2  (pula a area de dados)
        wb 0              ; byte 3
word1:  ww 0              ; word 1  SAIDA
word2:  ww 0              ; word 2  ENTRADA N
word3:  ww 0              ; word 3  (livre)
curn:   ww 0              ; word 4  scratch
quot:   ww 0              ; word 5  scratch

main:   clrz1            ; soma = 0
        ldx  word2       ; X = N
        jz   output0     ; N == 0 -> saida 0 (evita laco infinito)
        jodd odd         ; N impar -> ramo dos divisores

; ============================================================================
; N PAR : soma dos fatores primos distintos
; ============================================================================
even:   ldx  word2
        mov  curn        ; curn = N

        ; --- remove o fator 2 (N par => 2 divide N) ---
        ldxi 2
        addxz1
        xtoz1            ; soma += 2
rem2:   ldx  curn
        ldyi 2
        divxyh           ; X = curn / 2
        mov  curn
        ldx  curn
        ldyi 2
        modxyh           ; X = curn % 2
        jz   rem2        ; enquanto par, continua dividindo

        ; --- fatores impares d = 3,5,7,... ---
        ldz2i 3
efl:    ldx  curn
        z2toy
        divmod           ; X = curn/d , H = curn%d
        mov  quot
        ldx  quot
        z2toy
        subxy            ; X = quot - d
        jn   eend        ; d > curn/d  =>  d*d > curn  -> fim
        jzh  efac        ; resto == 0  -> d e fator
        incz2
        incz2            ; d += 2
        goto efl

efac:   z2tox
        addxz1
        xtoz1            ; soma += d (primo distinto)
        ldx  quot
        mov  curn        ; curn = curn / d  (primeira divisao ja feita)
erem:   ldx  curn
        z2toy
        modxyh
        jz   ediv        ; ainda divisivel por d? continua dividindo
        incz2
        incz2            ; d += 2
        goto efl
ediv:   ldx  curn
        z2toy
        divxyh
        mov  curn        ; curn /= d
        goto erem

eend:   ldx  curn
        decx
        jle  done_even   ; se curn <= 1, nada a somar
        ldx  curn
        addxz1
        xtoz1            ; soma += curn (ultimo primo restante)
done_even:
        z1tox
        mov  word1
        halt

; ============================================================================
; N IMPAR : soma dos divisores proprios (aliquot)
; ============================================================================
odd:    ldx  word2
        decx
        jz   output0     ; N == 1 -> saida 0
        ldz1i 1          ; soma = 1 (o divisor 1; o complemento N e excluido)
        ldz2i 3          ; d = 3  (N impar nao tem divisores pares)
ofl:    ldx  word2
        z2toy
        divmod           ; X = N/d , H = N%d
        mov  quot
        ldx  quot
        z2toy
        subxy            ; X = quot - d
        jn   oend        ; d > N/d -> fim
        jzh  ofac        ; resto == 0 -> d divide N
        incz2
        incz2            ; d += 2
        goto ofl

ofac:   z2tox
        addxz1
        xtoz1            ; soma += d
        ldx  quot
        z2toy
        subxy            ; quot - d
        jz   onoc        ; se quot == d (quadrado perfeito) nao soma o par
        ldx  quot
        addxz1
        xtoz1            ; soma += quot (= N/d, o divisor complementar)
onoc:   incz2
        incz2            ; d += 2
        goto ofl

oend:   z1tox
        mov  word1
        halt

; ============================================================================
output0:
        clrx
        mov  word1
        halt
