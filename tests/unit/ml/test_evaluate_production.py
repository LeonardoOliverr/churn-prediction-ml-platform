"""
Testes unitários para ml/evaluate_production.py.

Cobre todas as funções puras sem dependência de banco de dados:
- _parse_since(): parsing de janela temporal
- _compute_confusion(): matriz de confusão a partir de linhas
- _compute_metrics(): precision, recall e F1 com divisão por zero
- _compute_cost(): custo financeiro FP/FN
"""

import pytest
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# _parse_since()
# ---------------------------------------------------------------------------


def test_parse_since_valid_90d():
    """'90d' retorna 90."""
    from ml.evaluate_production import _parse_since
    assert _parse_since("90d") == 90


def test_parse_since_valid_30d():
    """'30d' retorna 30."""
    from ml.evaluate_production import _parse_since
    assert _parse_since("30d") == 30


def test_parse_since_valid_1d():
    """'1d' retorna 1."""
    from ml.evaluate_production import _parse_since
    assert _parse_since("1d") == 1


def test_parse_since_missing_d_suffix_raises():
    """Ausência do sufixo 'd' levanta ValueError."""
    from ml.evaluate_production import _parse_since
    with pytest.raises(ValueError, match="Formato inválido"):
        _parse_since("90")


def test_parse_since_wrong_suffix_raises():
    """Sufixo incorreto levanta ValueError."""
    from ml.evaluate_production import _parse_since
    with pytest.raises(ValueError):
        _parse_since("90h")


def test_parse_since_zero_days_raises():
    """'0d' levanta ValueError — deve ser inteiro positivo."""
    from ml.evaluate_production import _parse_since
    with pytest.raises(ValueError):
        _parse_since("0d")


def test_parse_since_negative_raises():
    """Valor negativo levanta ValueError."""
    from ml.evaluate_production import _parse_since
    with pytest.raises(ValueError):
        _parse_since("-30d")


def test_parse_since_non_numeric_raises():
    """Valor não numérico levanta ValueError."""
    from ml.evaluate_production import _parse_since
    with pytest.raises(ValueError):
        _parse_since("abcd")


# ---------------------------------------------------------------------------
# _compute_confusion()
# ---------------------------------------------------------------------------


def _row(pred: bool, churned: bool):
    return SimpleNamespace(churn_pred=pred, churned=churned)


def test_compute_confusion_all_tp():
    """Todos TP quando pred=True e churned=True."""
    from ml.evaluate_production import _compute_confusion
    rows = [_row(True, True)] * 5
    cm = _compute_confusion(rows)
    assert cm == {"tp": 5, "fp": 0, "fn": 0, "tn": 0}


def test_compute_confusion_all_fp():
    """Todos FP quando pred=True e churned=False."""
    from ml.evaluate_production import _compute_confusion
    rows = [_row(True, False)] * 3
    cm = _compute_confusion(rows)
    assert cm == {"tp": 0, "fp": 3, "fn": 0, "tn": 0}


def test_compute_confusion_all_fn():
    """Todos FN quando pred=False e churned=True."""
    from ml.evaluate_production import _compute_confusion
    rows = [_row(False, True)] * 4
    cm = _compute_confusion(rows)
    assert cm == {"tp": 0, "fp": 0, "fn": 4, "tn": 0}


def test_compute_confusion_all_tn():
    """Todos TN quando pred=False e churned=False."""
    from ml.evaluate_production import _compute_confusion
    rows = [_row(False, False)] * 6
    cm = _compute_confusion(rows)
    assert cm == {"tp": 0, "fp": 0, "fn": 0, "tn": 6}


def test_compute_confusion_mixed():
    """Contagem correta para mix de TP, FP, FN, TN."""
    from ml.evaluate_production import _compute_confusion
    rows = [
        _row(True,  True),   # TP
        _row(True,  True),   # TP
        _row(True,  False),  # FP
        _row(False, True),   # FN
        _row(False, False),  # TN
        _row(False, False),  # TN
    ]
    cm = _compute_confusion(rows)
    assert cm == {"tp": 2, "fp": 1, "fn": 1, "tn": 2}


def test_compute_confusion_empty_rows():
    """Sem linhas retorna zeros."""
    from ml.evaluate_production import _compute_confusion
    cm = _compute_confusion([])
    assert cm == {"tp": 0, "fp": 0, "fn": 0, "tn": 0}


