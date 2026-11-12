#!/usr/bin/env python3
"""Generate the TeleCat built-in themes.

Material 3: every Telegram color key is resolved through a Material 3 tonal
palette (primary / secondary / tertiary / neutral / neutral variant), keeping the
key-to-role mapping that Telegram ships for Monet, so the whole client moves
together instead of falling back to the legacy blue palette for unmapped keys.

Liquid Glass: the same role mapping, rendered with an iOS system palette. Surface
keys get a translucent treatment so panels, bubbles and bars read as glass over
the chat wallpaper.

Run from the repository root:
    python3 Tools/telecat-themes/generate.py
"""

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEME_JAVA = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/ActionBar/Theme.java"
THEME_COLORS_JAVA = ROOT / "TMessagesProj/src/main/java/org/telegram/ui/ActionBar/ThemeColors.java"
ASSETS = ROOT / "TMessagesProj/src/main/assets"

# Keys that are numbers rather than colors, plus the file-offset sentinel.
NON_COLOR_KEYS = {
    "wallpaperFileOffset",
    "chat_wallpaper_gradient_rotation",
    "chat_BlurAlpha",
    "chat_BlurAlphaSlow",
}

# Seed color: Telegram's own accent, pushed through Material 3 tonal generation.
MATERIAL_SEED = "#3390EC"
GLASS_SEED = "#007AFF"


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    sign = -1.0 if c < 0 else 1.0
    a = abs(c)
    return sign * (a * 12.92 if a <= 0.0031308 else 1.055 * (a ** (1 / 2.4)) - 0.055)


def rgb_to_xyz(r, g, b):
    r, g, b = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    return x, y, z


WHITE = (0.95047, 1.0, 1.08883)


def xyz_to_lab(x, y, z):
    def f(t):
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = f(x / WHITE[0]), f(y / WHITE[1]), f(z / WHITE[2])
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def lab_to_xyz(L, a, b):
    fy = (L + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200

    def finv(t):
        return t ** 3 if t ** 3 > 216 / 24389 else (116 * t - 16) / (24389 / 27)

    return finv(fx) * WHITE[0], finv(fy) * WHITE[1], finv(fz) * WHITE[2]


def xyz_to_rgb(x, y, z):
    r = x * 3.2404542 + y * -1.5371385 + z * -0.4985314
    g = x * -0.9692660 + y * 1.8760108 + z * 0.0415560
    b = x * 0.0556434 + y * -0.2040259 + z * 1.0572252
    return linear_to_srgb(r), linear_to_srgb(g), linear_to_srgb(b)


def lch_to_rgb(L, C, H):
    rad = math.radians(H)
    return xyz_to_rgb(*lab_to_xyz(L, C * math.cos(rad), C * math.sin(rad)))


def in_gamut(L, C, H, eps=0.0005):
    r, g, b = lch_to_rgb(L, C, H)
    return -eps <= min(r, g, b) and max(r, g, b) <= 1 + eps


def max_chroma(L, C, H):
    lo, hi = 0.0, C
    if in_gamut(L, hi, H):
        return hi
    for _ in range(24):
        mid = (lo + hi) / 2
        if in_gamut(L, mid, H):
            lo = mid
        else:
            hi = mid
    return lo


def tone_to_rgb(tone, chroma, hue):
    """Material tone (0 black .. 100 white) as an sRGB triplet."""
    L = min(100.0, max(0.0, tone))
    return lch_to_rgb(L, max_chroma(L, chroma, hue), hue)


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))


def seed_hue(value):
    x, y, z = rgb_to_xyz(*hex_to_rgb(value))
    _, a, b = xyz_to_lab(x, y, z)
    return (math.degrees(math.atan2(b, a)) + 360) % 360


def clamp_byte(v):
    return max(0, min(255, int(round(v))))


