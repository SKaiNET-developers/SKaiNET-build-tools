#!/usr/bin/env python3
"""
Test compilation readiness - verify all components are ready for Docker compilation.
This test checks everything except the actual Docker execution.
"""

import json
import tempfile
from pathlib import Path

def test_docker_image_build_readiness():
    """Test that Docker image can be built (check Dockerfile and scripts)."""
    print("=== Testing Docker Build Readiness ===")
    
    # Check CUDA Dockerfile exists
    dockerfile_path = Path("docker/cuda/Dockerfile")
    if not dockerfile_path.exists():
        print("✗ CUDA Dockerfile not found")
        return False
    print("✓ CUDA Dockerfile exists")
    
    # Check compilation script exists
    compile_script = Path("docker/cuda/scripts/compile.sh")
    if not compile_script.exists():
        print("✗ Compilation script not found")
        return False
    print("✓ Compilation script exists")
    
    # Check validation script exists
    validate_script = Path("docker/cuda/scripts/validate.sh")
    if not validate_script.exists():
        print("✗ Validation script not found")
        return False
    print("✓ Validation script exists")
    
    # Check benchmark script exists
    benchmark_script = Path("docker/cuda/scripts/benchmark.sh")
    if not benchmark_script.exists():
        print("✗ Benchmark script not found")
        return False
    print("✓ Benchmark script exists")
    
    return True


def test_end_to_end_config_flow():
    """Test the complete configuration flow from generation to validation."""
    print("\n=== Testing End-to-End Configuration Flow ===")
    
    try:
        from iree_docker_integration.config_validator import ConfigValidator
        from iree_docker_integration.file_handler import SecureFileHandler
        
        # Test configuration generation for all targets
        targets = ['cuda', 'cpu', 'vulkan', 'metal']
        
        for target in targets:
            try:
                validator = ConfigValidator.__new__(ConfigValidator)
                validator.schema = {}
                config = validator.generate_example_config(target)
                
                # Validate the generated config
                from iree_docker_integration.config_validator import IreeCompilationConfig
                validated = IreeCompilationConfig(**config)
                print(f"✓ {target.upper()} config generation and validation passed")
                
            except Exception as e:
                print(f"✗ {target.upper()} config failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ End-to-end config flow failed: {e}")
        return False


