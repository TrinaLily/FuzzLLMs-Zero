# 🌌️FuzzLLMs-Zero


This repository contains the source code for our paper <i> "FuzzLLMs-Zero: Fuzzing oriented LLMs Learning with Syntactical and Reasoning Fine-tuning" </i>

## 🌌️ About



## ⚡ Quick Start

First, create the corresponding environment and install the required packages

```bash
conda create -n FuzzLLMs-Zero python=3.10
conda activate FuzzLLMs-Zero

pip install -r requirements.txt
```

Next, build the target compiler environment and configure your experiment:

### Build Compiler Environment

After installing the virtual environment and dependencies, you need to build the corresponding compiler environment before running fuzzing tests. For example, to build GCC:

```bash
# Build GCC compiler with coverage support
cd FuzzLLMs-Zero/build_script
chmod +x gcc_build.sh
./gcc_build.sh
```

### Configure Your Experiment

Create or modify the `config.yaml` file to specify your experiment parameters:

```yaml
# Example: config/gcc_config.yaml
target: gcc                    # Target compiler (gcc, g++, java, etc.)
work_dir: gcc_output          # Output directory for results
model_name: "Qwen/Qwen2.5-Coder-7B-Instruct"  # LLM model name
temperature: 1.0              # Sampling temperature (0.0-2.0)
max_length: 512               # Maximum generation length
batch_size: 8                 # Batch size for generation
time_budget: 7200             # Time budget in seconds (2 hours)
coverage_interval_seconds: 3600  # Coverage collection interval (1 hour)
```

**Key Parameters:**
- `target`: Specifies which compiler to fuzz (must match your target directory)
- `model_name`: Hugging Face model identifier for code generation
- `time_budget`: Total experiment duration in seconds
- `coverage_interval_seconds`: How often to collect coverage metrics

### Run Fuzzing Experiments

After the build is complete and configuration is ready, you can start fuzzing experiments:

```bash
# Run fuzzing experiment with single GPU
python fuzz.py config/gcc_config.yaml --gpu 0

# Run fuzzing experiment with multiple GPUs
python fuzz.py config/gcc_config.yaml --gpu 1,2,3,4
```


## 🔧 Extension Guide

If you want to add support for other compilers, you can extend the framework by following these steps:

### Adding a New Compiler

1. **Create compiler directory structure**:
   ```bash
   mkdir -p target/your_compiler
   ```

2. **Add required scripts**:
   - `target/your_compiler/compile.sh` - Compilation script
   - `target/your_compiler/coverage.sh` - Coverage collection script

3. **Update COMPILER_INFO in fuzz.py** (see Configuration section below)

### Script Requirements

#### `compile.sh` Script
This script should accept two arguments and compile the source code:
```bash
#!/usr/bin/env bash
# Usage: $0 <work_dir> <source_file>

WORK_DIR="$1"
SOURCE_FILE="$2"

# Your compilation logic here
# - Compile the source file
# - Generate coverage data if needed
# - Return appropriate exit code
```

#### `coverage.sh` Script
This script should accept one argument and return coverage metrics:
```bash
#!/usr/bin/env bash
# Usage: $0 <work_dir>

WORK_DIR="$1"

# Your coverage collection logic here
# - Collect coverage data
# - Calculate coverage metrics
# - Output only the coverage number (e.g., "1234")
```

### Example Implementation

For reference, see the existing implementations:
- `target/gcc/` - GCC C compiler support
- `target/g++/` - GCC C++ compiler support  
- `target/java/` - Java compiler support

### Configuration

After adding your compiler scripts, you need to update the `COMPILER_INFO` in `fuzz.py` and create a corresponding config file:


Add your compiler information to the `COMPILER_INFO` dictionary:
```python
COMPILER_INFO = {
    "java": {"ext": ".java", "lang": "java"},
    "gcc": {"ext": ".c", "lang": "c"},
    "clang": {"ext": ".c", "lang": "c"},
    "g++": {"ext": ".cpp", "lang": "cpp"},
    "go": {"ext": ".go", "lang": "go"},
    "jerryscript": {"ext": ".js", "lang": "javascript"},
    "your_compiler": {"ext": ".your_ext", "lang": "your_language"}  # Add your compiler here
}
```


