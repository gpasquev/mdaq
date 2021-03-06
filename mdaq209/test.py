#!/usr/bin/env python
# coding: utf8

""" test module for mdaq.py working on mdaq209 """

import sys
import mdaq
import time

PORT = '/dev/ttyUSB0'
# BR   = 19200
BR   = 115200

# Auxiliary functions ------------------------------
def title(string):
    print((' '+string+' ').center(40,'-'))

def done():
    print('OK'.center(40,'-'))
    print()

def push():
    input('push enter to continue')
# --------------------------------------------------

# Create the object pointing to teh Instrument
hw = mdaq.Instrument(PORT,baudrate= BR)

#======================================================================
title('RESET')
hw.reset()
done()

#======================================================================
title('GET STATUS')
pars = hw.getStatus()
print(pars)
done()

#======================================================================
title('AMPLITUDE')
print('Put MDAQ### output module on oscilloscope and watch the signal.')
print('If possible, trigger oscilloscope externally with START-mdaq### output BNC')
print()
push()

hw.setAmplitude(0)
print('Amplitude has being set to maximum (negative)')
push()

hw.setAmplitude(8192)
print('Amplitude has being set to cero')
push()


hw.setAmplitude(0x3FFF)
print('Amplitude has being set to maximum (positive)')
done()

#======================================================================
title('FREQUENCY')
hw.reset()
base = hw.getStatus().split()[1]
print('default time base (read with getStatus): %s'%base)
push()

minbase = 0x200
maxbase = 0xFFFF
hw.setTimeBase(minbase)
print('Timebase changed to minimum value %s'%minbase)
push()

hw.setTimeBase(maxbase)
print('Timebase changed to maximum value %s'%maxbase)
push()
print('*** mdaq will not change instantanly!!! ***')
done()


#======================================================================
title('CHANNEL STEP')
hw.reset()
step = hw.getStatus().split()[2]
print('default step (read with getStatus): %s'%step)
push()

print('Loop over step from 2 to 2**9)')
for k in range(1,9):
    step = 2**k
    hw.setStep(step)
    print('Step changed to %d'%step)
    push()

done()

#======================================================================
title('GATE')
hw.reset()
pars = [int(k,16) for k in hw.getStatus().split()]

print('PUT GATE OUTPUT ON CHANNEL 2')
print('Default GATE from %d to %d'%(pars[6],pars[7]))
push()
hw.setGate(0,1024)
print('Set GATE ON on first half of tringualar wave')
push()
hw.setGate(1024,0)
print('Set GATE ON on second half of tringualar wave')

done()

#======================================================================
title('CYCLE NUMBER, START and STOP')
M0 = hw.getCycleNumber()
print('Initial Cycle numebers {:}'.format(M0))
hw.start()
print('Acqusition has started, wait 1 second')
time.sleep(1)
M0 = hw.getCycleNumber()
print('Cycle numebers {:}'.format(M0))
print('wait 1 second')
time.sleep(1)
hw.stop()
M0 = hw.getCycleNumber()
print('Acquisition is stopped')
print('Cycle numbers {:}'.format(M0))
print('wait 1 second')
time.sleep(1)
M0 = hw.getCycleNumber()
print('Cycle numbers {:}'.format(M0))

done()

#======================================================================
title('SET CYCLE NUMBERS ')
NNN = 100
hw.stop()
hw.clear()
freq = hw.frequency()
DT = NNN/freq
print('Current frequency: {:.2f}'.format(freq))
print('Acquisition will be done on {NNN:d} cycles'.format(NNN=NNN))
hw.setCycleNumber(NNN)
hw.start()
print('Acquisition has started, we have to wait to RK answer indicating')
print('Tt should be finnish in {:.2f} seconds'.format(DT))
hw.waitRK()
print('RK answer has arrived!!!')
M0 = hw.getCycleNumber()
print('Cycle numbers {:}'.format(M0))

done()









