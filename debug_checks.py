import tempfile, os, json
from pathlib import Path
import sys
# ensure package path
sys.path.insert(0, str(Path(__file__).parent))

from main_optimized import CalendarApp, DEFAULT_DATE_FORMAT
import tkinter as tk

results = {}

# Create hidden Tk root
root = tk.Tk()
root.withdraw()
app = CalendarApp(root)

# Basic helper checks
results['sanitize'] = app.sanitize_input('  hello   \nworld\t')
results['safe_date_valid'] = app._safe_parse_date('2026-02-06')
results['safe_date_invalid'] = app._safe_parse_date('invalid-date')

# Test sorted indices with sample events
app.events = [
    {'fecha_estimada':'2026-02-10','accion':'A'},
    {'fecha_estimada':'2026-01-01','accion':'B'},
    {'fecha_estimada':'','accion':'C'},
]
app._invalidate_sorted_cache()
results['sorted_indices'] = app.get_sorted_event_indices()

# Test extract_event_index
results['extract_ok'] = app.extract_event_index(('idx_2','src_ANV'))
results['extract_none'] = app.extract_event_index(('foo','bar'))

# Test save/load to temp file
tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
tmp.close()
try:
    app.data_file = Path(tmp.name)
    app.save_data()
    # modify then load
    app.events = []
    app.load_data()
    results['save_load_count'] = len(app.events)
finally:
    os.unlink(tmp.name)

print('SMOKE_OK', json.dumps(results, ensure_ascii=False))
# destroy root
root.destroy()
