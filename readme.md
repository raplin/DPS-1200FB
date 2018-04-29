# Results of reverse-engineering the PIC microcontroller in the HP DPS-1200FB power supply (made by Delta)

DrTune / March 2017  (drtune@gmail.com)

The DPS-1200FB is a very high-quality (and high power) power supply readily available on EBay and popular with
people who want a LOT of 12v DC power; most commonly R/C hobbyists to power their battery chargers.

It offers 99.9% power factor (due to active PFC), mid-90% efficiency, and 75A (110v) or 100A (240v) output at 12v. *It's a beast* - and it's very small and quiet (unless heavily loaded).

![picture](https://github.com/raplin/DPS-1200FB/raw/master/internal_pic.jpg "Internals picture from an EEVBlog posting")

There are many docs on the net (see links at bottom) about how to;
a) Get the PSU to turn on.
b) Convert two PSUs to run in series providing 24v by floating the GND output from the chassis.

However nobody figured out how to access the internal CPU to read all the useful status/monitoring info.

I opened one up, located the main CPU (a PIC 16F886) and read its code (was not readout protected), then disassembled and commented a lot of it. The goal was to reverse-engineer the I2C protocol, which is largely done.

This code works on a DPS-1200FB A (P/N 438202-002 REV:05F), it will probably work on all revisions of this PSU.

At time of writing this I have not figured out how to turn on/off the PSU output via I2C; this may or may not be possible, although the ENABLE pin is a simple logic-level (active-low) signal that may be driven by a GPIO.

NOTE: If you use two in series and want I2C from both of them you MUST use an I2C isolator on the high-side power supply unit (Maxim sell a suitable chip; I've got but not tried yet)

## Connecting I2C:
The PSUs output i2c nominally pulled up to 5v but in practice the pullups are extremely weak so it should be ok to connect them directly to 3.3v MCU (e.g. linux Single Board Computer; Raspberry Pi; I used a BananaPi) - a tiny amount of current will flow through the input protection diodes on the SBC and will pull it down to 3.3v; this should not be a problem. The I2C should work fine.

Just connect GND, SCL and SDA to the power supply (pins 30,31,32 on the PSU).
The PSU has two I2C devices inside; one a 24C02 EEPROM (not very interesting, just contains product ID information) and a PIC;

The PSU's I2C address is set with pins 27,28,29 (default to 1's); if you pull these down to GND the EEPROM will be on address 0x50 and the PIC will be at 0x58;  (if the address lines are left as 1's the EEPROM will be 0x57 and the PIC will be at 0x5F)

The PSU will respond on I2C as long as it's physically plugged in (the main 12v output doesn't have to be turned on)


## Note about register values from the PSU:
a) The Current Out value is not very accurate at a few amps output power (not surprisingly, it has to go up to 100A!) There may well be an internal dummy load to keep the PSU stable at low output power.

b) The Voltage Out (below) has a scaling factor of 254.5 (which should pretty obviously be 256) but for some reason my unit needs it fudged to match measured voltages; I do expect /256 to be the right value though. This is more surprising as you'd expect it to have pretty accurate ADC of the output voltage, but that's what I found on my unit so far. YMMV.

c) Hence the "WattsOut" at low power levels (which is just the result of the PSU doing an internal multiply of the voltage/current values) can seem a little strange when you compare input/output watts. I have not tested higher power levels yet but I expect things will be more accurate at e.g. >10A output.

d) To test higher power levels you will be wanting some high-power resistors, probably in a bucket of water :-)

This info/code (for what it's worth) is released under the MIT license.


Please credit DrTune (DrTune) if you use this information, and email me and let me know, I'm interested! :-)

NOTE that the PIC firmware image (and the disassembly) will be copyright Delta (who made the PSU) - I doubt
they mind (they migrated to using dsPIC CPUs in later model PSUs, so this is pretty ancient history).
Thanks Delta for not code-protecting the PIC, btw.

## Disassembly notes:

a) IDA was set up for PIC16F877 which is slightly different to the 16F886 actually used; I notice
some of the ADC control bits are slightly different and hence are annoted incorrectly in the disassembly. Most stuff appears to be accurate though.

b) They use only two IRQ sources; a Timer (which I think runs at a couple of Khz) and the I2C interrupt.

c) A fair amount of stuff is guessed, that's how it goes with RE'ing; I had to stop at some point. I would like to
get I2C on/off of the output but so far have not managed it. I do know how the PIC turns on/off power (look for comments) but i've not found a path to do that using I2C writes.  

