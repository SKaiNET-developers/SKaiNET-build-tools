#!/usr/bin/env python3
"""
IREE Docker Integration CLI

Standalone command-line interface for Docker-based IREE compilation.
Integrates local configuration validation with Docker container management.

Requirements: 5.1, 5.2
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

import click
import docker
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config_validator import ConfigValidator
from .docker_manager import DockerManager
from .utils import setup_logging, validate_file_paths


console = Console()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool) -> None:
    """IREE Docker Integration CLI - Compile StableHLO MLIR using Docker containers."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    
    # Set up logging
    setup_logging(verbose, debug)


@cli.command()
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True),
              help='Input StableHLO MLIR file')
@click.option('--output', '-o', 'output_file', required=True, type=click.Path(),
              help='Output compiled module file')
@click.option('--target', '-t', type=click.Choice(['cuda', 'cpu', 'vulkan', 'metal']),
              default='cuda', help='Compilation target backend')
@click.option('--optimization', type=click.Choice(['O0', 'O1', 'O2', 'O3']),
              default='O3', help='Optimization level')
@click.option('--target-features', multiple=True,
              help='Target-specific feature flags (can be specified multiple times)')
@click.option('--format', 'output_format', type=click.Choice(['vmfb', 'so', 'dylib']),
              default='vmfb', help='Output module format')
@click.option('--validate/--no-validate', default=True,
              help='Enable/disable output validation')
@click.option('--benchmark/--no-benchmark', default=False,
              help='Enable/disable performance benchmarking')
@click.option('--config', type=click.Path(exists=True),
              help='JSON configuration file (overrides command-line options)')
@click.option('--dry-run', is_flag=True,
              help='Show what would be done without executing')
@click.pass_context
def compile(ctx: click.Context, input_file: str, output_file: str, target: str,
           optimization: str, target_features: List[str], output_format: str,
           validate: bool, benchmark: bool, config: Optional[str], dry_run: bool) -> None:
    """Compile StableHLO MLIR to executable bytecode using Docker containers."""
    
    verbose = ctx.obj['verbose']
    debug = ctx.obj['debug']
    
    try:
        # Load configuration
        if config:
            with open(config, 'r') as f:
                config_data = json.load(f)
        else:
            # Build configuration from command-line arguments
            config_data = {
                "input_file": f"/input/{Path(input_file).name}",
                "output_file": f"/output/{Path(output_file).name}",
                "target": target,
                "optimization_level": optimization,
                "target_features": list(target_features),
                "output_format": output_format,
                "validation": validate,
                "benchmark": benchmark,
                "verbose": verbose
            }
        
        # Validate configuration locally
        console.print("[bold blue]Validating configuration...[/bold blue]")
        validator = ConfigValidator()
        is_valid, errors = validator.validate_config(config_data)
        
        if not is_valid:
            console.print("[bold red]Configuration validation failed:[/bold red]")
            for error in errors:
                console.print(f"  • {error}")
            sys.exit(1)
        
        # Normalize configuration
        normalized_config = validator.normalize_config(config_data)
        
        if verbose:
            console.print("[dim]Normalized configuration:[/dim]")
            console.print(json.dumps(normalized_config, indent=2))
        
        # Validate file paths
        input_path = Path(input_file)
        output_path = Path(output_file)
        
        if not validate_file_paths(input_path, output_path):
            sys.exit(1)
        
        if dry_run:
            console.print("[bold yellow]Dry run mode - showing what would be executed:[/bold yellow]")
            _show_compilation_plan(normalized_config, input_path, output_path)
            return
        
        # Execute compilation
        docker_manager = DockerManager(verbose=verbose, debug=debug)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            
            # Check Docker availability
            task = progress.add_task("Checking Docker availability...", total=None)
            if not docker_manager.check_docker_available():
                console.print("[bold red]Docker is not available. Please install Docker and try again.[/bold red]")
                sys.exit(1)
            progress.update(task, description="✓ Docker available")
            
            # Prepare Docker image
            progress.update(task, description="Preparing Docker image...")
            image_name = docker_manager.get_image_name(target)
            if not docker_manager.ensure_image_available(image_name):
                console.print(f"[bold red]Failed to prepare Docker image: {image_name}[/bold red]")
                sys.exit(1)
            progress.update(task, description=f"✓ Docker image ready: {image_name}")
            
            # Execute compilation
            progress.update(task, description="Executing compilation...")
            result = docker_manager.run_compilation(
                normalized_config, input_path, output_path
            )
            
            if result['success']:
                progress.update(task, description="✓ Compilation completed successfully")
            else:
                progress.update(task, description="✗ Compilation failed")
        
        # Display results
        _display_compilation_results(result, verbose)
        
        if not result['success']:
            sys.exit(1)
    
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Compilation interrupted by user[/bold yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.option('--target', '-t', type=click.Choice(['cuda', 'cpu', 'vulkan', 'metal']),
              default='cuda', help='Target to generate example for')
@click.option('--output', '-o', type=click.Path(), help='Output file for generated configuration')
def generate_config(target: str, output: Optional[str]) -> None:
    """Generate example configuration file for the specified target."""
    
    try:
        validator = ConfigValidator()
        example_config = validator.generate_example_config(target)
        
        if output:
            with open(output, 'w') as f:
                json.dump(example_config, f, indent=2)
            console.print(f"[bold green]Example {target} configuration written to {output}[/bold green]")
        else:
            console.print(f"[bold blue]Example {target} configuration:[/bold blue]")
            console.print(json.dumps(example_config, indent=2))
    
    except Exception as e:
        console.print(f"[bold red]Error generating configuration: {e}[/bold red]")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True,
              help='Configuration file to validate')
