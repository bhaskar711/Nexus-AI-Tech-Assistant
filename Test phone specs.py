"""
Offline tests for the Nexus smartphone pipeline.  No internet, no Ollama.
 
    python test_phone_specs.py
 
The HTML fixtures below are SYNTHETIC pages that copy the row layout of a
GSMArena spec table (section header + label/value rows). They test the parser
logic, not the real content of any live page.
"""
import sys
import types
 
# Stub the modules that need Ollama / network so the test runs anywhere.
for name, attrs in {
    "ollama": {"chat": lambda *a, **k: {}},
    "tools": {"search_knowledge": lambda *a, **k: []},
    "you_search_tool": {"web_search": lambda *a, **k: {}},
}.items():
    module = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(module, k, v)
    sys.modules.setdefault(name, module)
 
import agent                      # noqa: E402
import phone_specs as ps          # noqa: E402
 
PASS = FAIL = 0
 
 
def check(name, actual, expected):
    global PASS, FAIL
    if actual == expected:
        PASS += 1
        print(f"  ok    {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}\n        expected: {expected!r}\n        actual:   {actual!r}")
 
 
def gsm(sections):
    html = "<html><body><div id='specs-list'>"
    for section, rows in sections.items():
        html += "<table cellspacing='0'>"
        for i, (label, value) in enumerate(rows):
            html += "<tr>"
            if i == 0:
                html += f"<th rowspan='{len(rows)}' scope='row'>{section}</th>"
            html += f"<td class='ttl'><a href='#'>{label}</a></td><td class='nfo'>{value.replace(chr(10), '<br>')}</td></tr>"
        html += "</table>"
    return html + "</div></body></html>"
 
 
IPHONE16 = gsm({
    "Display": [
        ("Type", "Super Retina XDR OLED, 60Hz, HDR10, Dolby Vision, 1000 nits (typ), 2000 nits (peak)"),
        ("Size", "6.1 inches, 90.4 cm2 (~86.0% screen-to-body ratio)"),
        ("Resolution", "1179 x 2556 pixels, 19.5:9 ratio (~460 ppi density)"),
        ("Protection", "Ceramic Shield glass"),
    ],
    "Platform": [
        ("OS", "iOS 18"),
        ("Chipset", "Apple A18 (3 nm)"),
        ("CPU", "Hexa-core (2x4.04 GHz + 4x2.20 GHz)"),
        ("GPU", "Apple GPU (5-core graphics)"),
    ],
    "Main Camera": [
        ("Dual", '48 MP, f/1.6, 26mm (wide), 1/1.56", 1.0µm, dual pixel PDAF, sensor-shift OIS\n'
                 '12 MP, f/2.2, 13mm, 120˚ (ultrawide), 1/2.55", 1.4µm, dual pixel PDAF'),
        ("Features", "Dual-LED dual-tone flash, HDR (photo/panorama), 48 MP ProRAW"),
        ("Video", "4K@24/25/30/60fps, 1080p@25/30/60/120/240fps, HDR, Dolby Vision HDR (up to 60fps)"),
    ],
    "Selfie camera": [
        ("Single", '12 MP, f/1.9, 23mm (wide), 1/3.6", PDAF'),
        ("Video", "4K@24/25/30/60fps, 1080p@25/30/60/120fps"),
    ],
    "Battery": [
        ("Type", "Li-Ion 3561 mAh"),
        ("Charging", "Wired, PD2.0, 50% in 30 min (advertised)\n25W wireless (MagSafe)\n15W wireless (Qi2)\n4.5W reverse wired"),
    ],
})
 
