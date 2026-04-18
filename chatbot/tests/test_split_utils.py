from __future__ import annotations

from chatbot.data.split_utils import build_stratified_splits


def test_build_stratified_splits_preserves_labels_and_counts() -> None:
    rows = []
    for index in range(20):
        rows.append({'text': f'greeting {index}', 'intent': 'greeting', 'lang': 'en'})
        rows.append({'text': f'cbc {index}', 'intent': 'cbc_info', 'lang': 'en'})
        rows.append({'text': f'coag {index}', 'intent': 'coag_test', 'lang': 'en'})

    splits = build_stratified_splits(
        rows=rows,
        train_ratio=0.70,
        validation_ratio=0.15,
        test_ratio=0.15,
        seed=42,
    )

    assert len(splits['train']) + len(splits['validation']) + len(splits['test']) == len(rows)
    assert {row['intent'] for row in splits['train']} == {'greeting', 'cbc_info', 'coag_test'}
    assert {row['intent'] for row in splits['validation']} == {'greeting', 'cbc_info', 'coag_test'}
    assert {row['intent'] for row in splits['test']} == {'greeting', 'cbc_info', 'coag_test'}