d) If you have IDA Pro and would like my IDA database file, email me.


## Other notes:

a) You may be able to find it under several names on EBay; apart from "DPS-1200FB" try the HP part numbers "441830-001", "438202-001", "440785-001", "HSTNS-PD11". It's technically a Proliant DL580 G5 server hot-swappable PSU. I got 2 for $20 each, but the price has gone up a bit as they're exceptionally good PSUs; still (at time of writing; March 2017) readily findable for ~$30. I do not know of a better quality or value high-power 12v PSU.

b) One of the reasons they're so good (apart from the huge power capacity) is that they're very small (about two paperback books; 1U high - stuff is really crammed in there), quiet (at low fan speeds), and very efficient,  with excellent Power Factor Correction. This stuff doesn't come cheap; I think the original price was north of $500 each.  The fan can really get going; it's rated at 18k RPM (you can make it go full speed by writing 0x4000 to register 0x40 as I recall; sounds like a jet engine)

c) It's pretty much impossible to take one of these properly apart nondestructively; everything is soldered in; only one side of the logic controller board (the one that goes along the side of the PSU) is accessible. There is a trimpot on this board that adjusts output voltage between about 11v and 13.8v.  I imagine it may be possible with some hackery to make the output voltage lower (although PSU regulation may become unstable at much lower voltages, plus I expect the PIC firmware may need some hacking to avoid low-voltage-detect kicking in a failure mode and turning off power).  You won't get much higher voltage out of it; the output caps are only rated at 16v. At some point I will look at what can be done to get lower (or even I2C programmable) voltages out; the latter will definitely require adding a chip or two so is advanced modding.

d) SAFETY: If you take one of these apart !BE VERY VERY CAREFUL! This PSU works by taking the mains (110 to 240v), rectifying it, boosting it a little with a dynamically controlled step-up converter (which is the active PFC), and smoothing it to DC with a big, and VERY DANGEROUS capacitor, before chopping that at high speed into a transformer down to 12v and performing synchronous rectification. I haven't checked to see if they bleed this off when you unplug it (I hope so) but you will want to be exceptionally careful not to touch it when the PSU is on or has recently been on; it will have many hundreds of volts (350uF as I recall) on it; will absolutely ruin your day. 

Even if you don't take this apart, you should be cautious when using the DC output of this PSU - it can output 100Amps at 12v - 12v won't hurt you in the slightest if you touch it -BUT- 1.2KW into a short circuit can give you some impressive welding/wire-melting action. Expect big sparks, melted wiring and possibly things catching fire or burning you if you short the output. Apparently this PSU is short-circuit protected (I expect so) but I'm not personally inclined to test that feature, nor should you be.

* IF YOU ARE A NOOB WITH GNARLY POWER SUPPLIES TRY NOT TO LEARN ANYTHING THE HARD WAY. *

e) The PSU uses off the shelf chips except one marked "DNA 1006" on the controller board which the Web knows nothing about at all. It has two CPUs (a Freescale MC68HC908 marked "MC908" on the high side, connected via opto-isolators to the PIC 16F886 on the low side - I suspect the high-side CPU isn't very interesting, I didn't try to read it). It's a complicated beast; stuff like synchronous rectification and active PFC and general "high quality everything" add quite a lot of chippery to this design. The main controller is a TI UCC3895 "Phase-shift PWM controller" that handles the main step-down-to-12v stage. The main barrier to further hacking is simply the difficulty in taking it apart such that it can be reassembled as the inter-board connectors are soldered.


## Websites with more info than I give here (including hookup info)

c1) Mini teardown; http://www.eevblog.com/forum/reviews/teardown-hp-dps-1200fb-12v-100a-psu/

c2) 'Floating' one so you can run two in series to get 24v : basically you just have to replace the two metal screws+standoffs at the rear (connector end) of the PSU with non-conducting (e.g. nylon) versions. This is safe if you do it properly. Example vid: https://www.youtube.com/watch?v=_2QFBE6ZFF0

c3) This guy found a source for the PSU's edge connector if you want one; plus more info (he guesses the PSU uses PMBus protocol, which turns out not to be the case) however he's right about the PRESENT and ENABLE control lines. http://colintd.blogspot.com/search/label/DL580

Cheers, that was fun. 
DrTune/March 2017

