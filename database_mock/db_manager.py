"""Database manager for EDI 835 parsed data using TinyDB."""

from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
from tinydb import TinyDB, Query


class DatabaseManager:
    """Manages storage and retrieval of EDI 835 parsed data."""
    
    def __init__(self, db_path: str = "edi_835_data.json"):
        """
        Initialize the database manager.
        
        Args:
            db_path: Path to the TinyDB database file (default: edi_835_data.json)
        """
        self.db_path = Path(db_path)
        self.db = TinyDB(self.db_path)
        
        # Single table approach matching payments_835 schema
        self.payments_table = self.db.table('payments_835')
    
    def store_payment_835(self, file_data: Dict[str, Any]) -> int:
        """
        Store a complete 835 payment file using the single table approach.
        
        Args:
            file_data: Dictionary containing the complete file data
            Expected fields matching payments_835 schema:
            - file_name: TEXT
            - check_number: TEXT  
            - payment_date: DATE
            - payment_amount: NUMERIC
            - payer_id: TEXT
            - payee_id: TEXT
            - json_transaction: JSONB (complete parsed data)
            - raw_edi: TEXT (original EDI content)
            
        Returns:
            Document ID of the inserted payment record
        """
        import uuid
        
        payment_record = {
            'file_id': str(uuid.uuid4()),
            'file_name': file_data.get('file_name'),
            'received_at': datetime.now().isoformat(),
            'check_number': file_data.get('check_number'),
            'payment_date': file_data.get('payment_date'),
            'payment_amount': file_data.get('payment_amount'),
            'payer_id': file_data.get('payer_id'),
            'payee_id': file_data.get('payee_id'),
            'json_transaction': file_data.get('json_transaction', file_data),
            'raw_edi': file_data.get('raw_edi'),
            'created_at': datetime.now().isoformat()
        }
        
        return self.payments_table.insert(payment_record)
    
    def get_payment_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a payment record by its document ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Payment data or None if not found
        """
        return self.payments_table.get(doc_id=doc_id)
    
    def get_all_payments(self) -> List[Dict[str, Any]]:
        """
        Retrieve all stored payment records.
        
        Returns:
            List of all payment records
        """
        return self.payments_table.all()
    
    def search_payments(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Search payment records by field values.
        
        Args:
            **kwargs: Field-value pairs to search for
            
        Returns:
            List of matching payment records
            
        Example:
            db.search_payments(payer_id="12345")
            db.search_payments(check_number="CHK001")
        """
        PaymentQuery = Query()
        conditions = [getattr(PaymentQuery, key) == value for key, value in kwargs.items()]
        
        if len(conditions) == 1:
            return self.payments_table.search(conditions[0])
        
        # Combine multiple conditions with AND
        combined = conditions[0]
        for condition in conditions[1:]:
            combined = combined & condition
        
        return self.payments_table.search(combined)
    
    def search_payments_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Search payment records by payment date range.
        
        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            
        Returns:
            List of payment records within the date range
        """
        PaymentQuery = Query()
        return self.payments_table.search(
            (PaymentQuery.payment_date >= start_date) & 
            (PaymentQuery.payment_date <= end_date)
        )
    
    def delete_payment(self, doc_id: int) -> List[int]:
        """
        Delete a payment record by its document ID.
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            List of deleted document IDs
        """
        return self.payments_table.remove(doc_ids=[doc_id])
    
    def clear_all_data(self):
        """Clear all data from the payments table."""
        self.payments_table.truncate()
    
    def close(self):
        """Close the database connection."""
        self.db.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
