        goto    inicio
        wb      0
saida:  ww      0               ; word 1 -> resultado F(n)
op1:    ww      0               ; word 2 -> entrada n
temp:   ww      0               ; word 3 -> nao usado

inicio: ldx     op1             ; X = n
        jz      caso_zero       ; n == 0  ->  F(0) = 0

        decx                    ; X = n-1
        jz      caso_um         ; n == 1  ->  F(1) = 1

        decx                    ; X = n-2
        jz      caso_dois       ; n == 2  ->  F(2) = 1

        ; n >= 3:
        ; Inicializa janela em Z1=F(1)=1, Z2=F(2)=1
        ; (uma iteracao ja foi "consumida" ao verificar n>=3)
        ldxi    1
        xtoz1                   ; Z1 = 1 = F(1)
        xtoz2                   ; Z2 = 1 = F(2)

        ; contador = n-2 (ja calculado em X = n-2, nao zerado)
        ; Precisa de X = n-2 novamente; X ja tem n-2 de cima, mas
        ; ldxi 1 sobrescreveu X. Recarrega.
        ldx     op1             ; X = n
        decx                    ; X = n-1
        decx                    ; X = n-2
        xtoh                    ; H = n-2  (contador sem RAM)

loop_h: htox                    ; X = H (contador)
        jz      escreve         ; H == 0  ->  Z2 e F(n)

        ; decrementa H sem memoria
        decx                    ; X = H-1
        xtoh                    ; H = H-1

        ; proximo Fibonacci: precisa X=F(k-1) e Y=F(k) para usar addxy
        z2toy                   ; Y = Z2 = F(k)      (salva F(k) em Y)
        z1tox                   ; X = Z1 = F(k-1)
        addxy                   ; X = F(k-1) + F(k) = F(k+1)

        ; desliza janela
        ytoz1                   ; Z1 = Y = F(k)
        xtoz2                   ; Z2 = X = F(k+1)

        goto    loop_h

escreve: z2tox                  ; X = Z2 = F(n)
        mov     saida           ; mem[saida] = F(n)
        halt

caso_zero: clrx                 ; X = 0 = F(0)
        mov     saida
        halt

caso_um: ldxi   1               ; X = 1 = F(1)
        mov     saida
        halt

caso_dois: ldxi 1               ; X = 1 = F(2)
        mov     saida
        halt
