@service # so we can start it as a service
@time_trigger

def run():
    task.unique("rpi_cpu_fan_test_pigpio") # make sure we only have one instance running.
    '''
    This program controls a Fan by using PWM.
    The Fan will probably not work below 40% dutycycle, so that is the
    fan PWM baseline. The maximum PWM cannot be more than 100%.

    When the cpu temperature is above 50 'C, we will start to cool.
    When the cpu reaches 70 degrees, we would like to run the fan at max speed.

    To make the PWM related to the temperature, strip the actual temp from the
    cool baseline, multiply the delta with 3 and add that to the the baseline
    PWM to get 100% at 70 degrees.

    I have selected a PWM frequency of 100Hz to avoid high frequency noise, but
    you can change that.
    '''
    log.info(f"piscripter: starting run_fan_test_pigpio")

    import subprocess
    import shlex
    import os
    import time # for testing with sleep()

    # http://abyz.me.uk/rpi/pigpio/index.html
    try:
        import pigpio  # pigpio library
    except ImportError:
        log.info("Python module pigpio not found, installing...")
        cmd = "pip install pigpio"
        args = shlex.split(cmd)
        output, error = subprocess.Popen(args, stdout = subprocess.PIPE, \
                        stderr= subprocess.PIPE).communicate()
        import pigpio

    DEBUG = True

    FAN_PIN = 17 # GPIO-17

    #create instance of pigpio class
    pi = pigpio.pi()
    if not pi.connected:
        log.info("pigpio daemon not running...") 
        os.system("pigpiod")
        task.sleep(1)
        pi = pigpio.pi()

    pigpio.exceptions = True # tip from Joan
    pi.set_mode(FAN_PIN, pigpio.OUTPUT)
       # fatal exceptions back on
    pigpio.exceptions = True
    
    pi.set_PWM_frequency(FAN_PIN,100000) # 8000
    pi.set_PWM_range(FAN_PIN, 100)
    log.info(f"frequency : {pi.get_PWM_frequency(4)}" )

    '''
    # Here is a bit of a kludge. When a new instance of this script is started, HA will terminate the running instance.
    # However, because we use the task.sleep() function, it will only terminate the running process when that has passed.
    # In the meantime, this script will have started, but the GPIO ports are still assigned at that point.
    # The kludge is to try to assign it after we initiated the GPIO with setup, catch the exception,
    # and try it again. (you can't just use GPIO(cleanup) before actually using it)
    try:
        Fan = GPIO.PWM(FAN_PIN, 100)    # create object Fan for PWM on port 17 at 100 Hertz
    except:
        log.info("GPIO exception - port still in use, trying again...")
        GPIO.cleanup()  # release the used port(s)
        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(FAN_PIN, GPIO.OUT)
        Fan = GPIO.PWM(FAN_PIN, 100)
    '''

    log.info("starting with pwm 0...")
    pi.set_PWM_dutycycle(FAN_PIN, 0) # PWM off   # start Fan with 0 percent duty cycle (off)
    #GPIO.output(FAN_PIN, 0) # use this to test the "normal" GPIO functionality

    try: # have to use a try-except to catch the termination by HA.
        while True:
            
            #GPIO.output(FAN_PIN, 0) # use this to test the "normal" GPIO functionality
            log.info("pwm 80...")
            pi.set_PWM_dutycycle(FAN_PIN, 80)   # output the pwm 
            task.sleep(10) # task.sleep is needed instead of time.sleep() which is a blocking call
            #time.sleep(15) # testing with a blocking call
            #GPIO.output(FAN_PIN, 1) # use this to test the "normal" GPIO functionality
            log.info("pwm 40...")
            pi.set_PWM_dutycycle(FAN_PIN, 40)   # output the pwm
            #time.sleep(15) # testing with a blocking call
            task.sleep(10)


    except: # just in case...
        log.info(f"Exception : except")
    finally:
        log.info(f"terminating")
        pi.stop()  # release the pigpio resources

