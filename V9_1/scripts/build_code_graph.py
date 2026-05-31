#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import ast
import json
import datetime


class CallGraphVisitor(ast.NodeVisitor):
    def __init__(self):
        self.current_class = None
        self.current_function = None
        self.metadata = {
            "classes": {},
            "functions": {},
            "calls": [],
            "imports": []
        }

    def visit_Import(self, node):
        for alias in node.names:
            self.metadata["imports"].append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.metadata["imports"].append(node.module)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        old_class = self.current_class
        self.current_class = node.name

        self.metadata["classes"][node.name] = {
            "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
            "lineno": node.lineno
        }

        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        old_function = self.current_function
        full_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
        self.current_function = full_name

        self.metadata["functions"][full_name] = {
            "lineno": node.lineno,
            "args": [arg.arg for arg in node.args.args]
        }

        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node):
        call_name = None

        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                call_name = f"{node.func.value.id}.{node.func.attr}"
            else:
                call_name = node.func.attr

        if call_name and self.current_function:
            self.metadata["calls"].append({
                "caller": self.current_function,
                "callee": call_name,
                "lineno": node.lineno
            })

        self.generic_visit(node)


class QuantCallGraphEngine:
    def __init__(self, target_dir="projects", output_path="reports/code_graph_index.json"):
        self.target_dir = os.path.abspath(target_dir)
        self.output_path = os.path.abspath(output_path)
        self.global_graph = {}

    def analyze_repository(self):
        print(f"[*] Building Code Graph: {self.target_dir}")

        if not os.path.exists(self.target_dir):
            print(f"[ERROR] Target path not found: {self.target_dir}")
            return False

        ignored = [".venv", "node_modules", "logs", "reports", "__pycache__", ".git"]

        for root, _, files in os.walk(self.target_dir):
            if any(x in root for x in ignored):
                continue

            for file in files:
                if not file.endswith(".py"):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, os.getcwd())

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        source = f.read()

                    tree = ast.parse(source, filename=full_path)
                    visitor = CallGraphVisitor()
                    visitor.visit(tree)

                    if visitor.metadata["functions"] or visitor.metadata["imports"]:
                        self.global_graph[rel_path] = visitor.metadata

                except SyntaxError as e:
                    print(f"[WARNING] Syntax error skipped: {rel_path} | {e}")
                except Exception as e:
                    print(f"[WARNING] File skipped: {rel_path} | {e}")

        self.export_graph()
        return True

    def export_graph(self):
        payload = {
            "generated_at": datetime.datetime.now().isoformat(),
            "total_indexed_files": len(self.global_graph),
            "graph_data": self.global_graph
        }

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        print("[SUCCESS] Code Graph generated")
        print(f"Output: {self.output_path}")
        print(f"Indexed files: {len(self.global_graph)}")


if __name__ == "__main__":
    engine = QuantCallGraphEngine(
        target_dir="projects",
        output_path="reports/code_graph_index.json"
    )
    engine.analyze_repository()
