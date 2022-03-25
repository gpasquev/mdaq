#!/usr/bin/env python
# coding: utf8

"""
Python Drivers to work on MDAQ hardware

The current module have low leves drivers to interact through serial port with
MDAQ-UNLP NIM modules.

To start use mdaq with a MDAQ-UNLP equipment just put in an interactive python
shell::

    >>> mdaq.Instrument('/dev/ttyS0')

(with the **correct port** you are using). 

Class:
    mdaq.Instrument: Class of objects capables of interact with the hardware MDAQ
    through the serial port.

Func:
    mdaq.wavesonfile
    mdaq.wavefromfile
    mdaq.hes2numlist
    mdaq.hesws2numlist

"""
import serial
import warnings
import struct
from numpy import zeros

__version__='0.4.0'
__author__='Gustavo A. Pasquevich'

FIRMWARE='MDAQ107-MAC'

_TERMINATOR='\r\n'   #CR+LF
_RESETSTRING=FIRMWARE+_TERMINATOR     # String que devuelve la placa al resetear
_NUMBYTESRESETSTRING=len(_RESETSTRING)
_NUMBYTESWAVEIN=4096+2                   
_NUMBYTESESPEC=4096+2



print('Python Drivers for Mössbauer system %s'%FIRMWARE)
print('version %s'%__version__)

class _UnexpectedProtocol(Exception):
    def __init__(self, value, tipo=0,string=''):
        if tipo == 0:
            self.value = value
        elif tipo == 1:
            self.value = 'Respuesta al comando %s de longitud no esperada. Respuesta entre comillas: "%s"'%(value,string)
        elif tipo == 'EchoFail':
            self.value = 'Fallo en el echo del comando %s'%(value)
    def __str__(self):
        return repr(self.value)

def MossbauerHard(port):
    """ points to Instrument class. Deprecating function. """
    warnings.warn('El nombre de la calse MossbauerHard se cambio a Intsrument. En vesriones futuras no exitirá este parche.')
    return Instrument(port)

