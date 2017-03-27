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

