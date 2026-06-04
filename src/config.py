# Configuration file for proxy collector

import os

# ==================== SOURCES CONFIGURATION ====================

TELEGRAM_CHANNELS = [
    "https://t.me/s/PrivateVPNs",
    "https://t.me/s/DirectVPN",
    "https://t.me/s/free4allVPN",
    "https://t.me/s/vpn_ioss",
    "https://t.me/s/Outline_Vpn",
    # Add your channels here
    "https://t.me/s/mtproxy_lists" ,
    "https://t.me/s/DailyV2RY" ,
    "https://t.me/s/ir_IRANy" ,
    "https://t.me/s/Digeh_Direh" ,
    "https://t.me/s/blackRay" ,
    "https://t.me/s/filembad" ,
    "https://t.me/s/Proxymelimon" ,
    "https://t.me/s/saministamm" ,
    "https://t.me/s/lldalall" ,
    "https://t.me/s/prrofile_purple" ,
    "https://t.me/s/i10VPN" ,
    "https://t.me/s/proxy_kafee" ,
    "https://t.me/s/irshum2" ,
    "https://t.me/s/proxymtprotoir" ,
    "https://t.me/s/goldvpnhub" ,
    "https://t.me/s/MPT_Proxy" ,
    "https://t.me/s/AzadNet" ,
    "https://t.me/s/Express_freevpn" ,
    "https://t.me/s/ConfingV2RaayNG" ,
    "https://t.me/s/NightPing" ,
]

GITHUB_REPOS = [
    # "mfuu/v2ray",
    # "peasoft/NoMoreWalls",
    # "mahdibland/V2RayAggregator",
    # Add your repos here
    # "Epodonios/v2ray-configs",
    # "MatinGhanbari/v2ray-configs",
]

PUBLIC_APIS = [
    # "https://raw.githubusercontent.com/mfuu/v2ray/master/v2ray",
    # "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
    # Add your APIs here
    # "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity.txt",
    # "https://raw.githubusercontent.com/Barabama/FreeNodes/refs/heads/main/nodes/blues.txt",
    # "https://raw.githubusercontent.com/Barabama/FreeNodes/refs/heads/main/nodes/yudou66.txt",
    # "https://raw.githubusercontent.com/Barabama/FreeNodes/refs/heads/main/nodes/nodev2ray.txt",
    # "https://raw.githubusercontent.com/Flikify/Free-Node/refs/heads/main/v2ray.txt",
    # "https://raw.githubusercontent.com/Pawdroid/Free-servers/refs/heads/main/sub",
    # "https://raw.githubusercontent.com/shuaidaoya/FreeNodes/refs/heads/main/nodes/base64.txt",
    # "https://cdn.jsdelivr.net/gh/xiaoji235/airport-free/v2ray/clashnodecc.txt",
    # "https://cdn.jsdelivr.net/gh/xiaoji235/airport-free/v2ray/v2rayshare.txt",
    # "https://raw.githubusercontent.com/snakem982/proxypool/main/source/v2ray-2.txt",
     "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/refs/heads/main/Config/HamrahAval.txt",
     "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/refs/heads/main/Config/Irancell.txt",
     "https://github.com/V2RayRoot/V2RayConfig/raw/refs/heads/main/Config/Makhaberat.txt",
     "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/refs/heads/main/Config/Samantel.txt",
     "https://raw.githubusercontent.com/V2RayRoot/V2RayConfig/refs/heads/main/Config/proxies.txt",
     "https://raw.githubusercontent.com/SoliSpirit/mtproto/refs/heads/master/all_proxies.txt",
     "https://raw.githubusercontent.com/Mahdi0024/ProxyCollector/refs/heads/master/sub/proxies.txt",
     "https://raw.githubusercontent.com/jafarm83/ConfigV2Ray/refs/heads/main/jafar.txt",
     "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/SLIPNET_SUB/refs/heads/main/slipnet_no2.txt",
     "https://raw.githubusercontent.com/V2RAYCONFIGSPOOL/SLIPNET_SUB/refs/heads/main/slipnet_no1.txt",
    "https://raw.githubusercontent.com/shervinofpersia/SlipNet/refs/heads/main/%E2%98%ACSH%CE%9EN%E2%84%A2.txt",
    "https://raw.githubusercontent.com/masir-sefid/Sub/main/@Masir_Sefid.txt",
    #"https://raw.githubusercontent.com/jafarm83/ConfigV2Ray/refs/heads/main/jafar.txt",
]

WEB_SCRAPE_URLS = []

# ==================== IRANIAN CDN CONFIGURATION ====================

ARVAN_CLOUD_RANGES = [
    "185.143.232.0/22",
    "188.114.96.0/20",
    "5.213.255.0/24",
]

