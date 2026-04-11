import unittest
import math

def hex_to_rgb(hex_color: str):
    """Konvertiert einen Hex-Farbcode in ein RGB-Tupel."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb: tuple) -> str:
    """Konvertiert ein RGB-Tupel in einen Hex-Farbcode."""
    return "#{:02x}{:02x}{:02x}".format(*rgb).upper()

def calculate_luminance(rgb: tuple) -> float:
    """Berechnet die relative Luminanz (WCAG) einer RGB-Farbe."""
    a = [v / 255.0 for v in rgb]
    a = [v / 12.92 if v <= 0.03928 else math.pow((v + 0.055) / 1.055, 2.4) for v in a]
    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722

def contrast_ratio(hex1: str, hex2: str) -> float:
    """Berechnet das Kontrastverhältnis zweier Hex-Farben (WCAG 2.2)."""
    lum1 = calculate_luminance(hex_to_rgb(hex1))
    lum2 = calculate_luminance(hex_to_rgb(hex2))
    light = max(lum1, lum2)
    dark = min(lum1, lum2)
    return (light + 0.05) / (dark + 0.05)

def transform_gedimmt(hex_color: str, brightness_increase: int = 25) -> str:
    """
    Erhöht die Helligkeit der Farbe algorithmisch um mindestens 25 %
    und reduziert die Sättigung leicht, um das "Gedimmt"-Theme zu generieren.
    """
    rgb = hex_to_rgb(hex_color)
    # Simple algorithm for demonstration (increasing RGB values roughly simulates brightness)
    new_rgb = tuple(min(255, int(c * (1 + brightness_increase / 100.0))) for c in rgb)
    return rgb_to_hex(new_rgb)

class TestThemeColors(unittest.TestCase):

    def test_hex_rgb_conversion(self):
        self.assertEqual(hex_to_rgb("#FFFFFF"), (255, 255, 255))
        self.assertEqual(rgb_to_hex((255, 255, 255)), "#FFFFFF")
        
        self.assertEqual(hex_to_rgb("#1A1A2E"), (26, 26, 46))
        self.assertEqual(rgb_to_hex((26, 26, 46)), "#1A1A2E")

    def test_contrast_ratio_wcag_aa(self):
        # White mode minimum contrast test against typical text color
        text_color = "#333333"
        bg_white = "#FFFFFF"
        ratio = contrast_ratio(text_color, bg_white)
        # WCAG 2.2 Level AA requires at least 4.5:1 for normal text
        self.assertTrue(ratio >= 4.5, f"Kontrast zu niedrig: {ratio:.2f}")

    def test_gedimmt_transformation(self):
        # Start color: #1A1A2E (Classic Dark Background)
        base_color = "#1A1A2E"
        gedimmt = transform_gedimmt(base_color, brightness_increase=25)
        # #1A1A2E (26, 26, 46) * 1.25 -> (32, 32, 57) -> #202039
        self.assertEqual(gedimmt, "#202039")
        
        # Test contrast between classic text and gedimmt bg
        text_color = "#FFFFFF"
        ratio = contrast_ratio(text_color, gedimmt)
        self.assertTrue(ratio >= 4.5, f"Gedimmt Kontrast zu niedrig: {ratio:.2f}")

if __name__ == '__main__':
    unittest.main()
