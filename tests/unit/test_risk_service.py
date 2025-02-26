import pytest
from src.domain.services.risk_service import RiskService

@pytest.fixture
def risk_service():
    rs = RiskService()
    yield rs
    rs.close()

def test_calculate_var(risk_service):
    var = risk_service.calculate_var("2330")
    assert var is not None, "VaR calculation failed"
    assert var < 0, "VaR should be negative (potential loss)"

def test_calculate_sharpe_ratio(risk_service):
    sharpe = risk_service.calculate_sharpe_ratio("2330")
    assert sharpe is not None, "Sharpe Ratio calculation failed"

def test_calculate_beta(risk_service):
    beta = risk_service.calculate_beta("2330")
    assert beta is not None, "Beta calculation failed"

def test_calculate_max_drawdown(risk_service):
    mdd = risk_service.calculate_max_drawdown("2330")
    assert mdd is not None, "Max Drawdown calculation failed"
    assert mdd <= 0, "Max Drawdown should be zero or negative"

def test_calculate_volatility(risk_service):
    vol = risk_service.calculate_volatility("2330")
    assert vol is not None, "Volatility calculation failed"
    assert vol >= 0, "Volatility should be non-negative"

def test_calculate_cvar(risk_service):
    cvar = risk_service.calculate_cvar("2330")
    assert cvar is not None, "CVaR calculation failed"
    assert cvar < 0, "CVaR should be negative (potential loss)"

def test_calculate_sortino_ratio(risk_service):
    sortino = risk_service.calculate_sortino_ratio("2330")
    assert sortino is not None, "Sortino Ratio calculation failed"

def test_calculate_jensen_alpha(risk_service):
    alpha = risk_service.calculate_jensen_alpha("2330")
    assert alpha is not None, "Jensen's Alpha calculation failed"

def test_calculate_treynor_ratio(risk_service):
    treynor = risk_service.calculate_treynor_ratio("2330")
    assert treynor is not None, "Treynor Ratio calculation failed"