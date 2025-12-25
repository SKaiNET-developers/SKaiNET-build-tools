"""
Utility Functions

Common utility functions for the IREE Docker Integration CLI.

Requirements: 5.1, 5.2
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Set up logging configuration."""
    
    # Determine log level
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    
    # Configure logging with Rich handler
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )
    
    # Suppress noisy third-party loggers
    logging.getLogger("docker").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def validate_file_paths(input_path: Path, output_path: Path) -> bool:
    """Validate input and output file paths."""
    
    # Check input file
    if not input_path.exists():
        console.print(f"[bold red]Error: Input file does not exist: {input_path}[/bold red]")
        return False
    
    if not input_path.is_file():
        console.print(f"[bold red]Error: Input path is not a file: {input_path}[/bold red]")
        return False
    
    if not input_path.suffix.lower() == '.mlir':
        console.print(f"[bold yellow]Warning: Input file does not have .mlir extension: {input_path}[/bold yellow]")
    
    # Check output directory
    output_dir = output_path.parent
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"[dim]Created output directory: {output_dir}[/dim]")
        except OSError as e:
            console.print(f"[bold red]Error: Cannot create output directory {output_dir}: {e}[/bold red]")
            return False
    
    # Check if output file already exists
    if output_path.exists():
        console.print(f"[bold yellow]Warning: Output file already exists and will be overwritten: {output_path}[/bold yellow]")
    
    return True


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes."""
    if not file_path.exists():
        return 0.0
    return file_path.stat().st_size / (1024 * 1024)


def validate_target_features(target: str, features: list) -> bool:
    """Validate target-specific features."""
    
    if target == 'cuda':
        for feature in features:
            if not feature.startswith('sm_'):
                console.print(f"[bold red]Error: Invalid CUDA feature '{feature}'. Must start with 'sm_'[/bold red]")
                return False
            
            # Extract compute capability number
            try:
                cc = int(feature[3:])
                if cc < 30 or cc > 90:
                    console.print(f"[bold yellow]Warning: Unusual CUDA compute capability: {feature}[/bold yellow]")
            except ValueError:
                console.print(f"[bold red]Error: Invalid CUDA compute capability format: {feature}[/bold red]")
                return False
    
    elif target == 'cpu':
        valid_features = [
            'sse', 'sse2', 'sse3', 'ssse3', 'sse4.1', 'sse4.2', 
            'avx', 'avx2', 'avx512', 'neon', 'generic', 'native'
        ]
        for feature in features:
            if feature not in valid_features:
                console.print(f"[bold red]Error: Invalid CPU feature '{feature}'[/bold red]")
                console.print(f"[dim]Valid features: {', '.join(valid_features)}[/dim]")
                return False
    
    elif target == 'vulkan':
        for feature in features:
            if not feature.startswith('spirv'):
                console.print(f"[bold red]Error: Invalid Vulkan feature '{feature}'. Must start with 'spirv'[/bold red]")
                return False
    
    elif target == 'metal':
        for feature in features:
            if not feature.startswith('metal'):
                console.print(f"[bold red]Error: Invalid Metal feature '{feature}'. Must start with 'metal'[/bold red]")
                return False
    
    return True


def check_dependencies() -> bool:
    """Check if all required dependencies are available."""
    
    missing_deps = []
    
    try:
        import docker
    except ImportError:
        missing_deps.append("docker")
    
    try:
        import jsonschema
    except ImportError:
        missing_deps.append("jsonschema")
    
    try:
        import click
    except ImportError:
        missing_deps.append("click")
    
    try:
        import rich
    except ImportError:
        missing_deps.append("rich")
    
    if missing_deps:
        console.print("[bold red]Missing required dependencies:[/bold red]")
        for dep in missing_deps:
            console.print(f"  • {dep}")
        console.print("\n[bold blue]Install with:[/bold blue]")
        console.print(f"  pip install {' '.join(missing_deps)}")
        return False
    
    return True


def print_banner() -> None:
    """Print application banner."""
    console.print("""
[bold blue]╔══════════════════════════════════════════════════════════════╗[/bold blue]
[bold blue]║                    IREE Docker Integration                   ║[/bold blue]
[bold blue]║              Standalone IREE Compilation CLI                 ║[/bold blue]
[bold blue]╚══════════════════════════════════════════════════════════════╝[/bold blue]
""")


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask user for confirmation."""
    suffix = " [Y/n]" if default else " [y/N]"
    
    try:
        response = input(f"{message}{suffix}: ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes', 'true', '1']
    
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Cancelled by user[/bold yellow]")
        return False