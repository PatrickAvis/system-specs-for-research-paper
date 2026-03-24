"""
get_specs.py
------------
Collects hardware and software specifications from the current machine and
produces a ready-to-paste paragraph for a research paper (plain text + LaTeX).

Supports: Linux, macOS, Windows 11
Outputs:  specs.txt      – plain-text paragraph
          specs.tex      – LaTeX-safe paragraph (underscores escaped)
          specs_raw.txt  – individual fields, one per line (Key: Value)

Usage:
    python get_specs.py          # Windows
    python3 get_specs.py         # Linux / macOS
"""

import subprocess
import platform
import sys

_SYS = platform.system()
IS_WINDOWS = _SYS == "Windows"
IS_MAC     = _SYS == "Darwin"
IS_LINUX   = _SYS == "Linux"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd):
    """Run a shell command and return stdout, or '' on any error."""
    try:
        return subprocess.check_output(
            cmd, shell=True, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def ps(expression):
    """Evaluate a PowerShell expression and return its output (Windows only)."""
    return run(f'powershell -NoProfile -Command "{expression}"')


def cim(classname, field):
    """
    Query a single field from a CIM/WMI class via PowerShell Get-CimInstance.

    Example:
        cim("Win32_Processor", "Name")  ->  "AMD Ryzen 9 5950X 16-Core Processor"
    """
    out = ps(f"(Get-CimInstance {classname}).{field}")
    return out.strip()


# ---------------------------------------------------------------------------
# OS + Kernel
# ---------------------------------------------------------------------------

if IS_WINDOWS:
    os_name  = cim("Win32_OperatingSystem", "Caption") or f"Windows {platform.release()}"
    os_build = cim("Win32_OperatingSystem", "BuildNumber")
    os_info  = f"{os_name} (Build {os_build})" if os_build else os_name
    kernel   = cim("Win32_OperatingSystem", "Version")   # e.g. "10.0.26100"

elif IS_MAC:
    os_info = run("sw_vers -productName") + " " + run("sw_vers -productVersion")
    kernel  = run("uname -r")

else:  # Linux
    os_info = (
        run("lsb_release -ds")
        or run("grep PRETTY_NAME /etc/os-release | cut -d= -f2").replace('"', "")
    )
    kernel = run("uname -r")


# ---------------------------------------------------------------------------
# CPU
# ---------------------------------------------------------------------------

if IS_WINDOWS:
    cpu_model   = cim("Win32_Processor", "Name")
    cpu_cores   = cim("Win32_Processor", "NumberOfCores")
    logical     = cim("Win32_Processor", "NumberOfLogicalProcessors")
    socket_count = ps("(Get-CimInstance Win32_Processor | Measure-Object).Count")
    # For multi-socket systems, multiply per-socket cores by socket count
    if cpu_cores and socket_count and socket_count.isdigit() and int(socket_count) > 1:
        cpu_cores = str(int(cpu_cores) * int(socket_count))
        logical   = str(int(logical)   * int(socket_count))
    if cpu_cores and logical and int(cpu_cores) > 0:
        cpu_threads_per_core = str(int(logical) // int(cpu_cores))
    else:
        cpu_threads_per_core = ""

elif IS_MAC:
    cpu_model            = run("sysctl -n machdep.cpu.brand_string")
    cpu_cores            = run("sysctl -n hw.physicalcpu")
    logical              = run("sysctl -n hw.logicalcpu")
    if cpu_cores and logical and int(cpu_cores) > 0:
        cpu_threads_per_core = str(int(logical) // int(cpu_cores))
    else:
        cpu_threads_per_core = ""

else:  # Linux — use core(s) per socket × socket count for accuracy on multi-socket hosts
    cpu_model            = run("lscpu | grep 'Model name' | cut -d: -f2").strip()
    cores_per_socket     = run("lscpu | grep '^Core(s) per socket:' | awk '{print $NF}'")
    sockets              = run("lscpu | grep '^Socket(s):' | awk '{print $NF}'")
    cpu_threads_per_core = run("lscpu | grep '^Thread(s) per core:' | awk '{print $NF}'")
    if cores_per_socket and sockets:
        cpu_cores = str(int(cores_per_socket) * int(sockets))
    else:
        cpu_cores = run("lscpu | grep '^CPU(s):' | head -n1 | awk '{print $2}'")


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

if IS_WINDOWS:
    ram_bytes_str = cim("Win32_ComputerSystem", "TotalPhysicalMemory")
    if ram_bytes_str and ram_bytes_str.isdigit():
        ram_gib = int(ram_bytes_str) / (1024 ** 3)
        ram = f"{int(round(ram_gib))}G"
    else:
        ram = ""

elif IS_MAC:
    mem_bytes_str = run("sysctl -n hw.memsize")
    if mem_bytes_str and mem_bytes_str.isdigit():
        ram = f"{int(mem_bytes_str) // (1024 ** 3)}G"
    else:
        ram = ""

else:  # Linux
    ram = run("free -h | awk '/Mem:/ {print $2}'")


# ---------------------------------------------------------------------------
# GPU + CUDA  (NVIDIA via nvidia-smi, AMD via rocm-smi)
# ---------------------------------------------------------------------------

gpu_info     = ""
cuda_version = ""

# NVIDIA is checked first; rocm-smi is only used if nvidia-smi is absent,
# since a machine is unlikely to have both driver stacks active simultaneously.
nvidia_check = run("where nvidia-smi" if IS_WINDOWS else "command -v nvidia-smi")
rocm_check   = run("where rocm-smi"   if IS_WINDOWS else "command -v rocm-smi")

if nvidia_check:
    raw   = run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")
    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    gpu_count = len(lines)

    gpu_dict = {}
    for line in lines:
        gpu_dict[line] = gpu_dict.get(line, 0) + 1
    gpu_parts = [f"{count}x {model}" for model, count in gpu_dict.items()]
    gpu_info  = f"{gpu_count} GPU(s) ({'; '.join(gpu_parts)})"

    nvidia_out = run("nvidia-smi")
    for line in nvidia_out.splitlines():
        if "CUDA Version" in line:
            parts = line.split("CUDA Version:")
            if len(parts) > 1:
                cuda_version = parts[1].strip().split()[0].rstrip("|").strip()
            break

elif rocm_check:
    # rocm-smi --showproductname lists GPU names; --showmeminfo vram gives VRAM
    raw   = run("rocm-smi --showproductname --csv")
    lines = [l.strip() for l in raw.split("\n") if l.strip() and not l.lower().startswith("device")]
    if not lines:
        # fallback: non-CSV path
        raw   = run("rocm-smi --showproductname")
        lines = [l.strip() for l in raw.split("\n") if l.strip() and "GPU" in l]

    gpu_count = len(lines) if lines else 0

    # Try to get VRAM per GPU (in bytes → MiB)
    vram_raw = run("rocm-smi --showmeminfo vram --csv")
    vram_lines = [l.strip() for l in vram_raw.split("\n") if l.strip() and not l.lower().startswith("device")]
    vram_map = {}
    for i, vl in enumerate(vram_lines):
        parts = vl.split(",")
        if len(parts) >= 2 and parts[-1].strip().isdigit():
            vram_mib = int(parts[-1].strip()) // (1024 ** 2)
            vram_map[i] = f"{vram_mib} MiB"

    gpu_parts = []
    for i, line in enumerate(lines):
        name = line.split(",")[-1].strip() if "," in line else line
        vram = f", {vram_map[i]}" if i in vram_map else ""
        gpu_parts.append(f"{name}{vram}")

    # Collapse identical cards
    collapsed = {}
    for p in gpu_parts:
        collapsed[p] = collapsed.get(p, 0) + 1
    gpu_parts_str = "; ".join(
        f"{cnt}x {name}" if cnt > 1 else name for name, cnt in collapsed.items()
    )
    gpu_info = f"{gpu_count} GPU(s) ({gpu_parts_str})" if gpu_count else "no GPU detected"

    # ROCm version
    rocm_ver = run("rocm-smi --version")
    for line in rocm_ver.splitlines():
        if "ROCm" in line or "version" in line.lower():
            cuda_version = ""   # no CUDA on AMD; handled separately below
            break

else:
    # Generic fallback
    if IS_WINDOWS:
        out   = ps("(Get-CimInstance Win32_VideoController).Name")
        gpus  = [l.strip() for l in out.splitlines() if l.strip()]
        gpu_count = len(gpus)
        gpu_info  = f"{gpu_count} GPU(s) detected (non-NVIDIA)" if gpu_count else "no GPU detected"
    elif IS_MAC:
        gpu_info = run("system_profiler SPDisplaysDataType | grep 'Chipset Model' | cut -d: -f2").strip()
        if not gpu_info:
            gpu_info = "GPU info unavailable"
    else:
        count    = run("lspci | grep -i vga | wc -l")
        gpu_info = f"{count} GPU(s) detected (non-NVIDIA)"

# ROCm version string for paragraph (mirrors cuda_version usage)
rocm_version = ""
if rocm_check and not nvidia_check:
    rv = run("rocm-smi --version")
    for line in rv.splitlines():
        parts = line.split()
        for i, p in enumerate(parts):
            if p.lower() in ("version", "rocm") and i + 1 < len(parts):
                rocm_version = parts[i + 1]
                break
        if rocm_version:
            break


# ---------------------------------------------------------------------------
# ML Frameworks  (PyTorch, TensorFlow, JAX)
# ---------------------------------------------------------------------------

def py_import(expr):
    """Evaluate a Python expression in the active interpreter; return '' on failure."""
    return run(f'"{sys.executable}" -c "{expr}"')


torch_version = py_import("import torch; print(torch.__version__)")
torch_cuda    = py_import("import torch; print(torch.version.cuda)")

tf_version    = py_import("import tensorflow as tf; print(tf.__version__)")

jax_version   = py_import("import jax; print(jax.__version__)")
jaxlib_version= py_import("import jaxlib; print(jaxlib.__version__)")

framework_parts = []
if torch_version:
    t = f"PyTorch {torch_version}"
    # torch.version.cuda returns the string "None" (not Python None) for CPU-only builds
    if torch_cuda and torch_cuda != "None":
        t += f" (CUDA {torch_cuda})"
    framework_parts.append(t)
if tf_version:
    framework_parts.append(f"TensorFlow {tf_version}")
if jax_version:
    j = f"JAX {jax_version}"
    if jaxlib_version:
        j += f" / jaxlib {jaxlib_version}"
    framework_parts.append(j)

if framework_parts:
    framework_info = ", ".join(framework_parts)
else:
    framework_info = "no ML framework detected"


# ---------------------------------------------------------------------------
# Storage  (total raw capacity across all physical drives)
# ---------------------------------------------------------------------------

if IS_WINDOWS:
    out = ps("(Get-CimInstance Win32_DiskDrive).Size -join '\\n'")
    total_bytes = sum(
        int(x) for x in out.splitlines() if x.strip().isdigit()
    )

elif IS_MAC:
    # system_profiler reports each volume's capacity including the byte count in parentheses
    raw = run("system_profiler SPStorageDataType | grep 'Capacity'")
    total_bytes = 0
    for line in raw.splitlines():
        # Lines look like: "Capacity: 499.96 GB (499,963,174,912 bytes)"
        if "bytes" in line:
            try:
                b = line.split("(")[1].split("bytes")[0].replace(",", "").strip()
                total_bytes += int(b)
            except (IndexError, ValueError):
                pass

else:  # Linux
    # -b: output sizes in bytes; -d: skip partitions (physical drives only);
    # tail -n +2 strips the "SIZE" header row
    storage_bytes_raw = run("lsblk -b -d -o SIZE | tail -n +2")
    total_bytes = sum(int(x) for x in storage_bytes_raw.split() if x.isdigit())

storage_gb = int(total_bytes / (1024 ** 3))


# ---------------------------------------------------------------------------
# Assemble paragraph
# ---------------------------------------------------------------------------

if IS_WINDOWS:
    paragraph = (
        f"Experiments were conducted on a system running {os_info}, "
        f"equipped with a {cpu_model} CPU "
        f"({cpu_cores} cores, {cpu_threads_per_core} threads per core), "
        f"{ram} of RAM, and {gpu_info}. "
    )
elif IS_MAC:
    paragraph = (
        f"Experiments were conducted on a system running {os_info} "
        f"(kernel {kernel}), equipped with a {cpu_model} CPU "
        f"({cpu_cores} cores, {cpu_threads_per_core} threads per core), "
        f"{ram} of RAM, and {gpu_info}. "
    )
else:  # Linux
    paragraph = (
        f"Experiments were conducted on a server running {os_info} "
        f"(Linux kernel {kernel}), equipped with a {cpu_model} CPU "
        f"({cpu_cores} cores, {cpu_threads_per_core} threads per core), "
        f"{ram} of RAM, and {gpu_info}. "
    )

if cuda_version:
    paragraph += f"The system used CUDA {cuda_version}. "
elif rocm_version:
    paragraph += f"The system used ROCm {rocm_version}. "

paragraph += (
    f"Experiments were implemented using {framework_info}. "
    f"The system provided approximately {storage_gb} GB of storage."
)


# ---------------------------------------------------------------------------
# LaTeX-safe version  (escape underscores)
# ---------------------------------------------------------------------------

latex_paragraph = paragraph.replace("_", r"\_")


# ---------------------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------------------

with open("specs.txt", "w") as f:
    f.write(paragraph)

with open("specs.tex", "w") as f:
    f.write(latex_paragraph)

raw_fields = [
    ("OS",         os_info),
    ("Kernel",     kernel),
    ("CPU",        cpu_model),
    ("CPU Cores",  cpu_cores),
    ("Threads/Core", cpu_threads_per_core),
    ("RAM",        ram),
    ("GPU",        gpu_info),
    ("CUDA",       cuda_version or "N/A"),
    ("ROCm",       rocm_version or "N/A"),
    ("PyTorch",    torch_version or "N/A"),
    ("TensorFlow", tf_version    or "N/A"),
    ("JAX",        jax_version   or "N/A"),
    ("jaxlib",     jaxlib_version or "N/A"),
    ("Storage",    f"{storage_gb} GB"),
]

with open("specs_raw.txt", "w") as f:
    for key, val in raw_fields:
        f.write(f"{key}: {val}\n")


# ---------------------------------------------------------------------------
# Print
# ---------------------------------------------------------------------------

print("----- Plain Text -----\n")
print(paragraph)
print("\n----- LaTeX Version -----\n")
print(latex_paragraph)
print("\nSaved to specs.txt, specs.tex, and specs_raw.txt")
