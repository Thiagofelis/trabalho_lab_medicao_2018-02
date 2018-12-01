import serial
from time import time, sleep
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
from math import sqrt

# "macros"
HIGH = True
LOW = False

# OBS: se o buffer tiver dando overflow, mudar para false
graphic_antialias = True

sampling_freq = 2976

##################################
#### INICIO Set Up do Grafico ####
##################################

pg.setConfigOption('background', (248, 248, 248))
pg.setConfigOption('foreground', 'k')

app = QtGui.QApplication([])
win = pg.GraphicsWindow(title="Medicoes")
win.resize(1300,1300)
win.setWindowTitle('Medicoes')

# x das variaveis:

# tensao, corrente, potencia (tempo)
x_t = np.array(range(300)) * 0.336

# tensao e corrente (freq)
x_f = np.array(range(69)) * sampling_freq / 300 # so ate 68, pois as frequencias apos isso estao na banda de rejeicao

# energia
En = np.array([])
x_tE = np.array([])

# grafico da tensao
p0 = win.addPlot(title="Tensao [Tempo]")
p0.showGrid(x=True, y=True)
p0.setYRange(-200, 200)
p0.setLabel('left', "Tensão", units='V')
p0.setLabel('bottom', "Tempo", units='ms')
tensao = p0.plot(pen=(60,110,140), name="Tensao", antialias=graphic_antialias)

# grafico da corrente
p1 = win.addPlot(title="Corrente [Tempo]")
p1.setYRange(-1.5, 1.5)
p1.setLabel('bottom', "Tempo", units='ms')
p1.setLabel('left', "Tensao", units='A')
p1.showGrid(x=True, y=True)
corrente = p1.plot(pen=(150,50,80), name="Corrente", antialias=graphic_antialias)

win.nextRow()

# mostra valores RMS
label_tensaorms = win.addLabel()
label_correnterms = win.addLabel()

win.nextRow()

# mostra valores de pico
label_tensaopico = win.addLabel()
label_correntepico =  win.addLabel()

win.nextRow()

# grafico fft tensao
p4 = win.addPlot(title="Tensao [Frequencia]")
p4.setYRange(0, 180)
p4.showGrid(x=True, y=True)
p4.setLabel('bottom', "Frequencia", units='hz')
p4.setLabel('left', "Tensao", units='V/hz')
fftTensao = p4.plot(pen=None, name="FTT da tensao", symbolBrush=(0,0,0), symbolPen='w', symbolSize=6 )

# grafico fft corrente
p5 = win.addPlot(title="Corrente [Frequencia]")
p5.setYRange(0, 1.5)
p5.showGrid(x=True, y=True)
p5.setLabel('bottom', "Frequencia", units='hz')
p5.setLabel('left', "Corrente", units='A/hz')
fftCorrente = p5.plot(pen=None, name="FFT da corrente", symbolBrush=(0,0,0), symbolPen='w', symbolSize=6)

win.nextRow()

# grafico potencia instantanea
p6 = win.addPlot(title="Potencia Instantanea")
p6.setYRange(0, 100)
p6.showGrid(x=True, y=True)
p6.setLabel('bottom', "Tempo (ms)")
p6.setLabel('left', "Potencia", units='W')
potencia = p6.plot(pen=(90,120,50), name="Potencia", antialias=graphic_antialias)

# grafico energia por minuto
p7 = win.addPlot(title="Energia/Minuto")
p7.setYRange(0, 2000)
p7.setXRange(0, 9)
p7.enableAutoRange(axis="y")
p7.showGrid(x=True, y=True)
p7.setLabel('bottom', "Tempo (min)")
p7.setLabel('left', "Energia", units='J')
en_por_min = p7.plot(pen=None, name="Energia", symbolBrush=(0,0,0), symbolPen='w', symbolSize=6, symbol='s')

win.nextRow()

# mostra potencia ativa
label_potenciaAtiva=win.addLabel()

# FPS
label_fps=win.addLabel()

win.nextRow()

# mostra luminancia
label_luminancia = win.addLabel()

# mostra temperatura
label_temperatura = win.addLabel()

###############################
#### FIM Set Up do Grafico ####
###############################


canal_da_leitura = [ 0b000,  # 0
					 0b001,  # 1
					 0b010,  # 2
					 0b000,  # 0
					 0b001,  # 1
					 0b011,  # 3
					 0b000,  # 0
					 0b001,  # 1
					 0b100 ] # 4

# monitora interacao dentro do ciclo de medicao
i = 0

# monitora interacoes antes de mandar pro grafico
j = 0

#variável auxiliar para energia atualizar de 1 em 1 segundo
k = 0

# variavel para o fps counter
last_fps_time = 0

# ultimo tempo q se fez o calculo da energia
last_en_time = 0

# mostra em qual minuto estamos para calcula da energia por minuto
current_minute = 0

# energia acumulada
energia_acumulada = 0

# cada uma das listas guarda as medicoes de um canal
data_chunk = [[],[],[],[],[]]

# indica de qual tipo sera o novo byte. a transmissao comeca com um HIGH
new_byte_is = HIGH

# buffer do byte HIGH
high_buff = 0

# configura a comunicacao serial
arduino = serial.Serial()
arduino.baudrate = 345600
arduino.port = '/dev/ttyACM0'
arduino.open()

# necessario esperar
sleep(2)

# sinal de disparo para o arduino
arduino.write (bytes.fromhex('e6'))

