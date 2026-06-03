"""
Tester module for testing proxy connections
"""

import socket
import logging
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import CONNECTION_TIMEOUT, MAX_WORKERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConnectionTester:
    """Test proxy connections"""
    
    def __init__(self):
        self.timeout = CONNECTION_TIMEOUT
    
    def test_configs(self, configs: list) -> list:
        """Test multiple configs and return working ones"""
        logger.info(f"Testing {len(configs)} configs...")
        
        working_configs = []
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._test_single_config, config): config 
                for config in configs
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        working_configs.append(result)
                except Exception as e:
                    logger.debug(f"Test failed: {e}")
                    continue
        
        logger.info(f"{len(working_configs)} configs are working")
        return working_configs
    
    def _test_single_config(self, config: Dict) -> Optional[Dict]:
        """Test a single config by checking TCP connection"""
        try:
            address = config.get('address', '')
            port = config.get('port', '')
            
            if not address or not port:
                return None
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            
            try:
                result = sock.connect_ex((address, int(port)))
                sock.close()
                
                if result == 0:
                    config['tested'] = True
                    config['working'] = True
                    return config
                else:
                    return None
                    
            except Exception as e:
                sock.close()
                return None
                
        except Exception as e:
            logger.debug(f"Error testing config: {e}")
            return None
