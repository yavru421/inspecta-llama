#!/usr/bin/env python3
"""
Research Case Builder & Analysis Optimizer for Inspectallama
Enhanced version with specialized research case building tools
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from datetime import datetime
import webbrowser
import subprocess
import sys

class ResearchCaseBuilder:
    def __init__(self, goose_items=None):
        self.goose_items = goose_items or []
        self.case_templates = {
            "Legal Research": {
                "categories": ["Legal Precedents", "Case Law", "Statutes", "Regulations", "Expert Opinions"],
                "analysis_focus": "Legal implications, precedent analysis, regulatory compliance",
                "export_format": "chronological_with_citations"
            },
            "Market Research": {
                "categories": ["Market Data", "Competitor Analysis", "Consumer Insights", "Trends", "Forecasts"],
                "analysis_focus": "Market dynamics, competitive landscape, opportunity assessment",
                "export_format": "executive_summary_with_data"
            },
            "Academic Research": {
                "categories": ["Primary Sources", "Secondary Sources", "Literature Review", "Methodology", "Findings"],
                "analysis_focus": "Academic rigor, source credibility, methodology evaluation",
                "export_format": "academic_with_bibliography"
            },
            "Investigative Research": {
                "categories": ["Facts", "Sources", "Timeline", "Connections", "Evidence"],
                "analysis_focus": "Fact verification, source reliability, timeline reconstruction",
                "export_format": "investigative_timeline"
            },
            "Technical Research": {
                "categories": ["Technical Specs", "Implementation", "Best Practices", "Troubleshooting", "Updates"],
                "analysis_focus": "Technical accuracy, implementation feasibility, best practices",
                "export_format": "technical_documentation"
            }
        }

    def create_case_template(self, case_type):
        """Create a structured case template"""
        if case_type not in self.case_templates:
            return None

        template = self.case_templates[case_type]

        case_structure = {
            "case_type": case_type,
            "created_date": datetime.now().isoformat(),
            "categories": template["categories"],
            "analysis_focus": template["analysis_focus"],
            "export_format": template["export_format"],
            "research_items": {category: [] for category in template["categories"]},
            "case_notes": "",
            "key_findings": [],
            "next_steps": [],
            "confidence_level": "medium"
        }

        return case_structure

    def auto_categorize_goose_items(self, case_type):
        """Auto-categorize existing Goose items into case structure"""
        if case_type not in self.case_templates:
            return

        template = self.case_templates[case_type]
        categorized_items = {category: [] for category in template["categories"]}

        # Simple keyword-based categorization
        category_keywords = {
            "Legal Precedents": ["precedent", "case", "court", "ruling", "judgment"],
            "Case Law": ["law", "legal", "statute", "code", "regulation"],
            "Market Data": ["market", "sales", "revenue", "data", "statistics"],
            "Competitor Analysis": ["competitor", "competition", "rival", "market share"],
            "Primary Sources": ["study", "research", "paper", "journal", "original"],
            "Secondary Sources": ["review", "analysis", "commentary", "interpretation"],
            "Facts": ["fact", "evidence", "proof", "document", "record"],
            "Timeline": ["date", "when", "chronology", "sequence", "history"],
            "Technical Specs": ["specification", "technical", "API", "documentation", "manual"],
            "Implementation": ["install", "setup", "configure", "deploy", "implement"]
        }

        for item in self.goose_items:
            item_text = f"{item['title']} {item['summary']} {item['query']}".lower()

            best_category = "General"
            max_score = 0

            for category, keywords in category_keywords.items():
                if category in template["categories"]:
                    score = sum(1 for keyword in keywords if keyword in item_text)
                    if score > max_score:
                        max_score = score
                        best_category = category

            if best_category in categorized_items:
                categorized_items[best_category].append(item)
            else:
                # Default to first category if no match
                categorized_items[template["categories"][0]].append(item)

        return categorized_items

    def generate_case_analysis(self, case_data, analysis_type="comprehensive"):
        """Generate comprehensive case analysis"""
        analysis = {
            "case_overview": self._generate_case_overview(case_data),
            "key_insights": self._extract_key_insights(case_data),
            "source_analysis": self._analyze_sources(case_data),
            "gaps_identified": self._identify_research_gaps(case_data),
            "recommendations": self._generate_recommendations(case_data),
            "confidence_assessment": self._assess_confidence(case_data)
        }

        return analysis

    def _generate_case_overview(self, case_data):
        """Generate case overview"""
        total_items = sum(len(items) for items in case_data["research_items"].values())

        overview = f"""
