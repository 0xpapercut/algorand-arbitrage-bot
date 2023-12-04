from typing import Iterable, List, Tuple, Callable
import math
import networkx
import numpy as np
import matplotlib.pyplot as plt

from .asset import Asset, ALGO
from .pool import BasePool, ArbitrageAtomicTransaction
from .account import Account

DEFAULT_MIN_AMOUNT_IN = 10_000
DEFAULT_STEP = 10_000
DEFAULT_PRECISION = 100
DEFAULT_MAX_ITERATIONS = 10
DEFAULT_GRAPH_NUM = 1000


class ArbitragePath:

    def __init__(self, graph: networkx.MultiDiGraph, path: Iterable[Tuple[Asset, Asset, int]]):
        self.edges: List[ArbitrageEdge] = []
        for asset_in, asset_out, key in path:
            data = graph.get_edge_data(asset_in, asset_out, key)
            self.edges.append(ArbitrageEdge(asset_in, asset_out, key, **data))
        assert self.edges[0].asset_in == self.edges[-1].asset_out

    def __repr__(self):
        assets = [str(edge.asset_in) for edge in self.edges] + [self.asset]
        return f"{self.__class__.__name__}<{'|'.join(assets)}>"

    def amount_out(self, amount_in: int) -> int:
        for edge in self.edges:
            if amount_in == 0:
                break
            asset_in = edge.asset_in
            amount_in = edge.pool.amount_out(asset_in, amount_in)
        return amount_in

    def profit(self, amount_in: int) -> int:
        return self.amount_out(amount_in) - amount_in

    def profit_after_fee(self, amount_in: int, suggested_params: dict) -> int:
        assert self.asset == ALGO
        return self.profit(amount_in) - self.fee(suggested_params)

    def profit_slope(self, amount_in: int, step: int, centered: bool = True) -> float:
        left, right = amount_in, amount_in + step
        if centered:
            left -= step // 2
            right -= step // 2
        return (self.profit(right) - self.profit(left)) / step

    def profit_ratio(self, amount_in: int = DEFAULT_MIN_AMOUNT_IN) -> float:
        return self.profit(amount_in) / amount_in

    def optimal_amount_in_precise(self, max_amout_in, min_amount_in = DEFAULT_MIN_AMOUNT_IN, samples = 10, iterations = 100, precision = 100):
        f = np.vectorize(self.profit)
        @np.vectorize
        def corrector(x):
            t = np.array([
                amount_out_step_start(self.amount_out, x),
                amount_out_step_end(self.amount_out, x) + 1
            ])
            return t[np.argmax(f(t))]
        left, right = corrector([min_amount_in, max_amout_in])
        while right - left > precision:
            x = corrector(np.linspace(left, right, samples, dtype=int))
            argmax = np.argmax(f(x))
            if argmax == 0:
                right = x[1]
            if argmax == samples - 1:
                return right
            else:
                left, right = x[argmax - 1], x[argmax + 1]
        return int(left)

    def optimal_amount_in_fast(self,
                          max_amount_in: int,
                          min_amount_in = DEFAULT_MIN_AMOUNT_IN,
                          step: int = DEFAULT_STEP) -> int:
        x, y = min_amount_in, max_amount_in
        if self.profit_slope(y, step) >= 0:
            return y
        while y - x > step:
            m = (x + y) // 2
            if self.profit_slope(m, step) > 0:
                x = m
            else:
                y = m
        if x == min_amount_in:
            return 0
        return int(m)

    def maximum_profit(self, max_amount_in: int, precise: bool = False) -> int:
        if precise:
            optimal_amount_in = self.optimal_amount_in_precise(max_amount_in)
        else:
            optimal_amount_in = self.optimal_amount_in_fast(max_amount_in)
        return self.profit(optimal_amount_in)

    def maximum_profit_after_fee(self, max_amount_in: int, suggested_params: dict, precise: bool = False) -> int:
        if precise:
            optimal_amount_in = self.optimal_amount_in_precise(max_amount_in)
        else:
            optimal_amount_in = self.optimal_amount_in_fast(max_amount_in)
        return self.profit_after_fee(optimal_amount_in, suggested_params)

    @property
    def ratio(self) -> float:
        ratios = (edge.pool.ratio(edge.asset_in) for edge in self.edges)
        return math.prod(ratios) - 1

    @property
    def asset(self) -> Asset:
        return self.edges[0].asset_in

    @property
    def asset_cycle(self) -> List[Asset]:
        return [edge.asset_in for edge in self.edges] + [self.edges[0].asset_in]

    def fee(self, suggested_params: dict) -> int:
        return sum(edge.pool.fee(suggested_params) for edge in self.edges)

    def prepare_txn(self, account: Account, amount_in: int, suggested_params) -> ArbitrageAtomicTransaction:
        swap_txns = []
        for edge in self.edges:
            asset_in = edge.asset_in
            amount_out = edge.pool.amount_out(asset_in, amount_in)
            swap_txn = edge.pool.prepare_swap_txn(account, asset_in, amount_in, amount_out, suggested_params)
            amount_in = amount_out
            swap_txns.append(swap_txn)
        txn = ArbitrageAtomicTransaction(swap_txns)

        return txn

    def plot(self,
             min_amount_in: int,
             max_amount_in: int,
             num: int = DEFAULT_GRAPH_NUM):
        f = np.vectorize(lambda x: self.amount_out(x))
        x = np.linspace(min_amount_in, max_amount_in, num, dtype=int)
        y = f(x)

        plt.plot(x, y)

    def plot_profit(self,
                    min_amount_in: int,
                    max_amount_in: int,
                    num: int = DEFAULT_GRAPH_NUM):
        f = np.vectorize(lambda x: self.amount_out(x))
        x = np.linspace(min_amount_in, max_amount_in, num, dtype=int)
        y = f(x) - x

        plt.plot(x, y)

    def plot_profit_after_fee(self,
                              min_amount_in: int,
                              max_amount_in: int,
                              suggested_params: dict,
                              num: int = DEFAULT_GRAPH_NUM):
        f = np.vectorize(lambda x: self.amount_out(x))
        x = np.linspace(min_amount_in, max_amount_in, num, dtype=int)
        y = f(x) - x - self.fee(suggested_params)

        plt.plot(x, y)

    # def is_there_profit(self,
    #                     min_amount_in: int = DEFAULT_MIN_AMOUNT_IN,
    #                     max_amount_in: int)

    # def _corrector(self, amount_in: int):
    #     t = np.array([
    #         amount_out_step_start(self.amount_out, amount_in),
    #         amount_out_step_end(self.amount_out, amount_in) + 1
    #     ])
    #     return t[np.argmax(self.profit(t))]


