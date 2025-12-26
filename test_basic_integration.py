#!/usr/bin/env python3
"""
Basic integration test for IREE Docker compilation service.
Tests components that can work without Docker running.
"""

import json
import tempfile
from pathlib import Path

def test_python_modules():
    """Test that all Python modules can be imported."""
    print("=== Testing Python Module Imports ===")
    
    try:
        from iree_docker_integration.config_validator import ConfigValidator
        print("✓ ConfigValidator imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ConfigValidator: {e}")
        return False
    
    try:
        from iree_docker_integration.docker_manager import DockerManager
        print("✓ DockerManager imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import DockerManager: {e}")
        return False
    
    try:
        from iree_docker_integration.file_handler import SecureFileHandler
        print("✓ SecureFileHandler imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import SecureFileHandler: {e}")
        return False
    
    try:
        from iree_docker_integration.cli import main
        print("✓ CLI module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import CLI: {e}")
        return False
    
    return True


def test_config_validation():
    """Test configuration validation without Docker."""
    print("\n=== Testing Configuration Validation ===")
    
    try:
        from iree_docker_integration.config_validator import ConfigValidator
        
        # Check if schema file exists, if not skip schema-based validation
        try:
            validator = ConfigValidator()
        except FileNotFoundError:
            print("⚠ Schema file not found, testing basic validation only")
            # Create a minimal validator for testing
            validator = ConfigValidator.__new__(ConfigValidator)
            validator.schema = {}
            validator.validator = None
        
        # Test valid CUDA configuration
        cuda_config = {
            "input_file": "/input/model.mlir",
            "target": "cuda",
            "optimization_level": "O3",
            "target_features": ["sm_80"],
            "output_format": "vmfb",
            "validation": True,
            "benchmark": False
        }
        
        # Test basic validation using Pydantic directly
        try:
            from iree_docker_integration.config_validator import IreeCompilationConfig
            validated_config = IreeCompilationConfig(**cuda_config)
            print("✓ CUDA configuration validation passed")
        except Exception as e:
            print(f"✗ CUDA configuration validation failed: {e}")
            return False
        
        # Test invalid configuration
        invalid_config = {
            "input_file": "/nonexistent/path.mlir",
            "target": "invalid_target",
            "output_format": "invalid_format"
        }
        
        try:
            invalid_validated = IreeCompilationConfig(**invalid_config)
            print("✗ Invalid configuration was accepted")
            return False
        except Exception:
            print("✓ Invalid configuration properly rejected")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration validation test failed: {e}")
        return False


def test_file_handling():
    """Test file handling capabilities."""
    print("\n=== Testing File Handling ===")
    
    try:
        from iree_docker_integration.file_handler import SecureFileHandler
        file_handler = SecureFileHandler()
        
        # Create a mock MLIR file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mlir', delete=False) as f:
            f.write("""
module {
  func.func @main() -> tensor<4xf32> {
    %0 = stablehlo.constant dense<[1.0, 2.0, 3.0, 4.0]> : tensor<4xf32>
    return %0 : tensor<4xf32>
  }
}
""")
            mock_mlir_file = Path(f.name)
        
        try:
            # Test input file validation
            is_valid, error_msg = file_handler.validate_input_file(mock_mlir_file)
            if is_valid:
                print("✓ Input file validation passed")
            else:
                print(f"✗ Input file validation failed: {error_msg}")
                return False
            
            # Test file info retrieval
            file_info = file_handler.get_file_info(mock_mlir_file)
            if file_info and 'size' in file_info:
                print(f"✓ File info retrieved: {file_info.get('size_formatted', 'unknown size')}")
            else:
                print("✗ Failed to retrieve file info")
                return False
            
            return True
            
        finally:
            # Cleanup
            mock_mlir_file.unlink()
            file_handler.cleanup_all_temporary_files()
            
    except Exception as e:
        print(f"✗ File handling test failed: {e}")
        return False


def test_docker_manager_basic():
    """Test Docker manager basic functionality (without requiring Docker to be running)."""
    print("\n=== Testing Docker Manager (Basic) ===")
    
    try:
        from iree_docker_integration.docker_manager import DockerManager
        docker_manager = DockerManager(verbose=False)
        
        # Test image name generation
        cuda_image = docker_manager.get_image_name('cuda')
        if cuda_image == 'iree-compiler:cuda-latest':
            print("✓ CUDA image name generation correct")
        else:
            print(f"✗ CUDA image name incorrect: {cuda_image}")
            return False
        
        # Test Docker availability check (this should work even if Docker is not running)
        docker_available = docker_manager.check_docker_available()
        print(f"✓ Docker availability check completed: {docker_available}")
        
        return True
        
    except Exception as e:
        print(f"✗ Docker manager basic test failed: {e}")
        return False


def main():
    """Run all basic integration tests."""
    print("=== IREE Docker Integration - Basic Tests ===\n")
    
    tests = [
        test_python_modules,
        test_config_validation,
        test_file_handling,
        test_docker_manager_basic,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"Test {test.__name__} failed")
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("✓ All basic integration tests passed!")
        return True
    else:
        print("✗ Some tests failed")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)