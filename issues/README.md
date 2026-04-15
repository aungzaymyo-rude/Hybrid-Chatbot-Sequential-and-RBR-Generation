# Issue Tracking

This folder contains an append-only JSONL issue history log and a small CLI to create, update, and list issues.

## Files
- `issue_log.jsonl`: Append-only history log. Each line is a JSON event.
- `issue_cli.py`: CLI to add/update/close/list issues.

## Event Schema (per line)
```json
{
  "timestamp": "2026-04-13T14:02:00+00:00",
  "event": "create|update|close",
  "issue_id": 1,
  "title": "Short title",
  "description": "Optional longer text",
  "severity": "low|medium|high|critical",
  "status": "open|in_progress|blocked|closed",
  "owner": "name or team",
  "tags": ["training", "api"],
  "related_files": ["D:/Multilingual Chatbot Design/chatbot/api/main.py"],
  "note": "Optional note for updates/close"
}
```

## Usage
Create:
```bash
python issues/issue_cli.py create --title "Training fails" --description "CUDA OOM" --severity high --owner ml-team --tags training,infra
```

Update:
```bash
python issues/issue_cli.py update --id 1 --status in_progress --note "Retrying with smaller batch size"
```

Close:
```bash
python issues/issue_cli.py close --id 1 --note "Fixed by batch size 8"
```

List open issues:
```bash
python issues/issue_cli.py list --status open
```

History for an issue:
```bash
python issues/issue_cli.py history --id 1
```
