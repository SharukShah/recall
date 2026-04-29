# Python From Zero — Q&A for Recall

---

## Section 1: How Python Works

**Q: How does Python execute code?**
A: Python reads code top to bottom, line by line. You write instructions, Python reads them sequentially and executes them. There's no compiling or building step — just write and run.

**Q: How does Python define code blocks instead of using curly braces?**
A: Python uses indentation (spaces/tabs) instead of `{}` braces. Indentation is mandatory — it's how Python knows what belongs inside an if block, loop, function, etc.

**Q: Is Python case-sensitive?**
A: Yes. `Name` and `name` are two completely different variables in Python.

**Q: What are comments in Python and how do you write them?**
A: Comments are notes for the programmer that Python ignores. They start with `#`. Example: `# This is a comment`.

---

## Section 2: Variables & Data Types

**Q: What are the 4 basic data types in Python?**
A: `str` (text like `"hello"`), `int` (whole numbers like `42`), `float` (decimal numbers like `3.14`), and `bool` (True or False).

**Q: How do you create a variable in Python?**
A: Just assign a value with `=`. No special keyword needed. Python figures out the type automatically. Example: `name = "Sharuk"`, `age = 25`.

**Q: How do you check the type of a variable?**
A: Use `type()`. Example: `type(42)` returns `<class 'int'>`.

**Q: How does type conversion (casting) work in Python?**
A: Use the type name as a function: `int("42")` converts string to integer, `str(25)` converts integer to string, `float(10)` converts to `10.0`. Note: `int(9.99)` gives `9` — it chops off decimals, doesn't round.

**Q: What is `None` in Python?**
A: `None` is Python's null — it represents "no value" or "nothing." Its type is `NoneType`. Used as a placeholder when a variable exists but has no meaningful value yet.

**Q: How do you assign multiple variables in one line?**
A: Two ways: `x, y, z = 1, 2, 3` assigns different values, or `a = b = c = 0` assigns the same value to all three.

---

## Section 3: Operators

**Q: What is the difference between `/` and `//` in Python?**
A: `/` is true division and ALWAYS returns a float (e.g., `10 / 3 = 3.333`). `//` is floor division and chops off the decimal (e.g., `10 // 3 = 3`).

**Q: What does the modulo operator `%` do?**
A: It returns the remainder after division. Example: `10 % 3 = 1` because 10 divided by 3 is 3 remainder 1. Very useful for checking even/odd (`n % 2 == 0`).

**Q: What is the `**` operator in Python?**
A: It's the power/exponentiation operator. `2 ** 3 = 8` means 2 to the power of 3.

**Q: What are the three logical operators in Python?**
A: `and` (both must be True), `or` (at least one must be True), `not` (flips True to False and vice versa). Example: `age >= 18 and has_license`.

**Q: What is the difference between `==` and `is` in Python?**
A: `==` checks if values are equal. `is` checks if two variables point to the same object in memory. Rule: use `==` for value comparison, use `is` only with `None` (e.g., `if x is None`).

**Q: What are membership operators in Python?**
A: `in` checks if something exists in a collection. `not in` checks if it doesn't. Examples: `"apple" in fruits` returns True if "apple" is in the list. Works with lists, strings, dicts, sets.

---

## Section 4: Strings

**Q: Are strings mutable or immutable in Python?**
A: Strings are immutable — you cannot change a character in place. `s[0] = "h"` will crash with TypeError. You must create a new string instead.

**Q: How do you reverse a string in Python?**
A: Use slicing: `s[::-1]`. Example: `"Python"[::-1]` gives `"nohtyP"`.

**Q: Explain string slicing syntax in Python.**
A: `string[start:end:step]`. Start is included, end is excluded. `word[0:3]` gets characters at index 0, 1, 2. Omitting start means from beginning, omitting end means to end. Step of -1 reverses the string.