Case Type: {case_data['case_type']}
Created: {case_data['created_date']}
Total Research Items: {total_items}
Analysis Focus: {case_data['analysis_focus']}

Category Breakdown:
"""

        for category, items in case_data["research_items"].items():
            overview += f"• {category}: {len(items)} items\n"

        return overview

    def _extract_key_insights(self, case_data):
        """Extract key insights from research items"""
        insights = []

        for category, items in case_data["research_items"].items():
            if items:
                insights.append(f"**{category}:**")
                for item in items[:3]:  # Top 3 items per category
                    insights.append(f"  - {item['title']}")
                    if item.get('summary'):
                        insights.append(f"    Summary: {item['summary'][:100]}...")
                insights.append("")

        return "\n".join(insights)

    def _analyze_sources(self, case_data):
        """Analyze source quality and diversity"""
        all_items = []
        for items in case_data["research_items"].values():
            all_items.extend(items)

        if not all_items:
            return "No sources to analyze."

        # Source domain analysis
        domains = {}
        for item in all_items:
            if item.get('url'):
                try:
                    domain = item['url'].split('/')[2]
                    domains[domain] = domains.get(domain, 0) + 1
                except:
                    pass

        analysis = "Source Analysis:\n"
        analysis += f"Total Sources: {len(all_items)}\n"
        analysis += f"Unique Domains: {len(domains)}\n\n"

        analysis += "Top Domains:\n"
        for domain, count in sorted(domains.items(), key=lambda x: x[1], reverse=True)[:5]:
            analysis += f"• {domain}: {count} sources\n"

        return analysis

    def _identify_research_gaps(self, case_data):
        """Identify potential research gaps"""
        gaps = []

        for category, items in case_data["research_items"].items():
            if not items:
                gaps.append(f"No items in {category} category")
            elif len(items) < 3:
                gaps.append(f"Limited items in {category} category ({len(items)} items)")

        if not gaps:
            return "No obvious research gaps identified."

        return "Potential Research Gaps:\n" + "\n".join(f"• {gap}" for gap in gaps)

    def _generate_recommendations(self, case_data):
        """Generate research recommendations"""
        recommendations = []

        # Based on case type
        case_type = case_data["case_type"]

        if case_type == "Legal Research":
            recommendations.extend([
                "Verify all legal precedents with official court records",
                "Check for recent updates to relevant statutes",
                "Consider jurisdictional variations"
            ])
        elif case_type == "Market Research":
            recommendations.extend([
                "Validate market data with multiple sources",
                "Analyze competitor responses to market changes",
                "Consider seasonal and cyclical factors"
            ])
        elif case_type == "Academic Research":
            recommendations.extend([
                "Ensure peer-reviewed sources for key claims",
                "Check citation patterns and research impact",
                "Review methodology for potential biases"
            ])

        # Generic recommendations
        recommendations.extend([
            "Cross-reference key facts with multiple sources",
            "Update research with latest available information",
            "Document source credibility and limitations"
        ])

        return "Recommendations:\n" + "\n".join(f"• {rec}" for rec in recommendations)

    def _assess_confidence(self, case_data):
        """Assess research confidence level"""
        total_items = sum(len(items) for items in case_data["research_items"].values())

        if total_items == 0:
            return "Low - No research items"
        elif total_items < 5:
            return "Medium-Low - Limited research items"
        elif total_items < 15:
            return "Medium - Adequate research base"
        elif total_items < 30:
            return "Medium-High - Good research coverage"
        else:
            return "High - Comprehensive research coverage"

    def export_case_report(self, case_data, analysis_data, filename):
        """Export comprehensive case report"""
        report = {
            "header": "Research Case Report - Product of the System, System by JD",
            "generated_date": datetime.now().isoformat(),
            "case_data": case_data,
            "analysis": analysis_data,
            "export_metadata": {
                "total_research_items": sum(len(items) for items in case_data["research_items"].values()),
                "export_format": case_data.get("export_format", "standard"),
                "confidence_level": case_data.get("confidence_level", "medium")
            }
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return f"Case report exported to {filename}"

class ResearchCaseGUI:
    def __init__(self, parent, goose_items=None):
        self.parent = parent
        self.builder = ResearchCaseBuilder(goose_items)
        self.current_case = None

        self.create_gui()

    def create_gui(self):
        """Create the research case builder GUI"""
        # Main frame
        main_frame = ttk.Frame(self.parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=5)

        title_label = ttk.Label(header_frame, text="🔬 Research Case Builder",
                               font=('Segoe UI', 14, 'bold'))
        title_label.pack(side=tk.LEFT)

        # Case type selection
        case_type_frame = ttk.LabelFrame(main_frame, text="Case Type", padding=10)
        case_type_frame.pack(fill=tk.X, pady=5)

        self.case_type_var = tk.StringVar(value="Academic Research")
        case_type_combo = ttk.Combobox(case_type_frame, textvariable=self.case_type_var,
                                      values=list(self.builder.case_templates.keys()),
                                      state="readonly")
        case_type_combo.pack(side=tk.LEFT, padx=5)

        create_btn = ttk.Button(case_type_frame, text="Create Case Structure",
                               command=self.create_case_structure)
        create_btn.pack(side=tk.LEFT, padx=5)

        auto_categorize_btn = ttk.Button(case_type_frame, text="Auto-Categorize Goose Items",
                                        command=self.auto_categorize_items)
        auto_categorize_btn.pack(side=tk.LEFT, padx=5)

        # Case display area
        self.case_notebook = ttk.Notebook(main_frame)
        self.case_notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Analysis controls
        analysis_frame = ttk.Frame(main_frame)
        analysis_frame.pack(fill=tk.X, pady=5)

        analyze_btn = ttk.Button(analysis_frame, text="🔍 Generate Case Analysis",
                                command=self.generate_analysis)
        analyze_btn.pack(side=tk.LEFT, padx=5)

        export_btn = ttk.Button(analysis_frame, text="📄 Export Case Report",
                               command=self.export_case_report)
        export_btn.pack(side=tk.LEFT, padx=5)

        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready - Select a case type to begin")
        self.status_label.pack(pady=5)

    def create_case_structure(self):
        """Create a new case structure"""
        case_type = self.case_type_var.get()
        self.current_case = self.builder.create_case_template(case_type)

        if self.current_case:
            self.update_case_display()
            self.status_label.config(text=f"Created {case_type} case structure")

    def auto_categorize_items(self):
        """Auto-categorize Goose items into case structure"""
        if not self.current_case:
            messagebox.showwarning("No Case", "Please create a case structure first")
            return

        case_type = self.case_type_var.get()
        categorized = self.builder.auto_categorize_goose_items(case_type)

        if categorized:
            self.current_case["research_items"] = categorized
            self.update_case_display()
            total_items = sum(len(items) for items in categorized.values())
            self.status_label.config(text=f"Auto-categorized {total_items} items")

    def update_case_display(self):
        """Update the case display in the notebook"""
        # Clear existing tabs
        for tab in self.case_notebook.tabs():
            self.case_notebook.forget(tab)

        if not self.current_case:
            return

        # Create tabs for each category
        for category, items in self.current_case["research_items"].items():
            tab_frame = ttk.Frame(self.case_notebook)
            self.case_notebook.add(tab_frame, text=f"{category} ({len(items)})")

            # Create scrollable text area for items
            text_area = tk.Text(tab_frame, wrap=tk.WORD, font=('Segoe UI', 10))
            scrollbar = ttk.Scrollbar(tab_frame, orient="vertical", command=text_area.yview)
            text_area.configure(yscrollcommand=scrollbar.set)

            # Add items to text area
            if items:
                for i, item in enumerate(items, 1):
                    text_area.insert(tk.END, f"{i}. {item['title']}\n")
                    text_area.insert(tk.END, f"   URL: {item['url']}\n")
                    text_area.insert(tk.END, f"   Query: {item['query']}\n")
                    if item.get('summary'):
                        text_area.insert(tk.END, f"   Summary: {item['summary'][:200]}...\n")
                    text_area.insert(tk.END, "\n")
            else:
                text_area.insert(tk.END, f"No items in {category} category yet.\n")
                text_area.insert(tk.END, "Add items from your Goose collection or new searches.")

            text_area.config(state=tk.DISABLED)

            text_area.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

    def generate_analysis(self):
        """Generate case analysis"""
        if not self.current_case:
            messagebox.showwarning("No Case", "Please create a case structure first")
            return

        analysis = self.builder.generate_case_analysis(self.current_case)

        # Create analysis window
        analysis_window = tk.Toplevel(self.parent)
        analysis_window.title("Case Analysis")
        analysis_window.geometry("800x600")

        # Create scrollable text area
        text_area = tk.Text(analysis_window, wrap=tk.WORD, font=('Segoe UI', 10))
        scrollbar = ttk.Scrollbar(analysis_window, orient="vertical", command=text_area.yview)
        text_area.configure(yscrollcommand=scrollbar.set)

        # Add analysis content
        text_area.insert(tk.END, "🔬 RESEARCH CASE ANALYSIS\n")
        text_area.insert(tk.END, "=" * 60 + "\n\n")

        for section, content in analysis.items():
            text_area.insert(tk.END, f"📊 {section.upper().replace('_', ' ')}\n")
            text_area.insert(tk.END, "-" * 40 + "\n")
            text_area.insert(tk.END, f"{content}\n\n")

        text_area.config(state=tk.DISABLED)

        text_area.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Store analysis for export
        self.current_analysis = analysis
        self.status_label.config(text="Case analysis generated")

    def export_case_report(self):
        """Export case report"""
        if not self.current_case:
            messagebox.showwarning("No Case", "Please create a case structure first")
            return

        if not hasattr(self, 'current_analysis'):
            messagebox.showwarning("No Analysis", "Please generate case analysis first")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Case Report"
        )

        if filename:
            result = self.builder.export_case_report(
                self.current_case, self.current_analysis, filename
            )
            self.status_label.config(text=result)
            messagebox.showinfo("Export Complete", result)

def optimize_app_for_research():
    """Main function to optimize the app for research cases"""
    print("🔬 Research Case Builder & Analysis Optimizer")
    print("=" * 50)
    print()

    # Create main window
    root = tk.Tk()
    root.title("Research Case Builder & Analysis Optimizer")
    root.geometry("1200x800")

    # Create demo GUI (in real app, this would integrate with existing Goose data)
    demo_goose_items = [
        {
            "title": "Quantum Computing Applications in Cryptography",
            "url": "https://example.com/quantum-crypto",
            "summary": "Analysis of quantum computing impact on current cryptographic methods",
            "query": "quantum computing cryptography",
            "category": "General"
        },
        {
            "title": "Legal Framework for AI Ethics",
            "url": "https://example.com/ai-ethics-law",
            "summary": "Overview of emerging legal frameworks for AI governance",
            "query": "AI ethics legal framework",
            "category": "Important"
        }
    ]

    app = ResearchCaseGUI(root, demo_goose_items)

    # Show optimization tips
    tips_window = tk.Toplevel(root)
    tips_window.title("🚀 Research Optimization Tips")
    tips_window.geometry("600x400")

    tips_text = tk.Text(tips_window, wrap=tk.WORD, font=('Segoe UI', 10))
    tips_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tips_content = """🚀 RESEARCH OPTIMIZATION FEATURES

