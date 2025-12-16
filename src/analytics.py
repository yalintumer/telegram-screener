"""
Analytics and reporting module for telegram-screener
Tracks system performance, generates weekly reports
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

from .logger import logger
from .signal_tracker import SignalTracker


class Analytics:
    """System analytics and reporting"""

    def __init__(self, data_file: str = "analytics_data.json"):
        """Initialize analytics with data persistence"""
        self.data_file = Path(data_file)
        self.data = self._load_data()

    def _load_data(self) -> dict:
        """Load analytics data from file"""
        if self.data_file.exists():
            try:
                with open(self.data_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.error("analytics_load_failed", error=str(e))
                return self._default_data()
        return self._default_data()

    def _default_data(self) -> dict:
        """Default analytics data structure"""
        return {
            "market_scans": [],
            "stage1_scans": [],
            "stage2_scans": [],
            "alerts_sent": [],
            "last_report_date": None
        }

    def _save_data(self):
        """Save analytics data to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error("analytics_save_failed", error=str(e))

    def record_market_scan(self, found: int, added: int, updated: int):
        """Record market scanner run statistics"""
        self.data["market_scans"].append({
            "timestamp": datetime.now().isoformat(),
            "found": found,
            "added": added,
            "updated": updated
        })
        self._save_data()

    def record_stage1_scan(self, checked: int, passed: int):
        """Record Stage 1 (Stoch RSI + MFI) scan statistics"""
        self.data["stage1_scans"].append({
            "timestamp": datetime.now().isoformat(),
            "checked": checked,
            "passed": passed,
            "pass_rate": (passed / checked * 100) if checked > 0 else 0
        })
        self._save_data()

    def record_stage2_scan(self, checked: int, confirmed: int):
        """Record Stage 2 (WaveTrend) scan statistics"""
        self.data["stage2_scans"].append({
            "timestamp": datetime.now().isoformat(),
            "checked": checked,
            "confirmed": confirmed,
            "confirmation_rate": (confirmed / checked * 100) if checked > 0 else 0
        })
        self._save_data()

    def record_alert_sent(self, symbol: str, price: float):
        """Record Telegram alert sent"""
        self.data["alerts_sent"].append({
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "price": price
        })
        self._save_data()

    def get_weekly_stats(self) -> dict:
        """
        Get statistics for the past 7 days
        
        Returns:
            Dictionary with weekly analytics
        """
        cutoff = datetime.now() - timedelta(days=7)

        # Filter data for past 7 days
        market_scans = [
            s for s in self.data["market_scans"]
            if datetime.fromisoformat(s["timestamp"]) > cutoff
        ]
        stage1_scans = [
            s for s in self.data["stage1_scans"]
            if datetime.fromisoformat(s["timestamp"]) > cutoff
        ]
        stage2_scans = [
            s for s in self.data["stage2_scans"]
            if datetime.fromisoformat(s["timestamp"]) > cutoff
        ]
        alerts = [
            a for a in self.data["alerts_sent"]
            if datetime.fromisoformat(a["timestamp"]) > cutoff
        ]

        # Calculate aggregates
        total_market_scans = len(market_scans)
        total_stage1_scans = len(stage1_scans)
        total_stage2_scans = len(stage2_scans)
        total_alerts = len(alerts)

        avg_stage1_pass_rate = (
            sum(s["pass_rate"] for s in stage1_scans) / len(stage1_scans)
            if stage1_scans else 0
        )
        avg_stage2_confirm_rate = (
            sum(s["confirmation_rate"] for s in stage2_scans) / len(stage2_scans)
            if stage2_scans else 0
        )

        return {
            "period": "Last 7 days",
            "market_scans": total_market_scans,
            "stage1_scans": total_stage1_scans,
            "stage2_scans": total_stage2_scans,
            "alerts_sent": total_alerts,
            "avg_stage1_pass_rate": avg_stage1_pass_rate,
            "avg_stage2_confirm_rate": avg_stage2_confirm_rate,
            "alert_symbols": list(set(a["symbol"] for a in alerts))
        }

    def generate_weekly_report(self, signal_tracker: SignalTracker) -> str:
        """
        Generate comprehensive weekly report
        
        Args:
            signal_tracker: SignalTracker instance for signal performance data
            
        Returns:
            Formatted report string
        """
        stats = self.get_weekly_stats()

        # Get signal performance from tracker
        all_stats = signal_tracker.get_all_stats()

        # Calculate overall performance
        total_signals = len(all_stats)
        evaluated_signals = sum(1 for s in all_stats.values() if s['evaluated'] > 0)

        if evaluated_signals > 0:
            avg_return = sum(s['avg_return'] for s in all_stats.values() if s['evaluated'] > 0) / evaluated_signals
            avg_win_rate = sum(s['win_rate'] for s in all_stats.values() if s['evaluated'] > 0) / evaluated_signals
        else:
            avg_return = 0
            avg_win_rate = 0

        # Build report
        lines = [
            "=" * 60,
            "📊 WEEKLY TELEGRAM SCREENER REPORT",
            "=" * 60,
            "",
            f"📅 Period: {stats['period']}",
            "",
            "🔍 SCANNING ACTIVITY:",
            f"   • Market Scans (Stage 0): {stats['market_scans']}",
            f"   • Stage 1 Scans: {stats['stage1_scans']} (Avg pass rate: {stats['avg_stage1_pass_rate']:.1f}%)",
            f"   • Stage 2 Scans: {stats['stage2_scans']} (Avg confirm rate: {stats['avg_stage2_confirm_rate']:.1f}%)",
            "",
            "🚨 ALERTS:",
            f"   • Total Alerts Sent: {stats['alerts_sent']}",
            f"   • Unique Symbols: {len(stats['alert_symbols'])}",
        ]

        if stats['alert_symbols']:
            lines.append(f"   • Symbols: {', '.join(stats['alert_symbols'])}")

        lines.extend([
            "",
            "📈 SIGNAL PERFORMANCE:",
            f"   • Total Symbols Tracked: {total_signals}",
            f"   • Signals Evaluated (7+ days old): {evaluated_signals}",
        ])

        if evaluated_signals > 0:
            lines.extend([
                f"   • Average Return: {avg_return:+.2f}%",
                f"   • Average Win Rate: {avg_win_rate:.1f}%",
                "",
                "🏆 TOP PERFORMERS:",
            ])

            # Sort by avg return and show top 5
            sorted_symbols = sorted(
                [(sym, s) for sym, s in all_stats.items() if s['evaluated'] > 0],
                key=lambda x: x[1]['avg_return'],
                reverse=True
            )[:5]

            for symbol, perf in sorted_symbols:
                lines.append(
                    f"   • {symbol}: {perf['avg_return']:+.2f}% return, "
                    f"{perf['win_rate']:.0f}% win rate ({perf['evaluated']} signals)"
                )
        else:
            lines.append("   • No signals evaluated yet (need 7+ days)")

        lines.extend([
            "",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
        ])

        return "\n".join(lines)

    def should_send_weekly_report(self) -> bool:
        """Check if weekly report should be sent (once per week)"""
        if not self.data["last_report_date"]:
            return True

        last_report = datetime.fromisoformat(self.data["last_report_date"])
        days_since = (datetime.now() - last_report).days

        return days_since >= 7

    def mark_report_sent(self):
        """Mark that weekly report was sent"""
        self.data["last_report_date"] = datetime.now().isoformat()
        self._save_data()