class ArbitrageEdge:

    def __init__(self, asset_in, asset_out, key, pool):
        self.asset_in = asset_in
        self.asset_out = asset_out
        self.key = key
        self.pool: BasePool = pool

    def __repr__(self):
        return str(self.pool)

    def plot(self,
              min_amount_in: int,
              max_amount_in: int,
              num: int = DEFAULT_GRAPH_NUM):
        f = np.vectorize(lambda x: self.pool.amount_out(self.asset_in, x))
        x = np.linspace(min_amount_in, max_amount_in, num, dtype=int)
        y = f(x)

        plt.plot(x, y)


class ArbitrageGraph:

    def __init__(self, pools: List[BasePool]):
        self.pools = pools
        self.construct_graph()

    def construct_graph(self):
        self.graph = networkx.MultiDiGraph()
        for pool in self.pools:
            for asset_in in pool.assets:
                self.graph.add_edge(asset_in, pool.get_other_asset(asset_in), pool=pool)

    def get_paths(self, main_asset: Asset, cutoff: int, filter=None) -> Iterable[ArbitragePath]:
        if main_asset not in self.graph:
            raise ValueError('`main_asset` must be an asset in at least one pool.')
        if filter is None:
            filter = lambda x: True

        for cycle in find_cycles(self.graph, main_asset, cutoff):
            path = ArbitragePath(self.graph, cycle)
            if filter(path):
                yield path

    def find_opportunities(self, main_asset: Asset, cutoff: int, filter=None, sort=None) -> List[ArbitragePath]:
        """Search for opportunities in the assets' graph.

        Parameters
        ----------
        main_asset : Asset
            The asset where the cycle start and ends.
        cutoff : int
            Maximum number of edges for the cycle.
        filter : callable, optional (default = None)
            Filter function.
        sort : callable, optional (default = None)
            Sort function.

        Returns
        -------
        List[ArbitragePath]
            List of possible opportunities.

        References
        ----------
        .. [1] https://networkx.org/documentation/stable/reference/algorithms/traversal.html
        .. [2] https://networkx.org/documentation/stable/reference/algorithms/simple_paths.html
        .. [3] https://networkx.org/documentation/stable/reference/algorithms/cycles.html
        """
        paths = list(self.get_paths(main_asset, cutoff, filter))
        if sort is not None:
            paths.sort(key=sort)

        return paths


def find_cycles(G: networkx.Graph, source: any, cutoff: int):
    path = []
    stack = [iter(G.edges(source, keys=True))]

    while stack:
        children = stack[-1]
        try:
            child = next(children)
            if len(path) < cutoff - 1:
                if child[1] == source:
                    yield path + [child]
                else:
                    path.append(child)
                    stack.append(iter(G.edges(child[1], keys=True)))
            else:
                for (u, v, k) in [child] + list(children):
                    if v == source:
                        yield path + [(u, v, k)]
        except StopIteration:
            stack.pop()
            if path:
                path.pop()


def amount_out_step_start(amount_out: Callable[[int], int], amount_in: int):
    dx = 1
    while (y := amount_in - 10 * dx) > 0 and amount_out(amount_in) == amount_out(y):
        dx *= 10

    while dx > 0:
        y = amount_in - dx
        if y <= 0:
            return 0
        if amount_out(amount_in) == amount_out(y):
            amount_in = y
        else:
            if dx // 10 == 0 and dx != 1:
                dx = 1
            else:
                dx //= 10

    return amount_in


def amount_out_step_end(amount_out: Callable[[int], int], amount_in: int):
    dx = 1
    while (y := amount_in + 10 * dx) > 0 and amount_out(amount_in) == amount_out(y):
        dx *= 10
    while dx > 0:
        y = amount_in + dx
        if amount_out(amount_in) == amount_out(y):
            amount_in = y
        else:
            if dx // 10 == 0 and dx != 1:
                dx = 1
            else:
                dx //= 10
    return amount_in