ONEPLUS15 = gsm({
    "Display": [
        ("Type", "LTPO AMOLED, 1B colors, 165Hz, Dolby Vision, HDR10+, 1800 nits (peak)"),
        ("Size", "6.78 inches, 110.0 cm2"),
        ("Resolution", "1272 x 2772 pixels, 19.5:9 ratio (~450 ppi density)"),
    ],
    "Platform": [
        ("Chipset", "Qualcomm SM8850-AC Snapdragon 8 Elite Gen 5 (3 nm)"),
        ("CPU", "Octa-core (2x4.6 GHz + 6x3.62 GHz)"),
        ("GPU", "Adreno 840"),
    ],
    "Main Camera": [
        ("Triple", '50 MP, f/1.8, (wide), 1/1.56", OIS\n'
                   '50 MP, f/2.8, (telephoto), 1/2.76", OIS\n'
                   '50 MP, f/2.0, 116˚ (ultrawide)'),
        ("Video", "8K@30fps, 4K@30/60/120fps, 1080p@30/60/240fps"),
    ],
    "Selfie camera": [("Single", "32 MP, f/2.4, (wide)")],
    "Battery": [
        ("Type", "Si/C 7300 mAh"),
        ("Charging", "120W wired, PD, 50% in 15 min (advertised), 50W wireless, 10W reverse wireless"),
    ],
})
 
VIVOT4 = gsm({
    "Display": [
        ("Type", "AMOLED, 1B colors, 120Hz, 5000 nits (peak)"),
        ("Size", "6.77 inches"),
        ("Resolution", "1080 x 2392 pixels"),
    ],
    "Platform": [("Chipset", "Qualcomm SM7635 Snapdragon 7s Gen 3 (4 nm)")],
    "Main Camera": [("Dual", '50 MP, f/1.8, (wide), 1/1.95", OIS\n2 MP (depth)')],
    "Selfie camera": [("Single", "32 MP, f/2.0, (wide)")],
    "Battery": [("Type", "Si/C 7300 mAh, non-removable"), ("Charging", "90W wired")],
})
 
 
def spec(html):
    return ps.extract_all(ps.rows_from_html(html))
 
 
print("\n== Variant rejection (URL validation) ==")
P = "https://www.91mobiles.com/{}-price-in-india"
G = "https://www.gsmarena.com/{}.php"
check("iPhone 15 accepts iPhone 15", ps.is_exact_page(P.format("apple-iphone-15"), "Apple iPhone 15"), True)
for slug in ("apple-iphone-15-plus", "apple-iphone-15-pro", "apple-iphone-15-pro-max"):
    check(f"iPhone 15 rejects {slug}", ps.is_exact_page(P.format(slug), "Apple iPhone 15"), False)
check("iPhone 15 GSMArena ok", ps.is_exact_page(G.format("apple_iphone_15-12559"), "Apple iPhone 15"), True)
check("iPhone 15 rejects GSMArena Pro Max", ps.is_exact_page(G.format("apple_iphone_15_pro_max-12548"), "Apple iPhone 15"), False)
check("rejects GSMArena reviews page", ps.is_exact_page(G.format("apple_iphone_15-reviews-12559"), "Apple iPhone 15"), False)
check("iPhone 17 rejects 17e (your real bug)", ps.is_exact_page(P.format("apple-iphone-17e"), "Apple iPhone 17"), False)
check("iPhone 17 accepts 17", ps.is_exact_page(P.format("apple-iphone-17"), "Apple iPhone 17"), True)
check("iPhone 17e accepts 17e", ps.is_exact_page(P.format("apple-iphone-17e"), "Apple iPhone 17e"), True)
check("iPhone 15 Pro rejects Pro Max", ps.is_exact_page(P.format("apple-iphone-15-pro-max"), "Apple iPhone 15 Pro"), False)
check("OnePlus 15 accepts 15", ps.is_exact_page(P.format("oneplus-15"), "OnePlus 15"), True)
check("OnePlus 15 rejects 15R", ps.is_exact_page(P.format("oneplus-15r"), "OnePlus 15"), False)
check("S25 Ultra accepts S25 Ultra", ps.is_exact_page(P.format("samsung-galaxy-s25-ultra"), "Samsung Galaxy S25 Ultra"), True)
check("S25 Ultra rejects S25", ps.is_exact_page(P.format("samsung-galaxy-s25"), "Samsung Galaxy S25 Ultra"), False)
check("S25 rejects S25 Ultra", ps.is_exact_page(P.format("samsung-galaxy-s25-ultra"), "Samsung Galaxy S25"), False)
check("S25 rejects S25+ (GSMArena)", ps.is_exact_page(G.format("samsung_galaxy_s25+-13611"), "Samsung Galaxy S25"), False)
check("vivo T4 accepts vivo-t4-5g", ps.is_exact_page(P.format("vivo-t4-5g"), "vivo T4"), True)
check("vivo T4 rejects T4x", ps.is_exact_page(P.format("vivo-t4x-5g"), "vivo T4"), False)
check("vivo T4 rejects T4 Lite", ps.is_exact_page(P.format("vivo-t4-lite-5g"), "vivo T4"), False)
check("rejects non-product article", ps.is_exact_page("https://www.91mobiles.com/hub/iphone-16-discount", "Apple iPhone 16"), False)
 