**Q: What are the 10 most important string methods to know?**
A: `.upper()` (all caps), `.lower()` (all lowercase), `.strip()` (remove edge whitespace), `.split()` (string to list), `" ".join(list)` (list to string), `.replace(old, new)`, `.find(sub)` (returns index or -1), `.count(sub)`, `.startswith(prefix)`, `.isdigit()` (all digits?).

**Q: What is the difference between `.split()` and `.join()`?**
A: `.split()` breaks a string into a list: `"a b c".split()` → `["a", "b", "c"]`. `.join()` combines a list into a string: `" ".join(["a", "b", "c"])` → `"a b c"`. They are opposites.

**Q: How do you check if a substring exists in a string?**
A: Use the `in` operator: `"@" in "sharuk@gmail.com"` returns `True`.

**Q: What does negative indexing do in Python strings?**
A: It counts from the right. `-1` is the last character, `-2` is second to last, etc. Example: `"Python"[-1]` gives `"n"`.

---

## Section 5: Input & Output

**Q: What does `input()` always return in Python?**
A: `input()` ALWAYS returns a string, even if the user types a number. You must explicitly convert: `age = int(input("Enter age: "))`.

**Q: What are f-strings in Python?**
A: F-strings (formatted string literals) let you embed expressions inside strings with `f"..."` and `{variable}`. Example: `f"Hello, {name}! Age: {age}"`. You can put any expression inside `{}`.

**Q: How do you control the separator and end character in `print()`?**
A: Use `sep` for separator between items: `print("A", "B", sep="-")` → `"A-B"`. Use `end` to change the line ending: `print("Hello", end=" ")` prevents newline.

---

## Section 6: Conditionals

**Q: How does if/elif/else work in Python?**
A: Python checks conditions top to bottom. The first True condition's block runs, and the rest are skipped. `elif` means "else if." The `else` block runs only if no condition was True. Each block must be indented and preceded by a colon.

**Q: What is the ternary operator in Python?**
A: `value_if_true if condition else value_if_false`. Example: `status = "adult" if age >= 18 else "minor"`. It's a one-line if-else.

**Q: What values are falsy in Python?**
A: `False`, `0`, `0.0`, `""` (empty string), `[]` (empty list), `{}` (empty dict), `set()`, and `None`. Everything else is truthy. This means `if my_list:` checks if the list is non-empty.

**Q: What does `pass` do in Python?**
A: `pass` is a no-op — it does nothing. It's used as a placeholder where Python expects code but you haven't written any yet. Example: empty function body, empty class, or empty if block.

---

## Section 7: Loops

**Q: What is the difference between `for` and `while` loops?**
A: Use `for` when you know how many times to repeat (iterating over a sequence). Use `while` when you don't know — it keeps running while a condition is True. Always ensure a `while` loop's condition eventually becomes False to avoid infinite loops.

**Q: How does `range()` work?**
A: `range(stop)` → 0 to stop-1. `range(start, stop)` → start to stop-1. `range(start, stop, step)` → with custom step. Example: `range(0, 10, 2)` gives 0, 2, 4, 6, 8. `range(5, 0, -1)` counts down: 5, 4, 3, 2, 1.

**Q: What is the difference between `break` and `continue`?**
A: `break` exits the entire loop immediately. `continue` skips the current iteration and goes to the next one. Example: in a loop 0-9, `break` at 5 prints 0-4 then stops. `continue` at 2 prints 0, 1, 3, 4.

**Q: What does `enumerate()` do?**
A: It gives you both the index and the value when looping. `for i, fruit in enumerate(["apple", "banana"])` gives `(0, "apple")`, `(1, "banana")`. Preferred over `range(len(list))`.

**Q: How do you loop through a dictionary?**
A: `for key in dict:` loops through keys. `for value in dict.values():` loops through values. `for key, value in dict.items():` loops through both. The `.items()` method is preferred.

---

## Section 8: Lists

