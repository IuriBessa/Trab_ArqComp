
        goto main       ; pula as words reservadas (bytes 1-2)
        wb 0            ; padding — completa a word 0 (byte 3)

word1:                  ; byte 4  →  word address 1  (SAÍDA)
        ww 0

word2:                  ; byte 8  →  word address 2  (ENTRADA)
        ww 0

; ── Início do programa ───────────────────────────────────────
main:
        ldx  word2      ; X = n  (lê entrada da memória)
        jz   zero_case  ; n == 0  →  fib(0) = 0
        decx            ; X = n - 1
        jz   one_case   ; n == 1  →  fib(1) = 1

        ; Inicializa iteração: a=0 (Y), b=1 (Z1)
        clry            ; Y = 0   [ a = fib(0) ]
        ldz1i 1         ; Z1 = 1  [ b = fib(1) ]

; ── Loop principal: executa (n-1) vezes ──────────────────────
loop:
        z1toh           ; H  = b              (salva b atual)
        addyz1          ; Y  = a + b          (novo b temporário)
        ytoz1           ; Z1 = novo b         (persiste)
        htoy            ; Y  = b antigo = novo a
        decx            ; contador--
        jz   done       ; chegou a zero → resultado em Z1
        goto loop

; ── Escreve resultado e para ─────────────────────────────────
done:
        movz1 word1     ; mem[word1] = Z1 = fib(n)
        halt

; ── Casos base ───────────────────────────────────────────────
zero_case:
        ldxi  0
        mov   word1     ; mem[word1] = 0
        halt

one_case:
        ldxi  1
        mov   word1     ; mem[word1] = 1
        halt