        goto main
        wb 0

res     ww 50
v1      ww 0
v2      ww 3

main    add x, v1
        jz x, pulo
ret     mov x, res
        halt
pulo    add x, v2
        goto ret