def to_argb(rgb, alpha=255, alpha_scale=1.0):
    r, g, b = (clamp_byte(c * 255) for c in rgb)
    a = clamp_byte(alpha * alpha_scale)
    return (a << 24) | (r << 16) | (g << 8) | b


# Android's system_*_N colors are indexed by lightness of the role, not by the
# Material tone: index 0 is white, index 1000 is black. Faithful tone is
# 100 - index / 10.
PALETTE_INDICES = [0, 10, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]


def build_scheme(seed, chroma_primary, chroma_secondary, chroma_tertiary,
                 chroma_neutral, chroma_neutral_variant, tertiary_offset=60,
                 neutral_hue=None, accent_tone_shift=0.0):
    hue = seed_hue(seed)
    n_hue = neutral_hue if neutral_hue is not None else hue
    roles = {
        "a1": (chroma_primary, hue),
        "a2": (chroma_secondary, hue),
        "a3": (chroma_tertiary, (hue + tertiary_offset) % 360),
        "n1": (chroma_neutral, n_hue),
        "n2": (chroma_neutral_variant, n_hue),
    }
    palette = {}
    for role, (chroma, role_hue) in roles.items():
        shift = accent_tone_shift if role.startswith("a") else 0.0
        for idx in PALETTE_INDICES:
            palette[(role, idx)] = tone_to_rgb(100 - idx / 10 + shift, chroma, role_hue)
    return palette


def resolve_token(token, palette, error_rgb):
    if token.startswith("monetRed") or token.startswith("monetGreen"):
        return to_argb(error_rgb)
    match = re.fullmatch(r"([an])([123])_(\d+)(?:_(\d+))?", token)
    if not match:
        return None
    group, role, shade, alpha = match.groups()
    role = ("a" if group == "a" else "n") + role
    idx = int(shade)
    if idx not in PALETTE_INDICES:
        nearest = min(PALETTE_INDICES, key=lambda i: abs(i - idx))
        idx = nearest
    rgb = palette[(role, idx)]
    return to_argb(rgb, int(alpha) if alpha else 255)


def parse_theme_asset(name):
    values = {}
    for line in (ASSETS / name).read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("W"):
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip()
    return values


def load_keys():
    theme = THEME_JAVA.read_text(encoding="utf-8")
    keys = re.findall(r"public static final int key_(\w+)\s*=", theme)
    colors = THEME_COLORS_JAVA.read_text(encoding="utf-8")
    defaults = {}
    for name, raw in re.findall(r"defaultColors\[key_(\w+)\]\s*=\s*(0x[0-9a-fA-F]+|-?\d+)", colors):
        defaults[name] = int(raw, 16) if raw.lower().startswith("0x") else (int(raw) & 0xFFFFFFFF)
    return keys, defaults


def semantic_fallback(key, default_argb, palette):
    """Map a key without a Monet role by its own hue and lightness."""
    alpha = (default_argb >> 24) & 0xFF
    rgb = tuple(((default_argb >> shift) & 0xFF) / 255 for shift in (16, 8, 0))
    x, y, z = rgb_to_xyz(*rgb)
    L, a, b = xyz_to_lab(x, y, z)
    chroma = math.hypot(a, b)
    hue = (math.degrees(math.atan2(b, a)) + 360) % 360
    if chroma < 8:
        role, target_chroma = "n2", 6
    elif 230 <= hue <= 320:
        role, target_chroma = "a1", 36
    elif chroma > 30:
        role, target_chroma = "a3", 30
    else:
        role, target_chroma = "a2", 18
    idx = int(round((100 - L) * 10 / 10)) * 10
    idx = min(PALETTE_INDICES, key=lambda i: abs(i - idx))
    return to_argb(palette[(role, idx)], alpha)


def render(key, source, palette, defaults, error_rgb, overrides):
    if key in NON_COLOR_KEYS:
        return None
    if key in overrides:
        return overrides[key]
    token = source.get(key)
    if token is not None:
        value = resolve_token(token, palette, error_rgb)
        if value is not None:
            return value
    default = defaults.get(key)
    if default is None:
        return None
    return semantic_fallback(key, default, palette)


