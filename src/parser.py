"""
Parser module for parsing different proxy config formats
"""

import base64
import json
import re
import logging
import html
import os
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs, unquote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigParser:
    """Parser for different proxy config formats"""

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_base64_decode(data: str) -> str:
        """Helper method to safely decode Base64 strings with various quirks"""
        if not data:
            return ""

        # ممکن است لینک URL-encoded باشد
        data = unquote(data)

        # حذف فاصله‌ها
        data = data.strip()

        # استانداردسازی کاراکترهای URL-safe
        data = data.replace("-", "+").replace("_", "/")

        # اصلاح Padding
        padding = 4 - len(data) % 4
        if padding < 4:
            data += "=" * padding

        try:
            decoded_bytes = base64.b64decode(data)
            return decoded_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    @staticmethod
    def _clean_name(name: str) -> str:
        """Clean config name from control characters and weird symbols"""
        if not name:
            return ""
        name = unquote(name)
        name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", name)
        return name.strip()

    @staticmethod
    def _is_printable_ascii(s: str) -> bool:
        """Check that all chars are printable ASCII (no control / binary)"""
        return all(32 <= ord(ch) <= 126 for ch in s)

    # ------------------------------------------------------------------
    #  Main dispatcher
    # ------------------------------------------------------------------

    @staticmethod
    def parse_config(config: str) -> Optional[Dict]:
        """Parse a proxy config and extract information"""
        try:
            config = config.strip().strip('\'"')
            lower = config.lower()

            # VMess
            if lower.startswith("vmess://"):
                return ConfigParser._parse_vmess(config)

            # VLESS
            if lower.startswith("vless://"):
                return ConfigParser._parse_vless(config)

            # TROJAN
            if lower.startswith("trojan://"):
                return ConfigParser._parse_trojan(config)

            # Shadowsocks
            if lower.startswith("ss://"):
                return ConfigParser._parse_shadowsocks(config)

            # SSR
            if lower.startswith("ssr://"):
                return ConfigParser._parse_ssr(config)

            # Hysteria / Hysteria2
            if lower.startswith("hysteria://") or lower.startswith("hysteria2://"):
                return ConfigParser._parse_hysteria(config)

            # TUIC
            if lower.startswith("tuic://"):
                return ConfigParser._parse_tuic(config)

            # پروکسی‌های تلگرام (tg:// و https://t.me/proxy)
            if lower.startswith("tg://proxy?") or lower.startswith(
                "https://t.me/proxy?"
            ):
                return ConfigParser._parse_tg_proxy(config)

            # Slipnet
            if lower.startswith("slipnet"):
                return ConfigParser._parse_slipnet(config)

            # لینک‌های http/https:
            # - فقط اگر پسوند فایل معتبر داشته باشند (ovpn, npvt, conf, config, txt)
            # - URLهای ساده مثل https://t.me:443 یا http://1.2.3.4:8080 را نادیده می‌گیریم
            if lower.startswith("http://") or lower.startswith("https://"):
                parsed = urlparse(config)
                path = parsed.path or ""
                fragment = parsed.fragment or ""

                # اگر هیچ "." در path و fragment نیست، این لینک فایل/کانفیگ نیست → رد
                if "." not in path and "." not in fragment:
                    return None

                return ConfigParser._parse_file_link(config)

            return None

        except Exception as e:
            logger.debug(f"Error parsing config: {e}")
            return None

    # ------------------------------------------------------------------
    #  V2Ray family
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_vmess(config: str) -> Optional[Dict]:
        """Parse VMess config"""
        try:
            config_data = config.replace("vmess://", "")
            decoded = ConfigParser._safe_base64_decode(config_data)

            if not decoded:
                return None

            data = json.loads(decoded)

            return {
                "type": "vmess",
                "address": data.get("add", ""),
                "port": str(data.get("port", "")),
                "id": data.get("id", ""),
                "name": ConfigParser._clean_name(data.get("ps", "")),
                "network": data.get("net", ""),
                "host": data.get("host", ""),
                "sni": data.get("sni", ""),
                "original": config,
            }
        except Exception as e:
            logger.debug(f"Error parsing VMess: {e}")
            return None

    @staticmethod
    def _parse_vless(config: str) -> Optional[Dict]:
        """
        Parse VLESS config (پایدار و کامل‌تر)
        """
        try:
            # اگر از HTML (تلگرام) آمده باشد، &amp; و ... را به شکل عادی برمی‌گردانیم
            cfg_str = html.unescape(config)
            parsed = urlparse(cfg_str)

            if parsed.scheme.lower() != "vless":
                return None

            # uuid معمولاً در قسمت user (قبل از @) است
            uuid = parsed.username or ""
            # آدرس و پورت
            address = parsed.hostname or ""
            port = str(parsed.port or "")

            # نام (Remark) در fragment است
            name = parsed.fragment or ""
            name = ConfigParser._clean_name(name)

            # پارامترهای query
            params = parse_qs(parsed.query or "")

            # network type: tcp, ws, grpc, xhttp, ...
            network = params.get("type", [""])[0].lower()

            # security: tls, reality, ...
            security = params.get("security", [""])[0].lower()

            # flow (برای reality و ... )
            flow = params.get("flow", [""])[0]

            # encryption: none, ...
            encryption = params.get("encryption", [""])[0].lower()

            # headerType: http, none, ...
            header_type = params.get("headerType", [""])[0].lower()

            # fingerprint: chrome, firefox, ...
            fingerprint = params.get(
                "fp", params.get("fingerprint", [""])
            )[0].lower()

            # sni
            sni = params.get("sni", [""])[0]

            # header host / authority
            host_header = params.get("host", [""])[0] or params.get(
                "authority", [""]
            )[0]

            # در برخی لینک‌ها uuid در query با id آمده
            if not uuid:
                uuid = params.get("id", [""])[0]

            return {
                "type": "vless",
                "address": address,
                "port": port,
                "id": uuid,
                "name": name,
                "network": network,
                "sni": sni,
                "host": host_header,
                "security": security,
                "flow": flow,
                "encryption": encryption,
                "headerType": header_type,
                "fingerprint": fingerprint,
                "original": config,
            }

        except Exception as e:
            logger.debug(f"Error parsing VLESS: {e}")
            return None

    @staticmethod
    def _parse_trojan(config: str) -> Optional[Dict]:
        """Parse Trojan config"""
        try:
            pattern = r"trojan://([^@]+)@([^:]+):(\d+)\??([^#]*)#?(.*)"
            match = re.match(pattern, config)

            if not match:
                return None

            password, address, port, params, name = match.groups()
            params_dict = parse_qs(params) if params else {}

            return {
                "type": "trojan",
                "address": address,
                "port": port,
                "password": password,
                "name": ConfigParser._clean_name(name),
                "sni": params_dict.get("sni", [""])[0],
                "host": params_dict.get("host", [""])[0],
                "original": config,
            }
        except Exception as e:
            logger.debug(f"Error parsing Trojan: {e}")
            return None

    # ------------------------------------------------------------------
    #  Shadowsocks / SSR
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_shadowsocks(config: str) -> Optional[Dict]:
        """
        Parse Shadowsocks config

        پشتیبانی از:
        1) فرمت SIP002:
           ss://BASE64(method:password)@host:port#name
        2) فرمت legacy:
           ss://BASE64(method:password@host:port)#name
        3) در صورت لزوم، می‌توانیم ss2022 (بدون base64) را هم اضافه کنیم.

        منطق:
        - اگر نتوانیم هم method و هم password و هم address و port را مطمئن استخراج کنیم → این کانفیگ ss را رد می‌کنیم.
        """
        try:
            clean_config = config.replace("ss://", "")

            # 1. جدا کردن نام (Remark)
            name = ""
            if "#" in clean_config:
                clean_config, name_raw = clean_config.split("#", 1)
                name = ConfigParser._clean_name(name_raw)

            address = ""
            port = ""
            method = ""
            password = ""

            # 2. اگر @ وجود دارد: userinfo با base64 است (فرمت SIP002)
            if "@" in clean_config:
                # userinfo@host:port
                user_info_raw, server_part = clean_config.rsplit("@", 1)

                if ":" not in server_part:
                    return None

                address, port = server_part.rsplit(":", 1)
                address = address.strip("[]")

                # user_info_raw = BASE64(method:password)
                decoded_user = ConfigParser._safe_base64_decode(user_info_raw)
                if not decoded_user or ":" not in decoded_user:
                    return None

                method, password = decoded_user.split(":", 1)

            else:
                # 3. حالت legacy: کل رشته base64(method:password@host:port)
                full_decoded = ConfigParser._safe_base64_decode(clean_config)
                if not full_decoded:
                    return None

                # انتظار: method:password@host:port
                if "@" not in full_decoded:
                    return None

                creds, server_part = full_decoded.rsplit("@", 1)
                if ":" not in server_part:
                    return None

                address, port = server_part.rsplit(":", 1)

                if ":" not in creds:
                    return None
                method, password = creds.split(":", 1)

            # حالا باید method, password, address, port همگی قابل‌اعتماد باشند:

            if not address or not port or not method or not password:
                return None

            # method باید فقط حروف/عدد/نقطه/خط تیره/خط زیرین/علامت + داشته باشد
            if not re.fullmatch(r"[0-9A-Za-z._+\-]+", method):
                logger.debug(f"Invalid Shadowsocks method: {method!r} in {config!r}")
                return None

            # password نباید حاوی کاراکترهای کنترلی یا غیرچاپی باشد
            if not ConfigParser._is_printable_ascii(password):
                logger.debug(f"Invalid Shadowsocks password in {config!r}")
                return None

            return {
                "type": "ss",
                "address": address,
                "port": port,
                "method": method,
                "password": password,
                "name": name,
                "original": config,
            }

        except Exception as e:
            logger.debug(f"Error parsing Shadowsocks: {e}")
            return None

    @staticmethod
    def _parse_ssr(config: str) -> Optional[Dict]:
        """Parse ShadowsocksR config"""
        try:
            config_data = config.replace("ssr://", "")
            decoded = ConfigParser._safe_base64_decode(config_data)

            if not decoded:
                return None

            parts = decoded.split(":")
            if len(parts) >= 6:
                return {
                    "type": "ssr",
                    "address": parts[0],
                    "port": parts[1],
                    "name": "",
                    "original": config,
                }
            return None
        except Exception as e:
            logger.debug(f"Error parsing SSR: {e}")
            return None

    # ------------------------------------------------------------------
    #  Hysteria / TUIC
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_hysteria(config: str) -> Optional[Dict]:
        """Parse Hysteria / Hysteria2 config"""
        try:
            parsed = urlparse(config)
            name = parsed.fragment if parsed.fragment else ""

            return {
                "type": "hysteria" if config.startswith("hysteria://") else "hysteria2",
                "address": parsed.hostname or "",
                "port": str(parsed.port) if parsed.port else "",
                "name": ConfigParser._clean_name(name),
                "original": config,
            }
        except Exception as e:
            logger.debug(f"Error parsing Hysteria: {e}")
            return None

    @staticmethod
    def _parse_tuic(config: str) -> Optional[Dict]:
        """Parse TUIC config"""
        try:
            parsed = urlparse(config)
            name = parsed.fragment if parsed.fragment else ""

            return {
                "type": "tuic",
                "address": parsed.hostname or "",
                "port": str(parsed.port) if parsed.port else "",
                "name": ConfigParser._clean_name(name),
                "original": config,
            }
        except Exception as e:
            logger.debug(f"Error parsing TUIC: {e}")
            return None

    # ------------------------------------------------------------------
    #  Telegram proxy (tg://proxy)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tg_proxy(config: str) -> Optional[Dict]:
        """Parse Telegram MTProto proxy links (tg://proxy, https://t.me/proxy)"""
        try:
            cfg = html.unescape(config.strip())
            parsed = urlparse(cfg)
            scheme = (parsed.scheme or "").lower()
            netloc = (parsed.netloc or "").lower()
            path = (parsed.path or "").lower()

            if scheme == "tg" and parsed.path.lower().startswith("proxy"):
                # tg://proxy?server=...&port=...&secret=...
                query = parsed.query or ""
            elif scheme in ("http", "https") and netloc == "t.me" and path.startswith(
                "/proxy"
            ):
                # https://t.me/proxy?server=...&port=...&secret=...
                query = parsed.query or ""
            else:
                return None

            params = parse_qs(query)

            server = params.get("server", [""])[0]
            port = params.get("port", [""])[0]
            secret = params.get("secret", [""])[0]

            # name می‌تواند در query (پارامتر name) یا در fragment باشد
            name = params.get("name", [parsed.fragment or ""])[0]
            name = ConfigParser._clean_name(name)

            if not server or not port:
                return None

            return {
                "type": "tg",
                "address": server,
                "port": port,
                "secret": secret,
                "name": name,
                "original": config,
            }

        except Exception as e:
            logger.debug(f"Error parsing Telegram proxy: {e}")
            return None

    # ------------------------------------------------------------------
    #  Slipnet
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_slipnet(config: str) -> Optional[Dict]:
        """
        Parse Slipnet config.

        فعلاً فقط خود رشته‌ی کانفیگ را نگه می‌داریم.
        """
        try:
            cfg = config.strip()
            name = ""

            if "#" in cfg:
                base, frag = cfg.split("#", 1)
                cfg = base
                name = ConfigParser._clean_name(frag)

            return {
                "type": "slipnet",
                "name": name,
                "original": cfg,
            }
        except Exception as e:
            logger.debug(f"Error parsing Slipnet: {e}")
            return None

    # ------------------------------------------------------------------
    #  File-based configs (.ovpn / .npvt / .config / .txt)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_file_link(config: str) -> Optional[Dict]:
        """
        Parse links that point to config files:
          - .ovpn (OpenVPN)
          - .npvt / .npv (Napsternet)
          - .conf / .config (فایل کانفیگ)
          - .txt (فایل متنی)

        پسوند هم از path و هم از fragment (مثلاً #@proxy_kafee🚀🌜.ovpn) بررسی می‌شود.

        لینک‌های ساده بدون پسوند (مثل https://t.me:443) این‌جا نمی‌آیند، چون در parse_config رد شده‌اند.
        """
        try:
            url = config.strip().strip('\'"')
            parsed = urlparse(url)
            path = parsed.path or ""
            fragment = parsed.fragment or ""

            ext = None

            # ۱) تلاش برای گرفتن پسوند از path
            if "." in path:
                ext = path.rsplit(".", 1)[-1].lower()
            # ۲) اگر در path نبود، از fragment
            elif "." in fragment:
                ext = fragment.rsplit(".", 1)[-1].lower()

            if not ext:
                return None

            if ext == "ovpn":
                type_name = "ovpn"
            elif ext in ("npvt", "npv"):
                type_name = "npvt"
            elif ext in ("conf", "config"):
                type_name = "config_file"
            elif ext == "txt":
                type_name = "txt_file"
            else:
                return None

            # نام: اگر fragment وجود دارد، اولویت با آن؛ در غیر این‌صورت نام فایل از path
            name = fragment or os.path.basename(path)
            name = ConfigParser._clean_name(name)

            return {
                "type": type_name,
                "file_url": url,
                "name": name,
                "original": url,
            }
        except Exception as e:
            logger.debug(f"Error parsing file link: {e}")
            return None
