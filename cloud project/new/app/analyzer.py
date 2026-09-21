import re
from typing import Any, Dict, List

from app.rules_loader import load_detection_rules

SEVERITY_ORDER = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

# Performance limits for real-world logs
MAX_LOG_SIZE_MB = 50
MAX_PATTERNS_TO_CHECK = 1000


def _prepare_rules() -> List[Dict[str, Any]]:
    """Load detection rules and compile regex patterns safely."""
    prepared_rules: List[Dict[str, Any]] = []

    for rule in load_detection_rules():
        pattern = rule.get("pattern", "")
        if not pattern:
            continue

        compiled_pattern = None
        if rule.get("regex"):
            try:
                # Compile with optimizations: re.IGNORECASE for case-insensitive,
                # re.MULTILINE for line-based matching
                compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                # Skip rules with invalid regex
                print(f"Warning: Skipping rule {rule.get('id')} - Invalid regex: {e}")
                continue

        prepared_rules.append({
            "id": rule.get("id"),
            "type": rule.get("type"),
            "severity": rule.get("severity"),
            "description": rule.get("description"),
            "pattern": pattern,
            "regex": bool(rule.get("regex")),
            "repeatThreshold": rule.get("repeatThreshold"),
            "compiled_pattern": compiled_pattern,
        })

    return prepared_rules


DETECTION_RULES = _prepare_rules()


def _sanitize_logs(logs: str) -> str:
    """
    Sanitize logs to handle encoding issues and unusual characters.
    Handles: invalid UTF-8, null bytes, control characters.
    """
    # Replace null bytes
    logs = logs.replace('\x00', '')
    
    # Remove control characters except newlines and tabs
    logs = ''.join(ch for ch in logs if ord(ch) >= 32 or ch in '\n\r\t')
    
    # Handle common encoding issues
    try:
        # Try to encode/decode to fix any encoding issues
        logs = logs.encode('utf-8', errors='replace').decode('utf-8')
    except Exception:
        pass
    
    return logs


def _count_matches(rule: Dict[str, Any], logs: str, normalized_logs: str) -> int:
    """Count matches for a rule using regex or case-insensitive substring search."""
    try:
        if rule["regex"]:
            compiled_pattern = rule.get("compiled_pattern")
            if not compiled_pattern:
                return 0
            
            # Use finditer for better performance with large logs
            matches = list(compiled_pattern.finditer(logs))
            return len(matches)

        # For non-regex patterns, use substring search
        return normalized_logs.count(rule["pattern"].lower())
    except Exception as e:
        # Silently handle regex timeout or other matching errors
        print(f"Warning: Error matching rule {rule.get('id')}: {e}")
        return 0


def _validate_log_size(logs: str) -> tuple[bool, str]:
    """Validate log size to prevent performance issues."""
    try:
        size_mb = len(logs.encode('utf-8')) / (1024 * 1024)
        if size_mb > MAX_LOG_SIZE_MB:
            return False, f"Log size ({size_mb:.2f}MB) exceeds maximum ({MAX_LOG_SIZE_MB}MB). Please analyze logs in chunks."
        return True, ""
    except Exception as e:
        return False, f"Error validating log size: {str(e)}"


def detect_threat(logs: str) -> Dict[str, Any]:
    """Inspect logs against detection rules and return the highest severity threat."""
    
    # Validate log size
    is_valid, error_msg = _validate_log_size(logs)
    if not is_valid:
        return {
            "status": "error",
            "error": error_msg,
            "type": "processing_error",
            "severity": "INFO",
            "matchedRules": [],
        }
    
    try:
        # Sanitize logs to handle encoding issues
        logs = _sanitize_logs(logs)
        normalized_logs = logs.lower()
        matches: List[Dict[str, Any]] = []

        for rule in DETECTION_RULES:
            try:
                count = _count_matches(rule, logs, normalized_logs)
                if count <= 0:
                    continue

                repeat_threshold = rule.get("repeatThreshold")
                if repeat_threshold is not None and count < repeat_threshold:
                    continue

                matches.append(
                    {
                        "id": rule.get("id"),
                        "type": rule.get("type"),
                        "severity": rule.get("severity"),
                        "description": rule.get("description"),
                        "pattern": rule.get("pattern"),
                        "count": count,
                    }
                )
            except Exception as e:
                # Continue processing other rules if one fails
                print(f"Error processing rule {rule.get('id')}: {e}")
                continue

        if not matches:
            return {
                "status": "clean",
                "type": "none",
                "severity": "LOW",
                "matchedRules": [],
            }

        # Sort by severity (highest first)
        highest = max(
            matches,
            key=lambda item: SEVERITY_ORDER.get(item.get("severity", "LOW"), 1),
        )

        return {
            "status": "threat_detected",
            "type": highest["type"],
            "severity": highest["severity"],
            "matchedRules": matches,
            "topRuleId": highest.get("id"),
            "totalMatches": len(matches),
        }
    
    except Exception as e:
        # Return error response if analysis fails
        return {
            "status": "error",
            "error": f"Analysis error: {str(e)}",
            "type": "processing_error",
            "severity": "INFO",
            "matchedRules": [],
        }