**Q: What is a list in Python?**
A: An ordered, mutable collection that allows duplicates. Created with `[]`. Can hold mixed types. Elements are accessed by index starting at 0.

**Q: What is the difference between `append()` and `extend()`?**
A: `append()` adds ONE item to the end — even a list becomes a single nested item: `[1,2].append([3,4])` → `[1, 2, [3, 4]]`. `extend()` adds EACH item individually: `[1,2].extend([3,4])` → `[1, 2, 3, 4]`.

**Q: How do you remove elements from a list?**
A: `.remove(value)` removes the first occurrence by value. `.pop()` removes and returns the last item (or `.pop(index)` for a specific index). `del list[index]` deletes by index without returning. `.clear()` removes all items.

**Q: How do you sort a list with a custom key?**
A: Use the `key` parameter: `words.sort(key=len)` sorts by length. `students.sort(key=lambda x: x[1])` sorts tuples by second element. `sorted()` returns a new list; `.sort()` modifies in place.

**Q: What is the difference between shallow copy and deep copy?**
A: Shallow copy (`.copy()`, `list[:]`, `list()`) copies the outer list but inner objects are shared — changing a nested list in the copy affects the original. Deep copy (`copy.deepcopy()`) recursively copies everything — fully independent. Rule: use `.copy()` for flat lists, `deepcopy()` for nested structures.

**Q: How do you unpack a list in Python?**
A: Assign to multiple variables: `x, y, z = [10, 20, 30]`. Use `*` to catch remaining: `first, *rest = [1, 2, 3, 4, 5]` gives `first=1`, `rest=[2, 3, 4, 5]`.

**Q: What does `zip()` do?**
A: It pairs up elements from two or more iterables: `zip(["Alice", "Bob"], [25, 30])` gives `("Alice", 25), ("Bob", 30)`. Commonly used with `for name, age in zip(names, ages)`.

---

## Section 9: Tuples

**Q: What is a tuple and how is it different from a list?**
A: A tuple is an ordered, IMMUTABLE collection. Created with `()`. You cannot add, remove, or change elements after creation. Tuples are faster than lists and can be used as dictionary keys. Use tuples for data that shouldn't change (coordinates, RGB colors, database rows).

**Q: How do you create a single-element tuple?**
A: You must include a trailing comma: `single = (42,)`. Without the comma, `(42)` is just the integer 42 in parentheses, not a tuple.

**Q: How does tuple unpacking work for swapping variables?**
A: `a, b = b, a` — Python's elegant swap. It creates a temporary tuple `(b, a)` and unpacks it into `a` and `b`. No temporary variable needed.

---

## Section 10: Sets

**Q: What is a set in Python?**
A: An unordered collection with NO duplicates. Created with `{}` (but `{}` alone creates an empty dict — use `set()` for empty set). Useful for removing duplicates and fast membership testing (O(1)).

**Q: What are the four main set operations?**
A: Union `a | b` (everything from both), Intersection `a & b` (common elements), Difference `a - b` (in a but not b), Symmetric Difference `a ^ b` (in one but not both).

**Q: How do you remove duplicates from a list?**
A: `unique = list(set(my_list))`. Note: this doesn't preserve order. To preserve order: iterate with a seen-set and append only unseen items.

**Q: What is the difference between `.remove()` and `.discard()` for sets?**
A: `.remove(x)` raises a KeyError if x is not found. `.discard(x)` does nothing if x is not found — it's the safe version.

---

## Section 11: Dictionaries

**Q: What is a dictionary in Python?**
A: A collection of key-value pairs. Keys must be unique and immutable (strings, numbers, tuples). Values can be any type. Created with `{}` or `dict()`. Access by key: `d["key"]`.

**Q: What is the difference between `d["key"]` and `d.get("key")`?**
A: `d["key"]` raises a KeyError if the key doesn't exist. `d.get("key")` returns `None` (or a specified default) if the key doesn't exist. Always use `.get()` for safe access: `d.get("salary", 0)`.