class Instrument():
    """ Intermediary between de MDAQ-UNLP Hardware and the python user.

        El objeto queda definido solamente por el puerto serie donde se encuentra
        el dispositivo. Por ejemplo port='/dev/ttyS0' o '/dev/ttyUSB0'."""
    VERBOSE = True

    def __init__(self,port):
        self.version=__version__
        self.firmware=FIRMWARE
        self.port=port
        self.ser=serial.Serial(port,115200,timeout=2)
        self.counts=zeros(1024,'int')

    def __repr__(self):
        text= 'Intermediary serial object connected to MDAQ-UNLP hardware through\n'
        text+='port %s \n'%self.port
        return text
    #===========================================================================
    # Basic interface functions 

    #K) Set Amplitude -> 'K:kkkk?'[4xHEX] + EOL (kkkk is actual value)
    #[0000]=max+, [0FFF]=max-, [0800]=zero
    #Default=[0400]
    def setAmplitude(self,K):
        """ SET the AMPLITUDE of the wave. Send "K" command to the Instrument.
            
            Args:
                K: an integer between 0 and 4095. """
        if K>0xFFF :  raise ValueError('Maximum A 0xFFF')
        if K<0     :  raise ValueError('input must be an positive integer')
        self._command_with_echo('K',K)
        if self.VERBOSE: print('Amplitude %d'%K + ' OK')

    #Q) Set Central Channel -> 'Q:qqqq?'[4xHEX] + EOL (qqqq is actual value)
    #[0000]=max+, [0FFF]=max-, [0800]=center
    #Default=[0800]
    def setCentralChannel(self,Q):
        """ Set the CENTRAL CHANNEL. Send "Q" command to the instrument. 
            
            Args:
                Q: an integer betwenn 0 and 4095. """
        if Q>0xFFF :  raise ValueError('Maximum Q 0xFFF')
        if Q<0     :  raise ValueError('Input must be an positive integer')
        self._command_with_echo('Q',Q)
        if self.VERBOSE: print('Central Channel set to %d'%Q + ' OK') 

    #N) Set Number of cycles -> 'N:nnnn?'[4xHEX] + EOL (nnnn is actual value)
    #Default=[0000]
    def setCycleNumber(self,N):
        """ SET the NUMBER of CYCLES to be adquired. Send "N" command to Hardware.
            
            Args: 
                N: an integer between 0 and 0xFFFF."""
        if N>0xFFFF: raise ValueError('Maximum N 0xFFFF')
        self._command_with_echo('N',N)
        if self.VERBOSE: print('Cycle Number set to %d'%N + ' OK')

    #O) Set Offset -> 'O:oooo?'[4xHEX] + EOL (oooo is actual value)
    def setOffset(self,Offset):
        """ SET the OFFSET. Send "O" command to the Instrument.  

            Args:
                Offset: an integer between 0 and 0xFFF."""
        if Offset>0xFFF:    raise ValueError('Maximum N 0xFFF')
        self._command_with_echo('O',Offset)
        if self.VERBOSE: print('Offset %d'%Offset + ' OK')

    #G) Set start gate channel -> 'G:gggg?'[4xHEX] + EOL (gggg is actual value)
    #g) Set stop gate channel -> 'g:gggg?'[4xHEX] + EOL (gggg is actual value)
    def setGate(self,ch0,ch1):
        """ SET the GATE wave. Send G and g to the instrument.

            Args:
                 ch0: Start-channel of the GATE signal.

                 ch1: End-channel of the GATE signal. """
        if ch1>0x3FF :  raise ValueError('Maximum ch1 0x3FF')
        if ch0>ch1: raise ValueError('ch0 must be lower than ch1')
        self._command_with_echo('G',ch0)
        self._command_with_echo('G',ch1)
        if self.VERBOSE: print('Gate set between channels %d and %d'%(ch0,ch1) + ' OK' )  

    #U) Set Time Base -> 'U:uuuu?'[4xHEX] + EOL (uuuu is actual value)
    #f=41.78E6/1024/uuuu, ie [0800]=20Hz, [1000]=10Hz, [2000]=5Hz
    #Minimum value=[0200]=80Hz (stops responding->reset is the only way out)
    #Maximum value=[FFFF]=0.6Hz 
    #Default=[1000]
    def setTimeBase(self,U):
        """ SET the TIMEBASE on the instrument. Send "U" command to Hardware.
            
            Args:
                U: an integer between 0x500 (1280) and 0xFFFF (65535)."""
        if U>0xFFFF:  raise ValueError('Maximum Time Base 0xFFFF')
        if U<0x500:   raise ValueError('Minimum Time Base 0x500')
        self._command_with_echo('U',U)
        if self.VERBOSE: print('TimeBase %d'%U + ' OK')


    # P) Status -> 'kkkk qqqq nnnn oooo uuuu' + EOL
    def getStatus(self):
        """ GET instrument STATUS. Send P to the instrument.

        Returns: 
            The status string given by the Hardware, five four char hexadecimal 
            which represents: 
            Amplitude, central-channel, cycle-number, offset and time-base
        
        Example:
            output string: "0100 02A3 0010 0800 0FFF"+TERMINATOR correspond to
            Amplitude = 0x100, Central Channel = 0x2A3, Cycle Number 0x10,
            Offset = 0x800 and Time Base = 0xFFF """        
        self.ser.write('P')
        instr=self.ser.readline()
        if len(instr)!=26:
            raise _UnexpectedProtocol('P',tipo=1,string=instr)
        return instr[:-2]  # el -1 es para eliminar el fin de linea \r\n

    # L) Error  -> '11111111 22222222 33333333 44444444' + EOL
    # NO ESTA PROGRAMADA. Esta función tengo entendido que será discontinuada en
    # las próximas versiones.

    # DATA COMMANDS ------------------------------------------------------------
    # --------------------------------------------------------------------------

    # Dump hex Spectrum -> 4xHEX x 1024 + EOL
    def getCounters(self):             
        """ GET the COUNTERS in Hexadecimal ASCII representation. 

        Send "Y" command to Hardware and return the response.
        
        Returns:
            The complet string returned by the instrument. It should be a
            1024x4 chars string."""
        
        self.ser.write('Y')
        instr=self.ser.readline()
        if len(instr)!=_NUMBYTESESPEC:
            raise _UnexpectedProtocol('Y',tipo=1,string=instr)
        return instr

    #I) Dump bin Spectrum -> 4x1024 (LSB first, uint32)  Warning! No EOL
    #J) Dump short bin Spectrum -> 2x1024 (LSB first, uint16) Warning! No EOL
    #V) Dump char bin Spectrum -> 1x1024 (uint8)   Warning! No EOL
    def getBinCounters(self,nbytes=4):
        """ GET de COUNTERS in Binary format.

        Send "I","J" or "V" commands to the Hardware.

        Args:
            nbytes: an of the integers = 1,2 or 4. They indicate the number 
            of bytes per channel:
 
                nbytes=1: return the LSB unsigned char  [1024 bytes]
                
                nbytes=2: return the LSB unsigned short [2048 bytes]
                
                nbytes=4: return the LSB unsigned int   [4096 bytes] <-- default                

        Return:  1024 tuple with the counters.  """
        conversor={4:('I','I'),     # los valores del diccionario son:
                   2:('J','H'),     # (formato para el hardware, comando de 
                   1:('V','B')}     #            conversión para struct.unpack)
        self.ser.write(conversor[nbytes][0])
        numdata=nbytes*1024
        instr=self.ser.read(numdata)
        ctemp=struct.unpack('<1024'+conversor[nbytes][1],instr)
        self.counts += ctemp
        if self.VERBOSE: print('contador interno actualizado')
        return ctemp

    #M) Dump Cycle Counter -> MMMMMMMM + EOL
    def getCycleNumber(self):             
        """ GET the NUMBER of CYCLES being adquiring. 

        Send "M" command to Hardware.

        Returns: An int number.""" 
        self.ser.write('M')
        instr=self.ser.readline()
        if len(instr)!=10:
            raise _UnexpectedProtocol('M',tipo=1,string=instr)
        return int(instr,16)

    #Z) Reset Spectrum (resets cycle counter) -> 'OK' + EOL 
    def clear(self,soft=False):
        """ CLEAR the counters. 

        Send "Z" command to the instrument. Put the cycle counter and the 
        memories on zero.

        Args:
            soft: {False} or True. If True it claer also the internal variable 
                counts.  """        
        self.ser.write('Z')
        instr=self.ser.readline()
        if len(instr)!=4:
            raise _UnexpectedProtocol('Z',tipo=1,string=instr)
        if self.VERBOSE: print('Counters Cleared')
        
        if soft:
            self.counts=zeros(1024,'int')
            if self.VERBOSE: print('Internal Counter cleared')
        
    # WAVEFORM COMMANDS --------------------------------------------------------
    # --------------------------------------------------------------------------

    # X) Dump Waveform -> 4xHEX x 1024 + EOL
    def getWave(self):       
        """ GET WAVE from hardware. 

        Send "X" command to Hardware.

        Returns: 4x1024 +2 length string. (Wave + LF + CR)         
        """
        self.ser.write('X')
        instr = self.ser.readline()
        if len(instr)!=_NUMBYTESWAVEIN:
            raise _UnexpectedProtocol('Wave string not expected lenght')
        return instr

    # W) Upload Waveform -> 'OK' + EOL
    def setWave(self,wavestr):             
        """ SET WAVE on hardware. 

        Send "W" command to Hardware.

        Args:
            The input argument ("wavestr") must be an string with the WAVE values 
            one each before the other in 4 hexadecimal digits without spaces and 
            without end of line characters.
            
            Expected input string: 4x1024 char wavestring. 
        
        Example:
            wavestr='00000001000200030004......03FD03FE03FF'
            correspond to a wave that start with the numbers 0,1,2,3,4 and end with 
            the numbers 0x3FD,0x3FE and 0x3FF
        """ 
        self.ser.write('W'+wavestr)
        instr=self.ser.readline()
        if len(instr)!=4:
            raise _UnexpectedProtocol('W',tipo=1,string=instr)

    # RUN COMMANDS -------------------------------------------------------------
    # --------------------------------------------------------------------------

    # S) Start (resets cycle counter) -> 'OK' + EOL
    def start(self):
        """ START the adquisition. 

        Send "S" command to Hardware."""
        self.ser.write('S')
        instr = self.ser.read(4)
        if instr != 'OK\r\n':
            raise _UnexpectedProtocol('S',tipo=1,string=instr)        

    # T) Stop -> 'OK' + EOL
    def stop(self):
        """ STOP the adquisition. 

        Send "T" command to Hardware."""    
        self.ser.write('T')
        instr = self.ser.read(4)
        if instr != 'OK\r\n':
            raise _UnexpectedProtocol('T',tipo=1,string=instr)

    # R) Reset -> 'MDAQ107-MAC' + EOL 
    def reset(self):
        """ RESET the hardware. Send "R" to the hardware.
        
        Reset the hardware and clear the input buffer.
        """
        self.ser.write('*')  # Este asterisco no se para que lo mando? 
                             # Pero por algo debe estar
        self.ser.read(self.ser.inWaiting())
        self.ser.write('R')
        instr=self.ser.read( _NUMBYTESRESETSTRING)
        if instr == _RESETSTRING and self.ser.inWaiting()==0:
            print('reset.. OK')
        else:
            raise _UnexpectedProtocol('R',tipo=1,string=instr)  

    # rutinas auxiliares y secundarias------------------------------------------
    # --------------------------------------------------------------------------

    def _command_with_echo(self,com,value):
        """ Función auxiliar.

        Envía el comando "com".        
        Leé 7 caracteres: "com":XXXX?        
        """
        self.ser.write(com)
        instr=self.ser.read(7)
        if instr[0:2]!= com+':' or instr[6]!='?':
            raise _UnexpectedProtocol(com,tipo=1,string=instr)
        self.ser.write('%0.4X'%value)
        instr=self.ser.read(6)
        if instr != '%0.4X'%value + _TERMINATOR:
            raise _UnexpectedProtocol(com,tipo='EchoFail')
            
    def open(self):
        """ Open the serial port. """        
        self.ser.open()

    def close(self):
        """ Close the serial port. """        
        self.ser.close()

    def hes2numlist(self,string,bn):
        warnings.warn('This method is going to be eliminated from the class. Use the corresponding method from the module')
        return hes2numlist(string,bn)

    def heswis2numlist(self,string):
        warnings.warn('This method is going to be eliminated from the class. Use the corresponding method from the module')
        return heswis2numlist(string)

    def wavefromfile(self,datafile,label):
        warnings.warn('This method is going to be eliminated from the class. Use the corresponding method from the module')
        return wavefromfile(datafile,label)

    def wavesonfile(self,datafile):
        warnings.warn('This method is going to be eliminated from the class. Use the corresponding method from the module')
        return wavesonfile(datafile)