print("\n== Product identification from the question ==")
cases = {
    "iphone 15 specifications": "Apple iPhone 15",
    "iphone15 specs": "Apple iPhone 15",
    "iphone 16 specifications": "Apple iPhone 16",
    "iphone 15 pro specifications": "Apple iPhone 15 Pro",
    "iPhone 15 Pro Max battery": "Apple iPhone 15 Pro Max",
    "iphone 16e specs": "Apple iPhone 16e",
    "iphone 17 specifications": "Apple iPhone 17",
    "samsung galaxy s25 ultra specifications": "Samsung Galaxy S25 Ultra",
    "s25 ultra specs": "Samsung Galaxy S25 Ultra",
    "s25ultra": "Samsung Galaxy S25 Ultra",
    "explain the display of Galaxy S25 Ultra": "Samsung Galaxy S25 Ultra",
    "oneplus 15 specifications": "OnePlus 15",
    "oneplus 13r battery": "OnePlus 13R",
    "vivo t4 specifications": "vivo T4",
    "vivo t4": "vivo T4",
    "what processor does iPhone 16 use?": "Apple iPhone 16",
    "pixel 10 pro camera": "Google Pixel 10 Pro",
}
for question, expected in cases.items():
    check(f"'{question}'", agent.detect_product(question), expected)
 
print("\n== Router ==")
check("spec query -> techspecs", agent.route_question("vivo t4"), "techspecs")
check("latest phone -> techspecs", agent.route_question("latest oneplus phone"), "techspecs")
check("concept question -> rag", agent.route_question("what is OLED"), "rag")
check("news -> web", agent.route_question("latest AI news"), "web")
 
print("\n== iPhone 16 fixture: component association ==")
s = spec(IPHONE16)
check("display type", s.get("display_type"), "Super Retina XDR OLED")
check("display size", s.get("display_size"), "6.1 inches")
check("resolution", s.get("display_resolution"), "1179 × 2556")
check("refresh rate", s.get("refresh_rate"), "60 Hz")
check("peak brightness != typical", (s.get("peak_brightness"), s.get("typical_brightness")), ("2000 nits", "1000 nits"))
check("HDR", s.get("hdr"), "Dolby Vision, HDR10")
check("chipset clean", s.get("chipset"), "Apple A18")
check("process node", s.get("process_node"), "3 nm")
check("main camera", s.get("cam_main_mp"), "48 MP")
check("ultrawide is 12 MP, not main", s.get("cam_ultrawide"), "12 MP")
check("no telephoto invented", s.get("cam_telephoto"), None)
check("front camera 12 MP, not 48", s.get("cam_front"), "12 MP")
check("lens list complete (dual == 2 lenses)", s.get("lens_complete"), True)
check("main aperture", s.get("cam_main_aperture"), "f/1.6")
check("main OIS", s.get("cam_main_ois"), "Yes")
check("video = 4K 60, not 1080p 240 slow-mo", s.get("video"), "4K up to 60 fps")
check("no slow-mo invented", s.get("slow_motion"), None)
check("battery capacity", s.get("battery_mah"), "3561 mAh")
check("wireless != wired", (s.get("wired_charging"), s.get("wireless_charging")), (None, "25W"))
check("reverse charging 4.5W", s.get("reverse_charging"), "4.5W")
 
