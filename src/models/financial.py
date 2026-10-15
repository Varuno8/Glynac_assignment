"""Financial data models representing client accounts, holdings, and transactions."""

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import Field, field_validator, model_validator

from src.models.common import ClientId, ValidatedModel


class AssetClass(str, Enum):
    US_EQUITY = "US_EQUITY"
    INTL_EQUITY = "INTL_EQUITY"
    FIXED_INCOME = "FIXED_INCOME"
    REAL_ESTATE = "REAL_ESTATE"
    COMMODITIES = "COMMODITIES"
    CRYPTO = "CRYPTO"
    CASH = "CASH"


class AccountType(str, Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    BROKERAGE_TAXABLE = "BROKERAGE_TAXABLE"
    TRADITIONAL_401K = "TRADITIONAL_401K"
    ROTH_401K = "ROTH_401K"
    TRADITIONAL_IRA = "TRADITIONAL_IRA"
    ROTH_IRA = "ROTH_IRA"


class TransactionType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class Holding(ValidatedModel):
    ticker: str
    asset_class: AssetClass
    shares: float = Field(ge=0)
    current_price: float = Field(ge=0)
    market_value: float = Field(ge=0)
    cost_basis: Optional[float] = Field(default=None, ge=0)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value):
        value = value.strip().upper()
        if not value:
            raise ValueError("Ticker must not be empty")
        return value

    @property
    def unrealized_gain_loss(self) -> Optional[float]:
        if self.cost_basis is not None:
            return self.market_value - self.cost_basis
        return None


class Account(ValidatedModel):
    account_id: str
    type: AccountType
    institution: str
    balance: float = Field(ge=0)
    currency: str = "USD"
    interest_rate_apy: Optional[float] = Field(
        default=None, ge=0, le=1, description="Fraction: 0.0005 = 0.05% APY"
    )
    holdings: List[Holding] = Field(default_factory=list)

    @field_validator("currency")
    @classmethod
    def usd_only(cls, value):
        if value != "USD":
            raise ValueError("Only USD is supported; convert foreign balances before ingestion")
        return value


class MonthlyCashflow(ValidatedModel):
    average_monthly_net_income: float = Field(ge=0)
    average_monthly_expenses: float = Field(ge=0)
    monthly_mortgage: float = Field(default=0.0, ge=0)


class Transaction(ValidatedModel):
    tx_id: str
    date: str
    account_id: str
    category: str
    amount: float = Field(gt=0)
    type: TransactionType
    description: str
    flagged_by_bank: bool = False

    @field_validator("date")
    @classmethod
    def valid_date(cls, value):
        return date.fromisoformat(value).isoformat()


class EmploymentInfo(ValidatedModel):
    occupation: str
    annual_income: float = Field(ge=0)
    employer: str


class ClientFinancialData(ValidatedModel):
    client_id: ClientId
    name: str
    age: int = Field(ge=0, le=120)
    employment: EmploymentInfo
    accounts: List[Account]
    monthly_cashflow: MonthlyCashflow
    recent_transactions: List[Transaction] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self):
        ids = [a.account_id for a in self.accounts]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate account IDs")
        tx_ids = [t.tx_id for t in self.recent_transactions]
        if len(tx_ids) != len(set(tx_ids)):
            raise ValueError("Duplicate transaction IDs")
        if any(t.account_id not in ids for t in self.recent_transactions):
            raise ValueError("Transaction references an unknown account")
        return self

    @property
    def total_liquid_net_worth(self) -> float:
        return self.valuation().total

    @property
    def total_cash_balance(self) -> float:
        return self.valuation().available_cash

    def valuation(self) -> "PortfolioValuation":
        """Market values are authoritative. Unclassified balances are never assumed cash."""
        assets = {a.value: 0.0 for a in AssetClass}
        assets["UNCLASSIFIED"] = 0.0
        positions = {}
        warnings = []
        available_cash = 0.0
        for account in self.accounts:
            if account.type in (AccountType.CHECKING, AccountType.SAVINGS):
                assets["CASH"] += account.balance
                available_cash += account.balance
            elif not account.holdings:
                assets["UNCLASSIFIED"] += account.balance
                if account.balance:
                    warnings.append(f"{account.account_id}: investment balance has no holdings breakdown")
            else:
                holdings_total = sum(h.market_value for h in account.holdings)
                if abs(holdings_total - account.balance) > 0.01:
                    warnings.append(
                        f"{account.account_id}: balance differs from holdings; using market values"
                    )
                for holding in account.holdings:
                    assets[holding.asset_class.value] += holding.market_value
                    if holding.asset_class in (AssetClass.US_EQUITY, AssetClass.INTL_EQUITY):
                        positions[holding.ticker] = positions.get(holding.ticker, 0.0) + holding.market_value
                    if (
                        holding.asset_class == AssetClass.CASH
                        and account.type == AccountType.BROKERAGE_TAXABLE
                    ):
                        available_cash += holding.market_value
        return PortfolioValuation(
            total=sum(assets.values()),
            available_cash=available_cash,
            asset_values=assets,
            equity_positions=positions,
            warnings=warnings,
        )


class PortfolioValuation(ValidatedModel):
    total: float
    available_cash: float
    asset_values: dict[str, float]
    equity_positions: dict[str, float]
    warnings: list[str]