DERAK_CLOUD_RANGES = [
    "151.243.0.0/16",
]

IRANIAN_ASNS = {
    "AS44244": "Irancell",
    "AS197207": "MCI",
    "AS57218": "Rightel",
    "AS31549": "Shatel",
    "AS207994": "ArvanCloud",
    "AS60976": "DerakCloud",
    "AS49666": "ParsOnline",
    "AS41689": "AsiaNet",
    "AS48434": "FaraPik",
}

# ==================== COUNTRY FILTERS ====================

TEST_COUNTRIES = ["IR", "DE"]
PRIORITY_COUNTRY = "IR"

# ==================== OUTPUT CONFIGURATION ====================

OUTPUT_DIR = "output"
IRAN_DIR = os.path.join(OUTPUT_DIR, "iran")
GERMANY_DIR = os.path.join(OUTPUT_DIR, "germany")
OTHERS_DIR = os.path.join(OUTPUT_DIR, "others")
TESTED_DIR = os.path.join(OUTPUT_DIR, "tested")

# خروجی‌های جدید بر اساس پروتکل (در سطح سراسری، نه کشوری)
BY_PROTOCOL_DIR = os.path.join(OUTPUT_DIR, "by_protocol")
BY_PROTOCOL_ALL_DIR = os.path.join(BY_PROTOCOL_DIR, "all")
BY_PROTOCOL_TESTED_DIR = os.path.join(BY_PROTOCOL_DIR, "tested")

# ==================== UPDATE CONFIGURATION ====================

UPDATE_INTERVAL_HOURS = 4
CONNECTION_TIMEOUT = 10
MAX_WORKERS = 20

# ==================== GITHUB CONFIGURATION ====================

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
REPO_NAME = os.getenv("GITHUB_REPOSITORY", "")

# ==================== COUNTRY FLAGS ====================

# این دیکشنری برای overrideها و موارد خاص است؛
# برای بقیه کشورها پرچم به‌صورت خودکار از روی کد دوحرفی ساخته می‌شود.
COUNTRY_FLAGS = {
    "IR": "🇮🇷", "DE": "🇩🇪", "US": "🇺🇸", "GB": "🇬🇧",
    "FR": "🇫🇷", "NL": "🇳🇱", "CA": "🇨🇦", "SG": "🇸🇬",
    "JP": "🇯🇵", "KR": "🇰🇷", "HK": "🇭🇰", "TW": "🇹🇼",
    "AU": "🇦🇺", "IN": "🇮🇳", "RU": "🇷🇺", "TR": "🇹🇷",
    "AE": "🇦🇪", "SE": "🇸🇪", "FI": "🇫🇮", "PL": "🇵🇱",
    "UA": "🇺🇦", "BR": "🇧🇷", "AR": "🇦🇷", "MX": "🇲🇽",
    "ZA": "🇿🇦", "EG": "🇪🇬", "CH": "🇨🇭", "AT": "🇦🇹",
    # در صورت نیاز می‌توانی اینجا موارد خاص بیشتری اضافه کنی (مثلاً EU، UK و غیره)
}

CDN_NAMES = {
    "arvancloud": "☁️ArvanCloud",
    "derakcloud": "☁️DerakCloud",
    "cloudflare": "☁️Cloudflare",
    "asiatech": "☁️AsiaTech",
    "farapik": "☁️FaraPik",
}


def _auto_country_flag(country_code: str) -> str:
    """
    ساخت خودکار ایموجی پرچم از روی کد دوحرفی کشور/منطقه (A-Z).
    در صورت کد نامعتبر، 🌐 برمی‌گرداند.
    """
    code = (country_code or "").upper()
    if len(code) != 2 or not code.isalpha():
        return "🌐"
    # هر حرف A-Z به محدوده‌ی Regional Indicator Symbols نگاشت می‌شود
    return "".join(chr(ord(char) + 127397) for char in code)


def get_country_flag(country_code: str) -> str:
    """
    گرفتن ایموجی پرچم برای کد کشور:

    - اگر در COUNTRY_FLAGS تعریف شده باشد، همان مقدار برگردانده می‌شود (override).
    - در غیر این‌صورت، برای هر کد دوحرفی A-Z پرچم به‌صورت خودکار ساخته می‌شود.
    - برای کدهای نامعتبر یا خالی، 🌐 برگردانده می‌شود.
    """
    if not country_code:
        return "🌐"

    code = country_code.upper()

    # overrideهای دستی
    if code in COUNTRY_FLAGS:
        return COUNTRY_FLAGS[code]

    # تولید خودکار برای تمام کدهای دوحرفی معتبر
    return _auto_country_flag(code)
