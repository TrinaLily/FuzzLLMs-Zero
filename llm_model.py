# model.py
from typing import List, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import re
import os

class LLMGenerator:
    def __init__(self, 
                model_name: str = "",
                temperature: float = 1,
                max_length: int = 512,
                batch_size: int = 8,
                gpu_devices: List[int] = None):
        if gpu_devices is None:
            gpu_devices = [0]
        
        self.gpu_devices = gpu_devices
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Set CUDA visible devices to handle both single and multi-GPU scenarios uniformly
        
        os.environ["CUDA_VISIBLE_DEVICES"] = ",".join(map(str, gpu_devices))
        self.device = "cuda:0"  # In visible devices, the first device is always 0
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",  # Automatically distribute to visible GPUs
            torch_dtype=torch.bfloat16,
        ).eval()
        
        self.temperature = temperature
        self.max_length = max_length
        self.batch_size = batch_size
    
    def extract_code(self, completion):
        """Extract code from completion"""
        match = re.search(r"<code>(.+?)</code>", completion, flags=re.DOTALL)
        if match:
            code = match.group(1).strip()
            code = code.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            return code
        return None

    def generate(self, prompt: str) -> str:
        # Let tokenizer automatically handle padding and attention_mask
        inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                temperature=self.temperature,
                max_length=self.max_length,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id
            )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)[len(prompt):]
        
        code = self.extract_code(response)
        
        return code
