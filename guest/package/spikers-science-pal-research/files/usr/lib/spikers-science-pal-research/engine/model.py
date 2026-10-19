"""Small ridge model, leave-one-out score, and one equal-width interval."""

import math


def _solve(matrix, target):
    size = len(target)
    table = [row[:] + [target[index]] for index, row in enumerate(matrix)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(table[row][col]))
        table[col], table[pivot] = table[pivot], table[col]
        if abs(table[col][col]) < 1e-12:
            return [0.0] * size
        scale = table[col][col]
        for cell in range(col, size + 1):
            table[col][cell] /= scale
        for row in range(size):
            if row == col:
                continue
            factor = table[row][col]
            for cell in range(col, size + 1):
                table[row][cell] -= factor * table[col][cell]
    return [table[index][-1] for index in range(size)]


def _standardize(rows):
    width = len(rows[0])
    means = [sum(row[col] for row in rows) / len(rows) for col in range(width)]
    scales = []
    for col in range(width):
        variance = sum((row[col] - means[col]) ** 2 for row in rows) / len(rows)
        scales.append(math.sqrt(variance) or 1.0)
    return means, scales


def _design(row, means, scales):
    return [(row[index] - means[index]) / scales[index] for index in range(len(means))] + [1.0]


def fit(rows, target, lam=1.0):
    means, scales = _standardize(rows)
    width = len(rows[0]) + 1
    gram = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    for row, value in zip(rows, target):
        design = _design(row, means, scales)
        for left in range(width):
            rhs[left] += design[left] * value
            for right in range(width):
                gram[left][right] += design[left] * design[right]
    for index in range(width - 1):
        gram[index][index] += lam
    return _solve(gram, rhs), means, scales


def predict(model, row):
    weights, means, scales = model
    design = _design(row, means, scales)
    return sum(weight * value for weight, value in zip(weights, design))


def r2(target, predicted):
    mean = sum(target) / len(target)
    total = sum((value - mean) ** 2 for value in target) or 1e-9
    residual = sum((left - right) ** 2 for left, right in zip(target, predicted))
    return 1 - residual / total


def loocv(rows, target, lam=1.0):
    predicted = []
    for index in range(len(rows)):
        train_rows = rows[:index] + rows[index + 1:]
        train_target = target[:index] + target[index + 1:]
        model = fit(train_rows, train_target, lam)
        predicted.append(predict(model, rows[index]))
    return predicted, r2(target, predicted)


def equal_width(residuals):
    """Half-width shared by every row. The midpoint ranking matches the point prediction."""
    ordered = sorted(abs(value) for value in residuals)
    if not ordered:
        return 0.0
    quantile = ordered[min(len(ordered) - 1, int(0.9 * (len(ordered) - 1)))]
    return quantile
