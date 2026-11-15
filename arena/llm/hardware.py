"""What this machine can run. Uses nvidia-smi and /proc/meminfo, so torch is not needed."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class Hardware:
    gpu: str = ""
    vram_gb: float = 0.0
    ram_gb: float = 0.0
    ram_free_gb: float = 0.0

    @property
    def usable_gb(self) -> float:
        """Memory a model can use without spilling badly: VRAM if there is a GPU, else free RAM."""
        return self.vram_gb if self.vram_gb else max(1.0, self.ram_free_gb * 0.7)


def detect() -> Hardware:
    hw = Hardware()
    try:
        with open("/proc/meminfo") as f:
            info = {l.split(":")[0]: int(l.split()[1]) for l in f if ":" in l}
        hw.ram_gb = round(info.get("MemTotal", 0) / 1048576, 1)
        hw.ram_free_gb = round(info.get("MemAvailable", 0) / 1048576, 1)
    except Exception:
        pass
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                                 capture_output=True, text=True, timeout=5).stdout.strip().splitlines()
            if out:
                name, mem = [x.strip() for x in out[0].split(",")]
                hw.gpu, hw.vram_gb = name, round(float(mem) / 1024, 1)
        except Exception:
            pass
    return hw
