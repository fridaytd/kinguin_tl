import datetime
import time
from queue import Queue
from threading import Thread

from pydantic import ValidationError

from app import config, logger
from app.processes.process import process
from app.shared.utils import formated_datetime, sleep_for
from app.utils.browser_manager import BrowserManager

from app.sheet.models import RowModel

from app.gsheet_cache_manager import (
    gsheet_cache_manager,
    initialize_gsheet_cache_manager,
)


browser_manager = BrowserManager()
for _ in range(config.THREAD_NUMBER):
    browser_manager.create_browser(uc=True, headless=True)


def worker(index_queue: Queue, result_queue: Queue, worker_id: int):
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
            run_row = RowModel.get(
                sheet_id=config.SHEET_ID,
                sheet_name=config.SHEET_NAME,
                index=index,
            )

            updated_product = process(sb=sb, product=run_row)
            if updated_product:
                result_queue.put(updated_product)

        except ValidationError as e:
            logger.exception(f"{thread_prefix} VALIDATION ERROR AT ROW: {index}")
            logger.exception(e.errors())
            update_mapping = RowModel.updated_mapping_fields()
            gsheet_cache_manager.update_value(
                sheet_id=config.SHEET_ID,
                sheet_name=config.SHEET_NAME,
                cell=f"{update_mapping['Note']}{index}",
                value=f"VALIDATION ERROR: {e.errors()}",
            )
            gsheet_cache_manager.update_value(
                sheet_id=config.SHEET_ID,
                sheet_name=config.SHEET_NAME,
                cell=f"{update_mapping['Last_update']}{index}",
                value=formated_datetime(datetime.datetime.now()),
            )
        except Exception as e:
            logger.exception(f"{thread_prefix} FAILED AT ROW: {index}")
            update_mapping = RowModel.updated_mapping_fields()
            gsheet_cache_manager.update_value(
                sheet_id=config.SHEET_ID,
                sheet_name=config.SHEET_NAME,
                cell=f"{update_mapping['Note']}{index}",
                value=f"ERROR: {e}",
            )
            gsheet_cache_manager.update_value(
                sheet_id=config.SHEET_ID,
                sheet_name=config.SHEET_NAME,
                cell=f"{update_mapping['Last_update']}{index}",
                value=formated_datetime(datetime.datetime.now()),
            )

        finally:
            index_queue.task_done()


def main():
    logger.info("Start running")

    initialize_gsheet_cache_manager()

    run_indexes = RowModel.get_run_indexes(
        sheet_id=config.SHEET_ID,
        sheet_name=config.SHEET_NAME,
        col_range="B:B",
    )

    if not run_indexes:
        logger.info("No rows to process")
        return

    thread_number = config.THREAD_NUMBER
    logger.info(f"Run indexes: {run_indexes}")
    logger.info(f"Thread number: {thread_number}")

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
        result_queue = Queue()

        for index in batch:
            index_queue.put(index)

        threads = []
        for i in range(thread_number):
            t = Thread(
                target=worker,
                args=(index_queue, result_queue, i + 1),
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

        # Update products one by one sequentially
        logger.info(
            f"Updating products sequentially for batch {batch_idx}/{total_batches}..."
        )
        updated_count = 0
        time_sleep = 0.5
        while not result_queue.empty():
            product = result_queue.get()
            if product.RELAX_TIME and product.RELAX_TIME > time_sleep:
                time_sleep = product.RELAX_TIME
            product.update()
            updated_count += 1
            logger.info(
                f"Updated product at row {product.index} ({updated_count} products updated)"
            )

        logger.info(
            f"Total {updated_count} products updated for batch {batch_idx}/{total_batches}"
        )

        logger.info(f"Flushing batch {batch_idx}/{total_batches} to Google Sheet...")
        update_cells: list[str] = []
        for index in batch:
            update_mappping = RowModel.updated_mapping_fields()
            update_cells.append(f"{update_mappping['Last_update']}{index}")
            update_cells.append(f"{update_mappping['Note']}{index}")
        gsheet_cache_manager.flush_to_sheet(
            sheet_id=config.SHEET_ID,
            sheet_name=config.SHEET_NAME,
            cells=update_cells,
        )
        logger.info(f"Batch {batch_idx}/{total_batches} flushed successfully")
        sleep_for(time_sleep)

    logger.info(
        f"Completed processing {len(run_indexes)} rows in {total_batches} batches"
    )
    logger.info(f"Sleep for {config.RELAX_TIME_EACH_ROUND}s")
    time.sleep(config.RELAX_TIME_EACH_ROUND)
    gsheet_cache_manager.clear_all_sheets()


if __name__ == "__main__":
    logger.info("=== STARTING SCRIPT ===")

    while True:
        main()
        logger.info("=== SCRIPT COMPLETED ===")
