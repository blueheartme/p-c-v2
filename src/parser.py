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

    @staticmethod
    def _safe_base64_decode(data: str) -> str:
        """Helper method to safely decode Base64 strings with various quirks"""
        if not data:
            return ""

        data = unquote(data)
        data = data.strip()
        data = data.replace("-", "+").replace("_", "/")

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
    def parse_config(config: str) -> Optional[Dict]:
        """Parse a proxy config and extract information"""
        try:
            config = config.strip().strip('\'"')
            lower = config.lower()

            if lower.startswith("vmess://"):
                return ConfigParser._parse_vmess(config)
            elif lower.startswith("vless://"):
                return ConfigParser._parse_vless(config)
            elif lower.startswith("trojan://"):
                return ConfigParser._parse_trojan(config)
            elif lower.startswith("ss://"):
                return ConfigParser._parse_shadowsocks(config)
            elif lower.startswith("ssr://"):
                return ConfigParser._parse_ssr(config)
            elif lower.startswith("hysteria://") or lower.startswith("hysteria2://"):
                return ConfigParser._parse_hysteria(config)
            elif lower.startswith("tuic://"):
                return ConfigParser._parse_tuic(config)
            # پروکسی‌های تلگرام
            elif lower.startswith("tg://proxy?") or lower.startswith(
                "https://t.me/proxy?"
            ):
                return ConfigParser._parse_tg_proxy(config)
            # Slipnet (کانفیگ متنی)
            elif lower.startswith("slipnet"):
                return ConfigParser._parse_slipnet(config)
            # لینک‌های http/https (ممکن است #filename هم داشته باشند)
            elif lower.startswith("http://") or lower.startswith("https://"):
                return ConfigParser._parse_file_link(config)
            else:
                return None
        except Exception as e:
            logger.debug(f"Error parsing config: {e}")
            return None

    # ======================= V2Ray / Shadowsocks / ... =======================

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
        """Parse VLESS config (پایدار و کامل‌تر)"""
        try:
            cfg_str = html.unescape(config)
            parsed = urlparse(cfg_str)

            if parsed.scheme.lower() != "vless":
                return None

            uuid = parsed.username or ""
            address = parsed.hostname or ""
            port = str(parsed.port or "")

            name = parsed.fragment or ""
            name = ConfigParser._clean_name(name)

            params = parse_qs(parsed.query or "")

            network = params.get("type", [""])[0].lower()
            security = params.get("security", [""])[0].lower()
            flow = params.get("flow", [""])[0]
            encryption = params.get("encryption", [""])[0].lower()
            header_type = params.get("headerType", [""])[0].lower()
            fingerprint = params.get(
                "fp", params.get("fingerprint", [""])
            )[0].lower()
            sni = params.get("sni", [""])[0]
            host_header = params.get("host", [""])[0] or params.get(
                "authority", [""]
            )[0]

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

    @staticmethod
    def _parse_shadowsocks(config: str) -> Optional[Dict]:
        """Parse Shadowsocks config"""
        try:
            clean_config = config.replace("ss://", "")

            name = ""
            if "#" in clean_config:
                clean_config, name_raw = clean_config.split("#", 1)
                name = ConfigParser._clean_name(name_raw)

            address = ""
            port = ""
            decoded_info = ""

            if "@" in clean_config:
                user_info_raw, server_part = clean_config.rsplit("@", 1)

                if ":" in server_part:
                    address, port = server_part.rsplit(":", 1)
                    address = address.strip("[]")
                else:
                    return None

                decoded_info = ConfigParser._safe_base64_decode(user_info_raw)

            else:
                full_decoded = ConfigParser._safe_base64_decode(clean_config)

                if "@" in full_decoded:
                    decoded_info, server_part = full_decoded.rsplit("@", 1)
                    if ":" in server_part:
                        address, port = server_part.rsplit(":", 1)
                    else:
                        return None
                else:
                    return None

            if not decoded_info:
                return None

            if ":" in decoded_info:
                method, password = decoded_info.split(":", 1)
            else:
                method = decoded_info
                password = ""

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

    @staticmethod
    def _parse_hysteria(config: str) -> Optional[Dict]:
        """Parse Hysteria config"""
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

    # ======================= Telegram proxy (tg://proxy) =======================

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
                query = parsed.query or ""
            elif scheme in ("http", "https") and netloc == "t.me" and path.startswith(
                "/proxy"
            ):
                query = parsed.query or ""
            else:
                return None

            params = parse_qs(query)

            server = params.get("server", [""])[0]
            port = params.get("port", [""])[0]
            secret = params.get("secret", [""])[0]

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

    # ======================= Slipnet =======================

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

    # ======================= File-based configs =======================

    @staticmethod
    def _parse_file_link(config: str) -> Optional[Dict]:
        """
        Parse links that point to config files:
          - .ovpn (OpenVPN)
          - .npvt / .npv (Napsternet)
          - .conf / .config (فایل کانفیگ)
          - .txt (فایل متنی)

        پسوند هم از path و هم از fragment (مثلاً #@proxy_kafee🚀🌜.ovpn) بررسی می‌شود.
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
