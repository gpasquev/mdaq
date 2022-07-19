#!/usr/bin/env python
# coding: utf8

"""

05/11/2014 
Agrego el registro de la fecha y hora en el archivo log.

25/09/2014 
Start adaptation of spectrum.py(ver.140422)@mdaq208 to the mdaq107 package.
Elimino funcion auxiliar de ploteo y la importacion de matplotlib.
Elimino la entrada -step cuando corre como funcion __main__
"""
__version__ = '.141105'

import numpy as np
import sys, glob, time, argparse, os, datetime
import mdaq


# Reads the ASCII string with the smoothed-triangular wave from
# file and store it in ONDAMAC
with open('macveiga1.wave','r') as fid:
    ONDAMAC = fid.readline()



def espec0(hw,N,fout='noname.niente'):
    """ Adquire spectrum in Constant-Aceleration-Mode, using the Veiga's 
        smooth-ended-reference wave.

    Args:
        hw: instance of mdaq107.Instrument. 
        N:  mdaq107 Cycles per file download.
        fout: name (char-string) of the output file."""

    hw.VERBOSE = False

    COUNTS = np.zeros(1024)                # <<< HARDWARE-DEPENDENT-LINE >>>
    print(hw.getStatus())                  # <<< HARDWARE-DEPENDENT-LINE >>>

    i = 0
    t0 = time.time()
    try:
        MUSTSAVE = False
        while 1:
            hw.clear(soft=True)
            hw.setCycleNumber(N)
            
            # MDAQXXX Start to adquiring and timing control
            ti1 = time.time()            
            hw.start()                     
            ti2 = time.time()
            ti = (ti1+ti2)*0.5 -t0
            
            # Waits while MDAQ is counting. In the menwhiles update files and arrays. 
            while hw.getCycleNumber() != N:
                if MUSTSAVE:
                    WrtStr = '%6d %s'%(tflast,COUNTstr)
                    COUNTSnow = np.array(mdaq.hes2numlist(COUNTstr[:-2],4))  # [:-2] to remove TERMINATOR 
                    COUNTS += COUNTSnow
            
                    # New output file proposal (July 2022) --------          
                    COUNTStr2 = ' '.join(['%x'%k for k in COUNTSnow])
                    WrtStr2 = '%.2f %.2f %.2f:'%(tilast,tflast,tflast-tilast) + COUNTStr2 + '\n'
                    with open(fout,'a') as fid:
                        fid = open(fout,'a')
                        fid.write(WrtStr2)
        

                    print('%6d %d'%(tflast,sum(COUNTSnow)),'(ctrl + C to abort)')
                    sys.stdout.flush()
        
                    np.savetxt(fout+'.counts',COUNTS,fmt='%d')
                    MUSTSAVE = False
                time.sleep(0.01)


            tf = time.time() - t0
            tilast = ti
            tflast = tf
            COUNTstr = hw.getCounters()
            MUSTSAVE = True


    except KeyboardInterrupt:
        print('\n Ended by user.')

# FUNCIONE/S AUXILIARES
def _safename(name):
    """ This auxiliar function assure not to overwrite another file with the same name.
 		
	name is the base name of the file. 
    """
    n=glob.glob(name+'.*')
    if len(n)>0:
        k=0
        while 1:
            k+=1
            if len(glob.glob(name+'.%2.2d*'%k))==0:
                break
            elif k==99:
                raise(Exception, 'Please chose another filename')
        name=name+'.%2.2d'%k
        print('The name was changed to "%s" to avoid overwriting'%name+
              'another file with the same name.')
    else:
        name += '.00'    
    return name
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == "__main__":
    """
    
    """

    print()
    print('====================================================================')
    print('spectrum.py ')
    print('====================================================================')
    print()

    # --------------------------------------------------------------------------
    # ARGPARSER  http://docs.python.org/2/library/argparse.html

    parser = argparse.ArgumentParser(
    description='Start adquiring a Mössbauer spectrum with MDAQ107 in the' + 
                'constant-acceleration mode')

    parser.add_argument('filename',
                     type = str, 
                     help = 'Root name of the output spectrum files: filename.counts, '+
                            'filename.wave, filename.mdaqb')

    parser.add_argument('-p','--port',
                     type = str, 
                     default = '/dev/ttyS0',
                     metavar = 'serial-port',    
                     help='Serial port where the hardware mdaq107 is attached.')

    parser.add_argument('-t','--time',
                     type = int, 
                     default = 120, 
                     help = 'Time interval [in sec.] between data download process.')

	#    parser.add_argument('-step',
	#                     type = int, 
	#                     default = 1, 
	#                     help = 'mdaq208 P parameter. Step size in mdaq208-channel advance.')

    parser.add_argument('-tb','--timebase',
                     type = int, 
                     default = 0x1000, 
                     help = 'mdaq107 U parameter (Time Base parameter).')

    args = parser.parse_args()


    port = args.port          
    filename = args.filename   
    U = args.timebase
    #P = args.step  
    T = args.time  
    #N = mdaq.time2N(T,P,U)        # <<< HARDWARE-DEPENDENT-LINE >>>
    N = int(round(T*41.78e6/1024/U))

    # FIN ENTRADA DE ARGUMENTOS ------------------------------------------------
    # --------------------------------------------------------------------------

    #print port,filename,U,P,T,N
    print(port,filename,U,T,N)
     
    hw = mdaq.Instrument(port)
 
    hw.reset()
    time.sleep(0.8)

    hw.setWave(ONDAMAC)
    #hw.selectWave('PROG')         # <<< HARDWARE-DEPENDENT-LINE >>>
    hw.setTimeBase(U)
    hw.setAmplitude(0x400)
    hw.setCycleNumber(N) 

    filename = _safename(filename)

    y_wa = hw.getWave()
    np.savetxt(filename+'.wave', mdaq.hes2numlist(y_wa,4), fmt = '%d')    

    input('Presione una tecla para comenzar a medir')

    fid = open(filename+'.log','w')
    fid.write('#Hardware mdaq107, script spectrum107.py (ver %s)\n'%__version__)
    fid.write('#Veiga´s MAC wave (smooth triangular)\n')
    fid.write('#Status: KKKK QQQQ NNNN OOOO UUUU\n')
    fid.write('#Status: ' + hw.getStatus() + '\n')
    fid.write('#Init date: %s \n'%(datetime.datetime.now().strftime("%I:%M%p %B %d, %Y")))


    print('--------------------------------------------------------------------------------')
    print('%s running'%__file__)
    print('Port: %s'%port)
    print('Output file: %s'%filename)
    print('time step %d seconds:'%T)
    print('\n Ctrl + C to stop and quit')
    print('--------------------------------------------------------------------------------')
 
    fid.write('#Init time: %s \n'%(datetime.datetime.now().strftime("%b-%d-%Y %H:%M:%S")))
    fid.close()

    espec0(hw,N,fout = filename)
  


#    print ' --------------------------------- The End  -------------------------------------'