**Q: How do you count character frequency in a string using a dictionary?**
A: Use `.get()` with a default of 0: `freq = {}; for char in text: freq[char] = freq.get(char, 0) + 1`. Or use `collections.Counter("hello")` for a one-liner.

**Q: How do you merge two dictionaries?**
A: Use unpacking: `merged = {**dict1, **dict2}` (dict2 values overwrite dict1 for duplicate keys). Or use `dict1.update(dict2)` to modify dict1 in place.

**Q: What is a dictionary comprehension?**
A: One-liner dict creation: `{x: x**2 for x in range(5)}` creates `{0: 0, 1: 1, 2: 4, 3: 9, 4: 16}`.

---

## Section 12: Functions

**Q: What is the difference between a parameter and an argument?**
A: A parameter is the placeholder in the function definition (`def greet(name)` — `name` is the parameter). An argument is the actual value passed when calling (`greet("Sharuk")` — `"Sharuk"` is the argument).

**Q: What does a Python function return if there's no return statement?**
A: It returns `None`.

**Q: How do you return multiple values from a function?**
A: Return them as a tuple: `return min(nums), max(nums)`. Unpack with `smallest, largest = min_max([3, 1, 4])`.

**Q: What is variable scope in Python?**
A: Variables defined outside functions are global (accessible everywhere). Variables inside functions are local (only accessible inside that function). Use `global` keyword to modify a global variable inside a function. Use `nonlocal` to modify a variable from an enclosing (outer) function.

**Q: What is the mutable default argument trap?**
A: Using a mutable object (list, dict) as a default parameter creates it ONCE and reuses it across all calls. `def f(lst=[])` — the list is shared! Fix: use `def f(lst=None): if lst is None: lst = []`.

**Q: How does recursion work?**
A: A function calls itself with a smaller input until reaching a base case. Example: `factorial(5) = 5 * factorial(4) = 5 * 4 * factorial(3)...` until `factorial(1) = 1`. Always needs a base case to stop.

**Q: What are keyword arguments?**
A: Arguments passed by name: `create_profile(age=25, name="Sharuk")`. They can be passed in any order, unlike positional arguments.

---

## Section 13: List Comprehensions

**Q: What is a list comprehension?**
A: A one-liner way to create lists. Syntax: `[expression for item in iterable if condition]`. Example: `[x**2 for x in range(5)]` gives `[0, 1, 4, 9, 16]`. With filter: `[x for x in range(10) if x % 2 == 0]` gives even numbers.

**Q: How do you add an if-else in a list comprehension?**
A: Put the if-else BEFORE the for: `["even" if x % 2 == 0 else "odd" for x in range(5)]`. Note: if-else goes before `for`, but filter-only `if` goes after.

**Q: How do you flatten a 2D list with list comprehension?**
A: `flat = [num for row in matrix for num in row]`. Read it like nested loops: outer loop first, then inner loop.

---

## Section 14: Lambda, Map, Filter, Reduce

**Q: What is a lambda function?**
A: An anonymous (unnamed) one-line function. Syntax: `lambda parameters: expression`. Example: `square = lambda x: x**2`. Use when you need a short function once, especially with `sorted()`, `map()`, `filter()`.

**Q: What do `map()` and `filter()` do?**
A: `map(func, iterable)` applies a function to every item: `list(map(lambda x: x**2, [1,2,3]))` → `[1, 4, 9]`. `filter(func, iterable)` keeps only items where the function returns True: `list(filter(lambda x: x % 2 == 0, [1,2,3,4]))` → `[2, 4]`. List comprehensions are generally preferred.

**Q: What does `reduce()` do?**
A: It combines all items into a single value by applying a function cumulatively. `reduce(lambda a, b: a + b, [1,2,3,4,5])` → `15`. Must import from `functools`. Usually `sum()`, `max()`, etc. are preferred.

