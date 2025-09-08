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
        
        # 确保tokenizer有pad_token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # 设置CUDA可见设备，统一处理单GPU和多GPU情况
        
        os.environ["CUDA_VISIBLE_DEVICES"] = ",".join(map(str, gpu_devices))
        self.device = "cuda:0"  # 在可见设备中，第一个设备总是0
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",  # 自动分布到可见的GPU
            torch_dtype=torch.bfloat16,
        ).eval()
        
        self.temperature = temperature
        self.max_length = max_length
        self.batch_size = batch_size
    
    def extract_code(self, completion):
        """提取代码"""
        match = re.search(r"<code>(.+?)</code>", completion, flags=re.DOTALL)
        if match:
            code = match.group(1).strip()
            code = code.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            return code
        return None

    def generate(self, prompt: str) -> str:
        # 让tokenizer自动处理padding和attention_mask
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
