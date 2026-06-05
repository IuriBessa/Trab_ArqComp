; ==============================================================================
; fatores_ou_divisores.asm  (= fatores_ou_divisores.asm + divmodz2 nos lacos)
;
;   Igual a versao com roda 6k+/-1, mas usa 'divmodz2' (divmod com dividendo em
;   Z2) eliminando o 'z2tox' antes de cada divmod -> 1 instrucao a menos por
;   iteracao. Backup: fatores_ou_divisores.asm continua intacto.
;
;   word 1 = SAIDA | word 2 = ENTRADA N
; ============================================================================

        goto main
        wb 0
word1:  ww 0
word2:  ww 0
word3:  ww 0

main:   ldx  word2
        jz   out0
        jodd odd

; ===== N PAR : fatores primos distintos (roda 6k+/-1) =====
even:   xtoz2            ; curn = N
        clrz1
        ldxi 2
        addz1x           ; soma += 2
        ldyi 2
e2:     divmodz2         ; X=curn/2 , H=curn%2
        jzh  e2d
        goto e3
e2d:    xtoz2            ; curn /= 2
        goto e2

e3:     ldyi 3
        divmodz2
        jltxy eend
        jzh  ef3
        goto ew5
ef3:    xtoz2            ; curn /= 3
        xtoy
        addz1x           ; soma += 3
e3r:    divmodz2
        jzh  e3d
        goto ew5
e3d:    xtoz2
        goto e3r

ew5:    ldyi 5
ewl:    divmodz2         ; testa 6k-1
        jltxy eend
        jzh  efa
        goto enb
efa:    xtoz2
        xtoy
        addz1x
efar:   divmodz2
        jzh  efad
        goto enb
efad:   xtoz2
        goto efar
enb:    incy
        incy
        divmodz2         ; testa 6k+1
        jltxy eend
        jzh  efc
        goto enw
efc:    xtoz2
        xtoy
        addz1x
efcr:   divmodz2
        jzh  efcd
        goto enw
efcd:   xtoz2
        goto efcr
enw:    incy
        incy
        incy
        incy
        goto ewl

eend:   z2tox
        decx
        jle  edone
        z2tox
        addz1x           ; soma += curn (ultimo primo)
edone:  z1tox
        mov  word1
        halt

; ===== N IMPAR : aliquot (passo 2) =====
odd:    decx
        jz   out0
        ldz2 word2       ; Z2 = N
        ldz1i 1
        ldyi 3
ofl:    divmodz2         ; X=N/d , H=N%d
        jltxy oend
        jzh  ofac
        incy
        incy
        goto ofl
ofac:   xtoh
        subxy
        jz   ohalf
        xtoy
        addz1x
        htox
        addz1x
        incy
        incy
        goto ofl
ohalf:  xtoy
        addz1x
        incy
        incy
        goto ofl
oend:   z1tox
        mov  word1
        halt

out0:   clrx
        mov  word1
        halt
