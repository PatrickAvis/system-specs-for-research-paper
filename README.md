# system-specs-for-research-paper

Collects hardware and software specifications from the current machine and writes three files:

- **`specs.txt`** — plain-text paragraph, ready to paste into any document
- **`specs.tex`** — LaTeX-safe version of the same paragraph (underscores escaped)
- **`specs_raw.txt`** — individual fields as `Key: Value` pairs, one per line

## Example output

**Plain text / LaTeX paragraph:**
> Experiments were conducted on a server running Ubuntu 22.04.3 LTS (Linux kernel 5.15.0-91-generic), equipped with an Intel Xeon Gold 6326 CPU (32 cores, 2 threads per core), 512G of RAM, and 4 GPU(s) (4x NVIDIA A100-SXM4-80GB, 81920 MiB). The system used CUDA 12.2. Experiments were implemented using PyTorch 2.1.0 (CUDA 12.1), TensorFlow 2.14.0, JAX 0.4.23 / jaxlib 0.4.23. The system provided approximately 14901 GB of storage.

**Raw fields (`specs_raw.txt`):**
```
OS: Ubuntu 22.04.3 LTS
Kernel: 5.15.0-91-generic
CPU: Intel Xeon Gold 6326
CPU Cores: 32
Threads/Core: 2
RAM: 512G
GPU: 4 GPU(s) (4x NVIDIA A100-SXM4-80GB, 81920 MiB)
CUDA: 12.2
ROCm: N/A
PyTorch: 2.1.0
TensorFlow: 2.14.0
JAX: 0.4.23
jaxlib: 0.4.23
Storage: 14901 GB
```

## What it collects

| Field | Linux | macOS | Windows |
|---|---|---|---|
| OS | `lsb_release` / `/etc/os-release` | `sw_vers` | PowerShell `Win32_OperatingSystem` |
| Kernel / Build | `uname -r` | `uname -r` | Build number via CIM |
| CPU model | `lscpu` | `sysctl` | `Win32_Processor` |
| CPU cores / threads | `lscpu` (cores per socket × sockets) | `sysctl hw.physicalcpu` | `Win32_Processor` (multi-socket aware) |
| RAM | `free -h` | `sysctl hw.memsize` | `Win32_ComputerSystem` |
| NVIDIA GPU(s) | `nvidia-smi` | `nvidia-smi` | `nvidia-smi` |
| AMD GPU(s) | `rocm-smi` | `rocm-smi` | `rocm-smi` |
| Other GPU(s) | `lspci` | `system_profiler` | `Win32_VideoController` |
| CUDA version | `nvidia-smi` header | `nvidia-smi` header | `nvidia-smi` header |
| ROCm version | `rocm-smi --version` | `rocm-smi --version` | `rocm-smi --version` |
| PyTorch | active Python interpreter | active Python interpreter | active Python interpreter |
| TensorFlow | active Python interpreter | active Python interpreter | active Python interpreter |
| JAX / jaxlib | active Python interpreter | active Python interpreter | active Python interpreter |
| Storage (total) | `lsblk` | `system_profiler` | `Win32_DiskDrive` |

## Requirements

- Python 3.7+
- No external pip packages required — standard library only
- NVIDIA drivers (optional) — needed for GPU/CUDA detection via `nvidia-smi`
- ROCm (optional) — needed for AMD GPU detection via `rocm-smi`
- PyTorch, TensorFlow, JAX (optional) — detected automatically if installed in the active environment

## Setup

```bash
# Clone the repo
git clone https://github.com/PatrickAvis/system-specs-for-research-paper.git
cd system-specs-for-research-paper

# Create a virtual environment
python3 -m venv venv          # Linux / macOS
python  -m venv venv          # Windows

# Activate
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows
```

## Usage

Run the script with whatever Python is active in your environment:

```bash
python3 get_specs.py   # Linux / macOS
python  get_specs.py   # Windows
```

Three files are written to the current directory. The same paragraph is also printed to the terminal.

> **Note:** All three output files are excluded from git (via `.gitignore`) to avoid accidentally publishing your machine's hardware details.

### `specs.txt` — plain-text paragraph

A single ready-to-paste sentence describing your hardware and software environment. Use this for Word documents, Google Docs, or any plain-text submission.

### `specs.tex` — LaTeX paragraph

Identical to `specs.txt` but with underscores escaped (`\_`) for safe inclusion in LaTeX documents. Drop it into your paper with:

```latex
\section{Experimental Setup}
\input{specs.tex}
```

or copy-paste the contents inline.

### `specs_raw.txt` — raw key-value fields

Each spec on its own line (`Key: Value`), covering OS, kernel, CPU, RAM, GPU, CUDA/ROCm, ML frameworks, and storage. Useful when you want to hand-pick individual values or build your own sentence rather than use the generated paragraph.
