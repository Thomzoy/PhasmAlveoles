import uasyncio as asyncio
import helpers as h
from configuration import PWMS
from time import sleep

try:
    from ulab import numpy as np
except ImportError:
    import numpy as np

import random


def choice(choices, p):
    MIN = min(100, min(int(1 / prob) for prob in p if prob != 0))
    weighted_choices = []
    for c, prob in zip(choices, p):
        if prob == 0:
            continue
        weighted_choices.extend(int(MIN * prob) * [c])

    return weighted_choices[random.randint(0, len(weighted_choices) - 1)]


def get_adj(coords):
    """
    Build the adjacency matrix
    """
    N = len(coords)
    neighbours = [
        (idx0, idx1)
        for idx0, (i0, j0) in enumerate(coords)
        for idx1, (i1, j1) in enumerate(coords)
        if (max(abs(i1 - i0), abs(j0 - j1)) <= 1)
    ]

    adj_mat = np.zeros((N, N))

    for i, j in neighbours:
        adj_mat[i, j] = 1

    norm_adj_mat = (adj_mat.T / np.sum(adj_mat, axis=0)).T

    for i in range(len(adj_mat)):
        norm_adj_mat[i, i] = 0  # Or 1, depending on the program

    return adj_mat, norm_adj_mat


class Propagate:
    """
    Classe to propagate light on the grid
    """

    def __init__(
        self,
        norm_adj_mat,
        starting_vector=None,
        random_restart=True,
        decay=0.1,
        max_intensity=1023,
    ):
        self.N = len(norm_adj_mat)
        self.norm_adj_mat = norm_adj_mat

        self.random_restart = random_restart

        self.decay = decay
        self.max_intensity = max_intensity
        self.setup(starting_vector=starting_vector)

    def setup(self, starting_vector):

        self.starting_vector = (
            np.array(starting_vector)
            if starting_vector is not None
            else np.array(6 * [0] + [0.1] + (self.N - 7) * [0])
        )

        self.vectors = dict(
            light_vector=self.starting_vector.copy(),
            shadow_vector=self.starting_vector.copy(),
        )

        self.steps_weight = dict(
            light_vector=1,
            shadow_vector=0,
        )

        self.state = self.starting_vector.copy()
        self.ratio_filled = self.get_ratio_filled()
        self.run_shadow = False

    def get_ratio_filled(self):
        return np.sum(self.state) / self.N

    def set_shadow_state(self):
        self.ratio_filled = self.get_ratio_filled()
        if self.run_shadow:
            return
        if self.ratio_filled > 0.5:
            self.run_shadow = True
        return

    def global_step(self):

        self.set_shadow_state()

        self.vectors["light_vector"] = np.clip(
            self.vectors["light_vector"]
            + self.decay * np.dot(self.norm_adj_mat, self.vectors["light_vector"]),
            0,
            1,
        )

        if self.run_shadow:
            self.vectors["shadow_vector"] = np.clip(
                self.vectors["shadow_vector"]
                + self.decay * np.dot(self.norm_adj_mat, self.vectors["shadow_vector"]),
                0,
                1,
            )
            self.steps_weight["shadow_vector"] = -1

        if self.run_shadow and (self.ratio_filled < 0.01):
            if self.random_restart:
                idx = random.randint(0, self.N - 1)
                starting_vector = np.zeros(self.N)
                starting_vector[idx] = 0.3
            else:
                starting_vector = self.starting_vector
            self.setup(starting_vector)

    def combine(self, method="clip"):
        self.global_step()
        total_weight = sum(self.steps_weight.values())

        if method == "mean":
            state = (
                sum([self.steps_weight[step] * v for step, v in self.vectors.items()])
                / total_weight
            )

        elif method == "clip":
            state = np.clip(
                sum([self.steps_weight[step] * v for step, v in self.vectors.items()]),
                0,
                1,
            )

        self.state = state

    def set_color(self):
        self.combine()
        colors = self.max_intensity * self.state
        return colors


class Walker:
    """
    Simulates a random walker
    """

    def __init__(
        self,
        adj_mat,
        starting_idx=0,
        max_intensity=1023,
        trails=np.array([25, 40, 100]),
    ):

        self.starting_idx = starting_idx
        self.adj_mat = adj_mat

        self.max_intensity = max_intensity
        self.idx = len(trails) * [starting_idx]
        self.colored_trails = (self.max_intensity / trails[-1]) * trails

    def step(self):

        # Remove oldest trail
        del self.idx[0]

        current = self.idx[-1]
        choices = self.adj_mat[current, :]
        p = choices.copy()
        p[current] = 0
        p[self.idx[0]] = 0  # previous
        p = p / sum(p)
        picked = choice([i for i, _ in enumerate(choices)], p=p)
        self.idx = self.idx + [int(picked)]

        colors = np.zeros(N)  # 200 * self.adj_mat[picked]

        for idx, i in enumerate(self.idx):
            colors[i] = self.colored_trails[idx]
        self.colors = colors

        return self.colors

    def set_color(self):
        self.step()
        return self.colors


class MultiWalker:
    """
    Simulates multiples random walkers
    """

    def __init__(
        self,
        adj_mat,
        starting_idx=[0, 12],
        max_intensity=1023,
        trails=np.array([10, 40, 100]),
    ):

        self.max_intensity = max_intensity
        self.colored_trails = (self.max_intensity / trails[-1]) * trails
        self.walkers = [
            Walker(adj_mat, starting_idx=i, trails=trails) for i in starting_idx
        ]

    def set_color(self):
        colors = np.clip(sum([w.step() for w in self.walkers]), 0, self.max_intensity)
        return colors


