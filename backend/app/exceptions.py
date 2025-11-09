"""
Custom exceptions for the ETF Weekly Report application
"""


class ETFAppException(Exception):
    """Base exception for all application-specific errors"""
    pass


class DatabaseException(ETFAppException):
    """Exception raised for database-related errors"""
    pass


class ValidationException(ETFAppException):
    """Exception raised for data validation errors"""
    pass


class ScraperException(ETFAppException):
    """Exception raised for web scraping errors"""
    pass


class DataNotFoundException(ETFAppException):
    """Exception raised when requested data is not found"""
    pass


class ExternalServiceException(ETFAppException):
    """Exception raised for external service/API errors"""
    pass
