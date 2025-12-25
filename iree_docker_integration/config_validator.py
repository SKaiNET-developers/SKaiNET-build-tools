"""
Configuration Validator Module

Validates and normalizes IREE compilation configurations using JSON schema.
This module is imported from the existing scripts/validate-config.py implementation.

Requirements: 3.3, 8.2, 8.3, 8.4, 8.5
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
except ImportError:
    raise ImportError("jsonschema package is required. Install with: pip install jsonschema")


class ConfigValidator:
    """Validates and normalizes IREE compilation configurations."""
    
    def __init__(self, schema_path: Optional[str] = None):
        """Initialize validator with schema."""
        if schema_path is None:
            # Default schema path relative to project root
            project_root = Path(__file__).parent.parent
            schema_path = project_root / "config" / "schema" / "compile-config-schema.json"
        
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()
        self.validator = Draft7Validator(self.schema)
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema from file."""
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file: {e}")
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate configuration against schema.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            validate(instance=config, schema=self.schema)
            
            # Additional custom validations
            custom_errors = self._custom_validations(config)
            errors.extend(custom_errors)
            
            return len(errors) == 0, errors
            
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            if e.path:
                errors.append(f"  Path: {' -> '.join(str(p) for p in e.path)}")
            return False, errors
    
    def _custom_validations(self, config: Dict[str, Any]) -> List[str]:
        """Perform custom validation logic beyond JSON schema."""
        errors = []
        
        # Validate target-specific configurations
        target = config.get('target', 'cuda')
        target_specific = config.get('target_specific', {})
        
        if target in target_specific:
            target_config = target_specific[target]
            
            # CUDA-specific validations
            if target == 'cuda':
                errors.extend(self._validate_cuda_config(config, target_config))
            
            # CPU-specific validations
            elif target == 'cpu':
                errors.extend(self._validate_cpu_config(config, target_config))
            
            # Vulkan-specific validations
            elif target == 'vulkan':
                errors.extend(self._validate_vulkan_config(config, target_config))
            
            # Metal-specific validations
            elif target == 'metal':
                errors.extend(self._validate_metal_config(config, target_config))
        
        # Validate output format consistency
        output_format = config.get('output_format', 'vmfb')
        output_file = config.get('output_file', '/output/model.vmfb')
        
        if output_format == 'vmfb' and not output_file.endswith('.vmfb'):
            errors.append("Output file extension must match output format (vmfb)")
        elif output_format == 'so' and not output_file.endswith('.so'):
            errors.append("Output file extension must match output format (so)")
        elif output_format == 'dylib' and not output_file.endswith('.dylib'):
            errors.append("Output file extension must match output format (dylib)")
        
        # Validate target features consistency
        target_features = config.get('target_features', [])
        if target == 'cuda':
            for feature in target_features:
                if not feature.startswith('sm_'):
                    errors.append(f"CUDA target feature must start with 'sm_': {feature}")
        
        return errors
    
    def _validate_cuda_config(self, config: Dict[str, Any], cuda_config: Dict[str, Any]) -> List[str]:
        """Validate CUDA-specific configuration."""
        errors = []
        
        # Check compute capability consistency
        target_features = config.get('target_features', [])
        compute_caps = cuda_config.get('compute_capability', [])
        
        if compute_caps and target_features:
            # Ensure target_features and compute_capability are consistent
            for cap in compute_caps:
                if cap not in target_features:
                    errors.append(f"Compute capability {cap} not found in target_features")
        
        # Validate threads per block
        max_threads = cuda_config.get('max_threads_per_block', 256)
        if max_threads % 32 != 0:
            errors.append("max_threads_per_block must be a multiple of 32 (warp size)")
        
        return errors
    
    def _validate_cpu_config(self, config: Dict[str, Any], cpu_config: Dict[str, Any]) -> List[str]:
        """Validate CPU-specific configuration."""
        errors = []
        
        # Check vector extensions compatibility
        vector_exts = cpu_config.get('vector_extensions', [])
        target_cpu = cpu_config.get('target_cpu', 'generic')
        
        if target_cpu == 'arm64':
            x86_exts = ['sse', 'sse2', 'sse3', 'ssse3', 'sse4.1', 'sse4.2', 'avx', 'avx2', 'avx512']
            for ext in vector_exts:
                if ext in x86_exts:
                    errors.append(f"x86 vector extension {ext} not compatible with ARM64 target")
        
        return errors
    
    def _validate_vulkan_config(self, config: Dict[str, Any], vulkan_config: Dict[str, Any]) -> List[str]:
        """Validate Vulkan-specific configuration."""
        errors = []
        
        # Check SPIR-V and Vulkan version compatibility
        spirv_version = vulkan_config.get('spirv_version', '1.3')
        vulkan_version = vulkan_config.get('vulkan_version', '1.1')
        
        # SPIR-V 1.4+ requires Vulkan 1.1+
        if spirv_version in ['1.4', '1.5', '1.6'] and vulkan_version == '1.0':
            errors.append(f"SPIR-V {spirv_version} requires Vulkan 1.1 or higher")
        
        return errors
    
    def _validate_metal_config(self, config: Dict[str, Any], metal_config: Dict[str, Any]) -> List[str]:
        """Validate Metal-specific configuration."""
        errors = []
        
        # Check deployment target compatibility
        metal_version = metal_config.get('metal_version', '2.4')
        ios_target = metal_config.get('ios_deployment_target')
        macos_target = metal_config.get('macos_deployment_target')
        
        # Metal 3.0 requires iOS 15.0+ or macOS 12.0+
        if metal_version == '3.0':
            if ios_target and float(ios_target) < 15.0:
                errors.append("Metal 3.0 requires iOS 15.0 or higher")
            if macos_target and float(macos_target) < 12.0:
                errors.append("Metal 3.0 requires macOS 12.0 or higher")
        
        return errors
    
    def normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize configuration by applying defaults and cleaning up values.
        
        Args:
            config: Input configuration dictionary
            
        Returns:
            Normalized configuration dictionary
        """
        normalized = config.copy()
        
        # Apply schema defaults
        self._apply_defaults(normalized, self.schema)
        
        # Normalize target features
        if 'target_features' in normalized:
            normalized['target_features'] = list(set(normalized['target_features']))  # Remove duplicates
        
        # Ensure output directory structure
        output_file = normalized.get('output_file', '/output/model.vmfb')
        if not output_file.startswith('/output/'):
            normalized['output_file'] = f"/output/{os.path.basename(output_file)}"
        
        # Normalize input file path
        input_file = normalized.get('input_file', '/input/model.mlir')
        if not input_file.startswith('/input/'):
            normalized['input_file'] = f"/input/{os.path.basename(input_file)}"
        
        return normalized
    
    def _apply_defaults(self, config: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Recursively apply default values from schema."""
        if 'properties' not in schema:
            return
        
        for prop, prop_schema in schema['properties'].items():
            if 'default' in prop_schema and prop not in config:
                config[prop] = prop_schema['default']
            elif prop in config and 'type' in prop_schema and prop_schema['type'] == 'object':
                self._apply_defaults(config[prop], prop_schema)
    
    def generate_example_config(self, target: str = 'cuda') -> Dict[str, Any]:
        """Generate an example configuration for the specified target."""
        base_config = {
            "input_file": "/input/model.mlir",
            "output_file": "/output/model.vmfb",
            "target": target,
            "optimization_level": "O3",
            "output_format": "vmfb",
            "validation": True,
            "benchmark": False,
            "verbose": False,
            "metadata": {
                "description": f"Example {target.upper()} compilation configuration",
                "version": "1.0"
            }
        }
        
        # Add target-specific configurations
        if target == 'cuda':
            base_config.update({
                "target_features": ["sm_80", "sm_86"],
                "target_specific": {
                    "cuda": {
                        "compute_capability": ["sm_80", "sm_86"],
                        "max_threads_per_block": 256,
                        "use_fast_math": False
                    }
                }
            })
        elif target == 'cpu':
            base_config.update({
                "target_features": ["avx2", "fma"],
                "target_specific": {
                    "cpu": {
                        "target_cpu": "generic",
                        "vector_extensions": ["avx2", "fma"],
                        "num_threads": 0
                    }
                }
            })
        elif target == 'vulkan':
            base_config.update({
                "target_features": ["spirv1.3"],
                "target_specific": {
                    "vulkan": {
                        "spirv_version": "1.3",
                        "vulkan_version": "1.1"
                    }
                }
            })
        elif target == 'metal':
            base_config.update({
                "target_features": ["metal2.4"],
                "target_specific": {
                    "metal": {
                        "metal_version": "2.4",
                        "macos_deployment_target": "11.0"
                    }
                }
            })
        
        return base_config