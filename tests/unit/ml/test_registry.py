"""
Testes unitários para ml/core/registry.py.

Inclui:
- _next_version(): cálculo de versão semântica
- register_in_db(): inserção em churn.models com dry-run
- log_to_mlflow(): logging no MLflow com e sem feature importances
"""

from unittest.mock import MagicMock, patch

_FAKE_METRICS = {
    "f1_mean": 0.65,
    "f1_std": 0.04,
    "roc_auc_mean": 0.85,
    "roc_auc_std": 0.02,
    "recall_mean": 0.80,
    "recall_std": 0.04,
    "precision_mean": 0.70,
    "precision_std": 0.03,
    "train_f1_mean": 0.82,
    "train_roc_auc_mean": 0.94,
    "train_recall_mean": 0.89,
    "train_precision_mean": 0.78,
}
_DUMMY_METRICS = {k: 0.25 for k in _FAKE_METRICS}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_conn(count: int) -> MagicMock:
    """Cria um mock de conexão SQLAlchemy que retorna `count` para scalar()."""
    mock_conn = MagicMock()
    mock_conn.execute.return_value.scalar.return_value = count
    return mock_conn


def _make_mock_engine() -> tuple[MagicMock, MagicMock]:
    """Retorna (mock_engine, mock_conn) configurados como context manager."""
    mock_conn = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_ctx
    return mock_engine, mock_conn


# ---------------------------------------------------------------------------
# _next_version()
# ---------------------------------------------------------------------------


def test_next_version_first_model_is_v1():
    """Quando não existe nenhum modelo registrado, retorna 'v1'."""
    from ml.core.registry import _next_version

    conn = _make_mock_conn(count=0)
    assert _next_version(conn, "tenant-uuid", "project-uuid", "random-forest") == "v1"


def test_next_version_increments_correctly():
    """Quando já existem 3 versões, retorna 'v4'."""
    from ml.core.registry import _next_version

    conn = _make_mock_conn(count=3)
    assert _next_version(conn, "tenant-uuid", "project-uuid", "random-forest") == "v4"


def test_next_version_passes_correct_params_to_query():
    """Os parâmetros tenant_id, project_id e name são passados corretamente à query."""
    from ml.core.registry import _next_version

    conn = _make_mock_conn(count=0)
    _next_version(conn, "tenant-uuid", "project-uuid", "my-model")

    call_kwargs = conn.execute.call_args[0][1]
    assert call_kwargs["tenant_id"] == "tenant-uuid"
    assert call_kwargs["project_id"] == "project-uuid"
    assert call_kwargs["name"] == "my-model"


# ---------------------------------------------------------------------------
# register_in_db() — dry-run
# ---------------------------------------------------------------------------


def test_register_in_db_dry_run_no_db_writes(capsys):
    """dry_run=True imprime o registro e não executa nenhuma query de escrita."""
    from ml.core.registry import register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v1"),
    ):
        register_in_db(
            name="global-baseline",
            run_id="test-run-id",
            metrics=_FAKE_METRICS,
            tenant_slug=None,
            project_slug=None,
            status="approved",
            dry_run=True,
        )

    captured = capsys.readouterr()
    assert "dry_run" in captured.out
    assert "db_registration_skipped" in captured.out
    mock_conn.execute.assert_not_called()


def test_register_in_db_dry_run_includes_version_in_output(capsys):
    """O output do dry-run inclui a versão calculada."""
    from ml.core.registry import register_in_db

    mock_engine, _ = _make_mock_engine()

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v3"),
    ):
        register_in_db(
            name="global-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            tenant_slug=None,
            project_slug=None,
            status="approved",
            dry_run=True,
        )

    assert "v3" in capsys.readouterr().out


def test_register_in_db_dry_run_prints_metadata(capsys):
    """O dry-run imprime hyperparameters e training_params sem escrever no banco."""
    from ml.core.registry import register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v1"),
    ):
        register_in_db(
            name="global-random-forest",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            tenant_slug=None,
            project_slug=None,
            status="approved",
            dry_run=True,
            hyperparameters={"n_estimators": 500, "max_depth": None},
            training_params={"cv_folds": 5, "primary_metric": "f1"},
        )

    output = capsys.readouterr().out
    assert "hyperparameters" in output
    assert '"n_estimators": 500' in output
    assert "training_params" in output
    assert '"primary_metric": "f1"' in output
    mock_conn.execute.assert_not_called()


# ---------------------------------------------------------------------------
# register_in_db() — escrita real
# ---------------------------------------------------------------------------


def test_register_in_db_approved_status_executes_only_insert():
    """status='approved' executa INSERT em models + INSERT em model_audit_log."""
    from ml.core.registry import register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v2"),
    ):
        register_in_db(
            name="global-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            tenant_slug=None,
            project_slug=None,
            status="approved",
            dry_run=False,
        )

    assert mock_conn.execute.call_count == 2


