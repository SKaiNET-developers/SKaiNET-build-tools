"""
Configuration Validator Module

Validates and normalizes IREE compilation configurations using JSON schema and Pydantic models.
This module provides both JSON schema validation and type-safe Pydantic model validation.

Requirements: 3.3, 8.2, 8.3, 8.4, 8.5
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from enum import Enum

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
except ImportError:
    raise ImportError("jsonschema package is required. Install with: pip install jsonschema")

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    from pydantic import ValidationError as PydanticValidationError
except ImportError:
    raise ImportError("pydantic package is required. Install with: pip install pydantic")


class CompilationTarget(str, Enum):
    """Supported compilation targets."""
    CUDA = "cuda"
    CPU = "cpu"
    VULKAN = "vulkan"
    METAL = "metal"


class OptimizationLevel(str, Enum):
    """LLVM optimization levels."""
    O0 = "O0"
    O1 = "O1"
    O2 = "O2"
    O3 = "O3"


class OutputFormat(str, Enum):
    """Output module formats."""
    VMFB = "vmfb"
    SO = "so"
    DYLIB = "dylib"


class CudaConfig(BaseModel):
    """CUDA-specific configuration options."""
    compute_capability: Optional[List[str]] = Field(default_factory=list, description="CUDA compute capabilities")
    max_threads_per_block: int = Field(default=256, ge=32, le=1024, description="Maximum threads per CUDA block")
    use_fast_math: bool = Field(default=False, description="Enable fast math optimizations")
    
    @field_validator('compute_capability')
    @classmethod
    def validate_compute_capability(cls, v):
        for cap in v:
            if not cap.startswith('sm_') or not cap[3:].isdigit():
                raise ValueError(f"Invalid compute capability format: {cap}")
        return v
    
    @field_validator('max_threads_per_block')
    @classmethod
    def validate_threads_per_block(cls, v):
        if v % 32 != 0:
            raise ValueError("max_threads_per_block must be a multiple of 32 (warp size)")
        return v


class CpuConfig(BaseModel):
    """CPU-specific configuration options."""
    target_cpu: str = Field(default="generic", description="Target CPU architecture")
    vector_extensions: Optional[List[str]] = Field(default_factory=list, description="CPU vector extensions")
    num_threads: int = Field(default=0, ge=0, le=128, description="Number of CPU threads")
    
    @field_validator('vector_extensions')
    @classmethod
    def validate_vector_extensions(cls, v):
        valid_extensions = ['sse', 'sse2', 'sse3', 'ssse3', 'sse4.1', 'sse4.2', 
                          'avx', 'avx2', 'avx512', 'neon', 'fma', 'f16c', 'bmi', 'bmi2']
        for ext in v:
            if ext not in valid_extensions:
                raise ValueError(f"Invalid vector extension: {ext}")
        return v


class VulkanConfig(BaseModel):
    """Vulkan-specific configuration options."""
    spirv_version: str = Field(default="1.3", description="Target SPIR-V version")
    vulkan_version: str = Field(default="1.1", description="Target Vulkan API version")
    
    @field_validator('spirv_version')
    @classmethod
    def validate_spirv_version(cls, v):
        valid_versions = ['1.0', '1.1', '1.2', '1.3', '1.4', '1.5', '1.6']
        if v not in valid_versions:
            raise ValueError(f"Invalid SPIR-V version: {v}")
        return v
    
    @field_validator('vulkan_version')
    @classmethod
    def validate_vulkan_version(cls, v):
        valid_versions = ['1.0', '1.1', '1.2', '1.3']
        if v not in valid_versions:
            raise ValueError(f"Invalid Vulkan version: {v}")
        return v


class MetalConfig(BaseModel):
    """Metal-specific configuration options."""
    metal_version: str = Field(default="2.4", description="Target Metal shading language version")
    ios_deployment_target: Optional[str] = Field(default=None, description="iOS deployment target")
    macos_deployment_target: Optional[str] = Field(default=None, description="macOS deployment target")
    
    @field_validator('metal_version')
    @classmethod
    def validate_metal_version(cls, v):
        valid_versions = ['2.0', '2.1', '2.2', '2.3', '2.4', '3.0']
        if v not in valid_versions:
            raise ValueError(f"Invalid Metal version: {v}")
        return v


class TargetSpecificConfig(BaseModel):
    """Target-specific configuration options."""
    cuda: Optional[CudaConfig] = None
    cpu: Optional[CpuConfig] = None
    vulkan: Optional[VulkanConfig] = None
    metal: Optional[MetalConfig] = None


class CompilationOptions(BaseModel):
    """Advanced compilation options."""
    enable_assertions: bool = Field(default=False, description="Enable runtime assertions")
    strip_debug_info: bool = Field(default=True, description="Strip debug information")
    enable_profiling: bool = Field(default=False, description="Enable profiling instrumentation")
    memory_planning: str = Field(default="default", description="Memory planning strategy")
    
    @field_validator('memory_planning')
    @classmethod
    def validate_memory_planning(cls, v):
        valid_strategies = ['default', 'aggressive', 'conservative']
        if v not in valid_strategies:
            raise ValueError(f"Invalid memory planning strategy: {v}")
        return v


class ConfigMetadata(BaseModel):
    """Optional metadata for the compilation."""
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)


class IreeCompilationConfig(BaseModel):
    """Complete IREE compilation configuration model."""
    input_file: str = Field(..., description="Path to input StableHLO MLIR file")
    output_file: str = Field(default="/output/model.vmfb", description="Path to output file")
    target: CompilationTarget = Field(default=CompilationTarget.CUDA, description="Compilation target")
    optimization_level: OptimizationLevel = Field(default=OptimizationLevel.O3, description="Optimization level")
    target_features: Optional[List[str]] = Field(default_factory=list, description="Target-specific features")
    output_format: OutputFormat = Field(default=OutputFormat.VMFB, description="Output format")
    validation: bool = Field(default=True, description="Enable output validation")
    benchmark: bool = Field(default=False, description="Enable benchmarking")
    verbose: bool = Field(default=False, description="Enable verbose logging")
    compilation_options: Optional[CompilationOptions] = Field(default_factory=CompilationOptions)
    target_specific: Optional[TargetSpecificConfig] = Field(default_factory=TargetSpecificConfig)
    metadata: Optional[ConfigMetadata] = Field(default_factory=ConfigMetadata)
    
    @field_validator('input_file')
    @classmethod
    def validate_input_file(cls, v):
        if not v.startswith('/input/') or not v.endswith('.mlir'):
            raise ValueError("Input file must be in /input/ directory and have .mlir extension")
        return v
    
    @field_validator('output_file')
    @classmethod
    def validate_output_file(cls, v):
        if not v.startswith('/output/'):
            raise ValueError("Output file must be in /output/ directory")
        return v
    
    @model_validator(mode='after')
    def validate_output_format_consistency(self):
        output_format = self.output_format
        output_file = self.output_file
        
        if output_format and output_file:
            expected_ext = f".{output_format.value}"
            if not output_file.endswith(expected_ext):
                raise ValueError(f"Output file extension must match format: {expected_ext}")
        
        return self
    
    @model_validator(mode='after')
    def validate_target_features_consistency(self):
        target = self.target
        target_features = self.target_features or []
        
        if target == CompilationTarget.CUDA:
            for feature in target_features:
                if not feature.startswith('sm_'):
                    raise ValueError(f"CUDA target features must start with 'sm_': {feature}")
        
        return self


class ConfigValidator:
    """Validates and normalizes IREE compilation configurations using both JSON schema and Pydantic models."""
    
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
    
    def validate_config(self, config: Dict[str, Any], use_pydantic: bool = True) -> Tuple[bool, List[str]]:
        """
        Validate configuration against schema and/or Pydantic model.
        
        Args:
            config: Configuration dictionary to validate
            use_pydantic: Whether to use Pydantic validation (recommended)
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        if use_pydantic:
            # Use Pydantic validation (preferred)
            try:
                validated_config = IreeCompilationConfig(**config)
                
                # Additional cross-validation checks
                custom_errors = self._cross_validate_config(validated_config.dict())
                errors.extend(custom_errors)
                
                return len(errors) == 0, errors
                
            except PydanticValidationError as e:
                for error in e.errors():
                    field_path = " -> ".join(str(loc) for loc in error['loc'])
                    errors.append(f"Validation error at {field_path}: {error['msg']}")
                return False, errors
        else:
            # Fallback to JSON schema validation
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
    
    def validate_and_normalize(self, config: Dict[str, Any]) -> Tuple[bool, Union[Dict[str, Any], List[str]]]:
        """
        Validate and normalize configuration in one step.
        
        Returns:
            Tuple of (is_valid, normalized_config_or_errors)
        """
        try:
            # Use Pydantic for validation and normalization
            validated_config = IreeCompilationConfig(**config)
            normalized = validated_config.dict()
            
            # Additional cross-validation
            custom_errors = self._cross_validate_config(normalized)
            if custom_errors:
                return False, custom_errors
            
            # Apply additional normalization
            normalized = self._apply_additional_normalization(normalized)
            
            return True, normalized
            
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error['loc'])
                errors.append(f"Validation error at {field_path}: {error['msg']}")
            return False, errors
    
    def _cross_validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Perform cross-field validation that requires multiple fields."""
        errors = []
        
        target = config.get('target')
        target_specific = config.get('target_specific', {})
        
        # Validate target-specific configurations exist when needed
        if target in target_specific:
            target_config = target_specific[target]
            
            if target == 'cuda':
                errors.extend(self._validate_cuda_cross_fields(config, target_config))
            elif target == 'vulkan':
                errors.extend(self._validate_vulkan_cross_fields(config, target_config))
            elif target == 'metal':
                errors.extend(self._validate_metal_cross_fields(config, target_config))
        
        return errors
    
    def _validate_cuda_cross_fields(self, config: Dict[str, Any], cuda_config: Dict[str, Any]) -> List[str]:
        """Cross-validate CUDA configuration fields."""
        errors = []
        
        target_features = config.get('target_features', [])
        compute_caps = cuda_config.get('compute_capability', [])
        
        # Ensure consistency between target_features and compute_capability
        if compute_caps and target_features:
            for cap in compute_caps:
                if cap not in target_features:
                    errors.append(f"Compute capability {cap} not found in target_features")
        
        return errors
    
    def _validate_vulkan_cross_fields(self, config: Dict[str, Any], vulkan_config: Dict[str, Any]) -> List[str]:
        """Cross-validate Vulkan configuration fields."""
        errors = []
        
        spirv_version = vulkan_config.get('spirv_version', '1.3')
        vulkan_version = vulkan_config.get('vulkan_version', '1.1')
        
        # SPIR-V 1.4+ requires Vulkan 1.1+
        if spirv_version in ['1.4', '1.5', '1.6'] and vulkan_version == '1.0':
            errors.append(f"SPIR-V {spirv_version} requires Vulkan 1.1 or higher")
        
        return errors
    
    def _validate_metal_cross_fields(self, config: Dict[str, Any], metal_config: Dict[str, Any]) -> List[str]:
        """Cross-validate Metal configuration fields."""
        errors = []
        
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
    
    def _apply_additional_normalization(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply additional normalization beyond Pydantic defaults."""
        normalized = config.copy()
        
        # Normalize target features (remove duplicates, sort)
        if 'target_features' in normalized and normalized['target_features']:
            normalized['target_features'] = sorted(list(set(normalized['target_features'])))
        
        # Ensure proper path formatting
        if 'output_file' in normalized:
            output_file = normalized['output_file']
            if not output_file.startswith('/output/'):
                normalized['output_file'] = f"/output/{os.path.basename(output_file)}"
        
        if 'input_file' in normalized:
            input_file = normalized['input_file']
            if not input_file.startswith('/input/'):
                normalized['input_file'] = f"/input/{os.path.basename(input_file)}"
        
        return normalized
    
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
        try:
            target_enum = CompilationTarget(target)
        except ValueError:
            target_enum = CompilationTarget.CUDA
        
        # Create base configuration using Pydantic model
        if target_enum == CompilationTarget.CUDA:
            config = IreeCompilationConfig(
                input_file="/input/model.mlir",
                output_file="/output/model.vmfb",
                target=CompilationTarget.CUDA,
                target_features=["sm_80", "sm_86"],
                target_specific=TargetSpecificConfig(
                    cuda=CudaConfig(
                        compute_capability=["sm_80", "sm_86"],
                        max_threads_per_block=256,
                        use_fast_math=False
                    )
                ),
                metadata=ConfigMetadata(
                    description="Example CUDA compilation configuration",
                    version="1.0"
                )
            )
        elif target_enum == CompilationTarget.CPU:
            config = IreeCompilationConfig(
                input_file="/input/model.mlir",
                output_file="/output/model.vmfb",
                target=CompilationTarget.CPU,
                target_features=["avx2", "fma"],
                target_specific=TargetSpecificConfig(
                    cpu=CpuConfig(
                        target_cpu="generic",
                        vector_extensions=["avx2", "fma"],
                        num_threads=0
                    )
                ),
                metadata=ConfigMetadata(
                    description="Example CPU compilation configuration",
                    version="1.0"
                )
            )
        elif target_enum == CompilationTarget.VULKAN:
            config = IreeCompilationConfig(
                input_file="/input/model.mlir",
                output_file="/output/model.vmfb",
                target=CompilationTarget.VULKAN,
                target_features=["spirv1.3"],
                target_specific=TargetSpecificConfig(
                    vulkan=VulkanConfig(
                        spirv_version="1.3",
                        vulkan_version="1.1"
                    )
                ),
                metadata=ConfigMetadata(
                    description="Example Vulkan compilation configuration",
                    version="1.0"
                )
            )
        elif target_enum == CompilationTarget.METAL:
            config = IreeCompilationConfig(
                input_file="/input/model.mlir",
                output_file="/output/model.vmfb",
                target=CompilationTarget.METAL,
                target_features=["metal2.4"],
                target_specific=TargetSpecificConfig(
                    metal=MetalConfig(
                        metal_version="2.4",
                        macos_deployment_target="11.0"
                    )
                ),
                metadata=ConfigMetadata(
                    description="Example Metal compilation configuration",
                    version="1.0"
                )
            )
        
        return config.dict()
    
    def create_config_from_dict(self, config_dict: Dict[str, Any]) -> IreeCompilationConfig:
        """Create a validated Pydantic config model from dictionary."""
        return IreeCompilationConfig(**config_dict)
    
    def get_supported_targets(self) -> List[str]:
        """Get list of supported compilation targets."""
        return [target.value for target in CompilationTarget]
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats."""
        return [fmt.value for fmt in OutputFormat]
    
    def validate_target_features_for_target(self, target: str, features: List[str]) -> Tuple[bool, List[str]]:
        """Validate that target features are appropriate for the given target."""
        errors = []
        
        try:
            target_enum = CompilationTarget(target)
        except ValueError:
            errors.append(f"Unsupported target: {target}")
            return False, errors
        
        if target_enum == CompilationTarget.CUDA:
            for feature in features:
                if not feature.startswith('sm_'):
                    errors.append(f"CUDA target feature must start with 'sm_': {feature}")
                elif not feature[3:].isdigit():
                    errors.append(f"Invalid CUDA compute capability format: {feature}")
        
        elif target_enum == CompilationTarget.CPU:
            valid_cpu_features = ['sse', 'sse2', 'sse3', 'ssse3', 'sse4.1', 'sse4.2', 
                                'avx', 'avx2', 'avx512', 'neon', 'fma', 'f16c', 'bmi', 'bmi2', 'generic', 'native']
            for feature in features:
                if feature not in valid_cpu_features:
                    errors.append(f"Invalid CPU target feature: {feature}")
        
        elif target_enum == CompilationTarget.VULKAN:
            # Vulkan features are typically SPIR-V version indicators
            valid_vulkan_features = ['spirv1.0', 'spirv1.1', 'spirv1.2', 'spirv1.3', 'spirv1.4', 'spirv1.5', 'spirv1.6']
            for feature in features:
                if feature not in valid_vulkan_features:
                    errors.append(f"Invalid Vulkan target feature: {feature}")
        
        elif target_enum == CompilationTarget.METAL:
            # Metal features are typically version indicators
            valid_metal_features = ['metal2.0', 'metal2.1', 'metal2.2', 'metal2.3', 'metal2.4', 'metal3.0']
            for feature in features:
                if feature not in valid_metal_features:
                    errors.append(f"Invalid Metal target feature: {feature}")
        
        return len(errors) == 0, errors