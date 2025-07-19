#!/usr/bin/env python3
"""
Research Case Integration for Inspectallama
Adds research case building capabilities directly to the main app
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from datetime import datetime
import threading
import asyncio

class ResearchCaseIntegration:
    """Integration class to add research case building to the main app"""

    def __init__(self, web_search_gui):
        self.main_app = web_search_gui
        self.case_templates = {
            "Legal Research": {
                "categories": ["Legal Precedents", "Case Law", "Statutes", "Regulations", "Expert Opinions"],
                "analysis_focus": "Legal implications, precedent analysis, regulatory compliance",
                "search_strategies": [
                    "case law precedent {topic}",
                    "legal statute {topic}",
                    "court ruling {topic}",
                    "regulatory framework {topic}"
                ]
            },
            "Market Research": {
                "categories": ["Market Data", "Competitor Analysis", "Consumer Insights", "Trends", "Forecasts"],
                "analysis_focus": "Market dynamics, competitive landscape, opportunity assessment",
                "search_strategies": [
                    "market analysis {topic}",
                    "competitor strategy {topic}",
                    "market trends {topic}",
                    "industry forecast {topic}"
                ]
            },
            "Academic Research": {
                "categories": ["Primary Sources", "Secondary Sources", "Literature Review", "Methodology", "Findings"],
                "analysis_focus": "Academic rigor, source credibility, methodology evaluation",
                "search_strategies": [
                    "academic study {topic}",
                    "research paper {topic}",
                    "peer reviewed {topic}",
                    "scholarly article {topic}"
                ]
            },
            "Technical Research": {
                "categories": ["Documentation", "Implementation", "Best Practices", "Troubleshooting", "Updates"],
                "analysis_focus": "Technical accuracy, implementation feasibility, best practices",
                "search_strategies": [
                    "technical documentation {topic}",
                    "implementation guide {topic}",
                    "best practices {topic}",
                    "troubleshooting {topic}"
                ]
            }
        }

        self.current_case = None
        self.case_history = []

    def add_case_building_tab(self):
        """Add research case building tab to the main app"""
        if not hasattr(self.main_app, 'metrics_notebook'):
            return

        # Create case building tab
        case_frame = ttk.Frame(self.main_app.metrics_notebook)
        self.main_app.metrics_notebook.add(case_frame, text="🔬 Cases")

        # Case controls
        controls_frame = ttk.Frame(case_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        # Case type selection
        ttk.Label(controls_frame, text="Case Type:").pack(side=tk.LEFT)
        self.case_type_var = tk.StringVar(value="Academic Research")
        case_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.case_type_var,
            values=list(self.case_templates.keys()),
            state="readonly",
            width=15
        )
        case_combo.pack(side=tk.LEFT, padx=5)

        # Create case button
        create_btn = ttk.Button(controls_frame, text="Create", command=self.create_case)
        create_btn.pack(side=tk.LEFT, padx=2)

        # Auto-search button
        auto_search_btn = ttk.Button(controls_frame, text="Auto-Search", command=self.auto_search_for_case)
        auto_search_btn.pack(side=tk.LEFT, padx=2)

        # Export button
        export_btn = ttk.Button(controls_frame, text="Export", command=self.export_case)
        export_btn.pack(side=tk.RIGHT)

        # Case display
        self.case_text = tk.Text(
            case_frame,
            height=8,
            width=40,
            font=('Consolas', 8),
            bg='#f0f0f0',
            fg='#000000',
            wrap=tk.WORD
        )
        self.case_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Initial display
        self.update_case_display()

    def create_case(self):
        """Create a new research case"""
        case_type = self.case_type_var.get()
        template = self.case_templates[case_type]

        self.current_case = {
            "type": case_type,
            "created": datetime.now().isoformat(),
            "categories": template["categories"],
            "analysis_focus": template["analysis_focus"],
            "search_strategies": template["search_strategies"],
            "items": {category: [] for category in template["categories"]},
            "notes": "",
            "status": "active"
        }

        # Auto-categorize existing Goose items
        self.auto_categorize_goose_items()

        self.update_case_display()
        self.main_app.cli_print(f"🔬 Created {case_type} case")

    def auto_categorize_goose_items(self):
        """Auto-categorize existing Goose items into current case"""
        if not self.current_case or not self.main_app.goose_items:
            return

        # Keywords for categorization
        category_keywords = {
            "Legal Precedents": ["precedent", "case", "court", "ruling", "judgment", "decision"],
            "Case Law": ["law", "legal", "statute", "code", "regulation", "act"],
            "Market Data": ["market", "sales", "revenue", "data", "statistics", "numbers"],
            "Competitor Analysis": ["competitor", "competition", "rival", "market share", "competitive"],
            "Primary Sources": ["study", "research", "paper", "journal", "original", "first-hand"],
            "Secondary Sources": ["review", "analysis", "commentary", "interpretation", "summary"],
            "Documentation": ["documentation", "manual", "guide", "reference", "API", "spec"],
            "Implementation": ["implementation", "setup", "install", "configure", "deploy", "build"],
            "Best Practices": ["best practice", "recommendation", "guideline", "standard", "pattern"],
            "Troubleshooting": ["troubleshoot", "debug", "fix", "error", "problem", "issue", "solution"]
        }

        categorized_count = 0
        for item in self.main_app.goose_items:
            item_text = f"{item['title']} {item['summary']} {item['query']}".lower()

            best_category = None
            max_score = 0

            for category, keywords in category_keywords.items():
                if category in self.current_case["categories"]:
                    score = sum(1 for keyword in keywords if keyword in item_text)
                    if score > max_score:
                        max_score = score
                        best_category = category

            # Add to category if good match found
            if best_category and max_score > 0:
                self.current_case["items"][best_category].append({
                    "title": item["title"],
                    "url": item["url"],
                    "summary": item["summary"],
                    "query": item["query"],
                    "category": item["category"],
                    "added_to_case": datetime.now().isoformat()
                })
                categorized_count += 1

        if categorized_count > 0:
            self.main_app.cli_print(f"🎯 Auto-categorized {categorized_count} items into case")

    def auto_search_for_case(self):
        """Automatically search for items to build the case"""
        if not self.current_case:
            self.main_app.cli_print("❌ No active case. Create a case first!")
            return

        # Get current query as base topic
        if not self.main_app.current_query:
            self.main_app.cli_print("❌ No search query available. Search first!")
            return

        base_topic = self.main_app.current_query
        search_strategies = self.current_case["search_strategies"]

        self.main_app.cli_print(f"🔍 Auto-searching for {self.current_case['type']} case...")

        # Launch searches in background
        search_thread = threading.Thread(
            target=self.execute_auto_searches,
            args=(base_topic, search_strategies),
            daemon=True
        )
        search_thread.start()

    def execute_auto_searches(self, base_topic, search_strategies):
        """Execute automatic searches for case building"""
        try:
            for strategy in search_strategies:
                query = strategy.format(topic=base_topic)
                self.main_app.cli_print(f"🔍 Searching: {query}")

                # Add to message queue for processing
                self.main_app.message_queue.put(('command', query))

                # Wait between searches to avoid overwhelming
                threading.Event().wait(2)

        except Exception as e:
            self.main_app.cli_print(f"❌ Auto-search error: {str(e)}")

    def add_result_to_case(self, result, category=None):
        """Add a search result to the current case"""
        if not self.current_case:
            return False

        # Auto-determine category if not specified
        if not category:
            category = self.determine_result_category(result)

        if category not in self.current_case["items"]:
            category = self.current_case["categories"][0]  # Default to first category

        case_item = {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "summary": result.get("summary", ""),
            "query": self.main_app.current_query,
            "added_to_case": datetime.now().isoformat(),
            "analysis_passes": result.get("analysis_passes", 1)
        }

        self.current_case["items"][category].append(case_item)
        self.update_case_display()

        self.main_app.cli_print(f"📁 Added to case [{category}]: {case_item['title']}")
        return True

    def determine_result_category(self, result):
        """Determine the best category for a result"""
        if not self.current_case:
            return "General"

        result_text = f"{result.get('title', '')} {result.get('summary', '')}".lower()

        # Simple keyword matching
        category_scores = {}
        for category in self.current_case["categories"]:
            score = 0
            category_lower = category.lower()

            # Check for category keywords in result
            if any(word in result_text for word in category_lower.split()):
                score += 2

            # Check for related keywords
            if "legal" in category_lower and any(word in result_text for word in ["law", "court", "legal", "regulation"]):
                score += 3
            elif "market" in category_lower and any(word in result_text for word in ["market", "business", "industry"]):
                score += 3
            elif "technical" in category_lower and any(word in result_text for word in ["technical", "code", "API", "documentation"]):
                score += 3

            category_scores[category] = score

        # Return category with highest score
        best_category = max(category_scores, key=category_scores.get)
        return best_category if category_scores[best_category] > 0 else self.current_case["categories"][0]

    def update_case_display(self):
        """Update the case display"""
        self.case_text.delete(1.0, tk.END)

        if not self.current_case:
            self.case_text.insert(tk.END, "🔬 RESEARCH CASE BUILDER\n")
            self.case_text.insert(tk.END, "=" * 30 + "\n\n")
            self.case_text.insert(tk.END, "📋 Available Case Types:\n")
            for case_type in self.case_templates.keys():
                self.case_text.insert(tk.END, f"• {case_type}\n")
            self.case_text.insert(tk.END, "\n💡 Select a case type and click 'Create' to begin!\n")
            self.case_text.insert(tk.END, "\n🔍 After creating a case, use 'Auto-Search' to find relevant items.")
            return

        # Display current case
        self.case_text.insert(tk.END, f"🔬 {self.current_case['type'].upper()}\n")
        self.case_text.insert(tk.END, "=" * 30 + "\n")
        self.case_text.insert(tk.END, f"📅 Created: {self.current_case['created'][:10]}\n")
        self.case_text.insert(tk.END, f"🎯 Focus: {self.current_case['analysis_focus']}\n\n")

        # Category breakdown
        total_items = 0
        for category, items in self.current_case["items"].items():
            count = len(items)
            total_items += count
            self.case_text.insert(tk.END, f"📁 {category}: {count} items\n")

            # Show top 2 items per category
            for item in items[:2]:
                title = item["title"][:30] + "..." if len(item["title"]) > 30 else item["title"]
                self.case_text.insert(tk.END, f"   • {title}\n")

        self.case_text.insert(tk.END, f"\n📊 Total Items: {total_items}\n")

        if total_items > 0:
            self.case_text.insert(tk.END, "\n✅ Case ready for export!")
        else:
            self.case_text.insert(tk.END, "\n💡 Add items by searching or using Auto-Search")

    def export_case(self):
        """Export the current case"""
        if not self.current_case:
            self.main_app.cli_print("❌ No case to export!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Research Case"
        )

        if filename:
            try:
                # Prepare export data
                export_data = {
                    "header": "Research Case Export - Product of the System, System by JD",
                    "export_date": datetime.now().isoformat(),
                    "case_data": self.current_case,
                    "analysis": self.generate_case_analysis(),
                    "metadata": {
                        "total_items": sum(len(items) for items in self.current_case["items"].values()),
                        "categories": len(self.current_case["categories"]),
                        "export_version": "1.0"
                    }
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                self.main_app.cli_print(f"📄 Case exported to {filename}")
                messagebox.showinfo("Export Complete", f"Case exported successfully to {filename}")

            except Exception as e:
                self.main_app.cli_print(f"❌ Export error: {str(e)}")
                messagebox.showerror("Export Error", f"Failed to export case: {str(e)}")

    def generate_case_analysis(self):
        """Generate analysis of the current case"""
        if not self.current_case:
            return {}

        analysis = {
            "overview": f"Research case of type '{self.current_case['type']}' with focus on {self.current_case['analysis_focus']}",
            "item_distribution": {},
            "timeline": [],
            "recommendations": []
        }

        # Item distribution
        for category, items in self.current_case["items"].items():
            analysis["item_distribution"][category] = {
                "count": len(items),
                "percentage": len(items) / max(sum(len(items) for items in self.current_case["items"].values()), 1) * 100
            }

        # Timeline of additions
        all_items = []
        for category, items in self.current_case["items"].items():
            for item in items:
                all_items.append({
                    "category": category,
                    "title": item["title"],
                    "added": item.get("added_to_case", ""),
                    "query": item.get("query", "")
                })

        # Sort by addition time
        all_items.sort(key=lambda x: x["added"])
        analysis["timeline"] = all_items[-10:]  # Last 10 items

        # Recommendations
        total_items = sum(len(items) for items in self.current_case["items"].values())

        if total_items < 5:
            analysis["recommendations"].append("Consider adding more research items for comprehensive analysis")

        empty_categories = [cat for cat, items in self.current_case["items"].items() if not items]
        if empty_categories:
            analysis["recommendations"].append(f"Research needed in categories: {', '.join(empty_categories)}")

        if total_items > 0:
            analysis["recommendations"].append("Case has sufficient items for preliminary analysis")

        return analysis

    def enhance_goose_with_case_actions(self):
        """Add case-building actions to Goose items"""
        if not hasattr(self.main_app, 'goose_text'):
            return

        # This would integrate with the existing Goose display
        # to add "Add to Case" buttons for each item
        pass

def integrate_research_cases(web_search_gui):
    """Integrate research case building into the main web search GUI"""
    integration = ResearchCaseIntegration(web_search_gui)

    # Add case building tab
    integration.add_case_building_tab()

    # Enhance the add_to_goose method to also consider case building
    original_add_to_goose = web_search_gui.add_to_goose

    def enhanced_add_to_goose(result, category="General"):
        # Call original method
        original_add_to_goose(result, category)

        # Also add to current case if available
        if integration.current_case and hasattr(integration, 'add_result_to_case'):
            integration.add_result_to_case(result)

    web_search_gui.add_to_goose = enhanced_add_to_goose

    # Add case building button to result cards
    original_create_result_card = web_search_gui.create_result_card

    def enhanced_create_result_card(index, result):
        # Call original method
        original_create_result_card(index, result)

        # Could add case-specific buttons here
        # This would require modifying the card creation
        pass

    web_search_gui.create_result_card = enhanced_create_result_card

    web_search_gui.cli_print("🔬 Research case building integration loaded!")
    web_search_gui.cli_print("📋 Use the 'Cases' tab to create and manage research cases")

    return integration

# Example usage - this would be called from the main app
def main():
    """Example of how to use the integration"""
    print("🔬 Research Case Integration")
    print("This module adds research case building to the main app")
    print("Use integrate_research_cases(web_search_gui) to enable")

if __name__ == "__main__":
    main()