@click.option('--normalize', is_flag=True, help='Normalize and output the configuration')
@click.option('--output', '-o', type=click.Path(), help='Output file for normalized configuration')
def validate_config(config: str, normalize: bool, output: Optional[str]) -> None:
    """Validate IREE compilation configuration file."""
    
    try:
        with open(config, 'r') as f:
            config_data = json.load(f)
        
        validator = ConfigValidator()
        is_valid, errors = validator.validate_config(config_data)
        
        if is_valid:
            console.print("[bold green]✓ Configuration is valid[/bold green]")
            
            if normalize:
                normalized_config = validator.normalize_config(config_data)
                
                if output:
                    with open(output, 'w') as f:
                        json.dump(normalized_config, f, indent=2)
                    console.print(f"[bold blue]Normalized configuration written to {output}[/bold blue]")
                else:
                    console.print("[bold blue]Normalized configuration:[/bold blue]")
                    console.print(json.dumps(normalized_config, indent=2))
        else:
            console.print("[bold red]✗ Configuration validation failed:[/bold red]")
            for error in errors:
                console.print(f"  • {error}")
            sys.exit(1)
    
    except Exception as e:
        console.print(f"[bold red]Error validating configuration: {e}[/bold red]")
        sys.exit(1)


@cli.command()
@click.option('--target', '-t', type=click.Choice(['cuda', 'cpu', 'vulkan', 'metal']),
              help='Show status for specific target')
def status(target: Optional[str]) -> None:
    """Show Docker images and system status."""
    
    try:
        docker_manager = DockerManager()
        
        if not docker_manager.check_docker_available():
            console.print("[bold red]Docker is not available[/bold red]")
            sys.exit(1)
        
        console.print("[bold green]✓ Docker is available[/bold green]")
        
        # Show Docker images status
        table = Table(title="IREE Docker Images Status")
        table.add_column("Target", style="cyan")
        table.add_column("Image Name", style="blue")
        table.add_column("Status", style="green")
        table.add_column("Size", style="yellow")
        
        targets = [target] if target else ['cuda', 'cpu', 'vulkan', 'metal']
        
        for tgt in targets:
            image_name = docker_manager.get_image_name(tgt)
            status_info = docker_manager.get_image_status(image_name)
            
            table.add_row(
                tgt.upper(),
                image_name,
                "✓ Available" if status_info['available'] else "✗ Not available",
                status_info.get('size', 'Unknown')
            )
        
        console.print(table)
        
        # Show system information
        console.print("\n[bold blue]System Information:[/bold blue]")
        system_info = docker_manager.get_system_info()
        for key, value in system_info.items():
            console.print(f"  {key}: {value}")
    
    except Exception as e:
        console.print(f"[bold red]Error checking status: {e}[/bold red]")
        sys.exit(1)


def _show_compilation_plan(config: Dict[str, Any], input_path: Path, output_path: Path) -> None:
    """Show what would be executed in dry-run mode."""
    
    table = Table(title="Compilation Plan")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Input File", str(input_path))
    table.add_row("Output File", str(output_path))
    table.add_row("Target", config['target'])
    table.add_row("Optimization", config['optimization_level'])
    table.add_row("Output Format", config['output_format'])
    table.add_row("Validation", "Yes" if config['validation'] else "No")
    table.add_row("Benchmark", "Yes" if config['benchmark'] else "No")
    
    if config.get('target_features'):
        table.add_row("Target Features", ", ".join(config['target_features']))
    
    console.print(table)
    
    console.print(f"\n[bold blue]Docker Command:[/bold blue]")
    docker_manager = DockerManager()
    image_name = docker_manager.get_image_name(config['target'])
    console.print(f"docker run --rm -v {input_path.parent}:/input -v {output_path.parent}:/output {image_name}")


def _display_compilation_results(result: Dict[str, Any], verbose: bool) -> None:
    """Display compilation results in a formatted table."""
    
    if result['success']:
        console.print("[bold green]✓ Compilation completed successfully![/bold green]")
        
        table = Table(title="Compilation Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        if 'compilation_time' in result:
            table.add_row("Compilation Time", result['compilation_time'])
        
        if 'output_size' in result:
            table.add_row("Output Size", result['output_size'])
        
        if 'validation_result' in result:
            table.add_row("Validation", result['validation_result'])
        
        if result.get('benchmark_results'):
            benchmark = result['benchmark_results']
            if 'latency_ms' in benchmark:
                table.add_row("Latency", f"{benchmark['latency_ms']} ms")
            if 'throughput_ops_per_sec' in benchmark:
                table.add_row("Throughput", f"{benchmark['throughput_ops_per_sec']} ops/sec")
        
        console.print(table)
        
        if verbose and result.get('logs'):
            console.print("\n[bold blue]Compilation Logs:[/bold blue]")
            console.print(result['logs'])
    
    else:
        console.print("[bold red]✗ Compilation failed![/bold red]")
        
        if result.get('error'):
            console.print(f"[red]Error: {result['error']}[/red]")
        
        if result.get('logs'):
            console.print("\n[bold blue]Error Logs:[/bold blue]")
            console.print(result['logs'])


def main() -> None:
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupted by user[/bold yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error: {e}[/bold red]")
        sys.exit(1)


if __name__ == '__main__':
    main()