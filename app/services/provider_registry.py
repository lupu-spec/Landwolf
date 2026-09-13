from dataclasses import dataclass
from typing import Protocol


class Provider(Protocol):
    name: str
    def fetch(self, **kwargs): ...


@dataclass
class ProviderRegistry:
    providers: dict[str, Provider]

    def register(self, provider: Provider):
        self.providers[provider.name] = provider

    def get(self, name: str):
        return self.providers[name]
