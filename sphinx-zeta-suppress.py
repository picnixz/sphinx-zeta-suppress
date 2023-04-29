#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

__all__ = ()

import abc
import collections.abc
import importlib
import inspect
import logging
import pkgutil
import re
import warnings
from itertools import filterfalse, tee
from typing import TYPE_CHECKING

from sphinx.util.logging import NAMESPACE, SphinxLoggerAdapter

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator
    from typing import Any, Literal, TypeGuard, TypeVar

    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.extension import Extension

    T = TypeVar('T')

    #: Logging level type.
    Level = TypeVar('Level', int, str)

def _notnone(value):
    # type: (Any) -> TypeGuard[Literal[None]]
    return value is not None

def _is_sphinx_logger_adapter(value):
    # type: (Any) -> TypeGuard[SphinxLoggerAdapter]
    return isinstance(value, SphinxLoggerAdapter)

def _is_pattern_like(obj):
    # type: (Any) -> TypeGuard[str | re.Pattern]
    return isinstance(obj, (str, re.Pattern))

def _partition(predicate, iterable):
    # type: (Callable[[T], bool], Iterable[T]) -> (Iterator[T], Iterator[T])
    """Partition an iterable into two iterators according to *predicate*.

    The result is `(no, yes)` of iterators such that *no* and *yes* iterate
    over the values in *iterable* for which *predicate* is falsey and truthy
    respectively.

    Typical usage::

        odd, even = partition(lambda x: x % 2 == 0, range(10))

        assert list(odd) == [1, 3, 5, 7, 8]
        assert list(even) == [0, 2, 4, 6, 8]
    """

    no, yes = tee(iterable)
    no, yes = filterfalse(predicate, no), filter(predicate, yes)
    return no, yes

def _normalize_level(level):
    # type: (Level) -> int | None
    """Convert a logging level name or integer into a known logging level."""
    if isinstance(level, int):
        return level

    try:
        # pylint: disable-next=W0212
        return logging._nameToLevel[level]
    except KeyError:
        return None
    except TypeError:
        raise TypeError(f'invalid logging level type for {level}')

def _parse_levels(levels):
    # type: (Level | collections.abc.Iterable[Level]) -> list[int]
    """Convert one or more logging levels into a list of logging levels."""
    if not isinstance(levels, collections.abc.Iterable):
        if not isinstance(levels, (int, str)):
            raise TypeError('invalid logging level type')
        levels = [levels]
    return list(filter(_notnone, map(_normalize_level, levels)))

class SphinxSuppressFilter(logging.Filter, metaclass=abc.ABCMeta):
    def filter(self, record):
        # type: (logging.LogRecord) -> bool
        return not self.suppressed(record)

    @abc.abstractmethod
    def suppressed(self, record):
        # type: (logging.LogRecord) -> bool
        """Indicate whether *record* should be suppressed or not."""
        pass

class _All:
    """Container simulating the universe."""

    def __contains__(self, item):
        # type: (Any) -> Literal[True]
        return True

_ALL = _All()

class SphinxSuppressLogger(SphinxSuppressFilter):
    r"""A filter suppressing logging records issued by a Sphinx logger."""

    def __init__(self, name: str, levels=()):
        """
        Construct a :class:`SphinxSuppressLogger`.

        :param name: The (real) logger name to suppress.
        :type name: str
        :param levels: Optional logging levels to suppress.
        :type levels: bool | Level | list[Level] | tuple[Level, ...]
        """

        super().__init__(name)
        if isinstance(levels, bool):
            levels = _ALL if levels else []
        else:
            levels = _parse_levels(levels)

        #: List of logging levels to suppress.
        self.levels: list[int] = levels

    def suppressed(self, record):
        should_log = logging.Filter.filter(self, record)
        return not should_log or record.levelno in self.levels

class SphinxSuppressPatterns(SphinxSuppressFilter):
    r"""A filter suppressing matching messages."""

    def __init__(self, patterns=()):
        """
        Construct a :class:`SphinxSuppressPatterns`.

        :param patterns: Optional logging messages (regex) to suppress.
        :type patterns: list[str | re.Pattern]
        """

        super().__init__('')  # all loggers
        #: Set of patterns to search.
        self.patterns: set[re.Pattern] = set(map(re.compile, patterns))

    def suppressed(self, record):
        if not self.patterns:
            return False

        m = record.getMessage()
        return any(p.search(m) for p in self.patterns)

