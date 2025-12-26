#!/usr/bin/env python3
"""
Checkpoint Test - Comprehensive test suite for IREE Docker Integration.
This test verifies that basic Docker compilation is ready to work.
"""

import subprocess
import sys
from pathlib import Path

def run_test_suite(test_file: str, description: str) -> bool:
    """Run a test suite and return success status."""
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([
            "uv", "run", "python", test_file
        ], cwd=".")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Failed to run {test_file}: {e}")
        return False


def test_project_structure():
    """Test that all required project files exist."""
    print("\n=== Testing Project Structure ===")
    
    required_files = [
        "pyproject.toml",
        "docker/cuda/Dockerfile",
        "docker/cuda/scripts/compile.sh",
        "docker/cuda/scripts/validate.sh",
        "docker/cuda/scripts/benchmark.sh",
        "iree_docker_integration/__init__.py",
        "iree_docker_integration/cli.py",
        "iree_docker_integration/config_validator.py",
        "iree_docker_integration/docker_manager.py",
        "iree_docker_integration/file_handler.py",
        "input/test_model.mlir",
        "docker-compose.yml"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("✗ Missing required files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    print(f"✓ All {len(required_files)} required files exist")
    return True


def test_python_environment():
    """Test that the Python environment is properly set up."""
    print("\n=== Testing Python Environment ===")
    
    try:
        # Test uv is available
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("✗ uv is not available")
            return False
        print(f"✓ uv is available: {result.stdout.strip()}")
        
        # Test dependencies are installed
        result = subprocess.run(["uv", "run", "python", "-c", 
                               "import jsonschema, pydantic, click, docker; print('All dependencies available')"],
                               capture_output=True, text=True)
        if result.returncode != 0:
            print(f"✗ Dependencies not available: {result.stderr}")
            return False
        print("✓ All Python dependencies are available")
        
        return True
        
    except Exception as e:
        print(f"✗ Python environment test failed: {e}")
        return False


def main():
    """Run the complete checkpoint test suite."""
    print("="*80)
    print("IREE DOCKER INTEGRATION - CHECKPOINT TEST")
    print("="*80)
    print("This test verifies that basic Docker compilation is ready to work.")
    print("All components will be tested except actual Docker execution.")
    
    # Test suites to run
    test_suites = [
        ("test_basic_integration.py", "Basic Integration Tests"),
        ("test_compilation_readiness.py", "Compilation Readiness Tests")
    ]
    
    # Individual tests
    individual_tests = [
        (test_project_structure, "Project Structure"),
        (test_python_environment, "Python Environment")
    ]
    
    passed_suites = 0
    total_suites = len(test_suites)
    
    passed_individual = 0
    total_individual = len(individual_tests)
    
    # Run individual tests
    print(f"\n{'='*60}")
    print("Running Individual Tests")
    print(f"{'='*60}")
    
    for test_func, description in individual_tests:
        try:
            if test_func():
                passed_individual += 1
                print(f"✓ {description} - PASSED")
            else:
                print(f"✗ {description} - FAILED")
        except Exception as e:
            print(f"✗ {description} - CRASHED: {e}")
    
    # Run test suites
    for test_file, description in test_suites:
        if run_test_suite(test_file, description):
            passed_suites += 1
            print(f"✓ {description} - PASSED")
        else:
            print(f"✗ {description} - FAILED")
    
    # Final results
    print(f"\n{'='*80}")
    print("CHECKPOINT TEST RESULTS")
    print(f"{'='*80}")
    print(f"Individual Tests: {passed_individual}/{total_individual}")
    print(f"Test Suites:      {passed_suites}/{total_suites}")
    print(f"Overall:          {passed_individual + passed_suites}/{total_individual + total_suites}")
    
    if passed_individual == total_individual and passed_suites == total_suites:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("\n✅ CHECKPOINT COMPLETE - Basic Docker compilation is ready!")
        print("\n📋 Next Steps:")
        print("   1. Start Docker daemon if not running")
        print("   2. Build the Docker image:")
        print("      docker build -t iree-compiler:cuda-latest docker/cuda/")
        print("   3. Test actual compilation:")
        print("      uv run iree-docker-compile compile --input input/test_model.mlir --target cuda")
        print("\n🚀 The IREE Docker Integration system is ready for use!")
        return True
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\n⚠️  The system may not be ready for Docker compilation.")
        print("   Please review the failed tests above and fix any issues.")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)