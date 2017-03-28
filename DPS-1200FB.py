"""
Results of reverse-engineering the PIC microcontroller in the HP DPS-1200FB power supply (made by Delta)

DrTune / March 2017  (drtune@gmail.com)

The DPS-1200FB is a very high-quality (and high power) power supply readily available on EBay and popular with
people who want a LOT of 12v DC power; most commonly R/C hobbyists to power their battery chargers.
It offers 99.9% power factor (due to active PFC), mid-90% efficiency, and 75A (110v) or 100A (240v) output at 12v

There are many docs on the net about how to;
a) Get the PSU to turn on.
b) Convert two PSUs to run in series providing 24v by floating the GND output from the chassis.

However nobody figured out how to access the internal CPU to read all the useful status/monitoring info.

I opened one up, located the main CPU (a PIC 16F886) and read its code (was not readout protected), then
disassembled and commented a lot of it. The goal was to reverse-engineer the I2C protocol, which is largely done.

This code works on a DPS-1200FB A (P/N 438202-002 REV:05F), it will probably work on all revisions of this PSU.

At time of writing this I have not figured out how to turn on/off the PSU output via I2C; this may or may not be possible, 
although the ENABLE pin is a simple logic-level (active-low) signal that may be driven by a GPIO.

NOTE: If you use two in series and want I2C from both of them you MUST use an I2C isolator on the high-side power supply unit
(there's a Maxim one that I've got but not tried yet) 

Connecting I2C:
The PSUs output i2c nominally pulled up to 5v but in practice the pullups are extremely weak so it should be ok to connect them
directly to 3.3v MCU (e.g. linux Single Board Computer; Raspberry Pi; I used a BananaPi) - a tiny amount of current will flow through the input protection diodes
on the SBC and will pull it down to 3.3v; this should not be a problem. The I2C should work fine.

Just connect GND, SCL and SDA to the power supply (pins 30,31,32 on the PSU).
The PSU has two I2C devices inside; one a 24C02 EEPROM (not very interesting, just contains product ID information) and a PIC;

The PSU's I2C address is set with pins 27,28,29 (default to 1's); if you pull these down to GND the EEPROM will be on address 
0x50 and the PIC will be at 0x58;  (if the address lines are left as 1's the EEPROM will be 0x57 and the PIC will be at 0x5F)

The PSU will respond on I2C as long as it's physically plugged in (the main 12v output doesn't have to be turned on)


Note about register values from the PSU:
a) The Current Out value is not very accurate at a few amps output power (not surprisingly, it has to go up to 100A!)
b) The Voltage Out (below) has a scaling factor of 254.5 (which should pretty obviously be 256) but for some reason my unit needs it fudged to match measured voltages.
   This is more surprising as you'd expect it to have pretty accurate ADC of the output voltage, but that's what I found on my unit so far. YMMV.
c) Hence the "WattsOut" at low power levels (which is just the result of the PSU doing an internal multiply of the voltage/current values) can seem a little strange when you 
   compare input/output watts. I have not tested higher power levels yet but I expect things will be more accurate at e.g. >10A output.
d) To test higher power levels you will be wanting some high-power resistors, probably in a bucket of water :-)


This info/code (for what it's worth) is released under the MIT license.


Please credit DrTune (DrTune) if you use this information, and email me and let me know, I'm interested! :-)

NOTE that the PIC firmware image (and the disassembly) will be copyright Delta (who made the PSU) - I doubt
they mind (they migrated to using dsPIC CPUs in later model PSUs, so this is pretty ancient history).
Thanks Delta for not code-protecting the PIC, btw.

Disassembly notes
a) IDA was set up for PIC16F877 which is slightly different to the 16F886 actually used; I notice
some of the ADC control bits are slightly different and hence are annoted incorrectly in the disassembly. Most stuff appears to be accurate though.
b) They use only two IRQ sources; a Timer (which I think runs at a couple of Khz) and the I2C interrupt.
c) A fair amount of stuff is guessed, that's how it goes with RE'ing; I had to stop at some point. I would like to
get I2C on/off of the output but so far have managed it. I do know how the PIC turns on/off power (look for comments) but i've not found
a path to do that using I2C writes.  
d) If you have IDA Pro and would like my IDA database file, email me.


Cheers, that was fun. 
DrTune/March 2017

"""

import time