def test_compute_confusion_total_equals_row_count():
    """Soma de TP+FP+FN+TN é igual ao número de linhas."""
    from ml.evaluate_production import _compute_confusion
    rows = [_row(i % 2 == 0, i % 3 == 0) for i in range(20)]
    cm = _compute_confusion(rows)
    assert cm["tp"] + cm["fp"] + cm["fn"] + cm["tn"] == 20


# ---------------------------------------------------------------------------
# _compute_metrics()
# ---------------------------------------------------------------------------


def test_compute_metrics_perfect_precision_and_recall():
    """Todos TP → precision=1.0, recall=1.0, f1=1.0."""
    from ml.evaluate_production import _compute_metrics
    cm = {"tp": 10, "fp": 0, "fn": 0, "tn": 5}
    m = _compute_metrics(cm)
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["f1"] == 1.0


def test_compute_metrics_zero_precision_when_no_tp_or_fp():
    """tp=0 e fp=0 → precision=0.0 (sem divisão por zero)."""
    from ml.evaluate_production import _compute_metrics
    cm = {"tp": 0, "fp": 0, "fn": 5, "tn": 5}
    m = _compute_metrics(cm)
    assert m["precision"] == 0.0


def test_compute_metrics_zero_recall_when_no_tp_or_fn():
    """tp=0 e fn=0 → recall=0.0 (sem divisão por zero)."""
    from ml.evaluate_production import _compute_metrics
    cm = {"tp": 0, "fp": 3, "fn": 0, "tn": 5}
    m = _compute_metrics(cm)
    assert m["recall"] == 0.0


def test_compute_metrics_zero_f1_when_both_zero():
    """precision=0 e recall=0 → f1=0.0 (sem divisão por zero)."""
    from ml.evaluate_production import _compute_metrics
    cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 10}
    m = _compute_metrics(cm)
    assert m["f1"] == 0.0


def test_compute_metrics_known_values():
    """Verifica cálculo com valores conhecidos: tp=8, fp=2, fn=2."""
    from ml.evaluate_production import _compute_metrics
    cm = {"tp": 8, "fp": 2, "fn": 2, "tn": 8}
    m = _compute_metrics(cm)
    assert m["precision"] == pytest.approx(0.8, abs=1e-4)
    assert m["recall"]    == pytest.approx(0.8, abs=1e-4)
    assert m["f1"]        == pytest.approx(0.8, abs=1e-4)


def test_compute_metrics_returns_rounded_values():
    """Métricas retornam valores arredondados a 4 casas decimais."""
    from ml.evaluate_production import _compute_metrics
    cm = {"tp": 7, "fp": 3, "fn": 1, "tn": 9}
    m = _compute_metrics(cm)
    for key in ("precision", "recall", "f1"):
        assert isinstance(m[key], float)
        assert len(str(m[key]).split(".")[-1]) <= 4


# ---------------------------------------------------------------------------
# _compute_cost()
# ---------------------------------------------------------------------------


def test_compute_cost_basic():
    """Custo = FP * fp_cost + FN * fn_cost."""
    from ml.evaluate_production import _compute_cost
    cm = {"tp": 5, "fp": 10, "fn": 3, "tn": 2}
    cost = _compute_cost(cm, fp_cost=100.0, fn_cost=2000.0)
    assert cost == pytest.approx(10 * 100.0 + 3 * 2000.0)


def test_compute_cost_zero_fp():
    """Sem FP, custo é apenas dos FN."""
    from ml.evaluate_production import _compute_cost
    cm = {"tp": 5, "fp": 0, "fn": 4, "tn": 1}
    assert _compute_cost(cm, fp_cost=500.0, fn_cost=1000.0) == pytest.approx(4000.0)


def test_compute_cost_zero_fn():
    """Sem FN, custo é apenas dos FP."""
    from ml.evaluate_production import _compute_cost
    cm = {"tp": 5, "fp": 3, "fn": 0, "tn": 2}
    assert _compute_cost(cm, fp_cost=200.0, fn_cost=5000.0) == pytest.approx(600.0)


def test_compute_cost_zero_errors():
    """Sem FP e sem FN, custo é zero."""
    from ml.evaluate_production import _compute_cost
    cm = {"tp": 10, "fp": 0, "fn": 0, "tn": 5}
    assert _compute_cost(cm, fp_cost=100.0, fn_cost=2000.0) == pytest.approx(0.0)


