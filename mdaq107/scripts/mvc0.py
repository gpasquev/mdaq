#!/usr/bin/env python
# coding: utf8


""" 
script to get CONSTANT VELOCITY spectrum with MDAQXXX (here 107)  

Be sure thah on the same folder than this script file are the files
mdaq.py and mvcdef0.w
Be also sure mdaq.py correspond to this hardware.

python mvc0.py port fname ChTime ChStep

    port:  (string) serial port. Example: \dev\ttyUSB0
    fname: (string) tag for output filename. Example: firstspectrum
    ChTime: (int)   Time per channel (In seconds). Example: 10 
    ChStep: (int)   Step between channels. Example 32

    sys.argv[1]: serial port
    sys.argv[2]: fname
    sys.argv[3]: Time at each channel.
    sys.argv[4]: Step between channesl.
"""

import sys, time
import mdaq as mdaq

# getting input arguments
scriptname = sys.argv[0]
port = sys.argv[1]
name = sys.argv[2]
change_ratio = int(sys.argv[3])
PASO = int(sys.argv[4])

wavefile ='mvcdef0.w'
#ondalabel='MVC-DEF0'
with open(wavefile) as fid:
    wave_string = fid.read().rstrip('\n')

# output filename 
filename= time.strftime('%m-%d_%H:%M:%S_')+name

# Initiatting hardware communication
hw=mdaq.Instrument(port)
hw.setWave(wave_string)
hw.clear()

# Primeras líneas del archivo de datos
fid=open(filename,'w')
fid.write('# {:}'.format(scriptname))
fid.write('# script done for {:} hardware\n'.format('MDAQ107'))
fid.write('# Firmware: %s\n'%hw.firmware)
fid.write('# mdaq.py version: %s\n'%hw.version)
fid.write('# --------------------------------------------------------------------------------\n')
fid.write('# Velocity refrence wave from file "%s". \n'%(wavefile))
fid.write('# Hardware Status: %s\n'%hw.getStatus())
fid.write('# Output file name: %s\n'%filename)
fid.write('# --------------------------------------------------------------------------------\n')

# Setea la amplitud inicial (supuestamente negativo de máximo valor absoluto)
hw.setAmplitude(0)
CHAN=0
# Detenemos Para asegurar que la onda estabilizó 
input('Presione una tecla para comenzar a medir')


# Info en pantalla 
print('--------------------------------------------------------------------------------')
print('hw01 running')
print('Port: %s'%port)
print('Output file: %s'%filename)
print('Changin channel every %d seconds:'%change_ratio)
print('\n Ctrl + C to stop and quit')
print('--------------------------------------------------------------------------------')


P=1

# Calculamos el número de ciclos de manera que el tiempo entre canales sea "change_ratio"
status=hw.getStatus()
TB=int(status.split(' ')[-1],16)
print('TIME BASE %d'%TB)

NUMCICLOS = int(change_ratio*(40960./4400))
# Seteamos ese numero de cíclos
hw.setCycleNumber(NUMCICLOS)

# Main loop. Catching ctrl+c to getting out.
t_inicial=time.time()
try:
    while 1:
        hw.start()
        while hw.getCycleNumber()!=NUMCICLOS:
            # print hw.getCycleNumber()
            time.sleep(0.01)
        inpstr=hw.getCounters()

        # escribe a disco
        fid.write('%d:%d:'%(round(time.time()-t_inicial),CHAN)+inpstr)
        print('chan %d, counts %d'%(CHAN,int(inpstr[:4],16)))
        hw.clear()      
        # Setea nuevo canal:
        if P==1:
            if CHAN+PASO > 0xFFF:
                P=-1
            else:
                CHAN += PASO
        else:
            if CHAN - PASO < 0:
                P=1
            else:
                CHAN -= PASO

        hw.setAmplitude(CHAN)        
       
except KeyboardInterrupt:
    print('\n Finalizando\n Guardando última línea')
    inpstr=hw.getCounters()
    fid.write('%d:'%round(time.time()-t_inicial)+inpstr)

print(' --------------------------------- The End  -------------------------------------')        






