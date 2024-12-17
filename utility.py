from random import choice
from copy import copy
from typing import Tuple, Callable


def successors_by_predecessors(predecessors: list[list[int]]):
    size = len(predecessors)
    return [[succ for succ in range(size) if i in predecessors[succ]] for i in range(size)]


def calculate_critical_times(
        duration: list[int],
        predecessors: list[list[int]],
        successors: list[list[int]] = None) -> Tuple[list[int], list[int]]:
    """Расчёт ранних времён начала и поздних времён завершения работ

    Args:
        duration (list[int]): _description_
        predecessors (list[list[int]]): списки предшествующих работ
        successors (list[list[int]]): списки последующих работ

    Raises:
        ValueError:

    Returns:
        Tuple[list[int], list[int]]: ранние времена начала и поздние времена завершения
    """
    if not successors:
        successors = successors_by_predecessors(predecessors)
    if len(duration) != len(predecessors) or len(predecessors) != len(successors):
        raise ValueError("Invalid data")
    earliest_start = [0 for _ in duration]
    latest_finish = [0 for _ in duration]

    def _calc_earliest_start(index):
        if index:
            earliest_start[index] = max(_calc_earliest_start(pred) + duration[pred] for pred in predecessors[index])
        return earliest_start[index]

    def _calc_latest_finish(index):
        if index == len(successors) - 1:
            latest_finish[index] = earliest_start[index]
        else:
            latest_finish[index] = min(_calc_latest_finish(succ) - duration[succ] for succ in successors[index])
        return latest_finish[index]

    _calc_earliest_start(len(predecessors) - 1)
    _calc_latest_finish(0)

    return earliest_start, latest_finish


class TimeCapacityNode:
    """
    Вспомогательная структура связного списка моментов времени и 
    имеющихся в них остаточных запасов ресурсов
    """

    def __init__(self, time: int, capacity: list[int]):
        self.time = time
        self.capacity = capacity
        self.next = None
        self.prev = None

    def insert_after(self, time: int) -> 'TimeCapacityNode':
        if time <= self.time:
            raise ValueError("Invalid time")

        new_node = self.__class__(time, copy(self.capacity))
        new_node.prev = self
        new_node.next = self.next
        if self.next:
            self.next.prev = new_node
        self.next = new_node
        return new_node

    def find_first(self, time: int) -> 'TimeCapacityNode':
        node = self
        while node.time < time:
            if node.next:
                node = node.next
            else:
                return node
        return node.prev

    def enough_resources(self, demand: list[int]) -> bool:
        return all(self.capacity[i] >= demand[i] for i in range(len(self.capacity)))

    def consume(self, demand: list[int]) -> None:
        for i in range(len(self.capacity)):
            self.capacity[i] -= demand[i]


class ActivityListDecoder:
    def decode(
            self,
            activity_list: list[int],
            duration: list[int],
            predecessors: list[list[int]],
            renewable_demands: list[list[int]],
            renewable_capacity: list[int]) -> list[int]:
        """
        Последовательная схема генерации расписания для декодирования Activity List.

        Args:
            activity_list (list[int]): закодированное решение (Activity List)
            duration (list[int]): продолжительности работ
            predecessors (list[list[int]]): списки предшествующих работ
            renewable_demands (list[list[int]]): затраты неисчерпаемых ресурсов
            renewable_capacity (list[int]): запасы неисчерпаемых ресурсов

        Raises:
            ValueError: выбрасывается при нарушении связей предшествования

        Returns:
            list[int]: времена начала работ
        """
        count = len(activity_list)
        root_node = TimeCapacityNode(0, copy(renewable_capacity))  # Связный список моментов изменения запаса ресурсов
        starts = [0] * count
        finish_nodes = [None] * count
        finish_nodes[0] = root_node

        for i in activity_list:
            # Работа может начаться не раньше, чем её последняя предшественница
            start_node = root_node
            for pred in predecessors[i]:
                if not finish_nodes[pred]:
                    raise ValueError("Invalid activity list")
                if finish_nodes[pred].time > start_node.time:
                    start_node = finish_nodes[pred]
            # Ищем такую позицию для начала, при которой не нарушатся ресурсные ограничения
            start_node, last_node, finish_node, finish_time = self._find_position(
                start_node, duration[i], renewable_demands[i]
            )
            starts[i] = start_node.time
            if not finish_node or finish_node.time != finish_time:
                finish_node = last_node.insert_after(finish_time)
            finish_nodes[i] = finish_node
            # Обновляем доступное число ресурсов в моменты времени, затрагиваемые данной работой
            self._consume(start_node, finish_node, renewable_demands[i])

        return starts

    def _consume(
            self, start_node: TimeCapacityNode,
            finish_node: TimeCapacityNode,
            demand: list[int]) -> None:
        node = start_node
        while node != finish_node:
            node.consume(demand)
            node = node.next

    def _find_position(
            self, start_node: int, duration: int, demand: list[int]
    ) -> Tuple[TimeCapacityNode, TimeCapacityNode, TimeCapacityNode, int]:
        if not duration:
            return (start_node, start_node, start_node, start_node.time)

        finish_time = start_node.time + duration
        t = start_node.find_first(finish_time)
        last_node = t
        t_test = start_node

        while t != t_test.prev:
            if t.enough_resources(demand):
                t = t.prev
            else:
                start_node = t.next
                finish_time = start_node.time + duration
                if last_node.next:
                    t_test = last_node.next
                    last_node = t_test.find_first(finish_time)
                    t = last_node
                else:
                    break

        return (start_node, last_node, last_node.next, finish_time)


class ActivityListSampler:
    def __init__(
            self,
            predecessors: list[list[int]],
            successors: list[list[int]] = None) -> None:
        """
        Args:
            predecessors (list[list[int]]): списки предшествующих работ
            successors (list[list[int]]): списки последующих работ
        """
        self.predecessors = predecessors
        self.size = len(predecessors)
        if not successors:
            successors = successors_by_predecessors(predecessors)
        self.successors = successors

    def _generate(self, func: Callable = None) -> list[int]:
        result = []
        ramain_predecessors = [set(pred) for pred in self.predecessors]
        ready_set = [i for i in range(self.size) if not self.predecessors[i]]

        for _ in range(self.size):
            if not ready_set:
                raise ValueError("Incorrect project network")

            next_activity = func(ready_set) if func else choice(ready_set)
            ready_set.remove(next_activity)
            result.append(next_activity)

            for successor in self.successors[next_activity]:
                ramain_predecessors[successor].remove(next_activity)
                if not ramain_predecessors[successor]:
                    ready_set.append(successor)

        return result

    def generate_random(self) -> list[int]:
        """
        Генерация Activity List случайным образом

        Returns:
            list[int]: Activity List
        """
        return self._generate()

    def generate_by_max_rule(self, rule: Callable) -> list[int]:
        """
        Генерация Activity List упорядочивая по убыванию метрики

        Returns:
            list[int]: Activity List
        """

        def func(data: list[int]):
            return max(data, key=rule)

        return self._generate(func)

    def generate_by_min_rule(self, rule: Callable) -> list[int]:
        """
        Генерация Activity List упорядочивая по возрастанию метрики

        Returns:
            list[int]: Activity List
        """

        def func(data: list[int]):
            return min(data, key=rule)

        return self._generate(func)