def test_compute_cost_fn_dominates_when_much_higher():
    """Custo de FN muito maior domina o total."""
    from ml.evaluate_production import _compute_cost
    cm = {"tp": 0, "fp": 100, "fn": 1, "tn": 0}
    cost = _compute_cost(cm, fp_cost=10.0, fn_cost=50000.0)
    assert cost == pytest.approx(100 * 10.0 + 1 * 50000.0)
    assert cost > 50000.0


# ---------------------------------------------------------------------------
# _compute_derived_rates()
# ---------------------------------------------------------------------------


def test_derived_rates_normal_values():
    """Verifica FPR, FNR e especificidade com valores conhecidos."""
    from ml.evaluate_production import _compute_derived_rates
    cm = {"tp": 10, "fp": 5, "fn": 3, "tn": 20}
    d = _compute_derived_rates(cm)
    # FPR = 5 / (5 + 20) = 0.2
    assert d["false_positive_rate"] == pytest.approx(0.2, abs=1e-4)
    # FNR = 3 / (3 + 10) ≈ 0.2308
    assert d["false_negative_rate"] == pytest.approx(3 / 13, abs=1e-4)
    # Specificity = 20 / (20 + 5) = 0.8
    assert d["specificity"] == pytest.approx(0.8, abs=1e-4)


def test_derived_rates_zero_fpr_when_no_fp_or_tn():
    """FP=0, TN=0 → false_positive_rate=None (denominador zero)."""
    from ml.evaluate_production import _compute_derived_rates
    cm = {"tp": 5, "fp": 0, "fn": 2, "tn": 0}
    d = _compute_derived_rates(cm)
    assert d["false_positive_rate"] is None
    assert d["specificity"] is None


def test_derived_rates_zero_fnr_when_no_fn_or_tp():
    """FN=0, TP=0 → false_negative_rate=None (denominador zero)."""
    from ml.evaluate_production import _compute_derived_rates
    cm = {"tp": 0, "fp": 3, "fn": 0, "tn": 5}
    d = _compute_derived_rates(cm)
    assert d["false_negative_rate"] is None


