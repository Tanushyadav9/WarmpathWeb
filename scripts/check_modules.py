import sys, pkgutil, importlib, traceback
from pathlib import Path
sys.path.insert(0, "backend")
modules_dir = Path("backend/app/modules")
for module_info in pkgutil.iter_modules([str(modules_dir)]):
    mod_name = module_info.name
    try:
        mod = importlib.import_module(f"app.modules.{mod_name}.module")
        router_routes = len(mod.ROUTER.routes) if hasattr(mod, "ROUTER") else 0
        print(f"[OK] {mod_name}: {router_routes} routes")
    except Exception as e:
        print(f"[FAIL] {mod_name}: {type(e).__name__}: {e}")
