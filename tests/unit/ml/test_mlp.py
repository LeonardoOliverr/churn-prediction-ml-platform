"""
Testes unitários para ml/models/mlp/mlp_model.py.

Cobre ChurnMLP (arquitetura e forward pass), make_loaders, train_mlp e evaluate_mlp
sem dependência de banco de dados ou MLflow.
"""

import numpy as np
import pytest
import torch

from ml.models.mlp.mlp_model import ChurnMLP, evaluate_mlp, make_loaders, train_mlp

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

N_SAMPLES = 60
N_FEATURES = 10


@pytest.fixture()
def synthetic_data():
    """Arrays NumPy sintéticos balanceados para uso nos testes."""
    rng = np.random.default_rng(42)
    X = rng.standard_normal((N_SAMPLES, N_FEATURES)).astype(np.float32)
    y = np.array([i % 2 for i in range(N_SAMPLES)], dtype=np.float32)
    mid = N_SAMPLES // 2
    return X[:mid], y[:mid], X[mid:], y[mid:]


@pytest.fixture()
def loaders(synthetic_data):
    """DataLoaders train/val a partir dos dados sintéticos."""
    X_tr, y_tr, X_v, y_v = synthetic_data
    return make_loaders(X_tr, y_tr, X_v, y_v, batch_size=16)


@pytest.fixture()
def model():
    """Instância padrão do ChurnMLP com input_dim=N_FEATURES."""
    return ChurnMLP(input_dim=N_FEATURES)


# ---------------------------------------------------------------------------
# ChurnMLP — arquitetura
# ---------------------------------------------------------------------------


def test_churn_mlp_output_shape():
    """Forward pass retorna tensor (batch, 1) — logit sem sigmoid."""
    m = ChurnMLP(input_dim=N_FEATURES)
    x = torch.randn(8, N_FEATURES)
    out = m(x)
    assert out.shape == (8, 1)


def test_churn_mlp_no_sigmoid_in_architecture():
    """Confirma que não há nn.Sigmoid na rede — saída é logit bruto (BCEWithLogitsLoss)."""
    m = ChurnMLP(input_dim=N_FEATURES)
    has_sigmoid = any(isinstance(mod, torch.nn.Sigmoid) for mod in m.net)
    assert not has_sigmoid


def test_churn_mlp_default_hidden_layers():
    """Arquitetura padrão tem 3 blocos ocultos [64, 32, 16] + camada de saída."""
    m = ChurnMLP(input_dim=N_FEATURES)
    linear_layers = [mod for mod in m.net if isinstance(mod, torch.nn.Linear)]
    assert len(linear_layers) == 4  # 3 ocultas + 1 saída


def test_churn_mlp_custom_hidden_layers():
    """Layers customizadas [128, 64] produzem 3 Linears: 2 ocultas + 1 saída."""
    m = ChurnMLP(input_dim=N_FEATURES, hidden=[128, 64])
    linear_layers = [mod for mod in m.net if isinstance(mod, torch.nn.Linear)]
    assert len(linear_layers) == 3


def test_churn_mlp_parameters_are_learnable():
    """Modelo tem parâmetros treináveis (requires_grad=True)."""
    m = ChurnMLP(input_dim=N_FEATURES)
    assert any(p.requires_grad for p in m.parameters())


# ---------------------------------------------------------------------------
# make_loaders
# ---------------------------------------------------------------------------


def test_make_loaders_returns_two_dataloaders(synthetic_data):
    """make_loaders retorna exatamente dois DataLoaders."""
    X_tr, y_tr, X_v, y_v = synthetic_data
    train_loader, val_loader = make_loaders(X_tr, y_tr, X_v, y_v)
    assert train_loader is not None
    assert val_loader is not None


def test_make_loaders_batch_shape(synthetic_data):
    """Primeiro batch do train_loader tem forma (batch_size, N_FEATURES)."""
    X_tr, y_tr, X_v, y_v = synthetic_data
    train_loader, _ = make_loaders(X_tr, y_tr, X_v, y_v, batch_size=16)
    xb, yb = next(iter(train_loader))
    assert xb.shape[1] == N_FEATURES
    assert yb.shape[1] == 1  # unsqueeze(1) aplicado em make_loaders