---

## Section 15: Error Handling

**Q: How does try/except/else/finally work?**
A: `try` block runs the risky code. `except` catches specific errors if they occur. `else` runs ONLY if no error occurred. `finally` runs NO MATTER WHAT (error or not). Example: closing a resource in `finally`.

**Q: How do you catch any exception and get the error message?**
A: `except Exception as e: print(f"Error: {e}")`. This catches any exception and stores the message in variable `e`.

**Q: How do you raise your own errors?**
A: Use `raise`: `raise ValueError("Age cannot be negative!")`. This creates and throws an exception that callers must handle.

**Q: Name 5 common Python exceptions.**
A: `ValueError` (wrong value: `int("hello")`), `TypeError` (wrong type: `"hi" + 5`), `KeyError` (dict key not found), `IndexError` (list index out of range), `AttributeError` (object has no attribute).

---

## Section 16: File Handling

**Q: How do you read and write files in Python?**
A: Use `with open(filename, mode) as f:`. Modes: `"r"` (read), `"w"` (write/overwrite), `"a"` (append). Read: `f.read()` for entire content, `f.readlines()` for list of lines, or `for line in f:` to iterate. Write: `f.write("text")`.

**Q: Why should you use `with` when opening files?**
A: `with` automatically closes the file when the block ends, even if an error occurs. Without `with`, you must manually call `f.close()`. It's cleaner and safer.

---

## Section 17: Object-Oriented Programming

**Q: What is a class in Python?**
A: A class is a blueprint for creating objects. It bundles data (attributes) and behavior (methods) together. Created with `class MyClass:`. Objects are instances of a class.

**Q: What is `self` in Python?**
A: `self` is a reference to the current instance of the class (like `this` in Java/C#). It's the first parameter of every instance method. Used to access instance attributes: `self.name = name`.

**Q: What is `__init__`?**
A: It's the constructor — a special method that runs automatically when a new object is created. Used to initialize instance attributes: `def __init__(self, name): self.name = name`.

**Q: What are the 4 pillars of OOP?**
A: 1) Encapsulation — bundling data and methods, hiding internals. 2) Abstraction — showing only essential details. 3) Inheritance — child class inherits from parent class. 4) Polymorphism — same method name, different behavior in different classes.

**Q: How does inheritance work in Python?**
A: A child class inherits all attributes and methods from a parent: `class Cat(Animal):`. The child can override methods to change behavior. Use `super().__init__()` to call the parent's constructor.

**Q: What is the difference between class variables and instance variables?**
A: Class variables are shared by ALL instances (defined outside `__init__`). Instance variables are unique to each object (defined with `self.` inside `__init__`).

**Q: What are `@staticmethod` and `@classmethod`?**
A: `@staticmethod` — a method that doesn't need `self` or `cls`; behaves like a regular function inside the class. `@classmethod` — receives the class itself as `cls`; useful for factory methods.

**Q: What is encapsulation and how do you make attributes private?**
A: Encapsulation means hiding internal details. Prefix with `__` (double underscore) for name mangling/private: `self.__balance`. Access through getter/setter methods. Convention: `_` prefix means "private-ish, don't touch."

**Q: What is `@property` in Python?**
A: A Pythonic way to create getters and setters. Use `@property` for the getter and `@name.setter` for the setter. Allows accessing methods like attributes with validation: `c.radius = 10` calls the setter.

**Q: What are abstract classes in Python?**
A: Classes that cannot be instantiated directly; they force subclasses to implement certain methods. Use `from abc import ABC, abstractmethod`. Decorate methods with `@abstractmethod`. Any subclass MUST implement all abstract methods.

**Q: What are dunder (magic) methods?**
A: Double underscore methods like `__init__`, `__str__`, `__repr__`, `__eq__`, `__add__`, `__len__`. They customize how your class works with built-in operations: `__str__` for `print()`, `__eq__` for `==`, `__add__` for `+`, `__len__` for `len()`.

