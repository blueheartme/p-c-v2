"""
File handler module for downloading and storing file-based configs:

- .ovpn  (OpenVPN configs, with country detection from 'remote' line)
- .npvt / .npv (Napsternet / encrypted configs; only stored, no country)
- .config (client-specific config files; only stored)
- .txt (text files containing configs or data; only stored)

برای این فایل‌ها:
- لینک اصلی (source_url) حفظ می‌شود.
- فایل در پوشه output/files/... ذخیره می‌شود.
- برای OVPN:
  - آدرس/پورت remote استخراج می‌شود (در صورت امکان)
  - کشور سرور از روی IP تشخیص داده می‌شود (در صورت امکان)
  - نام فایل شامل کد کشور می‌شود.
- برای همه‌ی فایل‌ها:
  - local_path: مسیر نسبی فایل در ریپو
  - rebuilt: لینک raw گیت‌هاب (در صورت داشتن GITHUB_REPOSITORY)، برای استفاده در خروجی by-protocol.
"""

import os
import re
import logging
from typing import List, Dict, Optional, Tuple
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import (
    OUTPUT_DIR,
    CONNECTION_TIMEOUT,
    MAX_WORKERS,
    REPO_NAME,
)
from .filter import ConfigFilter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FILES_BASE_DIR = os.path.join(OUTPUT_DIR, "files")
OVPN_BASE_DIR = os.path.join(FILES_BASE_DIR, "ovpn")
NPVT_BASE_DIR = os.path.join(FILES_BASE_DIR, "npvt")
CONFIG_BASE_DIR = os.path.join(FILES_BASE_DIR, "config")
TXT_BASE_DIR = os.path.join(FILES_BASE_DIR, "txt")


