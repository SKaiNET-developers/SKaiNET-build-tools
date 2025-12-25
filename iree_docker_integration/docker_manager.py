"""
Docker Manager Module

Manages Docker container execution for IREE compilation.
Handles image management, container orchestration, and result processing.

Requirements: 5.1, 5.2
"""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import docker
    from docker.errors import DockerException, ImageNotFound, ContainerError
except ImportError:
    raise ImportError("docker package is required. Install with: pip install docker")


class DockerManager:
    """Manages Docker operations for IREE compilation."""
    
    def __init__(self, verbose: bool = False, debug: bool = False):
        """Initialize Docker manager."""
        self.verbose = verbose
        self.debug = debug
        self.client = None
        
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
    
    def run_compilation(self, config: Dict[str, Any], input_path: Path, output_path: Path) -> Dict[str, Any]:
        """Run IREE compilation in Docker container."""
        try:
            if not self.client:
                self.client = docker.from_env()
            
            # Prepare directories
            input_dir = input_path.parent
            output_dir = output_path.parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create temporary config file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(config, f, indent=2)
                config_file = Path(f.name)
            
            try:
                # Prepare volumes
                volumes = {
                    str(input_dir): {'bind': '/input', 'mode': 'ro'},
                    str(output_dir): {'bind': '/output', 'mode': 'rw'},
                    str(config_file.parent): {'bind': '/config', 'mode': 'ro'}
                }
                
                # Prepare environment variables
                environment = {
                    'CONFIG_FILE': f'/config/{config_file.name}',
                    'VERBOSE': '1' if self.verbose else '0',
                    'DEBUG': '1' if self.debug else '0'
                }
                
                # Get image name
                image_name = self.get_image_name(config['target'])
                
                if self.verbose:
                    print(f"Running compilation with image: {image_name}")
                    print(f"Input directory: {input_dir}")
                    print(f"Output directory: {output_dir}")
                
                # Run container
                start_time = time.time()
                
                container = self.client.containers.run(
                    image_name,
                    volumes=volumes,
                    environment=environment,
                    remove=True,
                    detach=False,
                    stdout=True,
                    stderr=True
                )
                
                compilation_time = time.time() - start_time
                
                # Parse container output
                output_lines = container.decode('utf-8').split('\n')
                
                # Check if compilation was successful
                success = any('SUCCESS' in line for line in output_lines)
                
                # Extract results
                result = {
                    'success': success,
                    'compilation_time': f"{compilation_time:.2f}s",
                    'logs': '\n'.join(output_lines)
                }
                
                # Check if output file was created
                if output_path.exists():
                    result['output_size'] = self._format_size(output_path.stat().st_size)
                    result['output_file'] = str(output_path)
                else:
                    result['success'] = False
                    if 'error' not in result:
                        result['error'] = 'Output file was not created'
                
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
                
                return result
                
            finally:
                # Clean up temporary config file
                if config_file.exists():
                    config_file.unlink()
        
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