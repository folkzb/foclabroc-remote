# Multiplayer VPad / VPad para dois jogadores

## Português

Instale o novo APK **nos dois celulares**. Versões anteriores usam a mesma
identidade de controle e não participam da reserva de posições.

1. Conecte os dois celulares ao mesmo Batocera por SSH.
2. No primeiro celular, conecte o VPad. Ele exibirá **P1**.
3. No segundo, conecte o VPad. Ele exibirá **P2**.
4. Nas configurações de controles do Batocera, mapeie os dispositivos
   **Foclabroc-VPad P1** e **Foclabroc-VPad P2**, incluindo ambos os analógicos.
5. Atribua esses dispositivos aos jogadores 1 e 2 no Batocera.
6. Abra um jogo com suporte a dois jogadores e use a tela inteira nos celulares.

A posição mostrada no aplicativo identifica o dispositivo virtual. A atribuição
ao jogador dentro do jogo continua sendo feita pelo Batocera/emulador.
Conecte os controles antes de iniciar jogos que não detectam controles novos
durante a execução.

Há quatro posições disponíveis. Cada conexão reserva a primeira posição livre;
nenhuma conexão assume uma posição já ocupada. Desconectar um celular não libera
os botões, altera o dispositivo nem encerra a sessão do outro.

Sem comunicação, os comandos voltam ao neutro após aproximadamente 2 segundos.
Após aproximadamente 10 segundos, a sessão abandonada é encerrada e sua posição
é liberada. Ao voltar ao aplicativo, reconecte o VPad se necessário. Depois de
todos desconectarem, conecte primeiro o celular que deve receber P1.

## English

Install the new APK on **both phones**, connect both to the same Batocera over
SSH, and connect each VPad. The first free slot is reserved automatically:
**Foclabroc-VPad P1**, then **Foclabroc-VPad P2** (up to four active controllers).

Map each named controller in Batocera's controller settings, including both
analog sticks, and assign them to player 1 and player 2 before launching a
multiplayer game. The app's slot label identifies the virtual device; Batocera
and the emulator still determine the in-game player assignment.

Inputs and devices are independent. Disconnecting one phone does not stop the
other controller. Without heartbeats, held inputs reset after about 2 seconds;
after about 10 seconds the abandoned device closes and its slot becomes free.
Reconnect the VPad when returning to the app if needed.