class SphinxSuppressRecord(SphinxSuppressLogger, SphinxSuppressPatterns):
    r"""A filter suppressing matching messages by logger's name pattern."""

    def __init__(self, name, levels=(), patterns=()):
        """
        Construct a :class:`SphinxSuppressRecord` filter.

        :param name: A logger's name to suppress.
        :type name: str
        :param levels: Optional logging levels to suppress.
        :type levels: bool | list[int]
        :param patterns: Optional logging messages (regex) to suppress.
        :type patterns: list[str | re.Pattern]
        """

        SphinxSuppressLogger.__init__(self, name, levels)
        SphinxSuppressPatterns.__init__(self, patterns)

    def suppressed(self, record):
        return (
            SphinxSuppressLogger.suppressed(self, record)
            and SphinxSuppressPatterns.suppressed(self, record)
        )

def _get_filters(config):
    """
    Get the default filter and the filters by logger's prefix.

    :param config: The current Sphinx configuration.
    :type config: sphinx.config.Config
    :return: The default filter and a list of filters by logger's prefix.
    :rtype: tuple[SphinxSuppressFilter, dict[str, list[SphinxSuppressFilter]]]
    """

    format_name = lambda name: f'{NAMESPACE}.{name}'

    filters_by_prefix = {}
    for name, levels in config.zeta_suppress_loggers.items():
        prefix = format_name(name)
        suppressor = SphinxSuppressLogger(prefix, levels)
        filters_by_prefix.setdefault(prefix, []).append(suppressor)

    suppress_records = config.zeta_suppress_records
    groups, patterns = _partition(_is_pattern_like, suppress_records)
    for group in groups:  # type: tuple[str, ...]
        prefix = format_name(group[0])
        suppressor = SphinxSuppressRecord(prefix, True, group[1:])
        filters_by_prefix.setdefault(prefix, []).append(suppressor)
    # default filter
    default_filter = SphinxSuppressPatterns(patterns)
    return default_filter, filters_by_prefix

def _update_logger_in(module, default_filter, filters_by_prefix, _cache):
    """Alter the Sphinx loggers accessible in *module*.

    :param module: The module to alter.
    :type module: types.ModuleType
    :param default_filter: The default filter.
    :type default_filter: SphinxSuppressFilter
    :param filters_by_prefix: List of filters indexed by logger's prefix.
    :type filters_by_prefix: dict[str, list[SphinxSuppressFilter]]
    :param _cache: Cache of module names that were already altered.
    :type _cache: set[str]
    """

    if module.__name__ in _cache:
        return

    _cache.add(module.__name__)
    members = inspect.getmembers(module, _is_sphinx_logger_adapter)
    for _, adapter in members:
        for prefix, filters in filters_by_prefix.items():
            if adapter.logger.name.startswith(prefix):
                # a logger might be imported from a module
                # that was not yet marked, so we only add
                # the filter once
                for f in filters:
                    if f not in adapter.logger.filters:
                        adapter.logger.addFilter(f)
        if default_filter not in adapter.logger.filters:
            adapter.logger.addFilter(default_filter)

def install_supress_handlers(app, config):
    # type: (Sphinx, Config) -> None
    """Event handler for :confval:`config-inited`.

    This handler should have the lowest priority among :confval:`config-inited`
    handlers. Sphinx loggers declared after :confval:`config-inited` is fired
    will not be altered or recognized at runtime.
    """

    default_filter, filters_by_prefix = _get_filters(config)
    seen = set()

    for extension in app.extensions.values():  # type: Extension
        if extension.name in config.zeta_suppress_protect:
            # skip the extension
            continue

        mod = extension.module
        _update_logger_in(mod, default_filter, filters_by_prefix, seen)
        if not hasattr(mod, '__path__'):
            continue

        # find the loggers declared in a submodule
        mod_path, mod_prefix = mod.__path__, mod.__name__ + '.'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            warnings.simplefilter('ignore', PendingDeprecationWarning)
            for mod_info in pkgutil.iter_modules(mod_path, mod_prefix):
                if mod_info.name in config.zeta_suppress_protect:
                    # skip the module
                    continue

                try:
                    mod = importlib.import_module(mod_info.name)
                except ImportError:
                    continue
                _update_logger_in(mod, default_filter, filters_by_prefix, seen)

def setup(app):
    # type: (Sphinx) -> dict
    app.add_config_value('zeta_suppress_loggers', {}, True)
    app.add_config_value('zeta_suppress_protect', [], True)
    app.add_config_value('zeta_suppress_records', [], True)
    # @contract: no logger is emitting a message before 'config-inited' is fired
    app.connect('config-inited', install_supress_handlers, priority=0)
    # @contract: no extension is loaded after config-inited is fired
    app.connect('config-inited', install_supress_handlers, priority=1000)
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
