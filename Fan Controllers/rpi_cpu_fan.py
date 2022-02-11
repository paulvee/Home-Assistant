@service # so we can start it as a service
@time_trigger # start it automatically after a boot or (re)load

def run_fan():
    '''
    This program controls a Fan by using PWM.
    The Fan will probably not work with a small dutycycle, so I use the
    fan PWM baseline that I experimented with. I use a 3-wire 40mm 5V Noctua fan,
    and it stalls with a pwm below 20. The positive lead of the fan is 
    connected to 5V. The GPIO pin is going to the Base of a transistor and that drives
    the negative power lead of the fan. I use my own developed "hat" PCB.

    This script will start at boot/restart time of HA, and will run forever unless
    reloaded with a newer version or a touch. There are no HA GUI elements.
    I do have a sensor card activated in HA so I can monitor the cpu temperature 
    over time.

    The fan will always run, but we'll start to force cooling above 50 degrees C.
    When the cpu reaches 70 degrees, the fan will run at max speed.

    To make the PWM related to the temperature, strip the actual temp from the
    cool baseline, multiply the delta with 3 and add that to the the baseline
    PWM to get 100% at 70 degrees.

    I have selected a PWM frequency of 1000Hz to avoid low frequency noise, but
    you can change that.
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
        cmd = "pip install pigpio" # may have to use pip3
        args = shlex.split(cmd)
        output, error = subprocess.Popen(args, stdout = subprocess.PIPE, \
                        stderr= subprocess.PIPE).communicate()
        import pigpio

    DEBUG = True

    FAN_PIN = 17 # GPIO 17 : using software PWM, it can be any GPIO pin
   
    #create instance of pigpio class
    pi = pigpio.pi()
    if not pi.connected:
        log.info("pigpio daemon not running...") 
        os.system("pigpiod") # start the daemon
        task.sleep(1) # give it some time and try again
        pi = pigpio.pi()

    pigpio.exceptions = True # can be turned off (set to False) after testing
    pi.set_mode(FAN_PIN, pigpio.OUTPUT)
    
    pi.set_PWM_frequency(FAN_PIN,10000) # 8,000Hz
    pi.set_PWM_range(FAN_PIN, 100) # set the maximum range to 100
    if DEBUG: log.info(f"frequency : {pi.get_PWM_frequency(FAN_PIN)}" ) # report the set frequency
    if DEBUG: log.info(f"kick-start the fan for 2 seconds" ) # so we know it works
    pi.set_PWM_dutycycle(FAN_PIN, 80)
    task.sleep(2) # run it for 2 seconds

    cool_baseline = 50      # start force cooling from this temp in Celcius onwards
    pwm_baseline = 20       # lowest PWM to keep the fan running without stalling
    factor = 3              # multiplication factor
    max_pwm = 100           # maximum PWM value

    try:
        while True:
            # get the cpu temperature
            # With Pyscript, it's better to avoid a file open because it is a blocking event.
            # So do not use this: cat /sys/class/thermal/thermal_zone0/temp
            # I'm using another method to get the cpu temperature
            # You need to use the full path otherwise root cannot find the command   
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
            if DEBUG: log.info(f"cpu temp : {cpu_temp}")

            if cpu_temp < cool_baseline :
                pi.set_PWM_dutycycle(FAN_PIN, 20) # lowest speed

            if cpu_temp > cool_baseline :
                duty_cycle = round(((cpu_temp-cool_baseline)*factor)+pwm_baseline, None)
                if DEBUG: log.info(f"duty_cycle : {duty_cycle}")
                pi.set_PWM_dutycycle(FAN_PIN, duty_cycle) # update the pwm value for the fan
            # test the temperature every 30 seconds
            task.sleep(30) # task.sleep is needed instead of time.sleep() which is a blocking call

    except: # just in case...
        if DEBUG: log.info(f"Exception : except")
        pass
    finally:
        log.info(f"rpi_cpu_fan.py terminating")
        pi.stop()  # release the pigpio resources

