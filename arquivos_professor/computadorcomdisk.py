import memory
import sys
import clock
import ufc2x as cpu
import disk

disk.read(str(sys.argv[1]))

print("Antes: ", memory.read_word(1))
clock.start([cpu])
print("Depois: ", memory.read_word(1))

print(memory.read_word(220))