import BananaPiI2CPort  #<<< you won't have this (is a custom class for my hacked kernel) - use SMBus instead! I will do this when I have a sec but it should be easy
#import smbus  #<<You want to use this - convert the i2c.read and i2c.write to match


class PowerSupply(object):
    def __init__(self,address):  #address 0..7 reflecting the i2c address select bits on the PSU edge connector
        self.i2c = BananaPiI2CPort.BananaPiI2CPort()    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
        self.address=0x58
        self.EEaddress=0x50+address

        self.numReg=0x58/2
        self.lastReg=[0 for n in range(self.numReg)]
        self.minReg=[0xffff for n in range(self.numReg)]
        self.maxReg=[0 for n in range(self.numReg)]
        

    #not very interesting - read the 24c02 eeprom (you can write it too)
    def readEEPROM(self):
        data=self.i2c.read(self.EEaddress,0,255)
        print data
        print "%s" % (" ".join([ "%02x" % ord(d) for d in data]) )

    #the most useful
    def readDPS1200(self,reg,count):
        cs=reg+(self.address<<1)
        regCS=((0xff-cs)+1)&0xff  #this is the 'secret sauce' - if you don't add the checksum byte when reading a register the PSU will play dumb
        #checksum is [ i2c_address, reg_address, checksum ] where checksum is as above.
        writeInts=[reg,regCS]   #send register # plus checksum
        #this should write [address,register,checksum] and then read two bytes (send address+read bit, read lsb,read msb)
        #note this device doesn't require you to use a "repeated start" I2C condition - you can just do start/write/stop;start/read/stop
        return self.i2c.readVar(self.address,writeInts,count)
    
    #  Writable registers/cmds:
    # Nothing very interesting discovered so far; you can control the fan speed. Not yet discovered how to turn 
    # the 12v output on/off in software.
    #
    # Random notes below:
    #
    #"interesting" write cmds;
    #0x35  (if msb+lsb==0 clear c4+c5)
    #
    #0x3b - checks bit 5 of lsb of write data, if set does (stuff), if bit 6 set does (other stuff), low 5 bits
    #stored @ 0xc8 (read with 0x3a)  
    #        b0..2= 1=(see 0x344); sets 'fan_related' to 9000
    #               2=(see 0x190a) sets 'surprise_more_flags bit 6'
    #        b3= 
    #        b4=
    #        b5=
    #        b6=
    #
    #..cmds that write to ram..
    #0x31 - if data=0 sets i2c_flags1 2 & 7 (0x2d8) = resets total_watts and uptime_secs
    #0x33 - if data=0 resets MaxInputWatts
    #0x35 - if data=0 resets MaxInputCurrent
    #0x37 - if data=0 resets MaxRecordedCurrent
    #0x3b - sets yet_more_flags:5, checks write data lsb:5
    #0x3d - something like set min fan speed
    #0x40  (writes 0xe5) 
    #0x41  (writes 0xd4)   <<d4= fan speed control - write 0x4000 to 0x40 = full speed fan (sets 'surprise_mnore_flags:5)')
    #0x45  sets some voltage threshold if written  (sets a4:1)
    #0x47  sets some other threshhold when written (sets a4:2) -
    #0x49  sets a4:3
    #0x4b  sets a4:4
    #50/51  (writes 0xee/ef) - default is 3200 
    #52/53 (0xa5/6) - some temp threshold 
    #54/55 (0xa7/8)  (sets some_major_flags:5) - eeprom related
    #56/57 (0xa9/a)  (a9 is EEPROM read address with cmd 57)


    def writeDPS1200(self,reg,value):
        valLSB=value&0xff
        valMSB=value>>8
        cs=(self.address<<1)+reg+valLSB+valMSB
        regCS=((0xff-cs)+1)&0xff
        #the checksum is the 'secret sauce'
        writeInts=[reg,valLSB,valMSB,regCS]  #write these 4 bytes to i2c
        bytes="".join([chr(n) for n in writeInts])
        return self.i2c.writeVar(self.address, bytes)  #<<Fix to work with smbus
        
    def testWrite(self):
        value=0
        #try fuzzing things to see if we can find power on/off.. (not yet) 0x40 controls fan speed (bitfield)
        #for n in [0x35,0x3b,0x40,0x50,0x52,0x54,0x56]:
        for n in [0x35,0x3b,0x50,0x52,0x54,0x56]:
        #for n in [0x40]:
            for b in range(16):
                value=(1<<b)-1
                print "%02x : %04x" % (n,value)
                self.writeDPS1200(n,value)
                time.sleep(0.5)

    #Readable registers - some of these are slightly guessed - comments welcome if you figure something new out or have a correction.
    REGS={
        #note when looking at PIC disasm table; "lookup_ram_to_read_for_cmd", below numbers are <<1
        #the second arg is the scale factor
        0x01:["FLAGS",0],           #not sure but includes e.g. "power good"
        0x04:["INPUT_VOLTAGE",32.0], #e.g. 120 (volts)
        0x05:["AMPS_IN",128.0],
        0x06:["WATTS_IN",2.0],
        0x07:["OUTPUT_VOLTAGE",254.5], #pretty sure this is right; unclear why scale is /254.5 not /256 but it's wrong - can't see how they'd not be measuring this to high precision
        0x08:["AMPS_OUT",128.0],  #rather inaccurate at low output <10A (reads under) - appears to have internal load for stability so always reads about 1.5 even open circuit
        0x09:["WATTS_OUT",2.0],
        0x0d:["TEMP1_INTAKE_FARENHEIT",32.0],   # this is a guess - may be C or F but F looks more right
        0x0e:["TEMP2_INTERNAL_FARENHEIT",32.0], 
        0x0f:["FAN_SPEED_RPM",1], #total guess at scale but this is def fan speed it may be counting ticks from the fan sensor which seem to be typically 2 ticks/revolution
        0x1a:["?flags",0],                      #unknown (from disassembly)
        0x1b:["?voltage",1],                    #unknown (from disassembly)
        (0x2c>>1):["WATT_SECONDS_IN",-4.0], #this is a special case; uses two consecutive regs to make a 32-bit value (the minus scale factor is a flag for that)
        (0x30>>1):["ON_SECONDS",2.0],
        (0x32>>1):["PEAK_WATTS_IN",2.0],
        (0x34>>1):["MIN_AMPS_IN",128.0],
        (0x36>>1):["PEAK_AMPS_OUT",128.0],
        (0x3A>>1):["COOL_FLAGS1",0],             #unknown (from disassembly)
        (0x3c>>1):["COOL_FLAGS2",0],             #unknown (from disassembly)
        (0x40>>1):["FAN_SOMETHING",1],          #unknown (from disassembly)
        (0x44>>1):["VOLTAGE_THRESHOLD_1",1],    #unknown (from disassembly)
        (0x46>>1):["VOLTAGE_THRESHOLD_2",1],    #unknown (from disassembly)
        #reading 0x57 reads internal EEPROM space in CPU (just logging info, e.g. hours in use)
        }

    def readDPS1200Register(self,reg):
        data=self.readDPS1200(reg<<1,3)  #if low bit set returns zeros (so use even # cmds)
        #check checksum (why not)
        replyCS=0
        for d in data:
            replyCS+=ord(d)
        replyCS=((0xff-replyCS)+1)&0xff  #check reply checksum (not really reqd)
        if replyCS!=0:
            raise Exception("Read error")
        data=data[:-1]
        value=ord(data[0]) | ord(data[1])<<8
        return value


    def read(self):
        for n in range(self.numReg):
            try:
                value=self.readDPS1200Register(n)
                self.minReg[n]=min(self.minReg[n],value)
                self.maxReg[n]=max(self.maxReg[n],value)
                name=""
                if n in self.REGS:
                    name,scale=self.REGS[n]
                    if scale<0:
                        scale=-scale
                        value+=self.readDPS1200Register(n+1)<<16
                else:
                    scale=1
                print "%02x\t%04x\t" % (n<<1,value ),
                if scale:
                    print "%d\t%d\t%d\t(%d)\t%.3f\t%s" % (value,self.minReg[n],self.maxReg[n],self.maxReg[n]-self.minReg[n],value/scale,name )
                else:
                    print "%s\t%s" % (bin(value),name)
            except Exception,ex:
                print "r %02x er %s" % (n,ex)
        return
        addr=self.address

        

ps=PowerSupply(0)

while True:
    print "\033c" #clear screen
    ps.read()
    time.sleep(0.1)
    #ps.testWrite()
#ps.write()


