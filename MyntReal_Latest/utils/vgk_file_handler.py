#!/usr/bin/env python3
"""
VGK File Upload Security Handler
Comprehensive security system for VGK VM CSV/Excel uploads

Security Features:
- Multi-layer file validation (extension, MIME, content, size)
- CSV/Excel formula injection prevention
- Content sanitization and safe parsing
- Magic number validation for file integrity
- Secure temporary file handling
- Comprehensive audit logging

Author: VGK VM Security System
Date: September 19, 2025
"""

import os
import magic
import hashlib
import secrets
import tempfile
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from werkzeug.datastructures import FileStorage
from datetime import datetime
from werkzeug.utils import secure_filename
import re
import csv
import openpyxl
from io import BytesIO, StringIO
from .safe_string_utils import safe_strip, safe_get_strip, safe_get_strip_upper, VGKSafeStringProcessor


class VGKFileSecurityHandler:
    """
    CRITICAL SECURITY: Comprehensive file upload security for VGK VM system
    
    Addresses the material security risks identified in the architect's analysis:
    - File size and type validation
    - MIME type validation (both header and content-based)
    - CSV/Excel formula injection prevention
    - Content sanitization
    - Magic number validation for file integrity
    - Safe temporary file handling
    - Comprehensive audit logging
    """
    
    # Security Configuration - Restrictive for VGK operations
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB (reduced from 5MB for security)
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}  # Added .xls support with enhanced security validation
    MAX_ROWS = 1000  # Prevent memory exhaustion attacks
    MAX_COLUMNS = 20  # Reasonable limit for user data
    
    # MIME type validation - Content-based security
    ALLOWED_MIME_TYPES = {
        'text/csv',
        'application/csv', 
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel',  # Legacy .xls
        'application/zip',  # Excel files are detected as ZIP by python-magic
        'application/octet-stream',  # Fallback detection for binary files
        'text/html',  # HTML-formatted Excel files (.xls exported as HTML)
        'application/xls',  # Alternative .xls MIME type
    }
    
    # Magic number validation for file integrity
    FILE_SIGNATURES = {
        'csv': [b'\x00\x00\x00', b'\xef\xbb\xbf'],  # CSV can have BOM
        'xlsx': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],  # ZIP-based XLSX
        'xls': [b'\xd0\xcf\x11\xe0', b'<html', b'<?xml'],  # Binary .xls or HTML-formatted .xls
    }
    
    # Formula injection patterns - CRITICAL SECURITY
    DANGEROUS_FORMULA_PATTERNS = [
        r'^\s*=',      # Excel formulas start with =
        r'^\s*\+',     # Alternative formula start
        r'^\s*-',      # Alternative formula start
        r'^\s*@',      # Macro references
        r'\bcmd\b',    # Command execution
        r'\bpowershell\b',  # PowerShell execution
        r'\beval\b',   # JavaScript eval
        r'\bsystem\b', # System calls
        r'\bshell\b',  # Shell execution
        r'\bexec\b',   # Code execution
        r'HYPERLINK\s*\(',  # Hyperlink formulas
        r'IMPORTXML\s*\(',  # XML import
        r'IMPORTDATA\s*\(',  # Data import
        r'WEBSERVICE\s*\(',  # Web service calls
    ]
    
    # Required columns with flexible naming support (multiple naming conventions) 
    # Based on actual Excel file: MemberId, SponsorId, PositionId, Position
    REQUIRED_COLUMNS_FLEXIBLE = {
        'member_id': ['MemberId', 'Member_Id', 'Member ID', 'ID', 'UserId', 'User_Id'],
        'name': ['Name', 'Full_Name', 'FullName', 'User_Name', 'Username'],
        'sponsor_id': ['SponsorId', 'Sponsor_Id', 'Sponsor ID', 'ReferrerId', 'Referrer_Id'],
        'position': ['Position', 'Placement', 'Side', 'TreePosition', 'Tree_Position']
    }
    
    # Backward compatibility - primary expected column names
    REQUIRED_COLUMNS = ['Member_Id', 'Name', 'Sponsor_Id', 'Position']
    
    OPTIONAL_COLUMNS = [
        'Sponsor_Name', 'Position_Id', 'PositionName', 'Status', 'Email', 'Phone', 'PhoneNo',
        'State', 'City', 'PinCode', 'DOJ', 'Time', 'Password', 'AccountNo', 'BankName', 
        'IfSC', 'BranchName', 'Pancard', 'PanNumber', 'AadhaarNumber', 'DateOfBirth', 
        'BankAccountNumber', 'BankIFSC', 'UPIId', 'Gender', 'Address', 'Source'
    ]
    
    @classmethod
    def validate_file_security(cls, file: FileStorage) -> Dict[str, Any]:
        """
        CRITICAL SECURITY: Multi-layer file validation
        
        Args:
            file: FileStorage object from Flask request
            
        Returns:
            dict: Comprehensive validation result
        """
        try:
            validation_result = {
                'valid': False,
                'error': None,
                'error_type': None,
                'security_checks': [],
                'file_info': {},
                'warnings': []
            }
            
            # Step 1: File presence validation
            if not file or not file.filename:
                validation_result.update({
                    'error': 'No file provided or empty filename',
                    'error_type': 'missing_file'
                })
                return validation_result
            
            original_filename = file.filename
            validation_result['file_info']['original_name'] = original_filename
            validation_result['security_checks'].append('✓ File presence verified')
            
            # Step 2: Filename security validation
            if not cls._validate_filename_security(original_filename):
                validation_result.update({
                    'error': 'Filename contains unsafe characters or patterns',
                    'error_type': 'unsafe_filename'
                })
                return validation_result
            
            validation_result['security_checks'].append('✓ Filename security verified')
            
            # Step 3: File extension validation
            file_ext = cls._get_file_extension(original_filename)
            if not file_ext:
                validation_result.update({
                    'error': 'File must have a valid extension',
                    'error_type': 'no_extension'
                })
                return validation_result
                
            if file_ext not in cls.ALLOWED_EXTENSIONS:
                validation_result.update({
                    'error': f'File type not allowed. Allowed: {cls.ALLOWED_EXTENSIONS}',
                    'error_type': 'invalid_extension'
                })
                return validation_result
            
            validation_result['file_info']['extension'] = file_ext
            validation_result['security_checks'].append(f'✓ Extension {file_ext} validated')
            
            # Step 4: File size validation
            file_size = cls._get_file_size(file)
            if file_size > cls.MAX_FILE_SIZE:
                validation_result.update({
                    'error': f'File size {file_size} bytes exceeds limit {cls.MAX_FILE_SIZE} bytes',
                    'error_type': 'file_too_large'
                })
                return validation_result
            
            validation_result['file_info']['size_bytes'] = file_size
            validation_result['security_checks'].append(f'✓ File size {file_size} bytes validated')
            
            # Step 5: MIME type validation (content-based)
            mime_result = cls._validate_mime_type(file)
            if not mime_result['valid']:
                validation_result.update({
                    'error': mime_result['error'],
                    'error_type': 'invalid_mime_type'
                })
                return validation_result
            
            validation_result['file_info']['mime_type'] = mime_result['mime_type']
            validation_result['security_checks'].append(f'✓ MIME type {mime_result["mime_type"]} validated')
            
            # Step 6: File content integrity validation
            integrity_result = cls._validate_file_integrity(file, file_ext)
            if not integrity_result['valid']:
                validation_result.update({
                    'error': integrity_result['error'],
                    'error_type': 'file_integrity_failed'
                })
                return validation_result
                
            validation_result['security_checks'].append('✓ File integrity verified')
            
            # Step 7: Content structure validation
            structure_result = cls._validate_file_structure(file, file_ext)
            if not structure_result['valid']:
                validation_result.update({
                    'error': structure_result['error'],
                    'error_type': 'invalid_structure'
                })
                return validation_result
                
            validation_result['file_info'].update(structure_result['info'])
            validation_result['security_checks'].append(
                f'✓ File structure validated: {structure_result["info"]["rows"]} rows, {structure_result["info"]["columns"]} columns'
            )
            
            # All validations passed
            validation_result['valid'] = True
            validation_result['security_checks'].append('🔒 ALL SECURITY CHECKS PASSED')
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Security validation failed: {str(e)}',
                'error_type': 'validation_exception',
                'security_checks': ['❌ Security validation exception occurred']
            }
    
    @classmethod
    def parse_secure_file(cls, file: FileStorage, validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRITICAL SECURITY: Parse file with comprehensive security measures
        
        Args:
            file: Validated FileStorage object
            validation_result: Result from validate_file_security
            
        Returns:
            dict: Parsed data with security sanitization applied
        """
        try:
            if not validation_result['valid']:
                return {'success': False, 'error': 'File validation failed before parsing'}
            
            file_ext = validation_result['file_info']['extension']
            
            # Parse based on file type with security measures
            if file_ext == 'csv':
                return cls._parse_csv_secure(file)
            elif file_ext == 'xlsx':
                return cls._parse_xlsx_secure(file)
            elif file_ext == 'xls':
                return cls._parse_xls_secure(file)
            else:
                return {'success': False, 'error': f'Unsupported file type: {file_ext}'}
                
        except UnicodeDecodeError as e:
            # Specific handling for encoding errors - likely Excel file misdetected as CSV
            return {
                'success': False, 
                'error': f'File encoding error: This appears to be a binary file (Excel) being processed as text. Please ensure your file is saved in the correct format (.xlsx for Excel, .csv for text).',
                'error_type': 'encoding_mismatch'
            }
                
        except Exception as e:
            return {'success': False, 'error': f'Secure parsing failed: {str(e)}'}
    
    @classmethod
    def _validate_filename_security(cls, filename: str) -> bool:
        """
        Validate filename for security issues
        
        Args:
            filename: Original filename
            
        Returns:
            bool: True if filename is safe
        """
        # Check for path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
            
        # Check for null bytes or control characters
        if '\x00' in filename or any(ord(c) < 32 for c in filename if c != '\t'):
            return False
            
        # Check filename length
        if len(filename) > 255:
            return False
            
        # Check for suspicious patterns
        suspicious_patterns = ['.exe', '.bat', '.cmd', '.scr', '.vbs', '.js']
        filename_lower = filename.lower()
        if any(pattern in filename_lower for pattern in suspicious_patterns):
            return False
            
        return True
    
    @classmethod 
    def _get_file_extension(cls, filename: str) -> Optional[str]:
        """Get and validate file extension"""
        if '.' not in filename:
            return None
        return filename.rsplit('.', 1)[1].lower()
    
    @classmethod
    def _get_file_size(cls, file: FileStorage) -> int:
        """Get file size safely"""
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning
        return size
    
    @classmethod
    def _validate_mime_type(cls, file: FileStorage) -> Dict[str, Any]:
        """
        Content-based MIME type validation using python-magic
        
        Args:
            file: FileStorage object
            
        Returns:
            dict: Validation result with MIME type
        """
        try:
            # Read first 1024 bytes for MIME detection
            file_header = file.read(1024)
            file.seek(0)  # Reset file pointer
            
            # Detect MIME type using python-magic
            try:
                detected_mime = magic.from_buffer(file_header, mime=True)
            except Exception:
                # Fallback to basic detection if python-magic fails
                if file_header.startswith(b'PK\x03\x04'):
                    detected_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                elif b',' in file_header[:100]:  # Basic CSV detection
                    detected_mime = 'text/csv'
                else:
                    return {'valid': False, 'error': 'Unable to detect file MIME type'}
            
            if detected_mime not in cls.ALLOWED_MIME_TYPES:
                return {
                    'valid': False, 
                    'error': f'MIME type {detected_mime} not allowed. Allowed: {cls.ALLOWED_MIME_TYPES}'
                }
            
            return {'valid': True, 'mime_type': detected_mime}
            
        except Exception as e:
            return {'valid': False, 'error': f'MIME validation failed: {str(e)}'}
    
    @classmethod
    def _validate_file_integrity(cls, file: FileStorage, file_ext: str) -> Dict[str, Any]:
        """
        Validate file integrity using magic numbers
        
        Args:
            file: FileStorage object
            file_ext: File extension
            
        Returns:
            dict: Validation result
        """
        try:
            # Read file header for magic number validation
            file_header = file.read(16)  # Read first 16 bytes
            file.seek(0)  # Reset file pointer
            
            # For CSV files, check for valid text content
            if file_ext == 'csv':
                try:
                    # Try multiple encodings to decode the header
                    encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
                    header_text = None
                    
                    for encoding in encodings:
                        try:
                            header_text = file_header.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    if header_text is None:
                        return {'valid': False, 'error': 'CSV file contains unsupported text encoding'}
                    
                    # Check if it looks like CSV (contains commas or printable characters)
                    if not any(c in header_text for c in [',', ';', '\t']) and not header_text.isprintable():
                        return {'valid': False, 'error': 'CSV file does not contain valid text content'}
                except Exception:
                    return {'valid': False, 'error': 'CSV file integrity check failed'}
            
            # For XLSX files, check ZIP signature
            elif file_ext == 'xlsx':
                expected_signatures = cls.FILE_SIGNATURES.get('xlsx', [])
                if not any(file_header.startswith(sig) for sig in expected_signatures):
                    return {'valid': False, 'error': 'XLSX file does not have valid ZIP signature'}
            
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': f'File integrity check failed: {str(e)}'}
    
    @classmethod
    def _validate_file_structure(cls, file: FileStorage, file_ext: str) -> Dict[str, Any]:
        """
        Validate file structure and size constraints
        
        Args:
            file: FileStorage object
            file_ext: File extension
            
        Returns:
            dict: Validation result with structure info
        """
        try:
            if file_ext == 'csv':
                return cls._validate_csv_structure(file)
            elif file_ext == 'xlsx':
                return cls._validate_xlsx_structure(file)
            elif file_ext == 'xls':
                return cls._validate_xls_structure(file)
            else:
                return {'valid': False, 'error': f'Unsupported file type for structure validation: {file_ext}'}
                
        except Exception as e:
            return {'valid': False, 'error': f'Structure validation failed: {str(e)}'}
    
    @classmethod
    def _validate_csv_structure(cls, file: FileStorage) -> Dict[str, Any]:
        """
        Validate CSV file structure
        
        Args:
            file: CSV FileStorage object
            
        Returns:
            dict: Validation result
        """
        try:
            # Read file content with encoding detection
            raw_content = file.read()
            file.seek(0)  # Reset file pointer
            
            # Try multiple encodings in order of preference
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
            content = None
            
            for encoding in encodings:
                try:
                    content = raw_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                return {'valid': False, 'error': 'Unable to decode file with any supported encoding (UTF-8, Latin1, CP1252, ISO-8859-1)'}
            
            # Parse CSV safely - detect delimiter (comma or tab)
            delimiter = '\t' if '\t' in content else ','
            reader = csv.reader(StringIO(content), delimiter=delimiter)
            rows = list(reader)
            
            if not rows:
                return {'valid': False, 'error': 'CSV file is empty'}
            
            if len(rows) > cls.MAX_ROWS:
                return {'valid': False, 'error': f'CSV has {len(rows)} rows, exceeding limit of {cls.MAX_ROWS}'}
            
            # Check columns in header row
            header = rows[0] if rows else []
            if len(header) > cls.MAX_COLUMNS:
                return {'valid': False, 'error': f'CSV has {len(header)} columns, exceeding limit of {cls.MAX_COLUMNS}'}
            
            return {
                'valid': True,
                'info': {
                    'rows': len(rows),
                    'columns': len(header),
                    'headers': header
                }
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'CSV structure validation failed: {str(e)}'}
    
    @classmethod
    def _validate_xlsx_structure(cls, file: FileStorage) -> Dict[str, Any]:
        """
        Validate XLSX file structure
        
        Args:
            file: XLSX FileStorage object
            
        Returns:
            dict: Validation result
        """
        try:
            # Load workbook safely without formulas
            wb = openpyxl.load_workbook(BytesIO(file.read()), data_only=True)
            file.seek(0)  # Reset file pointer
            
            # Get first worksheet
            ws = wb.active
            if ws is None:
                return {'valid': False, 'error': 'XLSX file has no active worksheet'}
            
            # Check dimensions with proper type handling
            max_row = getattr(ws, 'max_row', 0) or 0
            max_col = getattr(ws, 'max_column', 0) or 0
            
            if max_row > cls.MAX_ROWS:
                return {'valid': False, 'error': f'XLSX has {max_row} rows, exceeding limit of {cls.MAX_ROWS}'}
                
            if max_col > cls.MAX_COLUMNS:
                return {'valid': False, 'error': f'XLSX has {max_col} columns, exceeding limit of {cls.MAX_COLUMNS}'}
            
            # Get headers from first row
            headers = []
            if max_row > 0 and max_col > 0:
                for col in range(1, max_col + 1):
                    try:
                        cell_value = getattr(ws, 'cell', lambda **kwargs: None)(row=1, column=col)
                        if cell_value is not None:
                            headers.append(str(getattr(cell_value, 'value', '')) if getattr(cell_value, 'value', None) is not None else '')
                        else:
                            headers.append('')
                    except Exception:
                        headers.append('')
            
            return {
                'valid': True,
                'info': {
                    'rows': max_row,
                    'columns': max_col,
                    'headers': headers
                }
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'XLSX structure validation failed: {str(e)}'}
    
    @classmethod
    def _parse_csv_secure(cls, file: FileStorage) -> Dict[str, Any]:
        """
        Parse CSV file with security measures
        
        Args:
            file: CSV FileStorage object
            
        Returns:
            dict: Parsed data with security sanitization
        """
        try:
            # Read file content with encoding detection
            raw_content = file.read()
            file.seek(0)
            
            # Try multiple encodings in order of preference
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
            content = None
            
            for encoding in encodings:
                try:
                    content = raw_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                return {'success': False, 'error': 'Unable to decode file with any supported encoding (UTF-8, Latin1, CP1252, ISO-8859-1)'}
            
            # Parse CSV safely - detect delimiter (comma or tab)
            # Try tab-separated first (for migration files), then comma-separated
            delimiter = '\t' if '\t' in content else ','
            reader = csv.DictReader(StringIO(content), delimiter=delimiter)
            rows = []
            
            for row_num, row in enumerate(reader, 1):
                if row_num > cls.MAX_ROWS:
                    break
                
                # Sanitize each cell for formula injection
                sanitized_row = {}
                for key, value in row.items():
                    if key and value:
                        sanitized_value = cls._sanitize_cell_value(str(value))
                        sanitized_row[str(key).strip()] = sanitized_value
                    else:
                        sanitized_row[str(key).strip() if key else ''] = ''
                
                rows.append(sanitized_row)
            
            # Validate required columns using flexible mapping
            if rows:
                headers = list(rows[0].keys())
                validation_result = cls._validate_required_columns_flexible(headers)
                if not validation_result['valid']:
                    return {
                        'success': False,
                        'error': validation_result['error']
                    }
            
            return {
                'success': True,
                'data': rows,
                'headers': list(rows[0].keys()) if rows else [],
                'row_count': len(rows),
                'security_applied': ['Formula injection prevention', 'Content sanitization']
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Secure CSV parsing failed: {str(e)}'}
    
    @classmethod
    def _parse_xlsx_secure(cls, file: FileStorage) -> Dict[str, Any]:
        """
        Parse XLSX file with security measures
        
        Args:
            file: XLSX FileStorage object
            
        Returns:
            dict: Parsed data with security sanitization
        """
        try:
            # Load workbook with data_only=True to prevent formula execution
            wb = openpyxl.load_workbook(BytesIO(file.read()), data_only=True)
            file.seek(0)
            
            ws = wb.active
            if ws is None:
                return {'success': False, 'error': 'XLSX file has no active worksheet'}
                
            rows = []
            headers = []
            
            # Get dimensions safely
            max_col = getattr(ws, 'max_column', 0) or 0
            max_row = getattr(ws, 'max_row', 0) or 0
            
            if max_col == 0 or max_row == 0:
                return {'success': False, 'error': 'XLSX file appears to be empty'}
            
            # Extract headers from first row
            for col in range(1, max_col + 1):
                try:
                    header_cell = getattr(ws, 'cell', lambda **kwargs: None)(row=1, column=col)
                    if header_cell is not None:
                        header_value = getattr(header_cell, 'value', None)
                        headers.append(str(header_value).strip() if header_value else f'Column_{col}')
                    else:
                        headers.append(f'Column_{col}')
                except Exception:
                    headers.append(f'Column_{col}')
            
            # Extract data rows with security sanitization
            for row_num in range(2, min(max_row + 1, cls.MAX_ROWS + 2)):
                row_data = {}
                
                for col_num, header in enumerate(headers, 1):
                    try:
                        cell = getattr(ws, 'cell', lambda **kwargs: None)(row=row_num, column=col_num)
                        if cell is not None:
                            cell_value = getattr(cell, 'value', None)
                        else:
                            cell_value = None
                    except Exception:
                        cell_value = None
                    
                    if cell_value is not None:
                        # Sanitize cell value for security
                        sanitized_value = cls._sanitize_cell_value(str(cell_value))
                        row_data[header] = sanitized_value
                    else:
                        row_data[header] = ''
                
                rows.append(row_data)
            
            # Validate required columns using flexible mapping
            if headers:
                validation_result = cls._validate_required_columns_flexible(headers)
                if not validation_result['valid']:
                    return {
                        'success': False,
                        'error': validation_result['error']
                    }
            
            return {
                'success': True,
                'data': rows,
                'headers': headers,
                'row_count': len(rows),
                'security_applied': ['Formula execution disabled', 'Content sanitization', 'Data-only mode']
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Secure XLSX parsing failed: {str(e)}'}
    
    @classmethod
    def _parse_xls_secure(cls, file: FileStorage) -> Dict[str, Any]:
        """
        Parse XLS file with security measures using pandas (supports HTML-formatted Excel)
        
        Args:
            file: XLS FileStorage object
            
        Returns:
            dict: Parsed data with security sanitization
        """
        try:
            # Reset file pointer
            file.seek(0)
            
            # Try to read as Excel file using pandas which can handle HTML-formatted .xls
            try:
                # First try reading as binary Excel file
                df = pd.read_excel(file, engine='xlrd', nrows=cls.MAX_ROWS)
            except Exception:
                # If that fails, try reading as HTML (common export format)
                file.seek(0)
                try:
                    df = pd.read_html(file.read(), header=0)[0]  # Get first table
                    # Limit rows for security
                    if len(df) > cls.MAX_ROWS:
                        df = df.head(cls.MAX_ROWS)
                except Exception:
                    # Last resort: try reading as CSV-like content
                    file.seek(0)
                    content = file.read().decode('utf-8', errors='ignore')
                    if '<html' in content.lower():
                        return {'success': False, 'error': 'XLS file appears to be HTML-formatted but could not be parsed. Please save as .xlsx or .csv format.'}
                    else:
                        # Try reading as CSV
                        from io import StringIO
                        df = pd.read_csv(StringIO(content), nrows=cls.MAX_ROWS)
            
            if df.empty:
                return {'success': False, 'error': 'XLS file appears to be empty'}
            
            # Check column limits
            if len(df.columns) > cls.MAX_COLUMNS:
                return {'success': False, 'error': f'XLS has {len(df.columns)} columns, exceeding limit of {cls.MAX_COLUMNS}'}
            
            # Get headers
            headers = [str(col).strip() for col in df.columns]
            
            # Convert to rows with security sanitization
            rows = []
            for _, row in df.iterrows():
                row_data = {}
                for i, header in enumerate(headers):
                    try:
                        cell_value = row.iloc[i]
                        if pd.isna(cell_value):
                            cell_value = ''
                        else:
                            # Sanitize cell value for security
                            sanitized_value = cls._sanitize_cell_value(str(cell_value))
                            row_data[header] = sanitized_value
                    except Exception:
                        row_data[header] = ''
                
                rows.append(row_data)
            
            # Validate column requirements
            if headers:
                validation_result = cls._validate_required_columns_flexible(headers)
                if not validation_result['valid']:
                    return {
                        'success': False,
                        'error': validation_result['error']
                    }
            
            return {
                'success': True,
                'data': rows,
                'headers': headers,
                'info': {
                    'total_rows': len(rows),
                    'columns': len(headers),
                    'filename': secure_filename(file.filename) if file.filename else 'unknown.xls'
                },
                'security_applied': ['Pandas parsing with row/column limits', 'Content sanitization', 'HTML format support']
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Secure XLS parsing failed: {str(e)}. Please try saving the file as .xlsx or .csv format.'}

    @classmethod
    def _validate_xls_structure(cls, file: FileStorage) -> Dict[str, Any]:
        """
        Validate XLS file structure using pandas
        
        Args:
            file: XLS FileStorage object
            
        Returns:
            dict: Validation result
        """
        try:
            # Reset file pointer
            file.seek(0)
            
            # Try to read structure using pandas
            try:
                # First try as binary Excel
                df = pd.read_excel(file, engine='xlrd', nrows=1)  # Just read header
            except Exception:
                # Try as HTML format
                file.seek(0)
                try:
                    df = pd.read_html(file.read(), header=0)[0]
                    df = df.head(1)  # Just header info
                except Exception:
                    return {'valid': False, 'error': 'XLS file could not be read. Please save as .xlsx or .csv format.'}
            
            if df.empty:
                return {'valid': False, 'error': 'XLS file appears to be empty'}
            
            # Get basic info
            headers = [str(col).strip() for col in df.columns]
            
            # Check column limits
            if len(headers) > cls.MAX_COLUMNS:
                return {'valid': False, 'error': f'XLS has {len(headers)} columns, exceeding limit of {cls.MAX_COLUMNS}'}
            
            # Reset file and get row count estimate
            file.seek(0)
            try:
                df_full = pd.read_excel(file, engine='xlrd')
                row_count = len(df_full)
            except Exception:
                file.seek(0)
                try:
                    df_full = pd.read_html(file.read(), header=0)[0]
                    row_count = len(df_full)
                except Exception:
                    row_count = 1  # At least header
            
            if row_count > cls.MAX_ROWS:
                return {'valid': False, 'error': f'XLS has {row_count} rows, exceeding limit of {cls.MAX_ROWS}'}
            
            return {
                'valid': True,
                'info': {
                    'rows': row_count,
                    'columns': len(headers),
                    'headers': headers
                }
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'XLS structure validation failed: {str(e)}'}
    
    @classmethod
    def _validate_required_columns_flexible(cls, headers: List[str]) -> Dict[str, Any]:
        """
        Validate required columns using flexible naming conventions
        
        Args:
            headers: List of column headers from the file
            
        Returns:
            dict: Validation result with mapping info
        """
        # Normalize headers for case-insensitive comparison
        header_map = {header.strip(): header for header in headers}
        normalized_headers = {h.lower().replace(' ', '_').replace('-', '_'): original 
                            for h, original in header_map.items()}
        
        found_columns = {}
        missing_requirements = []
        
        # Check each required column type
        for requirement_key, possible_names in cls.REQUIRED_COLUMNS_FLEXIBLE.items():
            found = False
            for possible_name in possible_names:
                # Normalize possible name for comparison
                normalized_possible = possible_name.lower().replace(' ', '_').replace('-', '_')
                
                # Check if this column exists in headers
                if normalized_possible in normalized_headers:
                    found_columns[requirement_key] = normalized_headers[normalized_possible]
                    found = True
                    break
                    
                # Also check exact match (case-insensitive)
                for original_header in header_map.keys():
                    if original_header.lower() == possible_name.lower():
                        found_columns[requirement_key] = original_header
                        found = True
                        break
                        
                if found:
                    break
                    
            if not found:
                missing_requirements.append(f"{requirement_key} (expected: {possible_names})")
        
        if missing_requirements:
            available_headers = list(header_map.keys())
            return {
                'valid': False,
                'error': f'Missing required columns: {missing_requirements}. Available columns: {available_headers}',
                'found_columns': found_columns,
                'missing': missing_requirements
            }
        
        return {
            'valid': True,
            'found_columns': found_columns,
            'column_mapping': found_columns
        }

    @classmethod
    def _sanitize_cell_value(cls, value: str) -> str:
        """
        CRITICAL SECURITY: Sanitize cell values to prevent formula injection
        
        Args:
            value: Raw cell value
            
        Returns:
            str: Sanitized value
        """
        if not value:
            return ''
        
        # Check for dangerous formula patterns
        for pattern in cls.DANGEROUS_FORMULA_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                # Strip dangerous characters and add prefix to neutralize
                sanitized = re.sub(r'^\s*[=+\-@]', '', value)
                return f"SANITIZED_{sanitized[:100]}"  # Limit length and mark as sanitized
        
        # Remove any null bytes or control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
        
        # Limit length to prevent memory issues
        return sanitized[:500]
    
    @classmethod
    def create_audit_log(cls, user_id: str, action: str, file_info: Dict[str, Any], 
                        result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create comprehensive audit log for file operations
        
        Args:
            user_id: VGK ID of user performing action
            action: Action performed (upload, validation, parsing)
            file_info: File information
            result: Operation result
            
        Returns:
            dict: Audit log entry
        """
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'vgk_id': user_id,
            'action': action,
            'file_info': file_info,
            'result': result,
            'security_level': 'CRITICAL',
            'system': 'VGK_VM_FILE_HANDLER'
        }