def test_derived_rates_perfect_classifier():
    """Classificador perfeito: FPR=0, FNR=0, especificidade=1."""
    from ml.evaluate_production import _compute_derived_rates
    cm = {"tp": 10, "fp": 0, "fn": 0, "tn": 10}
    d = _compute_derived_rates(cm)
    assert d["false_positive_rate"] == pytest.approx(0.0)
    assert d["false_negative_rate"] == pytest.approx(0.0)
    assert d["specificity"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# _compute_risk_segmentation()
# ---------------------------------------------------------------------------


def _prob_row(prob: float):
    return SimpleNamespace(churn_prob=prob, churn_pred=prob >= 0.5, churned=False)


def test_risk_segmentation_counts_by_bucket():
    """Conta corretamente predições por faixa de probabilidade."""
    from ml.evaluate_production import _compute_risk_segmentation
    rows = [
        _prob_row(0.9),   # alto
        _prob_row(0.75),  # alto
        _prob_row(0.5),   # médio
        _prob_row(0.3),   # médio (inclusive)
        _prob_row(0.1),   # baixo
        _prob_row(0.29),  # baixo
    ]
    r = _compute_risk_segmentation(rows)
    assert r["high_risk_count"]   == 2
    assert r["medium_risk_count"] == 2
    assert r["low_risk_count"]    == 2


def test_risk_segmentation_boundary_0_7_is_high():
    """prob=0.71 cai em alto risco (> 0.7)."""
    from ml.evaluate_production import _compute_risk_segmentation
    rows = [_prob_row(0.71)]
    r = _compute_risk_segmentation(rows)
    assert r["high_risk_count"] == 1


def test_risk_segmentation_boundary_0_7_exact_is_medium():
    """prob=0.7 exato cai em médio risco (não > 0.7)."""
    from ml.evaluate_production import _compute_risk_segmentation
    rows = [_prob_row(0.7)]
    r = _compute_risk_segmentation(rows)
    assert r["medium_risk_count"] == 1


def test_risk_segmentation_empty_rows():
    """Sem linhas retorna zeros."""
    from ml.evaluate_production import _compute_risk_segmentation
    r = _compute_risk_segmentation([])
    assert r == {"high_risk_count": 0, "medium_risk_count": 0, "low_risk_count": 0}


def test_risk_segmentation_total_equals_row_count():
    """Soma das contagens equals o número total de linhas."""
    from ml.evaluate_production import _compute_risk_segmentation
    rows = [_prob_row(p / 10) for p in range(11)]  # 0.0 a 1.0
    r = _compute_risk_segmentation(rows)
    assert r["high_risk_count"] + r["medium_risk_count"] + r["low_risk_count"] == 11


# ---------------------------------------------------------------------------
# _compute_promotion_recommendation()
# ---------------------------------------------------------------------------


def _metrics(f1: float = 0.8, precision: float = 0.8, recall: float = 0.8) -> dict:
    return {"f1": f1, "precision": precision, "recall": recall}


def test_promotion_champion_is_never_candidate():
    """O próprio champion retorna candidate=False."""
    from ml.evaluate_production import _compute_promotion_recommendation
    result = _compute_promotion_recommendation(
        metrics=_metrics(f1=0.9), cost=1000.0, total=500, role="champion",
        champion_metrics=_metrics(f1=0.8), champion_cost=1200.0, champion_total=500,
    )
    assert result["promotion_candidate"] is False
    assert "produção" in result["recommendation_reason"]


def test_promotion_no_champion_returns_false():
    """Sem champion disponível para comparar → candidate=False."""
    from ml.evaluate_production import _compute_promotion_recommendation
    result = _compute_promotion_recommendation(
        metrics=_metrics(f1=0.9), cost=800.0, total=300, role="challenger",
        champion_metrics=None, champion_cost=None, champion_total=None,
    )
    assert result["promotion_candidate"] is False


def test_promotion_challenger_better_f1_and_cost():
    """Challenger com F1 e custo/pred melhores → candidate=True, reason menciona ambos."""
    from ml.evaluate_production import _compute_promotion_recommendation
    # champion: R$1000 / 500 = R$2.00/pred | challenger: R$200 / 200 = R$1.00/pred
    result = _compute_promotion_recommendation(
        metrics=_metrics(f1=0.85), cost=200.0, total=200, role="challenger",
        champion_metrics=_metrics(f1=0.80), champion_cost=1000.0, champion_total=500,
    )
    assert result["promotion_candidate"] is True
    assert "Promover" in result["recommendation_reason"]
    assert "F1" in result["recommendation_reason"]
    assert "custo" in result["recommendation_reason"]


def test_promotion_challenger_better_f1_only():
    """Challenger com F1 melhor mas custo/pred maior → candidate=True."""
    from ml.evaluate_production import _compute_promotion_recommendation
    # champion: R$1000 / 500 = R$2.00/pred | challenger: R$900 / 200 = R$4.50/pred
    result = _compute_promotion_recommendation(
        metrics=_metrics(f1=0.85), cost=900.0, total=200, role="challenger",
        champion_metrics=_metrics(f1=0.80), champion_cost=1000.0, champion_total=500,
    )
    assert result["promotion_candidate"] is True
    assert "Promover" in result["recommendation_reason"]
    assert "F1" in result["recommendation_reason"]


def test_promotion_challenger_better_cost_only():
    """Challenger com custo/pred menor mas F1 inferior → candidate=True."""
    from ml.evaluate_production import _compute_promotion_recommendation
    # champion: R$1000 / 500 = R$2.00/pred | challenger: R$100 / 200 = R$0.50/pred
    result = _compute_promotion_recommendation(
        metrics=_metrics(f1=0.75), cost=100.0, total=200, role="challenger",
        champion_metrics=_metrics(f1=0.80), champion_cost=1000.0, champion_total=500,
    )
    assert result["promotion_candidate"] is True
    assert "Promover" in result["recommendation_reason"]
    assert "custo" in result["recommendation_reason"].lower()


def test_promotion_champion_superior_in_both():
    """Champion superior em F1 e custo/pred → candidate=False, reason menciona 'Manter'."""
    from ml.evaluate_production import _compute_promotion_recommendation
    # champion: R$1000 / 500 = R$2.00/pred | challenger: R$1800 / 200 = R$9.00/pred
    result = _compute_promotion_recommendation(
        metrics=_metrics(f1=0.70), cost=1800.0, total=200, role="challenger",
        champion_metrics=_metrics(f1=0.85), champion_cost=1000.0, champion_total=500,
    )
    assert result["promotion_candidate"] is False
    assert "Manter" in result["recommendation_reason"]


def test_promotion_volume_bias_corrected():
    """Challenger com custo total menor mas custo/pred maior não é promovido por custo."""
    from ml.evaluate_production import _compute_promotion_recommendation
    # champion: R$10000 / 1000 = R$10/pred | challenger: R$800 / 50 = R$16/pred
    # Sem normalização, challenger pareceria mais barato (800 < 10000)
    result = _compute_promotion_recommendation(
        metrics=_metrics(f1=0.75), cost=800.0, total=50, role="challenger",
        champion_metrics=_metrics(f1=0.80), champion_cost=10000.0, champion_total=1000,
    )
    # F1 pior e custo/pred maior → não deve promover
    assert result["promotion_candidate"] is False


# ---------------------------------------------------------------------------
# _compute_roc_auc()
# ---------------------------------------------------------------------------


def test_compute_roc_auc_returns_float_for_binary_classes():
    """ROC-AUC calculado com duas classes distintas retorna float em [0,1]."""
    from ml.evaluate_production import _compute_roc_auc
    rows = [
        SimpleNamespace(churned=True,  churn_prob=0.9),
        SimpleNamespace(churned=True,  churn_prob=0.8),
        SimpleNamespace(churned=False, churn_prob=0.2),
        SimpleNamespace(churned=False, churn_prob=0.1),
    ]
    auc = _compute_roc_auc(rows)
    assert auc is not None
    assert 0.0 <= auc <= 1.0


def test_compute_roc_auc_single_class_returns_none():
    """Apenas uma classe nos outcomes torna AUC indefinido — retorna None."""
    from ml.evaluate_production import _compute_roc_auc
    rows = [SimpleNamespace(churned=True, churn_prob=0.8)] * 5
    assert _compute_roc_auc(rows) is None


def test_compute_roc_auc_perfect_discrimination():
    """Separação perfeita → AUC = 1.0."""
    from ml.evaluate_production import _compute_roc_auc
    rows = [
        SimpleNamespace(churned=True,  churn_prob=1.0),
        SimpleNamespace(churned=False, churn_prob=0.0),
    ]
    assert _compute_roc_auc(rows) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# _compute_row_cost()
# ---------------------------------------------------------------------------


def _full_row(monthly: float = 50.0, cltv: float = 1000.0):
    return SimpleNamespace(monthly_charges=monthly, cltv=cltv, churn_pred=True, churned=False)


def test_compute_row_cost_flat_when_no_config():
    """Sem config retorna os custos flat do CLI."""
    from ml.evaluate_production import _compute_row_cost
    fp, fn = _compute_row_cost(_full_row(), config=None, fp_cost_flat=100.0, fn_cost_flat=2000.0)
    assert fp == 100.0
    assert fn == 2000.0


def test_compute_row_cost_flat_config_returns_flat_values():
    """Config com cost_model=flat usa os valores flat do CLI."""
    from ml.evaluate_production import _compute_row_cost
    from domain.constants import CostModel
    config = {
        "cost_model": CostModel.FLAT,
        "fp_cost_months": 3, "fp_cost_discount": 0.5,
        "fn_cost_cltv_multiplier": 2.0, "fn_cost_months_multiplier": 6,
    }
    fp, fn = _compute_row_cost(_full_row(), config=config, fp_cost_flat=100.0, fn_cost_flat=2000.0)
    assert fp == 100.0
    assert fn == 2000.0


def test_compute_row_cost_cltv_model():
    """Config CLTV: FP baseado em monthly * meses * desconto; FN baseado em CLTV."""
    from ml.evaluate_production import _compute_row_cost
    from domain.constants import CostModel
    config = {
        "cost_model": CostModel.CLTV,
        "fp_cost_months": 2.0, "fp_cost_discount": 0.5,
        "fn_cost_cltv_multiplier": 3.0, "fn_cost_months_multiplier": 6,
    }
    row = _full_row(monthly=100.0, cltv=500.0)
    fp, fn = _compute_row_cost(row, config=config, fp_cost_flat=99.0, fn_cost_flat=99.0)
    assert fp == pytest.approx(100.0 * 2.0 * 0.5)   # 100.0
    assert fn == pytest.approx(500.0 * 3.0)          # 1500.0


def test_compute_row_cost_monthly_charges_model():
    """Config MONTHLY_CHARGES: FN baseado em monthly * meses."""
    from ml.evaluate_production import _compute_row_cost
    from domain.constants import CostModel
    config = {
        "cost_model": CostModel.MONTHLY_CHARGES,
        "fp_cost_months": 1.0, "fp_cost_discount": 1.0,
        "fn_cost_cltv_multiplier": 2.0, "fn_cost_months_multiplier": 12,
    }
    row = _full_row(monthly=200.0, cltv=0.0)
    fp, fn = _compute_row_cost(row, config=config, fp_cost_flat=99.0, fn_cost_flat=99.0)
    assert fp == pytest.approx(200.0 * 1.0 * 1.0)   # 200.0
    assert fn == pytest.approx(200.0 * 12)           # 2400.0


# ---------------------------------------------------------------------------
# _compute_cost_weighted()
# ---------------------------------------------------------------------------


def _pred_row(pred: bool, churned: bool, monthly: float = 50.0, cltv: float = 1000.0):
    return SimpleNamespace(
        churn_pred=pred, churned=churned, monthly_charges=monthly, cltv=cltv
    )


def test_compute_cost_weighted_flat_no_config():
    """Custo ponderado flat: FP*fp_cost + FN*fn_cost, averages são os custos flat."""
    from ml.evaluate_production import _compute_cost_weighted
    rows = [
        _pred_row(True,  False),   # FP
        _pred_row(False, True),    # FN
        _pred_row(True,  True),    # TP — sem custo
        _pred_row(False, False),   # TN — sem custo
    ]
    total, avg_fp, avg_fn = _compute_cost_weighted(rows, None, fp_cost_flat=100.0, fn_cost_flat=2000.0)
    assert total == pytest.approx(100.0 + 2000.0)
    assert avg_fp == pytest.approx(100.0)
    assert avg_fn == pytest.approx(2000.0)


def test_compute_cost_weighted_no_fp_no_fn_returns_flat_averages():
    """Sem FP e sem FN o custo total é zero e os averages caem para os custos flat."""
    from ml.evaluate_production import _compute_cost_weighted
    rows = [
        _pred_row(True,  True),    # TP
        _pred_row(False, False),   # TN
    ]
    total, avg_fp, avg_fn = _compute_cost_weighted(rows, None, fp_cost_flat=100.0, fn_cost_flat=2000.0)
    assert total == 0.0
    assert avg_fp == 100.0
    assert avg_fn == 2000.0


# ---------------------------------------------------------------------------
# _build_report() / _format_row()
# ---------------------------------------------------------------------------


def _model_result(name="rf", role="champion", version="v1", f1=0.8, cost=1000.0):
    return {
        "model_name": name, "model_role": role, "model_version": version,
        "total": 100,
        "cm": {"tp": 40, "fp": 10, "fn": 10, "tn": 40},
        "metrics": {"precision": 0.8, "recall": 0.8, "f1": f1},
        "cost": cost,
    }


def test_build_report_contains_project_and_window():
    """Relatório inclui slug do projeto e janela temporal."""
    from ml.evaluate_production import _build_report
    results = [_model_result()]
    report = _build_report(results, "telco-churn", "90d", 100.0, 2000.0, run_id=None)
    assert "telco-churn" in report
    assert "90d" in report


def test_build_report_shows_dry_run_marker_when_no_run_id():
    """Sem run_id indica 'dry-run' no cabeçalho."""
    from ml.evaluate_production import _build_report
    results = [_model_result()]
    report = _build_report(results, "proj", "30d", 100.0, 2000.0, run_id=None)
    assert "dry-run" in report


def test_build_report_shows_run_id_when_provided():
    """Com run_id exibe o ID no cabeçalho."""
    from ml.evaluate_production import _build_report
    results = [_model_result()]
    report = _build_report(results, "proj", "30d", 100.0, 2000.0, run_id="abc-123")
    assert "abc-123" in report


def test_build_report_highlights_best_f1_and_lowest_cost():
    """Relatório indica o modelo com melhor F1 e o de menor custo."""
    from ml.evaluate_production import _build_report
    results = [
        _model_result("rf", "champion", "v1", f1=0.85, cost=1000.0),
        _model_result("xgb", "challenger", "v2", f1=0.90, cost=800.0),
    ]
    report = _build_report(results, "proj", "30d", 100.0, 2000.0, run_id=None)
    assert "xgb" in report  # melhor F1 e menor custo
    assert "Melhor F1" in report
    assert "Menor custo" in report


# ---------------------------------------------------------------------------
# evaluate() — orquestração com banco mockado
# ---------------------------------------------------------------------------


def _make_engine_mock(mock_conn):
    """Cria mock de engine com context managers configurados."""
    from unittest.mock import MagicMock
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_conn)
    ctx.__exit__ = MagicMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = ctx
    begin_ctx = MagicMock()
    begin_ctx.__enter__ = MagicMock(return_value=mock_conn)
    begin_ctx.__exit__ = MagicMock(return_value=False)
    engine.begin.return_value = begin_ctx
    return engine