print("\n== OnePlus 15 fixture ==")
s = spec(ONEPLUS15)
check("chipset", s.get("chipset"), "Snapdragon 8 Elite Gen 5")
check("refresh", s.get("refresh_rate"), "165 Hz")
check("type", s.get("display_type"), "LTPO AMOLED")
check("main 50 MP", s.get("cam_main_mp"), "50 MP")
check("telephoto 50 MP is telephoto", s.get("cam_telephoto"), "50 MP")
check("ultrawide 50 MP", s.get("cam_ultrawide"), "50 MP")
check("front 32 MP (not 50)", s.get("cam_front"), "32 MP")
check("video 8K + 4K", s.get("video"), "8K up to 30 fps; 4K up to 120 fps")
check("battery 7300", s.get("battery_mah"), "7300 mAh")
check("120W wired / 50W wireless / 10W reverse in ONE line",
      (s.get("wired_charging"), s.get("wireless_charging"), s.get("reverse_charging")), ("120W", "50W", "10W"))
check("CPU clock", s.get("cpu_clock"), "4.6 GHz (max)")
check("CPU cores", s.get("cpu_cores"), "Octa-core")
 
print("\n== vivo T4 fixture ==")
s = spec(VIVOT4)
check("chipset", s.get("chipset"), "Snapdragon 7s Gen 3")
check("main 50 MP", s.get("cam_main_mp"), "50 MP")
check("front 32 MP (not 50)", s.get("cam_front"), "32 MP")
check("2 MP depth not treated as ultrawide/tele", (s.get("cam_ultrawide"), s.get("cam_telephoto")), (None, None))
check("lens list complete", s.get("lens_complete"), True)
check("battery 7300", s.get("battery_mah"), "7300 mAh")
check("wired 90W and no fake wireless", (s.get("wired_charging"), s.get("wireless_charging")), ("90W", None))
 
print("\n== Small parsers ==")
check("chip clean: 'Snapdragon 8 Elite Gen 5 chipset'", ps.chip_name("Snapdragon 8 Elite Gen 5 chipset"), "Snapdragon 8 Elite Gen 5")
check("chip clean: Dimensity 9400+", ps.chip_name("MediaTek Dimensity 9400+ (3 nm)"), "Dimensity 9400+")
check("chip clean: Tensor", ps.chip_name("Google Tensor G5 (3 nm)"), "Google Tensor G5")
check("chip clean: Exynos", ps.chip_name("Exynos 2500 (3 nm)"), "Exynos 2500")
check("brightness order independent", ps._brightness("peak brightness: 3000 nits, typical brightness: 1200 nits")[:2], (3000, 1200))
w = ps.classify_watts("120W wired, 50W wireless, 10W reverse wireless")
check("watts split", (w["wired"], w["wireless"], w["reverse"]), ([120.0], [50.0], [10.0]))
w = ps.classify_watts("Wireless charging 50W; wired 120W")
check("watts, qualifier first", (w["wired"], w["wireless"]), ([120.0], [50.0]))
check("video: only explicit slow-mo is labelled", ps.parse_video("4K@60fps, slow-mo 240fps").get("slow_motion"), "up to 240 fps")
check("video: 1080p/240 alone is not headline", ps.parse_video("1080p@30/240fps").get("video"), "1080p up to 240 fps")
 
 
print("\n== Regressions from your real run ==")
check("'oppo k14plus specifications' detected", agent.detect_product("oppo k14plus specifications"), "OPPO K14 Plus")
check("'realme 14 pro plus' keeps Plus", agent.detect_product("realme 14 pro plus specs"), "realme 14 Pro Plus")
check("'oppo k14plus specifications' routes to techspecs", agent.route_question("oppo k14plus specifications"), "techspecs")
check("oppo k14 plus URL accepted", ps.is_exact_page(P.format("oppo-k14-plus-5g"), "OPPO K14 Plus"), True)
check("oppo k14 URL rejected for K14 Plus", ps.is_exact_page(P.format("oppo-k14-5g"), "OPPO K14 Plus"), False)
check("iphone 18pro detected", agent.detect_product("iphone 18pro specifications"), "Apple iPhone 18 Pro")
check("iphone 18promax detected", agent.detect_product("iphone 18promax specifications"), "Apple iPhone 18 Pro Max")
 
