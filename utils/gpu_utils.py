# utils/gpu_utils.py
"""GPU detection and device management utilities."""
import os
import subprocess
from typing import Optional, Dict, Any

class GPUManager:
    """Manages GPU detection and device allocation for models."""
    
    def __init__(self):
        self.device = "cpu"
        self.gpu_available = False
        self.gpu_name = None
        self.gpu_memory = None
        self._detect_gpu()
    
    def _detect_gpu(self):
        """Detect available GPU and set device (silent mode)."""
        try:
            import torch
            
            if torch.cuda.is_available():
                self.gpu_available = True
                self.device = "cuda"
                self.gpu_name = torch.cuda.get_device_name(0)
                self.gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
                
                # Set CUDA optimizations
                os.environ['CUDA_LAUNCH_BLOCKING'] = '0'
                torch.backends.cudnn.benchmark = True
                
            elif torch.backends.mps.is_available():
                # Apple Metal Performance Shaders
                self.gpu_available = True
                self.device = "mps"
                self.gpu_name = "Apple Silicon GPU"
                
        except ImportError:
            pass  # Silent - will be shown in main if needed
        except Exception:
            pass  # Silent - will be shown in main if needed
    
    def get_device(self) -> str:
        """Get the device string for model loading."""
        return self.device
    
    def get_ollama_gpu_config(self) -> Dict[str, Any]:
        """Get GPU configuration for Ollama."""
        config = {}
        
        if self.gpu_available:
            if self.device == "cuda":
                # Ollama will auto-detect CUDA
                config['num_gpu'] = 1
                config['gpu_memory_fraction'] = 0.8  # Use 80% of GPU memory
            elif self.device == "mps":
                # Ollama will auto-detect Metal
                config['num_gpu'] = 1
        else:
            config['num_gpu'] = 0
        
        return config
    
    def optimize_for_ollama(self):
        """Set environment variables to optimize Ollama for GPU (silent mode)."""
        if self.gpu_available:
            if self.device == "cuda":
                os.environ['OLLAMA_NUM_GPU'] = '1'
                os.environ['OLLAMA_CUDA_VISIBLE_DEVICES'] = '0'
            elif self.device == "mps":
                os.environ['OLLAMA_NUM_GPU'] = '1'
        else:
            os.environ['OLLAMA_NUM_GPU'] = '0'
    
    def get_info(self) -> Dict[str, Any]:
        """Get GPU information as dictionary."""
        return {
            'available': self.gpu_available,
            'device': self.device,
            'name': self.gpu_name,
            'memory_gb': self.gpu_memory
        }
    
    def estimate_model_capacity(self) -> Dict[str, Any]:
        """Estimate how many models can run simultaneously based on GPU memory."""
        if not self.gpu_available or not self.gpu_memory:
            return {
                'max_models': 1,
                'recommended_size': '1b',
                'can_run_multiple': False
            }
        
        # Rough estimates for model memory usage (including overhead)
        # These are conservative estimates
        mem_gb = self.gpu_memory
        
        if mem_gb >= 24:  # RTX 4090, A100
            return {
                'max_models': 6,
                'recommended_size': '7b',
                'can_run_multiple': True,
                'suggested_models': ['llama3.2:3b', 'mistral:7b', 'phi3:mini', 
                                    'gemma2:2b', 'qwen2.5:3b', 'deepseek-r1:1.5b']
            }
        elif mem_gb >= 12:  # RTX 3060, 4060 Ti
            return {
                'max_models': 6,
                'recommended_size': '3b',
                'can_run_multiple': True,
                'suggested_models': ['llama3.2:3b', 'llama3.2:1b', 'phi3:mini', 
                                    'gemma2:2b', 'qwen2.5:3b', 'deepseek-r1:1.5b']
            }
        elif mem_gb >= 8:  # RTX 3050, 4050
            return {
                'max_models': 4,
                'recommended_size': '1b-3b',
                'can_run_multiple': True,
                'suggested_models': ['llama3.2:1b', 'llama3.2:3b', 'phi3:mini', 'gemma2:2b']
            }
        elif mem_gb >= 6:  # GTX 1660 Ti, RTX 2060
            return {
                'max_models': 3,
                'recommended_size': '1b-3b',
                'can_run_multiple': True,
                'suggested_models': ['llama3.2:1b', 'phi3:mini', 'gemma2:2b']
            }
        elif mem_gb >= 4:  # GTX 1650, lower end
            return {
                'max_models': 2,
                'recommended_size': '1b',
                'can_run_multiple': True,
                'suggested_models': ['llama3.2:1b', 'phi3:mini']
            }
        else:  # Less than 4GB
            return {
                'max_models': 1,
                'recommended_size': '1b',
                'can_run_multiple': False,
                'suggested_models': ['llama3.2:1b']
            }
    
    def clear_cache(self):
        """Clear GPU cache if available."""
        if self.gpu_available:
            try:
                import torch
                if self.device == "cuda":
                    torch.cuda.empty_cache()
                    # Silent success - no logging needed
            except Exception:
                pass  # Silent fail - not critical


# Global GPU manager instance
gpu_manager = GPUManager()