---

## Section 18: Modules & Imports

**Q: What are the different ways to import modules in Python?**
A: `import math` (full module), `from math import sqrt, pi` (specific items), `import math as m` (alias), `from math import *` (everything — not recommended). Prefer specific imports for clarity.

**Q: What does `if __name__ == "__main__":` do?**
A: When you run a file directly, `__name__` is set to `"__main__"`. When you import it, `__name__` is set to the module name. This guard ensures code only runs when the file is executed directly, not when imported.

**Q: Name 5 useful modules from Python's standard library.**
A: `collections` (Counter, defaultdict, deque), `itertools` (permutations, combinations), `heapq` (min-heap/priority queue), `json` (JSON serialization), `datetime` (date/time handling).

**Q: What is `collections.Counter`?**
A: A dict subclass for counting. `Counter("hello")` gives `{'l': 2, 'h': 1, 'e': 1, 'o': 1}`. `.most_common(n)` returns the n most frequent items.

**Q: What is `collections.defaultdict`?**
A: A dict that provides a default value for missing keys. `defaultdict(int)` defaults to 0, `defaultdict(list)` defaults to empty list. No more KeyError when accessing missing keys.

**Q: What is `heapq` and when do you use it?**
A: A min-heap (priority queue) module. `heapq.heapify(list)` converts to heap. `heappush()`/`heappop()` add/remove. `nlargest(k, list)` and `nsmallest(k, list)` get top/bottom k elements. Use for "find K largest/smallest" problems.

**Q: What is a virtual environment and why use one?**
A: An isolated Python environment for project-specific packages. Create: `python -m venv myenv`. Each project can have different package versions without conflicts. Use `pip freeze > requirements.txt` to save and `pip install -r requirements.txt` to restore.

---

## Section 19: Built-in Functions

**Q: What do `all()` and `any()` do?**
A: `all(iterable)` returns True if ALL elements are truthy. `any(iterable)` returns True if at LEAST ONE element is truthy. Example: `all([True, True, False])` → False. `any([False, False, True])` → True.

**Q: What does `isinstance()` do?**
A: Checks if an object is an instance of a type: `isinstance(42, int)` → True. Can check multiple types: `isinstance(42, (int, float))` → True. Preferred over `type(x) == int`.

**Q: What do `ord()` and `chr()` do?**
A: `ord('A')` → 65 (character to ASCII number). `chr(65)` → 'A' (ASCII number to character). Useful for character arithmetic in interview problems.

**Q: What does `divmod()` return?**
A: A tuple of (quotient, remainder): `divmod(10, 3)` → `(3, 1)`. Equivalent to `(10 // 3, 10 % 3)`.

---

## Section 20: String Formatting (f-strings)

**Q: How do you format numbers with f-strings?**
A: Decimal places: `f"{pi:.2f}"` → `"3.14"`. Comma separators: `f"{1000000:,}"` → `"1,000,000"`. Alignment: `f"{'text':<10}"` (left), `f"{'text':>10}"` (right), `f"{'text':^10}"` (center).

**Q: What are the three string formatting methods in Python?**
A: 1) f-strings (modern, preferred): `f"Hello {name}"`. 2) `.format()`: `"Hello {}".format(name)`. 3) `%` formatting (old): `"Hello %s" % name`. Always use f-strings in modern Python.

---

## Section 21: Iterators & Generators

**Q: What is an iterator in Python?**
A: An object that produces values one at a time using `next()`. Every `for` loop uses an iterator internally. Create with `iter(iterable)`. When exhausted, raises `StopIteration`.

**Q: What is a generator and how is it different from a regular function?**
A: A generator is a function that uses `yield` instead of `return`. It produces values one at a time (lazily), pausing between each yield. It doesn't store all values in memory at once — perfect for huge datasets. Example: `def count(n): i=0; while i<n: yield i; i+=1`.

