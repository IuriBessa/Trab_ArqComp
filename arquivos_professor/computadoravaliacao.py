import memory
import sys
import clock
import ufc2x as cpu
import disk

#LÃª binÃ¡rio do programa no disco e coloca na memÃ³ria
disk.read(str(sys.argv[1]))

#Inicializa valores de teste na memÃ³ria
if len(sys.argv) > 2: 
    input1 = int(sys.argv[2]) & 0xFFFFFFFF;
    memory.write_word(2, input1);
if len(sys.argv) == 4: 
    input2 = int(sys.argv[3]) & 0xFFFFFFFF;
    memory.write_word(3, input2);
memory.write_word(1, 0);

#Realiza a computaÃ§Ã£o (liga processador)
ticks = clock.start([cpu])

#Exibe resultado
print(memory.read_word(1),";",ticks)