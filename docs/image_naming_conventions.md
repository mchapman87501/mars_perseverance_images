# How are Perseverance images named?

So far I've looked only at Navcam images.  Here are some example Navcam image IDs:

* NRB_0002_0667129587_774ECM_N0010052AUT_04096_00_2I3J01
* NRE_0002_0667130259_241ECM_N0010052AUT_04096_00_0LLJ01
* NRG_0001_0667035548_700ECM_N0010052AUT_04096_00_2I3J01
* NRM_0002_0667130166_842ECM_T0010052AUT_04096_00_4I1J01
* NRR_0001_0667035529_850ECM_N0010052AUT_04096_00_2I3J01

I think the leading "N" stands for "Navcam".

The next character, "R" or "L", may stand for "left" or "right".

The next character seems to indicate the type of image data: "R" for "Red", "G" for "Green", "B" for "Blue", "M" for "thumbnail" (I think).

Per [Emily Lakdawalla](https://twitter.com/elakdawalla), "E" images are readouts of the full detector, which has a Bayer filter on it.  For more information she recommends "[Explaining the new black-and-white Mastcam and MARDI raw images](https://t.co/PORiQ3pcNq?amp=1)".  This was written about Curiosity cameras, but the information applies to Perseverance as well.

Also see "[The Mastcam-Z Filter Set: How Perseverance Will See the Colors of Mars](https://mastcamz.asu.edu/the-mastcam-z-filter-set-how-perseverance-will-see-the-colors-of-mars/)".

The subsequent four digit number may indicate mission date -- sol.

That's enough guessing for now...

## Details of the Imaging System

A description of the cameras on the Perseverance Rover is available from ResearchGate: [The Mars 2020 Engineering Cameras and Microphone on the Perseverance Rover: A Next-Generation Imaging System for Mars Exploration](https://www.researchgate.net/publication/346537343_The_Mars_2020_Engineering_Cameras_and_Microphone_on_the_Perseverance_Rover_A_Next-Generation_Imaging_System_for_Mars_Exploration/link/5fc675c9a6fdcc92169e4d1e/download).

> The Mars 2020 Navcams and Hazcams offer three primary improvements over MER and MSL. The ﬁrst improvement is an upgrade to a detector with 3-channel, red/green/blue (RGB) color capability...

> Color Filters: RGB Bayer color ﬁlter array (CFA)

Hm, it should be possible to build stereo images:
> The Navcams have a 42.4 cm stereo baseline.