def write_theme(path, values, note):
    lines = [f"# TeleCat {note}", "# Generated by Tools/telecat-themes/generate.py"]
    # Theme files store ARGB as signed 32-bit ints, like every upstream .attheme.
    lines += [f"{key}={value - 0x100000000 if value > 0x7FFFFFFF else value}"
              for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- schemes -----------------------------------------------------------------

material = build_scheme(MATERIAL_SEED, 46, 16, 24, 4, 8)
glass = build_scheme(GLASS_SEED, 72, 26, 45, 3, 8, tertiary_offset=140, neutral_hue=240,
                     accent_tone_shift=8.5)

material_error = tone_to_rgb(40, 60, 28)
glass_error = hex_to_rgb("#FF3B30")

# Explicit role decisions on top of the shared mapping.
material_light_overrides = {
    "chat_inBubble": to_argb(material[("a2", 100)]),
    "chat_inBubbleSelected": to_argb(material[("a2", 100)]),
    "chat_inFileBackground": to_argb(material[("a2", 100)]),
    "chat_inFileBackgroundSelected": to_argb(material[("a2", 100)]),
    "chat_outBubble": to_argb(material[("a1", 600)]),
    "chat_outBubbleSelected": to_argb(material[("a1", 600)]),
    "chat_outBubbleGradient": to_argb(material[("a1", 600)]),
    "chat_outBubbleGradient2": to_argb(material[("a1", 600)]),
    "chat_outBubbleGradient3": to_argb(material[("a1", 600)]),
    "chat_messageTextOut": to_argb(material[("a1", 0)]),
    "chat_messagePanelHint": to_argb(material[("n2", 600)]),
    "chat_messagePanelText": to_argb(material[("n1", 1000)]),
    "divider": to_argb(material[("n2", 200)]),
    "chat_replyPanelLine": to_argb(material[("n2", 200)]),
    "graySection": to_argb(material[("n1", 100)]),
}
material_dark_overrides = {
    "chat_inBubble": to_argb(material[("a2", 700)]),
    "chat_inBubbleSelected": to_argb(material[("a2", 700)]),
    "chat_inFileBackground": to_argb(material[("a2", 700)]),
    "chat_inFileBackgroundSelected": to_argb(material[("a2", 700)]),
    "chat_outBubble": to_argb(material[("a1", 400)]),
    "chat_outBubbleSelected": to_argb(material[("a1", 400)]),
    "chat_outBubbleGradient": to_argb(material[("a1", 400)]),
    "chat_outBubbleGradient2": to_argb(material[("a1", 400)]),
    "chat_outBubbleGradient3": to_argb(material[("a1", 400)]),
    "chat_messageTextOut": to_argb(material[("a1", 1000)]),
    "chat_messagePanelHint": to_argb(material[("n2", 300)]),
    "chat_messagePanelText": to_argb(material[("n1", 50)]),
    "divider": to_argb(material[("n2", 700)]),
    "chat_replyPanelLine": to_argb(material[("n2", 700)]),
    "graySection": to_argb(material[("n2", 800)]),
}

# iOS surfaces, half-transparent where they sit over the chat wallpaper.
GLASS_LIGHT = {
    "actionBarDefault": (0xF7, 0xF7, 0xFA, 210),
    "actionBarActionModeDefault": (0xF7, 0xF7, 0xFA, 214),
    "actionBarDefaultSubmenuBackground": (0xFA, 0xFA, 0xFC, 236),
    "actionBarBrowser": (0xF7, 0xF7, 0xFA, 210),
    "dialogBackground": (0xFF, 0xFF, 0xFF, 242),
    "chats_menuBackground": (0xFA, 0xFA, 0xFC, 236),
    "chat_messagePanelBackground": (0xFF, 0xFF, 0xFF, 226),
    "chat_emojiPanelBackground": (0xFF, 0xFF, 0xFF, 236),
    "chat_emojiSearchBackground": (0xE9, 0xE9, 0xEB, 226),
    "chat_inBubble": (0xE9, 0xE9, 0xEB, 235),
    "chat_inBubbleSelected": (0xE2, 0xE2, 0xE7, 240),
    "chat_inFileBackground": (0xEC, 0xEC, 0xEF, 235),
    "chat_inFileBackgroundSelected": (0xE2, 0xE2, 0xE7, 240),
    "chat_outBubble": (0x0A, 0x6E, 0xD1, 246),
    "chat_outBubbleSelected": (0x08, 0x60, 0xBA, 248),
    "chat_outBubbleGradient": (0x0A, 0x6E, 0xD1, 246),
    "chat_outBubbleGradient2": (0x0A, 0x6E, 0xD1, 246),
    "chat_outBubbleGradient3": (0x0A, 0x6E, 0xD1, 246),
    "chat_messageTextOut": (0xFF, 0xFF, 0xFF, 255),
    "chat_serviceBackground": (0x00, 0x00, 0x00, 0x38),
    "chat_serviceBackgroundSelected": (0x00, 0x00, 0x00, 0x46),
    "chat_topPanelBackground": (0xF7, 0xF7, 0xFA, 236),
    "chat_replyPanelLine": (0x3C, 0x3C, 0x43, 24),
    "profile_actionBackground": (0x00, 0x71, 0xE3, 255),
    "chat_messagePanelSend": (0x00, 0x71, 0xE3, 255),
    "chats_actionBackground": (0x00, 0x71, 0xE3, 255),
    "undo_background": (0x1C, 0x1C, 0x1E, 234),
    "dialogShadowLine": (0x00, 0x00, 0x00, 20),
    "divider": (0x3C, 0x3C, 0x43, 30),
    "graySection": (0xE9, 0xE9, 0xED, 255),
    "windowBackgroundWhite": (0xF2, 0xF2, 0xF7, 255),
    "windowBackgroundGray": (0xF2, 0xF2, 0xF7, 255),
    "chat_wallpaper": (0xF2, 0xF2, 0xF7, 255),
}
GLASS_DARK = {
    "actionBarDefault": (0x1C, 0x1C, 0x1E, 206),
    "actionBarActionModeDefault": (0x1C, 0x1C, 0x1E, 210),
    "actionBarDefaultSubmenuBackground": (0x2C, 0x2C, 0x2E, 232),
    "actionBarBrowser": (0x1C, 0x1C, 0x1E, 206),
    "dialogBackground": (0x2C, 0x2C, 0x2E, 240),
    "chats_menuBackground": (0x2C, 0x2C, 0x2E, 232),
    "chat_messagePanelBackground": (0x1C, 0x1C, 0x1E, 222),
    "chat_emojiPanelBackground": (0x1C, 0x1C, 0x1E, 232),
    "chat_emojiSearchBackground": (0x2C, 0x2C, 0x2E, 222),
    "chat_inBubble": (0x2C, 0x2C, 0x2E, 232),
    "chat_inBubbleSelected": (0x3A, 0x3A, 0x3C, 238),
    "chat_inFileBackground": (0x3A, 0x3A, 0x3C, 232),
    "chat_inFileBackgroundSelected": (0x48, 0x48, 0x4A, 238),
    "chat_outBubble": (0x0A, 0x6E, 0xD1, 250),
    "chat_outBubbleSelected": (0x08, 0x60, 0xBA, 252),
    "chat_outBubbleGradient": (0x0A, 0x6E, 0xD1, 250),
    "chat_outBubbleGradient2": (0x0A, 0x6E, 0xD1, 250),
    "chat_outBubbleGradient3": (0x0A, 0x6E, 0xD1, 250),
    "chat_messageTextOut": (0xFF, 0xFF, 0xFF, 255),
    "chat_serviceBackground": (0xFF, 0xFF, 0xFF, 0x2E),
    "chat_serviceBackgroundSelected": (0xFF, 0xFF, 0xFF, 0x3C),
    "chat_topPanelBackground": (0x1C, 0x1C, 0x1E, 232),
    "chat_replyPanelLine": (0xEB, 0xEB, 0xF5, 30),
    "profile_actionBackground": (0x00, 0x71, 0xE3, 255),
    "chat_messagePanelSend": (0x00, 0x71, 0xE3, 255),
    "chats_actionBackground": (0x00, 0x71, 0xE3, 255),
    "undo_background": (0x2C, 0x2C, 0x2E, 240),
    "dialogShadowLine": (0x00, 0x00, 0x00, 60),
    "divider": (0xEB, 0xEB, 0xF5, 26),
    "graySection": (0x23, 0x23, 0x26, 255),
    "windowBackgroundWhite": (0x1C, 0x1C, 0x1E, 255),
    "windowBackgroundGray": (0x00, 0x00, 0x00, 255),
    "chat_wallpaper": (0x1C, 0x1C, 0x1E, 255),
}


def composite(fg_argb, bg_argb):
    a = ((fg_argb >> 24) & 0xFF) / 255
    result = 0xFF000000
    for shift in (16, 8, 0):
        f = (fg_argb >> shift) & 0xFF
        b = (bg_argb >> shift) & 0xFF
        result |= clamp_byte(f * a + b * (1 - a)) << shift
    return result


def relative_luminance(argb):
    r, g, b = srgb_to_linear(((argb >> 16) & 0xFF) / 255), srgb_to_linear(((argb >> 8) & 0xFF) / 255), srgb_to_linear((argb & 0xFF) / 255)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg_argb, bg_argb, base=0xFFFFFFFF):
    bg = composite(bg_argb, base)
    fg = composite(fg_argb, bg)
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