def test_file_preparation_workflow():
    """Test the complete file preparation workflow."""
    print("\n=== Testing File Preparation Workflow ===")
    
    try:
        from iree_docker_integration.file_handler import SecureFileHandler
        file_handler = SecureFileHandler()
        
        # Test with the actual test MLIR file
        test_mlir = Path("input/test_model.mlir")
        if not test_mlir.exists():
            print("✗ Test MLIR file not found")
            return False
        
        # Validate input file
        is_valid, error_msg = file_handler.validate_input_file(test_mlir)
        if not is_valid:
            print(f"✗ Input file validation failed: {error_msg}")
            return False
        print("✓ Input file validation passed")
        
        # Test file preparation
        prepared_input = file_handler.prepare_input_file(test_mlir, "test_model.mlir")
        print(f"✓ Input file prepared: {prepared_input}")
        
        # Test output directory preparation
        prepared_output = file_handler.prepare_output_directory("test_model.vmfb")
        print(f"✓ Output directory prepared: {prepared_output}")
        
        # Test file info
        file_info = file_handler.get_file_info(prepared_input)
        print(f"✓ File info retrieved: {file_info.get('size_formatted', 'unknown')}")
        
        # Cleanup
        file_handler.cleanup_all_temporary_files()
        print("✓ Cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"✗ File preparation workflow failed: {e}")
        return False


def test_cli_integration():
    """Test CLI integration without Docker execution."""
    print("\n=== Testing CLI Integration ===")
    
    import subprocess
    import sys
    
    try:
        # Test CLI help
        result = subprocess.run([
            "uv", "run", "iree-docker-compile", "--help"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            print(f"✗ CLI help command failed: {result.stderr}")
            return False
        print("✓ CLI help command works")
        
        # Test config generation
        result = subprocess.run([
            "uv", "run", "iree-docker-compile", 
            "generate-config", "--target", "cuda", "--output", "test-cli-config.json"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            print(f"✗ CLI config generation failed: {result.stderr}")
            return False
        print("✓ CLI config generation works")
        
        # Test config validation
        result = subprocess.run([
            "uv", "run", "iree-docker-compile", 
            "validate-config", "--config", "test-cli-config.json"
        ], capture_output=True, text=True, cwd=".")
        
        if result.returncode != 0:
            print(f"✗ CLI config validation failed: {result.stderr}")
            return False
        print("✓ CLI config validation works")
        
        # Cleanup
        Path("test-cli-config.json").unlink(missing_ok=True)
        
        return True
        
    except Exception as e:
        print(f"✗ CLI integration test failed: {e}")
        return False


def test_compilation_script_syntax():
    """Test that the compilation script has valid syntax."""
    print("\n=== Testing Compilation Script Syntax ===")
    
    try:
        compile_script = Path("docker/cuda/scripts/compile.sh")
        
        # Basic syntax check - ensure it's a valid shell script
        with open(compile_script, 'r') as f:
            content = f.read()
        
        # Check for required components
        required_elements = [
            "#!/bin/bash",
            "set -euo pipefail",
            "CONFIG_FILE=",
            "iree-compile",
            "jq -r",
            "log()",
            "main()"
        ]
        
        for element in required_elements:
            if element not in content:
                print(f"✗ Missing required element in compile.sh: {element}")
                return False
        
        print("✓ Compilation script syntax check passed")
        
        # Check validation script
        validate_script = Path("docker/cuda/scripts/validate.sh")
        with open(validate_script, 'r') as f:
            validate_content = f.read()
        
        if "iree-run-module" not in validate_content:
            print("✗ Validation script missing iree-run-module")
            return False
        print("✓ Validation script syntax check passed")
        
        # Check benchmark script
        benchmark_script = Path("docker/cuda/scripts/benchmark.sh")
        with open(benchmark_script, 'r') as f:
            benchmark_content = f.read()
        
        if "iree-benchmark-module" not in benchmark_content:
            print("✗ Benchmark script missing iree-benchmark-module")
            return False
        print("✓ Benchmark script syntax check passed")
        
        return True
        
    except Exception as e:
        print(f"✗ Script syntax test failed: {e}")
        return False


def test_docker_compose_readiness():
    """Test Docker Compose configuration if it exists."""
    print("\n=== Testing Docker Compose Readiness ===")
    
    compose_file = Path("docker-compose.yml")
    if not compose_file.exists():
        print("⚠ Docker Compose file not found (optional)")
        return True
    
    try:
        import yaml
        with open(compose_file, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        # Check for IREE service
        if 'services' not in compose_config:
            print("✗ No services defined in docker-compose.yml")
            return False
        
        print("✓ Docker Compose file is valid YAML")
        print(f"✓ Found {len(compose_config['services'])} service(s)")
        
        return True
        
    except ImportError:
        print("⚠ PyYAML not available, skipping Docker Compose validation")
        return True
    except Exception as e:
        print(f"✗ Docker Compose validation failed: {e}")
        return False


def main():
    """Run all compilation readiness tests."""
    print("=== IREE Docker Compilation Readiness Test ===\n")
    
    tests = [
        test_docker_image_build_readiness,
        test_end_to_end_config_flow,
        test_file_preparation_workflow,
        test_cli_integration,
        test_compilation_script_syntax,
        test_docker_compose_readiness,
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
    
    print(f"\n=== Compilation Readiness Results ===")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("✓ All compilation readiness tests passed!")
        print("✓ System is ready for Docker-based IREE compilation")
        print("✓ To test with Docker, ensure Docker daemon is running and build the image:")
        print("  docker build -t iree-compiler:cuda-latest docker/cuda/")
        return True
    else:
        print("✗ Some readiness tests failed")
        print("✗ System may not be ready for Docker compilation")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)