def test_register_in_db_candidate_status_executes_two_inserts():
    """status='candidate' executa INSERT em models + INSERT em model_audit_log."""
    from ml.core.registry import register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v1"),
    ):
        register_in_db(
            name="global-baseline",
            run_id="run-id",
            metrics=_DUMMY_METRICS,
            tenant_slug=None,
            project_slug=None,
            status="candidate",
            dry_run=False,
        )

    assert mock_conn.execute.call_count == 2


def test_register_in_db_persists_training_metadata_jsons():
    """O INSERT em churn.models recebe hyperparameters e training_params."""
    from ml.core.registry import register_in_db

    mock_engine, mock_conn = _make_mock_engine()
    hyperparameters = {"n_estimators": 500, "max_depth": None}
    training_params = {"cv_folds": 5, "cv_strategy": "StratifiedKFold"}

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v1"),
    ):
        register_in_db(
            name="global-random-forest",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            tenant_slug=None,
            project_slug=None,
            status="approved",
            dry_run=False,
            hyperparameters=hyperparameters,
            training_params=training_params,
        )

    insert_params = mock_conn.execute.call_args_list[0][0][1]
    assert insert_params["hyperparameters"] == hyperparameters
    assert insert_params["training_params"] == training_params


# ---------------------------------------------------------------------------
# register_in_db() — scopes tenant e project
# ---------------------------------------------------------------------------


def test_register_in_db_tenant_scope_calls_resolve_tenant_id():
    """Quando tenant_slug está definido, chama _resolve_tenant_id; sem project_slug, não chama _resolve_project_id."""
    from ml.core.registry import register_in_db

    mock_engine, _ = _make_mock_engine()

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v1"),
        patch("ml.core.registry.db._resolve_tenant_id", return_value="tenant-uuid") as mock_tid,
        patch("ml.core.registry.db._resolve_project_id") as mock_pid,
    ):
        register_in_db(
            name="ibm-telco-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            tenant_slug="ibm-telco",
            project_slug=None,
            status="approved",
            dry_run=True,
        )

    mock_tid.assert_called()
    mock_pid.assert_not_called()


def test_register_in_db_project_scope_calls_both_resolvers():
    """Quando tenant_slug e project_slug estão definidos, ambos os resolvers são chamados."""
    from ml.core.registry import register_in_db

    mock_engine, _ = _make_mock_engine()

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v1"),
        patch("ml.core.registry.db._resolve_tenant_id", return_value="tenant-uuid") as mock_tid,
        patch("ml.core.registry.db._resolve_project_id", return_value="project-uuid") as mock_pid,
    ):
        register_in_db(
            name="ibm-telco-telco-churn-2018-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            tenant_slug="ibm-telco",
            project_slug="telco-churn-2018",
            status="approved",
            dry_run=True,
        )

    mock_tid.assert_called()
    mock_pid.assert_called()


def test_register_in_db_tenant_scope_not_dry_run_executes_write():
    """tenant_slug sem project_slug, dry_run=False executa INSERT em models + audit log."""
    from ml.core.registry import register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v1"),
        patch("ml.core.registry.db._resolve_tenant_id", return_value="tenant-uuid"),
        patch("ml.core.registry.db._resolve_project_id", return_value=None),
    ):
        register_in_db(
            name="ibm-telco-baseline",
            run_id="run-id",
            metrics=_FAKE_METRICS,
            tenant_slug="ibm-telco",
            project_slug=None,
            status="approved",
            dry_run=False,
        )

    assert mock_conn.execute.call_count == 2


def test_register_in_db_project_scope_not_dry_run_candidate_executes_two_inserts():
    """tenant+project, dry_run=False, status='candidate' executa INSERT em models + audit log."""
    from ml.core.registry import register_in_db

    mock_engine, mock_conn = _make_mock_engine()

    with (
        patch("ml.core.registry.db._build_engine", return_value=mock_engine),
        patch("ml.core.registry.db._next_version", return_value="v1"),
        patch("ml.core.registry.db._resolve_tenant_id", return_value="tenant-uuid"),
        patch("ml.core.registry.db._resolve_project_id", return_value="project-uuid"),
    ):
        register_in_db(
            name="ibm-telco-telco-churn-2018-baseline",
            run_id="run-id",
            metrics=_DUMMY_METRICS,
            tenant_slug="ibm-telco",
            project_slug="telco-churn-2018",
            status="candidate",
            dry_run=False,
        )

    assert mock_conn.execute.call_count == 2


# ---------------------------------------------------------------------------
# log_to_mlflow()
# ---------------------------------------------------------------------------