GLASS_OUT_FOREGROUND_HINTS = (
    "Text", "Icon", "Menu", "View", "Check", "Clock", "Progress", "Seekbar",
    "Loader", "Line", "Instant", "Name", "Forwarded", "Site", "Via", "Admin",
    "Psa", "Contact", "Venue", "Duration", "Performer", "Title", "Time", "Selected",
)


def glass_out_foreground(keys):
    """White content on the iOS blue bubble, in both light and dark."""
    values = {}
    for key in keys:
        if not key.startswith("chat_out") or "Background" in key or "Overlay" in key:
            continue
        if not any(hint in key for hint in GLASS_OUT_FOREGROUND_HINTS):
            continue
        alpha = 0x99 if ("Line" in key or "Divider" in key) else 0xE6
        if "messageTextOut" in key:
            alpha = 0xFF
        values[key] = (alpha << 24) | 0xFFFFFF
    return values


def glass_argb(entry):
    r, g, b, a = entry
    return (a << 24) | (r << 16) | (g << 8) | b


def extras(palette, dark):
    """Keys Telegram renders but ships without a default or a Monet role."""
    primary = to_argb(palette[("a1", 400 if dark else 600)])
    return {
        "chat_outBubbleGradient1": primary,
        "chat_outBubbleGradientAnimated": 0,
        "chat_wallpaper_gradient_to1": 0,
        "chat_wallpaper_gradient_to2": 0,
        "chat_wallpaper_gradient_to3": 0,
        "chat_inBubbleSelectedOverlay": 0x1FFFFFFF if dark else 0x1F000000,
        "chat_outBubbleSelectedOverlay": 0x24FFFFFF,
        "chat_msgIvButtonDefaultInText": to_argb(palette[("n1", 1000)]),
        "chat_msgIvButtonPrimaryIn": to_argb(palette[("a1", 700 if dark else 100)]),
        "chat_msgIvButtonPrimaryInPressed": to_argb(palette[("a1", 800 if dark else 200)]),
        "chat_msgIvButtonDefaultInlineInText": to_argb(palette[("a1", 600)]),
        "chat_outArticleCodeBackground": 0x33000000 if dark else 0x1A000000,
    }


