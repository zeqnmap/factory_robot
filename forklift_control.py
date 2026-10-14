"""Control for the forklift lift motor on a dedicated DRV8833 channel."""

from gpiozero import PWMOutputDevice


LIFT_IN1 = PWMOutputDevice(4)
LIFT_IN2 = PWMOutputDevice(18)
LIFT_SPEED = 1.0


def _set_lift(speed: float) -> None:
    """Drive the lift from -1.0 (down) to 1.0 (up); zero stops it."""
    speed = max(-1.0, min(1.0, speed))
    if speed > 0:
        LIFT_IN1.value = speed
        LIFT_IN2.value = 0.0
    elif speed < 0:
        LIFT_IN1.value = 0.0
        LIFT_IN2.value = -speed
    else:
        LIFT_IN1.value = 0.0
        LIFT_IN2.value = 0.0


def lift_up() -> None:
    _set_lift(LIFT_SPEED)


def lift_down() -> None:
    _set_lift(-LIFT_SPEED)


def lift_stop() -> None:
    _set_lift(0.0)
