#!/usr/bin/env python3
import argparse
import yaml
import time
import subprocess
import shutil
from pathlib import Path
from llm_model import LLMGenerator
from tqdm import tqdm

# 编译器到文件扩展名和编程语言的映射
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
    将秒数格式化为 XhYminZs、YminZs 或 Zs。
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
    """清理编译器覆盖率数据，确保每次实验从零开始"""
    try:
        # 获取项目根目录
        script_dir = Path(__file__).parent
        project_root = script_dir
        
        # 根据编译器类型确定覆盖率目录
        if target_compiler in ["gcc", "g++"]:
            coverage_dir = project_root / "target" / target_compiler / "gcc-coverage-build" / "gcc"
            
            if coverage_dir.exists():
                # 使用find命令清理.gcda和coverage.info文件
                cmd = f"find {coverage_dir} \\( -name \"*.gcda\" -o -name \"coverage.info\" \\) -type f -delete"
                returncode, stdout, stderr = run_cmd(cmd, project_root)
                
                if returncode == 0:
                    print(f"[INFO] 已清理{target_compiler}编译器覆盖率数据: {coverage_dir}")
                else:
                    print(f"[WARN] 清理{target_compiler}编译器覆盖率数据失败: {stderr}")
            else:
                print(f"[WARN] {target_compiler}编译器覆盖率目录不存在: {coverage_dir}")
        else:
            print(f"[INFO] 编译器{target_compiler}不需要清理覆盖率数据")
            
    except Exception as e:
        print(f"[ERROR] 清理编译器覆盖率数据时发生错误: {e}")

def generate_fuzzing_inputs(generator, target_compiler, codes_dir, gen_log, time_budget):
    """
    生成模糊测试输入

    Args:
        generator: LLM生成器实例
        target_compiler: 目标编译器名称
        codes_dir: 代码输出目录
        gen_log: 生成日志文件路径
        time_budget: 时间预算

    Returns:
        tuple: (llm_calls, valid_codes)
    """
    # 获取目标语言和文件扩展名
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

        # 根据目标语言生成代码
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
    编译源文件模块
    
    Args:
        target_compiler: 目标编译器名称
        work_dir: 工作目录路径
        crashes_dir: 崩溃文件目录
        comp_log: 编译日志文件路径
        batch_id: 批次ID
        batch_files: 源文件列表（该批次内的所有文件）
    
    Returns:
        bool: 是否所有文件都编译成功
    """
    print(f"\n=== Batch {batch_id}: {len(batch_files)} cases ===")
    
    # 获取编译脚本路径
    compile_script = Path(__file__).parent / "target" / target_compiler / "compiler.sh"
    
    if not compile_script.exists():
        print(f"Error: Compile script not found: {compile_script}")
        return False
    
    # 确保脚本有执行权限
    if not compile_script.stat().st_mode & 0o111:
        print(f"Warning: Compile script lacks execute permission: {compile_script}")
    
    all_success = True
    
    for src in batch_files:
        print(f"Compiling: {src.name}")
        
        # 调用编译脚本
        # 输入: work_dir, 源文件完整路径
        # 输出: 编译结果 (return_code, stdout, stderr)
        ret, out, err = run_cmd(
            ["bash", str(compile_script), str(work_dir), str(src)],  # 传递完整路径
            cwd=compile_script.parent  # 在脚本所在目录执行
        )
           
        if ret != 0:
            # 编译失败，记录详细信息
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
            
            
            # 保存源代码
            crash_src_file = crashes_dir / f"crash_{batch_id}_{src.name}"
            shutil.copy2(src, crash_src_file)
            
            # 保存编译错误信息
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
            # 编译成功，记录状态
            append_log(comp_log, f"{batch_id},{src.name},OK")
    
    return all_success


def collect_coverage(target_compiler, work_dir, cov_log, batch_id, coverage_interval_seconds, time_budget):
    """
    收集代码覆盖率
    
    Args:
        target_compiler: 目标编译器名称
        work_dir: 工作目录路径
        codes_dir: 代码目录
        cov_log: 覆盖率日志文件路径
        batch_id: 批次ID
        coverage_interval_seconds: 每批等价的时间间隔（秒）
        time_budget: 时间预算（秒）
    
    Returns:
        bool: 覆盖率收集是否成功
    """
    # 获取覆盖率收集脚本路径
    coverage_script = Path(__file__).parent / "target" / target_compiler / "coverage.sh"
    
    if not coverage_script.exists():
        print(f"Error: Coverage script not found: {coverage_script}")
        return False
    
    # 确保脚本有执行权限
    if not coverage_script.stat().st_mode & 0o111:
        print(f"Warning: Coverage script lacks execute permission: {coverage_script}")
    
    # 调用覆盖率收集脚本
    # 输入: work_dir参数
    # 输出: 覆盖率数据 (return_code, stdout, stderr)
    ret, out, err = run_cmd(
        ["bash", str(coverage_script), str(work_dir)],
        cwd=coverage_script.parent  # 在脚本所在目录执行
    )
    
    if ret == 0:
        try:
            # 解析覆盖率输出
            covered = out.strip()
            # 使用批次号 * 覆盖率间隔秒数 作为时间记录（时分秒显示）
            # 但不超过时间预算
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
    
    # 解析GPU参数
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

    # 创建所有需要的目录
    for d in (codes_dir, coverage_dir, crashes_dir, logs_dir):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    
    # 创建日志文件
    for logf in (gen_log, comp_log, cov_log):
        logf.parent.mkdir(parents=True, exist_ok=True)
        logf.write_text("", encoding="utf-8")

    # 清理编译器覆盖率数据（如果是gcc/g++编译器）
    clean_compiler_coverage(target_compiler)

    # fuzzing inputs generator
    generator = LLMGenerator(
        model_name=model_name,
        temperature=temperature,
        max_length=max_length,
        batch_size=batch_size,
        gpu_devices=gpu_devices
    )

    # 记录实验开始时间
    experiment_start_time = time.time()

    # 先进行生成阶段，生成完毕后再编译
    llm_calls, valid = generate_fuzzing_inputs(generator, target_compiler, codes_dir, gen_log, time_budget)

    # 将生成的文件按coverage_interval_seconds分批
    file_extension = COMPILER_INFO.get(target_compiler, {"ext": ".java"})["ext"]
    files = sorted(codes_dir.glob(f"case_*{file_extension}"))

    # 基于文件生成时间分批：每 coverage_interval_seconds 为一批
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
        # 编译该批次
        compile_source_files(target_compiler, work_dir, crashes_dir, comp_log, batch_id, batch_files)

        # 每个批次后收集一次覆盖率
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
