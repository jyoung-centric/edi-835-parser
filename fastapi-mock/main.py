"""
FastAPI application for querying EDI 835 data by check number.

This mock API provides endpoints to query the TinyDB database
storing EDI 835 payment data.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import sys
import os
from pathlib import Path

# Add the parent directory to the Python path to import database
sys.path.append(str(Path(__file__).parent.parent))

from database_mock import DatabaseManager

app = FastAPI(
    title="EDI 835 Payment Query API",
    description="API for querying EDI 835 payment data stored in TinyDB",
    version="1.0.0"
)

# Database configuration
DB_PATH = os.path.join(Path(__file__).parent.parent, "edi_835_data.json")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "EDI 835 Payment Query API",
        "version": "1.0.0",
        "endpoints": {
            "get_by_check_number": "/payments/check/{check_number}",
            "search_payments": "/payments/search",
            "list_all_payments": "/payments",
            "health_check": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        with DatabaseManager(DB_PATH) as db:
            # Simple check to see if database is accessible
            payments = db.get_all_payments()
            return {
                "status": "healthy",
                "database": "connected",
                "total_payments": len(payments)
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "database": "error",
                "error": str(e)
            }
        )


@app.get("/payments/check/{check_number}")
async def get_payment_by_check_number(check_number: str):
    """
    Query payments by check number.
    
    Args:
        check_number: The check number to search for
        
    Returns:
        JSON response with payment data or error message
    """
    try:
        with DatabaseManager(DB_PATH) as db:
            payments = db.search_payments(check_number=check_number)
            
            if not payments:
                raise HTTPException(
                    status_code=404,
                    detail=f"No payments found for check number: {check_number}"
                )
            
            return {
                "check_number": check_number,
                "found": len(payments),
                "payments": payments
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.get("/payments/search")
async def search_payments(
    payer_id: Optional[str] = Query(None, description="Payer ID to search for"),
    payee_id: Optional[str] = Query(None, description="Payee ID to search for"),
    file_name: Optional[str] = Query(None, description="File name to search for"),
    payment_date: Optional[str] = Query(None, description="Payment date (YYYY-MM-DD) to search for")
):
    """
    Search payments by various criteria.
    
    Args:
        payer_id: Optional payer ID filter
        payee_id: Optional payee ID filter  
        file_name: Optional file name filter
        payment_date: Optional payment date filter
        
    Returns:
        JSON response with matching payment data
    """
    try:
        # Build search criteria
        search_criteria = {}
        if payer_id:
            search_criteria['payer_id'] = payer_id
        if payee_id:
            search_criteria['payee_id'] = payee_id
        if file_name:
            search_criteria['file_name'] = file_name
        if payment_date:
            search_criteria['payment_date'] = payment_date
            
        if not search_criteria:
            raise HTTPException(
                status_code=400,
                detail="At least one search parameter must be provided"
            )
        
        with DatabaseManager(DB_PATH) as db:
            payments = db.search_payments(**search_criteria)
            
            return {
                "search_criteria": search_criteria,
                "found": len(payments),
                "payments": payments
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.get("/payments")
async def list_all_payments(
    limit: Optional[int] = Query(None, description="Limit number of results", ge=1, le=1000)
):
    """
    List all payments in the database.
    
    Args:
        limit: Optional limit on number of results (max 1000)
        
    Returns:
        JSON response with all payment data
    """
    try:
        with DatabaseManager(DB_PATH) as db:
            payments = db.get_all_payments()
            
            if limit and len(payments) > limit:
                payments = payments[:limit]
            
            return {
                "total": len(db.get_all_payments()),
                "returned": len(payments),
                "payments": payments
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.get("/payments/{payment_id}")
async def get_payment_by_id(payment_id: int):
    """
    Get a specific payment by its database ID.
    
    Args:
        payment_id: The database document ID
        
    Returns:
        JSON response with payment data
    """
    try:
        with DatabaseManager(DB_PATH) as db:
            payment = db.get_payment_by_id(payment_id)
            
            if not payment:
                raise HTTPException(
                    status_code=404,
                    detail=f"Payment with ID {payment_id} not found"
                )
            
            return {
                "payment_id": payment_id,
                "payment": payment
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)