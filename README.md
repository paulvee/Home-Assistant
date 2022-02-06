# Home-Assistant
Information and scripts for Home Assistent

This is using the HACS/Pyscript add-in to test things out.
It provides an almost full Python envorinment that can be used together with the Home Assistant environment.

https://github.com/custom-components/pyscript
I used the GUI install, first HACS, then Pyscript.
There is nothing added to my configuration.yaml.

I created a folder in config with the name pyscript and put all the related files in there.

Most of what I found and needed to do is listed as comments in the code.

There are two test scripts, one for RPi.GPIO, that does not support PWM but otherwise works, and one script for the pigpio library that does support PWM.
I also added my own script (rpi_cpu_fan.py) that I am using now and is fully working using the pigpio library.

