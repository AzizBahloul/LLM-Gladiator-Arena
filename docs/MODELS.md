# Model catalog

238 chat-capable local model families (450 sized variants) from https://ollama.com/library, snapshot 2026-11-15.
Sizes are approximate downloads for the default 4-bit builds. 'think' marks reasoning models (the arena turns their thinking off).
Embedding-only models and hosted-cloud-only entries are excluded from the arena and listed at the bottom.

| Model | Sizes (approx GB) | Capabilities | Pulls | What it is |
|---|---|---|---|---|
| `llama3.1` | 8b (5.1), 70b (42.4), 405b (243.3) | tools | 121.1M | Llama 3.1 is a new state-of-the-art model from Meta available in 8B, 70B and 405B parameter sizes. |
| `deepseek-r1` | 1.5b (1.2), 7b (4.5), 8b (5.1), 14b (8.8), 32b (19.6), 70b (42.4), 671b (402.9) | tools, think | 95.1M | DeepSeek-R1 is a family of open reasoning models with performance approaching that of leading models, such... |
| `llama3.2` | 1b (0.9), 3b (2.1) | tools | 87.7M | Meta's Llama 3.2 goes small with 1B and 3B models. |
| `qwen2.5` | 0.5b (0.6), 1.5b (1.2), 3b (2.1), 7b (4.5), 14b (8.8), 32b (19.6), 72b (43.5) | tools | 45.9M | Qwen2.5 models are pretrained on Alibaba's latest large-scale dataset, encompassing up to 18 trillion token... |
| `qwen3` | 0.6b (0.7), 1.7b (1.4), 4b (2.8), 8b (5.1), 14b (8.8), 30b (18.4), 32b (19.6), 235b (141.3) | tools, think | 43.6M | Qwen3 is the latest generation of large language models in Qwen series, offering a comprehensive suite of d... |
| `gemma3` | 270m (0.5), 1b (0.9), 4b (2.8), 12b (7.5), 27b (16.6) | vision | 41.9M | The current, most capable model that runs on a single GPU. |
| `gemma2` | 2b (1.5), 9b (5.7), 27b (16.6) | chat | 37.3M | Google Gemma 2 is a high-performing and efficient model available in three sizes: 2B, 9B, and 27B. |
| `mistral` | 7b (4.5) | tools | 34.2M | The 7B model released by Mistral AI, updated to version 0.3. |
| `gemma4` | e2b (1.5), e4b (2.8), 12b (7.5), 26b (15.9), 31b (18.9) | vision, tools, think, audio | 29.2M | Gemma 4 models are designed to deliver frontier-level performance at each size. They are well-suited for re... |
| `qwen3.5` | 0.8b (0.8), 2b (1.5), 4b (2.8), 9b (5.7), 27b (16.6), 35b (21.4), 122b (73.5) | vision, tools, think | 26.2M | Qwen 3.5 is a family of open-source multimodal models that delivers exceptional utility and performance. |
| `llama3` | 8b (5.1), 70b (42.4) | chat | 26.0M | Meta Llama 3: The most capable openly available LLM to date |
| `qwen2.5-coder` | 0.5b (0.6), 1.5b (1.2), 3b (2.1), 7b (4.5), 14b (8.8), 32b (19.6) | tools | 23.8M | The latest series of Code-Specific Qwen models, with significant improvements in code generation, code reas... |
| `phi3` | 3.8b (2.6), 14b (8.8) | chat | 18.4M | Phi-3 is a family of lightweight 3B (Mini) and 14B (Medium) state-of-the-art open models by Microsoft. |
| `gpt-oss` | 20b (12.3), 120b (72.3) | tools, think | 15.6M | OpenAI’s open-weight models designed for powerful reasoning, agentic tasks, and versatile developer use cases. |
| `llava` | 7b (4.5), 13b (8.2), 34b (20.8) | vision | 15.4M | LLaVA is a novel end-to-end trained large multimodal model that combines a vision encoder and Vicuna for ge... |
| `qwen3-coder` | 30b (18.4), 480b (288.4) | tools | 11.0M | Alibaba's performant long context models for agentic and coding tasks. |
| `glm-ocr` | latest | vision, tools | 9.4M | GLM-OCR is a multimodal OCR model for complex document understanding, built on the GLM-V encoder–decoder ar... |
| `gemma` | 2b (1.5), 7b (4.5) | chat | 8.4M | Gemma is a family of lightweight, state-of-the-art open models built by Google DeepMind. Updated to version... |
| `codellama` | 7b (4.5), 13b (8.2), 34b (20.8), 70b (42.4) | chat | 8.4M | A large language model that can use text prompts to generate and discuss code. |
| `qwen` | 0.5b (0.6), 1.8b (1.4), 4b (2.8), 7b (4.5), 14b (8.8), 32b (19.6), 72b (43.5), 110b (66.3) | chat | 8.3M | Qwen 1.5 is a series of large language models by Alibaba Cloud spanning from 0.5B to 110B parameters |
| `phi4` | 14b (8.8) | chat | 7.8M | Phi-4 is a 14B parameter, state-of-the-art open model from Microsoft. |
| `qwen3.6` | 27b (16.6), 35b (21.4) | vision, tools, think | 7.7M | Qwen3.6 delivers substantial upgrades in agentic coding and thinking preservation than previous Qwen models. |
| `llama2` | 7b (4.5), 13b (8.2), 70b (42.4) | chat | 7.6M | Llama 2 is a collection of foundation language models ranging from 7B to 70B parameters. |
| `qwen3-vl` | 2b (1.5), 4b (2.8), 8b (5.1), 30b (18.4), 32b (19.6), 235b (141.3) | vision, tools, think | 7.3M | The most powerful vision-language model in the Qwen model family to date. |
| `tinyllama` | 1.1b (1) | chat | 6.8M | The TinyLlama project is an open endeavor to train a compact 1.1B Llama model on 3 trillion tokens. |
| `qwen3.8` | 27b (16.6) | vision, tools, think | 6.6M | Qwen3.8 delivers substantial gains across coding, professional work, research, and long-horizon agentic tasks. |
| `qwen2` | 0.5b (0.6), 1.5b (1.2), 7b (4.5), 72b (43.5) | tools | 6.4M | Qwen2 is a new series of large language models from Alibaba group |
| `qwen2.5vl` | 3b (2.1), 7b (4.5), 32b (19.6), 72b (43.5) | vision | 6.1M | Flagship vision-language model of Qwen and also a significant leap from the previous Qwen2-VL. |
| `mistral-nemo` | 12b (7.5) | tools | 5.8M | A state-of-the-art 12B model with 128k context length, built by Mistral AI in collaboration with NVIDIA. |
| `minicpm-v` | 8b (5.1) | vision | 5.7M | A series of multimodal LLMs (MLLMs) designed for vision-language understanding. |
| `llama3.2-vision` | 11b (6.9), 90b (54.4) | vision | 5.6M | Llama 3.2 Vision is a collection of instruction-tuned image reasoning generative models in 11B and 90B sizes. |
| `deepseek-coder` | 1.3b (1.1), 6.7b (4.4), 33b (20.2) | chat | 4.9M | DeepSeek Coder is a capable coding model trained on two trillion code and natural language tokens. |
| `llama3.3` | 70b (42.4) | tools | 4.5M | New state of the art 70B model. Llama 3.3 70B offers similar performance compared to the Llama 3.1 405B model. |
| `dolphin3` | 8b (5.1) | chat | 4.3M | Dolphin 3.0 Llama 3.1 8B is the next generation of the Dolphin series of instruct-tuned models designed to... |
| `smollm2` | 135m (0.4), 360m (0.6), 1.7b (1.4) | tools | 4.2M | SmolLM2 is a family of compact language models available in three size: 135M, 360M, and 1.7B parameters. |
| `deepseek-v3` | 671b (402.9) | chat | 3.9M | A strong Mixture-of-Experts (MoE) language model with 671B total parameters with 37B activated for each token. |
| `olmo2` | 7b (4.5), 13b (8.2) | chat | 3.8M | OLMo 2 is a new family of 7B and 13B models trained on up to 5T tokens. These models are on par with or bet... |
| `deepseek-coder-v2` | 16b (9.9), 236b (141.9) | chat | 3.4M | An open-source Mixture-of-Experts code language model that achieves performance comparable to GPT4-Turbo in... |
| `codegemma` | 2b (1.5), 7b (4.5) | chat | 3.3M | CodeGemma is a collection of powerful, lightweight models that can perform a variety of coding tasks like f... |
| `mistral-small` | 22b (13.5), 24b (14.7) | tools | 3.2M | Mistral Small 3 sets a new benchmark in the “small” Large Language Models category below 70B. |
| `orca-mini` | 3b (2.1), 7b (4.5), 13b (8.2), 70b (42.4) | chat | 3.2M | A general-purpose model ranging from 3 billion parameters to 70 billion, suitable for entry-level hardware. |
| `granite3.1-moe` | 1b (0.9), 3b (2.1) | tools | 3.1M | The IBM Granite 1B and 3B models are long-context mixture of experts (MoE) Granite models from IBM designed... |
| `starcoder2` | 3b (2.1), 7b (4.5), 15b (9.3) | chat | 3.1M | StarCoder2 is the next generation of transparently trained open code LLMs that comes in three sizes: 3B, 7B... |
| `nemotron-3-super` | 120b (72.3) | tools, think | 3.1M | NVIDIA Nemotron 3 Super is a 120B open MoE model activating just 12B parameters to deliver maximum compute... |
| `mixtral` | 8x7b (4), 8x22b (4) | tools | 3.0M | A set of Mixture of Experts (MoE) model with open weights by Mistral AI in 8x7b and 8x22b parameter sizes. |
| `translategemma` | 4b (2.8), 12b (7.5), 27b (16.6) | vision | 2.9M | A new collection of open translation models built on Gemma 3, helping people communicate across 55 languages. |
| `devstral-small-2` | 24b (14.7) | vision, tools | 2.8M | 24B model that excels at using tools to explore codebases, editing multiple files and power software engine... |
| `llama2-uncensored` | 7b (4.5), 70b (42.4) | chat | 2.8M | Uncensored Llama 2 model by George Sung and Jarrad Hope. |
| `falcon3` | 1b (0.9), 3b (2.1), 7b (4.5), 10b (6.3) | chat | 2.7M | A family of efficient AI models under 10B parameters performant in science, math, and coding through innova... |
| `mistral-small3.2` | 24b (14.7) | vision, tools | 2.5M | An update to Mistral Small that improves on function calling, instruction following, and less repetition er... |
| `gemma3n` | e2b (1.5), e4b (2.8) | vision | 2.5M | Gemma 3n models are designed for efficient execution on everyday devices such as laptops, tablets or phones. |
| `smollm` | 135m (0.4), 360m (0.6), 1.7b (1.4) | chat | 2.4M | A family of small models with 135M, 360M, and 1.7B parameters, trained on a new high-quality dataset. |
| `sqlcoder` | 7b (4.5), 15b (9.3) | chat | 2.4M | SQLCoder is a code completion model fined-tuned on StarCoder for SQL generation tasks |
| `llava-llama3` | 8b (5.1) | vision | 2.3M | A LLaVA model fine-tuned from Llama 3 Instruct with better scores in several benchmarks. |
| `qwq` | 32b (19.6) | tools | 2.3M | QwQ is the reasoning model of the Qwen series. |
| `dolphin-llama3` | 8b (5.1), 70b (42.4) | chat | 2.2M | Dolphin 2.9 is a new model with 8B and 70B sizes by Eric Hartford based on Llama 3 that has a variety of in... |
| `qwen3-coder-next` | latest | tools | 2.2M | Qwen3-Coder-Next is a coding-focused language model from Alibaba's Qwen team, optimized for agentic coding... |
| `moondream` | 1.8b (1.4) | vision | 2.2M | moondream2 is a small vision language model designed to run efficiently on edge devices. |
| `glm-4.7-flash` | latest | tools, think | 2.2M | As the strongest model in the 30B class, GLM-4.7-Flash offers a new option for lightweight deployment that... |
| `cogito` | 3b (2.1), 8b (5.1), 14b (8.8), 32b (19.6), 70b (42.4) | tools | 2.2M | Cogito v1 Preview is a family of hybrid reasoning models by Deep Cogito that outperform the best available... |
| `starcoder` | 1b (0.9), 3b (2.1), 7b (4.5), 15b (9.3) | chat | 2.1M | StarCoder is a code generation model trained on 80+ programming languages. |
| `wizardcoder` | 33b (20.2) | chat | 2.0M | State-of-the-art code generation model |
| `dolphin-mixtral` | 8x7b (4), 8x22b (4) | chat | 2.0M | Uncensored, 8x7b and 8x22b fine-tuned models based on the Mixtral mixture of experts models that excels at... |
| `openhermes` | latest | chat | 1.9M | OpenHermes 2.5 is a 7B model fine-tuned by Teknium on Mistral with fully open datasets. |
| `llama4` | 16x17b (4), 128x17b (4) | vision, tools | 1.9M | Meta's latest collection of multimodal models. |
| `dolphin-mistral` | 7b (4.5) | chat | 1.9M | The uncensored Dolphin model based on Mistral that excels at coding tasks. Updated to version 2.8. |
| `hermes3` | 3b (2.1), 8b (5.1), 70b (42.4), 405b (243.3) | tools | 1.8M | Hermes 3 is the latest version of the flagship Hermes series of LLMs by Nous Research |
| `phi4-mini` | 3.8b (2.6) | tools | 1.7M | Phi-4-mini brings significant enhancements in multilingual support, reasoning, and mathematics, and now, th... |
| `phi4-reasoning` | 14b (8.8) | chat | 1.7M | Phi 4 reasoning and reasoning plus are 14-billion parameter open-weight reasoning models that rival much la... |
| `granite-code` | 3b (2.1), 8b (5.1), 20b (12.3), 34b (20.8) | chat | 1.7M | A family of open foundation models by IBM for Code Intelligence |
| `dolphin-phi` | 2.7b (2) | chat | 1.6M | 2.7B uncensored Dolphin model by Eric Hartford, based on the Phi language model by Microsoft Research. |
| `ministral-3` | 3b (2.1), 8b (5.1), 14b (8.8) | vision, tools | 1.6M | The Ministral 3 family is designed for edge deployment, capable of running on a wide range of hardware. |
| `yi` | 6b (3.9), 9b (5.7), 34b (20.8) | chat | 1.6M | Yi 1.5 is a high-performing, bilingual language model. |
| `granite4` | 350m (0.6), 1b (0.9), 3b (2.1) | tools | 1.6M | Granite 4 features improved instruction following (IF) and tool-calling capabilities, making them more effe... |
| `command-r` | 35b (21.4) | tools | 1.6M | Command R is a Large Language Model optimized for conversational interaction and long context tasks. |
| `phi` | 2.7b (2) | chat | 1.6M | Phi-2: a 2.7B language model by Microsoft Research that demonstrates outstanding reasoning and language und... |
| `magistral` | 24b (14.7) | tools, think | 1.5M | Magistral is a small, efficient reasoning model with 24B parameters. |
| `mistral-openorca` | 7b (4.5) | chat | 1.5M | Mistral OpenOrca is a 7 billion parameter model, fine-tuned on top of the Mistral 7B model using the OpenOr... |
| `openchat` | 7b (4.5) | chat | 1.4M | A family of open-source models trained on a wide variety of data, surpassing ChatGPT on various benchmarks.... |
| `codestral` | 22b (13.5) | chat | 1.4M | Codestral is Mistral AI’s first-ever code model designed for code generation tasks. |
| `mistral-large` | 123b (74.1) | tools | 1.4M | Mistral Large 2 is Mistral's new flagship model that is significantly more capable in code generation, math... |
| `wizard-vicuna-uncensored` | 7b (4.5), 13b (8.2), 30b (18.4) | chat | 1.3M | Wizard Vicuna Uncensored is a 7B, 13B, and 30B parameter model based on Llama 2 uncensored by Eric Hartford. |
| `vicuna` | 7b (4.5), 13b (8.2), 33b (20.2) | chat | 1.3M | General use chat model based on Llama and Llama 2 with 2K to 16K context sizes. |
| `deepseek-llm` | 7b (4.5), 67b (40.5) | chat | 1.3M | An advanced language model crafted with 2 trillion bilingual tokens. |
| `zephyr` | 7b (4.5), 141b (84.9) | chat | 1.3M | Zephyr is a series of fine-tuned versions of the Mistral and Mixtral models that are trained to act as help... |
| `lfm2.5-thinking` | 1.2b (1.1) | tools, think | 1.3M | LFM2.5 is a new family of hybrid models designed for on-device deployment. |
| `glm4` | 9b (5.7) | chat | 1.3M | A strong multi-lingual general language model with competitive performance to Llama 3. |
| `nous-hermes` | 7b (4.5), 13b (8.2) | chat | 1.3M | General use models based on Llama and Llama 2 from Nous Research. |
| `deepscaler` | 1.5b (1.2) | chat | 1.3M | A fine-tuned version of Deepseek-R1-Distilled-Qwen-1.5B that surpasses the performance of OpenAI’s o1-previ... |
| `deepseek-v2` | 16b (9.9), 236b (141.9) | chat | 1.3M | A strong, economical, and efficient Mixture-of-Experts language model. |
| `neural-chat` | 7b (4.5) | chat | 1.3M | A fine-tuned model based on Mistral with good coverage of domain and language. |
| `wizardlm2` | 7b (4.5), 8x22b (4) | chat | 1.2M | State of the art large language model from Microsoft AI with improved performance on complex chat, multilin... |
| `falcon` | 7b (4.5), 40b (24.4), 180b (108.3) | chat | 1.2M | A large language model built by the Technology Innovation Institute (TII) for use in summarization, text ge... |
| `llama2-chinese` | 7b (4.5), 13b (8.2) | chat | 1.2M | Llama 2 based model fine tuned to improve Chinese dialogue ability. |
| `llava-phi3` | 3.8b (2.6) | vision | 1.2M | A new small LLaVA model fine-tuned from Phi 3 Mini. |
| `qwen2-math` | 1.5b (1.2), 7b (4.5), 72b (43.5) | chat | 1.2M | Qwen2 Math is a series of specialized math language models built upon the Qwen2 LLMs, which significantly o... |
| `openthinker` | 7b (4.5), 32b (19.6) | chat | 1.2M | A fully open-source family of reasoning models built using a dataset derived by distilling DeepSeek-R1. |
| `stablelm2` | 1.6b (1.3), 12b (7.5) | chat | 1.2M | Stable LM 2 is a state-of-the-art 1.6B and 12B parameter language model trained on multilingual data in Eng... |
| `codeqwen` | 7b (4.5) | chat | 1.2M | CodeQwen1.5 is a large language model pretrained on a large amount of code data. |
| `granite3.3` | 2b (1.5), 8b (5.1) | tools | 1.2M | IBM Granite 2B and 8B models are 128K context length language models that have been fine-tuned for improved... |
| `yi-coder` | 1.5b (1.2), 9b (5.7) | chat | 1.2M | Yi-Coder is a series of open-source code language models that delivers state-of-the-art coding performance... |
| `lfm2` | 24b (14.7) | tools | 1.2M | LFM2 is a family of hybrid models designed for on-device deployment. LFM2-24B-A2B is the largest model in t... |
| `aya` | 8b (5.1), 35b (21.4) | chat | 1.2M | Aya 23, released by Cohere, is a new family of state-of-the-art, multilingual models that support 23 langua... |
| `nous-hermes2` | 10.7b (6.8), 34b (20.8) | chat | 1.1M | The powerful family of models by Nous Research that excels at scientific discussion and coding tasks. |
| `stable-code` | 3b (2.1) | chat | 1.1M | Stable Code 3B is a coding model with instruct and code completion variants on par with models such as Code... |
| `wizard-math` | 7b (4.5), 13b (8.2), 70b (42.4) | chat | 1.1M | Model focused on math and logic problems |
| `devstral` | 24b (14.7) | tools | 1.1M | Devstral: the best open source model for coding agents |
| `internlm2` | 1m (0.4), 1.8b (1.4), 7b (4.5), 20b (12.3) | chat | 1.1M | InternLM2.5 is a 7B parameter model tailored for practical scenarios with outstanding reasoning capability. |
| `llama-guard3` | 1b (0.9), 8b (5.1) | chat | 1.1M | Llama Guard 3 is a series of models fine-tuned for content safety classification of LLM inputs and responses. |
| `aya-expanse` | 8b (5.1), 32b (19.6) | tools | 1.1M | Cohere For AI's language models trained to perform well across 23 different languages. |
| `granite3.1-dense` | 2b (1.5), 8b (5.1) | tools | 1.1M | The IBM Granite 2B and 8B models are text-only dense LLMs trained on over 12 trillion tokens of data, demon... |
| `xwinlm` | 7b (4.5), 13b (8.2) | chat | 1.1M | Conversational model based on Llama 2 that performs competitively on various benchmarks. |
| `granite3-dense` | 2b (1.5), 8b (5.1) | tools | 1.1M | The IBM Granite 2B and 8B models are designed to support tool-based use cases and support for retrieval aug... |
| `llama3-chatqa` | 8b (5.1), 70b (42.4) | chat | 1.1M | A model from NVIDIA based on Llama 3 that excels at conversational question answering (QA) and retrieval-au... |
| `phi3.5` | 3.8b (2.6) | chat | 1.1M | A lightweight AI model with 3.8 billion parameters with performance overtaking similarly and larger sized m... |
| `dolphincoder` | 7b (4.5), 15b (9.3) | chat | 1.1M | A 7B and 15B uncensored variant of the Dolphin model family that excels at coding, based on StarCoder2. |
| `samantha-mistral` | 7b (4.5) | chat | 1.1M | A companion assistant trained in philosophy, psychology, and personal relationships. Based on Mistral. |
| `yarn-llama2` | 7b (4.5), 13b (8.2) | chat | 1.1M | An extension of Llama 2 that supports a context of up to 128k tokens. |
| `llama3-gradient` | 8b (5.1), 70b (42.4) | chat | 1.1M | This model extends LLama-3 8B's context length from 8k to over 1m tokens. |
| `llama3-groq-tool-use` | 8b (5.1), 70b (42.4) | tools | 1.1M | A series of models from Groq that represent a significant advancement in open-source AI capabilities for to... |
| `granite3.2-vision` | 2b (1.5) | vision, tools | 1.1M | A compact and efficient vision-language model, specifically designed for visual document understanding, ena... |
| `phind-codellama` | 34b (20.8) | chat | 1.0M | Code generation model based on Code Llama. |
| `starling-lm` | 7b (4.5) | chat | 1.0M | Starling is a large language model trained by reinforcement learning from AI feedback focused on improving... |
| `solar` | 10.7b (6.8) | chat | 1.0M | A compact, yet powerful 10.7B large language model designed for single-turn conversation. |
| `nemotron-3-nano` | 4b (2.8), 30b (18.4) | tools, think | 1.0M | Nemotron-3-Nano is a new Standard for Efficient, Open, and Intelligent Agentic Models, now updated with a 4... |
| `granite3-moe` | 1b (0.9), 3b (2.1) | tools | 1.0M | The IBM Granite 1B and 3B models are the first mixture of experts (MoE) Granite models from IBM designed fo... |
| `stable-beluga` | 7b (4.5), 13b (8.2), 70b (42.4) | chat | 1.0M | Llama 2 based model fine tuned on an Orca-style dataset. Originally called Free Willy. |
| `shieldgemma` | 2b (1.5), 9b (5.7), 27b (16.6) | chat | 1.0M | ShieldGemma is set of instruction tuned models for evaluating the safety of text prompt input and text outp... |
| `orca2` | 7b (4.5), 13b (8.2) | chat | 993K | Orca 2 is built by Microsoft research, and are a fine-tuned version of Meta's Llama 2 models. The model is... |
| `deepcoder` | 1.5b (1.2), 14b (8.8) | chat | 991K | DeepCoder is a fully open-Source 14B coder model at O3-mini level, with a 1.5B version also available. |
| `wizardlm` | latest | chat | 990K | General use model based on Llama 2. |
| `reader-lm` | 0.5b (0.6), 1.5b (1.2) | chat | 982K | A series of models that convert HTML content to Markdown content, which is useful for content conversion ta... |
| `llama-pro` | latest | chat | 958K | An expansion of Llama 2 that specializes in integrating both general language understanding and domain-spec... |
| `yarn-mistral` | 7b (4.5) | chat | 948K | An extension of Mistral to support context windows of 64K or 128K. |
| `nexusraven` | 13b (8.2) | chat | 941K | Nexus Raven is a 13B instruction tuned model for function calling tasks. |
| `meditron` | 7b (4.5), 70b (42.4) | chat | 937K | Open-source medical large language model adapted from Llama 2 to the medical domain. |
| `bakllava` | 7b (4.5) | vision | 925K | BakLLaVA is a multimodal model consisting of the Mistral 7B base model augmented with the LLaVA architecture. |
| `mistral-small3.1` | 24b (14.7) | vision, tools | 919K | Building upon Mistral Small 3, Mistral Small 3.1 (2503) adds state-of-the-art vision understanding and enha... |
| `nemotron-3.5-lightning` | 30b (18.4) | tools, think | 899K | NVIDIA Nemotron 3.5 Lightning is an open 30B mixture-of-experts (MoE) model with 3B active parameters built... |
| `command-r-plus` | 104b (62.8) | tools | 846K | Command R+ is a powerful, scalable large language model purpose-built to excel at real-world enterprise use... |
| `exaone-deep` | 2.4b (1.8), 7.8b (5), 32b (19.6) | chat | 798K | EXAONE Deep exhibits superior capabilities in various reasoning tasks including math and coding benchmarks,... |
| `ornith` | 9b (5.7), 35b (21.4) | tools, think | 778K | A self-improving family of open-source models for agentic coding |
| `tinydolphin` | 1.1b (1) | chat | 759K | An experimental 1.1B parameter model trained on the new Dolphin 2.8 dataset by Eric Hartford and based on T... |
| `deepseek-v3.1` | 671b (402.9) | tools, think | 756K | DeepSeek-V3.1-Terminus is a hybrid model that supports both thinking mode and non-thinking mode. |
| `medllama2` | 7b (4.5) | chat | 756K | Fine-tuned Llama 2 model to answer medical questions based on an open source medical dataset. |
| `nemotron-mini` | 4b (2.8) | tools | 747K | A commercial-friendly small language model by NVIDIA optimized for roleplay, RAG QA, and function calling. |
| `nemotron3` | 33b (20.2) | vision, tools, think, audio | 746K | NVIDIA Nemotron 3 Nano Omni is a multimodal large language model that unifies video, audio, image, and text... |
| `codegeex4` | 9b (5.7) | chat | 721K | A versatile model for AI software development scenarios, including code completion. |
| `deepseek-ocr` | 3b (2.1) | vision | 699K | DeepSeek-OCR is a vision-language model that can perform token-efficient OCR. |
| `opencoder` | 1.5b (1.2), 8b (5.1) | chat | 696K | OpenCoder is an open and reproducible code LLM family which includes 1.5B and 8B models, supporting chat in... |
| `wizardlm-uncensored` | 13b (8.2) | chat | 677K | Uncensored version of Wizard LM model |
| `nemotron` | 70b (42.4) | tools | 655K | Llama-3.1-Nemotron-70B-Instruct is a large language model customized by NVIDIA to improve the helpfulness o... |
| `granite4.1` | 3b (2.1), 8b (5.1), 30b (18.4) | tools | 645K | IBM Granite Models are a family of enterprise-ready, open foundation models that support multilingual capab... |
| `reflection` | 70b (42.4) | chat | 643K | A high-performing model trained with a new technique called Reflection-tuning that teaches a LLM to detect... |
| `codeup` | 13b (8.2) | chat | 625K | Great code generation model based on Llama2. |
| `athene-v2` | 72b (43.5) | tools | 619K | Athene-V2 is a 72B parameter model which excels at code completion, mathematics, and log extraction tasks. |
| `nous-hermes2-mixtral` | 8x7b (4) | chat | 618K | The Nous Hermes 2 model from Nous Research, now trained over Mixtral. |
| `qwen3-next` | 80b (48.4) | tools, think | 618K | The first installment in the Qwen3-Next series with strong performance in terms of both parameter efficienc... |
| `exaone3.5` | 2.4b (1.8), 7.8b (5), 32b (19.6) | chat | 616K | EXAONE 3.5 is a collection of instruction-tuned bilingual (English and Korean) generative models ranging fr... |
| `megadolphin` | 120b (72.3) | chat | 597K | MegaDolphin-2.2-120b is a transformation of Dolphin-2.2-70b created by interleaving the model with itself. |
| `everythinglm` | 13b (8.2) | chat | 597K | Uncensored Llama2 based model with support for a 16K context window. |
| `nuextract` | 3.8b (2.6) | chat | 592K | A 3.8B model fine-tuned on a private high-quality synthetic dataset for information extraction, based on Ph... |
| `solar-pro` | 22b (13.5) | chat | 588K | Solar Pro Preview: an advanced large language model (LLM) with 22 billion parameters designed to fit into a... |
| `mathstral` | 7b (4.5) | chat | 586K | MathΣtral: a 7B model designed for math reasoning and scientific discovery by Mistral AI. |
| `magicoder` | 7b (4.5) | chat | 585K | Magicoder is a family of 7B parameter models trained on 75K synthetic instruction data using OSS-Instruct,... |
| `notus` | 7b (4.5) | chat | 571K | A 7B chat model fine-tuned with high-quality data and based on Zephyr. |
| `falcon2` | 11b (6.9) | chat | 568K | Falcon2 is an 11B parameters causal decoder-only model built by TII and trained over 5T tokens. |
| `notux` | 8x7b (4) | chat | 566K | A top-performing mixture of experts model, fine-tuned with high-quality data. |
| `stablelm-zephyr` | 3b (2.1) | chat | 565K | A lightweight chat model allowing accurate, and responsive output without requiring high-end hardware. |
| `bespoke-minicheck` | 7b (4.5) | chat | 559K | A state-of-the-art fact-checking model developed by Bespoke Labs. |
| `duckdb-nsql` | 7b (4.5) | chat | 555K | 7B parameter text-to-SQL model made by MotherDuck and Numbers Station. |
| `firefunction-v2` | 70b (42.4) | tools | 552K | An open weights function calling model based on Llama 3, competitive with GPT-4o function calling capabilit... |
| `mistrallite` | 7b (4.5) | chat | 551K | MistralLite is a fine-tuned model based on Mistral with enhanced capabilities of processing long contexts. |
| `wizard-vicuna` | 13b (8.2) | chat | 544K | Wizard Vicuna is a 13B parameter model based on Llama 2 trained by MelodysDreamj. |
| `open-orca-platypus2` | 13b (8.2) | chat | 536K | Merge of the Open Orca OpenChat model and the Garage-bAInd Platypus 2 model. Designed for chat and code gen... |
| `rnj-1` | 8b (5.1) | tools | 531K | Rnj-1 is a family of 8B parameter open-weight, dense models trained from scratch by Essential AI, optimized... |
| `codebooga` | 34b (20.8) | chat | 529K | A high-performing code instruct model created by merging two existing code models. |
| `goliath` | latest | chat | 509K | A language model created by combining two fine-tuned Llama 2 70B models into one. |
| `olmo-3` | 7b (4.5), 32b (19.6) | tools, think | 489K | Olmo is a series of Open language models designed to enable the science of language models. These models ar... |
| `medgemma` | 4b (2.8), 27b (16.6) | vision | 486K | MedGemma is a collection of Gemma 3 variants that are trained for performance on medical text and image com... |
| `granite3.2` | 2b (1.5), 8b (5.1) | tools | 484K | Granite-3.2 is a family of long-context AI models from IBM Granite fine-tuned for thinking capabilities. |
| `ornith-1.5` | 9b (5.7), 35b (21.4), 122b (73.5), 397b (238.5) | vision, tools, think | 480K | Chirp Chirp! We are introducing Ornith-1.5, a major step toward building foundation models through end-to-e... |
| `sailor2` | 1b (0.9), 8b (5.1), 20b (12.3) | chat | 445K | Sailor2 are multilingual language models made for South-East Asia. Available in 1B, 8B, and 20B parameter s... |
| `mistral-medium-3.5` | 128b (77.1) | vision, tools, think | 443K | Mistral Medium 3.5 is the first flagship model of Mistral AI that merged instruction-following, reasoning,... |
| `r1-1776` | 70b (42.4), 671b (402.9) | chat | 441K | A version of the DeepSeek-R1 model that has been post trained to provide unbiased, accurate, and factual in... |
| `tulu3` | 8b (5.1), 70b (42.4) | chat | 431K | Tülu 3 is a leading instruction following model family, offering fully open-source data, code, and recipes... |
| `muse-glimmer` | 30b (18.4) | vision, tools, think | 394K | Meta's latest open model built for always-on local agents. 30B parameters, licensed under Apache 2.0 and ru... |
| `dbrx` | 132b (79.5) | chat | 388K | DBRX is an open, general-purpose LLM created by Databricks. |
| `devstral-2` | 123b (74.1) | tools | 382K | 123B model that excels at using tools to explore codebases, editing multiple files and power software engin... |
| `granite3-guardian` | 2b (1.5), 8b (5.1) | chat | 359K | The IBM Granite Guardian 3.0 2B and 8B models are designed to detect risks in prompts and/or responses. |
| `command-r7b` | 7b (4.5) | tools | 357K | The smallest model in Cohere's R series delivers top-tier speed, efficiency, and quality to build powerful... |
| `lfm2.5` | 8b (5.1), 24b (14.7) | tools, think | 346K | LFM2.5-8B-A1B, an edge model built for fast, reliable tool calling on consumer hardware. |
| `alfred` | 40b (24.4) | chat | 345K | A robust conversational model designed to be used for both chat and instruct use cases. |
| `phi4-mini-reasoning` | 3.8b (2.6) | chat | 332K | Phi 4 mini reasoning is a lightweight open model that balances efficiency with advanced reasoning ability. |
| `olmo-3.1` | 32b (19.6) | tools, think | 322K | Olmo is a series of Open language models designed to enable the science of language models. These models ar... |
| `deepseek-v2.5` | 236b (141.9) | chat | 313K | An upgraded version of DeekSeek-V2 that integrates the general and coding abilities of both DeepSeek-V2-Cha... |
| `granite4.2` | 3b (2.1), 8b (5.1), 30b (18.4) | chat | 296K | IBM Granite Models are a family of enterprise-ready, open foundation models that support multilingual capab... |
| `smallthinker` | 3b (2.1) | chat | 278K | A new small reasoning model fine-tuned from the Qwen 2.5 3B Instruct model. |
| `qwen3.8-flash-next` | latest | vision, tools, think | 257K | This experimental preview of the architecture that will underpin Qwen4. |
| `command-a` | 111b (66.9) | tools | 250K | 111 billion parameter model optimized for demanding enterprises that require fast, secure, and high-quality AI |
| `cogito-2.1` | 671b (402.9) | chat | 243K | The Cogito v2.1 LLMs are instruction tuned generative models. All models are released under MIT license for... |
| `marco-o1` | 7b (4.5) | chat | 231K | An open large reasoning model for real-world solutions by the Alibaba International Digital Commerce Group... |
| `medgemma1.5` | 4b (2.8) | vision | 230K | MedGemma 1.5 4B is an updated version of the MedGemma 4B model. |
| `functiongemma` | 270m (0.5) | tools | 219K | FunctionGemma is a specialized version of Google's Gemma 3 270M model fine-tuned explicitly for function ca... |
| `command-r7b-arabic` | 7b (4.5) | tools | 218K | A new state-of-the-art version of the lightweight Command R7B model that excels in advanced Arabic language... |
| `laguna-s-2.1` | latest | tools, think | 197K | Our most capable model to date, designed for long-horizon work. 70.2% on Terminal-Bench 2.1 at 118B-A8B. |
| `gpt-oss-safeguard` | 20b (12.3), 120b (72.3) | tools, think | 180K | gpt-oss-safeguard-20b and gpt-oss-safeguard-120b are safety reasoning models built-upon gpt-oss |
| `bonsai-2` | 2b (1.5), 4b (2.8), 9b (5.7), 27b (16.6) | vision, tools, think | 176K | Bonsai 2 from Prism ML is a family of vision models built for ternary weights – smaller models with close t... |
| `nemotron-cascade-2` | 30b (18.4) | tools, think | 172K | An open 30B MoE model from NVIDIA with 3B activated parameters that delivers strong reasoning and agentic c... |
| `tev1` | decision (4), 0.8b (0.8), 4b (2.8) | tools, think | 167K | A 4B decision model from Together AI for fast classification. |
| `laguna-xs-2.1` | latest | tools, think | 156K | Laguna XS 2.1 is a 33B total parameter Mixture-of-Experts model with 3B activated parameters per token desi... |
| `phonon` | latest | chat | 153K | Phonon is Gradium’s text-to-speech family. It turns written text into spoken audio as it generates, making... |
| `strands-decider` | decision (4), 2b (1.5) | chat | 123K | A 2B decision model from Strands Agents for fast classification, routing, and scoring. |
| `clef` | decision (4), 27b (16.6) | vision | 108K | Clef is a 27B multimodal model created by Cloudflare that turns a state and a schema of typed questions int... |
| `nimble` | decision (4), 9b (5.7) | tools, think | 98K | A 9B decision model from Bespoke Labs for fast, typed classification. |
| `minicpm-v4.6` | 1b (0.9) | vision | 98K | A Pocket-Sized MLLM for Ultra-Efficient Image and Video Understanding on Your Phone |
| `d3` | decision (4), 2b (1.5), 4b (2.8), 9b (5.7), 27b (16.6) | vision | 96K | Turn text, structured data, and images into scored choices, yes/no answers, and ratings. |
| `mimo-v2.6` | 9b (5.7) | vision, tools, think | 95K | MiMo-V2.6-Distill-Qwen-9B is Xiaomi MiMo’s 9B model for code and agent workflows |
| `flint` | 40b (24.4) | tools, think | 94K | Flint is a 39.8 billion-parameter mixture-of-experts model from Recursive, built for coding agents. |
| `north-mini-code-1.0` | latest | tools, think | 92K | North Mini Code is Cohere's first model for developers — a 30B Mixture-of-Experts model with 3B active para... |
| `lfm3` | 1.7b (1.4) | tools, think | 90K | LFM3-1.7B is a tri-hybrid model for local agents and specialized applications. |
| `clef-flash` | decision (4), 9b (5.7) | vision | 85K | Clef-Flash is a 9B multimodal model that turns a state and a schema of typed questions into decisions. |
| `minicpm-v4.5` | 8b (5.1) | vision | 78K | A GPT-4o Level MLLM for Single Image, Multi Image and High-FPS Video Understanding on Your Phone |
| `d1` | decision (4), 2b (1.5), 3b (2.1) | vision | 73K | d1 is a 3B decision model from Liquid AI, built on LFM2.5-VL-3B |
| `nemotron-3.5-bolt` | e4b (2.8) | vision, tools, think, audio | 70K | Nemotron 3.5 Bolt is NVIDIA’s compact vision-language model for local coding, reasoning, and tool use. |
| `lfm3-omni` | 2b (1.5) | vision, tools, audio | 67K | a single end-to-end model that understands text, images, video and audio, and answers in text and speech |
| `d1-omni` | decision (4), 600m (0.7), 2b (1.5) | vision, audio | 59K | d1-omni is a multimodal 600M decision model from Liquid AI |
| `granite4.1-guardian` | 8b (5.1) | tools, think | 51K | Granite Guardian 4.1 is a specialized safety and judging model from IBM Research that evaluates whether LLM... |
| `lfm3-vl` | 2b (1.5) | vision, tools, think | 50K | LFM3-VL-2B is a vision-language model for on-device visual understanding. |
| `laguna-xs.2` | latest | tools, think | 47K | Laguna XS.2 is a 33B total parameter Mixture-of-Experts model with 3B activated parameters per token design... |
| `autotrust-jev` | decision (4), 9b (5.7), 35b (21.4) | vision | 45K | AutoTrust’s decision models return choices, yes/no probabilities, and ratings for the questions you supply |
| `pplx-decider` | decision (4), 27b (16.6) | vision | 44K | pplx-decider is a 27B decision model from Perplexity, fine-tuned from Qwen3.8-27B |
| `ripple-preview` | 65b (39.4) | tools, think | 43K | 65B dense model built for agentic coding, with up to 1M tokens of context. |
| `lfm3-audio` | 2b (1.5) | vision, tools, audio | 43K | LFM3-Audio-2B is a compact, fully featured audio model. |
| `pplx-decider-flash` | decision (4), 4b (2.8) | vision | 36K | pplx-decider-flash is a 4B decision model from Perplexity, built on Qwen3.5-4B |
| `nemotron-3.5-super` | 120b (72.3) | vision, tools, think | 34K | Nemotron 3.5 Super is NVIDIA’s vision-language model for coding, reasoning, tool use, and document understa... |
| `nimble-v3` | decision (4), 9b (5.7) | tools, think | 30K | A 9B decision model from Bespoke Labs for fast classification, routing, and scoring. |
| `kev` | decision (4) | chat | 30K | Kev scores answers to structured questions about a supplied text state in a single forward pass. |

## Excluded

Embedding-only: `nomic-embed-text`, `mxbai-embed-large`, `bge-m3`, `qwen3-embedding`, `all-minilm`, `snowflake-arctic-embed`, `embeddinggemma`, `nomic-embed-text-v2-moe`, `paraphrase-multilingual`, `snowflake-arctic-embed2`, `granite-embedding`, `bge-large`, `embeddinggemma-2`, `laya`.

Hosted cloud only: `minimax-m3`, `kimi-k2.6`, `deepseek-v4-pro`, `glm-5.2`, `glm-5.3`, `kimi-k2.7-code`, `deepseek-v4.1-flash`, `glm-5.3-flash`, `nemotron-3-ultra`, `kimi-k3`, `beam`, `minimax-m3.1-flash`, `mistral-large-4`, `muse-spark-open`, `kimi-k3.1-pro`, `mimo-v2.6-flash`, `mimo-v2.6-pro`, `inkling-2-small`.
