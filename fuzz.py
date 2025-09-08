#!/usr/bin/env python3
import argparse
import yaml
import time
import subprocess
import shutil
from pathlib import Path
from llm_model import LLMGenerator
from tqdm import tqdm

# Mapping from compiler to file extension and programming language
COMPILER_INFO = {
    "java": {"ext": ".java", "lang": "java"},
    "gcc": {"ext": ".c", "lang": "c"},
    "clang": {"ext": ".c", "lang": "c"},
    "g++": {"ext": ".cpp", "lang": "cpp"},
    "go": {"ext": ".go", "lang": "go"},
    "jerryscript": {"ext": ".js", "lang": "javascript"}
}

def append_log(path: Path, line: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")

def format_hms(total_seconds: int) -> str:
    """
    Format seconds as XhYminZs, YminZs, or Zs.
    """
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours}h{minutes}min{seconds}s"
    if minutes > 0:
        return f"{minutes}min{seconds}s"
    return f"{seconds}s"

def run_cmd(cmd, cwd: Path):
    proc = subprocess.run(cmd, cwd=str(cwd),
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          text=True)
    return proc.returncode, proc.stdout, proc.stderr

def clean_compiler_coverage(target_compiler):
    """Clean compiler coverage data to ensure each experiment starts from zero"""
    try:
        # Get project root directory
        script_dir = Path(__file__).parent
        project_root = script_dir
        
        # Determine coverage directory based on compiler type
        if target_compiler in ["gcc", "g++"]:
            coverage_dir = project_root / "target" / target_compiler / "gcc-coverage-build" / "gcc"
            
            if coverage_dir.exists():
                # Use find command to clean .gcda and coverage.info files
                cmd = f"find {coverage_dir} \\( -name \"*.gcda\" -o -name \"coverage.info\" \\) -type f -delete"
                returncode, stdout, stderr = run_cmd(cmd, project_root)
                
                if returncode == 0:
                    print(f"[INFO] Cleaned {target_compiler} compiler coverage data: {coverage_dir}")
                else:
                    print(f"[WARN] Failed to clean {target_compiler} compiler coverage data: {stderr}")
            else:
                print(f"[WARN] {target_compiler} compiler coverage directory does not exist: {coverage_dir}")
        else:
            print(f"[INFO] Compiler {target_compiler} does not need coverage data cleanup")
            
    except Exception as e:
        print(f"[ERROR] Error occurred while cleaning compiler coverage data: {e}")

def generate_fuzzing_inputs(generator, target_compiler, codes_dir, gen_log, time_budget):
    """
    Generate fuzzing inputs

    Args:
        generator: LLM generator instance
        target_compiler: Target compiler name
        codes_dir: Code output directory
        gen_log: Generation log file path
        time_budget: Time budget

    Returns:
        tuple: (llm_calls, valid_codes)
    """
    # Get target language and file extension
    compiler_info = COMPILER_INFO.get(target_compiler, {"ext": ".java", "lang": "java"})
    target_language = compiler_info["lang"]
    file_extension = compiler_info["ext"]

    llm_calls = 0
    valid = 0
    start = time.time()
    append_log(gen_log, f"llm_calls,valid")
    pbar_gen = tqdm(unit="call", desc=f"Generate {target_compiler}", leave=True)

    while True:
        if time.time() - start >= time_budget:
            break
        llm_calls += 1

        # Generate code based on target language
        prompt = "Generate a "+ target_language + " code snippet that can trigger compiler crash.Strictly use the format of:<think>the content of the thinking</think><code>content code</code>"
        code = generator.generate(prompt) or ""
        pbar_gen.update(1)

        if code.strip():
            valid += 1
            fname = f"case_{valid}{file_extension}"
            (codes_dir / fname).write_text(code, encoding="utf-8")
            append_log(gen_log, f"{llm_calls},{valid},{fname}")

    pbar_gen.close()
    append_log(gen_log, f"Generated calls: {llm_calls},valid codes: {valid}")
    append_log(gen_log, f"valid rate: {valid/llm_calls:.2%}")

    return llm_calls, valid


