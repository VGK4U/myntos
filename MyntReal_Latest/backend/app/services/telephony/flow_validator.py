"""
Call Flow Graph Validation Engine — MyntOS Native Telephony
Performs rigorous structural, semantic, and security validation on Call Flow DAGs before publishing.
Detects missing entry nodes, unreachable branches, invalid configurations, missing fallbacks,
and unbounded infinite loops while safely permitting controlled IVR retry loops.
Created: Sep 2026
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict, deque
import re


VALID_NODE_TYPES = {
    'trigger_did',
    'time_router',
    'caller_lookup',
    'speak_prompt',
    'play_audio',
    'ivr_menu',
    'dial_user',
    'dial_ring_group',
    'dial_queue',
    'voicemail',
    'forward_pstn',
    'hangup'
}

TERMINAL_NODE_TYPES = {
    'dial_user',
    'dial_ring_group',
    'dial_queue',
    'voicemail',
    'forward_pstn',
    'hangup'
}


class FlowValidationError:
    def __init__(self, node_key: Optional[str], error_type: str, message: str, severity: str = 'error'):
        self.node_key = node_key
        self.error_type = error_type
        self.message = message
        self.severity = severity  # 'error' | 'warning'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'node_key': self.node_key,
            'error_type': self.error_type,
            'message': self.message,
            'severity': self.severity
        }


class CallFlowValidator:
    """
    Validates Call Flow graph structure and node properties.
    Ensures complete, safe, and robust execution topology before activation.
    """

    @classmethod
    def validate_flow_graph(
        cls,
        flow_data: Dict[str, Any],
        company_id: int,
        db=None
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate a full flow graph containing nodes and edges.
        Returns (is_valid: bool, issues: List[dict]).
        """
        issues: List[FlowValidationError] = []

        if not isinstance(flow_data, dict):
            return False, [{'node_key': None, 'error_type': 'INVALID_STRUCTURE', 'message': 'Flow data must be a JSON object', 'severity': 'error'}]

        nodes = flow_data.get('nodes', [])
        edges = flow_data.get('edges', [])

        if not isinstance(nodes, list) or len(nodes) == 0:
            return False, [{'node_key': None, 'error_type': 'EMPTY_FLOW', 'message': 'Flow must contain at least one node', 'severity': 'error'}]

        node_map: Dict[str, Dict[str, Any]] = {}
        trigger_nodes = []

        # 1. Inspect and index all nodes
        for idx, node in enumerate(nodes):
            if not isinstance(node, dict):
                issues.append(FlowValidationError(None, 'INVALID_NODE', f'Node at index {idx} is not an object'))
                continue

            node_key = node.get('id') or node.get('node_key')
            if not node_key or not isinstance(node_key, str):
                issues.append(FlowValidationError(None, 'MISSING_NODE_KEY', f'Node at index {idx} has missing or invalid ID'))
                continue

            node_key = node_key.strip()
            if node_key in node_map:
                issues.append(FlowValidationError(node_key, 'DUPLICATE_NODE_KEY', f'Duplicate node key "{node_key}"'))
                continue

            node_type = node.get('type') or node.get('node_type')
            if not node_type or node_type not in VALID_NODE_TYPES:
                issues.append(FlowValidationError(node_key, 'INVALID_NODE_TYPE', f'Unknown node type "{node_type}" for node {node_key}'))
                continue

            node_map[node_key] = node

            if node_type == 'trigger_did':
                trigger_nodes.append(node_key)

            # Node-specific configuration validations
            cls._validate_node_config(node, node_key, node_type, issues, company_id, db)

        # 2. Validate Entry Trigger Node
        if len(trigger_nodes) == 0:
            issues.append(FlowValidationError(None, 'MISSING_TRIGGER', 'Flow must have exactly one "trigger_did" entry node'))
        elif len(trigger_nodes) > 1:
            issues.append(FlowValidationError(trigger_nodes[1], 'MULTIPLE_TRIGGERS', 'Flow cannot have multiple "trigger_did" nodes in a single flow graph'))

        # 3. Inspect Edges / Transitions
        outgoing_edges: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        incoming_edges: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for e_idx, edge in enumerate(edges):
            if not isinstance(edge, dict):
                issues.append(FlowValidationError(None, 'INVALID_EDGE', f'Edge at index {e_idx} is not an object'))
                continue

            src = (edge.get('from') or edge.get('source_node') or edge.get('source_node_key') or '').strip()
            tgt = (edge.get('to') or edge.get('target_node') or edge.get('target_node_key') or '').strip()
            cond = (edge.get('condition') or 'always').strip().lower()

            if not src or src not in node_map:
                issues.append(FlowValidationError(src or None, 'INVALID_EDGE_SOURCE', f'Edge refers to non-existent source node "{src}"'))
                continue
            if not tgt or tgt not in node_map:
                issues.append(FlowValidationError(tgt or None, 'INVALID_EDGE_TARGET', f'Edge from "{src}" refers to non-existent target node "{tgt}"'))
                continue

            outgoing_edges[src].append({'target': tgt, 'condition': cond, 'edge': edge})
            incoming_edges[tgt].append({'source': src, 'condition': cond, 'edge': edge})

        # 4. Validate Reachability from Entry Node
        if len(trigger_nodes) == 1:
            entry_node = trigger_nodes[0]
            visited: Set[str] = set()
            queue = deque([entry_node])

            while queue:
                curr = queue.popleft()
                if curr in visited:
                    continue
                visited.add(curr)
                for out in outgoing_edges.get(curr, []):
                    nxt = out['target']
                    if nxt not in visited:
                        queue.append(nxt)

            # Check for orphaned unreachable nodes
            for n_key, n_val in node_map.items():
                if n_key not in visited:
                    issues.append(FlowValidationError(n_key, 'UNREACHABLE_NODE', f'Node "{n_val.get("name", n_key)}" is unreachable from the entry trigger', severity='warning'))

        # 5. Check Dead Ends and Outgoing Transitions per Node Type
        for n_key, n_val in node_map.items():
            n_type = n_val.get('type') or n_val.get('node_type')
            outs = outgoing_edges.get(n_key, [])

            if n_type == 'ivr_menu':
                cfg = n_val.get('config', {})
                valid_digits = [str(d) for d in cfg.get('valid_digits', [])]
                if not valid_digits and cfg.get('options'):
                    valid_digits = [str(opt.get('digit') or opt.get('key')) for opt in cfg.get('options') if opt.get('digit') or opt.get('key')]
                handled_conditions = {o.get('condition', '').strip().lower() for o in outs}

                for d in valid_digits:
                    expected_cond = f"digit_{d}"
                    if expected_cond not in handled_conditions and f"key_{d}" not in handled_conditions and d not in handled_conditions:
                        issues.append(FlowValidationError(n_key, 'UNHANDLED_IVR_DIGIT', f'IVR Menu "{n_val.get("name", n_key)}" defines option {d} but has no outgoing connection for it'))

                # Check timeout/invalid fallback
                if not any(c in handled_conditions for c in ('timeout', 'invalid', 'fallback', 'timeout_or_invalid', 'always', 'default', '0')):
                    issues.append(FlowValidationError(n_key, 'MISSING_IVR_FALLBACK', f'IVR Menu "{n_val.get("name", n_key)}" has no timeout or invalid fallback branch', severity='warning'))

            elif n_type == 'time_router':
                handled_conditions = {o.get('condition', '').strip().lower() for o in outs}
                if 'open' not in handled_conditions and 'always' not in handled_conditions:
                    issues.append(FlowValidationError(n_key, 'MISSING_OPEN_BRANCH', f'Time Router "{n_val.get("name", n_key)}" has no branch for "open" hours'))
                if 'closed' not in handled_conditions and 'after_hours' not in handled_conditions and 'fallback' not in handled_conditions:
                    issues.append(FlowValidationError(n_key, 'MISSING_CLOSED_BRANCH', f'Time Router "{n_val.get("name", n_key)}" has no branch for "closed" hours'))

            elif n_type not in TERMINAL_NODE_TYPES:
                if len(outs) == 0:
                    issues.append(FlowValidationError(n_key, 'DEAD_END_NODE', f'Node "{n_val.get("name", n_key)}" ({n_type}) has no outgoing connection'))

        # 6. Cycle & Loop Safety Analysis
        cls._validate_loop_safety(node_map, outgoing_edges, issues)

        # Determine overall validity
        has_errors = any(i.severity == 'error' for i in issues)
        return not has_errors, [i.to_dict() for i in issues]

    @classmethod
    def _validate_node_config(
        cls,
        node: Dict[str, Any],
        node_key: str,
        node_type: str,
        issues: List[FlowValidationError],
        company_id: int,
        db=None
    ):
        config = node.get('config') or {}

        if node_type == 'trigger_did':
            did = config.get('did_number')
            if did:
                clean_did = re.sub(r'[^\d+]', '', str(did))
                if len(clean_did) < 10:
                    issues.append(FlowValidationError(node_key, 'INVALID_DID_FORMAT', f'Trigger DID "{did}" is not a valid telephone number'))

        elif node_type == 'speak_prompt':
            text = config.get('text') or config.get('prompt_text')
            if not text or not str(text).strip():
                issues.append(FlowValidationError(node_key, 'EMPTY_PROMPT_TEXT', f'Speak prompt in node "{node_key}" has no text to speak'))

        elif node_type == 'play_audio':
            url = config.get('audio_url')
            if not url or not str(url).strip().startswith(('http://', 'https://', '/')):
                issues.append(FlowValidationError(node_key, 'INVALID_AUDIO_URL', f'Play audio node "{node_key}" requires a valid HTTP/HTTPS audio URL'))

        elif node_type == 'ivr_menu':
            text = config.get('text') or config.get('prompt_text')
            if not text or not str(text).strip():
                issues.append(FlowValidationError(node_key, 'EMPTY_IVR_PROMPT', f'IVR Menu in node "{node_key}" requires prompt text'))
            timeout = config.get('timeout_seconds', 6)
            if not isinstance(timeout, (int, float)) or timeout < 2 or timeout > 30:
                issues.append(FlowValidationError(node_key, 'INVALID_IVR_TIMEOUT', f'IVR timeout must be between 2 and 30 seconds'))

        elif node_type == 'dial_user':
            staff_id = config.get('staff_id')
            if not staff_id:
                issues.append(FlowValidationError(node_key, 'MISSING_STAFF_TARGET', f'Dial User node "{node_key}" requires a designated staff_id'))
            elif db:
                staff_emp = db.query(StaffEmployee).filter(StaffEmployee.id == staff_id).first()
                if not staff_emp:
                    issues.append(FlowValidationError(node_key, 'INVALID_STAFF_ID', f'Designated staff #{staff_id} does not exist'))
                elif (staff_emp.status or '').lower() != 'active':
                    issues.append(FlowValidationError(node_key, 'INACTIVE_STAFF_MEMBER', f'Staff member "{staff_emp.full_name}" (#{staff_id}) is not ACTIVE'))

        elif node_type == 'dial_ring_group':
            group_id = config.get('ring_group_id')
            if not group_id:
                issues.append(FlowValidationError(node_key, 'MISSING_RING_GROUP', f'Dial Ring Group node "{node_key}" requires a ring_group_id'))

        elif node_type == 'forward_pstn':
            dest = config.get('destination_phone')
            if not dest or len(re.sub(r'[^\d]', '', str(dest))) < 10:
                issues.append(FlowValidationError(node_key, 'INVALID_FORWARD_PHONE', f'Forward PSTN node "{node_key}" requires a valid 10+ digit destination phone'))

    @classmethod
    def _validate_loop_safety(
        cls,
        node_map: Dict[str, Dict[str, Any]],
        outgoing_edges: Dict[str, List[Dict[str, Any]]],
        issues: List[FlowValidationError]
    ):
        """
        Permits controlled retry loops (e.g. IVR -> Invalid -> Retry IVR) while
        rejecting un-escapable infinite loops.
        """
        # Tarjan's algorithm / DFS for Strongly Connected Components (cycles)
        visited = set()
        rec_stack = set()
        cycles: List[List[str]] = []

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for out in outgoing_edges.get(node, []):
                nxt = out['target']
                if nxt not in visited:
                    dfs(nxt, path)
                elif nxt in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(nxt)
                    cycles.append(path[cycle_start:] + [nxt])

            path.pop()
            rec_stack.remove(node)

        for n_key in node_map:
            if n_key not in visited:
                dfs(n_key, [])

        for cycle in cycles:
            # Check if cycle contains at least one node with a bounded exit condition (e.g. IVR with max_retries or fallback)
            has_exit = False
            for c_node in cycle[:-1]:
                c_outs = outgoing_edges.get(c_node, [])
                for out in c_outs:
                    if out['target'] not in cycle:
                        has_exit = True
                        break
                if has_exit:
                    break

            if not has_exit:
                cycle_str = " -> ".join(cycle)
                issues.append(FlowValidationError(cycle[0], 'UNBOUNDED_INFINITE_LOOP', f'Detected infinite cycle with no exit path: {cycle_str}'))
            else:
                # Controlled loop — add warning to ensure retry count is configured
                cycle_str = " -> ".join(cycle)
                issues.append(FlowValidationError(cycle[0], 'CONTROLLED_RETRY_LOOP', f'Flow contains loop ({cycle_str}) — ensure retry limit is enforced during runtime', severity='warning'))
