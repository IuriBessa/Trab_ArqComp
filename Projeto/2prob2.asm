; ==============================================================================
; primo_ou_proximo.asm
;
;   Recebe N (word 2) e escreve em word 1:
;     - se N for PRIMO     : soma dos divisores proprios de (N+1)
;                            ex.: 17 primo -> divisores de 18: 1,2,3,6,9 -> 21
;     - se N NAO for primo : o proximo primo (menor primo > N)
;                            ex.: 14 -> 17
;
; Layout de memoria (o assembler insere o byte 0 = 0 automaticamente):
;   word 1 (bytes  4..7)  -> SAIDA
;   word 2 (bytes  8..11) -> ENTRADA N
;   word 3 (bytes 12..15) -> (nao usado)
;   word 4 (bytes 16..19) -> curM  (numero em teste / em soma)
;   word 5 (bytes 20..23) -> quot  (quociente corrente)
;
; Registradores:
;   Z1 = acumulador da soma (aliquot)
;   Z2 = d (candidato a divisor)
;   X/Y/H = temporarios (H = resto do divmod)
;
; Tudo O(sqrt) e sem lacos infinitos. O limite de cada laco usa o quociente
; (d > V/d) em vez de d*d, evitando overflow de 32 bits.
; ==============================================================================

        goto main         ; bytes 1-2
        wb 0              ; byte 3
word1:  ww 0              ; word 1  SAIDA
word2:  ww 0              ; word 2  ENTRADA N
word3:  ww 0              ; word 3  (livre)
curM:   ww 0              ; word 4  scratch
quot:   ww 0              ; word 5  scratch

; ============================================================================
; Decide: N e primo?
; ============================================================================
main:   ldx  word2
        mov  curM        ; curM = N
        decx
        jle  do_next     ; N <= 1 -> nao primo -> proximo primo
        ldx  curM
        ldyi 2
        subxy
        jz   is_prime    ; N == 2 -> primo
        ldx  curM
        ldyi 2
        modxyh
        jz   do_next     ; N par (>2) -> nao primo
        ldz2i 3
ntl:    ldx  curM
        z2toy
        divmod           ; H = N%d , X = N/d
        mov  quot
        ldx  quot
        z2toy
        subxy
        jn   is_prime    ; d > N/d -> primo
        jzh  do_next     ; N%d == 0 -> composto
        incz2
        incz2
        goto ntl

; ============================================================================
; N PRIMO : soma dos divisores proprios de (N+1)
; ============================================================================
is_prime:
        ldx  word2
        incx
        mov  curM        ; curM = N+1
        ldz1i 1          ; soma = 1 (1 divide; o proprio M e excluido)
        ldz2i 2          ; d = 2 (M pode ser par -> passo de 1)
apl:    ldx  curM
        z2toy
        divmod           ; H = M%d , X = M/d
        mov  quot
        ldx  quot
        z2toy
        subxy
        jn   aend        ; d > M/d -> fim
        jzh  adiv        ; M%d == 0 -> d divide M
        incz2
        goto apl
adiv:   z2tox
        addxz1
        xtoz1            ; soma += d
        ldx  quot
        z2toy
        subxy
        jz   askip       ; d == M/d (quadrado perfeito) -> nao soma o par
        ldx  quot
        addxz1
        xtoz1            ; soma += M/d (divisor complementar)
askip:  incz2
        goto apl
aend:   z1tox
        mov  word1
        halt

; ============================================================================
; N NAO PRIMO : proximo primo (menor primo > N)
; ============================================================================
do_next:
        ldx  word2
        mov  curM        ; curM = N
nploop: ldx  curM
        incx
        mov  curM        ; curM = curM + 1  (candidato)
        ldx  curM
        decx
        jle  nploop      ; <= 1 nao e primo
        ldx  curM
        ldyi 2
        subxy
        jz   npfound     ; == 2 primo
        ldx  curM
        ldyi 2
        modxyh
        jz   nploop      ; par -> proximo candidato
        ldz2i 3
nptl:   ldx  curM
        z2toy
        divmod
        mov  quot
        ldx  quot
        z2toy
        subxy
        jn   npfound     ; d > c/d -> c e primo
        jzh  nploop      ; c%d == 0 -> composto, proximo candidato
        incz2
        incz2
        goto nptl
npfound:
        ldx  curM
        mov  word1
        halt
