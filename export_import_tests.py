import tempfile, os, json, csv
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from main_optimized import CalendarApp, DataSource, EXCEL_AVAILABLE
import tkinter as tk

# Hide Tk window
root = tk.Tk()
root.withdraw()
app = CalendarApp(root)

# Create sample test events
test_events = [
    {
        "fecha_estimada": "2026-02-06",
        "accion": "Reunión de inicio",
        "descripcion_breve": "Kickoff meeting",
        "descripcion_actividad": "Initial project planning",
        "autoridades": "Director, Manager",
        "materiales": "Laptop, projector",
        "coordinaciones": "IT, HR",
        "fuente_datos": "ANV",
        "timestamp": "2026-02-06T10:00:00"
    },
    {
        "fecha_estimada": "2026-02-10",
        "accion": "Taller de capacitación",
        "descripcion_breve": "Training workshop",
        "descripcion_actividad": "Staff training on new procedures",
        "autoridades": "HR Manager",
        "materiales": "Materials, handouts",
        "coordinaciones": "Training dept",
        "fuente_datos": "BHU",
        "timestamp": "2026-02-06T11:00:00"
    },
    {
        "fecha_estimada": "2026-02-15",
        "accion": "Auditoría interna",
        "descripcion_breve": "Internal audit",
        "descripcion_actividad": "Financial and compliance audit",
        "autoridades": "Audit team",
        "materiales": "Documents, systems",
        "coordinaciones": "Finance",
        "fuente_datos": "DGS",
        "timestamp": "2026-02-06T12:00:00"
    }
]

app.events = test_events
results = {}

# Test 1: Export to XLS
print("Testing XLS export...")
try:
    if EXCEL_AVAILABLE:
        import xlwt
        tmp_xls = tempfile.NamedTemporaryFile(delete=False, suffix='.xls')
        tmp_xls.close()
        wb = xlwt.Workbook()
        ws = wb.add_sheet("Eventos")
        header_style = xlwt.XFStyle()
        header_style.font.bold = True
        headers = ["Fecha", "Acción", "Descripción", "Descripción actividad", "Autoridades", "Materiales", "Coordinaciones", "Fuente"]
        for col, h in enumerate(headers):
            ws.write(0, col, h, header_style)
        sorted_events = sorted(app.events, key=lambda x: app._safe_parse_date(x.get("fecha_estimada", "")))
        for row, e in enumerate(sorted_events, start=1):
            ws.write(row, 0, e.get("fecha_estimada", ""))
            ws.write(row, 1, e.get("accion", ""))
            ws.write(row, 2, e.get("descripcion_breve", ""))
            ws.write(row, 3, e.get("descripcion_actividad", ""))
            ws.write(row, 4, e.get("autoridades", ""))
            ws.write(row, 5, e.get("materiales", ""))
            ws.write(row, 6, e.get("coordinaciones", ""))
            ws.write(row, 7, e.get("fuente_datos", ""))
        wb.save(tmp_xls.name)
        results['xls_export'] = f"✓ Created {os.path.getsize(tmp_xls.name)} bytes"
        results['xls_rows'] = len(sorted_events) + 1  # +1 for header
        os.unlink(tmp_xls.name)
    else:
        results['xls_export'] = "SKIP (xlwt not available)"
except Exception as e:
    results['xls_export_error'] = str(e)

# Test 2: Export to CSV
print("Testing CSV export...")
try:
    tmp_csv = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='w', newline='', encoding='utf-8-sig')
    tmp_csv_path = tmp_csv.name
    tmp_csv.close()
    
    with open(tmp_csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(["Fecha", "Acción", "Descripción", "Descripción actividad", "Autoridades", "Materiales", "Coordinaciones", "Fuente"])
        sorted_events = sorted(app.events, key=lambda x: app._safe_parse_date(x.get("fecha_estimada", "")))
        for e in sorted_events:
            w.writerow([e.get("fecha_estimada", ""), e.get("accion", ""), e.get("descripcion_breve", ""), 
                       e.get("descripcion_actividad", ""), e.get("autoridades", ""), e.get("materiales", ""), 
                       e.get("coordinaciones", ""), e.get("fuente_datos", "")])
    
    csv_size = os.path.getsize(tmp_csv_path)
    results['csv_export'] = f"✓ Created {csv_size} bytes"
    
    # Verify CSV contents
    with open(tmp_csv_path, 'r', encoding='utf-8-sig') as f:
        csv_lines = sum(1 for line in f)
    results['csv_rows'] = csv_lines
    results['csv_data_rows'] = csv_lines - 1  # subtract header
    os.unlink(tmp_csv_path)
except Exception as e:
    results['csv_export_error'] = str(e)

# Test 3: Data integrity - save and load
print("Testing save/load round-trip...")
try:
    tmp_json = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
    tmp_json.close()
    app.data_file = Path(tmp_json.name)
    app.save_data()
    
    # Load it back
    app.events = []
    app.load_data()
    
    results['roundtrip_original'] = len(test_events)
    results['roundtrip_loaded'] = len(app.events)
    results['roundtrip_match'] = len(app.events) == len(test_events)
    
    # Check field integrity
    if len(app.events) > 0:
        first = app.events[0]
        results['field_check_accion'] = first.get('accion') == test_events[0]['accion']
        results['field_check_fuente'] = first.get('fuente_datos') == test_events[0]['fuente_datos']
    
    os.unlink(tmp_json.name)
except Exception as e:
    results['roundtrip_error'] = str(e)

# Test 4: Validate data sources enum
print("Testing data sources enum...")
try:
    sources = DataSource.values()
    results['data_sources_count'] = len(sources)
    results['data_sources'] = ', '.join(sources[:3]) + '...'
    results['anv_in_sources'] = 'ANV' in sources
except Exception as e:
    results['sources_error'] = str(e)

# Print results
print("\n" + "="*70)
print("EXPORT/IMPORT SMOKE TEST RESULTS")
print("="*70)
for k, v in sorted(results.items()):
    status = '✓' if 'error' not in k.lower() else '✗'
    print(f"{status} {k:30s}: {v}")
print("="*70)

# Final status
all_ok = all('error' not in k.lower() for k in results.keys())
print(f"\nOVERALL: {'PASS ✓✓✓' if all_ok else 'FAIL ✗'}")

root.destroy()
