"""
File importer for RNG analysis.

Supports CSV, JSON, and Excel formats with smart parsing.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of file import operation."""
    success: bool
    rows_imported: int
    columns: list
    data: Optional[pd.DataFrame] = None
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class FileImporter:
    """Import bet history from various file formats."""
    
    # Column name mappings (flexible parsing)
    COLUMN_MAPPINGS = {
        'outcome': ['outcome', 'number', 'result', 'roll', 'dice'],
        'nonce': ['nonce', 'bet_id', 'id', 'bet_number'],
        'timestamp': ['date', 'timestamp', 'time', 'created_at'],
        'won': ['result', 'won', 'win', 'outcome_text'],
        'server_seed': ['server_seed', 'serverseed', 'ss'],
        'client_seed': ['client_seed', 'clientseed', 'cs'],
    }
    
    def __init__(self):
        """Initialize file importer."""
        self.progress_callback: Optional[Callable[[str, float], None]] = None
        
    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """Set progress callback function."""
        self.progress_callback = callback
        
    def _report_progress(self, message: str, progress: float):
        """Report progress if callback set."""
        if self.progress_callback:
            self.progress_callback(message, progress)
            
    def import_file(self, filepath: Path) -> ImportResult:
        """
        Import bet history from file (auto-detect format).
        
        Args:
            filepath: Path to file
            
        Returns:
            ImportResult with data and status
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            return ImportResult(
                success=False,
                rows_imported=0,
                columns=[],
                errors=[f"File not found: {filepath}"]
            )
        
        # Detect format by extension
        ext = filepath.suffix.lower()
        
        try:
            if ext == '.csv':
                return self.import_csv(filepath)
            elif ext == '.json':
                return self.import_json(filepath)
            elif ext in ['.xlsx', '.xls']:
                return self.import_excel(filepath)
            else:
                return ImportResult(
                    success=False,
                    rows_imported=0,
                    columns=[],
                    errors=[f"Unsupported file format: {ext}"]
                )
        except Exception as e:
            logger.error(f"Import error: {e}")
            return ImportResult(
                success=False,
                rows_imported=0,
                columns=[],
                errors=[f"Import failed: {str(e)}"]
            )
    
    def import_csv(self, filepath: Path) -> ImportResult:
        """Import from CSV file."""
        self._report_progress("Reading CSV file...", 0.1)
        
        # Try different encodings
        for encoding in ['utf-8', 'latin1', 'cp1252']:
            try:
                df = pd.read_csv(filepath, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            return ImportResult(
                success=False,
                rows_imported=0,
                columns=[],
                errors=["Failed to decode CSV file"]
            )
        
        self._report_progress("Parsing columns...", 0.3)
        return self._process_dataframe(df, filepath)
    
    def import_json(self, filepath: Path) -> ImportResult:
        """Import from JSON file."""
        self._report_progress("Reading JSON file...", 0.1)
        
        import json
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            if 'bets' in data:
                df = pd.DataFrame(data['bets'])
            elif 'data' in data:
                df = pd.DataFrame(data['data'])
            else:
                # Try to convert dict to DataFrame
                df = pd.DataFrame([data])
        else:
            return ImportResult(
                success=False,
                rows_imported=0,
                columns=[],
                errors=["Invalid JSON structure"]
            )
        
        self._report_progress("Parsing columns...", 0.3)
        return self._process_dataframe(df, filepath)
    
    def import_excel(self, filepath: Path) -> ImportResult:
        """Import from Excel file."""
        self._report_progress("Reading Excel file...", 0.1)
        
        df = pd.read_excel(filepath)
        
        self._report_progress("Parsing columns...", 0.3)
        return self._process_dataframe(df, filepath)
    
    def _process_dataframe(self, df: pd.DataFrame, filepath: Path) -> ImportResult:
        """Process and validate DataFrame."""
        result = ImportResult(
            success=True,
            rows_imported=len(df),
            columns=list(df.columns),
        )
        
        self._report_progress("Normalizing columns...", 0.5)
        
        # Normalize column names
        df = self._normalize_columns(df, result)
        
        self._report_progress("Extracting seeds...", 0.7)
        
        # Extract seeds from verification links if present
        df = self._extract_seeds(df, result)
        
        self._report_progress("Validating data...", 0.9)
        
        # Validate required columns
        if 'outcome' not in df.columns:
            result.errors.append("Missing 'outcome' column")
            result.success = False
        
        # Convert data types
        if 'outcome' in df.columns:
            df['outcome'] = pd.to_numeric(df['outcome'], errors='coerce')
        
        if 'nonce' in df.columns:
            df['nonce'] = pd.to_numeric(df['nonce'], errors='coerce')
        
        # Remove rows with NaN outcomes
        if 'outcome' in df.columns:
            before = len(df)
            df = df.dropna(subset=['outcome'])
            after = len(df)
            if before != after:
                result.warnings.append(f"Removed {before - after} rows with invalid outcomes")
        
        result.data = df
        result.rows_imported = len(df)
        
        self._report_progress("Import complete", 1.0)
        
        logger.info(f"Imported {len(df)} rows from {filepath}")
        return result
    
    def _normalize_columns(self, df: pd.DataFrame, result: ImportResult) -> pd.DataFrame:
        """Normalize column names to standard format."""
        # Make column names lowercase for matching
        df.columns = [col.lower().strip() for col in df.columns]
        
        # Map columns to standard names
        column_map = {}
        for standard_name, possible_names in self.COLUMN_MAPPINGS.items():
            for col in df.columns:
                if col in possible_names:
                    column_map[col] = standard_name
                    break
        
        if column_map:
            df = df.rename(columns=column_map)
            result.warnings.append(f"Mapped columns: {column_map}")
        
        return df
    
    def _extract_seeds(self, df: pd.DataFrame, result: ImportResult) -> pd.DataFrame:
        """Extract server/client seeds from verification links."""
        # Look for verification link column
        link_columns = [col for col in df.columns if 'verification' in col.lower() or 'link' in col.lower()]
        
        if not link_columns:
            return df
        
        link_col = link_columns[0]
        
        # Extract seeds using regex
        def extract_server_seed(link):
            if pd.isna(link):
                return None
            match = re.search(r'serverSeed=([^&]+)', str(link))
            return match.group(1) if match else None
        
        def extract_client_seed(link):
            if pd.isna(link):
                return None
            match = re.search(r'clientSeed=([^&]+)', str(link))
            return match.group(1) if match else None
        
        df['server_seed'] = df[link_col].apply(extract_server_seed)
        df['client_seed'] = df[link_col].apply(extract_client_seed)
        
        seeds_extracted = df['server_seed'].notna().sum()
        if seeds_extracted > 0:
            result.warnings.append(f"Extracted seeds from {seeds_extracted} verification links")
        
        return df
