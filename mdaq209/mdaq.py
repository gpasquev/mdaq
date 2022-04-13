#!/usr/bin/env python
# coding: utf8

"""
Python Driver for MDAQ209.

The current module have low level drivers to interact through serial port with
MDAQ209-UNLP NIM module.

To start use mdaq with a MDAQ209 just put in an interactive python
shell (as ipython)::

    >>> hw = mdaq.Instrument('/dev/ttyS0')

(where the '/dev/ttyS0' should be replaced by the **correct port**).

If the PC-Hardware is correctly connected you should receipt an OK to::

    >>> hw.reset()      

Class:
    mdaq.Instrument: Class of objects capables of interact with the
    hardware MDAQ through the serial port.

Func:
    mdaq.wavesonfile
    mdaq.wavefromfile
    mdaq.hes2numlist
    mdaq.hesws2numlist

"""

import struct
from time import sleep

import serial


__version__= '0.0.220411'
__author__ = 'Gustavo A. Pasquevich'


FIRMWARE='MDAQ209'
CANALES = 2048

_CODE = 'ascii'
CLOCK = 120e6

_TERMINATOR = '\r\n'   #CR+LF
_RESETSTRING = FIRMWARE+_TERMINATOR  
_NUMBYTESRESETSTRING = len(_RESETSTRING)
_NUMBYTESWAVEIN = 4*CANALES + 2
_NUMBYTESESPEC = 4096+2

