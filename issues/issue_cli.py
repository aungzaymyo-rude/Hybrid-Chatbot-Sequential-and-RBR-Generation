from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

LOG_PATH = Path(__file__).resolve().parent / 'issue_log.jsonl'

VALID_SEVERITIES = {'low', 'medium', 'high', 'critical'}
VALID_STATUSES = {'open', 'in_progress', 'blocked', 'closed'}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_events() -> List[Dict[str, Any]]:
    if not LOG_PATH.exists():
        return []
    events: List[Dict[str, Any]] = []
    with LOG_PATH.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def _append_event(event: Dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')


def _next_issue_id(events: Iterable[Dict[str, Any]]) -> int:
    max_id = 0
    for event in events:
        max_id = max(max_id, int(event.get('issue_id', 0)))
    return max_id + 1


def _parse_csv(value: str | None) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def _apply_event(state: Dict[int, Dict[str, Any]], event: Dict[str, Any]) -> None:
    issue_id = int(event['issue_id'])
    if event['event'] == 'create':
        state[issue_id] = {
            'issue_id': issue_id,
            'title': event.get('title', ''),
            'description': event.get('description', ''),
            'severity': event.get('severity', 'low'),
            'status': event.get('status', 'open'),
            'owner': event.get('owner', ''),
            'tags': event.get('tags', []),
            'related_files': event.get('related_files', []),
            'created_at': event.get('timestamp'),
            'updated_at': event.get('timestamp'),
        }
        return

    current = state.get(issue_id)
    if not current:
        return

    if event['event'] == 'update':
        for key in ['title', 'description', 'severity', 'status', 'owner']:
            if key in event and event[key] is not None:
                current[key] = event[key]
        if 'tags' in event and event['tags']:
            current['tags'] = list({*current.get('tags', []), *event['tags']})
        if 'related_files' in event and event['related_files']:
            current['related_files'] = list({*current.get('related_files', []), *event['related_files']})
        current['updated_at'] = event.get('timestamp')
        return

    if event['event'] == 'close':
        current['status'] = 'closed'
        current['updated_at'] = event.get('timestamp')


def _build_state(events: Iterable[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    state: Dict[int, Dict[str, Any]] = {}
    for event in events:
        _apply_event(state, event)
    return state


def cmd_create(args: argparse.Namespace) -> None:
    events = _read_events()
    issue_id = _next_issue_id(events)

    severity = args.severity.lower()
    if severity not in VALID_SEVERITIES:
        raise SystemExit(f'Invalid severity: {severity}')

    event = {
        'timestamp': _now(),
        'event': 'create',
        'issue_id': issue_id,
        'title': args.title,
        'description': args.description or '',
        'severity': severity,
        'status': 'open',
        'owner': args.owner or '',
        'tags': _parse_csv(args.tags),
        'related_files': _parse_csv(args.related_files),
    }
    _append_event(event)
    print(f'Created issue {issue_id}')


def cmd_update(args: argparse.Namespace) -> None:
    events = _read_events()
    state = _build_state(events)
    issue_id = int(args.id)
    if issue_id not in state:
        raise SystemExit(f'Issue {issue_id} not found')

    severity = args.severity.lower() if args.severity else None
    if severity and severity not in VALID_SEVERITIES:
        raise SystemExit(f'Invalid severity: {severity}')

    status = args.status.lower() if args.status else None
    if status and status not in VALID_STATUSES:
        raise SystemExit(f'Invalid status: {status}')

    event = {
        'timestamp': _now(),
        'event': 'update',
        'issue_id': issue_id,
        'title': args.title,
        'description': args.description,
        'severity': severity,
        'status': status,
        'owner': args.owner,
        'tags': _parse_csv(args.tags),
        'related_files': _parse_csv(args.related_files),
        'note': args.note or '',
    }
    _append_event(event)
    print(f'Updated issue {issue_id}')


def cmd_close(args: argparse.Namespace) -> None:
    events = _read_events()
    state = _build_state(events)
    issue_id = int(args.id)
    if issue_id not in state:
        raise SystemExit(f'Issue {issue_id} not found')

    event = {
        'timestamp': _now(),
        'event': 'close',
        'issue_id': issue_id,
        'note': args.note or '',
    }
    _append_event(event)
    print(f'Closed issue {issue_id}')


def cmd_list(args: argparse.Namespace) -> None:
    events = _read_events()
    state = _build_state(events)
    status_filter = args.status.lower() if args.status else None
    if status_filter and status_filter not in VALID_STATUSES:
        raise SystemExit(f'Invalid status: {status_filter}')

    for issue_id in sorted(state.keys()):
        issue = state[issue_id]
        if status_filter and issue['status'] != status_filter:
            continue
        print(f"[{issue['status']}] #{issue_id} {issue['title']} (severity: {issue['severity']})")


def cmd_history(args: argparse.Namespace) -> None:
    events = _read_events()
    issue_id = int(args.id)
    for event in events:
        if int(event.get('issue_id', 0)) == issue_id:
            print(json.dumps(event, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Issue tracking CLI')
    sub = parser.add_subparsers(dest='command', required=True)

    create_p = sub.add_parser('create', help='Create a new issue')
    create_p.add_argument('--title', required=True)
    create_p.add_argument('--description')
    create_p.add_argument('--severity', default='low')
    create_p.add_argument('--owner')
    create_p.add_argument('--tags')
    create_p.add_argument('--related-files')
    create_p.set_defaults(func=cmd_create)

    update_p = sub.add_parser('update', help='Update an issue')
    update_p.add_argument('--id', required=True)
    update_p.add_argument('--title')
    update_p.add_argument('--description')
    update_p.add_argument('--severity')
    update_p.add_argument('--status')
    update_p.add_argument('--owner')
    update_p.add_argument('--tags')
    update_p.add_argument('--related-files')
    update_p.add_argument('--note')
    update_p.set_defaults(func=cmd_update)

    close_p = sub.add_parser('close', help='Close an issue')
    close_p.add_argument('--id', required=True)
    close_p.add_argument('--note')
    close_p.set_defaults(func=cmd_close)

    list_p = sub.add_parser('list', help='List issues')
    list_p.add_argument('--status')
    list_p.set_defaults(func=cmd_list)

    history_p = sub.add_parser('history', help='Show issue history')
    history_p.add_argument('--id', required=True)
    history_p.set_defaults(func=cmd_history)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
