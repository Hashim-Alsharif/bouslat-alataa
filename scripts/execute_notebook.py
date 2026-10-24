"""Local maintainer check: execute with an explicit Python interpreter.

Usage: python scripts/execute_notebook.py
The interpreter running this utility also runs the temporary local kernel.
No kernel is installed globally.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

ROOT = Path(__file__).resolve().parents[1]
notebook_name = sys.argv[1] if len(sys.argv) > 1 else "analysis.ipynb"
if notebook_name not in {"analysis.ipynb", "analysis_national.ipynb", "analysis_social_services.ipynb"}:
    raise ValueError("Choose a known project Notebook")
kernel_root = ROOT / ".tools/jupyter/kernels"
kernel_dir = kernel_root / "qassim-local"
kernel_dir.mkdir(parents=True, exist_ok=True)
kernel_file = kernel_dir / "kernel.json"
kernel_file.write_text(json.dumps({
    "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
    "display_name": "Qassim local check", "language": "python",
    "env": {"PYTHONPATH": os.environ.get("PYTHONPATH", ""), "PYTHONIOENCODING": "utf-8",
            "MPLCONFIGDIR": str(ROOT / ".tools/matplotlib")},
}), encoding="utf-8")
manager = KernelManager(kernel_name="qassim-local", kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_root)]))
if Path(manager.kernel_spec.argv[0]).resolve() != Path(sys.executable).resolve():
    raise RuntimeError("Unexpected kernel interpreter")
source_path = ROOT / "data_raw/ncnp_qassim_source.csv"
before = hashlib.sha256(source_path.read_bytes()).hexdigest()
notebook = nbformat.read(ROOT / notebook_name, as_version=4)
client = NotebookClient(notebook, km=manager, timeout=180, resources={"metadata":{"path":str(ROOT)}})
client.execute()
errors = [output for cell in notebook.cells if cell.cell_type == "code"
          for output in cell.get("outputs", []) if output.output_type == "error"]
if errors or hashlib.sha256(source_path.read_bytes()).hexdigest() != before:
    raise RuntimeError("Notebook errors or raw source changed")
nbformat.validate(notebook)
nbformat.write(notebook, ROOT / notebook_name)
executed = sum(cell.cell_type == "code" and cell.execution_count is not None for cell in notebook.cells)
print("NOTEBOOK_EXECUTED_OK", notebook_name, executed, "code cells; source unchanged")