def test_evaluate_returns_empty_when_no_rows():
    """evaluate() retorna [] quando não há predições com outcomes no período."""
    from unittest.mock import MagicMock, patch
    from ml.evaluate_production import evaluate

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None
    mock_conn.execute.return_value.mappings.return_value.first.return_value = None
    mock_conn.execute.return_value.fetchall.return_value = []

    engine = _make_engine_mock(mock_conn)

    with patch("ml.evaluate_production._build_engine", return_value=engine), \
         patch("ml.evaluate_production._resolve_tenant_id", return_value="t-uuid"), \
         patch("ml.evaluate_production._resolve_project_id", return_value="p-uuid"):
        result = evaluate("ibm-telco", "telco-churn", days=90, fp_cost=100.0, fn_cost=2000.0)

    assert result == []


def test_evaluate_with_cost_config_logs_model_name():
    """evaluate() com cost_model_config no banco usa o cost_model do config, não flat_cli."""
    from unittest.mock import MagicMock, patch
    from ml.evaluate_production import evaluate
    from domain.constants import CostModel

    rows = [
        SimpleNamespace(
            model_id="m1", model_name="rf", model_version="v1", threshold_used=0.5,
            churn_pred=True, churned=True, churn_prob=0.85,
            monthly_charges=50.0, cltv=1200.0,
        ),
        SimpleNamespace(
            model_id="m1", model_name="rf", model_version="v1", threshold_used=0.5,
            churn_pred=False, churned=False, churn_prob=0.15,
            monthly_charges=40.0, cltv=900.0,
        ),
    ]
    role_row = SimpleNamespace(role="champion", traffic_split=None)
    cost_config_row = {
        "cost_model": CostModel.FLAT,
        "fp_cost_flat": 100.0, "fn_cost_flat": 2000.0,
        "fp_cost_months": 3, "fp_cost_discount": 0.5,
        "fn_cost_cltv_multiplier": 2.0, "fn_cost_months_multiplier": 6,
    }

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.side_effect = [None, role_row]
    mock_conn.execute.return_value.mappings.return_value.first.return_value = cost_config_row
    mock_conn.execute.return_value.fetchall.side_effect = [rows, []]

    engine = _make_engine_mock(mock_conn)

    with patch("ml.evaluate_production._build_engine", return_value=engine), \
         patch("ml.evaluate_production._resolve_tenant_id", return_value="t-uuid"), \
         patch("ml.evaluate_production._resolve_project_id", return_value="p-uuid"):
        result = evaluate(
            "ibm-telco", "telco-churn", days=30,
            fp_cost=100.0, fn_cost=2000.0, dry_run=True,
        )

    assert len(result) == 1
    assert result[0]["cost_model"] == CostModel.FLAT