def test_make_loaders_dtype_is_float(synthetic_data):
    """Tensores são FloatTensor (float32)."""
    X_tr, y_tr, X_v, y_v = synthetic_data
    train_loader, _ = make_loaders(X_tr, y_tr, X_v, y_v)
    xb, yb = next(iter(train_loader))
    assert xb.dtype == torch.float32
    assert yb.dtype == torch.float32


# ---------------------------------------------------------------------------
# train_mlp
# ---------------------------------------------------------------------------


def test_train_mlp_returns_history_keys(model, loaders):
    """train_mlp retorna dict com chaves 'train_loss' e 'val_loss'."""
    train_loader, val_loader = loaders
    history = train_mlp(model, train_loader, val_loader, epochs=3, patience=10)
    assert "train_loss" in history
    assert "val_loss" in history


def test_train_mlp_history_length(model, loaders):
    """Histórico de loss tem comprimento igual ao número de épocas executadas."""
    train_loader, val_loader = loaders
    history = train_mlp(model, train_loader, val_loader, epochs=5, patience=10)
    assert len(history["train_loss"]) == len(history["val_loss"])
    assert 1 <= len(history["train_loss"]) <= 5


def test_train_mlp_loss_is_positive(model, loaders):
    """Todos os valores de loss no histórico são positivos."""
    train_loader, val_loader = loaders
    history = train_mlp(model, train_loader, val_loader, epochs=4, patience=10)
    assert all(v > 0 for v in history["train_loss"])
    assert all(v > 0 for v in history["val_loss"])


def test_train_mlp_early_stopping_triggers(synthetic_data):
    """Early stopping interrompe antes do máximo de épocas com patience=1."""
    m = ChurnMLP(input_dim=N_FEATURES)
    X_tr, y_tr, X_v, y_v = synthetic_data
    train_loader, val_loader = make_loaders(X_tr, y_tr, X_v, y_v, batch_size=16)
    history = train_mlp(m, train_loader, val_loader, epochs=100, patience=1)
    assert len(history["train_loss"]) < 100


def test_train_mlp_restores_best_weights(loaders):
    """Modelo ao final tem os pesos da melhor época (best_val_loss)."""
    m = ChurnMLP(input_dim=N_FEATURES)
    train_loader, val_loader = loaders
    weights_before = {k: v.clone() for k, v in m.state_dict().items()}
    train_mlp(m, train_loader, val_loader, epochs=10, patience=5)
    weights_after = m.state_dict()
    any_changed = any(not torch.equal(weights_before[k], weights_after[k]) for k in weights_before)
    assert any_changed, "Pesos devem ter sido atualizados durante o treino"


# ---------------------------------------------------------------------------
# evaluate_mlp
# ---------------------------------------------------------------------------


def test_evaluate_mlp_returns_expected_keys(model, loaders):
    """evaluate_mlp retorna dict com f1, roc_auc, precision, recall."""
    _, val_loader = loaders
    metrics = evaluate_mlp(model, val_loader)
    assert set(metrics.keys()) == {"f1", "roc_auc", "precision", "recall"}


def test_evaluate_mlp_values_are_in_range(model, loaders):
    """Todas as métricas estão no intervalo [0, 1]."""
    _, val_loader = loaders
    metrics = evaluate_mlp(model, val_loader)
    for key, value in metrics.items():
        assert 0.0 <= value <= 1.0, f"{key}={value} fora do range esperado"


def test_evaluate_mlp_after_training(loaders):
    """Modelo treinado tem F1 >= 0.5 em dados sintéticos linearmente separáveis."""
    X_tr = torch.randn(40, N_FEATURES)
    y_tr = (X_tr[:, 0] > 0).float()
    X_v = torch.randn(20, N_FEATURES)
    y_v = (X_v[:, 0] > 0).float()
    from torch.utils.data import DataLoader, TensorDataset

    train_loader = DataLoader(TensorDataset(X_tr, y_tr.unsqueeze(1)), batch_size=16, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_v, y_v.unsqueeze(1)), batch_size=16)

    m = ChurnMLP(input_dim=N_FEATURES)
    train_mlp(m, train_loader, val_loader, epochs=30, patience=30, lr=1e-2)
    metrics = evaluate_mlp(m, val_loader)
    assert metrics["f1"] >= 0.5, f"F1 esperado >= 0.5, obtido: {metrics['f1']}"
