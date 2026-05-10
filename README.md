# Trab_ArqComp

## Possíveis melhorias
- Receber o valor do barramento A em vez de H, possibilidade de otimização.
- Se pedir multiplicação, implementar uma ula p multiplicação (faz no logisim, ou com portas logícas na ula mostra e usa a normal do python)
- Olhar slides cap 4 tanenbaum pra entender melhor processador
- Não botar nada no mdr Endereço
- MAR - só preencher outros bits dele, preencher 32 / Leitura não de MBR e sim MER alterando no firmware/ Só tá lendo no máx. 1KB, tá limitando o acesso de memória
- Ao jogar mdr p mar tem que ser read e não fetch.
- Olhar se não faz fetch não incrementa pc, se não incrementa pc lê a mesma instrção, tem que dar 4 fetchs antes de fazer o read (é necessário entender como a arquitetura está funcionando).
- MAR de 32 bits pode ser bom (aumentar memória se conseguir fazer isso).
- Nossa ISA só tem seis instruções / implementar mais a multiplicação!!!
- Ver se tem ideias pra melhorar essa soma / olhar o circuito logisim pra tentar diminuir os clocks.
- Colocar dois barramentos na ULA.

## Descrição Geral
### **O trabalho deverá ser submetido até o dia 04/06/2026.**
Você deverá projetar uma microarquitetura, implementar o respectivo emulador e permitir que sejam executados programas quaisquer para ela escritos. Deverá, portanto, projetar um conjunto de instruções para serem executadas pela sua microarquitetura (definindo uma macroarquitetura - ISA), implementando-o através do microprograma de controle. Por fim, você deve implementar um montador (assembler) para uma linguagem de montagem (assembly) que traduza para a linguagem de máquina da macroarquitetura criada.

## Parte 1 - Emulador
**Você pode tomar como base o emulador escrito nas aulas ou construir o seu a partir
do zero. É possível, assim:**

- Criar uma nova microarquitetura
- Melhorar a microarquitetura proposta em sala
- Manter a microarquitetura inalterada
- Criar um novo microprograma de controle, disponibilizando um novo conjunto de instruções (nova macroarquitetura – nova ISA)
- Melhorar o microprograma, tanto tornando mais eficientes as implementações das instruções já apresentadas, quanto adicionando novas instruções ao conjunto
- Manter o microprograma inalterado

O seu emulador deve poder receber arquivos binários com programas em linguagem de máquina da sua arquitetura e executá-los.

## Parte 2 - Assembler
O seu assembler deve montar programas escritos no assembly que você projetar na linguagem de máquina da sua arquitetura. O assembly deve cobrir todo o conjunto de instruções que você tiver criado em sua arquitetura, bem como disponibilizar pseudoinstruções para escrita direta de bytes ou words no processo de montagem. Um assembler para a arquitetura apresentada em sala de aula foi disponibilizado e, portanto, é possível:

- Utilizar o mesmo assembler sem qualquer alteração caso você não tenha construído um processador com um conjunto de instruções diferente;
- Alterar o assembler disponibilizado para dar conta do seu novo conjunto de instruções (solução especialmente útil se você apenas aumentou o conjunto de instruções, mantendo as que já existiam na arquitetura apresentada em aula, ou se quer mudar apenas alguns detalhes de sintaxe, como alterar os mnemônicos);
- Construir um novo assembler do zero (melhor caminho especialmente no caso no qual você queira disponibilizar uma linguagem assembly com muitas diferenças sintáticas em relação à apresentada em aula, ou se a linguagem de máquina da sua arquitetura também for muito diferente).

Sinta-se livre para propôr qualquer estrutura sintática que considerar mais adequada para uma linguagem assembly (palavras utilizadas, mnemônicos, ordens, símbolos, etc), bem como disponibilizar recursos extras, como macros (não contará para a avaliação, mas pode facilitar na parte 3).

## Parte 3 - Programando para sua máquina

Uma semana antes da entrega do trabalho serão disponibilizados quatro problemas para os quais você deve escrever programas que computem suas soluções, executando tais programas em seu emulador. Você deverá, portanto, escrever esses programas com sua linguagem assembly, usar o seu assembler para gerar o código binário e, finalmente, colocar para rodar no emulador.

### Organização do envio

1. O seu trabalho deverá ser enviado por um sistema online a ser disponibilizado até o dia da entrega;
2. Você deverá enviar sete arquivos:
- Microarquitetura (o .py do processador)
- Memória (o .py da memória)
- Assembler: (o .py do assembler)
- Código assembly do problema 1 (o .asm do problema 1)
- Código assembly do problema 2 (o .asm do problema 2)
- Código assembly do problema 3 (o .asm do problema 3)
- Código assembly do problema 4 (o .asm do problema 4)
3. O sistema de entrega utilizará o seu assembler para gerar os binários e rodará cada um dos programas com o mesmo “computador” disponibilizado no SIGAA, substituindo o processador e a memória originais por aqueles que você enviou. **_Atenção para os arquivos enviados: é de sua total responsabilidade enviar os arquivos corretos nos campos corretos do formulário do sistema. Arquivos trocados inviabilizarão a execução ou, no caso dos .asm, darão retornos errados._**
4. Em todos os seus códigos assembly, você deverá reservar as words 1, 2 e 3, respectivamente, para: a resposta (saída), o operando 1 e o operando 2 (entradas) do problema. Quando o problema exigir apenas uma entrada, não é necessário reservar a word 3. Isso se deve ao fato de que o computador de avaliação escreverá diretamente na memória, nas words 2 e 3, os valores de entrada para teste dos programas e, da mesma forma, lerá o conteúdo da word 1 ao final da execução como sendo a saída do programa.
5. O sistema exibirá para você, após a execução, a informação sobre sucesso ou não (se o resultado computado foi correto), a resposta calculada pelo seu computador e o número de ciclos de clock que o seu computador utilizou em cada problema. Além disso, mostrará também o número médio de ciclos de clock utilizados.
6. Para programas cujo tempo de execução exija mais de 30 segundos, será considerado tempo infinito e o respectivo problema será dado como não solucionado. Respostas erradas, mesmo que dentro do tempo de execução, também serão consideradas como problemas não solucionados.
7. Enquanto o sistema estiver disponível, você poderá reenviar o seu trabalho. Valerá sempre o resultado do último envio.
8. A nota será calculada e disponibilizada apenas após o fechamento do sistema de envios.
