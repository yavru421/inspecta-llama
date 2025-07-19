#!/usr/bin/env python3
#🦙 Inspectallama - AI-Powered Deep Research & Discovery Platform
##"""


import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading, queue, os, sys, time, json, re, webbrowser, argparse, asyncio, tkinter as tk
from research_case_integration import integrate_research_cases
from research_case_optimizer import optimize_app_for_research
import asyncio
import requests
import urllib.parse
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
try:
    import tiktoken
except ImportError:
    tiktoken = None
try:
    import psutil
except ImportError:
    psutil = None
from readability import Document
from llama_api_client import AsyncLlamaAPIClient
from datetime import datetime
from typing import Any, Awaitable, Callable, List, Optional, Dict


# ===== CONCURRENT UTILITIES =====
class ProgressTracker:
    """Track progress of concurrent operations with callbacks."""

    def __init__(self):
        self.calls_sent = 0
        self.calls_completed = 0
        self.errors = 0
        self.callbacks = []

    def register_callback(self, callback: Callable[[Dict[str, int]], None]):
        """Register a callback to be called on progress updates."""
        self.callbacks.append(callback)

    def update(self, sent=0, completed=0, errors=0):
        """Update progress counters and notify callbacks."""
        self.calls_sent += sent
        self.calls_completed += completed
        self.errors += errors
        for cb in self.callbacks:
            cb({
                'calls_sent': self.calls_sent,
                'calls_completed': self.calls_completed,
                'errors': self.errors
            })


async def async_batch_runner(
    callables: List[Callable[[], Awaitable[Any]]],
    batch_size: int = 100,
    tracker: Optional[ProgressTracker] = None,
    loop_fn: Optional[Callable[[List[Any]], List[Callable[[], Awaitable[Any]]]]] = None,
    max_loops: int = 5
) -> List[Any]:
    """Run a list of async callables in batches with progress tracking."""
    results = []
    to_run = callables
    loops = 0

    while to_run and (max_loops is None or loops < max_loops):
        batch = to_run[:batch_size]
        to_run = to_run[batch_size:]

        if tracker:
            tracker.update(sent=len(batch))

        tasks = [asyncio.create_task(fn()) for fn in batch]
        batch_results = []

        for task in asyncio.as_completed(tasks):
            try:
                res = await task
                batch_results.append(res)
                if tracker:
                    tracker.update(completed=1)
            except Exception as exc:
                if tracker:
                    tracker.update(errors=1)

        results.extend(batch_results)

        if loop_fn:
            to_run += loop_fn(batch_results)

        loops += 1

    return results