def compile_source_files(target_compiler, work_dir, crashes_dir, comp_log, batch_id, batch_files):
    """
    Compile source files module
    
    Args:
        target_compiler: Target compiler name
        work_dir: Working directory path
        crashes_dir: Crash files directory
        comp_log: Compilation log file path
        batch_id: Batch ID
        batch_files: Source file list (all files in this batch)
    
    Returns:
        bool: Whether all files compiled successfully
    """
    print(f"\n=== Batch {batch_id}: {len(batch_files)} cases ===")
    
    # Get compilation script path
    compile_script = Path(__file__).parent / "target" / target_compiler / "compiler.sh"
    
    if not compile_script.exists():
        print(f"Error: Compile script not found: {compile_script}")
        return False
    
    # Ensure script has execute permission
    if not compile_script.stat().st_mode & 0o111:
        print(f"Warning: Compile script lacks execute permission: {compile_script}")
    
    all_success = True
    
    for src in batch_files:
        print(f"Compiling: {src.name}")
        
        # Call compilation script
        # Input: work_dir, complete source file path
        # Output: compilation result (return_code, stdout, stderr)
        ret, out, err = run_cmd(
            ["bash", str(compile_script), str(work_dir), str(src)],  # Pass complete path
            cwd=compile_script.parent  # Execute in script directory
        )
           
        if ret != 0:
            # Compilation failed, record detailed information
            all_success = False
            log_entry = [
                f"--- FAIL batch {batch_id}: {src.name} (exit {ret}) ---",
                "=== STDOUT ===",
                out.strip(),
                "=== STDERR ===",
                err.strip(),
                "==================================================================",
                ""
            ]
            append_log(comp_log, "\n".join(log_entry))
            
            
            # Save source code
            crash_src_file = crashes_dir / f"crash_{batch_id}_{src.name}"
            shutil.copy2(src, crash_src_file)
            
            # Save compilation error information
            crash_log_file = crashes_dir / f"crash_{batch_id}_{src.stem}.log"
            crash_info = [
                f"Compilation failed for: {src.name}",
                f"Batch ID: {batch_id}",
                f"Exit code: {ret}",
                f"Time: -",
                "",
                "=== STDOUT ===",
                out.strip(),
                "",
                "=== STDERR ===",
                err.strip()
            ]
            crash_log_file.write_text("\n".join(crash_info), encoding="utf-8")
            
            print(f"Crash case saved: {crash_src_file}")
            print(f"Crash log saved: {crash_log_file}")
        else:
            # Compilation successful, record status
            append_log(comp_log, f"{batch_id},{src.name},OK")
    
    return all_success


def collect_coverage(target_compiler, work_dir, cov_log, batch_id, coverage_interval_seconds, time_budget):
    """
    Collect code coverage
    
    Args:
        target_compiler: Target compiler name
        work_dir: Working directory path
        codes_dir: Code directory
        cov_log: Coverage log file path
        batch_id: Batch ID
        coverage_interval_seconds: Time interval per batch (seconds)
        time_budget: Time budget (seconds)
    
    Returns:
        bool: Whether coverage collection was successful
    """
    # Get coverage collection script path
    coverage_script = Path(__file__).parent / "target" / target_compiler / "coverage.sh"
    
    if not coverage_script.exists():
        print(f"Error: Coverage script not found: {coverage_script}")
        return False
    
    # Ensure script has execute permission
    if not coverage_script.stat().st_mode & 0o111:
        print(f"Warning: Coverage script lacks execute permission: {coverage_script}")
    
    # Call coverage collection script
    # Input: work_dir parameter
    # Output: coverage data (return_code, stdout, stderr)
    ret, out, err = run_cmd(
        ["bash", str(coverage_script), str(work_dir)],
        cwd=coverage_script.parent  # Execute in script directory
    )
    
    if ret == 0:
        try:
            # Parse coverage output
            covered = out.strip()
            # Use batch number * coverage interval seconds as time record (HH:MM:SS format)
            # but not exceeding time budget
            elapsed_seconds = min(batch_id * int(coverage_interval_seconds), int(time_budget))
            elapsed_hms = format_hms(elapsed_seconds)
            append_log(cov_log, f"{elapsed_hms},{covered}")
            
            return True
            
        except ValueError as e:
            print(f"Error parsing coverage output: {e}")
            print(f"Raw output: {out.strip()}")
            return False
    else:
        print(f"[!] Coverage failed on batch {batch_id}:\n{err}")
        return False