# 'f/1.9' must never become a megapixel value; sub-5MP 'main camera' is rejected
bad = ps.rows_from_blob("")  # placeholder to keep API used
rows = [ps._make_row("Rear Camera", "Aperture", "f/1.9 MP"),
        ps._make_row("Rear Camera", "Primary Camera", "48 MP"),
        ps._make_row("Rear Camera", "Secondary Camera", "48 MP Ultra Wide"),
        ps._make_row("Rear Camera", "Tertiary Camera", "48 MP Telephoto")]
c = ps.extract_camera(rows)
check("f/1.9 ignored; 91mobiles-style rows give main/ultrawide/tele",
      (c.get("cam_main_mp"), c.get("cam_ultrawide"), c.get("cam_telephoto")), ("48 MP", "48 MP", "48 MP"))
c = ps.extract_camera([ps._make_row("Rear Camera", "Camera", "1.9 MP")])
check("1.9 MP is not accepted as a main camera", c.get("cam_main_mp"), None)
 
# protection: 'Yes' is not a glass name
rows = [ps._make_row("Display", "Screen Protection", "Yes"),
        ps._make_row("Display", "Protection Type", "Ceramic Shield 2")]
check("protection skips 'Yes'", ps.extract_display(rows).get("protection"), "Ceramic Shield 2")
 
# CPU clock must come from the CPU description, never a different row
rows = [ps._make_row("Performance", "Chipset", "Apple A20 Pro"),
        ps._make_row("Performance", "CPU", "Hexa-core (2x4.93 GHz + 4x2.64 GHz)"),
        ps._make_row("Performance", "Clock Speed", "3.464 GHz")]
check("CPU clock consistent with CPU line", ps.extract_processor(rows).get("cpu_clock"), "4.93 GHz (max)")
 
