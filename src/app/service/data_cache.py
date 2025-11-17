import csv
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from gspread.utils import ValueInputOption

from app import logger
from app.models.gsheet_model import Product as RowModel
from app.utils.gsheet import worksheet
# from gspread.worksheet import Worksheet
@dataclass
class CachedRow:
    index: int
    Product_name: str
    Product_link: str
    Product_compare: str
    Category: str
    Check_product_compare: str
    min_price_value: Optional[float]
    max_price_value: Optional[float]
    stock_value: Optional[int]
    blacklist_value: List[str]
    include_keywords_value: Optional[List[str]]
    exclude_keywords_value: Optional[List[str]]
    DONGIAGIAM_MIN: float
    DONGIAGIAM_MAX: float
    DONGIA_LAMTRON: int
    Relax_time: float

    # Fields that will be updated
    Note: Optional[str] = None
    Last_update: Optional[str] = None


class DataCache:
    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.data: Dict[int, CachedRow] = {}
        self.lock = threading.Lock()
        self.pending_updates: Dict[int, Dict[str, Optional[str]]] = {}

    def load_from_sheet(
        self, sheet_id: str, sheet_name: str, run_indexes: List[int]
    ) -> None:
        logger.info(f"Loading {len(run_indexes)} rows from Google Sheet...")

        if not run_indexes:
            logger.warning("No indexes to load")
            return

        try:
            # Get worksheet and all data at once
            # worksheet = RowModel.get_worksheet(sheet_id, sheet_name)

            # Get all values from sheet (this is just ONE API call!)
            logger.info("Fetching all sheet data in one request...")
            all_values = worksheet.get_all_values()

            if not all_values or len(all_values) < 2:
                logger.error("Sheet is empty or has no data rows")
                return

            # Get column mapping
            mapping_dict = RowModel.mapping_fields()

            # Create a reverse mapping: column_letter -> field_name
            col_to_field = {}
            for field_name, col_letter in mapping_dict.items():
                col_to_field[col_letter] = field_name

            loaded_count = 0
            skipped_count = 0
            skipped_rows = []

            # Collect all external references (min_price, max_price, stock, blacklist)
            external_refs = self._collect_external_references(
                all_values, run_indexes, col_to_field
            )

            logger.info(f"Fetching {len(external_refs)} external cell references...")
            external_data = self._batch_fetch_external_data(external_refs)

            logger.info("Processing rows...")
            for idx in run_indexes:
                try:
                    if idx > len(all_values):
                        logger.warning(
                            f"Row {idx} is out of range (sheet has {len(all_values)} rows)"
                        )
                        skipped_count += 1
                        skipped_rows.append(idx)
                        continue

                    # Get row data (idx-1 because array is 0-indexed but sheet rows are 1-indexed)
                    row_values = all_values[idx - 1]

                    # Parse row into CachedRow
                    cached_row = self._parse_row_to_cached(
                        idx, row_values, col_to_field, external_data
                    )
                    print(cached_row)
                    if cached_row:
                        self.data[idx] = cached_row
                        loaded_count += 1

                        if loaded_count % 10 == 0:
                            logger.info(
                                f"Processed {loaded_count}/{len(run_indexes)} rows"
                            )
                    else:
                        skipped_count += 1
                        skipped_rows.append(idx)

                except Exception as e:
                    logger.exception(f"Failed to process row {idx}: {e}")
                    skipped_count += 1
                    skipped_rows.append(idx)

            self.save_to_csv()
            logger.info(f"Successfully loaded {loaded_count} rows into cache")
            if skipped_count > 0:
                logger.warning(
                    f"Skipped {skipped_count} rows due to errors: {skipped_rows}"
                )

        except Exception as e:
            logger.exception(f"Failed to load data from sheet: {e}")

    def _collect_external_references(
        self,
        all_values: List[List[str]],
        run_indexes: List[int],
        col_to_field: Dict[str, str],
    ) -> Dict[str, Dict[str, str]]:
        external_refs = {}

        # Column letters for external references
        ref_configs = {
            "min_price": ["L", "M", "N"],  # IDSHEET_MIN, SHEET_MIN, CELL_MIN
            "max_price": ["O", "P", "Q"],  # IDSHEET_MAX, SHEET_MAX, CELL_MAX
            "stock": ["R", "S", "T"],  # IDSHEET_STOCK, SHEET_STOCK, CELL_STOCK
            "blacklist": [
                "U",
                "V",
                "W",
            ],  # IDSHEET_BLACKLIST, SHEET_BLACKLIST, CELL_BLACKLIST
        }

        for idx in run_indexes:
            if idx > len(all_values):
                continue

            row_values = all_values[idx - 1]

            for ref_type, cols in ref_configs.items():
                try:
                    # Convert column letters to indexes
                    col_indices = [self._col_letter_to_index(col) for col in cols]

                    if all(col_idx < len(row_values) for col_idx in col_indices):
                        sheet_id = (
                            row_values[col_indices[0]].strip()
                            if col_indices[0] < len(row_values)
                            else ""
                        )
                        sheet_name = (
                            row_values[col_indices[1]].strip()
                            if col_indices[1] < len(row_values)
                            else ""
                        )
                        cell = (
                            row_values[col_indices[2]].strip()
                            if col_indices[2] < len(row_values)
                            else ""
                        )

                        if sheet_id and sheet_name and cell:
                            ref_key = f"{sheet_id}|{sheet_name}|{cell}"
                            if ref_key not in external_refs:
                                external_refs[ref_key] = {
                                    "sheet_id": sheet_id,
                                    "sheet_name": sheet_name,
                                    "cell": cell,
                                    "type": ref_type,
                                }
                except Exception as e:
                    logger.debug(
                        f"Error collecting external ref for row {idx}, type {ref_type}: {e}"
                    )

        return external_refs

    def _batch_fetch_external_data(
        self, external_refs: Dict[str, Dict[str, str]]
    ) -> Dict[str, any]:
        from gspread import service_account

        from app import config
        from app.utils.paths import ROOT_PATH

        external_data = {}

        if not external_refs:
            return external_data

        g_client = service_account(ROOT_PATH.joinpath(config.KEYS_PATH))

        # Group by sheet_id and sheet_name to batch requests
        grouped_refs = {}
        for ref_key, ref_info in external_refs.items():
            group_key = f"{ref_info['sheet_id']}|{ref_info['sheet_name']}"
            if group_key not in grouped_refs:
                grouped_refs[group_key] = []
            grouped_refs[group_key].append((ref_key, ref_info))

        # Fetch data for each group
        for group_key, refs in grouped_refs.items():
            try:
                sheet_id, sheet_name = group_key.split("|")

                # For blacklist (ranges), we need special handling
                blacklist_refs = [r for r in refs if r[1]["type"] == "blacklist"]
                other_refs = [r for r in refs if r[1]["type"] != "blacklist"]

                # Batch get for single cells
                if other_refs:
                    ranges = [f"{sheet_name}!{ref[1]['cell']}" for ref in other_refs]
                    try:
                        print(ranges)
                        results = g_client.http_client.values_batch_get(
                            id=sheet_id, ranges=ranges
                        )

                        value_ranges = results.get("valueRanges", [])
                        for i, ref in enumerate(other_refs):
                            if i < len(value_ranges):
                                values = value_ranges[i].get("values", [])
                                if values and values[0]:
                                    external_data[ref[0]] = values[0][0]
                    except Exception as e:
                        logger.warning(f"Failed to batch fetch from {group_key}: {e}")
                        # Fallback to individual fetches
                        for ref_key, ref_info in other_refs:
                            try:
                                res = g_client.http_client.values_get(
                                    id=ref_info["sheet_id"],
                                    range=f"{ref_info['sheet_name']}!{ref_info['cell']}",
                                )
                                values = res.get("values", [])
                                if values and values[0]:
                                    external_data[ref_key] = values[0][0]
                            except Exception as e2:
                                logger.warning(f"Failed to fetch {ref_key}: {e2}")

                # Handle blacklist separately (they are ranges, not single cells)
                for ref_key, ref_info in blacklist_refs:
                    try:
                        spreadsheet = g_client.open_by_key(ref_info["sheet_id"])
                        worksheet = spreadsheet.worksheet(ref_info["sheet_name"])
                        blacklist = worksheet.batch_get([ref_info["cell"]])[0]
                        if blacklist:
                            res = []
                            for blist in blacklist:
                                for item in blist:
                                    if item and str(item).strip():
                                        res.append(str(item).strip())
                            external_data[ref_key] = res
                        else:
                            external_data[ref_key] = []
                    except Exception as e:
                        logger.warning(f"Failed to fetch blacklist {ref_key}: {e}")
                        external_data[ref_key] = []

            except Exception as e:
                logger.exception(f"Failed to process group {group_key}: {e}")

        logger.info(f"Successfully fetched {len(external_data)} external references")
        return external_data

    def _parse_row_to_cached(
        self,
        idx: int,
        row_values: List[str],
        col_to_field: Dict[str, str],
        external_data: Dict[str, any],
    ) -> Optional[CachedRow]:
        try:
            # Helper to get value by column letter
            def get_value(col_letter: str, default=None):
                col_idx = self._col_letter_to_index(col_letter)
                if col_idx < len(row_values):
                    value = row_values[col_idx]
                    if isinstance(value, str):
                        value = value.strip()
                    return value if value != "" else default
                return default

            # Helper to get external reference key
            def get_external_key(
                id_col: str, sheet_col: str, cell_col: str
            ) -> Optional[str]:
                sheet_id = get_value(id_col, "")
                sheet_name = get_value(sheet_col, "")
                cell = get_value(cell_col, "")
                if sheet_id and sheet_name and cell:
                    return f"{sheet_id}|{sheet_name}|{cell}"
                return None

            # Get basic fields
            product_name = get_value("B", "")
            product_link = get_value("F", "")
            product_compare = get_value("H", "")
            category = get_value("E", "")
            check_product_compare = get_value("G", "")

            # Get external data
            min_price_value = None
            min_key = get_external_key("L", "M", "N")
            if min_key and min_key in external_data:
                try:
                    min_price_value = float(external_data[min_key])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Row {idx}: Invalid min_price value - {e}")

            max_price_value = None
            max_key = get_external_key("O", "P", "Q")
            if max_key and max_key in external_data:
                try:
                    max_price_value = float(external_data[max_key])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Row {idx}: Invalid max_price value - {e}")

            stock_value = None
            stock_key = get_external_key("R", "S", "T")
            if stock_key and stock_key in external_data:
                try:
                    stock_value = int(external_data[stock_key])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Row {idx}: Invalid stock value - {e}")

            blacklist_value = []
            blacklist_key = get_external_key("U", "V", "W")
            if blacklist_key and blacklist_key in external_data:
                blacklist_value = external_data[blacklist_key]

            # Parse keywords
            include_keywords_value = None
            include_kw = get_value("Y")
            if include_kw:
                include_keywords_value = [
                    kw.strip() for kw in include_kw.split(";") if kw.strip()
                ]

            exclude_keywords_value = None
            exclude_kw = get_value("Z")
            if exclude_kw:
                exclude_keywords_value = [
                    kw.strip() for kw in exclude_kw.split(";") if kw.strip()
                ]

            # Get numeric fields
            dongiagiam_min = float(get_value("I", 0))
            dongiagiam_max = float(get_value("J", 0))
            dongia_lamtron = int(get_value("K", 0))
            relax_time = float(get_value("X", 0))

            # Get update fields
            note = get_value("C")
            last_update = get_value("D")

            cached_row = CachedRow(
                index=idx,
                Product_name=product_name,
                Product_link=product_link,
                Product_compare=product_compare,
                Category=category,
                Check_product_compare=check_product_compare,
                min_price_value=min_price_value,
                max_price_value=max_price_value,
                stock_value=stock_value,
                blacklist_value=blacklist_value,
                include_keywords_value=include_keywords_value,
                exclude_keywords_value=exclude_keywords_value,
                DONGIAGIAM_MIN=dongiagiam_min,
                DONGIAGIAM_MAX=dongiagiam_max,
                DONGIA_LAMTRON=dongia_lamtron,
                Relax_time=relax_time,
                Note=note,
                Last_update=last_update,
            )

            logger.info(f"Loaded row {idx}: {product_name}")
            return cached_row

        except Exception as e:
            logger.exception(f"Failed to parse row {idx}: {e}")
            return None

    def _col_letter_to_index(self, col_letter: str) -> int:
        """Convert column letter (A, B, AA, etc.) to 0-based index"""
        result = 0
        for char in col_letter:
            result = result * 26 + (ord(char.upper()) - ord("A") + 1)
        return result - 1

    def save_to_csv(self) -> None:
        with self.lock:
            if not self.data:
                logger.info("No data to save to CSV")
                return
            data_to_save = [asdict(row) for row in self.data.values()]

        try:
            with open(self.cache_file, "w", newline="", encoding="utf-8") as f:
                if not data_to_save:
                    return

                fieldnames = list(data_to_save[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for row_dict in data_to_save:
                    # Format list fields to semicolon-separated strings
                    if row_dict["blacklist_value"]:
                        row_dict["blacklist_value"] = ";".join(
                            row_dict["blacklist_value"]
                        )
                    else:
                        row_dict["blacklist_value"] = ""

                    if row_dict["include_keywords_value"]:
                        row_dict["include_keywords_value"] = ";".join(
                            row_dict["include_keywords_value"]
                        )
                    else:
                        row_dict["include_keywords_value"] = ""

                    if row_dict["exclude_keywords_value"]:
                        row_dict["exclude_keywords_value"] = ";".join(
                            row_dict["exclude_keywords_value"]
                        )
                    else:
                        row_dict["exclude_keywords_value"] = ""

                    # Handle None values - convert to empty strings for CSV
                    if row_dict["Note"] is None:
                        row_dict["Note"] = ""
                    if row_dict["Last_update"] is None:
                        row_dict["Last_update"] = ""

                    # Format float fields to avoid scientific notation
                    if row_dict["DONGIAGIAM_MIN"] and isinstance(row_dict["DONGIAGIAM_MIN"], float):
                        row_dict["DONGIAGIAM_MIN"] = (
                            f"{row_dict['DONGIAGIAM_MIN']:.10f}".rstrip("0").rstrip(".")
                        )
                    if row_dict["DONGIAGIAM_MAX"] and isinstance(row_dict["DONGIAGIAM_MAX"], float):
                        row_dict["DONGIAGIAM_MAX"] = (
                            f"{row_dict['DONGIAGIAM_MAX']:.10f}".rstrip("0").rstrip(".")
                        )

                    if row_dict["Relax_time"] and isinstance(row_dict["Relax_time"], float):
                        row_dict["Relax_time"] = (
                            f"{row_dict['Relax_time']:.10f}".rstrip("0").rstrip(".")
                        )

                    if row_dict["min_price_value"] and isinstance(
                        row_dict["min_price_value"], float
                    ):
                        row_dict["min_price_value"] = (
                            f"{row_dict['min_price_value']:.10f}".rstrip("0").rstrip(
                                "."
                            )
                        )
                    if row_dict["max_price_value"] and isinstance(
                        row_dict["max_price_value"], float
                    ):
                        row_dict["max_price_value"] = (
                            f"{row_dict['max_price_value']:.10f}".rstrip("0").rstrip(
                                "."
                            )
                        )

                    writer.writerow(row_dict)

            logger.info(f"Saved {len(data_to_save)} rows to {self.cache_file}")

        except Exception as e:
            logger.exception(f"Failed to save cache to CSV: {e}")

    def load_from_csv(self) -> None:
        with self.lock:
            try:
                self.data.clear()
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        row["index"] = int(row["index"])

                        row["min_price_value"] = (
                            float(row["min_price_value"])
                            if row["min_price_value"] and row["min_price_value"].strip()
                            else None
                        )

                        row["max_price_value"] = (
                            float(row["max_price_value"])
                            if row["max_price_value"] and row["max_price_value"].strip()
                            else None
                        )

                        row["stock_value"] = (
                            int(row["stock_value"])
                            if row["stock_value"] and row["stock_value"].strip()
                            else None
                        )

                        row["DONGIAGIAM_MIN"] = float(row["DONGIAGIAM_MIN"])
                        row["DONGIAGIAM_MAX"] = float(row["DONGIAGIAM_MAX"])
                        row["DONGIA_LAMTRON"] = int(row["DONGIA_LAMTRON"])
                        row["Relax_time"] = float(row["Relax_time"])

                        row["blacklist_value"] = (
                            row["blacklist_value"].split(";")
                            if row["blacklist_value"] and row["blacklist_value"].strip()
                            else []
                        )
                        row["include_keywords_value"] = (
                            row["include_keywords_value"].split(";")
                            if row["include_keywords_value"]
                            and row["include_keywords_value"].strip()
                            else None
                        )
                        row["exclude_keywords_value"] = (
                            row["exclude_keywords_value"].split(";")
                            if row["exclude_keywords_value"]
                            and row["exclude_keywords_value"].strip()
                            else None
                        )

                        row["Note"] = (
                            row["Note"] if row["Note"] and row["Note"].strip() else None
                        )
                        row["Last_update"] = (
                            row["Last_update"]
                            if row["Last_update"] and row["Last_update"].strip()
                            else None
                        )

                        cached_row = CachedRow(**row)
                        self.data[cached_row.index] = cached_row

                logger.info(f"Loaded {len(self.data)} rows from {self.cache_file}")
            except FileNotFoundError:
                logger.warning(f"Cache file {self.cache_file} not found")
            except Exception as e:
                logger.exception(f"Failed to load cache from CSV: {e}")

    def get(self, index: int) -> Optional[CachedRow]:
        with self.lock:
            return self.data.get(index)

    def update_fields(
        self, index: int, note: Optional[str], last_update: Optional[str]
    ) -> None:
        with self.lock:
            if index in self.data:
                self.data[index].Note = note
                self.data[index].Last_update = last_update
                self.pending_updates[index] = {"Note": note, "Last_update": last_update}

    def flush_updates_to_sheet(self, sheet_id: str, sheet_name: str) -> None:
        logger.info("Starting flush_updates_to_sheet...")

        with self.lock:
            logger.info("Acquired lock for flush")

            if not self.pending_updates:
                logger.info("No pending updates to flush")
                return

            updates_to_flush = dict(self.pending_updates)
            self.pending_updates.clear()

            logger.info(f"Copied {len(updates_to_flush)} updates, releasing lock")

        logger.info("Starting API call to Google Sheets...")

        try:
            worksheet = RowModel.get_worksheet(sheet_id, sheet_name)
            mapping_dict = RowModel.updated_mapping_fields()

            batch_data = []

            for index, updates in updates_to_flush.items():
                if "Note" in mapping_dict:
                    batch_data.append(
                        {
                            "range": f"{mapping_dict['Note']}{index}",
                            "values": [[updates["Note"] if updates["Note"] else ""]],
                        }
                    )

                if "Last_update" in mapping_dict:
                    batch_data.append(
                        {
                            "range": f"{mapping_dict['Last_update']}{index}",
                            "values": [
                                [
                                    updates["Last_update"]
                                    if updates["Last_update"]
                                    else ""
                                ]
                            ],
                        }
                    )

            if batch_data:
                logger.info(
                    f"Sending {len(batch_data)} cell updates to Google Sheets..."
                )
                worksheet.batch_update(
                    batch_data, value_input_option=ValueInputOption.user_entered
                )
                logger.info(
                    f"Successfully flushed {len(updates_to_flush)} updates to Google Sheet"
                )
            else:
                logger.warning(
                    "No batch data to send (mapping fields might be missing)"
                )

            logger.info("Saving cache to CSV...")
            self.save_to_csv()
            logger.info("CSV save completed")

        except Exception as e:
            logger.exception(f"Failed to flush updates to sheet: {e}")

            with self.lock:
                # Merge failed updates back into pending_updates
                for index, updates in updates_to_flush.items():
                    if index not in self.pending_updates:
                        self.pending_updates[index] = updates
                    else:
                        # If there are newer updates, keep them
                        logger.warning(
                            f"Index {index} has newer updates, skipping restore"
                        )

            logger.error(
                f"Restored {len(updates_to_flush)} failed updates back to pending queue"
            )

    def get_all_indexes(self) -> List[int]:
        with self.lock:
            return list(self.data.keys())

    def count(self) -> int:
        with self.lock:
            return len(self.data)


# Global cache instance
_cache: Optional[DataCache] = None


def initialize_cache(
    cache_file: Path, sheet_id: str, sheet_name: str, run_indexes: List[int]
) -> DataCache:
    global _cache
    _cache = DataCache(cache_file)
    _cache.load_from_sheet(sheet_id, sheet_name, run_indexes)
    return _cache


def get_cache() -> DataCache:
    if _cache is None:
        raise RuntimeError("Cache not initialized. Call initialize_cache() first!!!")
    return _cache