def main():
    # Parsing config.yaml
    p = argparse.ArgumentParser()
    p.add_argument("config", help="Path to config.yaml")
    p.add_argument("--gpu", type=str, default="0", help="GPU devices to use, e.g., '0' or '0,1,2,3'")
    args = p.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))

    target_compiler = cfg["target"]
    work_dir        = Path(cfg["work_dir"]).expanduser().resolve()
    model_name      = cfg["model_name"]
    temperature     = cfg["temperature"]
    max_length      = cfg["max_length"]
    batch_size      = cfg["batch_size"]
    time_budget     = cfg["time_budget"]
    
    coverage_interval_seconds = int(cfg.get("coverage_interval_seconds", 3600))
    
    # Parse GPU parameters
    gpu_devices = [int(x.strip()) for x in args.gpu.split(",")]

    # Initialize the working directory
    if work_dir.exists():
        print(" Error: work_dir exists")
        return 0

    codes_dir    = work_dir / "codes"
    coverage_dir = work_dir / "coverage"
    crashes_dir = work_dir / "crashes"
    logs_dir     = work_dir / "logs"
    gen_log      = logs_dir / "generation.log"
    comp_log     = logs_dir / "compiler.log"
    cov_log      = logs_dir / "coverage.log"

    # Create all required directories
    for d in (codes_dir, coverage_dir, crashes_dir, logs_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    
    # Create log files
    for logf in (gen_log, comp_log, cov_log):
        logf.parent.mkdir(parents=True, exist_ok=True)
        logf.write_text("", encoding="utf-8")

    # Clean compiler coverage data (if gcc/g++ compiler)
    clean_compiler_coverage(target_compiler)

    # fuzzing inputs generator
    generator = LLMGenerator(
        model_name=model_name,
        temperature=temperature,
        max_length=max_length,
        batch_size=batch_size,
        gpu_devices=gpu_devices
    )

    # Record experiment start time
    experiment_start_time = time.time()

    # First perform generation phase, then compile after generation is complete
    llm_calls, valid = generate_fuzzing_inputs(generator, target_compiler, codes_dir, gen_log, time_budget)

    # Batch generated files by coverage_interval_seconds
    file_extension = COMPILER_INFO.get(target_compiler, {"ext": ".java"})["ext"]
    files = sorted(codes_dir.glob(f"case_*{file_extension}"))

    # Batch based on file generation time: one batch per coverage_interval_seconds
    files = sorted(files, key=lambda p: p.stat().st_mtime)
    batches_dict = {}
    for f in files:
        elapsed = int(max(0, f.stat().st_mtime - experiment_start_time))
        batch_key = elapsed // coverage_interval_seconds
        batches_dict.setdefault(batch_key, []).append(f)
    batches = [batches_dict[k] for k in sorted(batches_dict.keys())]

    pbar_cc = tqdm(total=len(batches), unit="batch", desc="Compile & Cover", leave=True)
    
    append_log(cov_log, f"run_time, coverage")

    for batch_id, batch_files in enumerate(batches, start=1):
        # Compile this batch
        compile_source_files(target_compiler, work_dir, crashes_dir, comp_log, batch_id, batch_files)

        # Collect coverage once after each batch
        collect_coverage(target_compiler, work_dir, cov_log, batch_id, coverage_interval_seconds, time_budget)

        pbar_cc.update(1)

    pbar_cc.close()
    print("\nAll done.")
    print(f"Generated calls: {llm_calls}, valid codes: {valid}")
    print(f"valid rate: {valid/llm_calls:.2%}")
    print(f"Generation log: {gen_log}")
    print(f"Compiler   log: {comp_log}")
    print(f"Crashes   log: {crashes_dir}")
    print(f"Coverage   log: {cov_log}")

if __name__ == "__main__":
    main()
