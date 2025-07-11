from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List
import json
import os
import threading
import sys
import time
import queue
import re
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

from prreview.review.context_selector import Chunk


@dataclass
class Qwen3Model:
    """Wrapper around a local Qwen model generating review text."""

    model_name: str = "Qwen/Qwen3-8B"
    max_model_tokens: int = 131072  # Qwen3's context limit
    force_gpu: bool = True  # Force GPU usage, raise error if not available
    quantization: str = "4bit"  # Options: "4bit", "8bit", "none"

    def __post_init__(self) -> None:
        print(f"🤖 Loading {self.model_name}...")
        
        # Fix tokenizer configuration to prevent character corruption
        os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Prevent tokenizer warnings
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, 
            trust_remote_code=True,
            clean_up_tokenization_spaces=True,  # Clean tokenization
            legacy=False  # Use newer tokenizer behavior
        )
        
        # Ensure pad token is set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load model with memory-efficient settings
        cuda_available = torch.cuda.is_available()
        device = "cuda" if cuda_available else "cpu"
        
        print(f"🖥️  CUDA available: {cuda_available}")
        if cuda_available:
            print(f"🖥️  GPU device: {torch.cuda.get_device_name(0)}")
            print(f"🖥️  GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        elif self.force_gpu:
            raise RuntimeError(
                "GPU requested but CUDA is not available! "
                "Please check your PyTorch installation with: python -c 'import torch; print(torch.cuda.is_available())'"
            )
        
        load_kwargs = {
            "trust_remote_code": True,
            "torch_dtype": torch.float16 if device == "cuda" else torch.float32,
            "low_cpu_mem_usage": True,
        }

        # Use quantization to reduce memory usage
        if cuda_available:
            # For GPU, use device_map="auto" to automatically distribute model across GPUs
            load_kwargs["device_map"] = "auto"
            
            if self.quantization in ["4bit", "8bit"]:
                try:
                    import bitsandbytes as bnb
                    
                    if self.quantization == "4bit":
                        # Use 4-bit quantization for 12GB VRAM
                        load_kwargs["load_in_4bit"] = True
                        load_kwargs["bnb_4bit_compute_dtype"] = torch.float16
                        load_kwargs["bnb_4bit_use_double_quant"] = True
                        load_kwargs["bnb_4bit_quant_type"] = "nf4"
                        print("💾 Using 4-bit quantization on GPU (optimized for 12GB VRAM)")
                        print("   Model will use ~4-5GB VRAM with 4-bit quantization")
                    else:  # 8bit
                        load_kwargs["load_in_8bit"] = True
                        print("💾 Using 8-bit quantization on GPU")
                        print("   Model will use ~8-10GB VRAM with 8-bit quantization")
                        
                except ImportError:
                    print(f"⚠️  bitsandbytes not installed - cannot use {self.quantization} quantization!")
                    print("   This model needs ~16GB+ VRAM without quantization")
                    print("   To enable quantization, run: pip install bitsandbytes")
                    if self.force_gpu:
                        raise ImportError(
                            f"bitsandbytes is required for {self.quantization} quantization on GPU. "
                            "Install with: pip install bitsandbytes"
                        )
            else:
                print("⚠️  No quantization - model will use ~16GB+ VRAM")
                print("   Consider using quantization='4bit' for 12GB GPUs")
        else:
            # For CPU, 4-bit quantization doesn't work well
            try:
                load_kwargs["load_in_8bit"] = True
                print("💾 Using 8-bit quantization on CPU")
            except Exception as e:
                print(
                    f"⚠️  8-bit quantization not available on CPU, using full precision"
                )

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name, **load_kwargs
        )
        self.model.eval()
        
        # Check where the model actually ended up
        actual_device = next(self.model.parameters()).device
        print(f"✅ Model loaded on {actual_device}")
        
        # Create bad tokens to suppress
        self._create_bad_tokens_ids()

    def _create_bad_tokens_ids(self):
        """Create a list of token IDs to suppress during generation."""
        # Common corrupted characters that appear instead of JSON syntax
        bad_chars = ['ä', 'å', 'Ä', 'Å', 'é', 'Ö', 'ü', 'ß', 'ö', 'ë', 'ï', 'ÿ']
        self.bad_token_ids = []
        
        for char in bad_chars:
            try:
                # Get token IDs for these characters
                token_ids = self.tokenizer.encode(char, add_special_tokens=False)
                self.bad_token_ids.extend(token_ids)
            except:
                pass
        
        # Remove duplicates
        self.bad_token_ids = list(set(self.bad_token_ids))
        if self.bad_token_ids:
            print(f"🚫 Suppressing {len(self.bad_token_ids)} problematic tokens")

    def _truncate_to_token_limit(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        # Suppress warnings about sequence length since we're truncating
        import warnings
        import logging
        # Suppress both warnings and transformers logging
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            # Temporarily suppress transformers logging
            transformers_logger = logging.getLogger("transformers.tokenization_utils_base")
            original_level = transformers_logger.level
            transformers_logger.setLevel(logging.ERROR)
            try:
                tokens = self.tokenizer.encode(text, add_special_tokens=False)
            finally:
                transformers_logger.setLevel(original_level)
                
        if len(tokens) <= max_tokens:
            return text

        # Truncate and decode back to text
        truncated_tokens = tokens[:max_tokens]
        return self.tokenizer.decode(truncated_tokens, skip_special_tokens=True)

    def _clean_corrupted_json(self, text: str) -> str:
        """Clean up corrupted JSON characters that some models produce."""
        # Fix common corrupted characters with extended mapping
        char_map = {
            'ä': '{',
            'å': '}',
            'Ä': '[',
            'Å': ']',
            'é': '"',
            'É': '"',
            'è': '"',
            'È': '"',
            'Ö': '/',
            'ö': '/',
            'ü': ':',
            'Ü': ':',
            'ß': ',',
            '«': '"',
            '»': '"',
            '„': '"',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '‚': "'",
            '—': '-',
            '–': '-',
            '…': '...',
            '\u200b': '',  # Zero-width space
            '\ufeff': '',  # Zero-width no-break space
        }
        
        cleaned = text
        for corrupt_char, correct_char in char_map.items():
            cleaned = cleaned.replace(corrupt_char, correct_char)
        
        # Fix Windows-specific encoding issues
        try:
            # Try to decode and re-encode to fix encoding issues
            cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        except:
            pass
        
        # Remove any remaining non-ASCII characters that aren't standard JSON
        # But preserve Unicode within string values
        if '"' in cleaned:
            # Split by quotes to preserve content within strings
            parts = cleaned.split('"')
            for i in range(0, len(parts), 2):  # Only clean outside of strings
                parts[i] = re.sub(r'[^\x00-\x7F]+', '', parts[i])
            cleaned = '"'.join(parts)
        else:
            # No strings, clean everything
            cleaned = re.sub(r'[^\x00-\x7F]+', '', cleaned)
        
        return cleaned

    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON from response that may contain <think> tags."""
        # Remove <think> tags if present
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        
        # Clean up any remaining whitespace
        cleaned_text = cleaned_text.strip()
        
        # Clean corrupted characters
        cleaned_text = self._clean_corrupted_json(cleaned_text)
        
        # If there are still issues, try to find JSON within the text
        if cleaned_text.startswith('{') and cleaned_text.endswith('}'):
            return cleaned_text
        
        # Try to find JSON object in the text
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return cleaned_text

    def _is_json_complete(self, text: str) -> bool:
        """Check if the text after <think> tags contains a complete JSON object."""
        # Remove <think> tags if present
        cleaned_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        cleaned_text = cleaned_text.strip()
        
        if not cleaned_text:
            return False
        
        # Clean corrupted characters first
        cleaned_text = self._clean_corrupted_json(cleaned_text)
        
        # Try to parse as JSON to see if it's complete
        try:
            json.loads(cleaned_text)
            return True
        except json.JSONDecodeError:
            return False

    def generate_review(
        self, diff: str, context: Iterable[Chunk], max_tokens: int = 2048
    ) -> dict:
        """Return a structured JSON review for *diff* and *context*."""
        # Debug: Check raw input sizes
        # Suppress the warning about sequence length since we're going to truncate anyway
        import warnings
        import logging
        
        # Set Windows console to UTF-8 mode
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            # Temporarily suppress transformers logging
            transformers_logger = logging.getLogger("transformers.tokenization_utils_base")
            original_level = transformers_logger.level
            transformers_logger.setLevel(logging.ERROR)
            try:
                diff_tokens_raw = len(self.tokenizer.encode(diff, add_special_tokens=False))
            finally:
                transformers_logger.setLevel(original_level)
            
        print(f"📊 Raw diff size: {diff_tokens_raw:,} tokens")
        if diff_tokens_raw > 50000:
            print(f"⚠️  This is a very large diff! Consider breaking it into smaller PRs for better reviews.")
        
        # Reserve tokens for the prompt structure and generation
        reserved_tokens = (
            max_tokens + 1000
        )  # Extra buffer for prompt formatting
        # Limit the total prompt size to avoid extremely slow first-token latency on CPU-only setups.
        MAX_PROMPT_TOKENS = 8192  # Reasonable upper bound for fast generation
        available_tokens = min(self.max_model_tokens - reserved_tokens, MAX_PROMPT_TOKENS)

        # Allocate tokens between diff and context (70% diff, 30% context)
        diff_token_budget = int(available_tokens * 0.7)
        context_token_budget = int(available_tokens * 0.3)

        # Truncate diff if needed
        diff_truncated = self._truncate_to_token_limit(diff, diff_token_budget)
        if (
            len(self.tokenizer.encode(diff, add_special_tokens=False))
            > diff_token_budget
        ):
            print(
                f"⚠️  Diff truncated to fit token limit ({diff_token_budget} tokens)"
            )

        # Build context with token budget
        ctx_blocks: List[str] = []
        context_so_far = ""

        for c in context:
            block = f"### {c.file_path}:{c.start_line}-{c.end_line}\n{c.text}\n"
            test_context = context_so_far + block

            # Check if adding this block would exceed budget
            if (
                len(
                    self.tokenizer.encode(
                        test_context, add_special_tokens=False
                    )
                )
                > context_token_budget
            ):
                if ctx_blocks:  # We have at least some context
                    print(
                        f"⚠️  Context truncated to fit token limit (included {len(ctx_blocks)} chunks)"
                    )
                    break
                else:  # Even the first chunk is too big, truncate it
                    truncated_text = self._truncate_to_token_limit(
                        c.text, context_token_budget - 100
                    )
                    ctx_blocks.append(
                        f"### {c.file_path}:{c.start_line}-{c.end_line}\n{truncated_text}"
                    )
                    print(
                        f"⚠️  First context chunk truncated to fit token limit"
                    )
                    break

            ctx_blocks.append(block)
            context_so_far = test_context

        # Build the prompt with explicit JSON formatting requirements
        # Build messages using Qwen3's expected format
        system_message = """You are a precise code reviewer bot. Analyze the PR diff and context.

First, think through your analysis in <think> tags, then provide a JSON response.

CRITICAL RULES:
1. Use ONLY standard ASCII characters in your JSON output
2. Use double quotes " for all strings - NEVER use single quotes or special quotes
3. Use standard brackets { } [ ] - NEVER use accented characters
4. NO Unicode or special characters outside of string values
5. Escape any special characters within strings properly

JSON Format:
{
  "summary": "1-2 sentence summary",
  "actionable_comments": [
    {
      "line_range": "start-end",
      "comment": "Issue with fix",
      "suggested_fix": "Code suggestion"
    }
  ],
  "nitpick_comments": [
    {
      "line_range": "start-end",
      "comment": "Minor suggestion"
    }
  ]
}

Review based on diff and context. Max 5 actionable, max 3 nitpicks.
Format: <think>analysis</think> then clean JSON only."""

        user_message = f"""Review this PR:

Diff:
{diff_truncated}

Context:
{"".join(ctx_blocks)}

Output valid JSON with ASCII characters only."""

        # Use the tokenizer's chat template
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        print(f"📝 Using Qwen3 chat template format")

        # Verify total size
        # When using apply_chat_template, tokens are already properly formatted
        total_tokens = len(self.tokenizer.encode(prompt, add_special_tokens=False))
        print(f"📊 Total prompt tokens: {total_tokens} (limit: {MAX_PROMPT_TOKENS})")
        
        if total_tokens > MAX_PROMPT_TOKENS:
            print(
                f"❌ Error: Even after truncation, prompt is too long ({total_tokens} tokens)"
            )
            error_review = {
                "summary": f"Error: Prompt too large ({total_tokens} tokens > {MAX_PROMPT_TOKENS} limit)",
                "actionable_comments": [],
                "nitpick_comments": [],
            }
            
            # Save the error review to .output/review.json
            output_dir = Path(".output")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / "review.json"
            
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(error_review, f, indent=2, ensure_ascii=True)
            
            print(f"💾 Error review saved to {output_file}")
            
            return error_review

        # Tokenize with the formatted prompt
        inputs = self.tokenizer(prompt, return_tensors="pt", add_special_tokens=False)

        # Move inputs to the same device as the model
        # When using device_map="auto", the model handles device placement automatically
        # but we still need to move inputs to the correct device
        model_device = next(self.model.parameters()).device
        inputs = {k: v.to(model_device) for k, v in inputs.items()}

        for attempt in range(2):
            # Set up streaming with clean decoding
            streamer = TextIteratorStreamer(
                self.tokenizer,
                skip_prompt=True,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
                timeout=0.5,  # Allow __next__ to raise queue.Empty periodically
            )
            
            # Generate in a separate thread so we can stream the output
            generation_kwargs = {
                **inputs,
                "max_new_tokens": max_tokens,
                "do_sample": False,
                "streamer": streamer,
                "pad_token_id": self.tokenizer.eos_token_id,
                "bad_words_ids": [[token_id] for token_id in self.bad_token_ids] if hasattr(self, 'bad_token_ids') else None,
                "repetition_penalty": 1.05,  # Slight penalty to avoid loops
                "length_penalty": 1.0,  # No length penalty
                "use_cache": True,  # Enable KV cache for efficiency
                "forced_decoder_ids": None,  # Don't force any specific tokens
            }
            
            thread = threading.Thread(
                target=self.model.generate, kwargs=generation_kwargs
            )
            thread.start()
            
            # Stream the output and collect it
            print("🤖 Generating review...")
            generated_text = ""
            # Iterate over streamer with a heartbeat so the user sees progress even before first tokens
            while True:
                try:
                    # Attempt to get next token (TextIteratorStreamer blocks internally with its own timeout)
                    new_text = next(streamer)
                    # Clean the text before printing
                    clean_text = self._clean_corrupted_json(new_text)
                    print(clean_text, end="", flush=True)
                    generated_text += clean_text
                    
                    # Check if we have a complete JSON response
                    if self._is_json_complete(generated_text):
                        print("\n✅ Complete JSON detected, stopping generation early")
                        break
                        
                except StopIteration:
                    break
                except queue.Empty:
                    # In rare cases we may hit a queue timeout before tokens start streaming.
                    if thread.is_alive():
                        print(".", end="", flush=True)
                        time.sleep(1)
                        continue
                    else:
                        break
            
            # Wait for generation to complete
            thread.join()
            print("\n")  # Add newline after streaming
            
            text = generated_text.strip()
            print(f"🔍 Generated {len(text)} characters, {len(text.split())} words")
            
            # Check for corrupted characters
            corrupted_chars = ['ä', 'å', 'Ä', 'Å', 'é', 'Ö', 'ü', 'ß']
            found_corrupted = [c for c in corrupted_chars if c in text]
            if found_corrupted:
                print(f"⚠️  Found corrupted characters: {found_corrupted}")
                print("🔧 Cleaning corrupted JSON...")
            
            # Debug: Check if we have thinking tags
            if "<think>" in text:
                think_end = text.find("</think>")
                if think_end != -1:
                    think_content = text[:think_end + 8]  # Include </think>
                    json_content = text[think_end + 8:].strip()
                    print(f"🧠 Think section: {len(think_content)} chars")
                    print(f"📝 JSON section: {len(json_content)} chars")
                    if not json_content:
                        print("⚠️  No JSON content after think section!")
                else:
                    print("⚠️  Found <think> but no </think> - incomplete thinking?")

            # Extract JSON from response (removing <think> tags and fixing corruption)
            json_text = self._extract_json_from_response(text)
            
            try:
                review_data = json.loads(json_text)
                
                # Save the review to .output/review.json
                output_dir = Path(".output")
                output_dir.mkdir(exist_ok=True)
                output_file = output_dir / "review.json"
                
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(review_data, f, indent=2, ensure_ascii=True)
                
                print(f"💾 Review saved to {output_file}")
                
                return review_data
            except json.JSONDecodeError as e:
                if attempt == 0:
                    print(f"⚠️  JSON decode error: {e}")
                    print("⚠️  Generated invalid JSON, retrying once")
                    print(f"    Raw response: {text[:200]}...")
                    print(f"    Cleaned JSON: {json_text[:200]}...")
                    continue
                print("❌ Error parsing JSON after retry")
                print(f"    Final cleaned JSON: {json_text[:500]}...")

        error_review = {
            "summary": "Error generating valid JSON review",
            "actionable_comments": [],
            "nitpick_comments": [],
        }
        
        # Save the error review to .output/review.json
        output_dir = Path(".output")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "review.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(error_review, f, indent=2, ensure_ascii=True)
        
        print(f"💾 Error review saved to {output_file}")
        
        return error_review


__all__ = ["Qwen3Model"]