**Q: What is a generator expression?**
A: A one-liner generator using parentheses instead of brackets: `(x**2 for x in range(1000000))`. Uses almost no memory compared to `[x**2 for x in range(1000000)]` which stores everything.

---

## Section 22: Closures

**Q: What is a closure in Python?**
A: A closure is a nested function that remembers variables from its enclosing scope even after that scope has finished executing. Three requirements: 1) nested function, 2) inner function uses outer function's variable, 3) outer function returns inner function. Example: `make_multiplier(2)` returns a function that always multiplies by 2.

**Q: Why are closures important?**
A: Closures are the foundation of decorators. They enable data hiding (the enclosed variable can't be accessed directly) and creating function factories (functions that create customized functions).

---

## Section 23: Decorators

**Q: What is a decorator in Python?**
A: A function that wraps another function to add extra behavior without changing the original function. Applied with `@decorator_name` above the function definition. Uses closures internally — the wrapper function remembers the original function.

**Q: How do you write a decorator that works with any function arguments?**
A: Use `*args` and `**kwargs` in the wrapper: `def wrapper(*args, **kwargs): result = func(*args, **kwargs); return result`. This forwards any arguments to the original function.

**Q: Give a practical example of a decorator.**
A: A timer decorator: wraps a function to measure execution time. Records `time.time()` before and after calling the function, prints the difference. Applied with `@timer` above any function you want to time.

---

## Section 24: *args and **kwargs

**Q: What are `*args` and `**kwargs`?**
A: `*args` collects extra positional arguments into a tuple: `def f(*args)` — `f(1,2,3)` gives `args = (1, 2, 3)`. `**kwargs` collects extra keyword arguments into a dict: `def f(**kwargs)` — `f(name="Sharuk")` gives `kwargs = {"name": "Sharuk"}`.

**Q: What is the required order of parameters in a function?**
A: Regular parameters first, then `*args`, then `**kwargs`: `def func(a, b, *args, **kwargs)`.

**Q: How do you unpack a list or dict into function arguments?**
A: Use `*` to unpack a list: `func(*[1, 2, 3])` is like `func(1, 2, 3)`. Use `**` to unpack a dict: `func(**{"a": 1, "b": 2})` is like `func(a=1, b=2)`.

---

## Section 25: Stack & Queue

**Q: What is a stack and how do you implement one in Python?**
A: Stack is Last In, First Out (LIFO) — like a stack of plates. Use a list: `stack.append(item)` to push, `stack.pop()` to pop, `stack[-1]` to peek. Check empty with `if not stack`.

**Q: What is a queue and how do you implement one in Python?**
A: Queue is First In, First Out (FIFO) — like a line at a store. Use `collections.deque`: `queue.append(item)` to enqueue, `queue.popleft()` to dequeue. DON'T use `list.pop(0)` — it's O(n). `deque.popleft()` is O(1).

**Q: Solve the Valid Parentheses problem using a stack.**
A: Use a stack: push opening brackets, for closing brackets check if stack top matches. Map closing to opening: `{')':'(', '}':'{', ']':'['}`. For each char: if opening, push; if closing, check stack top matches, else return False. At end, stack must be empty.

---

## Section 26: Type Hints

**Q: What are type hints in Python?**
A: Annotations showing expected types. They don't enforce types at runtime but improve documentation, IDE support, and allow static analysis with tools like `mypy`. Syntax: `def add(a: int, b: int) -> int:`.

**Q: What is `Optional` in type hints?**
A: `Optional[str]` means the value can be `str` or `None`. Equivalent to `str | None` in Python 3.10+. Use when a function might return None.

**Q: Why use type hints?**
A: 1) Self-documenting code, 2) Better IDE autocomplete, 3) Static type checking with mypy catches bugs before runtime, 4) Shows interviewers you write professional Python.