def hes2numlist(string,bn):
    """ hexadecimal string to list of integers.

    Args:
        string: string with hexadecimal integers of the same char length without
            separation character.
        bn: integer. Number of characters per hexadecimal number.

    Returns: A list of integers.
 
    Example:
        if string='0001000A000D...' and bn = 4 then the function 
        returns [1,10,13,...].   """
    n=len(string)/bn
    y=list()
    for i in xrange(n):
        y.append(int(string[i*bn:bn*(i+1)],16))
    return y

def heswis2numlist(string):
    """ hexadecimal with sring string to list of integers.

    Args:
        string: string with hexadecimal integers of the same char length without
            separation character.
        bn: integer. Number of characters per hexadecimal number.

    Returns: A list of integers.
 
    Example:
        if string='0001 000A 000D...' and bn = 4 then the function 
        returns [1,10,13,...].   """
    a=string.split()
    lista=list()
    for k in a:
        lista.append(int(k,16))
    return lista

def wavefromfile(datafile,label):
    """Takes the "label" wave from "datafile".

        Args:
            datafile: a file with MDAQxxx waves.
            label: string that identifie the wave.
        Returns:
            wave in a list fo integers.

        Read /auxilires/ondas.txt and /auxilires/ondas.dat for more information"""
    fid=open(datafile,'r')
    for k in fid.readlines():
        if k.split(':')[0] == label:
            return k.split(':')[1][:-1]   # el -1 es para eliminar el fin de  
                                          # línea al final del archivo
    raise ValueError('Wave labeled: %s isn''t in the file %s'%(label,datafile))

def wavesonfile(datafile):
    """list the waves contents of datafile.

        Args: datafile: the name of a file with MDAQ waves.
        
        Returns: a list with the labels of the waves on the file."""
    fid=open(datafile,'r')
    lista=list()
    for k in fid.readlines():
        if k[0] == '#' or len(k) < 4096:
            pass
        else: 
            lista.append(k.split(':')[0])
    return lista
        

