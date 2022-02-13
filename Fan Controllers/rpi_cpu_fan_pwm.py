@service # so we can start it as a service
@time_trigger # start it automatically after a boot or (re)load

def run_fan():
     '''
    This program controls a PWM capable Fan.
  
    I use the fan that is an option for the RPi-4 enclosure, an 18mm ADDA with the
    partnumber AD0205DX-K59. It has three leads, VCC(red), GND(black) and 
    the PWM input (blue) 
    The required GPIO pin to drive the PWM signal can be any free pin, but I used
    the GPIO-17 pin. The Fan will not run below a PWM of 20.

    This script will start at boot/restart time of HA, and will run forever unless
    reloaded with a newer version or a touch. There are no HA GUI elements.
    I do have a sensor card activated in HA so I can monitor the cpu temperature 
    over time.

    The fan will always run at the minimum speed. When the cpu reaches 70 degrees, 
    the fan will run at max speed.

    To make the PWM related to the temperature, strip the actual temp from the
    cool baseline, multiply the delta with 3 and add that to the the baseline
    PWM to get 100% at 70 degrees.

    I have selected a PWM frequency of 8KHz. This is the maximum because the pigpiod
    is invoked by default which is with the 5us sample speed. You can't seem to add options
    with the invocation.
    '''
    log.info(f"pyscript: starting run_fan")
    task.unique("run_fan") # make sure we only have one instance running.

    import subprocess
    import shlex
    import os

    try:
        import pigpio  # pigpio library http://abyz.me.uk/rpi/pigpio/index.html
    except ImportError:
        log.info("Python module pigpio not found, installing...")
        cmd = "pip3 install pigpio"
        args = shlex.split(cmd)
        output, error = subprocess.Popen(args, stdout = subprocess.PIPE, \
                        stderr= subprocess.PIPE).communicate()
        import pigpio

    DEBUG = False

    '''
    Using one of the pulled-up GPIO pins will force the fan speed at maximum until this
    script starts to execute. Keep that in mind. Otherwise, select a universal GPIO pin 
    like GPIO-17.
    Because we use software PWM, you can use any of the GPIO pins.
    '''
    FAN_PIN = 17 # GPIO 17 : using software PWM, it can be any GPIO pin
   
    #create instance of pigpio class
    '''
    Make sure you install the pigpio daemon first from the HACS add-on store
    If it's not there, it may crash the HA GUI (happened to me)
    If that happens, put a # in front of the filename so it will no longer start
    '''
    try:
        pi = pigpio.pi()
        if not pi.connected:
            log.info("Required pigpio daemon is not running...") 
            log.info("Add this integration from the add-on store - exiting...")
            exit()
    except: # see if we can gracefully exit without crashing the HA GUI
        if DEBUG: log.info(f"Exception : found no pigpiod")
        exit()

    pigpio.exceptions = True # can be turned off (set to False) after testing
    pi.set_mode(FAN_PIN, pigpio.OUTPUT)
    
    pi.set_PWM_frequency(FAN_PIN, 8000) # the maximum with the standard deamon setting
    pi.set_PWM_range(FAN_PIN, 100) # maximum range= 100 if you find this too loud, reduce it
    log.info(f"fan pwm frequency : {pi.get_PWM_frequency(FAN_PIN)}" ) # report the set frequency
    if DEBUG: log.info(f"kick-start the fan for 2 seconds" ) # so we know it works
    pi.set_PWM_dutycycle(FAN_PIN, 70)
    task.sleep(2) # run it for 2 seconds

    cool_baseline = 55      # start force cooling from this temp in Celcius onwards
    pwm_baseline = 20       # lowest PWM to keep the fan running without stalling
    factor = 3              # multiplication factor

    try:
        while True:
            # get the cpu temperature
            # With Pyscript, it's better to avoid a file open because it is a blocking event.
            # So do not use this: cat /sys/class/thermal/thermal_zone0/temp
            # I'm using another method to get the cpu temperature
            # You need to use the full path otherwise root cannot find the command 
            # with some versions of RPiOS, you need to use the following command
            # cmd = "/usr/bin/vcgencmd measure_temp"  
            cmd = "/opt/vc/bin/vcgencmd measure_temp"
            args = shlex.split(cmd)
            output, error = subprocess.Popen(args, stdout = subprocess.PIPE, \
                            stderr= subprocess.PIPE).communicate()
            # strip the temperature out of the returned string
            # the returned string is in the form : b"temp=43.9'C\n"
            # if your localization is using Farenheit, you need to change the stripping
            # remove the comment below to see what is returned
            #if DEBUG: log.info(f"output : {output}")
            cpu_temp =float(output[5:9]) # stripping for Celcius

            if cpu_temp < cool_baseline :
                pi.set_PWM_dutycycle(FAN_PIN, 20) # lowest speed

            if cpu_temp > cool_baseline :
                duty_cycle = round(((cpu_temp-cool_baseline)*factor)+pwm_baseline, None)
                if DEBUG: log.info(f"cpu temp : {cpu_temp}  duty_cycle : {duty_cycle}")
                pi.set_PWM_dutycycle(FAN_PIN, duty_cycle) # update the pwm value for the fan
            # test the temperature every 30 seconds
            task.sleep(30) # task.sleep is needed instead of time.sleep() which is a blocking call

    except: # just in case...
        if DEBUG: log.info(f"Exception : except")
        pass
    finally:
        log.info(f"rpi_cpu_fan.py terminating")
        pi.stop()  # release the pigpio resources

