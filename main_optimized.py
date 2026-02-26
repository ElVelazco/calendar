import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import csv, json
from pathlib import Path
import calendar
import shutil
from enum import Enum
import re

try:
    import xlwt
    EXCEL_AVAILABLE = True
except:
    EXCEL_AVAILABLE = False

# --- Constants and Configuration ---
DEFAULT_WINDOW_SIZE = "1400x850"
DEFAULT_DATE_FORMAT = "%Y-%m-%d"
DISPLAY_DATE_FORMAT = "%d/%m/%Y"
TREEVIEW_ROW_HEIGHT = 26
MAX_EVENTS_MONTHLY = 3
BACKUP_SUFFIX = ".backup"
SEARCH_MIN_LENGTH = 1

class DataSource(Enum):
    """Enumeration for data sources with consistent representation."""
    ANV = "ANV"
    BHU = "BHU"
    DGS = "DGS"
    DINAVI_BPS = "DINAVI-BPS"
    DINOT = "DINOT"
    MEVIR = "MEVIR"
    INSTITUCIONALES = "INSTITUCIONALES"
    
    @classmethod
    def values(cls):
        """Return list of string values for all sources."""
        return [src.value for src in cls]

class CalendarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Calendario Organizacional - Gestor de Eventos")
        self.root.geometry(DEFAULT_WINDOW_SIZE)
        self.root.minsize(1200, 700)  # Prevent UI breaking on resize
        
        # --- UI styling (vivid, attractive) ---
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass
        # General fonts and colors
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'))
        style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'), background='#2E86AB', foreground='white')
        style.map('Accent.TButton', background=[('active', '#1F5F7A')])
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'), background='#2E86AB', foreground='white')
        style.configure('Treeview', rowheight=TREEVIEW_ROW_HEIGHT, font=('Segoe UI', 9))
        # Notebook tab style
        style.configure('TNotebook.Tab', font=('Segoe UI', 10, 'bold'), padding=[12, 8])
        
        self.events = []
        self.data_file = Path("calendar_data.json")
        self.current_date = datetime.now()
        self._sorted_indices_cache = None  # Cache for sorted indices
        
        self.load_data()
        
        # Updated calendar origins/sources with Enum-based values
        self.data_sources = DataSource.values()
        
        # Vivid color mapping for the new data sources (used to color-code events)
        self.source_colors = {
            "ANV": "#ff7f50",            # Coral
            "BHU": "#1abc9c",            # Turquoise
            "DGS": "#f1c40f",            # Yellow
            "DINAVI-BPS": "#9b59b6",     # Violet
            "DINOT": "#e67e22",          # Orange
            "MEVIR": "#2ecc71",          # Green
            "INSTITUCIONALES": "#3498db",# Blue
        }
        # Unicode icons for each source
        self.source_icons = {
            "ANV": "🏛️",                  # Government building
            "BHU": "🏢",                  # Office building
            "DGS": "📋",                  # Clipboard
            "DINAVI-BPS": "🚀",           # Rocket
            "DINOT": "⚙️",                # Gear
            "MEVIR": "🏡",                # House
            "INSTITUCIONALES": "🤝",     # Handshake
        }
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.forms_frame = ttk.Frame(self.notebook)
        self.calendar_frame = ttk.Frame(self.notebook)
        self.weekly_frame = ttk.Frame(self.notebook)
        self.monthly_frame = ttk.Frame(self.notebook)
        self.manage_frame = ttk.Frame(self.notebook)
        self.export_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.forms_frame, text="Formularios (8 Fuentes)")
        self.notebook.add(self.calendar_frame, text="Calendario (Lista)")
        self.notebook.add(self.weekly_frame, text="Vista Semanal")
        self.notebook.add(self.monthly_frame, text="Vista Mensual")
        self.notebook.add(self.manage_frame, text="Gestionar Eventos")
        self.notebook.add(self.export_frame, text="Exportar")
        
        self.setup_forms_tab()
        self.setup_calendar_tab()
        self.setup_weekly_tab()
        self.setup_monthly_tab()
        self.setup_manage_tab()
        self.setup_export_tab()
    
    def setup_forms_tab(self):
        forms_container = ttk.Frame(self.forms_frame, padding="15")
        forms_container.pack(fill=tk.BOTH, expand=True)
        ttk.Label(forms_container, text="Registrar Evento - Selecciona Fuente de Datos", font=("Arial", 14, "bold")).pack(pady=10)
        source_frame = ttk.Frame(forms_container)
        source_frame.pack(fill=tk.X, pady=10)
        ttk.Label(source_frame, text="Fuente de Datos:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.source_var = tk.StringVar(value=self.data_sources[0])
        ttk.Combobox(source_frame, textvariable=self.source_var, values=self.data_sources, state="readonly", width=30).pack(side=tk.LEFT, padx=5)
        
        self.form_fields = {}
        for label, key in [("Fecha estimada (YYYY-MM-DD)", "fecha_estimada"),("Acción", "accion"),("Descripción breve", "descripcion_breve"),("Descripción de la actividad", "descripcion_actividad"),("Autoridades que participan", "autoridades"),("Materiales / productos", "materiales"),("Coordinaciones", "coordinaciones")]:
            frame = ttk.Frame(forms_container)
            frame.pack(fill=tk.X, pady=5)
            ttk.Label(frame, text=label, width=35).pack(side=tk.LEFT, padx=5)
            if key == "fecha_estimada":
                entry = ttk.Entry(frame, width=30)
                entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
            elif key in ["descripcion_actividad", "coordinaciones"]:
                entry = tk.Text(frame, height=3, width=50)
            else:
                entry = ttk.Entry(frame, width=50)
            entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            self.form_fields[key] = entry
        
        button_frame = ttk.Frame(forms_container)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Guardar Evento", command=self.save_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Limpiar", command=self.clear_form).pack(side=tk.LEFT, padx=5)
    
    def setup_calendar_tab(self):
        c = ttk.Frame(self.calendar_frame, padding="15")
        c.pack(fill=tk.BOTH, expand=True)
        ttk.Label(c, text="Calendario - Lista", font=("Arial", 14, "bold")).pack(side=tk.LEFT, pady=10)
        s = ttk.Frame(c)
        s.pack(fill=tk.X, pady=10)
        ttk.Label(s, text="Buscar:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.refresh_calendar())
        ttk.Entry(s, textvariable=self.search_var, width=40).pack(side=tk.LEFT, padx=5)
        self.filter_source_var = tk.StringVar(value="Todas")
        ttk.Combobox(s, textvariable=self.filter_source_var, values=["Todas"]+self.data_sources, state="readonly", width=25).pack(side=tk.LEFT, padx=5)
        self.filter_source_var.trace("w", lambda *a: self.refresh_calendar())
        
        self.tree = self.create_treeview(c)
        sb = ttk.Scrollbar(c, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        # configure Treeview tags for source colors
        self.configure_treeview_tags(self.tree)
        ttk.Button(c, text="Actualizar", command=self.refresh_calendar).pack(pady=10)
        self.refresh_calendar()
    
    def setup_weekly_tab(self):
        w = ttk.Frame(self.weekly_frame, padding="15")
        w.pack(fill=tk.BOTH, expand=True)
        n = ttk.Frame(w)
        n.pack(fill=tk.X, pady=10)
        ttk.Button(n, text="< Ant", command=self.prev_week).pack(side=tk.LEFT, padx=5)
        self.week_label = ttk.Label(n, text="", font=("Arial", 12, "bold"))
        self.week_label.pack(side=tk.LEFT, padx=20)
        ttk.Button(n, text="Sig >", command=self.next_week).pack(side=tk.LEFT, padx=5)
        ttk.Button(n, text="Hoy", command=self.week_today).pack(side=tk.LEFT, padx=5)
        
        self.weekly_canvas = tk.Canvas(w, bg="white")
        sb = ttk.Scrollbar(w, orient=tk.VERTICAL, command=self.weekly_canvas.yview)
        self.weekly_scrollframe = ttk.Frame(self.weekly_canvas)
        self.weekly_scrollframe.bind("<Configure>", lambda e: self.weekly_canvas.configure(scrollregion=self.weekly_canvas.bbox("all")))
        self.weekly_canvas.create_window((0, 0), window=self.weekly_scrollframe, anchor="nw")
        self.weekly_canvas.configure(yscrollcommand=sb.set)
        self.weekly_canvas.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.refresh_weekly()
    
    def setup_monthly_tab(self):
        m = ttk.Frame(self.monthly_frame, padding="15")
        m.pack(fill=tk.BOTH, expand=True)
        n = ttk.Frame(m)
        n.pack(fill=tk.X, pady=10)
        ttk.Button(n, text="< Ant", command=self.prev_month).pack(side=tk.LEFT, padx=5)
        self.month_label = ttk.Label(n, text="", font=("Arial", 12, "bold"))
        self.month_label.pack(side=tk.LEFT, padx=20)
        ttk.Button(n, text="Sig >", command=self.next_month).pack(side=tk.LEFT, padx=5)
        ttk.Button(n, text="Hoy", command=self.month_today).pack(side=tk.LEFT, padx=5)
        
        self.monthly_canvas = tk.Canvas(m, bg="white")
        sb = ttk.Scrollbar(m, orient=tk.VERTICAL, command=self.monthly_canvas.yview)
        self.monthly_scrollframe = ttk.Frame(self.monthly_canvas)
        self.monthly_scrollframe.bind("<Configure>", lambda e: self.monthly_canvas.configure(scrollregion=self.monthly_canvas.bbox("all")))
        self.monthly_canvas.create_window((0, 0), window=self.monthly_scrollframe, anchor="nw")
        self.monthly_canvas.configure(yscrollcommand=sb.set)
        self.monthly_canvas.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.refresh_monthly()
    
    def setup_manage_tab(self):
        mg = ttk.Frame(self.manage_frame, padding="15")
        mg.pack(fill=tk.BOTH, expand=True)
        ttk.Label(mg, text="Gestionar Eventos", font=("Arial", 14, "bold")).pack(pady=10)
        f = ttk.Frame(mg)
        f.pack(fill=tk.X, pady=10)
        ttk.Label(f, text="Buscar:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.manage_search_var = tk.StringVar()
        self.manage_search_var.trace("w", lambda *a: self.refresh_manage_list())
        ttk.Entry(f, textvariable=self.manage_search_var, width=40).pack(side=tk.LEFT, padx=5)
        
        self.manage_tree = self.create_treeview(mg)
        sb = ttk.Scrollbar(mg, orient=tk.VERTICAL, command=self.manage_tree.yview)
        self.manage_tree.configure(yscroll=sb.set)
        self.manage_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.configure_treeview_tags(self.manage_tree)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.manage_tree.bind("<Double-1>", self.on_manage_double_click)
        bf = ttk.Frame(mg)
        bf.pack(pady=15)
        ttk.Button(bf, text="Editar", command=self.edit_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Eliminar", command=self.delete_event).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Detalles", command=self.view_event_details).pack(side=tk.LEFT, padx=5)
        self.refresh_manage_list()
    
    def setup_export_tab(self):
        e = ttk.Frame(self.export_frame, padding="20")
        e.pack(fill=tk.BOTH, expand=True)
        ttk.Label(e, text="Exportar Datos", font=("Arial", 14, "bold")).pack(pady=10)
        ttk.Label(e, text="Seleccione formato", wraplength=400).pack(pady=10)
        b = ttk.Frame(e)
        b.pack(pady=20)
        ttk.Button(b, text="Exportar XLS", command=self.export_xls).pack(pady=5, fill=tk.X)
        ttk.Button(b, text="Exportar CSV", command=self.export_csv).pack(pady=5, fill=tk.X)
    
    def save_event(self):
        """Save new event with comprehensive validation."""
        try:
            # Validate date format
            f = self.get_field_value("fecha_estimada")
            try:
                datetime.strptime(f, DEFAULT_DATE_FORMAT)
            except ValueError:
                messagebox.showerror("Error", f"Fecha inválida ({DEFAULT_DATE_FORMAT})")
                return
            
            # Validate required fields
            a = self.get_field_value("accion")
            desc = self.get_field_value("descripcion_breve")
            if not a or not a.strip():
                messagebox.showwarning("Validación", "Ingrese Acción")
                return
            if not desc or not desc.strip():
                messagebox.showwarning("Validación", "Ingrese Descripción")
                return
            
            # Validate source
            source = self.source_var.get()
            if source not in self.data_sources:
                messagebox.showerror("Error", "Fuente de datos inválida")
                return
            
            # Create event with sanitized data
            ev = {}
            for k in self.form_fields:
                value = self.get_field_value(k)
                ev[k] = self.sanitize_input(value)
            
            ev["fuente_datos"] = source
            ev["timestamp"] = datetime.now().isoformat()
            
            self.events.append(ev)
            self.save_data()
            self.refresh_all_views()
            self.clear_form()
            messagebox.showinfo("Éxito", "Evento guardado")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar evento: {str(e)}")
    
    def get_field_value(self, k):
        """Safely retrieve field value from form inputs (Text or Entry widgets)."""
        f = self.form_fields[k]
        return f.get("1.0", tk.END).strip() if isinstance(f, tk.Text) else f.get().strip()
    
    def sanitize_input(self, value):
        """Sanitize user input to prevent injection and data corruption."""
        if not isinstance(value, str):
            return value
        # Remove excess whitespace and control characters
        value = re.sub(r'\s+', ' ', value.strip())
        return value
    
    def create_treeview(self, parent):
        """Factory method to create and configure a treeview widget with consistent settings."""
        tree = ttk.Treeview(parent, columns=("F", "A", "D", "S"), height=20)
        tree.column("#0", width=0, stretch=tk.NO)
        header_labels = {"F": "Fecha", "A": "Acción", "D": "Descripción", "S": "Fuente"}
        for col, w in [("F", 110), ("A", 220), ("D", 520), ("S", 180)]:
            tree.column(col, anchor=tk.W, width=w)
            tree.heading(col, text=header_labels.get(col, col), anchor=tk.W)
        return tree
    
    def configure_treeview_tags(self, tree):
        """Configure treeview tags for all data sources with their colors."""
        for src, color in self.source_colors.items():
            try:
                tag = f"src_{src}"
                # Validate color format before applying
                if color and color.startswith('#') and len(color) == 7:
                    tree.tag_configure(tag, background=color)
            except Exception:
                pass  # Skip invalid colors
    
    def get_sorted_event_indices(self):
        """Return indices sorted by event date for consistent ordering across views.
        Uses caching to improve performance when called frequently."""
        if self._sorted_indices_cache is None:
            if not self.events:
                self._sorted_indices_cache = []
            else:
                self._sorted_indices_cache = sorted(
                    range(len(self.events)), 
                    key=lambda i: self._safe_parse_date(self.events[i].get("fecha_estimada", ""))
                )
        return self._sorted_indices_cache
    
    def _invalidate_sorted_cache(self):
        """Invalidate cached sorted indices when data changes."""
        self._sorted_indices_cache = None
    
    def _safe_parse_date(self, date_str):
        """Safely parse date string for comparison, returning tuple (year, month, day) or maximum date."""
        try:
            dt = datetime.strptime(date_str, DEFAULT_DATE_FORMAT)
            return (dt.year, dt.month, dt.day)
        except (ValueError, TypeError):
            return (9999, 12, 31)  # Invalid dates sort to end
    
    def clear_form(self):
        """Clear all form fields and reset date to today."""
        try:
            self.form_fields["fecha_estimada"].delete(0, tk.END)
            self.form_fields["fecha_estimada"].insert(0, datetime.now().strftime(DEFAULT_DATE_FORMAT))
            for k, f in self.form_fields.items():
                if k != "fecha_estimada":
                    if isinstance(f, tk.Text):
                        f.delete("1.0", tk.END)
                    else:
                        f.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Error al limpiar formulario: {str(e)}")
    
    def refresh_calendar(self):
        """Refresh calendar list view with search and source filtering applied."""
        for i in self.tree.get_children():
            self.tree.delete(i)
        st = self.search_var.get().lower().strip()
        fs = self.filter_source_var.get()
        sorted_indices = self.get_sorted_event_indices()
        
        for idx in sorted_indices:
            if not 0 <= idx < len(self.events):
                continue
            e = self.events[idx]
            
            # Apply search filter with early return for efficiency
            if st and len(st) >= SEARCH_MIN_LENGTH:
                action_match = st in e.get("accion", "").lower()
                desc_match = st in e.get("descripcion_breve", "").lower()
                if not (action_match or desc_match):
                    continue
            
            # Apply source filter
            if fs != "Todas" and e.get("fuente_datos", "") != fs:
                continue
            
            src = e.get("fuente_datos", '')
            icon = self.source_icons.get(src, '•')
            tag_src = f"src_{src}"
            self.tree.insert("", tk.END, 
                           values=(e.get("fecha_estimada", ""), 
                                  f"{icon} {e.get('accion', '')}",
                                  e.get("descripcion_breve", "")[:50], 
                                  src), 
                           tags=(f"idx_{idx}", tag_src))
    
    def get_events_for_date(self, ds):
        """Safely retrieve events for a given date with error handling."""
        try:
            return [e for e in self.events if e.get("fecha_estimada") == ds]
        except Exception:
            return []
    
    def prev_week(self):
        self.current_date -= timedelta(days=7)
        self.refresh_weekly()
    
    def next_week(self):
        self.current_date += timedelta(days=7)
        self.refresh_weekly()
    
    def week_today(self):
        self.current_date = datetime.now()
        self.refresh_weekly()
    
    def refresh_weekly(self):
        for w in self.weekly_scrollframe.winfo_children():
            w.destroy()
        sw = self.current_date - timedelta(days=self.current_date.weekday())
        ew = sw + timedelta(days=6)
        self.week_label.config(text=f"Semana del {sw.strftime('%d/%m/%Y')} al {ew.strftime('%d/%m/%Y')}")
        mf = ttk.Frame(self.weekly_scrollframe)
        mf.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for i, dn in enumerate(["Lun", "Mar", "Mié", "Jue", "Vie", "Sab", "Dom"]):
            dd = sw + timedelta(days=i)
            ds = dd.strftime("%Y-%m-%d")
            hf = ttk.Frame(mf, relief=tk.RAISED, borderwidth=2)
            hf.pack(fill=tk.X, padx=2, pady=2)
            ttk.Label(hf, text=f"{dn} {dd.strftime('%d/%m')}", font=("Segoe UI", 11, "bold")).pack(pady=6)
            ef = ttk.Frame(mf, relief=tk.SUNKEN, borderwidth=1)
            ef.pack(fill=tk.X, padx=2, pady=2)
            des = self.get_events_for_date(ds)
            if des:
                for ev in des:
                    color = self.source_colors.get(ev.get('fuente_datos', ''), '#dddddd')
                    src = ev.get('fuente_datos', '')
                    icon = self.source_icons.get(src, '•')
                    lbl = tk.Label(ef, text=f" {icon} {ev['accion']}", bg=color, fg='black', anchor='w', padx=6, font=("Segoe UI", 9))
                    lbl.pack(fill=tk.X, padx=8, pady=4)
            else:
                tk.Label(ef, text="(Sin eventos)", foreground="gray").pack(anchor=tk.W, padx=10, pady=6)
    
    def prev_month(self):
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(year=self.current_date.year-1, month=12)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month-1)
        self.refresh_monthly()
    
    def next_month(self):
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(month=self.current_date.month+1)
        self.refresh_monthly()
    
    def month_today(self):
        self.current_date = datetime.now()
        self.refresh_monthly()
    
    def refresh_monthly(self):
        for w in self.monthly_scrollframe.winfo_children():
            w.destroy()
        y, m = self.current_date.year, self.current_date.month
        self.month_label.config(text=datetime(y, m, 1).strftime("%B %Y").title())
        mf = ttk.Frame(self.monthly_scrollframe)
        mf.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        # Header with day names
        hf = ttk.Frame(mf)
        hf.pack(fill=tk.X, pady=5)
        for dn in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sab", "Dom"]:
            ttk.Label(hf, text=dn, width=15, relief=tk.RAISED, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        # Calendar weeks with evenly distributed cells
        for w in calendar.monthcalendar(y, m):
            wf = ttk.Frame(mf)
            wf.pack(fill=tk.BOTH, expand=True, pady=2)
            for dn in w:
                if dn == 0:
                    # Empty day cell - fixed height for consistency
                    df = tk.Frame(wf, bg='#f0f0f0', height=100)
                    df.pack(side=tk.LEFT, padx=2, fill=tk.BOTH, expand=True)
                    df.pack_propagate(False)
                else:
                    ds = f"{y:04d}-{m:02d}-{dn:02d}"
                    des = self.get_events_for_date(ds)
                    df = tk.Frame(wf, bg='white', relief=tk.SUNKEN, borderwidth=1)
                    df.pack(side=tk.LEFT, padx=2, fill=tk.BOTH, expand=True)
                    # Day number
                    day_label = tk.Label(df, text=str(dn), font=("Segoe UI", 10, "bold"), bg='white', anchor='ne')
                    day_label.pack(anchor=tk.NE, padx=4, pady=3, fill=tk.X)
                    # Events container with scroll-like appearance
                    events_frame = tk.Frame(df, bg='white')
                    events_frame.pack(fill=tk.BOTH, expand=True, padx=3, pady=2)
                    for idx, ev in enumerate(des[:3]):
                        color = self.source_colors.get(ev.get('fuente_datos', ''), '#dddddd')
                        src = ev.get('fuente_datos', '')
                        icon = self.source_icons.get(src, '•')
                        evt_label = tk.Label(events_frame, text=f"{icon} {ev.get('accion', '')[:11]}", wraplength=95, font=("Segoe UI", 7), bg=color, fg='black', anchor='w', padx=2)
                        evt_label.pack(anchor=tk.W, pady=1, fill=tk.X)
                    if len(des) > 3:
                        more_label = tk.Label(events_frame, text=f"+{len(des)-3} más", font=("Segoe UI", 6, "italic"), fg='#666666')
                        more_label.pack(anchor=tk.W, pady=1)
    
    def refresh_manage_list(self):
        """Refresh manage view list with search filtering and validation."""
        for i in self.manage_tree.get_children():
            self.manage_tree.delete(i)
        st = self.manage_search_var.get().lower().strip()
        sorted_indices = self.get_sorted_event_indices()
        
        for idx in sorted_indices:
            if not 0 <= idx < len(self.events):
                continue
            e = self.events[idx]
            
            # Apply search filter
            if st and len(st) >= SEARCH_MIN_LENGTH:
                action_match = st in e.get("accion", "").lower()
                desc_match = st in e.get("descripcion_breve", "").lower()
                if not (action_match or desc_match):
                    continue
            
            tag_src = f"src_{e.get('fuente_datos','')}"
            self.manage_tree.insert("", tk.END, 
                                   values=(e.get("fecha_estimada", ""), 
                                          e.get("accion", ""), 
                                          e.get("descripcion_breve", "")[:50], 
                                          e.get("fuente_datos", "Sin fuente")), 
                                   tags=(f"idx_{idx}", tag_src))
    
    def show_context_menu(self, e):
        """Display context menu for tree item selection (edit/delete)."""
        i = self.tree.selection()
        if not i:
            return
        try:
            m = tk.Menu(self.root, tearoff=0)
            m.add_command(label="Editar", command=self.edit_from_calendar)
            m.add_command(label="Eliminar", command=self.delete_from_calendar)
            m.post(e.x_root, e.y_root)
        except Exception:
            pass  # Menu display error - non-critical

    def extract_event_index(self, tags):
        """Extract event index from tag tuple by locating 'idx_*' tag."""
        for t in tags:
            if isinstance(t, str) and t.startswith('idx_'):
                try:
                    return int(t.split('_', 1)[1])
                except (ValueError, IndexError):
                    pass
        return None

    def on_tree_double_click(self, event):
        """Handle double-click on calendar tree - open edit dialog."""
        sel = self.tree.selection()
        if not sel:
            return
        tags = self.tree.item(sel[0]).get('tags', ())
        idx = self.extract_event_index(tags)
        if idx is not None and 0 <= idx < len(self.events):
            self.open_edit_dialog(idx)

    def on_manage_double_click(self, event):
        """Handle double-click on manage tree - open edit dialog."""
        sel = self.manage_tree.selection()
        if not sel:
            return
        tags = self.manage_tree.item(sel[0]).get('tags', ())
        idx = self.extract_event_index(tags)
        if idx is not None and 0 <= idx < len(self.events):
            self.open_edit_dialog(idx)
    
    def edit_from_calendar(self):
        """Edit event from calendar view using context menu."""
        s = self.tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        tags = self.tree.item(s[0]).get('tags', ())
        idx = self.extract_event_index(tags)
        if idx is not None and 0 <= idx < len(self.events):
            self.open_edit_dialog(idx)
        else:
            messagebox.showerror("Error", "Evento no encontrado")
    
    def edit_event(self):
        """Edit event from manage view."""
        s = self.manage_tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        tags = self.manage_tree.item(s[0]).get('tags', ())
        idx = self.extract_event_index(tags)
        if idx is not None and 0 <= idx < len(self.events):
            self.open_edit_dialog(idx)
    
    def open_edit_dialog(self, eidx):
        """Open modal dialog to edit event at given index with full validation."""
        if not 0 <= eidx < len(self.events):
            messagebox.showerror("Error", "Índice de evento inválido")
            return
        ev = self.events[eidx]
        ew = tk.Toplevel(self.root)
        ew.title("Editar Evento")
        ew.geometry("600x450")
        ew.resizable(False, False)  # Prevent accidental resize issues
        efields = {}
        
        # Source field with validation
        src_frame = ttk.Frame(ew)
        src_frame.pack(fill=tk.X, pady=5, padx=10)
        ttk.Label(src_frame, text="Fuente de Datos", width=35).pack(side=tk.LEFT, padx=5)
        src_var = tk.StringVar(value=ev.get("fuente_datos", self.data_sources[0]))
        ttk.Combobox(src_frame, textvariable=src_var, values=self.data_sources, state="readonly", width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        efields["fuente_datos"] = src_var
        
        for label, key in [("Fecha (YYYY-MM-DD)", "fecha_estimada"),("Acción", "accion"),("Descripción breve", "descripcion_breve"),("Descripción actividad", "descripcion_actividad"),("Autoridades", "autoridades"),("Materiales", "materiales"),("Coordinaciones", "coordinaciones")]:
            f = ttk.Frame(ew)
            f.pack(fill=tk.X, pady=5, padx=10)
            ttk.Label(f, text=label, width=35).pack(side=tk.LEFT, padx=5)
            if key in ["descripcion_actividad", "coordinaciones"]:
                entry = tk.Text(f, height=2, width=40)
                entry.insert("1.0", ev.get(key, ""))
            else:
                entry = ttk.Entry(f, width=40)
                entry.insert(0, ev.get(key, ""))
            entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            efields[key] = entry
        
        def sc():
            """Validate and save event changes."""
            try:
                # Validate date format
                date_val = efields["fecha_estimada"].get().strip()
                try:
                    datetime.strptime(date_val, DEFAULT_DATE_FORMAT)
                except ValueError:
                    messagebox.showerror("Error", f"Fecha inválida ({DEFAULT_DATE_FORMAT})")
                    return
                
                # Validate source
                source_val = efields["fuente_datos"].get()
                if source_val not in self.data_sources:
                    messagebox.showerror("Error", "Fuente de datos inválida")
                    return
                
                # Validate required fields
                action_val = efields["accion"].get().strip()
                desc_val = efields["descripcion_breve"].get().strip()
                if not action_val:
                    messagebox.showwarning("Validación", "Acción es requerida")
                    return
                if not desc_val:
                    messagebox.showwarning("Validación", "Descripción es requerida")
                    return
                
                # Update all fields with proper type handling
                for k in efields:
                    if k == "fuente_datos":
                        self.events[eidx][k] = efields[k].get()
                    else:
                        val = efields[k].get("1.0", tk.END).strip() if isinstance(efields[k], tk.Text) else efields[k].get().strip()
                        self.events[eidx][k] = self.sanitize_input(val)
                
                self._invalidate_sorted_cache()
                self.save_data()
                self.refresh_all_views()
                ew.destroy()
                messagebox.showinfo("Éxito", "Evento actualizado")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar: {str(e)}")
        
        ttk.Button(ew, text="Guardar", command=sc).pack(pady=10)
    
    def refresh_all_views(self):
        """Batch refresh all views to avoid repetition."""
        self.refresh_calendar()
        self.refresh_weekly()
        self.refresh_monthly()
        self.refresh_manage_list()
    
    def delete_event(self):
        """Delete event from manage view with confirmation and validation."""
        s = self.manage_tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar evento?"):
            return
        
        tags = self.manage_tree.item(s[0]).get('tags', ())
        idx = self.extract_event_index(tags)
        if idx is None or not (0 <= idx < len(self.events)):
            messagebox.showerror("Error", "Evento no encontrado")
            return
        
        try:
            del self.events[idx]
            self._invalidate_sorted_cache()
            self.save_data()
            self.refresh_all_views()
            messagebox.showinfo("Éxito", "Evento eliminado")
        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar: {str(e)}")
    
    def delete_from_calendar(self):
        """Delete event from calendar view using context menu with validation."""
        s = self.tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar evento?"):
            return
        
        tags = self.tree.item(s[0]).get('tags', ())
        idx = self.extract_event_index(tags)
        if idx is None or not (0 <= idx < len(self.events)):
            messagebox.showerror("Error", "Evento no encontrado")
            return
        
        try:
            del self.events[idx]
            self._invalidate_sorted_cache()
            self.save_data()
            self.refresh_all_views()
            messagebox.showinfo("Éxito", "Evento eliminado")
        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar: {str(e)}")
    
    def view_event_details(self):
        """Display detailed information about selected event."""
        s = self.manage_tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        tags = self.manage_tree.item(s[0]).get('tags', ())
        idx = self.extract_event_index(tags)
        if idx is not None and 0 <= idx < len(self.events):
            ev = self.events[idx]
            details = (f"Fecha: {ev.get('fecha_estimada', 'N/A')}\n"
                      f"Acción: {ev.get('accion', 'N/A')}\n"
                      f"Fuente: {ev.get('fuente_datos', 'N/A')}\n"
                      f"Descripción: {ev.get('descripcion_breve', 'N/A')}")
            messagebox.showinfo("Detalles del Evento", details)
        else:
            messagebox.showerror("Error", "Evento no encontrado")
    
    def export_xls(self):
        """Export all events to XLS format with robust error handling."""
        if not EXCEL_AVAILABLE:
            messagebox.showerror("Error", "xlwt no instalado. Instale con: pip install xlwt")
            return
        try:
            fp = filedialog.asksaveasfilename(defaultextension=".xls", filetypes=[("Excel", "*.xls")])
            if not fp:
                return
            if not self.events:
                messagebox.showwarning("Aviso", "No hay eventos para exportar")
                return
            wb = xlwt.Workbook()
            ws = wb.add_sheet("Eventos")
            header_style = xlwt.XFStyle()
            header_style.font.bold = True
            headers = ["Fecha", "Acción", "Descripción", "Descripción actividad", "Autoridades", "Materiales", "Coordinaciones", "Fuente"]
            for col, h in enumerate(headers):
                ws.write(0, col, h, header_style)
            # Sort events by date for consistent export order
            sorted_events = sorted(self.events, key=lambda x: self._safe_parse_date(x.get("fecha_estimada", "")))
            for row, e in enumerate(sorted_events, start=1):
                ws.write(row, 0, e.get("fecha_estimada", ""))
                ws.write(row, 1, e.get("accion", ""))
                ws.write(row, 2, e.get("descripcion_breve", ""))
                ws.write(row, 3, e.get("descripcion_actividad", ""))
                ws.write(row, 4, e.get("autoridades", ""))
                ws.write(row, 5, e.get("materiales", ""))
                ws.write(row, 6, e.get("coordinaciones", ""))
                ws.write(row, 7, e.get("fuente_datos", ""))
            wb.save(fp)
            messagebox.showinfo("Éxito", f"Exportado a {fp}")
        except IOError as e:
            messagebox.showerror("Error", f"Error de archivo: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar XLS: {str(e)}")
    
    def export_csv(self):
        """Export all events to CSV format with robust error handling."""
        try:
            fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if not fp:
                return
            if not self.events:
                messagebox.showwarning("Aviso", "No hay eventos para exportar")
                return
            with open(fp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Fecha", "Acción", "Descripción", "Descripción actividad", "Autoridades", "Materiales", "Coordinaciones", "Fuente"])
                sorted_events = sorted(self.events, key=lambda x: self._safe_parse_date(x.get("fecha_estimada", "")))
                for e in sorted_events:
                    w.writerow([e.get("fecha_estimada", ""), e.get("accion", ""), e.get("descripcion_breve", ""), 
                               e.get("descripcion_actividad", ""), e.get("autoridades", ""), e.get("materiales", ""), 
                               e.get("coordinaciones", ""), e.get("fuente_datos", "")])
            messagebox.showinfo("Éxito", f"Exportado a {fp}")
        except IOError as e:
            messagebox.showerror("Error", f"Error de archivo: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar CSV: {str(e)}")
    
    def save_data(self):
        """Persist event data to JSON file with backup and error handling."""
        try:
            # Create backup before overwriting
            if self.data_file.exists():
                try:
                    backup_file = Path(str(self.data_file) + BACKUP_SUFFIX)
                    shutil.copy(self.data_file, backup_file)
                except Exception:
                    pass  # Backup failure is non-critical
            
            # Write new data
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.events, f, ensure_ascii=False, indent=2)
        except IOError as e:
            messagebox.showerror("Error", f"Error al guardar datos: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error inesperado al guardar: {e}")
    
    def load_data(self):
        """Load event data from JSON file with validation."""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.events = data
                    else:
                        messagebox.showwarning("Advertencia", "Formato de datos incorrecto, iniciando vacío")
                        self.events = []
            except json.JSONDecodeError:
                messagebox.showwarning("Advertencia", "Datos corruptos, iniciando vacío")
                self.events = []
            except Exception as e:
                messagebox.showerror("Error", f"Error al cargar datos: {e}")
                self.events = []

if __name__ == "__main__":
    root = tk.Tk()
    app = CalendarApp(root)
    root.mainloop()
