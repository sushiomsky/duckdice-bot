"""
API importer for RNG analysis.

Fetch bet history directly from DuckDice API.
"""

import asyncio
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class APIImporter:
    """Import bet history from DuckDice API."""
    
    def __init__(self, api_client=None):
        """
        Initialize API importer.
        
        Args:
            api_client: DuckdiceAPI instance (optional, will create if needed)
        """
        self.api_client = api_client
        self.progress_callback: Optional[Callable[[str, float], None]] = None
        
    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """Set progress callback function."""
        self.progress_callback = callback
        
    def _report_progress(self, message: str, progress: float):
        """Report progress if callback set."""
        if self.progress_callback:
            self.progress_callback(message, progress)
    
    async def import_from_api(
        self,
        api_key: str,
        currency: str = 'BTC',
        max_bets: int = 1000,
        days_back: int = 7,
        save_to_file: bool = True,
    ) -> dict:
        """
        Import bet history from DuckDice API.
        
        Args:
            api_key: DuckDice API key
            currency: Currency to fetch (BTC, ETH, etc.)
            max_bets: Maximum number of bets to fetch
            days_back: How many days back to fetch
            save_to_file: Whether to save to bet_history/
            
        Returns:
            Dictionary with bets and metadata
        """
        self._report_progress("Connecting to DuckDice API...", 0.1)
        
        # Import API client here to avoid circular dependency
        from src.duckdice_api import DuckdiceAPI
        
        if self.api_client is None:
            self.api_client = DuckdiceAPI(api_key)
        
        # TODO: DuckDice API doesn't currently expose bet history endpoint
        # This is a placeholder for when they add it
        
        self._report_progress("Fetching bet history...", 0.3)
        
        # For now, return mock data structure
        result = {
            'bets': [],
            'metadata': {
                'currency': currency,
                'fetched_at': datetime.utcnow().isoformat(),
                'max_bets': max_bets,
                'days_back': days_back,
            },
            'success': False,
            'error': 'DuckDice API does not currently support bet history fetching',
        }
        
        logger.warning("API bet history not available - use file import instead")
        
        self._report_progress("API fetch not available", 1.0)
        
        return result
    
    def import_from_file_and_validate(
        self,
        filepath: Path,
        api_key: Optional[str] = None,
    ) -> dict:
        """
        Import from file and optionally validate via API.
        
        Args:
            filepath: Path to bet history file
            api_key: Optional API key for validation
            
        Returns:
            Dictionary with imported data
        """
        from .file_importer import FileImporter
        
        self._report_progress("Importing from file...", 0.2)
        
        importer = FileImporter()
        result = importer.import_file(filepath)
        
        if not result.success:
            return {
                'success': False,
                'error': f"Import failed: {result.errors}",
            }
        
        self._report_progress("Processing data...", 0.8)
        
        # Convert to dictionary format
        bets = []
        for _, row in result.data.iterrows():
            bet = {
                'outcome': float(row.get('outcome', 0)),
                'nonce': int(row.get('nonce', 0)) if 'nonce' in row else None,
                'timestamp': str(row.get('timestamp', '')),
                'won': bool(row.get('won', False)) if 'won' in row else None,
                'server_seed': str(row.get('server_seed', '')) if 'server_seed' in row else None,
                'client_seed': str(row.get('client_seed', '')) if 'client_seed' in row else None,
            }
            bets.append(bet)
        
        self._report_progress("Import complete", 1.0)
        
        return {
            'success': True,
            'bets': bets,
            'metadata': {
                'source': str(filepath),
                'total_bets': len(bets),
                'imported_at': datetime.utcnow().isoformat(),
                'warnings': result.warnings,
            },
        }
    
    def save_to_bet_history(self, data: dict, filename: Optional[str] = None) -> Path:
        """
        Save imported data to bet_history/ directory.
        
        Args:
            data: Dictionary with bets and metadata
            filename: Optional custom filename
            
        Returns:
            Path to saved file
        """
        bet_history_dir = Path('bet_history')
        bet_history_dir.mkdir(exist_ok=True)
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'imported_{timestamp}.json'
        
        filepath = bet_history_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(data.get('bets', []))} bets to {filepath}")
        
        return filepath
