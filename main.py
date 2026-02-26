import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import csv, json
from pathlib import Path
import calendar

try:
    import xlwt
    EXCEL_AVAILABLE = True
except:
    EXCEL_AVAILABLE = False

class CalendarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Calendario Organizacional - Gestor de Eventos")
        self.root.geometry("1600x900")
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
        style.configure('Treeview', rowheight=26, font=('Segoe UI', 9))
        # Notebook tab style
        style.configure('TNotebook.Tab', font=('Segoe UI', 10, 'bold'), padding=[12, 8])
        self.events = []
        self.data_file = Path("calendar_data.json")
        self.current_date = datetime.now()
        self.load_data()
        # Updated calendar origins/sources as requested
        self.data_sources = [
            "ANV",
            "BHU",
            "DGS",
            "DINAVI-BPS",
            "DINOT",
            "MEVIR",
            "INSTITUCIONALES",
        ]
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
        
        # Title and search bar
        ttk.Label(c, text="Calendario - Vista de Lista", font=("Arial", 14, "bold")).pack(side=tk.LEFT, pady=10)
        
        # Search and filter controls
        s = ttk.Frame(c)
        s.pack(fill=tk.X, pady=10)
        ttk.Label(s, text="Buscar:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.refresh_calendar())
        ttk.Entry(s, textvariable=self.search_var, width=40).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(s, text="Fuente:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.filter_source_var = tk.StringVar(value="Todas")
        ttk.Combobox(s, textvariable=self.filter_source_var, values=["Todas"]+self.data_sources, state="readonly", width=25).pack(side=tk.LEFT, padx=5)
        self.filter_source_var.trace("w", lambda *a: self.refresh_calendar())
        
        # Treeview with improved column widths
        self.tree = ttk.Treeview(c, columns=("F", "A", "D", "S"), height=20)
        self.tree.column("#0", width=0, stretch=tk.NO)
        header_labels = {"F": "Fecha", "A": "Acción", "D": "Descripción", "S": "Fuente"}
        
        # Better column sizing - increased width for description
        for col, w in [("F", 100), ("A", 180), ("D", 600), ("S", 140)]:
            self.tree.column(col, anchor=tk.W, width=w)
            self.tree.heading(col, text=header_labels.get(col, col), anchor=tk.W)
        
        sb = ttk.Scrollbar(c, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        
        # configure Treeview tags for source colors
        for src, color in self.source_colors.items():
            try:
                # tag names without spaces
                tag = f"src_{src}"
                self.tree.tag_configure(tag, background=color)
            except Exception:
                pass
        
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
        
        # Search controls
        f = ttk.Frame(mg)
        f.pack(fill=tk.X, pady=10)
        ttk.Label(f, text="Buscar:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.manage_search_var = tk.StringVar()
        self.manage_search_var.trace("w", lambda *a: self.refresh_manage_list())
        ttk.Entry(f, textvariable=self.manage_search_var, width=40).pack(side=tk.LEFT, padx=5)
        
        # Treeview with improved columns
        self.manage_tree = ttk.Treeview(mg, columns=("F", "A", "D", "S"), height=20)
        self.manage_tree.column("#0", width=0, stretch=tk.NO)
        header_labels_local = {"F": "Fecha", "A": "Acción", "D": "Descripción", "S": "Fuente"}
        
        # Better column sizing
        for col, w in [("F", 100), ("A", 180), ("D", 600), ("S", 140)]:
            self.manage_tree.column(col, anchor=tk.W, width=w)
            self.manage_tree.heading(col, text=header_labels_local.get(col, col), anchor=tk.W)
        
        sb = ttk.Scrollbar(mg, orient=tk.VERTICAL, command=self.manage_tree.yview)
        self.manage_tree.configure(yscroll=sb.set)
        self.manage_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        self.manage_tree.bind("<Double-1>", self.on_manage_double_click)
        
        # configure tags for manage_tree as well
        for src, color in self.source_colors.items():
            try:
                tag = f"src_{src}"
                self.manage_tree.tag_configure(tag, background=color)
            except Exception:
                pass
        
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
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
        try:
            f = self.get_field_value("fecha_estimada")
            datetime.strptime(f, "%Y-%m-%d")
            a = self.get_field_value("accion")
            if not a or not self.get_field_value("descripcion_breve"):
                messagebox.showwarning("Validación", "Ingrese Acción y Descripción")
                return
            ev = {k: self.get_field_value(k) for k in self.form_fields}
            ev["fuente_datos"] = self.source_var.get()
            ev["timestamp"] = datetime.now().isoformat()
            self.events.append(ev)
            self.save_data()
            self.refresh_calendar()
            self.refresh_weekly()
            self.refresh_monthly()
            self.refresh_manage_list()
            self.clear_form()
            messagebox.showinfo("Éxito", "Evento guardado")
        except ValueError:
            messagebox.showerror("Error", "Fecha inválida (YYYY-MM-DD)")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def get_field_value(self, k):
        f = self.form_fields[k]
        return f.get("1.0", tk.END).strip() if isinstance(f, tk.Text) else f.get().strip()
    
    def clear_form(self):
        self.form_fields["fecha_estimada"].delete(0, tk.END)
        self.form_fields["fecha_estimada"].insert(0, datetime.now().strftime("%Y-%m-%d"))
        for k, f in self.form_fields.items():
            if k != "fecha_estimada":
                if isinstance(f, tk.Text):
                    f.delete("1.0", tk.END)
                else:
                    f.delete(0, tk.END)
    
    def refresh_calendar(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        st = self.search_var.get().lower()
        fs = self.filter_source_var.get()
        # insert rows with tags referencing the original event index and source for color-coding
        sorted_indices = sorted(range(len(self.events)), key=lambda i: self.events[i]["fecha_estimada"]) if self.events else []
        for idx in sorted_indices:
            e = self.events[idx]
            if st and st not in e["accion"].lower() and st not in e["descripcion_breve"].lower():
                continue
            if fs != "Todas" and e.get("fuente_datos", "") != fs:
                continue
            src = e.get("fuente_datos", '')
            icon = self.source_icons.get(src, '•')
            tag_src = f"src_{src}"
            # idx tag for easy lookup, display action with icon
            self.tree.insert("", tk.END, values=(e["fecha_estimada"], f"{icon} {e['accion']}", e["descripcion_breve"][:50], src), tags=(f"idx_{idx}", tag_src))
    
    def get_events_for_date(self, ds):
        return [e for e in self.events if e["fecha_estimada"] == ds]
    
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
        
        # Main container for the week grid
        main_frame = ttk.Frame(self.weekly_scrollframe)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create 7 columns (one per day) displayed side-by-side
        day_frames = []
        for i, dn in enumerate(["Lun", "Mar", "Mié", "Jue", "Vie", "Sab", "Dom"]):
            dd = sw + timedelta(days=i)
            ds = dd.strftime("%Y-%m-%d")
            
            # Day column with border
            day_col = tk.Frame(main_frame, relief=tk.RIDGE, borderwidth=2, bg='white')
            day_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=3, pady=3)
            day_frames.append(day_col)
            
            # Day header with day name and date
            header = tk.Label(day_col, text=f"{dn}\n{dd.strftime('%d/%m')}", 
                            font=("Segoe UI", 12, "bold"), bg='#2E86AB', fg='white', pady=8)
            header.pack(fill=tk.X)
            
            # Events container
            events_container = tk.Frame(day_col, bg='white')
            events_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            des = self.get_events_for_date(ds)
            if des:
                for ev in des:
                    color = self.source_colors.get(ev.get('fuente_datos', ''), '#dddddd')
                    src = ev.get('fuente_datos', '')
                    icon = self.source_icons.get(src, '•')
                    event_label = tk.Label(events_container, 
                                         text=f"{icon} {ev['accion'][:20]}", 
                                         bg=color, fg='black', anchor='w', padx=6, 
                                         pady=5, font=("Segoe UI", 9), 
                                         wraplength=120, justify=tk.LEFT)
                    event_label.pack(fill=tk.X, pady=3)
            else:
                empty_label = tk.Label(events_container, text="(Sin eventos)", 
                                      foreground="gray", font=("Segoe UI", 9, "italic"), 
                                      bg='#f9f9f9', pady=20)
                empty_label.pack(fill=tk.BOTH, expand=True)
    
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
        
        # Header with day names - better styling
        hf = ttk.Frame(mf)
        hf.pack(fill=tk.X, pady=10)
        for dn in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sab", "Dom"]:
            day_header = tk.Label(hf, text=dn, width=18, relief=tk.RAISED, 
                                 font=("Segoe UI", 11, "bold"), bg='#2E86AB', 
                                 fg='white', pady=6)
            day_header.pack(side=tk.LEFT, padx=2, fill=tk.BOTH, expand=True)
        
        # Calendar weeks with better spacing
        for w in calendar.monthcalendar(y, m):
            wf = ttk.Frame(mf)
            wf.pack(fill=tk.BOTH, expand=True, pady=4)
            for dn in w:
                if dn == 0:
                    # Empty day cell
                    df = tk.Frame(wf, bg='#f0f0f0', relief=tk.FLAT)
                    df.pack(side=tk.LEFT, padx=2, fill=tk.BOTH, expand=True)
                    df.pack_propagate(False)
                else:
                    ds = f"{y:04d}-{m:02d}-{dn:02d}"
                    des = self.get_events_for_date(ds)
                    # Day cell with better height
                    df = tk.Frame(wf, bg='white', relief=tk.SUNKEN, borderwidth=1)
                    df.pack(side=tk.LEFT, padx=2, fill=tk.BOTH, expand=True)
                    
                    # Day number - larger font
                    day_label = tk.Label(df, text=str(dn), font=("Segoe UI", 13, "bold"), 
                                        bg='white', anchor='ne', fg='#333333')
                    day_label.pack(anchor=tk.NE, padx=6, pady=4, fill=tk.X)
                    
                    # Separator line
                    sep = tk.Frame(df, bg='#e0e0e0', height=1)
                    sep.pack(fill=tk.X, padx=3, pady=2)
                    
                    # Events container with better sizing
                    events_frame = tk.Frame(df, bg='white')
                    events_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=3)
                    
                    # Display up to 4 events with better spacing
                    for idx, ev in enumerate(des[:4]):
                        color = self.source_colors.get(ev.get('fuente_datos', ''), '#dddddd')
                        src = ev.get('fuente_datos', '')
                        icon = self.source_icons.get(src, '•')
                        evt_text = f"{icon} {ev['accion'][:15]}"
                        evt_label = tk.Label(events_frame, text=evt_text, 
                                           wraplength=110, font=("Segoe UI", 8), 
                                           bg=color, fg='black', anchor='w', padx=3, pady=2)
                        evt_label.pack(anchor=tk.W, pady=2, fill=tk.X)
                    
                    # Show count of remaining events
                    if len(des) > 4:
                        more_label = tk.Label(events_frame, text=f"+{len(des)-4} más", 
                                            font=("Segoe UI", 7, "italic"), 
                                            fg='#666666', anchor='w', padx=3)
                        more_label.pack(anchor=tk.W, pady=1)
    
    def refresh_manage_list(self):
        for i in self.manage_tree.get_children():
            self.manage_tree.delete(i)
        st = self.manage_search_var.get().lower()
        # insert rows with idx tags and source color tags
        sorted_indices = sorted(range(len(self.events)), key=lambda i: self.events[i]["fecha_estimada"]) if self.events else []
        for idx in sorted_indices:
            e = self.events[idx]
            if st and st not in e["accion"].lower() and st not in e["descripcion_breve"].lower():
                continue
            tag_src = f"src_{e.get('fuente_datos','')}"
            self.manage_tree.insert("", tk.END, values=(e["fecha_estimada"], e["accion"], e["descripcion_breve"][:50], e.get("fuente_datos", "Sin fuente")), tags=(f"idx_{idx}", tag_src))
    
    def show_context_menu(self, e):
        i = self.tree.selection()
        if not i:
            return
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Editar", command=self.edit_from_calendar)
        m.add_command(label="Eliminar", command=self.delete_from_calendar)
        m.post(e.x_root, e.y_root)

    def on_tree_double_click(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        tags = self.tree.item(sel[0]).get('tags', ())
        for t in tags:
            if isinstance(t, str) and t.startswith('idx_'):
                try:
                    idx = int(t.split('_', 1)[1])
                    self.open_edit_dialog(idx)
                except Exception:
                    pass
                return

    def on_manage_double_click(self, event):
        sel = self.manage_tree.selection()
        if not sel:
            return
        tags = self.manage_tree.item(sel[0]).get('tags', ())
        for t in tags:
            if isinstance(t, str) and t.startswith('idx_'):
                try:
                    idx = int(t.split('_', 1)[1])
                    self.open_edit_dialog(idx)
                except Exception:
                    pass
                return
    
    def edit_from_calendar(self):
        s = self.tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        sorted_events = sorted(self.events, key=lambda x: x["fecha_estimada"])
        ec = 0
        for idx in range(len(sorted_events)):
            if ec == int(s[0]):
                self.open_edit_dialog(idx)
                return
            ec += 1
    
    def edit_event(self):
        s = self.manage_tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        tags = self.manage_tree.item(s[0])['tags']
        if tags:
            for t in tags:
                if isinstance(t, str) and t.startswith('idx_'):
                    try:
                        idx = int(t.split('_', 1)[1])
                        self.open_edit_dialog(idx)
                    except Exception:
                        pass
                    return
    
    def open_edit_dialog(self, eidx):
        ev = self.events[eidx]
        ew = tk.Toplevel(self.root)
        ew.title("Editar Evento")
        ew.geometry("600x400")
        efields = {}
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
            try:
                datetime.strptime(efields["fecha_estimada"].get(), "%Y-%m-%d")
                for k in efields:
                    self.events[eidx][k] = efields[k].get("1.0", tk.END).strip() if isinstance(efields[k], tk.Text) else efields[k].get()
                self.save_data()
                self.refresh_calendar()
                self.refresh_weekly()
                self.refresh_monthly()
                self.refresh_manage_list()
                ew.destroy()
                messagebox.showinfo("Éxito", "Evento actualizado")
            except ValueError:
                messagebox.showerror("Error", "Fecha inválida")
        ttk.Button(ew, text="Guardar", command=sc).pack(pady=10)
    
    def delete_event(self):
        s = self.manage_tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar?"):
            tags = self.manage_tree.item(s[0])['tags']
            if tags:
                del self.events[int(tags[0])]
                self.save_data()
                self.refresh_calendar()
                self.refresh_weekly()
                self.refresh_monthly()
                self.refresh_manage_list()
                messagebox.showinfo("Éxito", "Evento eliminado")
    
    def delete_from_calendar(self):
        s = self.tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        if messagebox.askyesno("Confirmar", "¿Eliminar?"):
            sorted_events = sorted(self.events, key=lambda x: x["fecha_estimada"])
            ec = 0
            for idx in range(len(sorted_events)):
                if ec == int(s[0]):
                    del self.events[idx]
                    self.save_data()
                    self.refresh_calendar()
                    self.refresh_weekly()
                    self.refresh_monthly()
                    self.refresh_manage_list()
                    messagebox.showinfo("Éxito", "Evento eliminado")
                    return
                ec += 1
    
    def view_event_details(self):
        s = self.manage_tree.selection()
        if not s:
            messagebox.showwarning("Advertencia", "Selecciona un evento")
            return
        tags = self.manage_tree.item(s[0])['tags']
        if tags:
            for t in tags:
                if isinstance(t, str) and t.startswith('idx_'):
                    try:
                        idx = int(t.split('_', 1)[1])
                        ev = self.events[idx]
                        messagebox.showinfo("Detalles", f"Fecha: {ev.get('fecha_estimada')}\nAcción: {ev.get('accion')}\nFuente: {ev.get('fuente_datos')}")
                    except Exception:
                        pass
                    return
    
    def export_xls(self):
        if not EXCEL_AVAILABLE:
            messagebox.showerror("Error", "xlwt no instalado")
            return
        try:
            fp = filedialog.asksaveasfilename(defaultextension=".xls", filetypes=[("Excel", "*.xls")])
            if not fp:
                return
            wb = xlwt.Workbook()
            ws = wb.add_sheet("Eventos")
            hs = xlwt.XFStyle()
            hs.font.bold = True
            hs = ["Fecha", "Acción", "Descripción", "Descripción actividad", "Autoridades", "Materiales", "Coordinaciones", "Fuente"]
            for col, h in enumerate(hs):
                ws.write(0, col, h)
            for row, e in enumerate(sorted(self.events, key=lambda x: x["fecha_estimada"]), start=1):
                ws.write(row, 0, e["fecha_estimada"])
                ws.write(row, 1, e["accion"])
                ws.write(row, 2, e["descripcion_breve"])
                ws.write(row, 3, e["descripcion_actividad"])
                ws.write(row, 4, e["autoridades"])
                ws.write(row, 5, e["materiales"])
                ws.write(row, 6, e["coordinaciones"])
                ws.write(row, 7, e.get("fuente_datos", ""))
            wb.save(fp)
            messagebox.showinfo("Éxito", f"Exportado a {fp}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def export_csv(self):
        try:
            fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if not fp:
                return
            with open(fp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Fecha", "Acción", "Descripción", "Descripción actividad", "Autoridades", "Materiales", "Coordinaciones", "Fuente"])
                for e in sorted(self.events, key=lambda x: x["fecha_estimada"]):
                    w.writerow([e["fecha_estimada"], e["accion"], e["descripcion_breve"], e["descripcion_actividad"], e["autoridades"], e["materiales"], e["coordinaciones"], e.get("fuente_datos", "")])
            messagebox.showinfo("Éxito", f"Exportado a {fp}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def save_data(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.events, f, ensure_ascii=False, indent=2)
    
    def load_data(self):
        if self.data_file.exists():
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.events = json.load(f)

if __name__ == "__main__":
    root = tk.Tk()
    app = CalendarApp(root)
    root.mainloop()