class RandomFill:
    def __init__(
        self,
        max_intensity=1023,
    ):

        self.max_intensity = max_intensity
        self.idx = [7]
        self.all_ids = set(range(0, len(PWMS)))
        self.adding = True

    def forward_step(self):
        left_ids = list(self.all_ids - set(self.idx))
        added_idx = left_ids[random.randint(0, len(left_ids) - 1)]
        self.idx = list(set(self.idx) | set([added_idx]))
        if len(self.idx) == 13:
            self.adding = False

    def backward_step(self):
        self.idx.pop(random.randint(0, len(self.idx) - 1))
        if len(self.idx) == 1:
            self.adding = True

    def set_color(self):
        self.forward_step() if self.adding else self.backward_step()
        colors = len(PWMS) * [0]
        for i in self.idx:
            colors[i] = self.max_intensity
        return colors


class Flash:
    def __init__(
        self,
        max_intensity=1023,
        duration=1,
        pause_between=1,
    ):
        self.duration = duration
        self.max_intensity = max_intensity
        self.n_steps = 100
        self.steps = 0
        self.adding = True

    def set_all(self, intensity):
        return [int(intensity) for _ in PWMS]

    def ramp_up(self):
        intensity = self.max_intensity * (self.steps / self.n_steps)
        if self.steps == self.n_steps:
            self.adding = False
            return self.set_all(intensity)
        self.steps = self.steps + 1
        return self.set_all(intensity)

    def ramp_down(self):
        intensity = self.max_intensity * (self.steps / self.n_steps)
        if self.steps == 0:
            self.adding = True
            return self.set_all(intensity)
        self.steps = self.steps - 1
        return self.set_all(intensity)

    def set_color(self):
        return self.ramp_up() if self.adding else self.ramp_down()


COORDS = [
    (0, 1),
    (1, 0),
    (1, 1),
    (1, 2),
    (2, 2),
    (2, 3),
    (3, 1),
    (3, 2),
    (4, 1),
    (4, 2),
    (4, 3),
    (5, 1),
    (5, 0),
]

N = len(COORDS)
ADJ_MAT, NORM_ADJ_MAT = get_adj(COORDS)


async def alveoles_propagate(**kwargs):

    duration_step = kwargs.get("duration_step", 0.01)
    max_intensity = kwargs.get("max_intensity", 1023)

    propagate = Propagate(
        NORM_ADJ_MAT,
        max_intensity=max_intensity,
    )

    while True:
        colors = propagate.set_color()
        for i, pin in enumerate(PWMS):
            pin.duty(int(colors[i]))
        await asyncio.sleep(float(duration_step))


async def alveoles_phasm(**kwargs):

    duration_step = kwargs.get("duration_step", 0.01)
    max_intensity = kwargs.get("max_intensity", 1023)

    propagate = Propagate(
        NORM_ADJ_MAT,
        max_intensity=max_intensity,
        random_restart=False,
    )

    while True:
        colors = propagate.set_color()
        for i, pin in enumerate(PWMS):
            pin.duty(int(colors[i]))
        await asyncio.sleep(float(duration_step))


async def alveoles_walker(**kwargs):

    duration_step = kwargs.get("duration_step", 0.1)
    max_intensity = kwargs.get("max_intensity", 1023)
    numbers = kwargs.get("numbers", 1)

    starting_idx = [random.randint(0, 13) for n in range(numbers)]

    propagate = MultiWalker(
        ADJ_MAT,
        starting_idx=starting_idx,
        max_intensity=max_intensity,
    )

    while True:
        colors = propagate.set_color()
        for i, pin in enumerate(PWMS):
            pin.duty(int(colors[i]))
        await asyncio.sleep(float(duration_step))


async def alveoles_random_fill(**kwargs):

    duration_step = kwargs.get("duration_step", 0.01)
    max_intensity = kwargs.get("max_intensity", 1023)

    propagate = RandomFill(
        max_intensity=max_intensity,
    )

    while True:
        colors = propagate.set_color()
        for i, pin in enumerate(PWMS):
            pin.duty(int(colors[i]))
        await asyncio.sleep(float(duration_step))


async def alveoles_flash(**kwargs):

    duration = kwargs.get("duration", 1)
    max_intensity = kwargs.get("max_intensity", 1023)
    pause_between = kwargs.get("pause_between", 0)

    propagate = Flash(
        max_intensity=max_intensity,
        duration=duration,
    )

    while True:
        colors = propagate.set_color()
        for i, pin in enumerate(PWMS):
            pin.duty(int(colors[i]))
        await asyncio.sleep(float(duration / propagate.n_steps))
        if propagate.steps == 0:
            for i, pin in enumerate(PWMS):
                pin.duty(0)
            await asyncio.sleep(float(pause_between))


async def program(program_name, **kwargs):
    if program_name == "alveoles_propagate":
        await alveoles_propagate(**kwargs)
    if program_name == "alveoles_walker":
        await alveoles_walker(**kwargs)
    if program_name == "alveoles_phasm":
        await alveoles_phasm(**kwargs)
    if program_name == "alveoles_random_fill":
        await alveoles_random_fill(**kwargs)
    if program_name == "alveoles_flash":
        await alveoles_flash(**kwargs)
