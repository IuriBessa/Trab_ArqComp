        goto    inicio          ; pula as words de dados
        wb      0               ; padding (byte 3) para alinhar saida em word 1
saida:  ww      0               ; word 1: resultado
op1:    ww      0               ; word 2: operando 1 (multiplicando)
op2:    ww      0               ; word 3: operando 2 (multiplicador)
inicio: clrx                    ; X = 0 (acumulador resultado)
        ldy     op2             ; Y = op2 (contador)
        mov     saida           ; saida = 0
loop:   jzy     fim             ; se Y==0, termina
        add     op1             ; X += op1
        mov     saida           ; saida = X
        decy                    ; Y--
        goto    loop
fim:    halt
