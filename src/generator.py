"""
Generator module for creating output files with standard protocol-based naming
All transmission types supported: tcp, ws, grpc, h2, kcp, quic, httpupgrade, xhttp
"""

import os
import json
import base64
import logging
import re
import html
from typing import Dict, List, Optional
from datetime import datetime
from urllib.parse import quote, parse_qs
from .config import *  # شامل get_country_flag, مسیرهای by_protocol و ...

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OutputGenerator:
    """Generate output files in different formats"""

    def __init__(self):
        self._ensure_directories()

    def _ensure_directories(self):
        """Create output directories if they don't exist"""
        for directory in [
            OUTPUT_DIR,
            IRAN_DIR,
            GERMANY_DIR,
            OTHERS_DIR,
            TESTED_DIR,
            BY_PROTOCOL_ALL_DIR,
            BY_PROTOCOL_TESTED_DIR,
        ]:
            os.makedirs(directory, exist_ok=True)

    def generate_all_outputs(
        self,
        categorized_configs: Dict[str, List[Dict]],
        tested_configs: Dict[str, List[Dict]],
        extra_configs: Optional[List[Dict]] = None,
    ):
        """
        Generate all output formats.

        - categorized_configs: خروجی فیلتر بر اساس کشور
        - tested_configs: کانفیگ‌های تست‌شده (بر اساس کشور)
        - extra_configs: کانفیگ‌هایی که کشور ندارند (Slipnet، فایل‌ها و ...) و فقط در by-protocol می‌آیند.
        """
        logger.info("Generating output files...")

        try:
            # 1) خروجی بر اساس کشور (منطق قبلی، بدون تغییر)
            for country, configs in categorized_configs.items():
                logger.info(
                    f"Generating outputs for {country} with {len(configs)} configs"
                )
                self._generate_country_outputs(country, configs, tested=False)

            for country, configs in tested_configs.items():
                logger.info(
                    f"Generating tested outputs for {country} with {len(configs)} configs"
                )
                self._generate_country_outputs(country, configs, tested=True)

            # 2) گروه‌بندی بر اساس پروتکل (در سطح سراسری، همراه با extra_configs)
            all_for_protocol: List[Dict] = []
            for configs in categorized_configs.values():
                all_for_protocol.extend(configs)

            if extra_configs:
                all_for_protocol.extend(extra_configs)

            tested_for_protocol: List[Dict] = []
            for configs in tested_configs.values():
                tested_for_protocol.extend(configs)

            protocol_all = self._group_by_protocol(all_for_protocol)
            protocol_tested = self._group_by_protocol(tested_for_protocol)

            self._generate_by_protocol_outputs(protocol_all, protocol_tested)

            # 3) README
            self._generate_readme(
                categorized_configs, tested_configs, protocol_all, protocol_tested
            )

            logger.info("Output generation complete!")

        except Exception as e:
            logger.error(f"Error generating outputs: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # گروه‌بندی بر اساس پروتکل
    # ------------------------------------------------------------------

    def _group_by_protocol(
        self, configs: List[Dict]
    ) -> Dict[str, List[Dict]]:
        """
        دسته‌بندی کانفیگ‌ها بر اساس پروتکل (type)، مستقل از کشور.
        ورودی: لیست کلی از کانفیگ‌ها
        خروجی: دیکشنری protocol -> list[config]
        """
        grouped: Dict[str, List[Dict]] = {}
        for config in configs or []:
            proto = str(config.get("type", "unknown") or "unknown").lower()
            grouped.setdefault(proto, []).append(config)
        return grouped

    def _generate_by_protocol_outputs(
        self,
        protocol_all: Dict[str, List[Dict]],
        protocol_tested: Dict[str, List[Dict]],
    ):
        """
        تولید خروجی‌ها بر اساس پروتکل، در دو سطح:
          - output/by_protocol/all/<protocol>/
          - output/by_protocol/tested/<protocol>/
        و در هر پروتکل، خروجی‌های جدا بر اساس کشور در زیرپوشه by_country.
        """
        logger.info("Generating by-protocol outputs (all configs)...")

        # ALL
        for proto, configs in protocol_all.items():
            if not configs:
                continue

            proto_dir = os.path.join(BY_PROTOCOL_ALL_DIR, proto)
            os.makedirs(proto_dir, exist_ok=True)

            logger.info(f"  Protocol {proto}: {len(configs)} configs (all)")

            # همه کشورها باهم
            self._generate_json(proto_dir, f"{proto}.json", configs)
            self._generate_txt(proto_dir, f"{proto}.txt", configs)
            self._generate_subscription(
                proto_dir, f"{proto}_subscription.txt", configs
            )

            # تفکیک بر اساس کشور برای این پروتکل
            self._generate_by_country_for_protocol(proto_dir, proto, configs, tested=False)

        # TESTED
        logger.info("Generating by-protocol outputs (tested configs)...")

        for proto, configs in protocol_tested.items():
            if not configs:
                continue

            proto_dir = os.path.join(BY_PROTOCOL_TESTED_DIR, proto)
            os.makedirs(proto_dir, exist_ok=True)

            logger.info(f"  Protocol {proto}: {len(configs)} tested configs")

            # همه کشورها باهم
            self._generate_json(proto_dir, f"tested_{proto}.json", configs)
            self._generate_txt(proto_dir, f"tested_{proto}.txt", configs)
            self._generate_subscription(
                proto_dir, f"tested_{proto}_subscription.txt", configs
            )

            # تفکیک بر اساس کشور برای این پروتکل (فقط تست‌شده‌ها)
            self._generate_by_country_for_protocol(proto_dir, proto, configs, tested=True)

    def _generate_by_country_for_protocol(
        self,
        proto_root_dir: str,
        proto: str,
        configs: List[Dict],
        tested: bool = False,
    ):
        """
        برای یک پروتکل خاص (مثلاً tg یا vmess)، خروجی‌های جدا بر اساس country تولید می‌کند:

        خروجی:
          proto_root_dir/
            by_country/
              ir/
                configs.json
                configs.txt
                subscription.txt
              de/
                ...
        """
        # گروه‌بندی بر اساس country
        by_country: Dict[str, List[Dict]] = {}
        for cfg in configs:
            country = cfg.get("country")
            if not country:
                continue
            by_country.setdefault(country.upper(), []).append(cfg)

        if not by_country:
            return

        base_dir = os.path.join(proto_root_dir, "by_country")
        os.makedirs(base_dir, exist_ok=True)

        kind = "tested" if tested else "all"
        logger.info(
            f"    Generating per-country outputs for protocol {proto} ({kind}) "
            f"for {len(by_country)} countries"
        )

        for country, country_configs in by_country.items():
            country_dir = os.path.join(base_dir, country.lower())
            os.makedirs(country_dir, exist_ok=True)

            # برای سادگی، مثل ساختار اصلی کشورها از نام‌های ثابت استفاده می‌کنیم
            self._generate_json(country_dir, "configs.json", country_configs)
            self._generate_txt(country_dir, "configs.txt", country_configs)
            self._generate_subscription(
                country_dir, "subscription.txt", country_configs
            )

    # ------------------------------------------------------------------
    # خروجی بر اساس کشور (ساختار اصلی، بدون تغییر در منطق)
    # ------------------------------------------------------------------

    def _generate_country_outputs(
        self, country: str, configs: List[Dict], tested: bool = False
    ):
        """Generate outputs for a specific country"""
        try:
            if tested:
                base_dir = TESTED_DIR
                prefix = "tested_"
            elif country == "IR":
                base_dir = IRAN_DIR
                prefix = ""
            elif country == "DE":
                base_dir = GERMANY_DIR
                prefix = ""
            else:
                base_dir = OTHERS_DIR
                prefix = ""

            country_dir = os.path.join(base_dir, country.lower())
            os.makedirs(country_dir, exist_ok=True)

            rebuilt_configs = self._rebuild_configs_with_standard_names(
                configs, country
            )

            logger.info(f"Rebuilt {len(rebuilt_configs)} configs for {country}")

            if not rebuilt_configs:
                logger.warning(f"No configs to generate for {country}!")
                return

            self._generate_json(
                country_dir, prefix + "configs.json", rebuilt_configs
            )
            self._generate_txt(country_dir, prefix + "configs.txt", rebuilt_configs)
            self._generate_subscription(
                country_dir, prefix + "subscription.txt", rebuilt_configs
            )

            logger.info(
                f"✅ Generated outputs for {country} ({'tested' if tested else 'all'})"
            )

        except Exception as e:
            logger.error(
                f"Error generating country outputs for {country}: {e}", exc_info=True
            )

    # ------------------------------------------------------------------
    # بخش نام‌گذاری و rebuild کانفیگ‌ها (بدون تغییر نسبت به نسخهٔ قبلی)
    # ------------------------------------------------------------------

    def _rebuild_configs_with_standard_names(
        self, configs: List[Dict], country: str
    ) -> List[Dict]:
        """Rebuild configs with standard protocol-based naming"""
        rebuilt = []

        logger.info(f"Rebuilding {len(configs)} configs for {country}...")

        for idx, config in enumerate(configs, 1):
            try:
                cfg_type = str(config.get("type", "")).lower()

                # Shadowsocks را دست نمی‌زنیم (قبلاً ثابت شده درست است)
                if cfg_type == "ss":
                    config["rebuilt"] = config.get("original", "")
                    rebuilt.append(config)
                    continue

                new_name = self._build_standard_name(config, country, idx)
                logger.debug(f"Config {idx}: New name = {new_name}")

                new_config = self._rebuild_config_with_name(config, new_name)

                if new_config:
                    config["rebuilt"] = new_config
                    rebuilt.append(config)
                else:
                    logger.warning(
                        f"Failed to rebuild config {idx}, using original"
                    )
                    config["rebuilt"] = config.get("original", "")
                    rebuilt.append(config)

            except Exception as e:
                logger.error(f"Error rebuilding config {idx}: {e}")
                config["rebuilt"] = config.get("original", "")
                rebuilt.append(config)

        logger.info(f"Successfully rebuilt {len(rebuilt)} configs")
        return rebuilt

    def _build_standard_name(self, config: Dict, country: str, idx: int) -> str:
        protocol = config.get("type", "unknown").lower()

        try:
            if protocol == "vless":
                return self._build_vless_name(config, country, idx)
            elif protocol == "vmess":
                return self._build_vmess_name(config, country, idx)
            elif protocol == "trojan":
                return self._build_trojan_name(config, country, idx)
            elif protocol == "ss":
                return self._build_shadowsocks_name(config, country, idx)
            elif protocol == "ssr":
                return self._build_ssr_name(config, country, idx)
            elif protocol in ["hysteria", "hysteria2"]:
                return self._build_hysteria_name(config, country, idx)
            elif protocol == "tuic":
                return self._build_tuic_name(config, country, idx)
            else:
                flag = get_country_flag(country)
                return f"{protocol}-{country}{flag}-{idx}"
        except Exception as e:
            logger.error(f"Error in _build_standard_name: {e}")
            flag = get_country_flag(country)
            return f"{protocol}-{country}{flag}-{idx}"

    def _build_vless_name(self, config: Dict, country: str, idx: int) -> str:
        parts = ["vless"]

        try:
            original = config.get("original", "")
            params = self._extract_vless_params(original)

            flow = (config.get("flow") or params.get("flow", "") or "").lower()
            if flow and flow not in ["none", ""]:
                parts.append(flow)

            encryption = (
                config.get("encryption") or params.get("encryption", "") or ""
            ).lower()
            if encryption and encryption not in ["none", ""]:
                parts.append(encryption)

            network = (config.get("network") or params.get("type", "") or "").lower()
            if not network:
                network = "tcp"
            parts.append(network)

            header_type = (
                config.get("headerType") or params.get("headerType", "") or ""
            ).lower()
            if header_type and header_type not in ["none", ""]:
                parts.append(header_type)

            security = (
                config.get("security") or params.get("security", "") or ""
            ).lower()
            if security and security not in ["none", ""]:
                parts.append(security)

            fingerprint = (
                config.get("fingerprint")
                or params.get("fp", params.get("fingerprint", ""))
                or ""
            ).lower()
            if fingerprint and fingerprint not in ["none", ""]:
                parts.append(fingerprint)

            cdn = config.get("cdn", "")
            if cdn:
                cdn_name = CDN_NAMES.get(cdn, cdn).replace("☁️", "").strip()
                parts.append(cdn_name)

        except Exception as e:
            logger.debug(f"Error building VLESS name: {e}")

        flag = get_country_flag(country)
        parts.append(f"{country}{flag}")
        parts.append(str(idx))

        return "-".join(parts)

    def _build_vmess_name(self, config: Dict, country: str, idx: int) -> str:
        parts = ["vmess"]

        try:
            vmess_data = self._extract_vmess_data(config.get("original", ""))

            scy = vmess_data.get("scy", "")
            if scy and scy not in ["", "none", "auto"]:
                parts.append(scy)
            elif scy == "auto":
                parts.append("auto")

            network = vmess_data.get("net", config.get("network", "")).lower()
            if not network or network == "":
                network = "tcp"
            parts.append(network)

            header_type = vmess_data.get("type", "")
            if header_type and header_type not in ["none", "", "http"]:
                parts.append(header_type)

            tls = vmess_data.get("tls", "")
            if tls and tls not in ["none", ""]:
                parts.append(tls)

            cdn = config.get("cdn", "")
            if cdn:
                cdn_name = CDN_NAMES.get(cdn, cdn).replace("☁️", "").strip()
                parts.append(cdn_name)

        except Exception as e:
            logger.debug(f"Error building VMESS name: {e}")

        flag = get_country_flag(country)
        parts.append(f"{country}{flag}")
        parts.append(str(idx))

        return "-".join(parts)

    def _build_trojan_name(self, config: Dict, country: str, idx: int) -> str:
        parts = ["trojan"]

        try:
            original = config.get("original", "")
            params = self._extract_trojan_params(original)

            network = params.get("type", config.get("network", "")).lower()
            if not network or network == "":
                network = "tcp"
            parts.append(network)

            header_type = params.get("headerType", "")
            if header_type and header_type not in ["none", ""]:
                parts.append(header_type)

            security = params.get("security", "")
            if security and security not in ["none", ""]:
                parts.append(security)
            elif not security:
                parts.append("tls")

            cdn = config.get("cdn", "")
            if cdn:
                cdn_name = CDN_NAMES.get(cdn, cdn).replace("☁️", "").strip()
                parts.append(cdn_name)

        except Exception as e:
            logger.debug(f"Error building Trojan name: {e}")

        flag = get_country_flag(country)
        parts.append(f"{country}{flag}")
        parts.append(str(idx))

        return "-".join(parts)

    def _build_shadowsocks_name(self, config: Dict, country: str, idx: int) -> str:
        parts = ["ss"]

        method = str(config.get("method", "") or "").lower()
        if method:
            method = method.replace("_", "-")
            method = re.sub(r"[^a-z0-9.\-]+", "", method)
            if method:
                parts.append(method)

        plugin = str(config.get("plugin", "") or "")
        plugin = plugin.lower().strip()
        if plugin and plugin not in ["none", ""]:
            plugin = re.sub(r"[^a-z0-9.\-]+", "", plugin)
            if plugin:
                parts.append(plugin)

        cdn = config.get("cdn", "")
        if cdn:
            cdn_name = CDN_NAMES.get(cdn, cdn).replace("☁️", "").strip()
            parts.append(cdn_name)

        flag = get_country_flag(country)
        parts.append(f"{country}{flag}")
        parts.append(str(idx))

        return "-".join(parts)

    def _build_ssr_name(self, config: Dict, country: str, idx: int) -> str:
        parts = ["ssr"]
        flag = get_country_flag(country)
        parts.append(f"{country}{flag}")
        parts.append(str(idx))
        return "-".join(parts)

    def _build_hysteria_name(self, config: Dict, country: str, idx: int) -> str:
        protocol_type = config.get("type", "hysteria")
        parts = [protocol_type, "udp"]

        cdn = config.get("cdn", "")
        if cdn:
            cdn_name = CDN_NAMES.get(cdn, cdn).replace("☁️", "").strip()
            parts.append(cdn_name)

        flag = get_country_flag(country)
        parts.append(f"{country}{flag}")
        parts.append(str(idx))
        return "-".join(parts)

    def _build_tuic_name(self, config: Dict, country: str, idx: int) -> str:
        parts = ["tuic", "udp"]

        cdn = config.get("cdn", "")
        if cdn:
            cdn_name = CDN_NAMES.get(cdn, cdn).replace("☁️", "").strip()
            parts.append(cdn_name)

        flag = get_country_flag(country)
        parts.append(f"{country}{flag}")
        parts.append(str(idx))
        return "-".join(parts)

    # ------------------------------------------------------------------
    # Helperها برای VLESS/VMESS/Trojan
    # ------------------------------------------------------------------

    def _extract_vless_params(self, config_str: str) -> dict:
        try:
            if "?" not in config_str:
                return {}

            cfg = html.unescape(config_str)
            params_part = cfg.split("?")[1].split("#")[0]
            params = parse_qs(params_part)

            result = {}
            for key, value in params.items():
                result[key] = value[0] if len(value) == 1 else value

            return result
        except Exception as e:
            logger.debug(f"Error extracting VLESS params: {e}")
            return {}

    def _extract_trojan_params(self, config_str: str) -> dict:
        try:
            if "?" not in config_str:
                return {}

            params_part = config_str.split("?")[1].split("#")[0]
            params = parse_qs(params_part)

            result = {}
            for key, value in params.items():
                result[key] = value[0] if len(value) == 1 else value

            return result
        except Exception as e:
            logger.debug(f"Error extracting Trojan params: {e}")
            return {}

    def _extract_vmess_data(self, config_str: str) -> dict:
        try:
            config_data = config_str.replace("vmess://", "")
            padding = 4 - len(config_data) % 4
            if padding != 4:
                config_data += "=" * padding
            decoded = base64.b64decode(config_data).decode("utf-8")
            data = json.loads(decoded)
            return data
        except Exception as e:
            logger.debug(f"Error extracting VMess data: {e}")
            return {}

    # ------------------------------------------------------------------
    # Rebuild های پروتکل‌ها
    # ------------------------------------------------------------------

    def _rebuild_config_with_name(self, config: Dict, new_name: str) -> str:
        config_type = config.get("type", "")
        original = config.get("original", "")

        if not original:
            logger.warning("Config has no original string!")
            return ""

        try:
            if config_type == "vmess":
                return self._rebuild_vmess(original, new_name)
            elif config_type == "vless":
                return self._rebuild_vless(original, new_name)
            elif config_type == "trojan":
                return self._rebuild_trojan(original, new_name)
            elif config_type == "ss":
                return self._rebuild_shadowsocks(original, new_name)
            elif config_type == "ssr":
                return self._rebuild_ssr(original, new_name)
            elif config_type in ["hysteria", "hysteria2"]:
                return self._rebuild_hysteria(original, new_name)
            elif config_type == "tuic":
                return self._rebuild_tuic(original, new_name)
            else:
                logger.warning(f"Unknown config type: {config_type}")
                return original
        except Exception as e:
            logger.error(f"Error rebuilding {config_type}: {e}")
            return original

    def _rebuild_vmess(self, original: str, new_name: str) -> str:
        try:
            config_data = original.replace("vmess://", "")
            padding = 4 - len(config_data) % 4
            if padding != 4:
                config_data += "=" * padding
            decoded = base64.b64decode(config_data).decode("utf-8")
            data = json.loads(decoded)
            data["ps"] = new_name
            new_json = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            new_b64 = base64.b64encode(new_json.encode("utf-8")).decode("utf-8")
            return "vmess://" + new_b64
        except Exception as e:
            logger.debug(f"Error rebuilding VMess: {e}")
            return original

    def _rebuild_vless(self, original: str, new_name: str) -> str:
        try:
            base = original.split("#")[0] if "#" in original else original
            encoded_name = quote(
                new_name,
                safe="🇮🇷🇩🇪🇺🇸🇬🇧🇫🇷🇳🇱🇨🇦🇸🇬🇯🇵🇰🇷🇭🇰🇹🇼🇦🇺🇮🇳🇷🇺🇹🇷🇦🇪🇸🇪🇫🇮🇵🇱🇺🇦🇧🇷🇦🇷🇲🇽🇿🇦🇪🇬🇨🇭🇦🇹🌐-",
            )
            return f"{base}#{encoded_name}"
        except Exception as e:
            logger.debug(f"Error rebuilding VLESS: {e}")
            return original

    def _rebuild_trojan(self, original: str, new_name: str) -> str:
        try:
            base = original.split("#")[0] if "#" in original else original
            encoded_name = quote(
                new_name,
                safe="🇮🇷🇩🇪🇺🇸🇬🇧🇫🇷🇳🇱🇨🇦🇸🇬🇯🇵🇰🇷🇭🇰🇹🇼🇦🇺🇮🇳🇷🇺🇹🇷🇦🇪🇸🇪🇫🇮🇵🇱🇺🇦🇧🇷🇦🇷🇲🇽🇿🇦🇪🇬🇨🇭🇦🇹🌐-",
            )
            return f"{base}#{encoded_name}"
        except Exception as e:
            logger.debug(f"Error rebuilding Trojan: {e}")
            return original

    def _rebuild_shadowsocks(self, original: str, new_name: str) -> str:
        try:
            base = original.split("#")[0] if "#" in original else original
            encoded_name = quote(
                new_name,
                safe="🇮🇷🇩🇪🇺🇸🇬🇧🇫🇷🇳🇱🇨🇦🇸🇬🇯🇵🇰🇷🇭🇰🇹🇼🇦🇺🇮🇳🇷🇺🇹🇷🇦🇪🇸🇪🇫🇮🇵🇱🇺🇦🇧🇷🇦🇷🇲🇽🇿🇦🇪🇬🇨🇭🇦🇹🌐-",
            )
            return f"{base}#{encoded_name}"
        except Exception as e:
            logger.debug(f"Error rebuilding SS: {e}")
            return original

    def _rebuild_ssr(self, original: str, new_name: str) -> str:
        return original

    def _rebuild_hysteria(self, original: str, new_name: str) -> str:
        try:
            base = original.split("#")[0] if "#" in original else original
            encoded_name = quote(
                new_name,
                safe="🇮🇷🇩🇪🇺🇸🇬🇧🇫🇷🇳🇱🇨🇦🇸🇬🇯🇵🇰🇷🇭🇰🇹🇼🇦🇺🇮🇳🇷🇺🇹🇷🇦🇪🇸🇪🇫🇮🇵🇱🇺🇦🇧🇷🇦🇷🇲🇽🇿🇦🇪🇬🇨🇭🇦🇹🌐-",
            )
            return f"{base}#{encoded_name}"
        except Exception as e:
            logger.debug(f"Error rebuilding Hysteria: {e}")
            return original

    def _rebuild_tuic(self, original: str, new_name: str) -> str:
        try:
            base = original.split("#")[0] if "#" in original else original
            encoded_name = quote(
                new_name,
                safe="🇮🇷🇩🇪🇺🇸🇬🇧🇫🇷🇳🇱🇨🇦🇸🇬🇯🇵🇰🇷🇭🇰🇹🇼🇦🇺🇮🇳🇷🇺🇹🇷🇦🇪🇸🇪🇫🇮🇵🇱🇺🇦🇧🇷🇦🇷🇲🇽🇿🇦🇪🇬🇨🇭🇦🇹🌐-",
            )
            return f"{base}#{encoded_name}"
        except Exception as e:
            logger.debug(f"Error rebuilding TUIC: {e}")
            return original

    # ------------------------------------------------------------------
    # تولید JSON/TXT/Subscription
    # ------------------------------------------------------------------

    def _generate_json(self, directory: str, filename: str, configs: List[Dict]):
        try:
            filepath = os.path.join(directory, filename)

            output_data = {
                "updated": datetime.utcnow().isoformat(),
                "count": len(configs),
                "configs": [],
            }

            for config in configs:
                output_config = config.copy()
                output_config["original"] = config.get(
                    "rebuilt", config.get("original", "")
                )
                output_data["configs"].append(output_config)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Generated JSON: {filepath}")

        except Exception as e:
            logger.error(f"Error generating JSON: {e}", exc_info=True)

    def _generate_txt(self, directory: str, filename: str, configs: List[Dict]):
        try:
            filepath = os.path.join(directory, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                for config in configs:
                    config_str = config.get("rebuilt", config.get("original", ""))
                    if config_str:
                        f.write(config_str + "\n")

            logger.info(f"✅ Generated TXT: {filepath}")

        except Exception as e:
            logger.error(f"Error generating TXT: {e}", exc_info=True)

    def _generate_subscription(
        self, directory: str, filename: str, configs: List[Dict]
    ):
        try:
            filepath = os.path.join(directory, filename)

            config_lines = []
            for config in configs:
                config_str = config.get("rebuilt", config.get("original", ""))
                if config_str:
                    config_lines.append(config_str)

            if not config_lines:
                logger.warning("No config lines to encode for subscription!")
                return

            all_configs = "\n".join(config_lines)
            encoded = base64.b64encode(all_configs.encode("utf-8")).decode("utf-8")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(encoded)

            logger.info(f"✅ Generated Subscription: {filepath}")

        except Exception as e:
            logger.error(f"Error generating subscription: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # README
    # ------------------------------------------------------------------

    def _generate_readme(
        self,
        all_configs: Dict[str, List[Dict]],
        tested_configs: Dict[str, List[Dict]],
        protocol_all: Dict[str, List[Dict]],
        protocol_tested: Dict[str, List[Dict]],
    ):
        try:
            readme_path = os.path.join(OUTPUT_DIR, "README.md")

            with open(readme_path, "w", encoding="utf-8") as f:
                f.write("# 🌐 Free Proxy Configs\n\n")
                f.write(
                    f"**Last Updated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                )

                f.write("## 📊 Statistics\n\n")

                total_configs = sum(len(configs) for configs in all_configs.values())
                total_tested = sum(len(configs) for configs in tested_configs.values())
                total_countries = len(all_configs)
                total_protocols = len(protocol_all)

                f.write(f"- **Total Configs:** {total_configs}\n")
                f.write(f"- **Tested & Working:** {total_tested}\n")
                f.write(f"- **Countries:** {total_countries}\n")
                f.write(f"- **Protocols:** {total_protocols}\n\n")

                if "IR" in all_configs:
                    ir_count = len(all_configs["IR"])
                    ir_tested = len(tested_configs.get("IR", []))
                    f.write("## 🇮🇷 Iran Configs (Priority)\n\n")
                    f.write(f"- **Total:** {ir_count}\n")
                    f.write(f"- **Tested:** {ir_tested}\n\n")
                    f.write("### 📥 Download Links:\n")
                    f.write("- [JSON](iran/ir/configs.json)\n")
                    f.write("- [TXT](iran/ir/configs.txt)\n")
                    f.write("- [Subscription](iran/ir/subscription.txt)\n")
                    if ir_tested > 0:
                        f.write(
                            "- [Tested Subscription](tested/ir/tested_subscription.txt) ✅\n"
                        )
                    f.write("\n")

                if "DE" in all_configs:
                    de_count = len(all_configs["DE"])
                    de_tested = len(tested_configs.get("DE", []))
                    f.write("## 🇩🇪 Germany Configs\n\n")
                    f.write(f"- **Total:** {de_count}\n")
                    f.write(f"- **Tested:** {de_tested}\n\n")
                    f.write("### 📥 Download Links:\n")
                    f.write("- [JSON](germany/de/configs.json)\n")
                    f.write("- [TXT](germany/de/configs.txt)\n")
                    f.write("- [Subscription](germany/de/subscription.txt)\n")
                    if de_tested > 0:
                        f.write(
                            "- [Tested Subscription](tested/de/tested_subscription.txt) ✅\n"
                        )
                    f.write("\n")

                other_countries = [
                    c for c in all_configs.keys() if c not in ["IR", "DE"]
                ]
                if other_countries:
                    f.write("## 🌍 Other Countries\n\n")
                    for country in sorted(other_countries):
                        flag = get_country_flag(country)
                        count = len(all_configs[country])
                        f.write(f"### {flag} {country}\n")
                        f.write(f"- **Count:** {count}\n")
                        f.write(
                            f"- [JSON](others/{country.lower()}/configs.json) | "
                        )
                        f.write(
                            f"[TXT](others/{country.lower()}/configs.txt) | "
                        )
                        f.write(
                            f"[Subscription](others/{country.lower()}/subscription.txt)\n\n"
                        )

                if protocol_all:
                    f.write("## 🔀 By Protocol (All Countries & Extra)\n\n")
                    f.write(
                        "Aggregated configs by protocol across all countries and extra types (Slipnet, file refs, ...):\n\n"
                    )

                    for proto in sorted(protocol_all.keys()):
                        total_p = len(protocol_all.get(proto, []))
                        tested_p = len(protocol_tested.get(proto, []))

                        f.write(f"### `{proto}`\n")
                        f.write(f"- **Total:** {total_p}\n")
                        if tested_p:
                            f.write(f"- **Tested:** {tested_p}\n")
                        f.write(
                            f"- [JSON](by_protocol/all/{proto}/{proto}.json) | "
                        )
                        f.write(
                            f"[TXT](by_protocol/all/{proto}/{proto}.txt) | "
                        )
                        f.write(
                            f"[Subscription](by_protocol/all/{proto}/{proto}_subscription.txt)\n"
                        )

                        if tested_p:
                            f.write(
                                f"  - Tested: [JSON](by_protocol/tested/{proto}/tested_{proto}.json) | "
                            )
                            f.write(
                                f"[TXT](by_protocol/tested/{proto}/tested_{proto}.txt) | "
                            )
                            f.write(
                                f"[Subscription](by_protocol/tested/{proto}/tested_{proto}_subscription.txt)\n"
                            )

                        f.write("\n")

                f.write("\n---\n")
                f.write("*🤖 Auto-updated via GitHub Actions*\n")

            logger.info(f"✅ Generated README: {readme_path}")

        except Exception as e:
            logger.error(f"Error generating README: {e}", exc_info=True)
