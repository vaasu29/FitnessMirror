"""
angle.py
Utility functions for computing joint angles from pose landmarks.
"""
import numpy as np


def calculate_angle(a, b, c):
    """
    Calculate the angle (in degrees) at point b, formed by points a-b-c.
    a, b, c: each a tuple/list of (x, y) coordinates (can also be (x, y, z)).
    """
    a = np.array(a[:2])
    b = np.array(b[:2])
    c = np.array(c[:2])

    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    angle = np.degrees(np.arccos(cosine_angle))

    return angle
