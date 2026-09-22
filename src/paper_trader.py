"""교육용 모의매매 MVP — 실제 주문 또는 네트워크 요청을 하지 않습니다."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PriceBar:
    date: str
    close: float


@dataclass(frozen=True)
class TradingConfig:
    initial_cash: float = 10_000.0
    max_position_value: float = 1_000.0
    max_loss_fraction: float = 0.05
    short_window: int = 5
    long_window: int = 20


class PaperBroker:
    """현금·보유 수량만 바꾸는 가상 브로커. 외부 주문 기능은 의도적으로 없다."""

    def __init__(self, initial_cash: float) -> None:
        self.cash = initial_cash
        self.shares = 0
        self.trades: list[dict[str, str | int | float]] = []

    def buy(self, date: str, price: float, quantity: int) -> None:
        cost = price * quantity
        if quantity <= 0 or cost > self.cash:
            return
        self.cash -= cost
        self.shares += quantity
        self.trades.append({"date": date, "side": "BUY", "price": price, "quantity": quantity, "cash_after": self.cash})

    def sell_all(self, date: str, price: float) -> None:
        if self.shares == 0:
            return
        quantity = self.shares
        self.cash += price * quantity
        self.shares = 0
        self.trades.append({"date": date, "side": "SELL", "price": price, "quantity": quantity, "cash_after": self.cash})

    def equity(self, price: float) -> float:
        return self.cash + self.shares * price


def load_prices(path: Path) -> list[PriceBar]:
    with path.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    prices = [PriceBar(row["date"], float(row["close"])) for row in rows]
    if len(prices) < 2:
        raise ValueError("가격 데이터는 두 행 이상 필요합니다.")
    if any(bar.close <= 0 for bar in prices):
        raise ValueError("close 가격은 0보다 커야 합니다.")
    return prices


def average(values: list[float]) -> float:
    return sum(values) / len(values)


def crossover_signal(closes: list[float], config: TradingConfig) -> str | None:
    """가장 최근 시점에만 교차가 일어났을 때 BUY 또는 SELL을 반환한다."""
    if len(closes) < config.long_window + 1:
        return None

    previous_short = average(closes[-config.short_window - 1:-1])
    previous_long = average(closes[-config.long_window - 1:-1])
    current_short = average(closes[-config.short_window:])
    current_long = average(closes[-config.long_window:])

    if previous_short <= previous_long and current_short > current_long:
        return "BUY"
    if previous_short >= previous_long and current_short < current_long:
        return "SELL"
    return None


def run_backtest(prices: list[PriceBar], config: TradingConfig) -> PaperBroker:
    broker = PaperBroker(config.initial_cash)
    closes: list[float] = []

    for bar in prices:
        closes.append(bar.close)
        signal = crossover_signal(closes, config)
        current_equity = broker.equity(bar.close)
        loss_limit_hit = current_equity <= config.initial_cash * (1 - config.max_loss_fraction)

        if signal == "SELL":
            broker.sell_all(bar.date, bar.close)
        elif signal == "BUY" and broker.shares == 0 and not loss_limit_hit:
            budget = min(config.max_position_value, broker.cash)
            broker.buy(bar.date, bar.close, int(budget // bar.close))

    return broker


def write_results(broker: PaperBroker, last_price: float, output_dir: Path, config: TradingConfig) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    trade_columns = ["date", "side", "price", "quantity", "cash_after"]
    with (output_dir / "trades.csv").open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=trade_columns)
        writer.writeheader()
        writer.writerows(broker.trades)

    final_equity = broker.equity(last_price)
    with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(destination, fieldnames=["initial_cash", "final_equity", "return_percent", "open_shares"])
        writer.writeheader()
        writer.writerow({
            "initial_cash": f"{config.initial_cash:.2f}",
            "final_equity": f"{final_equity:.2f}",
            "return_percent": f"{(final_equity / config.initial_cash - 1) * 100:.2f}",
            "open_shares": broker.shares,
        })


def main() -> None:
    parser = argparse.ArgumentParser(description="실제 주문을 하지 않는 교육용 모의매매")
    parser.add_argument("--prices", type=Path, required=True, help="date,close 열을 가진 CSV 파일")
    parser.add_argument("--output", type=Path, default=Path("output"), help="결과 CSV 폴더")
    args = parser.parse_args()

    config = TradingConfig()
    prices = load_prices(args.prices)
    broker = run_backtest(prices, config)
    write_results(broker, prices[-1].close, args.output, config)
    print(f"완료: {len(broker.trades)}건의 가상 거래를 {args.output}에 저장했습니다.")


if __name__ == "__main__":
    main()