# generic 'Charging' row: never guess an unlabelled wattage
w = ps.classify_watts("Wired, PD3.0, 50% in 20 min\n25W wireless (MagSafe)\n15W Qi2.2 wireless", default=None)
check("generic row: no wired guess", (w["wired"], w["wireless"]), ([], [25.0, 15.0]))
w = ps.classify_watts("40W wired, PD3.0\n15W", default=None)
check("generic row: unlabelled later value ignored", w["wired"], [40.0])
 
 
print("\n== Real-page regressions (layouts copied from live 91mobiles / GSMArena pages) ==")
RENO15_91 = """<html><body><table><tr><th colspan=2>Performance (Very Good)</th></tr>
<tr><td>Chipset</td><td>Qualcomm Snapdragon 7 Gen 4 <a>View Details</a></td></tr>
<tr><td>Processor</td><td>Octa core (2.8 GHz, Single core, Cortex A725 + 2.4 GHz, Tri core, Cortex A725 + 1.84 GHz, Quad core, Cortex A725)</td></tr>
<tr><td>Fabrication</td><td>4 nm</td></tr><tr><td>Graphics (GPU)</td><td>Adreno 722</td></tr></table>
<table><tr><th colspan=2>Display (Excellent)</th></tr>
<tr><td>Display Type</td><td>LTPS AMOLED</td></tr><tr><td>Screen Size</td><td>6.59 inches (16.74 cm)</td></tr>
<tr><td>Resolution</td><td>1256x2760 px (FHD+)</td></tr><tr><td>Peak Brightness</td><td>1800 nits</td></tr>
<tr><td>HBM Brightness</td><td>1200 nits</td></tr><tr><td>Refresh Rate</td><td>120 Hz</td></tr>
<tr><td>Touch Sampling Rate</td><td>240 Hz</td></tr><tr><td>Screen Protection</td><td>Corning Gorilla Glass 7i</td></tr></table>
<table><tr><th colspan=2>Rear Camera (Very Good)</th></tr>
<tr><td>Resolution</td><td><table><tr><th>Camera</th><th>MP</th><th>Lens Features</th><th>Aperture</th><th>Sensor Size</th><th>Sensor Name</th></tr>
<tr><td>Primary</td><td>50 MP</td><td>Wide Angle(79° field-of-view)</td><td>f/1.8</td><td>1/1.95"</td><td>Sony ISOCELL IMX882</td></tr>
<tr><td>Secondary</td><td>8 MP</td><td>Periscope Ultra-Wide Angle</td><td>f/2.2</td><td>1/4"</td><td>OmniVision OV08D</td></tr>
<tr><td>Tertiary</td><td>50 MP</td><td>Telephoto</td><td>f/2.8</td><td>1/2.76"</td><td>Samsung ISOCELL S5KJN5</td></tr></table></td></tr>
<tr><td>OIS</td><td>Yes</td></tr>
<tr><td>Video Recording</td><td>4k @30/60 fps   Full HD @30/60 fps   HD @30/120/240 fps</td></tr></table>
<table><tr><th colspan=2>Front Camera (Excellent)</th></tr>
<tr><td>Resolution</td><td><table><tr><th>Camera</th><th>MP</th><th>Lens Features</th></tr>
<tr><td>Primary</td><td>50 MP</td><td>Wide Angle</td></tr></table></td></tr></table>
<table><tr><th colspan=2>Battery (Very Good)</th></tr>
<tr><td>Capacity</td><td>6500 mAh</td></tr><tr><td>Quick Charging</td><td>Yes, 80W Super VOOC Charging</td></tr>
<tr><td>Reverse Charging</td><td>Yes</td></tr></table></body></html>"""
s = spec(RENO15_91)
check("nested lens table: main 50 MP (not 200)", s.get("cam_main_mp"), "50 MP")
check("nested lens table: 8 MP is the ultrawide", s.get("cam_ultrawide"), "8 MP")
check("nested lens table: 50 MP is the telephoto", s.get("cam_telephoto"), "50 MP")
check("nested lens table: front 50 MP", s.get("cam_front"), "50 MP")
check("nested lens table: main sensor size / aperture", (s.get("cam_main_sensor"), s.get("cam_main_aperture")), ('1/1.95"', "f/1.8"))
check("separate OIS row is reported as OIS", s.get("cam_ois"), "Yes")
check("nested lens table: lens list complete", s.get("lens_complete"), True)
check("nested: video", s.get("video"), "4K up to 60 fps")
check("91mobiles chipset", s.get("chipset"), "Snapdragon 7 Gen 4")
check("91mobiles CPU line from 'Processor' row", s.get("cpu_cores"), "Octa-core")
check("91mobiles CPU clock = 2.8", s.get("cpu_clock"), "2.8 GHz (max)")
check("91mobiles charging 80W wired, reverse flag", (s.get("wired_charging"), s.get("reverse_charging")), ("80W", "Yes"))
check("protection name", s.get("protection"), "Corning Gorilla Glass 7i")
check("peak brightness", s.get("peak_brightness"), "1800 nits")
 
S26 = """<html><body><table><tr><th colspan=2>Display (Excellent)</th></tr>
<tr><td>Display Type</td><td>Dynamic AMOLED 2x</td></tr><tr><td>Screen Size</td><td>6.736 inches (171.1 mm)</td></tr>
<tr><td>Resolution</td><td>1080x2340 px (FHD+)</td></tr><tr><td>Peak Brightness</td><td>1900 nits</td></tr>
<tr><td>Refresh Rate</td><td>120 Hz</td></tr><tr><td>HDR 10 / HDR+ Support</td><td>Yes, HDR 10+</td></tr></table>
<table><tr><th colspan=2>Battery (Very Good)</th></tr><tr><td>Capacity</td><td>4900 mAh</td></tr>
<tr><td>Quick Charging</td><td>Yes, 45W Fast Charging v2.0, 69% in 70 minutes</td></tr>
<tr><td>Wireless Charging</td><td>Yes, 15W Wireless Charging</td></tr><tr><td>Reverse Charging</td><td>Yes</td></tr>
<tr><td>Wireless Reverse Charging</td><td>Yes</td></tr></table></body></html>"""
s = spec(S26)
check("S26 FE size 6.736 -> 6.74 (not '6 inches')", s.get("display_size"), "6.74 inches")
check("S26 FE HDR '10+' with a space", s.get("hdr"), "HDR10+")
check("S26 FE 45W wired / 15W wireless", (s.get("wired_charging"), s.get("wireless_charging")), ("45W", "15W"))
 
