"""
Main script for collecting, filtering, testing and generating proxy configs
"""

import logging
from src.collector import ConfigCollector
from src.parser import ConfigParser
from src.filter import ConfigFilter
from src.tester import ConnectionTester
from src.generator import OutputGenerator
from src.file_handler import FileHandler
from src.config import TEST_COUNTRIES, get_country_flag

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main execution function"""
    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting Proxy Config Collector")
        logger.info("=" * 60)

        # STEP 1: Collect configs
        logger.info("\n[STEP 1/7] 📡 Collecting configs from all sources...")
        collector = ConfigCollector()
        raw_configs = collector.collect_all()
        logger.info(f"✅ Collected {len(raw_configs)} raw configs")

        if not raw_configs:
            logger.warning("⚠️  No configs collected! Exiting...")
            return

        # STEP 2: Parse configs
        logger.info("\n[STEP 2/7] 🔍 Parsing configs...")
        parser = ConfigParser()
        parsed_configs = []

        for config in raw_configs:
            try:
                parsed = parser.parse_config(config)
                if parsed:
                    parsed_configs.append(parsed)
            except Exception as e:
                logger.debug(f"Error parsing config: {e}")
                continue

        logger.info(f"✅ Successfully parsed {len(parsed_configs)} configs")

        if not parsed_configs:
            logger.warning("⚠️  No configs parsed successfully! Exiting...")
            return

        # STEP 3: Download and store file-based configs (ovpn, npvt, config, txt)
        logger.info("\n[STEP 3/7] 💾 Downloading file-based configs (OVPN / NPVT / CONFIG / TXT)...")
        file_types = {"ovpn", "npvt", "config_file", "txt_file"}
        file_configs = [cfg for cfg in parsed_configs if cfg.get("type") in file_types]

        if file_configs:
            file_handler = FileHandler()
            file_handler.process_files(file_configs)
        else:
            logger.info("No file-based configs found.")

        # STEP 4: Filter and categorize (geo) – فقط برای کانفیگ‌هایی که آدرس/پورت دارند
        logger.info("\n[STEP 4/7] 🌍 Filtering and categorizing by country...")
        filter_obj = ConfigFilter()

        # extra_types: کانفیگ‌هایی که کشور ندارند یا نباید geo-filter شوند
        extra_types = file_types | {"slipnet"}

        geo_eligible = [
            cfg
            for cfg in parsed_configs
            if cfg.get("type") not in extra_types
            and cfg.get("address")
            and cfg.get("port")
        ]

        categorized = filter_obj.filter_and_categorize(geo_eligible)

        for country in categorized:
            categorized[country] = filter_obj.remove_duplicates(categorized[country])

        logger.info(f"✅ Categorized into {len(categorized)} countries")

        # STEP 5: Test configs for specific countries
        logger.info("\n[STEP 5/7] 🧪 Testing configs for selected countries...")
        tester = ConnectionTester()
        tested_configs = {}

        for country in TEST_COUNTRIES:
            if country in categorized:
                logger.info(f"Testing {len(categorized[country])} configs for {country}...")
                tested = tester.test_configs(categorized[country])
                if tested:
                    tested_configs[country] = tested
                    logger.info(f"✅ Found {len(tested)} working configs for {country}")

        # STEP 6: Prepare extra configs (Slipnet + stored files) for by-protocol outputs
        logger.info("\n[STEP 6/7] 🧩 Preparing extra configs (Slipnet / files) for by-protocol outputs...")
        extra_configs = []

        for cfg in parsed_configs:
            t = cfg.get("type")
            if t == "slipnet":
                extra_configs.append(cfg)
            elif t in file_types and cfg.get("stored"):
                extra_configs.append(cfg)

        logger.info(f"Extra configs collected for by-protocol: {len(extra_configs)}")

        # STEP 7: Generate outputs
        logger.info("\n[STEP 7/7] 📝 Generating output files...")
        generator = OutputGenerator()
        generator.generate_all_outputs(
            categorized_configs=categorized,
            tested_configs=tested_configs,
            extra_configs=extra_configs,
        )

        # Summary
        logger.info("\n[SUMMARY] 📊 Summary")
        logger.info("=" * 60)
        total = sum(len(configs) for configs in categorized.values())
        total_tested = sum(len(configs) for configs in tested_configs.values())
        logger.info(f"📦 Total geo-categorized configs: {total}")
        logger.info(f"✅ Tested & working: {total_tested}")
        logger.info(f"🌍 Countries found: {len(categorized)}")

        for country, configs in sorted(categorized.items()):
            flag = get_country_flag(country)
            logger.info(f"  {flag} {country}: {len(configs)} configs")

        logger.info(f"➕ Extra configs (Slipnet / files): {len(extra_configs)}")

        logger.info("=" * 60)
        logger.info("✅ Process completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
