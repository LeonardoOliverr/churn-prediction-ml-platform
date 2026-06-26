"""
Rede Neural MLP para classificação binária de churn.

ChurnMLP: arquitetura configurável com early stopping.
train_mlp: loop de treinamento com BCEWithLogitsLoss + Adam.
evaluate_mlp: métricas sklearn a partir de um DataLoader.
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

SEED = 42
torch.manual_seed(SEED)


class ChurnMLP(nn.Module):
    """MLP para classificação binária de churn.

    Saída: logit bruto (sem Sigmoid) — compatível com BCEWithLogitsLoss.
    Para obter probabilidade em inferência: torch.sigmoid(model(x)).
    """

    def __init__(
        self,
        input_dim: int,
        hidden: list[int] | None = None,
        dropout: float = 0.3,
    ):
        super().__init__()
        if hidden is None:
            hidden = [64, 32, 16]

        layers: list[nn.Module] = []
        prev = input_dim
        for h in hidden:
            layers += [nn.Linear(prev, h), nn.ReLU(), nn.Dropout(dropout)]
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def make_loaders(
    X_train: "np.ndarray",
    y_train: "np.ndarray",
    X_val: "np.ndarray",
    y_val: "np.ndarray",
    batch_size: int = 64,
) -> tuple[DataLoader, DataLoader]:
    """Converte arrays NumPy em DataLoaders PyTorch."""
    X_tr = torch.FloatTensor(np.array(X_train))
    y_tr = torch.FloatTensor(np.array(y_train)).unsqueeze(1)
    X_v = torch.FloatTensor(np.array(X_val))
    y_v = torch.FloatTensor(np.array(y_val)).unsqueeze(1)

    train_loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_v, y_v), batch_size=batch_size, shuffle=False)
    return train_loader, val_loader


def train_mlp(
    model: ChurnMLP,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int = 100,
    lr: float = 1e-3,
    pos_weight: float = 2.7,
    patience: int = 15,
) -> dict:
    """Loop de treinamento com early stopping baseado em val_loss.

    Salva o melhor state_dict e o restaura ao fim. Retorna histórico de loss.
    """
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight]))

    best_val_loss = float("inf")
    best_state: dict | None = None
    epochs_no_improve = 0
    history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}

    for _epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(xb)
        train_loss /= len(train_loader.dataset)

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                val_loss += criterion(model(xb), yb).item() * len(xb)
        val_loss /= len(val_loader.dataset)

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    return history


def evaluate_mlp(
    model: ChurnMLP,
    loader: DataLoader,
    threshold: float = 0.5,
) -> dict:
    """Avalia o modelo em um DataLoader e retorna métricas sklearn.

    Aplica sigmoid nos logits brutos antes de calcular métricas.
    """
    from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

    model.eval()
    all_probs: list[float] = []
    all_labels: list[float] = []

    with torch.no_grad():
        for xb, yb in loader:
            probs = torch.sigmoid(model(xb)).squeeze(1).tolist()
            labels = yb.squeeze(1).tolist()
            all_probs.extend(probs)
            all_labels.extend(labels)

    preds = [1 if p >= threshold else 0 for p in all_probs]

    return {
        "f1": float(round(f1_score(all_labels, preds, zero_division=0), 4)),
        "roc_auc": float(round(roc_auc_score(all_labels, all_probs), 4)),
        "precision": float(round(precision_score(all_labels, preds, zero_division=0), 4)),
        "recall": float(round(recall_score(all_labels, preds, zero_division=0), 4)),
    }