def test_evaluate_returns_empty_when_run_already_exists():
    """evaluate() retorna [] quando já existe um run para o mesmo período."""
    from unittest.mock import MagicMock, patch
    from ml.evaluate_production import evaluate

    existing_run = SimpleNamespace(id="existing-run-id")
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = existing_run

    engine = _make_engine_mock(mock_conn)

    with patch("ml.evaluate_production._build_engine", return_value=engine), \
         patch("ml.evaluate_production._resolve_tenant_id", return_value="t-uuid"), \
         patch("ml.evaluate_production._resolve_project_id", return_value="p-uuid"):
        result = evaluate("ibm-telco", "telco-churn", days=90, fp_cost=100.0, fn_cost=2000.0)

    assert result == []


def test_evaluate_dry_run_returns_results_without_writing():
    """evaluate() dry_run=True retorna resultados calculados sem gravar no banco."""
    from unittest.mock import MagicMock, patch
    from ml.evaluate_production import evaluate

    rows = [
        SimpleNamespace(
            model_id="m1", model_name="rf", model_version="v1", threshold_used=0.5,
            churn_pred=True, churned=True, churn_prob=0.85,
            monthly_charges=50.0, cltv=1200.0,
        ),
        SimpleNamespace(
            model_id="m1", model_name="rf", model_version="v1", threshold_used=0.5,
            churn_pred=False, churned=False, churn_prob=0.15,
            monthly_charges=40.0, cltv=900.0,
        ),
    ]
    role_row = SimpleNamespace(role="champion", traffic_split=None)

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.side_effect = [None, role_row]
    mock_conn.execute.return_value.mappings.return_value.first.return_value = None
    mock_conn.execute.return_value.fetchall.side_effect = [rows, []]

    engine = _make_engine_mock(mock_conn)

    with patch("ml.evaluate_production._build_engine", return_value=engine), \
         patch("ml.evaluate_production._resolve_tenant_id", return_value="t-uuid"), \
         patch("ml.evaluate_production._resolve_project_id", return_value="p-uuid"):
        result = evaluate(
            "ibm-telco", "telco-churn", days=30,
            fp_cost=100.0, fn_cost=2000.0, dry_run=True,
        )

    assert len(result) == 1
    assert result[0]["model_name"] == "rf"
    assert result[0]["model_role"] == "champion"
    assert result[0]["total"] == 2


