"""
Filter module for filtering configs by country and CDN
"""

import socket
import ipaddress
import requests
import logging
import re
from typing import Dict, Optional, Set, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigFilter:
    """Filter configs based on geo-location and CDN"""
    
    def __init__(self):
        self.iran_ips = self._load_iran_ip_ranges()
        self.session = requests.Session()
        self.ip_cache = {}
    
    def _load_iran_ip_ranges(self) -> Set[ipaddress.IPv4Network]:
        """Load Iran IP ranges"""
        ip_ranges = set()
        
        try:
            url = "https://raw.githubusercontent.com/herrbischoff/country-ip-blocks/master/ipv4/ir.cidr"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                for line in response.text.strip().split('\n'):
                    try:
                        ip_ranges.add(ipaddress.IPv4Network(line.strip()))
                    except:
                        continue
                logger.info(f"Loaded {len(ip_ranges)} Iran IP ranges")
                        
        except Exception as e:
            logger.warning(f"Could not load Iran IP ranges: {e}")
        
        for cidr in ARVAN_CLOUD_RANGES + DERAK_CLOUD_RANGES:
            try:
                ip_ranges.add(ipaddress.IPv4Network(cidr))
            except:
                continue
        
        return ip_ranges
    
    def get_ip_from_address(self, address: str) -> Optional[str]:
        """Resolve domain to IP or return IP if already IP"""
        try:
            if address in self.ip_cache:
                return self.ip_cache[address]
            
            try:
                ipaddress.ip_address(address)
                self.ip_cache[address] = address
                return address
            except ValueError:
                pass
            
            ip = socket.gethostbyname(address)
            self.ip_cache[address] = ip
            return ip
            
        except Exception as e:
            logger.debug(f"Could not resolve {address}: {e}")
            return None
    
    def get_country_code(self, ip: str) -> Optional[str]:
        """Get country code from IP"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for network in self.iran_ips:
                if ip_obj in network:
                    return "IR"
            
            response = self.session.get(f"https://ipinfo.io/{ip}/json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('country', None)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting country for {ip}: {e}")
            return None
    
    def detect_cdn(self, ip: str, address: str) -> Optional[str]:
        """Detect CDN provider"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            for cidr in ARVAN_CLOUD_RANGES:
                if ip_obj in ipaddress.IPv4Network(cidr):
                    return "arvancloud"
            
            for cidr in DERAK_CLOUD_RANGES:
                if ip_obj in ipaddress.IPv4Network(cidr):
                    return "derakcloud"
            
            cloudflare_ranges = ["173.245.48.0/20", "103.21.244.0/22"]
            for cidr in cloudflare_ranges:
                if ip_obj in ipaddress.IPv4Network(cidr):
                    return "cloudflare"
            
            return None
            
        except Exception as e:
            logger.debug(f"Error detecting CDN: {e}")
            return None
    
    def filter_and_categorize(self, parsed_configs: list) -> Dict[str, list]:
        """Filter configs and categorize by country"""
        categorized = {}
        
        logger.info(f"Filtering and categorizing {len(parsed_configs)} configs...")
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._process_config, config): config 
                for config in parsed_configs
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        country, config_data = result
                        if country not in categorized:
                            categorized[country] = []
                        categorized[country].append(config_data)
                except Exception as e:
                    logger.debug(f"Error processing config: {e}")
                    continue
        
        for country, configs in categorized.items():
            logger.info(f"Found {len(configs)} configs for {country}")
        
        return categorized
    
    def _process_config(self, config: Dict) -> Optional[tuple]:
        """Process single config"""
        try:
            address = config.get('address', '')
            if not address:
                return None
            
            ip = self.get_ip_from_address(address)
            if not ip:
                return None
            
            country = self.get_country_code(ip)
            if not country:
                return None
            
            cdn = self.detect_cdn(ip, address)
            
            config['ip'] = ip
            config['country'] = country
            config['cdn'] = cdn
            
            return (country, config)
            
        except Exception as e:
            logger.debug(f"Error in _process_config: {e}")
            return None
    
    def remove_duplicates(self, configs: list) -> list:
        """Remove duplicate configs based on content"""
        unique = {}
        
        for config in configs:
            content_hash = f"{config['type']}_{config['address']}_{config['port']}_{config.get('id', '')}_{config.get('password', '')}"
            
            if content_hash not in unique:
                unique[content_hash] = config
        
        removed = len(configs) - len(unique)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate configs")
        
        return list(unique.values())