class Instrument():
    """ Intermediary between de MDAQ-UNLP Hardware and the python user.

    Each instance gives the user a full set of methods to intercat with the
    MDAQxxx module. In fact there is almost a  method for each intrinsic
    command of the Hardware.

    Some parallel to hardware parameters (as class' atribute) are defined::

        Intrument.HWPARS: a dictionary with the values of the fundamental
        parameters of the Hardware: K, N, U, P, G, g, M and C.

        counts: ¿PARA QUÉ ERA ESTO? TO BE DEFINED.

    >>> hw = mdaq.Instrument(port)

    where "port" is a string indicating the port where the Hardware is 
    conected. For example, '/dev/ttyS0' or '/dev/ttyUSB0'.

    """
    VERBOSE = True
    COMMVERBOSE = False

    HWPARS = {   'K':None,
                 'N':None,
                 'U':None,
                 'P':None,
                 'G':None,
                 'g':None,
                 'M':None,
                 'C':None}

    def __init__(self,port,baudrate=115200):
        self.version = __version__
        self.firmware = FIRMWARE
        self.port = port
        self.ser = serial.Serial(port,baudrate,timeout=4)   # MIRAR BAUD RATE --ETAPA DE PRUEBA
        self.counts = [] #zeros(CANALES,'int')

    def __repr__(self):
        text = 'Intermediary serial object connected to MDAQ-UNLP hardware through\n'
        text += 'port %s \n'%self.port
        return text

    #===========================================================================
    # Basic interface functions ================================================
    #===========================================================================

    #  ACTUALIZADO - TEST COM
    #K) Set Amplitude -> 'K:kkkk?'[4xHEX] + EOL (kkkk is actual value)
    #[0000]=max-, [3FFF]=max+, [2000]=zero
    #Default=[1000]

    def setAmplitude(self,K):
        """ SET the AMPLITUDE of the wave. Send "K" command to the Instrument.

            Args:
                K: an integer between 0 and 16383 (0x3FFF). """
        if K>0x3FFF:
            raise ValueError('Maximum Amplitude 0x3FFF')
        if K<0:
            raise ValueError('input must be an positive integer')
        self._command_with_echo('K',K)
        if self.VERBOSE:
            print('Amplitude %d'%K + ' OK')


    # ACTUALIZADO - TEST COM
    #N) Set Number of cycles -> 'N:nnnn?'[4xHEX] + EOL (nnnn is actual value)
    #Default=[0000]

    def setCycleNumber(self,N):
        """ 
        SET the NUMBER of CYCLES to be adquired. Send "N" command to Hardware.

        Args:
            N: integer between 0 and 0xFFFF.
        """
        if N>0xFFFF: raise ValueError('Maximum N 0xFFFF')
        self._command_with_echo('N',N)
        if self.VERBOSE: print('Cycle Number set to %d'%N + ' OK')

    def waitRK(self):
        """ 
        Wait until RK (answer to START when N != 0) appears on input buffer.
        """
        while self.ser.inWaiting() == 0:
            pass
        instr = self.ser.read(4).decode(_CODE)
        if self.COMMVERBOSE:
            print('<<',instr)
        if instr != 'RK\r\n':
            raise _UnexpectedProtocol('RK',tipo=2,string=instr)
        
    # ACTUALIZADO - TEST COM
    #U) Set Time Base -> 'U:uuuu?'[4xHEX] + EOL (uuuu is actual value)
    #f=120Mhz*PASO/CANALES/BASE
    #Minimum value=[0200]=114 Hz (stops responding->reset is the only way out)
    #Maximum value=[FFFF]=0.9 Hz
    #Default=[16E3]=10Hz

    def setTimeBase(self,U):
        """ SET the TIMEBASE on the instrument. Send "U" command to Hardware.

            Args:
                U: an integer between 0x200 (512) and 0xFFFF (65535)."""
        if U>0xFFFF:
            raise ValueError('Maximum Time Base 0xFFFF')
        if U<0x200:
            raise ValueError('Minimum Time Base 0x200')
        self._command_with_echo('U',U)
        if self.VERBOSE:
            print('TimeBase %d'%U + ' OK')

    # ACTUALIZADO, nuevo en mdaq208  - TEST COM
    #P) Set step -> 'P:pppp?'[4xHEX] + EOL (pppp is actual value)
    #Default=[0001]
    #f=120Mhz*PASO/CANALES/BASE
    #PASO mejor que sea potencia de 2
    #DWELLmin = 33.33 us. Con 4 puntos (PASO=0x0200) se llega hasta 50 KHz. Ojo el slew-rate. Usar K=0x1900 o menos.
    ### Dejo este comentario durante programación de mdaq209

    def setStep(self,P):
        """ SET the STEP on the instrument. Send "P" command to Hardware.

            Args:
                P: an integer between 0x0000 (0) and 0x0x0200 (512)."""
        if P > 0x0200:
            raise ValueError('Maximum Step 0x0200')
        if P < 0:
            raise ValueError('Minimum Step 0x0000')
        self._command_with_echo('P',P)
        if self.VERBOSE:
            print('Step %d'%P + ' OK')

    # ACTUALIZADO  - TEST COM
    #G) Set start gate channel -> 'G:gggg?'[4xHEX] + EOL (gggg is actual value)
    #g) Set stop gate channel -> 'g:gggg?'[4xHEX] + EOL (gggg is actual value)

    def setGate(self,ch0,ch1):
        """ SET the GATE wave. Send G and g to the instrument.

            Args:
                 ch0: Start-channel of the GATE signal.

                 ch1: End-channel of the GATE signal. """
        if ch0 > 0x800:
            raise ValueError('Maximum ch0 0x800')
        if ch1 > 0x800:
            raise ValueError('Maximum ch1 0x800')
        self._command_with_echo('G',ch0)
        self._command_with_echo('g',ch1)
        if self.VERBOSE:
            print('Gate ON on channel %d and GATE OFF on channel %d'%(ch0,ch1) + ' OK')

    # ==========================================================================
    # Data commands ============================================================
    # ==========================================================================

    # VERIFY 2022 mdaq209
    #Y) Dump hex Spectrum -> 8xHEX x 2048/P + EOL

    def getCounters(self):
        """ 
        GET the COUNTERS in Hexadecimal ASCII representation.

        Send "Y" command to Hardware and return the response.

        Returns:
            The complete string returned by the instrument. 
        """

        if self.HWPARS['P'] == None:
            self.getStatus()
        P = self.HWPARS['P']
        if P == 0:
            raise NotImplementedError

        self.ser.write('Y'.encode(_CODE))
        instr = self.ser.readline().decode(_CODE)

        if CANALES%P == 0:    # For take into acount non divisible Steps
            plus = 0
        else:
            plus = 1
        
        # modified from 4 to 8 for mdaq209
        if len(instr)!= 8 * (int(CANALES/P) + plus) + 2:
            raise _UnexpectedProtocol('Y',tipo=1,string=instr)
        return instr

    # ACTUALIZADO -TESTEADO
    #I) Dump bin Spectrum -> 4x2048/P (LSB first, uint32) Warning! No EOL
    #J) Dump short bin Spectrum -> 2x2048/P (LSB first, uint16) Warning! No EOL
    #V) Dump char bin Spectrum -> 1x2048/P (uint8) Warning! No EOL

    def getBinCounters(self,nbytes=4):
        """ 
        GET de COUNTERS in Binary format.

        Send "I","J" or "V" commands to the Hardware.

        Args:
            nbytes: number of bytes per channel 1,2 or 4.

                nbytes = 1: return the LSB unsigned char  [2048 bytes].  
                            I at mdaq208/209
                nbytes = 2: return the LSB unsigned short [4096 bytes].  
                            J at mdaq208/209
                nbytes = 4: DEFAULT. return the LSB unsigned int [8192 bytes].
                            V at mdaq208/209

        Returns:  2048/P list of integers (the counters!). 
        
        
        """
        conversor={4:('I','I'),     # los valores del diccionario son:
                   2:('J','H'),     # (formato para el hardware, comando de
                   1:('V','B')}     #      conversión para struct.unpack)

        # somthing related to P different of one     
        if self.HWPARS['P'] == None:
            self.getStatus()
        P = self.HWPARS['P']
        if P == 0:
            raise NotImplementedError

        if CANALES%P == 0:    # For take into acount non divisible Steps
            plus = 0
        else:
            plus = 1

        # send V J or I dependieng of nbytes
        self.ser.write(conversor[nbytes][0].encode(_CODE))  
        numchan = int(CANALES/P) + plus  # number of spected channels


        
        self.ser.timeout = 10
        instr = self.ser.read(nbytes*numchan)
        self.ser.timeout = 4
        # Timeout workaround is due to low baudrate of mdaq209A. 


        ctemp = struct.unpack('<%d'%numchan+conversor[nbytes][1],instr)
        self.counts += ctemp
        if self.VERBOSE:
            print('internal counter updated')
        return ctemp

    # ACTUALIZADO - testeado
    #M) Dump Cycle Counter -> MMMMMMMM + EOL
    def getCycleNumber(self):
        """ GET the NUMBER of CYCLES being adquiring.

        Send "M" command to Hardware.

        Returns: An int number."""
        self.ser.write('M'.encode(_CODE))
        instr=self.ser.readline().decode(_CODE)
        if self.COMMVERBOSE:
            print('>> M')
            print('<<',instr)
        
        if len(instr)!=10:
            raise _UnexpectedProtocol('M',tipo=1,string=instr)
        return int(instr,16)

    # NUEVO COMANDO. ACTUALIZADO, testeado
    #m) Dump Sum(Spectrum(GGGG:gggg)) -> mmmmmmmm + EOL
    def getSumInGate(self):
        """ GET the sum of counts in the channels between G and g.

        Send "m" command to Hardware.

        Returns: An int number."""
        self.ser.write('m'.encode(_CODE))
        instr=self.ser.readline().decode(_CODE)
        if len(instr)!=10:
            raise _UnexpectedProtocol('m',tipo=1,string=instr)
        return int(instr,16)

    # Testeado
    #Z) Reset Spectrum (resets cycle counter) -> 'OK' + EOL
    def clear(self,soft=False):
        """ CLEAR the counters.

        Send "Z" command to the instrument. Put the cycle counter and the
        memories on zero.

        Args:
            soft: {False} or True. If True it claer also the internal variable
                of the instance: Instruments.counts.  """
        self.ser.write('Z'.encode(_CODE))
        instr=self.ser.readline().decode(_CODE)
        if len(instr)!=4:
            raise _UnexpectedProtocol('Z',tipo=1,string=instr)
        if self.VERBOSE: print('Hardware Counters Cleared')

        if soft:
            self.counts = []
            if self.VERBOSE: 
                print('Internal Counter cleared')

    #O) Set Offset -> 'O:oooo?'[4xHEX] + EOL (oooo is actual value)
    # THIS COMMAND IS STILL ON MDAQ209.... BUT IS NOT IN HELP.
    # I DON'T KNOW WHAT IT IS DOING THERE. (8/4/22)
    def setOffset(self,Offset):
        """ SET the OFFSET. Send "O" command to the Instrument.

            Args:
                Offset: an integer between 0 and 0xFFF."""
        if Offset>0xFFF:    
            raise ValueError('Maximum N 0xFFF')
        self._command_with_echo('O',Offset)
        if self.VERBOSE: 
            print('Offset %d'%Offset + ' OK')

    # ACTUALIZADO
    # h) Status line only -> '......' + EOL
    def getStatus(self,pretty=False):
        """ 
        GET instrument STATUS. Send "h" to the instrument.

        Returns:
            The status string given by the Hardware, three four char 
            hexadecimal which represents:
            CHAN BASE STEP N_CYCLES M_CYCLES AMPLTUDE GATESTRT GATESTOP

        kwarg pretty: True or {False}.  prints status in a pretty format

        Example raw output string (pretty = False):
            output string::

        0800 16E3 0001 00000000 00000000 00003FFF 00000100 000006FF +TERMINATOR

        """
        self.ser.write('h'.encode(_CODE))
        instr=self.ser.readline().decode(_CODE)

        if len(instr)!=61:
            raise _UnexpectedProtocol('h',tipo=1,string=instr)

        for i,k in enumerate(['C','U','P','N','M','K','G','g']):
            self.HWPARS[k] = int(instr.split()[i],16)

        if pretty:
            for k in ['C','U','P','N','M','K','G','g']:
                print(k,self.HWPARS[k])

        return instr[:-2]  # el -1 es para eliminar el fin de linea \r\n

    #==========================================================================
    # WAVEFORM COMMANDS =======================================================
    #==========================================================================

    # Verified 2022 mdaq209
    # X) Dump Waveform -> 4xHEX x 2048 + EOL
    def getWave(self):
        """ GET WAVE from hardware.

        Send "X" command to Hardware.

        Returns: 4*2048 + 2 length string. (Wave + EOL)
        """
        self.ser.write('X'.encode(_CODE))
        instr = self.ser.readline().decode(_CODE)
        if len(instr)!=_NUMBYTESWAVEIN:
            raise _UnexpectedProtocol('Unexpected wave-string length')
        return instr


    # PROBLEMAS CON EL SETEO DE ONDAS. PUEDE 
    # QUE ALGO CON EL TIEMPO ENTER CARACTERES
    # ENVIADOS   WORKING!!!!
    # W) Upload Waveform -> 'OK' + EOL
    def setWave(self,wavestr):
        """ SET WAVE on hardware.

        Send "W" command to the hardware.

        Args:
            The input argument ("wavestr") must be an string with the WAVE 
            values one each before the other in 4 hexadecimal digits without 
            spaces and without end of line characters.
            Expected input string: 4x2048 char wavestring.

        Example:
            wavestr='00000001000200030004......03FD03FE03FF'
            correspond to a wave that start with the numbers 0,1,2,3,4 and 
            end with the numbers 0x3FD,0x3FE and 0x3FF.
        """
        self.ser.write('W'.encode(_CODE))
        self.ser.write(wavestr.encode(_CODE))
        instr = self.ser.readline().decode(_CODE)
        if len(instr)!=4:
            raise _UnexpectedProtocol('W',tipo=1,string=instr)

    # NUEVA VERIFICAR ENTRADA!!!!!
    #L) Select waveform (+A:MAC DEFAULT, +V:MVC or +P:PROG)
    def selectWave(self,which):
        """ SELECT from the stored waves on hardware.

        Send "L" command to Hardware.

        Args:
            string:  CA, CV or PROG.

        """
        dic = {'MAC':'A','MVC':'V','PROG':'P','CA':'A','CV':'V'}
        outstr = 'L'+dic[which]
        self.ser.write(outstr.encode(_CODE))

    #==========================================================================
    # RUN COMMANDS ============================================================
    #==========================================================================

    # ACTUALIZADO
    # S) Start (does NOT reset cycle counter) -> 'OK' + EOL
    def start(self):
        """ START the adquisition.

        Send "S" command to Hardware."""
        self.ser.write('S'.encode(_CODE))
        if self.COMMVERBOSE:
            print('>> S')
        instr = self.ser.read(4).decode(_CODE)
        if self.COMMVERBOSE:
            print('<<',instr)
        if instr != 'OK\r\n':
            raise _UnexpectedProtocol('S',tipo=1,string=instr)

    # ACTUALIZADO
    # T) Stop -> 'OK' + EOL
    def stop(self):
        """ STOP the adquisition.

        Send "T" command to Hardware."""
        self.ser.write('T'.encode(_CODE))
        if self.COMMVERBOSE:
            print('>> T')
        instr = self.ser.read(4).decode(_CODE)
        if self.COMMVERBOSE:
            print('<<',instr)
        if instr != 'OK\r\n':
            raise _UnexpectedProtocol('T',tipo=1,string=instr)

    # R) Reset -> 'MDAQ208' + EOL
    def reset(self):
        """ RESET the hardware.

            Send "R" to the hardware.

        Reset the hardware and clear the input buffer.
        """
        
        # I don't remember why I send that '*'. Maybe to ensure
        # abort any thing is waitting mdaq module 
        self.ser.write('*'.encode(_CODE))  

        self.ser.read(self.ser.inWaiting())   # vacio el buffer
        if self.VERBOSE:
            print('bytes:',self.ser.inWaiting())
        self.ser.write('R'.encode(_CODE))
        instr = self.ser.read(_NUMBYTESRESETSTRING).decode(_CODE)
        if instr == _RESETSTRING and self.ser.inWaiting() == 0:
            print('reset.. OK')
        else:
            raise _UnexpectedProtocol('R',tipo=1,string=instr)

    # Auxilary Routines ------------------------------------------
    # -------------------------------------------------------------------------

    def open(self):
        """ Open the serial port. """
        self.ser.open()

    def close(self):
        """ Close the serial port. """
        self.ser.close()

    def raw(self,string):
        """ 
        Send raw strings to the MDAQxxxx. 
        
        Any string to be sended directly to the MDAQxxx.
        This functions print on standard output the inmediatly response
        of the MDAQxxx. 
        
        Example:
            raw('K0001') will send the string K0001 and change the amplitude
            to 0x0001 value. Inmediartly MDAQxxx answer KXXXX?0001 indicating
            the change has be done. Where XXXX is the amplitude before 
            modification.
        """
        self.ser.write(string.encode(_CODE))
        sleep(0.1)
        nb = self.ser.inWaiting()
        strout = ''
        while nb > 0:
            strout += self.ser.read(nb).decode(_CODE)
            nb = self.ser.inWaiting()
            sleep(0.05)
        print(strout)

    def frequency(self,P=None,U=None):
        """ Calculate the actual work frequency (in Herz).

            Atetntion! It use HWPARS, so this variable must be well actualized. 
        """
        if P == None:
            P = self.HWPARS['P']
        if U == None:
            U = self.HWPARS['U']
        return frequency(P,U)
    
    def _command_with_echo(self,com,value):
        """ Auxiliar function for standar setting parameters comunication.

        Send the "com" command, then read the next 7 chars: "com":XXXX?. Then
        send the wanted value and read the echo.

        If all works right the corresponding self.HWPARS is updates.
        On the contrary if something goes bad, all the HWPARS are updated to
        None indicating the unknown situation.

        """
        self.ser.write(com.encode(_CODE))
        instr=self.ser.read(7).decode(_CODE)
 
        if instr[0:2]!= com+':' or instr[6]!='?':
            raise _UnexpectedProtocol(com,tipo=1,string=instr)

        numstr = '{:04X}'.format(value)
        self.ser.write(numstr.encode(_CODE))
        instr = self.ser.read(6).decode(_CODE)

        if instr != '%0.4X'%value + _TERMINATOR:  # something wrong!!!
            for k in self.HWPARS.keys():
                self.HWPARS[k] = None
            raise _UnexpectedProtocol(com,tipo='EchoFail')
        else:                                     # All OK
            self.HWPARS[com] = value


