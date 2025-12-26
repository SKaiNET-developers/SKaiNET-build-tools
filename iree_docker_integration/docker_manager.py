"""
Docker Manager Module

Manages Docker container execution for IREE compilation.
Handles image management, container orchestration, and result processing.
Integrates with SecureFileHandler for secure file operations.

Requirements: 5.1, 5.2, 10.1, 10.3
"""

import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import docker
    from docker.errors import DockerException, ImageNotFound, ContainerError
except ImportError:
    raise ImportError("docker package is required. Install with: pip install docker")

from .file_handler import SecureFileHandler


class DockerManager:
    """Manages Docker operations for IREE compilation with secure file handling."""
    
    def __init__(self, verbose: bool = False, debug: bool = False, 
                 input_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        """Initialize Docker manager with file handler."""
        self.verbose = verbose
        self.debug = debug
        self.client = None
        
        # Initialize secure file handler
        self.file_handler = SecureFileHandler(
            base_input_dir=input_dir or Path("input"),
            base_output_dir=output_dir or Path("output")
        )
        
        # Image name mapping
        self.image_names = {
            'cuda': 'iree-compiler:cuda-latest',
            'cpu': 'iree-compiler:cpu-latest',
            'vulkan': 'iree-compiler:vulkan-latest',
            'metal': 'iree-compiler:metal-latest'
        }
    
    def check_docker_available(self) -> bool:
        """Check if Docker is available and accessible."""
        try:
            self.client = docker.from_env()
            self.client.ping()
            return True
        except DockerException:
            return False
    
    def get_image_name(self, target: str) -> str:
        """Get Docker image name for the specified target."""
        return self.image_names.get(target, f'iree-compiler:{target}-latest')
    
    def ensure_image_available(self, image_name: str) -> bool:
        """Ensure Docker image is available, build if necessary."""
        try:
            if not self.client:
                self.client = docker.from_env()
            
            # Check if image exists locally
            try:
                self.client.images.get(image_name)
                if self.verbose:
                    print(f"Docker image {image_name} found locally")
                return True
            except ImageNotFound:
                if self.verbose:
                    print(f"Docker image {image_name} not found locally")
            
            # Try to pull image from registry
            if self.verbose:
                print(f"Attempting to pull {image_name}...")
            
            try:
                self.client.images.pull(image_name)
                if self.verbose:
                    print(f"Successfully pulled {image_name}")
                return True
            except DockerException as e:
                if self.verbose:
                    print(f"Failed to pull {image_name}: {e}")
            
            # Try to build image locally
            return self._build_image_locally(image_name)
            
        except DockerException as e:
            if self.debug:
                print(f"Docker error: {e}")
            return False
    
    def _build_image_locally(self, image_name: str) -> bool:
        """Build Docker image locally from Dockerfile."""
        try:
            # Determine target from image name
            target = None
            for tgt, img_name in self.image_names.items():
                if img_name == image_name:
                    target = tgt
                    break
            
            if not target:
                if self.debug:
                    print(f"Unknown target for image {image_name}")
                return False
            
            # Build path
            dockerfile_path = Path(f"docker/{target}")
            if not dockerfile_path.exists():
                if self.debug:
                    print(f"Dockerfile not found at {dockerfile_path}")
                return False
            
            if self.verbose:
                print(f"Building {image_name} from {dockerfile_path}...")
            
            # Build image
            image, build_logs = self.client.images.build(
                path=str(dockerfile_path.parent.parent),  # Project root
                dockerfile=str(dockerfile_path / "Dockerfile"),
                tag=image_name,
                rm=True,
                forcerm=True
            )
            
            if self.verbose:
                print(f"Successfully built {image_name}")
                if self.debug:
                    for log in build_logs:
                        if 'stream' in log:
                            print(log['stream'].strip())
            
            return True
            
        except DockerException as e:
            if self.debug:
                print(f"Failed to build {image_name}: {e}")
            return False
    
    def get_image_status(self, image_name: str) -> Dict[str, Any]:
        """Get status information for a Docker image."""
        try:
            if not self.client:
                self.client = docker.from_env()
            
            try:
                image = self.client.images.get(image_name)
                return {
                    'available': True,
                    'size': self._format_size(image.attrs.get('Size', 0)),
                    'created': image.attrs.get('Created', 'Unknown'),
                    'id': image.short_id
                }
            except ImageNotFound:
                return {
                    'available': False,
                    'size': 'N/A',
                    'created': 'N/A',
                    'id': 'N/A'
                }
        except DockerException:
            return {
                'available': False,
                'size': 'Error',
                'created': 'Error',
                'id': 'Error'
            }
    
    def get_system_info(self) -> Dict[str, str]:
        """Get Docker system information."""
        try:
            if not self.client:
                self.client = docker.from_env()
            
            info = self.client.info()
            return {
                'Docker Version': info.get('ServerVersion', 'Unknown'),
                'Total Memory': self._format_size(info.get('MemTotal', 0)),
                'CPUs': str(info.get('NCPU', 'Unknown')),
                'Operating System': info.get('OperatingSystem', 'Unknown'),
                'Architecture': info.get('Architecture', 'Unknown')
            }
        except DockerException:
            return {'Error': 'Unable to get Docker system information'}
    
    def run_compilation(self, config: Dict[str, Any], source_input_path: Path, 
                       target_output_path: Optional[Path] = None) -> Dict[str, Any]:
        """
        Run IREE compilation in Docker container with secure file handling.
        
        Args:
            config: Compilation configuration
            source_input_path: Path to source MLIR file
            target_output_path: Optional target output path
            
        Returns:
            Compilation result dictionary
        """
        try:
            if not self.client:
                self.client = docker.from_env()
            
            # Prepare input file securely
            try:
                prepared_input = self.file_handler.prepare_input_file(source_input_path)
                if self.verbose:
                    print(f"Prepared input file: {prepared_input}")
            except ValueError as e:
                return {
                    'success': False,
                    'error': f'Input file preparation failed: {e}',
                    'logs': str(e)
                }
            
            # Prepare output directory and file path
            output_filename = None
            if target_output_path:
                output_filename = target_output_path.name
            elif 'output_file' in config:
                output_filename = Path(config['output_file']).name
            
            prepared_output = self.file_handler.prepare_output_directory(output_filename)
            if self.verbose:
                print(f"Prepared output path: {prepared_output}")
            
            # Create volume mappings and config file
            try:
                with self.file_handler.temporary_directory("docker_config_") as temp_dir:
                    # Create config file in temporary directory
                    config_file = temp_dir / "compile_config.json"
                    
                    # Update config with Docker paths
                    docker_config = config.copy()
                    docker_config['input_file'] = f"/input/{prepared_input.name}"
                    docker_config['output_file'] = f"/output/{prepared_output.name}"
                    
                    with open(config_file, 'w') as f:
                        json.dump(docker_config, f, indent=2)
                    
                    # Create secure volume mappings
                    volumes = {
                        str(prepared_input.parent): {'bind': '/input', 'mode': 'ro'},
                        str(prepared_output.parent): {'bind': '/output', 'mode': 'rw'},
                        str(config_file.parent): {'bind': '/config', 'mode': 'ro'}
                    }
                    
                    # Prepare environment variables
                    environment = {
                        'CONFIG_FILE': f'/config/{config_file.name}',
                        'VERBOSE': '1' if self.verbose else '0',
                        'DEBUG': '1' if self.debug else '0'
                    }
                    
                    # Get and ensure image is available
                    image_name = self.get_image_name(config['target'])
                    if not self.ensure_image_available(image_name):
                        return {
                            'success': False,
                            'error': f'Docker image not available: {image_name}',
                            'logs': f'Failed to pull or build image: {image_name}'
                        }
                    
                    if self.verbose:
                        print(f"Running compilation with image: {image_name}")
                        print(f"Input file: {prepared_input}")
                        print(f"Output file: {prepared_output}")
                    
                    # Run container with security constraints
                    start_time = time.time()
                    
                    container = self.client.containers.run(
                        image_name,
                        volumes=volumes,
                        environment=environment,
                        remove=True,
                        detach=False,
                        stdout=True,
                        stderr=True,
                        # Security constraints
                        user='1000:1000',  # Run as non-root user
                        read_only=True,    # Read-only root filesystem
                        tmpfs={'/tmp': 'rw,noexec,nosuid,size=100m'},  # Temporary filesystem
                        mem_limit='2g',    # Memory limit
                        cpu_quota=100000,  # CPU limit (1 CPU)
                        network_mode='none',  # No network access
                        cap_drop=['ALL'],  # Drop all capabilities
                        security_opt=['no-new-privileges']  # Prevent privilege escalation
                    )
                    
                    compilation_time = time.time() - start_time
                    
                    # Parse container output
                    output_lines = container.decode('utf-8').split('\n')
                    
                    # Verify output file was created and is valid
                    output_valid, output_info = self.file_handler.verify_output_file(
                        prepared_output, 
                        config.get('output_format', 'vmfb')
                    )
                    
                    # Build result
                    result = {
                        'success': output_valid,
                        'compilation_time': f"{compilation_time:.2f}s",
                        'logs': '\n'.join(output_lines),
                        'input_file': str(prepared_input),
                        'output_file': str(prepared_output) if output_valid else None,
                        'output_info': output_info
                    }
                    
                    if output_valid:
                        file_info = self.file_handler.get_file_info(prepared_output)
                        result['output_size'] = file_info['size_formatted']
                        result['output_hash'] = file_info['hash_sha256']
                    else:
                        result['error'] = f'Output validation failed: {output_info}'
                    
                    # Parse additional results from container output
                    for line in output_lines:
                        if line.startswith('VALIDATION_RESULT:'):
                            result['validation_result'] = line.split(':', 1)[1].strip()
                        elif line.startswith('BENCHMARK_LATENCY:'):
                            result['benchmark_results'] = result.get('benchmark_results', {})
                            result['benchmark_results']['latency_ms'] = float(line.split(':', 1)[1].strip())
                        elif line.startswith('BENCHMARK_THROUGHPUT:'):
                            result['benchmark_results'] = result.get('benchmark_results', {})
                            result['benchmark_results']['throughput_ops_per_sec'] = float(line.split(':', 1)[1].strip())
                        elif line.startswith('ERROR:'):
                            result['error'] = line.split(':', 1)[1].strip()
                    
                    # Copy output file to target location if specified
                    if output_valid and target_output_path and target_output_path != prepared_output:
                        try:
                            target_output_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(prepared_output, target_output_path)
                            result['output_file'] = str(target_output_path)
                            if self.verbose:
                                print(f"Copied output to: {target_output_path}")
                        except Exception as e:
                            result['warning'] = f'Failed to copy output to target location: {e}'
                    
                    return result
                    
            except Exception as e:
                return {
                    'success': False,
                    'error': f'File preparation error: {e}',
                    'logs': str(e)
                }
        
        except ContainerError as e:
            return {
                'success': False,
                'error': f'Container execution failed: {e}',
                'logs': e.stderr.decode('utf-8') if e.stderr else 'No error logs available'
            }
        except DockerException as e:
            return {
                'success': False,
                'error': f'Docker error: {e}',
                'logs': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {e}',
                'logs': str(e)
            }
    
    def cleanup(self) -> None:
        """Clean up temporary files and resources."""
        self.file_handler.cleanup_all_temporary_files()
    
    def get_file_handler(self) -> SecureFileHandler:
        """Get the file handler instance for direct access."""
        return self.file_handler
    
    def __del__(self):
        """Cleanup when manager is destroyed."""
        try:
            self.cleanup()
        except:
            pass  # Ignore cleanup errors during destruction