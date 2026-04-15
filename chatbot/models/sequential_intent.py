from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import torch
from torch import nn
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset

from chatbot.utils.preprocessing import tokenize_text

PAD_TOKEN = "<pad>"
UNK_TOKEN = "<unk>"


@dataclass
class Vocabulary:
    stoi: Dict[str, int]
    itos: List[str]
    max_length: int = 64

    @property
    def pad_id(self) -> int:
        return self.stoi[PAD_TOKEN]

    @property
    def unk_id(self) -> int:
        return self.stoi[UNK_TOKEN]

    def encode(self, text: str) -> List[int]:
        tokens = tokenize_text(text)[: self.max_length]
        if not tokens:
            return [self.unk_id]
        return [self.stoi.get(token, self.unk_id) for token in tokens]


class IntentTextDataset(Dataset):
    def __init__(self, records: Sequence[dict[str, str]], vocab: Vocabulary, label2id: Dict[str, int]):
        self.records = list(records)
        self.vocab = vocab
        self.label2id = label2id

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int):
        row = self.records[index]
        input_ids = torch.tensor(self.vocab.encode(row['text']), dtype=torch.long)
        label = torch.tensor(self.label2id[row['intent']], dtype=torch.long)
        return input_ids, label


def build_vocab(
    texts: Iterable[str],
    min_freq: int = 1,
    max_vocab_size: int | None = None,
    max_length: int = 64,
) -> Vocabulary:
    counter = Counter()
    for text in texts:
        counter.update(tokenize_text(text))
    tokens = [token for token, freq in counter.items() if freq >= min_freq]
    tokens.sort(key=lambda token: (-counter[token], token))
    if max_vocab_size is not None:
        tokens = tokens[: max(0, max_vocab_size - 2)]
    itos = [PAD_TOKEN, UNK_TOKEN, *tokens]
    stoi = {token: idx for idx, token in enumerate(itos)}
    return Vocabulary(stoi=stoi, itos=itos, max_length=max_length)


def collate_batch(batch, pad_id: int):
    input_ids, labels = zip(*batch)
    lengths = torch.tensor([len(item) for item in input_ids], dtype=torch.long)
    padded = pad_sequence(input_ids, batch_first=True, padding_value=pad_id)
    return padded, lengths, torch.stack(labels)


class SequentialIntentClassifier(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int,
        hidden_dim: int,
        num_classes: int,
        architecture: str = 'bilstm',
        num_layers: int = 1,
        dropout: float = 0.2,
        padding_idx: int = 0,
    ) -> None:
        super().__init__()
        normalized_arch = architecture.lower()
        bidirectional = normalized_arch in {'bilstm', 'bigru'}
        rnn_type = 'gru' if 'gru' in normalized_arch else 'lstm'

        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=padding_idx)
        recurrent_dropout = dropout if num_layers > 1 else 0.0
        rnn_cls = nn.GRU if rnn_type == 'gru' else nn.LSTM
        self.encoder = rnn_cls(
            input_size=embedding_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=recurrent_dropout,
            bidirectional=bidirectional,
        )
        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_dim * (2 if bidirectional else 1), num_classes)
        self.rnn_type = rnn_type
        self.bidirectional = bidirectional

    def forward(self, input_ids: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        embedded = self.embedding(input_ids)
        packed = nn.utils.rnn.pack_padded_sequence(
            embedded,
            lengths.cpu(),
            batch_first=True,
            enforce_sorted=False,
        )
        _, hidden = self.encoder(packed)
        if self.rnn_type == 'lstm':
            hidden = hidden[0]
        if self.bidirectional:
            features = torch.cat((hidden[-2], hidden[-1]), dim=1)
        else:
            features = hidden[-1]
        return self.classifier(self.dropout(features))