while (arduino.inWaiting() == 0):
	pass
# primeira medicao e invalida, jogamos fora
arduino.read()
arduino.read()

#####################
### LOOP INFINITO ###
#####################

while True:
	while (arduino.inWaiting() == 0):
		pass

	# le o buffer de entrada
	bit_buff = arduino.read()
	bit_buff_num = bit_buff[0]

	# byte HIGH
	if new_byte_is == HIGH:

		if bit_buff_num >> 4 != (canal_da_leitura[i] | 0b1000): # algo deu errado
			print (bit_buff_num)
			print (i)
			quit()

		new_byte_is = LOW
		high_buff = bit_buff_num

	# byte LOW
	else:

		data = ((high_buff & 0b11) << 8) | bit_buff_num
		data_chunk[canal_da_leitura[i]].append(data)

		i = (i + 1) % 9
		j += 1
		new_byte_is = HIGH

	# aprox 10 hz
	if j == 900:

		tensao_inst = ((np.array(data_chunk[0]) * 5/1023) - 2.52) * 112.6
		corrente_inst = ((np.array(data_chunk[1]) * 5/1023) - 2.4) / 2.397
		temp_termopar = (np.array(data_chunk[2]) * 5/1023)
		temp_ref = (np.array(data_chunk[3]) * 5/1023)
		ilum = (np.array(data_chunk[4]) * 5/1023)
		
		# calculos de tensao, corrente e potencia
		
		# fft da tensao
		fft_tensao = np.fft.fft(tensao_inst)

		# fft da corrente
		fft_corrente = np.fft.fft(corrente_inst)

		# calcula grafico tensao na freq
		tensao_freq = abs(fft_tensao) * 1/300
		# pega so as freq na banda de passagem. multiplica por dois por causa da simetria da transformada
		tensao_freq = 2 * tensao_freq[:69]
		# tensao dc foi multiplicada por dois, voltamos ao valor original
		tensao_freq[0] *= 0.5
		
		# calcula grafico corrente na freq
		corrente_freq = abs(fft_corrente) * 1/300
		corrente_freq = 2 * corrente_freq[:69]
		corrente_freq[0] *= 0.5

		# filtra a tensao
		fft_tensao[70:230] = 0 # deleta componentes das freq na banda de rejeicao
		tensao_inst = np.real(np.fft.ifft(fft_tensao))

		# filtra a corrente
		fft_corrente[70:230] = 0
		corrente_inst = np.real(np.fft.ifft(fft_corrente))
		
		# valores de pico da tensao e da corrente
		label_correntepico.setText("Corrente [pico] = " + "{:7.2f}".format(round(max(corrente_inst), 2)) + " A" )
		label_tensaopico.setText("Tensao [pico] = " + "{:7.2f}".format(round(max(tensao_inst), 2)) + " V" )
		
		# valores rms da tensao e da corrente
		label_correnterms.setText("Corrente [RMS] = " +  "{:7.2f}".format(round(sqrt(np.mean(np.square(corrente_inst))), 2)) + " A" )
		label_tensaorms.setText("Tensao [RMS] = " +  "{:7.2f}".format(round(sqrt(np.mean(np.square(tensao_inst))), 2)) + " V" )

		# seta graficos de tensao e corrente no tempo
		tensao.setData(x_t, tensao_inst)
		corrente.setData(x_t, corrente_inst)

		# seta graficos de tensao e corrente na freq
		fftTensao.setData(x_f, tensao_freq)
		fftCorrente.setData(x_f, corrente_freq)

		# potencia instantanea
		pot_inst = tensao_inst * corrente_inst
		potencia.setData(x_t, pot_inst)
		
		# potencia atva
		label_potenciaAtiva.setText("Potencia Ativa = " +  "{:7.2f}".format(round(np.mean(pot_inst), 2)) + " W")

		# tira 0.82 V de offset do amplificador do termopar. 40.9e-6 é o coeficiente do termopar utilizado
		temp_media = (np.average(temp_ref) * 10) +  ( (np.average(temp_termopar) - 0.82) *(1/1000) *(1/(40.9e-6)))
		label_temperatura.setText("Temperatura = " +  "{:7.2f}".format(round(temp_media, 2)) + " C")

		# iluminancia
		label_luminancia.setText("Iluminancia = " +  "{:7.2f}".format(round(np.average(ilum) * 400/3, 2)) + " lx")

		# energia (multiplica sempre pelo periodo)
		energia_acumulada += sum(pot_inst)/sampling_freq
		last_en_time = time() if last_en_time == 0 else last_en_time
		if time() - last_en_time > 60:
			last_en_time = time()
			if current_minute < 10:
				En = np.append(En, energia_acumulada)
				x_tE = np.append(x_tE, current_minute)
			else:
				En = np.append(En, energia_acumulada)
				En = np.delete(En, 0)
				x_tE += 1
				p7.setXRange(current_minute - 9, current_minute)
			en_por_min.setData(x_tE, En)
			current_minute += 1
			energia_acumulada = 0

		# fps
		fps_string = "{:0.1f}".format(1/ (time() - last_fps_time))
		label_fps.setText("FPS = " + fps_string.zfill(4))
		last_fps_time = time()

		pg.QtGui.QApplication.processEvents()

		print("Pacotes no buffer: " + str(arduino.inWaiting()))

		data_chunk = [[],[],[],[],[]]
		j = 0
