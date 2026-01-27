#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import ClassVar

import httpx
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import DataTable, Footer, Header, Log, Static


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    name: str
    port: int
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: datetime | None = None
    response_time_ms: float = 0.0


class ServiceHealthPanel(Static):
    SERVICES: ClassVar[list[tuple[str, int]]] = [
        ("Claude", 5011),
        ("Gemini", 5012),
        ("Codex", 5013),
        ("Gateway", 8000),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.services: dict[str, ServiceInfo] = {
            name: ServiceInfo(name=name, port=port) for name, port in self.SERVICES
        }

    def compose(self) -> ComposeResult:
        yield Static("Service Health", classes="panel-title")
        yield DataTable(id="health-table")

    def on_mount(self) -> None:
        table = self.query_one("#health-table", DataTable)
        table.add_columns("Service", "Port", "Status", "Response", "Last Check")
        self._update_table()

    def _update_table(self) -> None:
        table = self.query_one("#health-table", DataTable)
        table.clear()
        for svc in self.services.values():
            status_text = self._format_status(svc.status)
            response = f"{svc.response_time_ms:.0f}ms" if svc.response_time_ms > 0 else "-"
            last_check = svc.last_check.strftime("%H:%M:%S") if svc.last_check else "-"
            table.add_row(svc.name, str(svc.port), status_text, response, last_check)

    def _format_status(self, status: ServiceStatus) -> Text:
        styles = {
            ServiceStatus.HEALTHY: ("● HEALTHY", "green"),
            ServiceStatus.UNHEALTHY: ("● UNHEALTHY", "red"),
            ServiceStatus.UNKNOWN: ("● UNKNOWN", "yellow"),
        }
        label, color = styles[status]
        return Text(label, style=color)

    def update_service(self, name: str, status: ServiceStatus, response_ms: float) -> None:
        if name in self.services:
            self.services[name].status = status
            self.services[name].response_time_ms = response_ms
            self.services[name].last_check = datetime.now()
            self._update_table()


class MetricsPanel(Static):
    def __init__(self) -> None:
        super().__init__()
        self.total_requests = 0
        self.success_rate = 0.0
        self.avg_latency = 0.0
        self.active_connections = 0

    def compose(self) -> ComposeResult:
        yield Static("Metrics Overview", classes="panel-title")
        yield Static(id="metrics-content")

    def on_mount(self) -> None:
        self._update_display()

    def _update_display(self) -> None:
        content = self.query_one("#metrics-content", Static)
        text = Text()
        text.append("Total Requests:    ", style="bold")
        text.append(f"{self.total_requests:,}\n", style="cyan")
        text.append("Success Rate:      ", style="bold")
        rate_color = (
            "green" if self.success_rate >= 95 else "yellow" if self.success_rate >= 80 else "red"
        )
        text.append(f"{self.success_rate:.1f}%\n", style=rate_color)
        text.append("Avg Latency:       ", style="bold")
        text.append(f"{self.avg_latency:.1f}ms\n", style="cyan")
        text.append("Active Connections:", style="bold")
        text.append(f" {self.active_connections}", style="cyan")
        content.update(text)

    def update_metrics(
        self, total: int, success_rate: float, latency: float, connections: int
    ) -> None:
        self.total_requests = total
        self.success_rate = success_rate
        self.avg_latency = latency
        self.active_connections = connections
        self._update_display()


class LogPanel(Static):
    def compose(self) -> ComposeResult:
        yield Static("Live Logs", classes="panel-title")
        yield Log(id="log-view", max_lines=100)

    def add_log(self, message: str, level: str = "INFO") -> None:
        log_view = self.query_one("#log-view", Log)
        timestamp = datetime.now().strftime("%H:%M:%S")
        level_colors = {"INFO": "cyan", "WARN": "yellow", "ERROR": "red", "SUCCESS": "green"}
        color = level_colors.get(level, "white")
        log_view.write_line(f"[{color}][{timestamp}] [{level}] {message}[/{color}]")


class SynapsDashboard(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
    }

    .panel {
        border: solid green;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
    }

    #health-panel {
        column-span: 1;
        row-span: 1;
    }

    #metrics-panel {
        column-span: 1;
        row-span: 1;
    }

    #log-panel {
        column-span: 2;
        row-span: 1;
    }

    DataTable {
        height: auto;
    }

    Log {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("c", "clear_logs", "Clear Logs"),
    ]

    TITLE = "Synaps AI Agent Dashboard"

    def __init__(self) -> None:
        super().__init__()
        self.gateway_url = "http://localhost:8000"
        self._refresh_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            ServiceHealthPanel(id="health-panel", classes="panel"),
            MetricsPanel(id="metrics-panel", classes="panel"),
            LogPanel(id="log-panel", classes="panel"),
        )
        yield Footer()

    async def on_mount(self) -> None:
        self._log("Dashboard started")
        self._start_auto_refresh()

    def _log(self, message: str, level: str = "INFO") -> None:
        try:
            log_panel = self.query_one("#log-panel", LogPanel)
            log_panel.add_log(message, level)
        except Exception:
            pass

    def _start_auto_refresh(self) -> None:
        self._check_services_background()

    @work(exclusive=True)
    async def _check_services_background(self) -> None:
        while True:
            await self._check_all_services()
            await asyncio.sleep(5)

    async def _check_all_services(self) -> None:
        health_panel = self.query_one("#health-panel", ServiceHealthPanel)
        metrics_panel = self.query_one("#metrics-panel", MetricsPanel)

        for name, port in ServiceHealthPanel.SERVICES:
            status, response_ms = await self._check_service_health(name, port)
            health_panel.update_service(name, status, response_ms)

        await self._fetch_gateway_metrics(metrics_panel)

    async def _check_service_health(self, name: str, port: int) -> tuple[ServiceStatus, float]:
        url = f"http://localhost:{port}"
        if name == "Gateway":
            url = f"{self.gateway_url}/health"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                start = asyncio.get_event_loop().time()
                response = await client.get(url)
                elapsed = (asyncio.get_event_loop().time() - start) * 1000

                if response.status_code == 200:
                    return ServiceStatus.HEALTHY, elapsed
                return ServiceStatus.UNHEALTHY, elapsed
        except httpx.ConnectError:
            return ServiceStatus.UNHEALTHY, 0.0
        except Exception as e:
            self._log(f"Health check failed for {name}: {e}", "WARN")
            return ServiceStatus.UNKNOWN, 0.0

    async def _fetch_gateway_metrics(self, metrics_panel: MetricsPanel) -> None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.gateway_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    metrics_panel.update_metrics(
                        total=data.get("total_requests", 0),
                        success_rate=data.get("success_rate", 0.0),
                        latency=data.get("avg_latency_ms", 0.0),
                        connections=data.get("active_connections", 0),
                    )
        except Exception:
            pass

    def action_refresh(self) -> None:
        self._log("Manual refresh triggered", "INFO")
        self._check_services_background()

    def action_clear_logs(self) -> None:
        log_view = self.query_one("#log-view", Log)
        log_view.clear()
        self._log("Logs cleared", "INFO")


def main() -> None:
    app = SynapsDashboard()
    app.run()


if __name__ == "__main__":
    main()
