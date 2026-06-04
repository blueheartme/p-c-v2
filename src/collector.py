"""
Collector module for gathering proxy configs from various sources
"""

import re
import requests
import logging
import html
from typing import Set
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigCollector:
    """Main collector class for gathering configs from multiple sources"""

    def __init__(self):
        self.configs: Set[str] = set()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    def collect_all(self) -> Set[str]:
        """Collect configs from all sources"""
        logger.info("Starting config collection from all sources...")

        try:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = []

                futures.append(executor.submit(self.collect_from_github))
                futures.append(executor.submit(self.collect_from_telegram))
                futures.append(executor.submit(self.collect_from_apis))
                futures.append(executor.submit(self.collect_from_web))

                for future in as_completed(futures):
                    try:
                        configs = future.result()
                        self.configs.update(configs)
                    except Exception as e:
                        logger.error(f"Error in collection task: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error in collect_all: {e}")

        logger.info(f"Total configs collected: {len(self.configs)}")
        return self.configs

    def collect_from_github(self) -> Set[str]:
        """Collect configs from GitHub repositories"""
        configs = set()
        logger.info("Collecting from GitHub repositories...")

        for repo in GITHUB_REPOS:
            try:
                paths = [
                    f"https://raw.githubusercontent.com/{repo}/main/sub/mix",
                    f"https://raw.githubusercontent.com/{repo}/main/sub/base64",
                    f"https://raw.githubusercontent.com/{repo}/master/sub/mix",
                    f"https://raw.githubusercontent.com/{repo}/main/configs.txt",
                    f"https://raw.githubusercontent.com/{repo}/master/v2ray",
                ]

                for url in paths:
                    try:
                        response = self.session.get(url, timeout=CONNECTION_TIMEOUT)
                        if response.status_code == 200:
                            extracted = self._extract_configs_from_text(response.text)
                            configs.update(extracted)
                            logger.info(f"Found {len(extracted)} configs from {url}")
                            break
                    except Exception as e:
                        logger.debug(f"Failed to fetch {url}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error collecting from GitHub repo {repo}: {e}")
                continue

        return configs

    def collect_from_telegram(self) -> Set[str]:
        """Collect configs from Telegram channels"""
        configs = set()
        logger.info("Collecting from Telegram channels...")

        for channel in TELEGRAM_CHANNELS:
            try:
                response = self.session.get(channel, timeout=CONNECTION_TIMEOUT)
                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                extracted = self._extract_configs_from_soup(soup)
                configs.update(extracted)
                logger.info(f"Found {len(extracted)} configs from {channel}")
            except Exception as e:
                logger.error(f"Error collecting from Telegram {channel}: {e}")
                continue

        return configs

    def collect_from_apis(self) -> Set[str]:
        """Collect configs from public APIs"""
        configs = set()
        logger.info("Collecting from public APIs...")

        for api_url in PUBLIC_APIS:
            try:
                response = self.session.get(api_url, timeout=CONNECTION_TIMEOUT)
                if response.status_code == 200:
                    extracted = self._extract_configs_from_text(response.text)
                    configs.update(extracted)
                    logger.info(f"Found {len(extracted)} configs from {api_url}")
            except Exception as e:
                logger.error(f"Error collecting from API {api_url}: {e}")
                continue

        return configs

    def collect_from_web(self) -> Set[str]:
        """Collect configs from web scraping"""
        configs = set()

        if not WEB_SCRAPE_URLS:
            return configs

        logger.info("Collecting from web scraping...")

        for url in WEB_SCRAPE_URLS:
            try:
                response = self.session.get(url, timeout=CONNECTION_TIMEOUT)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    extracted = self._extract_configs_from_soup(soup)
                    configs.update(extracted)
                    logger.info(f"Found {len(extracted)} configs from {url}")
            except Exception as e:
                logger.error(f"Error scraping web {url}: {e}")
                continue

        return configs

    def _extract_configs_from_soup(self, soup: BeautifulSoup) -> Set[str]:
        """
        Extract proxy configs and related links from a BeautifulSoup HTML document.
        - متن خالص (vmess/vless/...)
        - href لینک‌ها (tg://, https://t.me/proxy, slipnet, لینک‌های مستقیم فایل)
        - فایل‌های تلگرام بر اساس عنوان (tgme_widget_message_document_title)
        """
        configs: Set[str] = set()

        try:
            # ۱) استخراج از متن خالص
            text_content = soup.get_text(separator=" ")
            configs.update(self._extract_configs_from_text(text_content))

            # ۲) بررسی همه لینک‌ها
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if not href:
                    continue

                href = html.unescape(href).strip()
                lower = href.lower()

                # پروتکل‌های استاندارد اگر در href باشند
                if lower.startswith("vmess://") or lower.startswith("vless://"):
                    configs.add(href)
                    continue
                if lower.startswith("trojan://") or lower.startswith("ss://") \
                   or lower.startswith("ssr://") or lower.startswith("hysteria://") \
                   or lower.startswith("hysteria2://") or lower.startswith("tuic://"):
                    configs.add(href)
                    continue

                # پروکسی‌های تلگرام
                if lower.startswith("tg://proxy?") or lower.startswith(
                    "https://t.me/proxy?"
                ):
                    configs.add(href)
                    continue

                # Slipnet (اگر به‌صورت لینک باشد)
                if "slipnet" in lower:
                    configs.add(href)

                # لینک مستقیم فایل‌های کانفیگ
                if re.search(r"\.(ovpn|npvt|npv|conf|config|txt)\b", href, re.IGNORECASE):
                    if href.startswith("//"):
                        href = "https:" + href
                    configs.add(href)
                    continue

            # ۳) فایل‌های تلگرام از روی عنوان (tgme_widget_message_document_title)
            #    مثل: @proxy_kafee🚀🌜.ovpn  یا  کافه پروکسی👑🦁.npvt  یا  ..._2.conf
            for title in soup.select(".tgme_widget_message_document_title"):
                filename_full = title.get_text(strip=True)
                if not filename_full:
                    continue

                # فقط اگر یکی از پسوندهای مدنظر را داشته باشد
                if not re.search(r"\.(ovpn|npvt|npv|conf|config|txt)\b", filename_full, re.IGNORECASE):
                    continue

                parent_a = title.find_parent("a", href=True)
                if not parent_a:
                    continue

                href = parent_a.get("href", "").strip()
                if not href:
                    continue

                href = html.unescape(href)
                if href.startswith("//"):
                    href = "https:" + href

                # URL مصنوعی: لینک پیام + #عنوان‌فایل
                # parser پسوند را از fragment تشخیص می‌دهد
                synthetic = f"{href}#{filename_full}"
                configs.add(synthetic)

        except Exception as e:
            logger.error(f"Error extracting configs from HTML soup: {e}")

        return configs

    def _extract_configs_from_text(self, text: str) -> Set[str]:
        """Extract proxy configs from plain text using regex patterns"""
        configs: Set[str] = set()

        try:
            patterns = [
                # VMESS
                r"vmess://\S+",
                # VLESS
                r"vless://\S+",
                # TROJAN
                r"trojan://\S+",
                # SS: جلوگیری از match وسط vless/vmess
                r"(?<!vle)(?<!vme)ss://\S+",
                # SSR
                r"ssr://\S+",
                # سایر پروتکل‌ها
                r"hysteria://\S+",
                r"hysteria2://\S+",
                r"tuic://\S+",
                # پروکسی‌های تلگرام
                r"tg://proxy\?\S+",
                r"https://t\.me/proxy\?\S+",
                # Slipnet (متن یا کانفیگ)
                r"slipnet[^\s]+",
                # لینک مستقیم فایل‌های کانفیگ
                r"https?://[^\s'\"]+\.(?:ovpn|npvt|npv|conf|config|txt)\b",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                configs.update(matches)

        except Exception as e:
            logger.error(f"Error extracting configs from text: {e}")

        return configs
