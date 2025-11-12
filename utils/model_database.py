"""
Comprehensive Ollama Model Database
====================================

This database contains all major models available on Ollama with:
- Memory requirements (VRAM in GB)
- Parameter counts
- Model types (general, code, reasoning, vision)
- Quality ratings (1-10)
- Categories based on GPU tier requirements

Data sourced from: https://ollama.com/search
Last updated: November 2025
"""

from typing import Dict, Any, List

# Complete model database with memory estimates
# Memory calculated as: parameters * bytes_per_param (Q4_K_M quantization ≈ 0.5-0.6 bytes/param)
OLLAMA_MODELS = {
    
    # ============================================================================
    # TINY MODELS (< 1GB VRAM) - For integrated GPUs and low-end cards
    # ============================================================================
    "smollm2:135m": {
        "params": "135M",
        "ram_gb": 0.3,
        "category": "tiny",
        "type": "general",
        "quality": 2,
        "description": "Smallest general purpose model"
    },
    "smollm:135m": {
        "params": "135M",
        "ram_gb": 0.3,
        "category": "tiny",
        "type": "general",
        "quality": 2,
        "description": "Tiny efficient model"
    },
    "smollm2:360m": {
        "params": "360M",
        "ram_gb": 0.5,
        "category": "tiny",
        "type": "general",
        "quality": 3,
        "description": "Small efficient model"
    },
    "smollm:360m": {
        "params": "360M",
        "ram_gb": 0.5,
        "category": "tiny",
        "type": "general",
        "quality": 3,
        "description": "Small general model"
    },
    "qwen2.5:0.5b": {
        "params": "0.5B",
        "ram_gb": 0.7,
        "category": "tiny",
        "type": "general",
        "quality": 4,
        "description": "Qwen tiny model"
    },
    
    # ============================================================================
    # SMALL MODELS (1-2GB VRAM) - GTX 1050, MX series, entry GPUs
    # ============================================================================
    "tinyllama:1.1b": {
        "params": "1.1B",
        "ram_gb": 1.0,
        "category": "small",
        "type": "general",
        "quality": 4,
        "description": "Compact Llama variant"
    },
    "tinydolphin:1.1b": {
        "params": "1.1B",
        "ram_gb": 1.0,
        "category": "small",
        "type": "general",
        "quality": 4,
        "description": "Tiny dolphin uncensored"
    },
    "llama3.2:1b": {
        "params": "1B",
        "ram_gb": 1.0,
        "category": "small",
        "type": "general",
        "quality": 6,
        "description": "Meta's small Llama 3.2"
    },
    "qwen2.5:1.5b": {
        "params": "1.5B",
        "ram_gb": 1.3,
        "category": "small",
        "type": "general",
        "quality": 5,
        "description": "Alibaba Qwen 1.5B"
    },
    "qwen2.5-coder:1.5b": {
        "params": "1.5B",
        "ram_gb": 1.3,
        "category": "small",
        "type": "code",
        "quality": 6,
        "description": "Qwen code specialist"
    },
    "deepseek-r1:1.5b": {
        "params": "1.5B",
        "ram_gb": 1.4,
        "category": "small",
        "type": "reasoning",
        "quality": 7,
        "description": "DeepSeek reasoning model"
    },
    "deepscaler:1.5b": {
        "params": "1.5B",
        "ram_gb": 1.4,
        "category": "small",
        "type": "reasoning",
        "quality": 7,
        "description": "Math reasoning specialist"
    },
    "opencoder:1.5b": {
        "params": "1.5B",
        "ram_gb": 1.3,
        "category": "small",
        "type": "code",
        "quality": 6,
        "description": "Open source code model"
    },
    "deepcoder:1.5b": {
        "params": "1.5B",
        "ram_gb": 1.3,
        "category": "small",
        "type": "code",
        "quality": 6,
        "description": "DeepSeek code model"
    },
    "stablelm2:1.6b": {
        "params": "1.6B",
        "ram_gb": 1.4,
        "category": "small",
        "type": "general",
        "quality": 5,
        "description": "StabilityAI language model"
    },
    "smollm2:1.7b": {
        "params": "1.7B",
        "ram_gb": 1.5,
        "category": "small",
        "type": "general",
        "quality": 5,
        "description": "Efficient small model"
    },
    "qwen:1.8b": {
        "params": "1.8B",
        "ram_gb": 1.5,
        "category": "small",
        "type": "general",
        "quality": 5,
        "description": "Qwen v1 model"
    },
    
    # ============================================================================
    # MEDIUM-SMALL MODELS (2-3GB VRAM) - GTX 1650, RTX 3050 (4GB)
    # ============================================================================
    "gemma2:2b": {
        "params": "2B",
        "ram_gb": 1.8,
        "category": "medium-small",
        "type": "general",
        "quality": 7,
        "description": "Google Gemma 2B v2"
    },
    "gemma:2b": {
        "params": "2B",
        "ram_gb": 1.8,
        "category": "medium-small",
        "type": "general",
        "quality": 6,
        "description": "Google Gemma 2B"
    },
    "granite3.3:2b": {
        "params": "2B",
        "ram_gb": 1.8,
        "category": "medium-small",
        "type": "general",
        "quality": 7,
        "description": "IBM Granite 3.3"
    },
    "granite3.2:2b": {
        "params": "2B",
        "ram_gb": 1.8,
        "category": "medium-small",
        "type": "general",
        "quality": 7,
        "description": "IBM Granite 3.2"
    },
    "granite3-dense:2b": {
        "params": "2B",
        "ram_gb": 1.8,
        "category": "medium-small",
        "type": "general",
        "quality": 7,
        "description": "IBM dense model"
    },
    "codegemma:2b": {
        "params": "2B",
        "ram_gb": 1.8,
        "category": "medium-small",
        "type": "code",
        "quality": 6,
        "description": "Google code model"
    },
    "qwen3:2b": {
        "params": "2B",
        "ram_gb": 1.8,
        "category": "medium-small",
        "type": "general",
        "quality": 7,
        "description": "Qwen 3 generation"
    },
    "phi:2.7b": {
        "params": "2.7B",
        "ram_gb": 2.2,
        "category": "medium-small",
        "type": "general",
        "quality": 7,
        "description": "Microsoft Phi-2"
    },
    "dolphin-phi:2.7b": {
        "params": "2.7B",
        "ram_gb": 2.2,
        "category": "medium-small",
        "type": "general",
        "quality": 7,
        "description": "Uncensored Phi variant"
    },
    
    # ============================================================================
    # MEDIUM MODELS (3-5GB VRAM) - GTX 1660 Ti, RTX 2060, RTX 3050 Ti
    # ============================================================================
    "llama3.2:3b": {
        "params": "3B",
        "ram_gb": 2.5,
        "category": "medium",
        "type": "general",
        "quality": 8,
        "description": "Meta Llama 3.2 3B"
    },
    "qwen2.5:3b": {
        "params": "3B",
        "ram_gb": 2.5,
        "category": "medium",
        "type": "general",
        "quality": 8,
        "description": "Qwen 2.5 3B"
    },
    "qwen2.5-coder:3b": {
        "params": "3B",
        "ram_gb": 2.5,
        "category": "medium",
        "type": "code",
        "quality": 8,
        "description": "Qwen code 3B"
    },
    "qwen3:4b": {
        "params": "4B",
        "ram_gb": 3.0,
        "category": "medium",
        "type": "reasoning",
        "quality": 8,
        "description": "Qwen 3 reasoning"
    },
    "gemma3:4b": {
        "params": "4B",
        "ram_gb": 3.0,
        "category": "medium",
        "type": "general",
        "quality": 8,
        "description": "Google Gemma 3"
    },
    "granite-code:3b": {
        "params": "3B",
        "ram_gb": 2.5,
        "category": "medium",
        "type": "code",
        "quality": 7,
        "description": "IBM code model"
    },
    "stable-code:3b": {
        "params": "3B",
        "ram_gb": 2.5,
        "category": "medium",
        "type": "code",
        "quality": 7,
        "description": "Stability code model"
    },
    "starcoder2:3b": {
        "params": "3B",
        "ram_gb": 2.5,
        "category": "medium",
        "type": "code",
        "quality": 7,
        "description": "BigCode StarCoder"
    },
    "phi3:mini": {
        "params": "3.8B",
        "ram_gb": 3.0,
        "category": "medium",
        "type": "general",
        "quality": 8,
        "description": "Microsoft Phi-3 Mini"
    },
    "phi3.5:3.8b": {
        "params": "3.8B",
        "ram_gb": 3.0,
        "category": "medium",
        "type": "general",
        "quality": 8,
        "description": "Microsoft Phi-3.5"
    },
    "phi4-mini:3.8b": {
        "params": "3.8B",
        "ram_gb": 3.0,
        "category": "medium",
        "type": "general",
        "quality": 8,
        "description": "Microsoft Phi-4 Mini"
    },
    "nemotron-mini:4b": {
        "params": "4B",
        "ram_gb": 3.0,
        "category": "medium",
        "type": "general",
        "quality": 8,
        "description": "NVIDIA mini model"
    },
    
    # ============================================================================
    # LARGE MODELS (5-8GB VRAM) - RTX 3060, RTX 4060, RTX 2070
    # ============================================================================
    "mistral:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "general",
        "quality": 9,
        "description": "Mistral AI 7B"
    },
    "llama3.1:8b": {
        "params": "8B",
        "ram_gb": 5.0,
        "category": "large",
        "type": "general",
        "quality": 9,
        "description": "Meta Llama 3.1 8B"
    },
    "llama3:8b": {
        "params": "8B",
        "ram_gb": 5.0,
        "category": "large",
        "type": "general",
        "quality": 9,
        "description": "Meta Llama 3 8B"
    },
    "qwen2.5:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "general",
        "quality": 9,
        "description": "Qwen 2.5 7B flagship"
    },
    "qwen2.5-coder:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "code",
        "quality": 9,
        "description": "Qwen code expert"
    },
    "codellama:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "code",
        "quality": 8,
        "description": "Meta Code Llama"
    },
    "deepseek-r1:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "reasoning",
        "quality": 9,
        "description": "DeepSeek reasoning 7B"
    },
    "gemma2:9b": {
        "params": "9B",
        "ram_gb": 5.5,
        "category": "large",
        "type": "general",
        "quality": 9,
        "description": "Google Gemma 2 9B"
    },
    "gemma:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "general",
        "quality": 8,
        "description": "Google Gemma 7B"
    },
    "dolphin-mistral:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "general",
        "quality": 8,
        "description": "Uncensored Mistral"
    },
    "dolphin-llama3:8b": {
        "params": "8B",
        "ram_gb": 5.0,
        "category": "large",
        "type": "general",
        "quality": 9,
        "description": "Uncensored Llama3"
    },
    "dolphin3:8b": {
        "params": "8B",
        "ram_gb": 5.0,
        "category": "large",
        "type": "general",
        "quality": 9,
        "description": "Latest dolphin model"
    },
    "neural-chat:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "general",
        "quality": 8,
        "description": "Intel neural chat"
    },
    "openchat:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "general",
        "quality": 8,
        "description": "OpenChat model"
    },
    "yi:6b": {
        "params": "6B",
        "ram_gb": 4.0,
        "category": "large",
        "type": "general",
        "quality": 8,
        "description": "01.AI Yi model"
    },
    "yi-coder:9b": {
        "params": "9B",
        "ram_gb": 5.5,
        "category": "large",
        "type": "code",
        "quality": 9,
        "description": "Yi code specialist"
    },
    "granite-code:8b": {
        "params": "8B",
        "ram_gb": 5.0,
        "category": "large",
        "type": "code",
        "quality": 8,
        "description": "IBM Granite code"
    },
    "starcoder2:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "code",
        "quality": 8,
        "description": "StarCoder 2 7B"
    },
    "hermes3:8b": {
        "params": "8B",
        "ram_gb": 5.0,
        "category": "large",
        "type": "general",
        "quality": 9,
        "description": "Nous Hermes 3"
    },
    "qwen3:8b": {
        "params": "8B",
        "ram_gb": 5.0,
        "category": "large",
        "type": "reasoning",
        "quality": 9,
        "description": "Qwen 3 8B"
    },
    "deepseek-r1:8b": {
        "params": "8B",
        "ram_gb": 5.0,
        "category": "large",
        "type": "reasoning",
        "quality": 9,
        "description": "DeepSeek R1 8B"
    },
    "opencoder:8b": {
        "params": "8B",
        "ram_gb": 5.0,
        "category": "large",
        "type": "code",
        "quality": 8,
        "description": "Open code model"
    },
    "marco-o1:7b": {
        "params": "7B",
        "ram_gb": 4.5,
        "category": "large",
        "type": "reasoning",
        "quality": 8,
        "description": "Alibaba reasoning"
    },
    
    # ============================================================================
    # XLARGE MODELS (8-16GB VRAM) - RTX 3060 Ti, RTX 4060 Ti, RTX 3070
    # ============================================================================
    "mistral-nemo:12b": {
        "params": "12B",
        "ram_gb": 7.5,
        "category": "xlarge",
        "type": "general",
        "quality": 9,
        "description": "Mistral Nemo"
    },
    "phi3:14b": {
        "params": "14B",
        "ram_gb": 8.5,
        "category": "xlarge",
        "type": "general",
        "quality": 9,
        "description": "Microsoft Phi-3 14B"
    },
    "phi4:14b": {
        "params": "14B",
        "ram_gb": 8.5,
        "category": "xlarge",
        "type": "general",
        "quality": 10,
        "description": "Microsoft Phi-4"
    },
    "qwen2.5:14b": {
        "params": "14B",
        "ram_gb": 8.5,
        "category": "xlarge",
        "type": "general",
        "quality": 9,
        "description": "Qwen 2.5 14B"
    },
    "qwen2.5-coder:14b": {
        "params": "14B",
        "ram_gb": 8.5,
        "category": "xlarge",
        "type": "code",
        "quality": 9,
        "description": "Qwen coder 14B"
    },
    "deepseek-r1:14b": {
        "params": "14B",
        "ram_gb": 8.5,
        "category": "xlarge",
        "type": "reasoning",
        "quality": 9,
        "description": "DeepSeek R1 14B"
    },
    "deepcoder:14b": {
        "params": "14B",
        "ram_gb": 8.5,
        "category": "xlarge",
        "type": "code",
        "quality": 9,
        "description": "DeepSeek coder"
    },
    "starcoder2:15b": {
        "params": "15B",
        "ram_gb": 9.0,
        "category": "xlarge",
        "type": "code",
        "quality": 9,
        "description": "StarCoder 2 15B"
    },
    "codellama:13b": {
        "params": "13B",
        "ram_gb": 8.0,
        "category": "xlarge",
        "type": "code",
        "quality": 8,
        "description": "Code Llama 13B"
    },
    "llama2:13b": {
        "params": "13B",
        "ram_gb": 8.0,
        "category": "xlarge",
        "type": "general",
        "quality": 8,
        "description": "Meta Llama 2 13B"
    },
    "granite-code:20b": {
        "params": "20B",
        "ram_gb": 12.0,
        "category": "xlarge",
        "type": "code",
        "quality": 9,
        "description": "IBM Granite 20B"
    },
    "mistral-small:22b": {
        "params": "22B",
        "ram_gb": 13.0,
        "category": "xlarge",
        "type": "general",
        "quality": 10,
        "description": "Mistral Small"
    },
    "codestral:22b": {
        "params": "22B",
        "ram_gb": 13.0,
        "category": "xlarge",
        "type": "code",
        "quality": 10,
        "description": "Mistral Codestral"
    },
    "mistral-small3.2:24b": {
        "params": "24B",
        "ram_gb": 14.0,
        "category": "xlarge",
        "type": "general",
        "quality": 10,
        "description": "Mistral Small 3.2"
    },
    "devstral:24b": {
        "params": "24B",
        "ram_gb": 14.0,
        "category": "xlarge",
        "type": "code",
        "quality": 10,
        "description": "Devstral code agent"
    },
    "magistral:24b": {
        "params": "24B",
        "ram_gb": 14.0,
        "category": "xlarge",
        "type": "reasoning",
        "quality": 10,
        "description": "Magistral reasoning"
    },
    
    # ============================================================================
    # XXLARGE MODELS (16-24GB VRAM) - RTX 3080, RTX 3090, RTX 4080
    # ============================================================================
    "gemma2:27b": {
        "params": "27B",
        "ram_gb": 16.0,
        "category": "xxlarge",
        "type": "general",
        "quality": 10,
        "description": "Google Gemma 2 27B"
    },
    "qwen3:30b": {
        "params": "30B",
        "ram_gb": 18.0,
        "category": "xxlarge",
        "type": "reasoning",
        "quality": 10,
        "description": "Qwen 3 30B"
    },
    "qwen2.5:32b": {
        "params": "32B",
        "ram_gb": 19.0,
        "category": "xxlarge",
        "type": "general",
        "quality": 10,
        "description": "Qwen 2.5 32B"
    },
    "qwen2.5-coder:32b": {
        "params": "32B",
        "ram_gb": 19.0,
        "category": "xxlarge",
        "type": "code",
        "quality": 10,
        "description": "Qwen coder 32B"
    },
    "deepseek-r1:32b": {
        "params": "32B",
        "ram_gb": 19.0,
        "category": "xxlarge",
        "type": "reasoning",
        "quality": 10,
        "description": "DeepSeek R1 32B"
    },
    "openthinker:32b": {
        "params": "32B",
        "ram_gb": 19.0,
        "category": "xxlarge",
        "type": "reasoning",
        "quality": 10,
        "description": "OpenThinker 32B"
    },
    "qwq:32b": {
        "params": "32B",
        "ram_gb": 19.0,
        "category": "xxlarge",
        "type": "reasoning",
        "quality": 10,
        "description": "QwQ reasoning"
    },
    "codellama:34b": {
        "params": "34B",
        "ram_gb": 20.0,
        "category": "xxlarge",
        "type": "code",
        "quality": 9,
        "description": "Code Llama 34B"
    },
    "granite-code:34b": {
        "params": "34B",
        "ram_gb": 20.0,
        "category": "xxlarge",
        "type": "code",
        "quality": 9,
        "description": "IBM Granite 34B"
    },
    
    # ============================================================================
    # MASSIVE MODELS (24GB+ VRAM) - RTX 4090, A100, H100
    # ============================================================================
    "llama3.1:70b": {
        "params": "70B",
        "ram_gb": 40.0,
        "category": "massive",
        "type": "general",
        "quality": 10,
        "description": "Meta Llama 3.1 70B"
    },
    "llama3:70b": {
        "params": "70B",
        "ram_gb": 40.0,
        "category": "massive",
        "type": "general",
        "quality": 10,
        "description": "Meta Llama 3 70B"
    },
    "llama3.3:70b": {
        "params": "70B",
        "ram_gb": 40.0,
        "category": "massive",
        "type": "general",
        "quality": 10,
        "description": "Meta Llama 3.3 70B"
    },
    "qwen2.5:72b": {
        "params": "72B",
        "ram_gb": 42.0,
        "category": "massive",
        "type": "general",
        "quality": 10,
        "description": "Qwen 2.5 72B"
    },
    "deepseek-r1:70b": {
        "params": "70B",
        "ram_gb": 40.0,
        "category": "massive",
        "type": "reasoning",
        "quality": 10,
        "description": "DeepSeek R1 70B"
    },
    "codellama:70b": {
        "params": "70B",
        "ram_gb": 40.0,
        "category": "massive",
        "type": "code",
        "quality": 9,
        "description": "Code Llama 70B"
    },
    "llama2:70b": {
        "params": "70B",
        "ram_gb": 40.0,
        "category": "massive",
        "type": "general",
        "quality": 9,
        "description": "Meta Llama 2 70B"
    },
    "mistral-large:123b": {
        "params": "123B",
        "ram_gb": 70.0,
        "category": "massive",
        "type": "general",
        "quality": 10,
        "description": "Mistral Large"
    },
}


def get_models_by_vram(vram_gb: float, min_quality: int = 5) -> List[str]:
    """Get models that fit within VRAM budget with minimum quality."""
    return [
        name for name, info in OLLAMA_MODELS.items()
        if info["ram_gb"] <= vram_gb and info["quality"] >= min_quality
    ]


def get_models_by_category(category: str) -> List[str]:
    """Get all models in a specific category."""
    return [
        name for name, info in OLLAMA_MODELS.items()
        if info["category"] == category
    ]


def get_models_by_type(model_type: str) -> List[str]:
    """Get all models of a specific type (general, code, reasoning, vision)."""
    return [
        name for name, info in OLLAMA_MODELS.items()
        if info["type"] == model_type
    ]


# Export for easy import
__all__ = [
    'OLLAMA_MODELS',
    'get_models_by_vram',
    'get_models_by_category',
    'get_models_by_type'
]