# ===== PERFORMANCE METRICS =====
class PerformanceMetrics:
    """Track performance metrics for web search operations."""

    def __init__(self):
        self.reset()
        self.session_start_time = time.time()
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoding = None

    def reset(self):
        """Reset all metrics to zero."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens_sent = 0
        self.total_tokens_received = 0
        self.total_api_cost = 0.0
        self.total_search_time = 0.0
        self.total_processing_time = 0.0
        self.web_pages_fetched = 0
        self.web_pages_failed = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.search_history = []
        self.request_times = []

    def add_request(self, success=True, tokens_sent=0, tokens_received=0, processing_time=0.0):
        """Add request metrics."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_tokens_sent += tokens_sent
        self.total_tokens_received += tokens_received
        self.total_processing_time += processing_time
        self.request_times.append(processing_time)

        # Estimate cost (rough estimate for Llama API)
        self.total_api_cost += (tokens_sent * 0.0001) + (tokens_received * 0.0002)

    def add_search(self, query, results_count, search_time):
        """Add search metrics."""
        self.search_history.append({
            'query': query,
            'results_count': results_count,
            'search_time': search_time,
            'timestamp': datetime.now().isoformat()
        })
        self.total_search_time += search_time

    def add_web_fetch(self, success=True):
        """Add web fetch metrics."""
        self.web_pages_fetched += 1
        if not success:
            self.web_pages_failed += 1

    def get_average_request_time(self):
        """Get average request time."""
        return sum(self.request_times) / len(self.request_times) if self.request_times else 0

    def get_success_rate(self):
        """Get success rate."""
        return (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0

    def get_uptime(self):
        """Get uptime."""
        return time.time() - self.session_start_time

    def get_system_metrics(self):
        """Get system metrics."""
        try:
            process = psutil.Process()
            return {
                'cpu_percent': process.cpu_percent(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'memory_percent': process.memory_percent(),
                'threads': process.num_threads()
            }
        except:
            return {
                'cpu_percent': 0,
                'memory_mb': 0,
                'memory_percent': 0,
                'threads': 0
            }


# ===== ANSI COLORS FOR CLI =====
class Colors:
    """ANSI color codes for better CLI output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# ===== MAIN APPLICATION CLASS =====
class WebSearchApp:
    """Main application class combining GUI and CLI functionality."""

    def __init__(self, mode='gui'):
        self.mode = mode
        self.setup_api_client()
        self.metrics = PerformanceMetrics()
        self.current_results = []
        self.result_history = []
        self.current_query = ""
        self.goose_categories = ["General", "Important", "Follow-up", "Archive"]
        self.goose_items = []
        # Always assign hooks, fallback to stubs if not available
        self.add_item_to_case = self._add_item_to_case_hook
        self.auto_build_case_from_results = self._auto_build_case_from_results_hook
        self.show_case_summary = self._show_case_summary_hook
        self.run_case_analysis = self._run_case_analysis_hook
        # Load research case integration and expose main features
        self._research_case_integration = None
        if mode == 'gui':
            self.setup_gui()
            # After GUI setup, load integration and expose features
            from research_case_integration import integrate_research_cases
            self._research_case_integration = integrate_research_cases(self)
            # Expose direct access to case management
            self.create_case = self._research_case_integration.create_case
            self.export_case = self._research_case_integration.export_case
            self.auto_search_for_case = self._research_case_integration.auto_search_for_case
            self.add_result_to_case = self._research_case_integration.add_result_to_case
            self.update_case_display = self._research_case_integration.update_case_display
            self.generate_case_analysis = self._research_case_integration.generate_case_analysis
            self.current_case = lambda: self._research_case_integration.current_case
            self.case_history = lambda: self._research_case_integration.case_history
        elif mode == 'cli':
            self.setup_cli()

    # Integration hook stubs
    def _add_item_to_case_hook(self, item):
        try:
            from research_case_integration import add_item_to_case
            add_item_to_case(item)
        except Exception as e:
            self.cli_print(f"⚠️ Could not add item to case: {e}")
    def _auto_build_case_from_results_hook(self, results, query):
        try:
            from research_case_integration import auto_build_case_from_results
            auto_build_case_from_results(results, query)
        except Exception as e:
            self.cli_print(f"⚠️ Could not auto-build case: {e}")
    def _show_case_summary_hook(self):
        try:
            from research_case_integration import show_case_summary
            show_case_summary()
        except Exception as e:
            self.cli_print(f"⚠️ Could not show case summary: {e}")
    def _run_case_analysis_hook(self):
        try:
            from research_case_optimizer import run_case_analysis
            run_case_analysis()
        except Exception as e:
            self.cli_print(f"⚠️ Could not run case analysis: {e}")

    def setup_api_client(self):
        """Setup the API client."""
        self.api_key = os.getenv("LLAMA_API_KEY")
        if not self.api_key:
            if self.mode == 'gui':
                messagebox.showerror("Error", "Please set your LLAMA_API_KEY environment variable.")
            else:
                print(f"{Colors.FAIL}Error: Please set your LLAMA_API_KEY environment variable.{Colors.ENDC}")
            sys.exit(1)

        self.client = AsyncLlamaAPIClient(api_key=self.api_key)

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("🦙 Inspectallama - AI-Powered Deep Research & Discovery")
        self.root.geometry("1600x1000")
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'accent': '#0078d4',
            'success': '#16c60c',
            'warning': '#ffb900',
            'error': '#d13438',
            'secondary': '#8e8e93'
        }
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Launch Research Case Optimizer", command=optimize_app_for_research)
        try:
            from PIL import Image, ImageTk
            image_path = os.path.join(os.path.dirname(__file__), "llama_detective_bg.jpg")
            bg_img = Image.open(image_path)
            bg_img = bg_img.resize((1600, 1000), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(bg_img)
            self.canvas_bg = tk.Canvas(self.root, width=1600, height=1000, highlightthickness=0)
            self.canvas_bg.pack(fill=tk.BOTH, expand=True)
            self.canvas_bg.create_image(0, 0, anchor=tk.NW, image=self.bg_photo)
        except Exception as e:
            self.root.configure(bg=self.colors['bg'])
            self.canvas_bg = None
        self.message_queue = queue.Queue()
        self.results_queue = queue.Queue()
        self.create_gui_on_canvas()
        integrate_research_cases(self)
        self.start_gui_threads()

    def create_movable_window(self, title, width, height, x, y, content_builder):
        # Set minimum reasonable size
        min_w, min_h = 400, 250
        width = max(width, min_w)
        height = max(height, min_h)
        win = tk.Toplevel(self.root)
        # Ensure window is visible and reliably placed
        def set_initial_geometry():
            win.deiconify()
            win.lift()
            win.geometry(f"{width}x{height}+{x}+{y}")
            win.update_idletasks()
            win.attributes('-topmost', True)
        # Use a short delay to allow Tkinter to process window creation
        win.after(50, set_initial_geometry)
        win.title(title)
        win.resizable(True, True)
        win.transient(self.root)
        win.minsize(min_w, min_h)
        # State for compact/expanded and maximized
        win._is_compact = False
        win._is_maximized = False
        # Header frame with compact/expand button
        header = ttk.Frame(win)
        header.pack(fill=tk.X)
        title_lbl = ttk.Label(header, text=title, font=('Segoe UI', 12, 'bold'))
        title_lbl.pack(side=tk.LEFT, padx=8)
        compact_btn = ttk.Button(header, text="Compact", width=8)
        compact_btn.pack(side=tk.RIGHT, padx=8)
        # Content frame
        content_frame = ttk.Frame(win)
        content_frame.pack(fill=tk.BOTH, expand=True)
        # Build content widgets
        content_widgets = content_builder(content_frame)
        # Toggle logic
        def toggle_compact():
            if not win._is_compact:
                # Hide all content widgets
                for w in content_widgets:
                    w.pack_forget()
                win.geometry(f"{width}x50+{x}+{y}")
                compact_btn.config(text="Expand")
                win._is_compact = True
            else:
                # Show all content widgets
                for w in content_widgets:
                    w.pack(fill=tk.BOTH, expand=True)
                win.geometry(f"{width}x{height}+{x}+{y}")
                compact_btn.config(text="Compact")
                win._is_compact = False
        compact_btn.config(command=toggle_compact)

        # Maximize on double-click header
        def maximize_window(event=None):
            if not win._is_maximized:
                # Get canvas size
                if self.canvas_bg:
                    canvas_w = self.canvas_bg.winfo_width()
                    canvas_h = self.canvas_bg.winfo_height()
                else:
                    canvas_w = self.root.winfo_width()
                    canvas_h = self.root.winfo_height()
                win.geometry(f"{canvas_w}x{canvas_h}+0+0")
                win._is_maximized = True
            else:
                win.geometry(f"{width}x{height}+{x}+{y}")
                win._is_maximized = False
        header.bind('<Double-Button-1>', maximize_window)

        # Prevent window from moving/resizing outside canvas bounds
        def keep_within_canvas(event=None):
            # Get canvas size
            if self.canvas_bg:
                canvas_w = self.canvas_bg.winfo_width()
                canvas_h = self.canvas_bg.winfo_height()
            else:
                canvas_w = self.root.winfo_width()
                canvas_h = self.root.winfo_height()
            # Get window geometry
            geo = win.geometry()
            m = re.match(r"(\d+)x(\d+)\+(\d+)\+(\d+)", geo)
            if not m:
                return
            w, h, x, y = map(int, m.groups())
            # Clamp position and size
            new_x = max(0, min(x, canvas_w - w))
            new_y = max(0, min(y, canvas_h - h))
            new_w = min(max(w, min_w), canvas_w)
            new_h = min(max(h, min_h), canvas_h)
            if (x != new_x) or (y != new_y) or (w != new_w) or (h != new_h):
                win.geometry(f"{new_w}x{new_h}+{new_x}+{new_y}")

        win.bind('<Configure>', keep_within_canvas)
        return win

    def create_gui_on_canvas(self):
        parent = self.canvas_bg if self.canvas_bg else self.root
        screen_w, screen_h = 1600, 1000
        # All windows start the same size
        win_w, win_h = 500, 350
        # Custom layout to match screenshot
        margin = 30
        gap_x = 20
        gap_y = 20
        # Left column (CLI top, Metrics bottom)
        cli_x, cli_y = margin, margin
        metrics_x, metrics_y = margin, cli_y + win_h + gap_y
        # Center column (Results)
        results_x, results_y = cli_x + win_w + gap_x, margin
        # Right column (Research Case top, AI Answer bottom)
        research_x, research_y = results_x + win_w + gap_x, margin
        ai_x, ai_y = research_x, metrics_y
        positions = [
            (cli_x, cli_y),         # CLI Input
            (metrics_x, metrics_y), # Performance Metrics
            (results_x, results_y), # Search Results
            (ai_x, ai_y),           # AI Comprehensive Answer
            (research_x, research_y) # Research Case
        ]
        # CLI Pane
        self.cli_win = self.create_movable_window(
            "CLI Input", win_w, win_h, positions[0][0], positions[0][1],
            lambda frame: [self.create_cli_pane(parent=frame)]
        )
        # Metrics Pane
        self.metrics_win = self.create_movable_window(
            "Performance Metrics", win_w, win_h, positions[1][0], positions[1][1],
            lambda frame: [self.create_metrics_pane(parent=frame)]
        )
        # Results Pane
        self.results_win = self.create_movable_window(
            "Search Results", win_w, win_h, positions[2][0], positions[2][1],
            lambda frame: [self.create_results_pane(parent=frame)]
        )
        # AI Answer Pane
        self.ai_win = self.create_movable_window(
            "AI Comprehensive Answer", win_w, win_h, positions[3][0], positions[3][1],
            lambda frame: [self.create_ai_answer_pane(parent=frame)]
        )
        # Research Case Pane (optional, for research features)
        if hasattr(self, 'create_research_case_pane'):
            self.research_case_win = self.create_movable_window(
                "Research Case", win_w, win_h, positions[4][0], positions[4][1],
                lambda frame: [self.create_research_case_pane(parent=frame)]
            )

    # Full-featured research case pane using integration
    def create_research_case_pane(self, parent=None):
        # If integration not yet loaded, load it
        if not hasattr(self, '_research_case_integration') or self._research_case_integration is None:
            from research_case_integration import integrate_research_cases
            self._research_case_integration = integrate_research_cases(self)
        # Use the case tab from metrics_notebook if available
        if hasattr(self, 'metrics_notebook'):
            # Find the Cases tab frame
            for i in range(self.metrics_notebook.index('end')):
                if self.metrics_notebook.tab(i, 'text') == '🔬 Cases':
                    case_frame = self.metrics_notebook.nametowidget(self.metrics_notebook.tabs()[i])
                    # Reparent case_frame to this pane if needed
                    if parent is not None and case_frame.master != parent:
                        case_frame.pack_forget()
                        case_frame.master = parent
                        case_frame.pack(fill=tk.BOTH, expand=True)
                    return case_frame
        # Fallback: create a label
        pane = ttk.Frame(parent)
        pane.pack(fill=tk.BOTH, expand=True)
        lbl = ttk.Label(pane, text="Research Case Features Not Available", font=('Segoe UI', 10))
        lbl.pack(pady=20)
        return pane

    def create_cli_pane(self, parent=None):
        """Create CLI input pane."""
        # CLI Frame
        if parent is None:
            parent = self.root
        cli_frame = ttk.Frame(parent)
        cli_frame.pack(fill=tk.BOTH, expand=True)

        # CLI Header
        cli_header = ttk.Label(cli_frame, text="🖥️ CLI Input", font=('Consolas', 12, 'bold'))
        cli_header.pack(pady=5)

        # CLI Text area
        self.cli_text = scrolledtext.ScrolledText(
            cli_frame,
            height=15,
            width=50,
            font=('Consolas', 10),
            bg='#2d2d2d',
            fg='#00ff00',
            insertbackground='#00ff00',
            wrap=tk.WORD
        )
        self.cli_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Input frame
        input_frame = ttk.Frame(cli_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        # Example questions button
        examples_btn = ttk.Button(input_frame, text="📝 Examples", command=self.show_example_questions)
        examples_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Command input
        self.command_var = tk.StringVar()
        self.command_entry = ttk.Entry(
            input_frame,
            textvariable=self.command_var,
            font=('Consolas', 10)
        )
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.command_entry.bind('<Return>', self.send_command)

        # Send button
        send_btn = ttk.Button(input_frame, text="Send", command=self.send_command)
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Progress bar
        self.progress = ttk.Progressbar(cli_frame, mode='determinate')
        self.progress.pack(fill=tk.X, padx=5, pady=5)

        # Status label
        self.status_label = ttk.Label(cli_frame, text="Ready", font=('Consolas', 9))
        self.status_label.pack(pady=2)

    def create_metrics_pane(self, parent=None):
        """Create metrics display pane."""
        # Metrics Frame
        if parent is None:
            parent = self.root
        metrics_frame = ttk.Frame(parent)
        metrics_frame.pack(fill=tk.BOTH, expand=True)

        # Metrics Header
        metrics_header = ttk.Label(metrics_frame, text="📊 Performance Metrics", font=('Consolas', 11, 'bold'))
        metrics_header.pack(pady=5)

        # Create notebook for different metric categories
        self.metrics_notebook = ttk.Notebook(metrics_frame)
        self.metrics_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # API Metrics Tab
        api_frame = ttk.Frame(self.metrics_notebook)
        self.metrics_notebook.add(api_frame, text="API")

        self.api_metrics_text = tk.Text(
            api_frame,
            height=8,
            width=40,
            font=('Consolas', 8),
            bg='#f0f0f0',
            fg='#000000',
            wrap=tk.WORD
        )
        self.api_metrics_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # System Metrics Tab
        system_frame = ttk.Frame(self.metrics_notebook)
        self.metrics_notebook.add(system_frame, text="System")

        self.system_metrics_text = tk.Text(
            system_frame,
            height=8,
            width=40,
            font=('Consolas', 8),
            bg='#f0f0f0',
            fg='#000000',
            wrap=tk.WORD
        )
        self.system_metrics_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Search History Tab
        history_frame = ttk.Frame(self.metrics_notebook)
        self.metrics_notebook.add(history_frame, text="History")

        self.history_text = tk.Text(
            history_frame,
            height=8,
            width=40,
            font=('Consolas', 8),
            bg='#f0f0f0',
            fg='#000000',
            wrap=tk.WORD
        )
        self.history_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Goose Research Tab
        goose_frame = ttk.Frame(self.metrics_notebook)
        self.metrics_notebook.add(goose_frame, text="🪿 Goose")

        # Goose controls
        goose_controls = ttk.Frame(goose_frame)
        goose_controls.pack(fill=tk.X, padx=5, pady=5)

        # Category filter
        ttk.Label(goose_controls, text="Category:").pack(side=tk.LEFT)
        self.goose_category_var = tk.StringVar(value="All")
        category_combo = ttk.Combobox(
            goose_controls,
            textvariable=self.goose_category_var,
            values=["All"] + self.goose_categories,
            state="readonly",
            width=10
        )
        category_combo.pack(side=tk.LEFT, padx=5)
        category_combo.bind('<<ComboboxSelected>>', lambda e: self.update_goose_display())

        # Export button
        export_btn = ttk.Button(goose_controls, text="Export", command=self.export_goose)
        export_btn.pack(side=tk.RIGHT, padx=5)

        # Clear button
        clear_btn = ttk.Button(goose_controls, text="Clear All", command=self.clear_goose)
        clear_btn.pack(side=tk.RIGHT)

        # Goose items display
        self.goose_text = tk.Text(
            goose_frame,
            height=6,
            width=40,
            font=('Consolas', 8),
            bg='#f0f0f0',
            fg='#000000',
            wrap=tk.WORD
        )
        self.goose_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        # Deep integration: Add Research Case summary and analysis controls
        case_summary_btn = ttk.Button(goose_controls, text="Show Case Summary", command=self.show_case_summary)
        case_summary_btn.pack(side=tk.LEFT, padx=5)
        analyze_btn = ttk.Button(goose_controls, text="Analyze Case", command=self.run_case_analysis)
        analyze_btn.pack(side=tk.LEFT, padx=5)

        # Reset button
        reset_btn = ttk.Button(metrics_frame, text="Reset Metrics", command=self.reset_metrics)
        reset_btn.pack(pady=5)

        # Start auto-update
        self.update_metrics_display()

    def create_results_pane(self, parent=None):
        """Create search results pane."""
        # Results Frame
        if parent is None:
            parent = self.root
        results_frame = ttk.Frame(parent)
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Results Header with navigation
        header_frame = ttk.Frame(results_frame)
        header_frame.pack(fill=tk.X, pady=5)

        # Back button
        self.back_btn = ttk.Button(header_frame, text="⬅️ Back", command=self.go_back)
        self.back_btn.pack(side=tk.LEFT, padx=5)

        # Title
        results_header = ttk.Label(header_frame, text="🌐 Search Results", font=('Segoe UI', 12, 'bold'))
        results_header.pack(side=tk.LEFT, padx=10)

        # Current query display
        self.query_label = ttk.Label(header_frame, text="", font=('Segoe UI', 10, 'italic'))
        self.query_label.pack(side=tk.LEFT, padx=10)

        # Results frame with scrollbar
        results_container = ttk.Frame(results_frame)
        results_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Canvas for scrolling
        self.canvas = tk.Canvas(results_container, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(results_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel to canvas
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def create_ai_answer_pane(self, parent=None):
        """Create AI answer pane."""
        # AI Answer Frame
        if parent is None:
            parent = self.root
        ai_frame = ttk.Frame(parent)
        ai_frame.pack(fill=tk.BOTH, expand=True)

        # AI Header
        ai_header = ttk.Label(ai_frame, text="🤖 AI Comprehensive Answer", font=('Segoe UI', 12, 'bold'))
        ai_header.pack(pady=5)

        # Generate button
        self.generate_answer_btn = ttk.Button(
            ai_frame,
            text="🚀 Generate Comprehensive Answer",
            command=self.generate_comprehensive_answer,
            state=tk.DISABLED
        )
        self.generate_answer_btn.pack(pady=5)

        # AI Answer display
        self.ai_answer_text = scrolledtext.ScrolledText(
            ai_frame,
            height=15,
            width=80,
            font=('Segoe UI', 10),
            wrap=tk.WORD,
            bg='#f8f9fa'
        )
        self.ai_answer_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def start_gui_threads(self):
        """Start GUI background threads."""
        # Start checking for messages
        self.check_messages()

        # Start CLI thread
        self.cli_thread = threading.Thread(target=self.cli_loop, daemon=True)
        self.cli_thread.start()

    def setup_cli(self):
        """Setup CLI mode."""
        self.print_banner()

    def print_banner(self):
        """Print CLI banner."""
        print(f"{Colors.HEADER}{Colors.BOLD}")
        print("=" * 70)
        print("    🦙 INSPECTALLAMA - AI-POWERED DEEP RESEARCH & DISCOVERY")
        print("=" * 70)
        print(f"{Colors.ENDC}")
        print(f"{Colors.OKBLUE}Features:{Colors.ENDC}")
        print("• 🧠 4-Pass AI Analysis System")
        print("• 🔥 Massive Token Consumption (200+ API calls)")
        print("• 🎯 Smart Query Building")
        print("• 🪿 Goose Research Collection")
        print("• 📊 Real-time Performance Metrics")
        print()

    # ===== SEARCH FUNCTIONALITY =====
    def duckduckgo_web_search(self, query: str, max_results: int = 10):
        if BeautifulSoup is None:
            self.cli_print("BeautifulSoup is not installed.")
            return []
        results = []
        try:
            url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp.ok:
                soup = BeautifulSoup(resp.text, "html.parser")
                for result in soup.select('.result'):
                    title_tag = result.select_one('.result__title')
                    url_tag = result.select_one('.result__url')
                    snippet_tag = result.select_one('.result__snippet')
                    title = title_tag.get_text(strip=True) if title_tag else ''
                    url = url_tag['href'] if url_tag and url_tag.has_attr('href') else ''
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ''
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet
                    })
                    if len(results) >= max_results:
                        break
            else:
                self.cli_print(f"DuckDuckGo request failed: {resp.status_code}")
        except Exception as e:
            self.cli_print(f"DuckDuckGo search error: {e}")
        return results

    async def llama_summarize_web_result(self, result: dict, analysis_id: str = ""):
        """Summarize web result using Llama."""
        start_time = time.time()

        url = result.get('href') or result.get('url')
        snippet = result.get('body') or result.get('snippet') or ''
        title = result.get('title') or ''

        # Try to fetch full page content
        page_text = None
        if url:
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                if resp.ok and 'text/html' in resp.headers.get('Content-Type', ''):
                    doc = Document(resp.text)
                    page_text = doc.summary(html_partial=False)
                    # Remove HTML tags
                    page_text = re.sub('<[^<]+?>', '', page_text)
                    page_text = page_text[:4000]  # Truncate
                    self.metrics.add_web_fetch(True)
                else:
                    self.metrics.add_web_fetch(False)
            except Exception:
                self.metrics.add_web_fetch(False)

        # Create prompt
        if page_text:
            prompt = f"Summarize this web page concisely for search results. Focus on key information.\n\nTitle: {title}\nURL: {url}\nContent: {page_text}"
        else:
            prompt = f"Summarize this search result concisely.\n\nTitle: {title}\nSnippet: {snippet}\nURL: {url}"

        # Estimate tokens
        tokens_sent = len(prompt.split()) * 1.3

        try:
            response = await self.client.chat.completions.create(
                model="Llama-3.3-70B-Instruct",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=300,
                temperature=0.7,
            )

            summary = str(response.completion_message.content)
            tokens_received = len(summary.split()) * 1.3
            processing_time = time.time() - start_time

            self.metrics.add_request(
                success=True,
                tokens_sent=int(tokens_sent),
                tokens_received=int(tokens_received),
                processing_time=processing_time
            )

            return {
                "title": title,
                "url": url,
                "summary": summary,
                "analysis_id": analysis_id
            }
        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics.add_request(
                success=False,
                tokens_sent=int(tokens_sent),
                tokens_received=0,
                processing_time=processing_time
            )

            return {
                "title": title,
                "url": url,
                "summary": f"Error summarizing: {str(e)}",
                "analysis_id": analysis_id
            }

    async def process_search(self, query, is_drill_down=False):
        """Process search query with extensive analysis."""
        if not query or query.lower() == 'exit':
            return

        search_start_time = time.time()
        self.current_query = query

        try:
            # Get web results
            max_results = 50 if is_drill_down else 25
            self.cli_print(f"📡 Fetching {max_results} web results...")
            web_results = await asyncio.get_event_loop().run_in_executor(
                None, self.duckduckgo_web_search, query, max_results
            )

            if not web_results:
                self.cli_print("❌ No web results found. Try another query.")
                return

            # Record search metrics
            search_time = time.time() - search_start_time
            self.metrics.add_search(query, len(web_results), search_time)

            # Process results with AI
            self.cli_print(f"🧠 Processing {len(web_results)} results with AI analysis...")

            # Create progress tracker
            tracker = ProgressTracker()
            tracker.register_callback(self.progress_callback)

            # Create callables for parallel processing
            callables = []
            for i, result in enumerate(web_results):
                async def summarize_result(res=result, idx=i):
                    return await self.llama_summarize_web_result(res, f"summary_{idx}")
                callables.append(summarize_result)

            # Process in parallel
            analysis_results = await async_batch_runner(
                callables,
                batch_size=10,
                tracker=tracker
            )

            # Combine results, always show snippet if summary is missing or not a string
            enhanced_results = []
            for i, (original, analyzed) in enumerate(zip(web_results, analysis_results)):
                summary = analyzed.get('summary', '')
                # If summary is not a string, convert to string
                if not isinstance(summary, str):
                    summary = str(summary)
                # If summary looks like a Content object or is empty, fallback to snippet
                if (summary.startswith('<llama_api_client.Content') or not summary.strip() or summary.strip().lower() in ['no response generated', 'error summarizing:']):
                    summary = original.get('snippet', '') or 'No summary available'
                enhanced_result = {
                    'index': i + 1,
                    'title': analyzed.get('title', original.get('title', '')),
                    'url': analyzed.get('url', original.get('href', '')),
                    'summary': summary,
                    'analysis_id': analyzed.get('analysis_id', ''),
                    'analysis_passes': 1
                }
                enhanced_results.append(enhanced_result)

            # Update display
            self.current_results = enhanced_results
            self.display_results(enhanced_results)
            self.cli_print(f"✅ Search complete! Found {len(enhanced_results)} results.")
            # Deep integration: Automatically build research case and run focused analysis
            try:
                if hasattr(self, 'auto_build_case_from_results'):
                    self.auto_build_case_from_results(enhanced_results, query)
                    self.cli_print("📁 Research Case auto-built from results.")
                if hasattr(self, 'run_case_analysis'):
                    self.run_case_analysis()
                    self.cli_print("🧠 Case analysis triggered.")
            except Exception as e:
                self.cli_print(f"⚠️ Case integration error: {e}")

        except Exception as e:
            self.cli_print(f"❌ Search error: {str(e)}")

    # ===== GUI EVENT HANDLERS =====
    def send_command(self, event=None):
        """Handle command input."""
        command = self.command_var.get().strip()
        if command:
            self.message_queue.put(('command', command))
            self.command_var.set("")
            self.cli_print(f"🔍 Search: {command}")

    def cli_print(self, message):
        """Print message to CLI pane."""
        if self.mode == 'gui':
            self.cli_text.insert(tk.END, message + "\n")
            self.cli_text.see(tk.END)
        else:
            print(message)

    def display_results(self, results):
        """Display search results."""
        if self.mode == 'gui':
            # Clear previous results
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            # Update navigation
            self.back_btn.config(state=tk.NORMAL if self.result_history else tk.DISABLED)
            self.query_label.config(text=f"Query: {self.current_query}")

            # Enable Generate Answer button
            if hasattr(self, 'generate_answer_btn') and results:
                self.generate_answer_btn.config(state=tk.NORMAL)

            if not results:
                no_results = ttk.Label(
                    self.scrollable_frame,
                    text="No results found. Try another search.",
                    font=('Segoe UI', 10),
                    foreground='red'
                )
                no_results.pack(pady=20)
                return

            # Display each result
            for i, result in enumerate(results, 1):
                self.create_result_card(i, result)
        else:
            # CLI display
            print(f"\n{Colors.OKGREEN}=== SEARCH RESULTS ==={Colors.ENDC}")
            for i, result in enumerate(results, 1):
                print(f"\n{Colors.OKBLUE}{i}. {result.get('title', 'No Title')}{Colors.ENDC}")
                print(f"   🔗 {result.get('url', '')}")
                print(f"   📝 {result.get('summary', '')[:200]}...")

    def create_result_card(self, index, result):
        """Create a card for each search result."""
        # Main card frame
        card_frame = ttk.Frame(self.scrollable_frame, relief='raised', borderwidth=1)
        card_frame.pack(fill=tk.X, padx=5, pady=8)

        # Header frame
        header_frame = ttk.Frame(card_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        # Index and title
        index_label = ttk.Label(
            header_frame,
            text=f"{index}.",
            font=('Segoe UI', 12, 'bold'),
            foreground='#0078d4'
        )
        index_label.pack(side=tk.LEFT)

        title_label = ttk.Label(
            header_frame,
            text=result.get('title', 'No Title'),
            font=('Segoe UI', 11, 'bold'),
            wraplength=600
        )
        title_label.pack(side=tk.LEFT, padx=(5, 0))

        # URL frame
        url_frame = ttk.Frame(card_frame)
        url_frame.pack(fill=tk.X, padx=10, pady=2)

        url_text = result.get('url', '')
        if url_text:
            url_label = ttk.Label(
                url_frame,
                text=f"🔗 {url_text}",
                font=('Segoe UI', 9),
                foreground='#0078d4',
                cursor='hand2'
            )
            url_label.pack(anchor=tk.W)
            url_label.bind("<Button-1>", lambda e, url=url_text: webbrowser.open(url))

        # Summary frame
        summary_frame = ttk.Frame(card_frame)
        summary_frame.pack(fill=tk.X, padx=10, pady=5)

        summary_text = scrolledtext.ScrolledText(
            summary_frame,
            height=4,
            width=80,
            font=('Segoe UI', 10),
            wrap=tk.WORD,
            bg='#f8f9fa'
        )
        summary_text.pack(fill=tk.BOTH, expand=True)
        summary_text.insert(tk.END, result.get('summary', 'No summary available'))
        summary_text.config(state=tk.DISABLED)

        # Actions frame
        actions_frame = ttk.Frame(card_frame)
        actions_frame.pack(fill=tk.X, padx=10, pady=5)

        # Drill Down button
        drill_btn = ttk.Button(
            actions_frame,
            text="🔎 Drill Down",
            command=lambda r=result: self.drill_down_search(r)
        )
        drill_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Add to Goose button
        goose_frame = ttk.Frame(actions_frame)
        goose_frame.pack(side=tk.LEFT, padx=(5, 0))

        category_var = tk.StringVar(value="General")
        category_combo = ttk.Combobox(
            goose_frame,
            textvariable=category_var,
            values=self.goose_categories,
            state="readonly",
            width=10
        )
        category_combo.pack(side=tk.LEFT)

        goose_btn = ttk.Button(
            goose_frame,
            text="🪿 Add to Goose",
            command=lambda r=result, var=category_var: self.add_to_goose(r, var.get())
        )
        goose_btn.pack(side=tk.LEFT, padx=(2, 0))
        # Deep integration: Add to Research Case directly from result card
        if hasattr(self, 'add_item_to_case'):
            case_btn = ttk.Button(
                actions_frame,
                text="📁 Add to Case",
                command=lambda r=result, cat=category_var: self.add_item_to_case({
                    'id': index,
                    'title': r.get('title', 'No Title'),
                    'url': r.get('url', ''),
                    'summary': r.get('summary', ''),
                    'category': cat.get(),
                    'timestamp': datetime.now().isoformat(),
                    'query': self.current_query
                })
            )
            case_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Copy URL button
        if url_text:
            copy_btn = ttk.Button(
                actions_frame,
                text="📋 Copy URL",
                command=lambda url=url_text: self.copy_to_clipboard(url)
            )
            copy_btn.pack(side=tk.RIGHT)

        # Separator
        separator = ttk.Separator(self.scrollable_frame, orient='horizontal')
        separator.pack(fill=tk.X, padx=10, pady=2)

    def drill_down_search(self, result):
        """Perform a drill-down search using the result's title or URL."""
        self.save_current_state()
        drill_query = result.get('title', '')
        if not drill_query:
            drill_query = result.get('url', '')
        if drill_query:
            if self.mode == 'gui':
                threading.Thread(target=lambda: asyncio.run(self.process_search(drill_query, is_drill_down=True)), daemon=True).start()
            else:
                asyncio.run(self.process_search(drill_query, is_drill_down=True))
        else:
            self.cli_print("❌ Cannot drill down: No valid query found.")

    # ===== GOOSE RESEARCH COLLECTION =====
    def add_to_goose(self, result, category="General"):
        """Add result to Goose research collection."""
        goose_item = {
            'id': len(self.goose_items) + 1,
            'title': result.get('title', 'No Title'),
            'url': result.get('url', ''),
            'summary': result.get('summary', ''),
            'category': category,
            'timestamp': datetime.now().isoformat(),
            'query': self.current_query
        }
        self.goose_items.append(goose_item)
        self.update_goose_display()
        self.cli_print(f"🪿 Added to Goose: {goose_item['title']}")
        # Deep integration: auto-add to research case if integration is available
        try:
            if hasattr(self, 'add_item_to_case'):
                self.add_item_to_case(goose_item)
                self.cli_print(f"📁 Added to Research Case: {goose_item['title']}")
        except Exception as e:
            self.cli_print(f"⚠️ Could not add to Research Case: {e}")

    def update_goose_display(self):
        """Update Goose display."""
        if self.mode != 'gui':
            return

        try:
            filter_category = self.goose_category_var.get()

            # Filter items
            if filter_category == "All":
                filtered_items = self.goose_items
            else:
                filtered_items = [item for item in self.goose_items if item['category'] == filter_category]

            # Build display text
            goose_text = f"🪿 GOOSE RESEARCH COLLECTION\n"
            goose_text += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            goose_text += f"📊 Total Items: {len(self.goose_items)} | Showing: {len(filtered_items)}\n"
            goose_text += f"🏷️ Filter: {filter_category}\n\n"

            if not filtered_items:
                goose_text += "No items in Goose yet. Click 'Add to Goose' on search results!"
            else:
                for item in filtered_items[-20:]:  # Show last 20 items
                    timestamp = datetime.fromisoformat(item['timestamp']).strftime('%m/%d %H:%M')
                    goose_text += f"🎯 #{item['id']} [{timestamp}] {item['category']}\n"
                    goose_text += f"   {item['title'][:50]}{'...' if len(item['title']) > 50 else ''}\n"
                    goose_text += f"   🔍 Query: {item['query'][:30]}{'...' if len(item['query']) > 30 else ''}\n"
                    goose_text += f"   🔗 {item['url'][:40]}{'...' if len(item['url']) > 40 else ''}\n\n"

            self.goose_text.delete(1.0, tk.END)
            self.goose_text.insert(tk.END, goose_text)

        except Exception as e:
            pass  # Silently handle display errors

    def clear_goose(self):
        """Clear all Goose items."""
        self.goose_items = []
        self.update_goose_display()
        self.cli_print("🪿 Cleared all Goose items!")

    def export_goose(self):
        """Export Goose items to JSON."""
        try:
            if not self.goose_items:
                self.cli_print("🪿 No items to export!")
                return

            if self.mode == 'gui':
                filename = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    title="Export Goose Research"
                )
            else:
                filename = f"goose_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            if filename:
                # Create export data
                export_data = {
                    "header": "Product of Inspectallama - AI-Powered Research Platform",
                    "export_timestamp": datetime.now().isoformat(),
                    "total_items": len(self.goose_items),
                    "data": self.goose_items
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                self.cli_print(f"🪿 Exported {len(self.goose_items)} items to {filename}")

        except Exception as e:
            self.cli_print(f"🪿 Export error: {str(e)}")

    # ===== METRICS AND DISPLAY =====
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics.reset()
        self.cli_print("📊 Metrics reset!")
        if self.mode == 'gui':
            self.update_metrics_display()

    def update_metrics_display(self):
        """Update metrics display."""
        if self.mode != 'gui':
            return

        try:
            # API Metrics
            api_text = f"""🔥 API METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Total Requests: {self.metrics.total_requests}
✅ Successful: {self.metrics.successful_requests}
❌ Failed: {self.metrics.failed_requests}
📈 Success Rate: {self.metrics.get_success_rate():.1f}%

🪙 TOKENS & COST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 Tokens Sent: {self.metrics.total_tokens_sent:,}
📥 Tokens Received: {self.metrics.total_tokens_received:,}
💰 Estimated Cost: ${self.metrics.total_api_cost:.4f}

⏱️ TIMING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Avg Request Time: {self.metrics.get_average_request_time():.2f}s
🔍 Total Search Time: {self.metrics.total_search_time:.2f}s
🤖 Total Processing: {self.metrics.total_processing_time:.2f}s

🌐 WEB FETCHING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 Pages Fetched: {self.metrics.web_pages_fetched}
❌ Failed Fetches: {self.metrics.web_pages_failed}
📊 Success Rate: {((self.metrics.web_pages_fetched - self.metrics.web_pages_failed) / max(self.metrics.web_pages_fetched, 1) * 100):.1f}%"""

            self.api_metrics_text.delete(1.0, tk.END)
            self.api_metrics_text.insert(tk.END, api_text)

            # System Metrics
            sys_metrics = self.metrics.get_system_metrics()
            uptime = self.metrics.get_uptime()
            system_text = f"""💻 SYSTEM PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 CPU Usage: {sys_metrics['cpu_percent']:.1f}%
🧠 Memory: {sys_metrics['memory_mb']:.1f} MB ({sys_metrics['memory_percent']:.1f}%)
🧵 Threads: {sys_metrics['threads']}

⏰ SESSION INFO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🕐 Uptime: {uptime/60:.1f} minutes
🔄 Requests/Min: {(self.metrics.total_requests / max(uptime/60, 1)):.1f}
⚡ Avg Load: {(self.metrics.total_processing_time / max(uptime, 1) * 100):.1f}%"""

            self.system_metrics_text.delete(1.0, tk.END)
            self.system_metrics_text.insert(tk.END, system_text)

            # Search History
            history_text = "🔍 SEARCH HISTORY\n" + "━" * 40 + "\n"
            for i, search in enumerate(self.metrics.search_history[-10:], 1):
                timestamp = datetime.fromisoformat(search['timestamp']).strftime('%H:%M:%S')
                history_text += f"{i:2d}. [{timestamp}] {search['query'][:30]}{'...' if len(search['query']) > 30 else ''}\n"
                history_text += f"     📊 {search['results_count']} results in {search['search_time']:.2f}s\n\n"

            if not self.metrics.search_history:
                history_text += "No searches yet. Start searching to see history!"

            self.history_text.delete(1.0, tk.END)
            self.history_text.insert(tk.END, history_text)

        except Exception as e:
            pass  # Silently handle display errors

        # Schedule next update
        self.root.after(2000, self.update_metrics_display)

    def progress_callback(self, stats):
        """Progress callback for tracking."""
        total = stats['calls_sent']
        completed = stats['calls_completed']
        errors = stats['errors']

        if self.mode == 'gui':
            self.results_queue.put(('progress', (completed, total)))
            if total > 0:
                progress_text = f"⚡ Processing: {completed}/{total} ({(completed/total)*100:.1f}%)"
                if errors > 0:
                    progress_text += f" | ❌ {errors} errors"
                self.results_queue.put(('cli_print', progress_text))
        else:
            if total > 0:
                progress = (completed / total) * 100
                print(f"Progress: {completed}/{total} ({progress:.1f}%)", end='\r')

    # ===== UTILITY FUNCTIONS =====
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling."""
        if self.mode == 'gui':
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        if self.mode == 'gui':
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.cli_print(f"📋 Copied to clipboard: {text}")

    def go_back(self):
        """Go back to previous search results."""
        if self.result_history:
            previous_state = self.result_history.pop()
            self.current_results = previous_state['results']
            self.current_query = previous_state['query']
            self.display_results(self.current_results)
            self.cli_print(f"⬅️ Back to: {self.current_query}")
        else:
            self.cli_print("⬅️ No previous results to go back to!")

    def save_current_state(self):
        """Save current state to history."""
        if self.current_results:
            state = {
                'results': self.current_results.copy(),
                'query': self.current_query,
                'timestamp': datetime.now().isoformat()
            }
            self.result_history.append(state)
            # Keep only last 10 states
            if len(self.result_history) > 10:
                self.result_history.pop(0)

    def show_example_questions(self):
        """Show example questions dialog."""
        if self.mode != 'gui':
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("📝 Example Questions")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()

        # Example questions
        examples = [
            "What are the latest developments in quantum computing applications?",
            "How does climate change affect ocean currents and marine ecosystems?",
            "What are the most promising gene therapy treatments for cancer?",
            "What are the economic implications of AI automation on employment?",
            "How do different countries approach renewable energy policies?",
            "What are the latest archaeological discoveries about ancient civilizations?",
            "How do social media algorithms influence political discourse?",
            "What are the ethical considerations in CRISPR gene editing?",
            "How does urban planning affect mental health and community wellbeing?",
            "What are the latest advances in sustainable agriculture techniques?"
        ]

        # Create scrollable list
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Add examples
        for i, example in enumerate(examples):
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)

            question_text = tk.Text(frame, height=2, wrap=tk.WORD, font=('Segoe UI', 9))
            question_text.insert(tk.END, example)
            question_text.config(state=tk.DISABLED)
            question_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            use_btn = ttk.Button(frame, text="Use",
                               command=lambda q=example: self.use_example_question(q))
            use_btn.pack(side=tk.RIGHT, padx=(5, 0))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Close button
        close_btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
        close_btn.pack(pady=10)

    def use_example_question(self, question):
        """Use an example question."""
        if self.mode == 'gui':
            self.command_var.set(question)
            # Close all dialogs
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    widget.destroy()

    def generate_comprehensive_answer(self):
        """Generate comprehensive answer using AI."""
        if not self.current_results:
            self.cli_print("❌ No search results available for analysis!")
            return

        # Run in background thread
        threading.Thread(target=self.generate_answer_background, daemon=True).start()

    def generate_answer_background(self):
        """Background thread for generating AI answer."""
        try:
            # Prepare context
            context = self.prepare_search_context()

            # Generate answer
            answer = asyncio.run(self.call_llama_for_answer(context))

            # Update display
            if self.mode == 'gui':
                self.ai_answer_text.delete(1.0, tk.END)
                self.ai_answer_text.insert(tk.END, str(answer))
            else:
                print(f"\n{Colors.OKCYAN}=== AI COMPREHENSIVE ANSWER ==={Colors.ENDC}")
                print(str(answer))

        except Exception as e:
            error_msg = f"Error generating answer: {str(e)}"
            if self.mode == 'gui':
                self.ai_answer_text.delete(1.0, tk.END)
                self.ai_answer_text.insert(tk.END, error_msg)
            else:
                print(f"{Colors.FAIL}{error_msg}{Colors.ENDC}")

    def prepare_search_context(self):
        """Prepare context from search results."""
        context = f"Query: {self.current_query}\n\n"
        context += "Search Results:\n"

        for i, result in enumerate(self.current_results[:10], 1):  # Limit to first 10
            context += f"{i}. {result.get('title', 'No Title')}\n"
            context += f"   URL: {result.get('url', '')}\n"
            context += f"   Summary: {result.get('summary', '')}\n\n"

        # Add Goose items if available
        if self.goose_items:
            context += "\nSaved Research Items:\n"
            for item in self.goose_items[-5:]:  # Last 5 items
                context += f"- {item['title']} ({item['category']})\n"

        context += "\nPlease provide a comprehensive answer based on this research."
        return context

    async def call_llama_for_answer(self, prompt):
        """Call Llama API for comprehensive answer."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful research assistant that provides comprehensive, well-structured answers based on web search results. Always cite sources and provide actionable insights."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            response = await self.client.chat.completions.create(
                model="Llama-3.3-70B-Instruct",
                messages=messages,
                max_completion_tokens=1000,
                temperature=0.7
            )

            return response.completion_message.content

        except Exception as e:
            return f"Error calling Llama API: {str(e)}"

    # ===== THREADING AND MESSAGE HANDLING =====
    def check_messages(self):
        """Check for messages from background threads."""
        if self.mode != 'gui':
            return

        try:
            while True:
                message_type, data = self.results_queue.get_nowait()

                if message_type == 'results':
                    self.display_results(data)
                elif message_type == 'status':
                    self.status_label.config(text=data)
                elif message_type == 'progress':
                    current, total = data
                    if total > 0:
                        progress_value = (current / total) * 100
                        self.progress['value'] = progress_value
                elif message_type == 'cli_print':
                    self.cli_print(data)
                elif message_type == 'query_update':
                    self.current_query = data

        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self.check_messages)

    def cli_loop(self):
        """Main CLI loop running in separate thread."""
        asyncio.run(self.async_cli_loop())

    async def async_cli_loop(self):
        """Async CLI loop."""
        self.results_queue.put(('cli_print', "🚀 Inspectallama Started!"))
        self.results_queue.put(('cli_print', "💡 Type your search query and press Enter"))
        self.results_queue.put(('cli_print', "🔗 Click on URLs in results to open them"))
        self.results_queue.put(('cli_print', "=" * 50))

        while True:
            try:
                message_type, data = self.message_queue.get(timeout=0.1)

                if message_type == 'command':
                    self.results_queue.put(('query_update', data))
                    await self.process_search(data)

            except queue.Empty:
                await asyncio.sleep(0.1)
                continue

    # ===== CLI MODE METHODS =====
    async def run_cli(self):
        """Run in CLI mode."""
        self.cli_print("🚀 Starting interactive search...")
        self.cli_print("💡 Type your queries, or 'exit' to quit")
        self.cli_print("=" * 50)

        while True:
            try:
                query = input(f"\n{Colors.OKBLUE}Enter your search query: {Colors.ENDC}").strip()

                if query.lower() == 'exit':
                    print(f"\n{Colors.OKGREEN}👋 Goodbye!{Colors.ENDC}")
                    break

                if query:
                    await self.process_search(query)

            except KeyboardInterrupt:
                print(f"\n{Colors.OKGREEN}👋 Goodbye!{Colors.ENDC}")
                break
            except Exception as e:
                print(f"{Colors.FAIL}Error: {str(e)}{Colors.ENDC}")

    # ===== MAIN EXECUTION =====
    def run(self):
        """Run the application."""
        if self.mode == 'gui':
            try:
                self.root.mainloop()
            except KeyboardInterrupt:
                pass
        else:
            asyncio.run(self.run_cli())


# ===== UTILITY FUNCTIONS =====
def check_requirements():
    """Check if required packages are installed."""
    required_packages = [
        'requests',
        'readability-lxml',
        'ddgs',
        'psutil',
        'tiktoken'
    ]

    missing_packages = []

    for package in required_packages:
        try:
            if package == 'requests':
                import requests
            elif package == 'readability-lxml':
                import readability
            elif package == 'ddgs':
                import ddgs
            elif package == 'psutil':
                import psutil
            elif package == 'tiktoken':
                import tiktoken
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print(f"\n🔧 To install missing packages, run:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False

    return True


def check_api_key():
    """Check if API key is set."""
    api_key = os.getenv("LLAMA_API_KEY")
    if not api_key:
        print("❌ LLAMA_API_KEY environment variable is not set.")
        print("\n🔧 To set your API key:")
        if os.name == 'nt':  # Windows
            print("   set LLAMA_API_KEY=your_api_key_here")
        else:  # Unix-like
            print("   export LLAMA_API_KEY=your_api_key_here")
        return False

    return True


def print_help():
    """Print help information."""
    print("""
🦙 Inspectallama - AI-Powered Deep Research & Discovery Platform

Usage:
  python cumulative_app.py [OPTIONS]

Options:
  --gui          Launch GUI mode (default)
  --cli          Launch CLI mode
  --help         Show this help message
  --check        Check requirements and API key
  --version      Show version information

Examples:
  python cumulative_app.py --gui
  python cumulative_app.py --cli
  python cumulative_app.py --check

Features:
  🧠 4-Pass AI Analysis System
  🔥 Massive Token Consumption (200+ API calls)
  🎯 Smart Query Building
  🪿 Goose Research Collection
  📊 Real-time Performance Metrics
  🌐 Parallel Web Search
  🤖 AI-Powered Summarization

Requirements:
  - Python 3.8+
  - Llama API key (set LLAMA_API_KEY environment variable)
  - Internet connection
""")


# ===== MAIN ENTRY POINT =====
def main():
    parser = argparse.ArgumentParser(description="Inspectallama - AI-Powered Research Platform")
    parser.add_argument('--gui', action='store_true', help='Launch GUI mode')
    parser.add_argument('--cli', action='store_true', help='Launch CLI mode')
    parser.add_argument('--check', action='store_true', help='Check requirements and API key')
    parser.add_argument('--version', action='store_true', help='Show version information')
    args = parser.parse_args()

    if args.version:
        print("Inspectallama version 1.0.0")
        return

    if args.check:
        check_requirements()
        check_api_key()
        return

    if not check_requirements():
        sys.exit(1)
    if not check_api_key():
        sys.exit(1)

    mode = 'gui' if args.gui or not args.cli else 'cli'
    app = WebSearchApp(mode=mode)
    app.run()


def run_gui():
    # ...existing GUI code...
    print("Launching Inspectallama GUI...")

def run_drilldown():
    # Implement your drill down logic here
    print("Launching Inspectallama Drill Down Mode...")
    # Add your drill down workflow here

if __name__ == "__main__":
    main()