class _UnexpectedProtocol(Exception):
    def __init__(self, value, tipo=0,string=''):
        if tipo == 0:
            self.value = value
        elif tipo == 1:
            self.value = 'Unexpected response to the command %s. Response: "%s"'%(value,string)
        elif tipo == 'EchoFail':
            self.value = 'Failed echo command %s'%(value)
        elif tipo == 2:
            self.value = 'Not expected string. Received: {:}'.format(value)
    def __str__(self):
        return repr(self.value)


def hes2numlist(string,bn):
    """ Hexadecimal string to list of integers.

    Args:
        string: string with hexadecimal integers of the same char length 
                without separation character.
        bn:     integer. Number of characters per hexadecimal number.

    Returns: A list of integers.

    Example:
        If string='0001000A000D0010...' and bn = 4 then the function
        returns [1,10,13,16,...].  
        
        Same string but with bn = 8 returns [65546, 851984, ...].
    """
    n = int(len(string)/bn)
    y = list()
    for i in range(n):
        y.append(int(string[i*bn:bn*(i+1)],16))
    return y

def heswis2numlist(string):
    """ 
    Convert a string to a list of integers. 
        
    String to list of integers. The string is a list of integers writen in
    hexadecimal and separated by sapces:
    HExadeciaml-String-WIth-Space-TO-NUMber-LIST

    Args:
        string: string with hexadecimal integers of the same char length 
                without separation character.
        bn:     integer. Number of characters per hexadecimal number.

    Returns: A list of integers.

    Example:
        if string='0001 000A 000D...' and bn = 4 then the function
        returns [1,10,13,...].   """
    a = string.split()
    lista = list()
    for k in a:
        lista.append(int(k,16))
    return lista