CHINA = "<html><head><title>Oppo Reno15 (China) - Full phone specifications</title></head><body>" \
        "<a href=\"oppo_reno15_5g_(global)-14395.php\">Oppo Reno15</a><a href=\"oppo_reno15_pro_5g_(global)-14394.php\">Pro</a></body></html>"
check("GSMArena China page detected", ps.page_region(CHINA), "china")
check("finds the global page of the SAME model (not Pro)",
      ps.find_regional_link(CHINA, "https://www.gsmarena.com/oppo_reno15_5g-14288.php", "OPPO Reno15"),
      "https://www.gsmarena.com/oppo_reno15_5g_(global)-14395.php")
check("GSMArena (global) slug accepted", ps.is_exact_page("https://www.gsmarena.com/oppo_reno15_5g_(global)-14395.php", "OPPO Reno15"), True)
check("Reno15 Pro (global) rejected for Reno15", ps.is_exact_page("https://www.gsmarena.com/oppo_reno15_pro_5g_(global)-14394.php", "OPPO Reno15"), False)
india = {"spec": {"chipset": "Snapdragon 7 Gen 4", "display_size": "6.59 inches", "battery_mah": "6500 mAh"}}
china = {"spec": {"chipset": "Dimensity 8450", "display_size": "6.32 inches", "battery_mah": "6200 mAh"}}
check("India vs China variant is detected (not mixed)", len(ps.variant_mismatch(india, china)) >= 2, True)
same = {"spec": {"chipset": "Snapdragon 7 Gen 4", "display_size": "6.6 inches", "battery_mah": "6500 mAh"}}
check("same variant is NOT flagged", ps.variant_mismatch(india, same), [])
 
print("\n== More product names ==")
more = {
    "oppo reno 15": "OPPO Reno 15",
    "oppo reno15 pro mini specs": "OPPO Reno 15 Pro Mini",
    "oppo k14 plus": "OPPO K14 Plus",
    "realme 14 pro plus specs": "realme 14 Pro Plus",
    "redmi note 14 pro plus": "Redmi Note 14 Pro Plus",
    "poco x7 pro": "POCO X7 Pro",
    "xiaomi 15 ultra": "Xiaomi 15 Ultra",
    "iqoo neo 10": "iQOO Neo 10",
    "nothing phone 3a pro": "Nothing Phone 3a Pro",
    "motorola edge 60 fusion": "Motorola Edge 60 Fusion",
    "oppo reno 15 f": "OPPO Reno 15 F",
    "vivo s2 5g": "vivo S2",
    "samsung galaxy s26 fe": "Samsung Galaxy S26 FE",
    "s26fe": "Samsung Galaxy S26 FE",
}
for question, expected in more.items():
    check(f"'{question}'", agent.detect_product(question), expected)
check("RAG question with a brand but no model stays out of specs", agent.route_question("what is the history of oppo"), "rag")
 
print("\n== Merge / conflict handling ==")
a = {"name": "91mobiles", "kind": "full page", "url": "u1", "spec": {"battery_mah": "7300 mAh", "chipset": "Snapdragon 8 Elite Gen 5"}}
b = {"name": "GSMArena", "kind": "full page", "url": "u2", "spec": {"battery_mah": "7200 mAh", "chipset": "Snapdragon 8 Elite Gen 5", "gpu": "Adreno 840"}}
merged, conflicts, fallback, _ = ps.merge_sources([a, b])
check("primary wins", merged["battery_mah"], "7300 mAh")
check("conflict reported", [c[0] for c in conflicts], ["Battery capacity"])
check("missing field filled from fallback", merged.get("gpu"), "Adreno 840")
 
print(f"\n{PASS} passed, {FAIL} failed")
if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)
 
