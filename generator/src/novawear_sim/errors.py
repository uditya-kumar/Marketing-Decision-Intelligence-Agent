"""Errors raised by the generator, reported by the CLI without a traceback."""


class GeneratorError(Exception):
    """Base class for expected, user-facing generator failures."""


class ConfigError(GeneratorError):
    """A config file is missing or does not match its schema."""


class ScenarioError(GeneratorError):
    """A scheduled scenario cannot be applied to the world (bad target or params)."""
