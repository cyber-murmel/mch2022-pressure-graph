from time import ticks_ms, sleep
from math import log, ceil, floor
from bme680.bme680 import BME680_I2C
from mch22 import exit_python
from machine import SoftI2C, Pin
import display
import buttons

bme = BME680_I2C(SoftI2C(scl=Pin(21), sda=Pin(22)))

BACKGROUND = 0x491D88
PALETTE_0 = 0xFEC859
PALETTE_1 = 0xFA448C
PALETTE_2 = 0x331A38
PALETTE_3 = 0x43B5A0

IIR_FILTER_TIME_S = 5


def round_res(num, res):
    return round(num / res) * res


def floor_res(num, res):
    return floor(num / res) * res


def ceil_res(num, res):
    return ceil(num / res) * res


def map_vals_fn(in_min, in_max, out_min, out_max):
    scaleFactor = float(out_max - out_min) / float(in_max - in_min)

    def map_vals(value):
        return out_min + (value - in_min) * scaleFactor

    return map_vals


def draw_samples(
    samples,
    x_min=0,
    x_max=display.width(),
    y_min=0,
    y_max=display.height(),
    padding=0.05,
    grid=True,
    n_grid=5,
):
    keys, values = list(zip(*samples))

    min_key = min(keys)
    max_key = max(keys)
    min_value = min(values)
    max_value = max(values)

    width = x_max - x_min
    height = y_max - y_min

    x_map_fn = map_vals_fn(
        min_key, max_key, x_min + padding * width, x_min + (1 - padding) * width
    )
    y_map_fn = map_vals_fn(
        max_value,
        min_value,
        x_min + padding * height,
        x_min + (1 - padding) * height,
    )

    xs = map(int, map(x_map_fn, keys))
    ys = map(int, map(y_map_fn, values))

    nodes = list(zip(xs, ys))

    if grid:
        key_res = 10 ** round(log(max_key - min_key, 10)) / n_grid
        value_res = 10 ** round(log(max_value - min_value, 10)) / n_grid

        min_key_grid = round_res(min_key, key_res)
        min_value_grid = round_res(min_value, value_res)

        n_key_grids = ceil((max_key - min_key_grid) / key_res + 0.5)
        n_value_grids = ceil((max_value - min_value_grid) / value_res + 0.5)

        for x_grid_idx in range(n_key_grids):
            x = x_map_fn(min_key_grid + x_grid_idx * key_res)
            display.drawLine(x, y_min, x, y_max, PALETTE_2)

        for y_grid_idx in range(n_value_grids):
            y = y_map_fn(min_value_grid + y_grid_idx * value_res)
            display.drawLine(x_min, y, x_max, y, PALETTE_2)

    for idx in range(len(nodes) - 1):
        display.drawLine(
            nodes[idx][0],
            nodes[idx][1],
            nodes[idx + 1][0],
            nodes[idx + 1][1],
            PALETTE_3,
        )


delay_s = 1 / 64
samples = [(ticks_ms(), bme.pressure)]

while not buttons.value(buttons.BTN_HOME):
    display.drawFill(BACKGROUND)

    current_ticks_ms = ticks_ms()
    current_pressure = bme.pressure
    diff_ticks_ms = current_ticks_ms - samples[-1][0]

    # apply simple IIR filtering
    # use 1/5 of IIR_FILTER_TIME_S, as 97% of signal level will then be achieve within IIR_FILTER_TIME_S
    alpha = (diff_ticks_ms) / ((diff_ticks_ms) + IIR_FILTER_TIME_S * 10 ** 3 / 5)

    fitered_presure = samples[-1][1] + alpha * (current_pressure - samples[-1][1])

    samples.append((current_ticks_ms, fitered_presure))
    draw_samples(samples, y_max=display.height() * 4 // 5)

    display.drawText(
        display.width() // 20,
        display.height() * 19 // 20 - 18,
        "{} mbar".format(current_pressure),
        PALETTE_3,
        "roboto_regular18",
    )

    display.flush()

    sleep(delay_s)

    # if screen is full, half number of stored samples and double delay time
    if len(samples) > (display.width() / 3):
        samples = samples[::2]
        delay_s = delay_s * 2

exit_python()
