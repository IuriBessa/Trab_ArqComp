; ==============================================================================
; primo_ou_proximo.asm  (= primo_ou_proximo.asm + divmodz nos lacos)
;
;   Igual a versao com roda 6k+/-1, mas usa divmodz1/divmodz2 (dividendo em
;   Z1/Z2) eliminando o z1tox/z2tox antes de cada divmod. Backup:
;   primo_ou_proximo.asm continua intacto.
;
;   word 1 = SAIDA | word 2 = ENTRADA N
; ============================================================================

        goto main
        wb 0
word1:  ww 0
word2:  ww 0
word3:  ww 0

main:   ldx  word2
        xtoz1
        z1tox
        ldyi 2
        subxy
        jz   isP
        jn   do_next
        z1tox
        jodd nsetd
        goto do_next
nsetd:  ldyi 3
        divmodz1
        jltxy isP
        jzh  do_next
        ldyi 5
nw:     divmodz1
        jltxy isP
        jzh  do_next
        incy
        incy
        divmodz1
        jltxy isP
        jzh  do_next
        incy
        incy
        incy
        incy
        goto nw

; ===== N PRIMO : aliquot(N+1), passo 1 =====
isP:    ldx  word2
        incx
        xtoz2            ; M = N+1
        ldz1i 1
        ldyi 2
apl:    divmodz2
        jltxy aend
        jzh  adiv
        incy
        goto apl
adiv:   xtoh
        xtoy
        addz1x
        htox
        subxy
        jz   askip
        htox
        addz1x
askip:  incy
        goto apl
aend:   z1tox
        mov  word1
        halt

; ===== N NAO PRIMO : proximo primo (roda 6k+/-1) =====
do_next:
        ldx  word2
        xtoz1            ; c = N
nploop: incz1
        z1tox
        ldyi 2
        subxy
        jz   npf
        jn   nploop
        z1tox
        jodd npodd
        goto nploop
npodd:  ldyi 3
        divmodz1
        jltxy npf
        jzh  nploop
        ldyi 5
npw:    divmodz1
        jltxy npf
        jzh  nploop
        incy
        incy
        divmodz1
        jltxy npf
        jzh  nploop
        incy
        incy
        incy
        incy
        goto npw
npf:    z1tox
        mov  word1
        halt
