from pathlib import Path

# Project root = current working directory
project_root = Path.cwd()

# Target: multifractals/mpe/code/mpe
target_dir = project_root / "mpe" / "code" / "mpe"
target_dir.mkdir(parents=True, exist_ok=True)

# Add __init__.py files so Python treats them as packages
for pkg_dir in [
    project_root / "mpe",
    project_root / "mpe" / "code",
    target_dir
]:
    init_file = pkg_dir / "__init__.py"
    init_file.touch(exist_ok=True)

print("✅ Created package structure at:", target_dir.resolve())