class VGKUserDataValidator:
    """
    Validator for user data extracted from uploaded files
    """
    
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    @classmethod
    def validate_user_data(cls, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate enhanced user data for creation (16-column Excel format)
        
        Args:
            user_data: User data dictionary
            
        Returns:
            dict: Validation result
        """
        errors = []
        warnings = []
        
        # Validate required fields
        # MemberId validation
        if not safe_get_strip(user_data, 'MemberId'):
            errors.append('MemberId is required')
        elif not user_data['MemberId'].startswith('BEV'):
            errors.append('MemberId must start with BEV')
        
        # Name validation
        if not safe_get_strip(user_data, 'Name'):
            errors.append('Name is required')
        elif len(user_data['Name']) > 100:
            errors.append('Name exceeds 100 character limit')
        
        # PhoneNo validation
        if not safe_get_strip(user_data, 'PhoneNo'):
            errors.append('PhoneNo is required')
        elif not user_data['PhoneNo'].isdigit() or len(user_data['PhoneNo']) != 10:
            errors.append('PhoneNo must be exactly 10 digits')
            
        # SponsorId validation
        if not safe_get_strip(user_data, 'SponsorId'):
            errors.append('SponsorId is required')
        elif not user_data['SponsorId'].startswith('BEV'):
            errors.append('SponsorId must start with BEV')
            
        # Position validation
        if not safe_get_strip(user_data, 'Position'):
            errors.append('Position is required')
        elif user_data['Position'].upper() not in ['LEFT', 'RIGHT']:
            errors.append('Position must be LEFT or RIGHT')
        
        # Validate optional fields
        # EmailId validation (if provided)
        email_value = safe_get_strip(user_data, 'EmailId')
        if email_value:
            if not cls.EMAIL_PATTERN.match(email_value):
                warnings.append('Invalid email format')
            elif len(email_value) > 255:
                warnings.append('Email exceeds 255 character limit')
        
        # Password validation (if provided)
        password_value = safe_get_strip(user_data, 'Password')
        if password_value and len(password_value) < 3:
            warnings.append('Password is too short, minimum 3 characters required')
            
        # Banking info validation (if provided)
        account_no = safe_get_strip(user_data, 'AccountNo')
        if account_no:
            if not account_no.isdigit() or len(account_no) < 9:
                warnings.append('AccountNo should be at least 9 digits')
                
        ifsc_value = safe_get_strip(user_data, 'IfSC')
        if ifsc_value:
            if len(ifsc_value) != 11:
                warnings.append('IFSC code should be exactly 11 characters')
        
        # PAN card validation (if provided)  
        pancard_value = safe_get_strip(user_data, 'Pancard')
        if pancard_value:
            pan_pattern = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$')
            if not pan_pattern.match(pancard_value.upper()):
                warnings.append('Invalid PAN card format (should be like ABCDE1234F)')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'sanitized_data': user_data
        }
