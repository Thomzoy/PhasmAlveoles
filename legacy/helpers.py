from configuration import PWMS


def reset_pins():
    [pwm.duty(0) for pwm in PWMS]