class FileHandler:
    """Handle downloading and storing file-based configs"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        # برای تشخیص کشور از روی IP
        self.filter = ConfigFilter()

        # ایجاد پوشه‌ها
        for d in [FILES_BASE_DIR, OVPN_BASE_DIR, NPVT_BASE_DIR, CONFIG_BASE_DIR, TXT_BASE_DIR]:
            os.makedirs(d, exist_ok=True)

    def process_files(self, file_configs: List[Dict]) -> None:
        """
        دانلود و ذخیره‌ی فایل‌ها.

        این تابع روی خود دیکشنری‌های config درجا (in-place) کار می‌کند:
        - در صورت موفقیت:
          - config['stored'] = True
          - config['local_path'] = 'output/...'
          - config['rebuilt'] = 'https://raw.githubusercontent.com/...'
        - در صورت شکست:
          - config['stored'] = False
        """
        if not file_configs:
            return

        logger.info(f"Processing {len(file_configs)} file-based configs...")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._process_single_file, cfg): cfg
                for cfg in file_configs
            }

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.debug(f"Error in file processing task: {e}")
                    continue

    def _process_single_file(self, config: Dict) -> None:
        file_type = config.get("type")
        url = config.get("file_url") or config.get("original")

        if not url:
            config["stored"] = False
            return

        try:
            logger.info(f"Downloading file ({file_type}): {url}")
            resp = self.session.get(url, timeout=CONNECTION_TIMEOUT)
            if resp.status_code != 200 or not resp.content:
                logger.warning(f"Failed to download file: {url} (status {resp.status_code})")
                config["stored"] = False
                return

            parsed = urlparse(url)
            path = parsed.path or ""
            orig_name = os.path.basename(path) or file_type

            if file_type == "ovpn":
                self._handle_ovpn_file(config, orig_name, resp.content)
            elif file_type == "npvt":
                self._handle_generic_file(config, orig_name, resp.content, NPVT_BASE_DIR, default_ext=".npvt")
            elif file_type == "config_file":
                self._handle_generic_file(config, orig_name, resp.content, CONFIG_BASE_DIR, default_ext=".config")
            elif file_type == "txt_file":
                self._handle_generic_file(config, orig_name, resp.content, TXT_BASE_DIR, default_ext=".txt")
            else:
                config["stored"] = False
                return

        except Exception as e:
            logger.warning(f"Error processing file {url}: {e}")
            config["stored"] = False

    # ---------- OVPN ----------

    def _handle_ovpn_file(self, config: Dict, orig_name: str, content: bytes) -> None:
        """
        ذخیره‌ی فایل OVPN با تشخیص کشور (در صورت امکان) از روی خط remote
        """
        try:
            try:
                text = content.decode("utf-8", errors="ignore")
            except Exception:
                text = content.decode("latin-1", errors="ignore")

            host, port = self._extract_ovpn_remote(text)
            country_code = "UN"
            ip = None

            if host and port:
                try:
                    ip = self.filter.get_ip_from_address(host)
                    if ip:
                        c = self.filter.get_country_code(ip)
                        if c:
                            country_code = c.upper()
                except Exception as e:
                    logger.debug(f"Error getting country for OVPN host {host}: {e}")

            country_dir = os.path.join(OVPN_BASE_DIR, country_code.lower())
            os.makedirs(country_dir, exist_ok=True)

            # اطمینان از پسوند .ovpn
            if not orig_name.lower().endswith(".ovpn"):
                orig_name = orig_name + ".ovpn"

            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", orig_name)
            file_path = os.path.join(country_dir, safe_name)

            with open(file_path, "wb") as f:
                f.write(content)

            rel_path = os.path.relpath(file_path, start=".")

            config["stored"] = True
            config["local_path"] = rel_path.replace("\\", "/")
            config["original_url"] = config.get("file_url") or config.get("original")
            config["ovpn_remote_host"] = host or ""
            config["ovpn_remote_port"] = port or ""
            config["country"] = country_code

            # لینک raw گیت‌هاب برای خروجی txt/subscription
            if REPO_NAME:
                base_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/"
                config["rebuilt"] = base_url + config["local_path"]
            else:
                config["rebuilt"] = config["local_path"]

            # original را هم به لینک فایل در ریپو تغییر می‌دهیم (برای JSON)
            config["original"] = config["local_path"]

            logger.info(
                f"Stored OVPN file for country {country_code}: {config['local_path']}"
            )

        except Exception as e:
            logger.warning(f"Error handling OVPN file {orig_name}: {e}")
            config["stored"] = False

    def _extract_ovpn_remote(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        استخراج اولین خط remote معتبر از متن OVPN:
        مثلا: remote 45.154.155.9 443 tcp-client
        """
        try:
            pattern = re.compile(r"^\s*remote\s+([^\s]+)\s+(\d+)", re.MULTILINE)
            m = pattern.search(text)
            if m:
                host = m.group(1).strip()
                port = m.group(2).strip()
                return host, port
            return None, None
        except Exception as e:
            logger.debug(f"Error extracting remote from OVPN: {e}")
            return None, None

    # ---------- Generic file types (npvt, config, txt) ----------

    def _handle_generic_file(
        self,
        config: Dict,
        orig_name: str,
        content: bytes,
        base_dir: str,
        default_ext: str,
    ) -> None:
        """
        ذخیره‌ی فایل‌های عمومی (npvt, config, txt) بدون تفکیک کشوری
        """
        try:
            if not orig_name.lower().endswith(default_ext):
                orig_name = orig_name + default_ext

            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", orig_name)
            file_path = os.path.join(base_dir, safe_name)

            with open(file_path, "wb") as f:
                f.write(content)

            rel_path = os.path.relpath(file_path, start=".")

            config["stored"] = True
            config["local_path"] = rel_path.replace("\\", "/")
            config["original_url"] = config.get("file_url") or config.get("original")

            if REPO_NAME:
                base_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/"
                config["rebuilt"] = base_url + config["local_path"]
            else:
                config["rebuilt"] = config["local_path"]

            config["original"] = config["local_path"]

            logger.info(
                f"Stored {config.get('type')} file: {config['local_path']}"
            )

        except Exception as e:
            logger.warning(f"Error handling generic file {orig_name}: {e}")
            config["stored"] = False
