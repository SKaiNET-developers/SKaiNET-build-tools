"""
File Handler Module

Manages secure file operations for IREE Docker compilation.
Handles input/output file management, temporary file cleanup, and security validation.

Requirements: 10.3, 10.1
"""

import os
import shutil
import tempfile
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from contextlib import contextmanager


class SecureFileHandler:
    """Handles secure file operations for Docker compilation."""
    
    def __init__(self, base_input_dir: Optional[Path] = None, base_output_dir: Optional[Path] = None):
        """Initialize file handler with base directories."""
        self.base_input_dir = base_input_dir or Path("input")
        self.base_output_dir = base_output_dir or Path("output")
        self.temp_dirs: List[Path] = []
        
        # Ensure base directories exist
        self.base_input_dir.mkdir(parents=True, exist_ok=True)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_input_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate input file for security and format requirements.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path.exists():
            return False, f"Input file does not exist: {file_path}"
        
        if not file_path.is_file():
            return False, f"Input path is not a file: {file_path}"
        
        # Check file extension
        if not file_path.suffix.lower() == '.mlir':
            return False, f"Input file must have .mlir extension, got: {file_path.suffix}"
        
        # Check file size (reasonable limit for MLIR files)
        file_size = file_path.stat().st_size
        max_size = 100 * 1024 * 1024  # 100MB limit
        if file_size > max_size:
            return False, f"Input file too large: {file_size} bytes (max: {max_size})"
        
        # Basic content validation - check if it looks like MLIR
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_lines = f.read(1024)  # Read first 1KB
                if not any(keyword in first_lines for keyword in ['module', 'func', 'stablehlo']):
                    return False, "Input file does not appear to be valid MLIR content"
        except UnicodeDecodeError:
            return False, "Input file is not valid UTF-8 text"
        except Exception as e:
            return False, f"Error reading input file: {e}"
        
        return True, ""
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal and other security issues."""
        # Remove path separators and dangerous characters
        sanitized = "".join(c for c in filename if c.isalnum() or c in "._-")
        
        # Ensure it's not empty and doesn't start with dot
        if not sanitized or sanitized.startswith('.'):
            sanitized = f"file_{sanitized}"
        
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized
    
    def prepare_input_file(self, source_path: Path, target_filename: Optional[str] = None) -> Path:
        """
        Prepare input file for Docker compilation.
        
        Args:
            source_path: Path to source MLIR file
            target_filename: Optional target filename (will be sanitized)
            
        Returns:
            Path to prepared input file in input directory
        """
        # Validate input file
        is_valid, error_msg = self.validate_input_file(source_path)
        if not is_valid:
            raise ValueError(f"Input file validation failed: {error_msg}")
        
        # Determine target filename
        if target_filename:
            target_name = self.sanitize_filename(target_filename)
            if not target_name.endswith('.mlir'):
                target_name += '.mlir'
        else:
            target_name = self.sanitize_filename(source_path.name)
        
        # Copy to input directory
        target_path = self.base_input_dir / target_name
        
        # Ensure we don't overwrite existing files accidentally
        counter = 1
        original_target = target_path
        while target_path.exists():
            stem = original_target.stem
            suffix = original_target.suffix
            target_path = original_target.parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.copy2(source_path, target_path)
        
        # Set secure permissions (read-only for group/others)
        target_path.chmod(0o644)
        
        return target_path
    
    def prepare_output_directory(self, output_filename: Optional[str] = None) -> Path:
        """
        Prepare output directory and return expected output file path.
        
        Args:
            output_filename: Optional output filename (will be sanitized)
            
        Returns:
            Path where output file should be created
        """
        # Determine output filename
        if output_filename:
            output_name = self.sanitize_filename(output_filename)
        else:
            output_name = "model.vmfb"
        
        # Ensure proper extension based on format
        if not any(output_name.endswith(ext) for ext in ['.vmfb', '.so', '.dylib']):
            output_name += '.vmfb'
        
        output_path = self.base_output_dir / output_name
        
        # Ensure output directory exists and is writable
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        return output_path
    
    @contextmanager
    def temporary_directory(self, prefix: str = "iree_temp_"):
        """
        Create a temporary directory with automatic cleanup.
        
        Args:
            prefix: Prefix for temporary directory name
            
        Yields:
            Path to temporary directory
        """
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix))
        self.temp_dirs.append(temp_dir)
        
        try:
            yield temp_dir
        finally:
            self.cleanup_temporary_directory(temp_dir)
    
    def cleanup_temporary_directory(self, temp_dir: Path) -> None:
        """Clean up a specific temporary directory."""
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            if temp_dir in self.temp_dirs:
                self.temp_dirs.remove(temp_dir)
        except Exception as e:
            # Log error but don't raise - cleanup should be best effort
            print(f"Warning: Failed to cleanup temporary directory {temp_dir}: {e}")
    
    def cleanup_all_temporary_files(self) -> None:
        """Clean up all temporary directories created by this handler."""
        for temp_dir in self.temp_dirs.copy():
            self.cleanup_temporary_directory(temp_dir)
    
    def calculate_file_hash(self, file_path: Path, algorithm: str = "sha256") -> str:
        """Calculate hash of a file for integrity verification."""
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
    
    def verify_output_file(self, output_path: Path, expected_format: str = "vmfb") -> Tuple[bool, str]:
        """
        Verify output file was created successfully and has expected properties.
        
        Returns:
            Tuple of (is_valid, error_message_or_info)
        """
        if not output_path.exists():
            return False, f"Output file was not created: {output_path}"
        
        if not output_path.is_file():
            return False, f"Output path is not a file: {output_path}"
        
        # Check file size (should not be empty)
        file_size = output_path.stat().st_size
        if file_size == 0:
            return False, "Output file is empty"
        
        # Check file extension matches expected format
        expected_ext = f".{expected_format}"
        if not output_path.name.endswith(expected_ext):
            return False, f"Output file extension doesn't match format: expected {expected_ext}"
        
        # Basic format validation
        if expected_format == "vmfb":
            # VMFB files should be binary and start with specific magic bytes
            try:
                with open(output_path, 'rb') as f:
                    header = f.read(16)
                    if len(header) < 4:
                        return False, "Output file too small to be valid VMFB"
                    # Note: Actual VMFB magic bytes validation would go here
            except Exception as e:
                return False, f"Error reading output file: {e}"
        
        return True, f"Output file valid: {file_size} bytes"
    
    def create_volume_mappings(self, input_file: Path, output_file: Path, 
                             config_data: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, str]], Path]:
        """
        Create Docker volume mappings for secure file access.
        
        Returns:
            Tuple of (volume_mappings, config_file_path)
        """
        # Create temporary config file
        with self.temporary_directory("config_") as temp_dir:
            config_file = temp_dir / "compile_config.json"
            
            # Update config with Docker paths
            docker_config = config_data.copy()
            docker_config['input_file'] = f"/input/{input_file.name}"
            docker_config['output_file'] = f"/output/{output_file.name}"
            
            # Write config file
            import json
            with open(config_file, 'w') as f:
                json.dump(docker_config, f, indent=2)
            
            # Create volume mappings
            volumes = {
                str(input_file.parent): {'bind': '/input', 'mode': 'ro'},
                str(output_file.parent): {'bind': '/output', 'mode': 'rw'},
                str(config_file.parent): {'bind': '/config', 'mode': 'ro'}
            }
            
            return volumes, config_file
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """Get comprehensive information about a file."""
        if not file_path.exists():
            return {'exists': False}
        
        stat = file_path.stat()
        
        return {
            'exists': True,
            'size': stat.st_size,
            'size_formatted': self._format_size(stat.st_size),
            'modified': stat.st_mtime,
            'permissions': oct(stat.st_mode)[-3:],
            'is_file': file_path.is_file(),
            'is_dir': file_path.is_dir(),
            'extension': file_path.suffix,
            'hash_sha256': self.calculate_file_hash(file_path) if file_path.is_file() else None
        }
    
    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def __del__(self):
        """Cleanup temporary files when handler is destroyed."""
        self.cleanup_all_temporary_files()