📋 CASE TEMPLATES
• Legal Research: Precedents, case law, statutes
• Market Research: Market data, competitor analysis
• Academic Research: Primary/secondary sources
• Investigative Research: Facts, timeline, evidence
• Technical Research: Specs, implementation, practices

🎯 AUTO-CATEGORIZATION
• Automatically sorts Goose items into relevant categories
• Uses keyword matching for intelligent classification
• Helps organize large research collections

🔍 COMPREHENSIVE ANALYSIS
• Case overview with source breakdown
• Key insights extraction
• Source quality assessment
• Research gap identification
• Confidence level assessment

📊 EXPORT FORMATS
• JSON reports with full metadata
• Structured by case type requirements
• Includes analysis and recommendations
• Professional formatting for sharing

🛠️ INTEGRATION FEATURES
• Works with existing Goose research collection
• Maintains compatibility with current search workflow
• Adds research case building to existing tools
• Preserves all original functionality

💡 RESEARCH BEST PRACTICES
• Verify sources across multiple references
• Document confidence levels for each finding
• Track research methodology and limitations
• Regular updates to maintain currency
• Cross-reference key facts and findings

🔧 USAGE WORKFLOW
1. Create case structure for your research type
2. Auto-categorize existing Goose items
3. Continue adding items through normal search
4. Generate comprehensive case analysis
5. Export structured research report

This optimizer enhances your existing research capabilities with structured case building and professional analysis tools."""

    tips_text.insert(tk.END, tips_content)
    tips_text.config(state=tk.DISABLED)

    print("🎯 Research Case Builder launched successfully!")
    print("📋 Available case templates:")
    for case_type in ResearchCaseBuilder().case_templates.keys():
        print(f"   • {case_type}")
    print()
    print("🔍 Create a case structure and auto-categorize your Goose items to begin!")

    root.mainloop()

if __name__ == "__main__":
    optimize_app_for_research()
