"""
Copyright (c) 2023 Tom Kalmijn / MIT License.
"""
from typing import Any, Dict

import kelvin_rgb
from ColorConverter import Converter, XYPoint
from DmxFixture import DmxFixture


class AdjSaberSpotRGBW(DmxFixture):
    kelvin_white_led = 5000

    def get_dmx_message(self, hue_light_info: Dict[str, Any]) -> bytes:

        if not 'on' in hue_light_info or not hue_light_info['on']['on']:
            return bytes([0, 0, 0, 0])

        dim_factor = hue_light_info['dimming']['brightness'] / 100 if 'dimming' in hue_light_info else 1.0

        if hue_light_info['color']['gamut_type'] == 'other':
            raise Exception(f"No gamut info for {self.name}, tracking Hue lamp {self.hue_light_id}")

        gamut = (
            XYPoint(hue_light_info['color']['gamut']['red']['x'], hue_light_info['color']['gamut']['red']['y']),
            XYPoint(hue_light_info['color']['gamut']['green']['x'], hue_light_info['color']['gamut']['green']['y']),
            XYPoint(hue_light_info['color']['gamut']['blue']['x'], hue_light_info['color']['gamut']['blue']['y']),
        )
        x = hue_light_info['color']['xy']['x']
        y = hue_light_info['color']['xy']['y']

        # convert Hue gamut coordinates to r g b
        color_converter = Converter(gamut)
        r, g, b = color_converter.xy_to_rgb(x, y)

        # apply dimming level
        r, g, b = r * dim_factor, g * dim_factor, b * dim_factor

        # convert to rgbw
        (r, g, b, w) = self.rgb_to_rgbw(r, g, b)
        return bytes([r, g, b, w])

    def rgb_to_rgbw(self, r, g, b):
        k_white_red = kelvin_rgb.kelvin_table[self.kelvin_white_led][0]
        k_white_green = kelvin_rgb.kelvin_table[self.kelvin_white_led][1]
        k_white_blue = kelvin_rgb.kelvin_table[self.kelvin_white_led][2]

        white_value_for_red = r * 255.0 / k_white_red
        white_value_for_green = g * 255.0 / k_white_green
        white_value_for_blue = b * 255.0 / k_white_blue

        white = min(white_value_for_red, white_value_for_green, white_value_for_blue)
        white = white if white <= 255 else 255

        red = int(r - white * k_white_red / 255)
        green = int(g - white * k_white_green / 255)
        blue = int(b - white * k_white_blue / 255)

        return red, green, blue, int(white)