---

## Section 27: Big O Cheat Sheet

**Q: What is the time complexity for searching in a list vs dict vs set?**
A: List: O(n) — must check each element. Dict: O(1) — hash table lookup. Set: O(1) — hash table lookup. Rule: if you need fast lookups, use dict or set.

**Q: What is the time complexity of common list operations?**
A: Access by index: O(1). Insert at end (append): O(1). Insert at beginning: O(n) — must shift all elements. Delete by value: O(n). Search: O(n). Sort: O(n log n).

**Q: When should you use a set vs a list vs a dict?**
A: Need fast lookup? → set or dict (O(1)). Need order? → list. Need unique items? → set. Need key-value pairs? → dict. Need to allow duplicates? → list.

---

## Section 28: Must-Solve Problems

**Q: How do you solve Two Sum (find two numbers that add up to target)?**
A: Use a dictionary to store seen values: for each number, compute complement (target - num). If complement is in the dict, return both indices. Otherwise, store current number and index. Time: O(n), Space: O(n).

**Q: How do you check if a string is a palindrome?**
A: Normalize (lowercase, remove spaces): `s = s.lower().replace(" ", "")`. Then check: `return s == s[::-1]`.

**Q: How do you check if two strings are anagrams?**
A: Sort both and compare: `sorted(s1.lower()) == sorted(s2.lower())`. Or use Counter: `Counter(s1.lower()) == Counter(s2.lower())`.

**Q: Write FizzBuzz.**
A: Loop 1 to n. If divisible by both 3 and 5, print "FizzBuzz". Elif divisible by 3, print "Fizz". Elif divisible by 5, print "Buzz". Else print the number. Check "both" first to avoid wrong output.

**Q: How do you compute Fibonacci iteratively?**
A: Use two variables: `a, b = 0, 1`. Loop n-1 times: `a, b = b, a + b`. Return `b`. Time: O(n), Space: O(1). Much better than recursive O(2^n).

**Q: How do you check if a number is prime?**
A: If n < 2, return False. Check divisors from 2 to sqrt(n): `for i in range(2, int(n**0.5) + 1)`. If any divides evenly, not prime. Only need to check up to sqrt(n) because factors come in pairs.

**Q: How do you remove duplicates from a list while preserving order?**
A: Use a set to track seen items: `seen = set(); result = []; for item in lst: if item not in seen: seen.add(item); result.append(item)`. Time: O(n).

---

## Section 29: Quick-Fire Interview Questions

**Q: Is Python compiled or interpreted?**
A: Interpreted (technically compiled to bytecode first, then interpreted by the Python Virtual Machine).

**Q: What is PEP 8?**
A: Python's official style guide — rules for writing clean, readable Python code (naming conventions, indentation, line length, etc.).

**Q: Which Python types are mutable and which are immutable?**
A: Mutable: list, dict, set. Immutable: int, str, tuple, frozenset, bool. Immutable objects cannot be changed after creation.

**Q: What is the Global Interpreter Lock (GIL)?**
A: A mutex in CPython that allows only one thread to execute Python bytecode at a time. This means Python threads don't achieve true parallelism for CPU-bound tasks. Use `multiprocessing` for CPU-bound parallelism.

**Q: What is the difference between `append()` vs `extend()` for lists?**
A: `append` adds one item (even a list as a single nested item). `extend` iterates and adds each item individually. `[1,2].append([3,4])` → `[1,2,[3,4]]`. `[1,2].extend([3,4])` → `[1,2,3,4]`.

**Q: What is `nonlocal` in Python?**
A: A keyword that allows modifying a variable from an enclosing (outer) function's scope — not the global scope. Used in closures and nested functions.

**Q: How do you sort by a custom key in Python?**
A: `sorted(items, key=lambda x: x[1])` sorts by the second element. The `key` function extracts the comparison value from each item.