def wavefromfile(datafile,label):
    """
    OLD FUNCTION 
    Takes the "label" wave from "datafile".

    Args:
        datafile: a file with MDAQxxx waves.
        label: string that identifie the wave.
    Returns:
        wave in a list fo integers.

    Read /auxilires/ondas.txt and /auxilires/ondas.dat for more information.
    """
    fid=open(datafile,'r')
    for k in fid.readlines():
        if k.split(':')[0] == label:
            return k.split(':')[1][:-1]   # el -1 es para eliminar el fin de
                                          # línea al final del archivo
    raise ValueError('Wave labeled: %s isn''t in the file %s'%(label,datafile))

def wavesonfile(datafile):
    """  OKD FUNCTION 
    List the waves contents of datafile.

    Args: datafile: the name of a file with MDAQ waves.

    Returns: a list with the labels of the waves on the file.
    """
    fid=open(datafile,'r')
    lista=list()
    for k in fid.readlines():
        if k[0] == '#' or len(k) < 4096:
            pass
        else:
            lista.append(k.split(':')[0])
    return lista

def frequency(P,U):
    """ 
    Returns the frequency corresponding to the parameters P (step) and 
    U (TimeBase). 

    Returns   f = CLOCK * STEP / CHANNELS / BASE

    """

    return CLOCK*P/CANALES/U

def time2N(t,P,U):
    """ 
    Returns cycle number N such that the total elapsed time is as close 
    as possible 't'. 
    """
    return int( round( t*frequency(P,U) ) )   

def elapsedtime(N,P,U):
    """ 
    Returns elapsed-time corresponding to N cycles, when P and U are given.

    Returns   T = N * 1 / :func:`frequency`
    """ 
    return N/frequency(P,U)

