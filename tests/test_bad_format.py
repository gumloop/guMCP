"""This file has intentionally bad formatting that Black would flag."""

# Importing with wrong order and spacing
import sys, os
import json


# Extra whitespace and bad indentation
def very_poorly_formatted(a=1, b=2):
    return a + b


# Single quotes mixed with double quotes and bad spacing
data = {"a": 1, "b": 2, "c": 3}

# Long lines that exceed Black's default limit
very_long_string = "This is an extremely long string that definitely exceeds Black's default line length limit. It should be broken up into multiple lines."

# Bad list formatting
my_list = [1, 2,3,
]

# Inconsistent function calls
print("This is a test")
print("This is also a test")


# Mix of tabs and spaces
def mixed_indentation():
    # This line uses tabs
    # This line uses spaces
    return True
