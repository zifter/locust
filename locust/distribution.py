import math
from operator import attrgetter
from typing import (
    Dict,
    List,
    Type,
)

from locust import User


def weight_users(
    user_classes: List[Type[User]],
    number_of_users: int,
) -> Dict[str, int]:
    """
    Compute users to spawn

    :param user_classes: the list of user class
    :param number_of_users: total number of users
    :return: the new set of users to run
    """
    assert number_of_users >= 0

    if len(user_classes) == 0:
        return {}

    user_classes = sorted(user_classes, key=lambda u: u.__name__)

    user_class_occurrences = {user_class.__name__: 0 for user_class in user_classes}

    if number_of_users <= len(user_classes):
        user_class_occurrences.update(
            {
                user_class.__name__: 1
                for user_class in sorted(
                    user_classes,
                    key=lambda user_class: user_class.weight,
                    reverse=True,
                )[:number_of_users]
            }
        )
        return user_class_occurrences

    weights = list(map(attrgetter("weight"), user_classes))
    user_class_occurrences = {
        user_class.__name__: round(relative_weight * number_of_users) or 1
        for user_class, relative_weight in zip(user_classes, (weight / sum(weights) for weight in weights))
    }

    if sum(user_class_occurrences.values()) == number_of_users:
        return user_class_occurrences

    elif sum(user_class_occurrences.values()) > number_of_users:
        user_class_occurrences_candidates: Dict[float, Dict[str, int]] = {}
        _recursive_remove_users(
            user_classes,
            number_of_users,
            user_class_occurrences.copy(),
            user_class_occurrences_candidates,
        )
        return user_class_occurrences_candidates[min(user_class_occurrences_candidates.keys())]

    elif sum(user_class_occurrences.values()) < number_of_users:
        user_class_occurrences_candidates: Dict[float, Dict[str, int]] = {}
        _recursive_add_users(
            user_classes,
            number_of_users,
            user_class_occurrences.copy(),
            user_class_occurrences_candidates,
        )
        return user_class_occurrences_candidates[min(user_class_occurrences_candidates.keys())]


def _recursive_add_users(
    user_classes: List[Type[User]],
    number_of_users: int,
    user_class_occurrences_candidate: Dict[str, int],
    user_class_occurrences_candidates: Dict[float, Dict[str, int]],
):
    if sum(user_class_occurrences_candidate.values()) == number_of_users:
        distance = distance_from_desired_distribution(
            user_classes,
            user_class_occurrences_candidate,
        )
        if distance not in user_class_occurrences_candidates:
            user_class_occurrences_candidates[distance] = user_class_occurrences_candidate
        return
    elif sum(user_class_occurrences_candidate.values()) > number_of_users:
        return

    for user_class in user_classes:
        user_class_occurrences_candidate_ = user_class_occurrences_candidate.copy()
        user_class_occurrences_candidate_[user_class.__name__] += 1
        _recursive_add_users(
            user_classes,
            number_of_users,
            user_class_occurrences_candidate_,
            user_class_occurrences_candidates,
        )


def _recursive_remove_users(
    user_classes: List[Type[User]],
    number_of_users: int,
    user_class_occurrences_candidate: Dict[str, int],
    user_class_occurrences_candidates: Dict[float, Dict[str, int]],
):
    if sum(user_class_occurrences_candidate.values()) == number_of_users:
        distance = distance_from_desired_distribution(
            user_classes,
            user_class_occurrences_candidate,
        )
        if distance not in user_class_occurrences_candidates:
            user_class_occurrences_candidates[distance] = user_class_occurrences_candidate
        return
    elif sum(user_class_occurrences_candidate.values()) < number_of_users:
        return

    for user_class in sorted(user_classes, key=lambda u: u.__name__, reverse=True):
        if user_class_occurrences_candidate[user_class.__name__] == 1:
            continue
        user_class_occurrences_candidate_ = user_class_occurrences_candidate.copy()
        user_class_occurrences_candidate_[user_class.__name__] -= 1
        _recursive_remove_users(
            user_classes,
            number_of_users,
            user_class_occurrences_candidate_,
            user_class_occurrences_candidates,
        )


def distance_from_desired_distribution(
    user_classes: List[Type[User]],
    user_class_occurrences: Dict[str, int],
) -> float:
    user_class_2_actual_percentage = {
        user_class: 100 * occurrences / sum(user_class_occurrences.values())
        for user_class, occurrences in user_class_occurrences.items()
    }

    user_class_2_expected_percentage = {
        user_class.__name__: 100 * user_class.weight / sum(map(attrgetter("weight"), user_classes))
        for user_class in user_classes
    }

    differences = [
        user_class_2_actual_percentage[user_class] - expected_percentage
        for user_class, expected_percentage in user_class_2_expected_percentage.items()
    ]

    return math.sqrt(math.fsum(map(lambda x: x ** 2, differences)))
