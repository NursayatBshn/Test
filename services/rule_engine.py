import json
import os

class RuleEngine:
    def __init__(self, rules_file):
        self.rules_file = self._resolve_rules_file(rules_file)
        self.rules = self._load_rules()

    def _resolve_rules_file(self, rules_file):
        if os.path.isabs(rules_file) or os.path.exists(rules_file):
            return rules_file

        project_root = os.path.dirname(os.path.dirname(__file__))
        project_rules_file = os.path.join(project_root, rules_file)
        if os.path.exists(project_rules_file):
            return project_rules_file

        return rules_file

    def _load_rules(self):
        if not os.path.exists(self.rules_file):
            self.rules_source = "missing"
            return []
        
        with open(self.rules_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                self.rules_source = "invalid"
                return []

        if data.get("enabled"):
            self.rules_source = self.rules_file
            return data.get("rules", [])

        self.rules_source = "disabled"
        return []

    def get_target_folder(self, filename):
        """Determine the target folder based on the file extension."""
        match = self.get_matching_rule(filename)
        if match:
            return match.get("target")

        return "Others" # Default folder if no rule is found.

    def get_matching_rule(self, filename):
        """Return the rule that matches the filename, if any."""
        filename = filename.lower()
        
        for rule in sorted(self.rules, key=lambda item: len(item.get("extension", "")), reverse=True):
            extension = rule.get("extension", "").lower()
            if extension and filename.endswith(extension):
                return rule

        return None

    def get_target_folders(self):
        """Return all target folders managed by the rules."""
        return {rule.get("target") for rule in self.rules if rule.get("target")}
