        goto    inicio          ; pula as words de dados
        wb      0               ; padding (byte 3) para alinhar saida em word 1
saida:  ww      0               ; word 1: resultado
op1:    ww      0               ; word 2: multiplicando (m)
op2:    ww      0               ; word 3: multiplicador (r)
inicio: clrx
        xtoz1                   ; Z1 = acc = 0
        ldy     op1             ; Y  = m
        ldx     op2             ; X  = r
loop:   jz      fim             ; r == 0 → fim
        jodd    do_add          ; se r ímpar, acc += m
shift:  shly                    ; m <<= 1
        shrx                    ; r >>= 1
        goto    loop
do_add: xtoh                    ; H = r (salva)
        z1tox                   ; X = acc
        addxy                   ; X = acc + m
        xtoz1                   ; acc = X
        htox                    ; X = r (restaura)
        goto    shift
fim:    z1tox                   ; X = acc
        mov     saida
        halt
