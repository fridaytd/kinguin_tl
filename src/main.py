import time
from datetime import datetime
from queue import Queue
from threading import Thread
from typing import Optional

from pydantic import ValidationError

from app import config, logger
from app.processes.process import process
from app.service.data_cache import CachedRow, get_cache, initialize_cache, retry_on_rate_limit
from app.shared.paths import SRC_PATH
from app.shared.utils import formated_datetime
from app.utils.browser_manager import BrowserManager

# from app.sheet import RowModel
from gspread.worksheet import Worksheet
from app.sheet import worksheet


browser_manager = BrowserManager()
for _ in range(config.THREAD_NUMBER):
    browser_manager.create_browser(uc=True, headless=True)


@retry_on_rate_limit(max_retries=10, initial_delay=5.0)
def get_run_indexes(sheet: Worksheet) -> list[int]:
    run_indexes = []
    check_col = sheet.col_values(2)
    for idx, value in enumerate(check_col):
        idx += 1
        if isinstance(value, int):
            if value == 1:
                run_indexes.append(idx)
        if isinstance(value, str):
            try:
                int_value = int(value)
            except Exception:
                continue
            if int_value == 1:
                run_indexes.append(idx)

    return run_indexes


def update_error_to_cache(index: int, error_msg: str):
    try:
        now = datetime.now()
        cache = get_cache()
        cache.update_fields(
            index=index,
            note=f"{formated_datetime(now)}: {error_msg}",
            last_update=formated_datetime(now),
        )
    except Exception as e:
        logger.exception(f"Failed to update error to cache: {e}")


def validate_required_fields(
    cached_row: CachedRow, thread_prefix: str
) -> tuple[bool, Optional[str]]:
    required_fields = {
        "Product_link": "Product_link",
        "PRODUCT_COMPARE": "PRODUCT_COMPARE",
        "CHECK_PRODUCT_COMPARE": "CHECK_PRODUCT_COMPARE",
        "DONGIAGIAM_MIN": "DONGIAGIAM_MIN",
        "DONGIAGIAM_MAX": "DONGIAGIAM_MAX",
        "DONGIA_LAMTRON": "DONGIA_LAMTRON",
        "min_price_value": "MIN_PRICE",
        "stock_value": "STOCK",
        "blacklist_value": "BLACKLIST",
        "UNIT_STOCK": "UNIT_STOCK",
        "RELAX_TIME": "RELAX_TIME",
    }

    for field_name, display_name in required_fields.items():
        value = getattr(cached_row, field_name, None)

        # Check None
        if value is None:
            error_msg = f"Giá trị {display_name} đang rỗng. Vui lòng cập nhật!"
            logger.error(f"{thread_prefix} Validation failed: {error_msg}")
            return False, error_msg

        # Check empty string for string fields
        # if isinstance(value, str) and not value.strip():
        #     error_msg = f"Giá trị {display_name} đang rỗng. Vui lòng cập nhật!"
        #     logger.error(f"{thread_prefix} Validation failed: {error_msg}")
        #     return False, error_msg

    logger.info(f"{thread_prefix} All required fields are not empty")
    return True, None


def worker(index_queue: Queue, worker_id: int):
    thread_prefix = f"[Worker-{worker_id}]"

    sb = browser_manager.get(worker_id - 1)

    sb.activate_cdp_mode("https://google.com")

    while True:
        index = index_queue.get()
        if index is None:
            index_queue.task_done()
            break

        logger.info(f"{thread_prefix} INDEX (ROW): {index}")
        try:
            cache = get_cache()
            cached_row = cache.get(index)

            if cached_row is None:
                logger.error(f"{thread_prefix} Row {index} not found in cache")
                index_queue.task_done()
                continue

            is_valid, error_message = validate_required_fields(
                cached_row, thread_prefix
            )
            if not is_valid:
                logger.error(
                    f"{thread_prefix} Row {index} validation failed: {error_message}"
                )
                if error_message:  # Type guard to ensure error_message is not None
                    update_error_to_cache(index, error_message)
                index_queue.task_done()
                continue

            process(sb, cached_row)
            logger.info(f"{thread_prefix} Sleep for {cached_row.RELAX_TIME}s")
            time.sleep(cached_row.RELAX_TIME)

        except ValidationError as e:
            logger.exception(f"{thread_prefix} VALIDATION ERROR AT ROW: {index}")
            logger.exception(e.errors())
            update_error_to_cache(index, f"VALIDATION ERROR: {e.errors()}")

        except Exception as e:
            logger.exception(f"{thread_prefix} FAILED AT ROW: {index}")
            update_error_to_cache(index, f"FAILED: {e}")
            time.sleep(20)

        finally:
            index_queue.task_done()


def main():
    logger.info("Start running")

    run_indexes = get_run_indexes(worksheet)

    if not run_indexes:
        logger.info("No rows to process")
        return

    thread_number = config.THREAD_NUMBER
    logger.info(f"Run indexes: {run_indexes}")
    logger.info(f"Thread number: {thread_number}")

    cache_file = SRC_PATH / "data" / "cache.csv"
    initialize_cache(cache_file, config.SHEET_ID, config.SHEET_NAME, run_indexes)

    batches = [
        run_indexes[i : i + thread_number]
        for i in range(0, len(run_indexes), thread_number)
    ]

    total_batches = len(batches)
    logger.info(f"Total batches: {total_batches}")

    for batch_idx, batch in enumerate(batches, 1):
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Processing batch {batch_idx}/{total_batches}: {batch}")
        logger.info(f"{'=' * 50}\n")

        index_queue = Queue()

        for index in batch:
            index_queue.put(index)

        threads = []
        for i in range(thread_number):
            t = Thread(
                target=worker,
                args=(index_queue, i + 1),
                daemon=True,
                name=f"Worker-{i + 1}",
            )
            t.start()
            threads.append(t)
            logger.info(f"Started worker thread {i + 1}/{thread_number}")

        index_queue.join()

        for _ in range(thread_number):
            index_queue.put(None)

        for t in threads:
            t.join(timeout=120)
            if t.is_alive():
                logger.warning(f"Thread {t.name} did not finish in time!!!!!!!!!!")

        logger.info(f"Flushing batch {batch_idx}/{total_batches} to Google Sheet...")
        cache = get_cache()
        cache.flush_updates_to_sheet(config.SHEET_ID, config.SHEET_NAME)
        logger.info(f"Batch {batch_idx}/{total_batches} flushed successfully")

    logger.info(
        f"Completed processing {len(run_indexes)} rows in {total_batches} batches"
    )
    logger.info(f"Sleep for {config.RELAX_TIME_EACH_ROUND}s")
    time.sleep(config.RELAX_TIME_EACH_ROUND)


if __name__ == "__main__":
    logger.info("=== STARTING SCRIPT ===")

    while True:
        main()
        logger.info("=== SCRIPT COMPLETED ===")