def build(name, source, palette, defaults, error_rgb, overrides):
    keys, _ = load_keys()
    values = {}
    for key in keys:
        value = render(key, source, palette, defaults, error_rgb, overrides)
        if value is not None:
            values[key] = value & 0xFFFFFFFF
    write_theme(ASSETS / name, values, name)
    return values


def main():
    keys, defaults = load_keys()
    light = parse_theme_asset("monet_light.attheme")
    dark = parse_theme_asset("monet_dark.attheme")

    material_light = build("telecat_material_light.attheme", light, material, defaults,
                           material_error,
                           {**extras(material, False), **material_light_overrides})
    material_dark = build("telecat_material_dark.attheme", dark, material, defaults,
                          material_error,
                          {**extras(material, True), **material_dark_overrides})
    keys, _ = load_keys()
    out_fg = glass_out_foreground(keys)
    glass_light = build("telecat_glass_light.attheme", light, glass, defaults, glass_error,
                        {**extras(glass, False), **material_light_overrides,
                         **{k: glass_argb(v) for k, v in GLASS_LIGHT.items()}, **out_fg})
    glass_dark = build("telecat_glass_dark.attheme", dark, glass, defaults, glass_error,
                       {**extras(glass, True), **material_dark_overrides,
                        **{k: glass_argb(v) for k, v in GLASS_DARK.items()}, **out_fg})

    for name, values in (
        ("material light", material_light),
        ("material dark", material_dark),
        ("glass light", glass_light),
        ("glass dark", glass_dark),
    ):
        print(f"{name}: {len(values)} keys")

    print("\nThemeInfo preview values (ARGB):")
    print("material light", hex(material_light["windowBackgroundWhite"]),
          hex(material_light["chat_inBubble"]), hex(material_light["chat_outBubble"]))
    print("material dark", hex(material_dark["windowBackgroundWhite"]),
          hex(material_dark["chat_inBubble"]), hex(material_dark["chat_outBubble"]))
    print("glass light", hex(glass_light["windowBackgroundWhite"]),
          hex(glass_light["chat_inBubble"]), hex(glass_light["chat_outBubble"]))
    print("glass dark", hex(glass_dark["windowBackgroundWhite"]),
          hex(glass_dark["chat_inBubble"]), hex(glass_dark["chat_outBubble"]))

    missing = [k for k in keys if k not in material_light and k not in NON_COLOR_KEYS]
    if missing:
        print("\nUNRESOLVED:", missing)

    for label, theme in (("material light", material_light), ("material dark", material_dark),
                         ("glass light", glass_light), ("glass dark", glass_dark)):
        print(f"\ncontrast {label}")
        for pair in (
            ("chat_messageTextIn", "chat_inBubble"),
            ("chat_messageTextOut", "chat_outBubble"),
            ("chat_inTimeText", "chat_inBubble"),
            ("windowBackgroundWhiteBlackText", "windowBackgroundWhite"),
            ("actionBarDefaultTitle", "actionBarDefault"),
            ("chats_name", "windowBackgroundWhite"),
            ("chats_message", "windowBackgroundWhite"),
            ("dialogTextBlack", "dialogBackground"),
            ("chat_messagePanelHint", "chat_messagePanelBackground"),
        ):
            base = theme.get("windowBackgroundWhite", 0xFFFFFFFF)
            ratio = contrast(theme.get(pair[0], 0xFF000000), theme.get(pair[1], 0xFFFFFFFF), base)
            print(f"  {pair[0]} on {pair[1]}: {ratio:.2f}")


if __name__ == "__main__":
    main()