def test_evaluate_full_write_path_inserts_run_and_results():
    """evaluate() dry_run=False grava evaluation_run e evaluation_run_results no banco."""
    from unittest.mock import MagicMock, patch
    from ml.evaluate_production import evaluate

    rows = [
        SimpleNamespace(
            model_id="m1", model_name="rf", model_version="v1", threshold_used=0.5,
            churn_pred=True, churned=True, churn_prob=0.85,
            monthly_charges=50.0, cltv=1200.0,
        ),
        SimpleNamespace(
            model_id="m1", model_name="rf", model_version="v1", threshold_used=0.5,
            churn_pred=False, churned=False, churn_prob=0.15,
            monthly_charges=40.0, cltv=900.0,
        ),
    ]
    role_row = SimpleNamespace(role="champion", traffic_split=None)

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.side_effect = [None, role_row]
    mock_conn.execute.return_value.mappings.return_value.first.return_value = None
    mock_conn.execute.return_value.fetchall.side_effect = [rows, []]
    mock_conn.execute.return_value.scalar_one.return_value = "run-uuid-123"

    engine = _make_engine_mock(mock_conn)

    with patch("ml.evaluate_production._build_engine", return_value=engine), \
         patch("ml.evaluate_production._resolve_tenant_id", return_value="t-uuid"), \
         patch("ml.evaluate_production._resolve_project_id", return_value="p-uuid"):
        result = evaluate(
            "ibm-telco", "telco-churn", days=30,
            fp_cost=100.0, fn_cost=2000.0, dry_run=False,
        )

    assert len(result) == 1
    assert result[0]["model_name"] == "rf"
    # engine.begin() deve ter sido chamado para gravar o run
    engine.begin.assert_called()


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_main_calls_evaluate_with_correct_arguments():
    """main() parseia sys.argv e delega para evaluate() corretamente."""
    import sys
    from unittest.mock import patch
    from ml.evaluate_production import main

    argv = [
        "prog",
        "--project", "telco-churn-2018",
        "--fp-cost", "100.0",
        "--fn-cost", "2000.0",
        "--since", "30d",
        "--dry-run",
    ]
    with patch.object(sys, "argv", argv), \
         patch("ml.evaluate_production.evaluate", return_value=[]) as mock_eval:
        main()

    mock_eval.assert_called_once()
    kwargs = mock_eval.call_args.kwargs
    assert kwargs["project_slug"] == "telco-churn-2018"
    assert kwargs["days"] == 30
    assert kwargs["fp_cost"] == pytest.approx(100.0)
    assert kwargs["dry_run"] is True


def test_main_uses_default_since_when_not_provided():
    """main() usa '90d' como padrão para --since."""
    import sys
    from unittest.mock import patch
    from ml.evaluate_production import main

    argv = ["prog", "--project", "proj", "--fp-cost", "50.0", "--fn-cost", "1000.0"]
    with patch.object(sys, "argv", argv), \
         patch("ml.evaluate_production.evaluate", return_value=[]) as mock_eval:
        main()

    assert mock_eval.call_args.kwargs["days"] == 90