def _make_mlflow_ctx(run_id: str = "test-run-id"):
    """Cria context manager mock para mlflow.start_run."""
    mock_run = MagicMock()
    mock_run.info.run_id = run_id
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_run)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return mock_ctx


def test_log_to_mlflow_saves_artifact_and_returns_run_id():
    """log_to_mlflow salva artefato sklearn e retorna run_id. Pipeline já fitado."""
    from ml.core.registry import log_to_mlflow

    mock_pipeline = MagicMock()

    with (
        patch("ml.core.registry.mlflow.mlflow.start_run", return_value=_make_mlflow_ctx("abc-123")),
        patch("ml.core.registry.mlflow.mlflow.log_params") as mock_params,
        patch("ml.core.registry.mlflow.mlflow.log_metrics") as mock_metrics,
        patch("ml.core.registry.mlflow.mlflow.sklearn.save_model"),
        patch("ml.core.registry.mlflow.mlflow.log_artifacts") as mock_artifacts,
    ):
        run_id = log_to_mlflow(
            run_name="test_model",
            params={"model_type": "dummy"},
            metrics=_FAKE_METRICS,
            pipeline=mock_pipeline,
            log_feature_importances=False,
        )

    assert run_id == "abc-123"
    mock_params.assert_called_once()
    mock_metrics.assert_called_once_with(_FAKE_METRICS)
    mock_artifacts.assert_called_once()
    assert mock_artifacts.call_args.kwargs["artifact_path"] == "model"


def test_log_to_mlflow_does_not_call_fit_on_pipeline():
    """log_to_mlflow NÃO chama pipeline.fit — pipeline deve chegar já fitado."""
    from ml.core.registry import log_to_mlflow

    mock_pipeline = MagicMock()

    with (
        patch("ml.core.registry.mlflow.mlflow.start_run", return_value=_make_mlflow_ctx()),
        patch("ml.core.registry.mlflow.mlflow.log_params"),
        patch("ml.core.registry.mlflow.mlflow.log_metrics"),
        patch("ml.core.registry.mlflow.mlflow.sklearn.save_model"),
        patch("ml.core.registry.mlflow.mlflow.log_artifacts"),
    ):
        log_to_mlflow(
            run_name="test",
            params={},
            metrics=_FAKE_METRICS,
            pipeline=mock_pipeline,
            log_feature_importances=False,
        )

    mock_pipeline.fit.assert_not_called()


def test_log_to_mlflow_logs_feature_importances_when_flag_set(fake_customers_df):
    """log_to_mlflow com log_feature_importances=True chama mlflow.log_dict."""
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.pipeline import Pipeline

    from ml.config.settings import TARGET
    from ml.core.registry import log_to_mlflow
    from ml.data.preprocessing import build_preprocessor

    X = fake_customers_df.drop(columns=[TARGET])
    y = fake_customers_df[TARGET]

    pipeline = Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            (
                "classifier",
                RandomForestClassifier(n_estimators=5, random_state=42, class_weight="balanced"),
            ),
        ]
    )
    pipeline.fit(X, y)

    with (
        patch("ml.core.registry.mlflow.mlflow.start_run", return_value=_make_mlflow_ctx()),
        patch("ml.core.registry.mlflow.mlflow.log_params"),
        patch("ml.core.registry.mlflow.mlflow.log_metrics"),
        patch("ml.core.registry.mlflow.mlflow.sklearn.save_model"),
        patch("ml.core.registry.mlflow.mlflow.log_artifacts"),
        patch("ml.core.registry.mlflow.mlflow.log_dict") as mock_log_dict,
    ):
        log_to_mlflow(
            run_name="rf",
            params={},
            metrics=_FAKE_METRICS,
            pipeline=pipeline,
            log_feature_importances=True,
        )

    mock_log_dict.assert_called_once()
    assert mock_log_dict.call_args[0][1] == "feature_importances.json"


def test_log_to_mlflow_skips_feature_importances_when_flag_false():
    """log_to_mlflow com log_feature_importances=False não chama mlflow.log_dict."""
    from ml.core.registry import log_to_mlflow

    mock_pipeline = MagicMock()

    with (
        patch("ml.core.registry.mlflow.mlflow.start_run", return_value=_make_mlflow_ctx()),
        patch("ml.core.registry.mlflow.mlflow.log_params"),
        patch("ml.core.registry.mlflow.mlflow.log_metrics"),
        patch("ml.core.registry.mlflow.mlflow.sklearn.save_model"),
        patch("ml.core.registry.mlflow.mlflow.log_artifacts"),
        patch("ml.core.registry.mlflow.mlflow.log_dict") as mock_log_dict,
    ):
        log_to_mlflow(
            run_name="dummy",
            params={},
            metrics=_FAKE_METRICS,
            pipeline=mock_pipeline,
            log_feature_importances=False,
        )

    mock_log_dict.assert_not_called()
