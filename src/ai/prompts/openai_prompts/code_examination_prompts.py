CODE_SECURITY_EXAMINATION_TEMPLATE = """You are examining code specifically for security vulnerabilities.  You should be looking for the following issues, as well as anything else you deem security-related:

Injection Vulnerabilities, such as:
    Python: os.system('rm -rf ' + userInput) If userInput is not properly sanitized, a malicious user could inject commands.
    C++: Using system() function without proper sanitization can lead to the same issue as the Python example.

Buffer Overflow, such as:
    C++: char buffer[5]; strcpy(buffer, "This string is too long!"); This will overflow the buffer and potentially overwrite important memory.

Insecure Direct Object References, such as:
    Python: eval(userInput) The eval() function can execute arbitrary Python code, so using it on user input is risky.

Security Misconfiguration, such as:
    Python: Leaving debug information in production code, like debug=True in a Flask app.

Sensitive Data Exposure, such as:
    Python: password = "plaintextPassword" Storing passwords in plain text is a bad idea.

Error Handling and Logging, such as:
    Python: except: pass This will silence all exceptions, which can make debugging difficult and hide serious errors.
    C++: catch (...) {{}} This will catch all exceptions, but does nothing with them.

Insecure Cryptographic Storage, such as:
    Python: hashlib.md5(password).hexdigest() MD5 is considered broken for cryptographic use.

Memory Leaks, such as:
    C++: int *p = new int[10]; If you forget to call delete [] p;, the memory is never freed, causing a memory leak.

Thread Safety Issues, such as:
    Python: If multiple threads are modifying a shared data structure without proper locking, race conditions can occur.

Unvalidated Redirects and Forwards, such as:
    Python (Flask): return redirect(request.args.get('next', '/')) If the next parameter is manipulated, it could redirect to an attacker-controlled site.

Cross-Site Scripting (XSS), such as:
    Python: In Django, if you use {{ data }} instead of {{ data|escape }} in a template, it could lead to XSS if data contains script tags.

Improper Authorization or Authentication, such as:
    Python: A Flask route without @login_required decorator can be accessed without authentication.

Unsafe use of pointers, such as:
    C++: int *p = NULL; *p = 1; This is a null pointer dereference, which can cause a crash.

Race Conditions, such as:
    Python: If you have a web app that increases a view count on a page, if two people access it simultaneously, one view might not be counted.

SQL Injection, such as:
    Python: cursor.execute('SELECT * FROM users WHERE name = ' + name) If name is 'admin';--', it can lead to SQL injection.
    C++: Similar to Python, using user controlled input directly in SQL command can lead to SQL injection. It's better to use parameterized queries or prepared statements.

You can safely ignore anything that isn't security related, such as the following:
- Performance: Inefficient algorithm choice.
- Memory Management: Failure to free allocated memory (memory leak).
- Code Correctness: Incorrect conditional statement.
- Maintainability: Monolithic, hard-to-modify functions.
- Reliability: Absence of error handling for critical operations.
"""

CODE_PERFORMANCE_EXAMINATION_TEMPLATE = """You are examining code specifically for performance issues.  You should be looking for the following issues, as well as anything else you deem performance-related:

Inefficient Algorithms
    Python: Using Bubble Sort (O(n^2)) instead of built-in sort() (O(n log n))
    C++: Same issue, using inefficient algorithms over more efficient ones.

Improper Use of Language Constructs
    Python: Using list when set or dict would offer faster lookups.
    C++: Misusing STL algorithms or containers can degrade performance.

Memory Leaks
    C++: int *p = new int; but forgetting to do delete p;

Unnecessary Object Creation
    Python: Creating new strings in a loop, as strings are immutable in Python.
    C++: Creating unnecessary temporary objects.

Excessive Use of Global Variables
    Python/C++: Overuse of global variables which can lead to slower access times and higher memory usage.

Inefficient Database Access
    Python: Using sqlite3 to fetch all rows into memory instead of using an iterator.

Redundant Operations
    Python/C++: Performing the same calculation repeatedly in a loop instead of storing the result.

Lack of Concurrency or Parallelism
    Python: Using a single-threaded approach for IO-bound or high-latency operations instead of asyncio or threading.
    C++: Not making use of std::thread or similar constructs for CPU-bound tasks.

Excessive Use of Recursion
    Python/C++: Implementing a factorial function with recursion instead of iteration can cause stack overflows and is generally slower.

Improper Error Handling
    Python: Using try/except block for control flow can be a performance issue as exceptions in Python are slow.

Blocking I/O Calls
    Python: Using requests.get() without threading can block your program until the request is completed.

Not Using Buffering or Caching
    Python: Not using functools.lru_cache for repeated function calls with the same arguments.
    C++: Not buffering file or network IO.

Lack of Optimization
    Python/C++: Not using language-specific or compiler optimizations.

Inefficient String Concatenation
    Python: Using += in a loop to concatenate strings. It's better to use ''.join(list_of_strings).
    C++: Using + operator to concatenate strings in a loop. It's better to use std::ostringstream or std::string::append.

You can safely ignore anything that isn't performance related, including the following:
- Security: Unsanitized inputs, buffer overflows, etc.
- Memory Management: Failure to free allocated memory (memory leak).
- Code Correctness: Incorrect conditional statement.
- Maintainability: Monolithic, hard-to-modify functions.
- Reliability: Absence of error handling for critical operations.
"""

CODE_MEMORY_EXAMINATION_TEMPLATE = """You are examining code specifically for memory issues.  You should be looking for the following issues, as well as anything else you deem memory-related:

Memory Leaks
    Python: Creating circular references can cause memory leaks. For example:
    ``` python
        class Node:
            def __init__(self):
            self.ref = None
        a = Node()
        b = Node()
        a.ref = b
        b.ref = a
    ```
    C++: Allocating memory and not deleting it can cause a memory leak.
    ``` cpp
        int *ptr = new int;
        // Forgot to call delete ptr;
    ```

Uninitialized Memory Access
    C++: Trying to use a pointer before it's been initialized can lead to undefined behavior.
    ``` cpp
        int *ptr;
        cout << *ptr;  // Uninitialized memory access
    ```

Null Pointer Dereference
    Python: Trying to access an attribute of None.
    ``` python
        a = None
        print(a.some_attribute)  # Will raise AttributeError
    ```
    C++: Trying to use a null pointer can cause a crash.
    ``` cpp
        int *ptr = nullptr;
        cout << *ptr;  // Null pointer dereference
    ```

Double Freeing Memory
    C++: Deleting a pointer twice can lead to undefined behavior.
    ``` cpp
        int *ptr = new int;
        delete ptr;
        delete ptr;  // Double delete
    ```

Buffer Overflows
    C++: Writing beyond the end of an array can cause a buffer overflow.
    ``` cpp
        int arr[10];
        arr[15] = 100;  // Buffer overflow
    ```

Improper Use of Stack Memory
    C++: Declaring a very large array on the stack can cause a stack overflow.
    ``` cpp
        int arr[1000000];  // Possible stack overflow
    ```

Inefficient Memory Use
    Python: Duplicating large data structures unnecessarily.
    ``` python
        large_list = range(1, 1000000)
        duplicate = list(large_list)  # Inefficient memory use
    ```    

Failure to Release Unused Memory
    Python: Holding onto large data structures even when they're not needed.
    ``` python
        large_list = range(1, 1000000)
        # ... rest of code that doesn't use large_list
    ```

Not Accounting for Memory Fragmentation
    C++: Frequent allocations and deallocations of varying sizes can cause fragmentation.
    ``` cpp
        for (int i = 0; i < 1000000; ++i) {{
            char *ptr = new char[i];
            delete[] ptr;
        }}
    ```
    
Improper Thread-Safe Memory Handling
    Python/C++: If multiple threads are manipulating a shared data structure without proper locking, race conditions can occur and lead to various memory issues.

Improper Error Handling
    Python/C++: If exceptions or error conditions cause the program to skip the deallocation of memory, it can lead to memory leaks.

You can safely ignore anything that isn't memory related, including the following:
- Security: Unsanitized inputs, buffer overflows, etc.
- Performance: Inefficient algorithm choice.
- Code Correctness: Incorrect conditional statement.
- Maintainability: Monolithic, hard-to-modify functions.
- Reliability: Absence of error handling for critical operations.
"""

CODE_CORRECTNESS_EXAMINATION_TEMPLATE = """You are examining code specifically for correctness issues.  You should be looking for the following issues, as well as anything else you deem correctness-related:

Off-By-One Errors
    Python/C++: Looping from 1 to len(array) or array.size() instead of len(array) - 1 or array.size() - 1.

Ignoring Return Values
    Python: Ignoring the return value of list.pop() which could indicate the list is empty.
    C++: Ignoring the return value of fread() which could indicate a file read error.

Logic Errors
    Python/C++: Using = (assignment) instead of == (equality) in an if statement.

Null Dereferencing
    Python: Trying to call a method on None.
    C++: Trying to use a null pointer.

Undefined Behavior
    C++: Shifting a negative number left is undefined behavior.

Failing to Handle Errors or Exceptions
    Python: Not catching exceptions from a function that can raise them.
    C++: Not catching exceptions from a function that can throw them.

Type Errors
    Python: Trying to use a string as a number, or vice versa.

Race Conditions
    Python/C++: Two threads incrementing a shared counter without proper locking can lead to a race condition.

Memory Management Errors
    Python: Creating circular references.
    C++: Leaking memory by forgetting to delete it.

Integer Overflow
    Python: Python3 has built-in arbitrary precision, so this is less of a concern.
    C++: Adding two large positive integers can result in a negative number.

Deadlocks
    Python/C++: Two threads each holding a lock and waiting for the other's lock can lead to a deadlock.

Improper Initialization
    Python/C++: Using a variable before it's initialized.

Infinite Loops
    Python/C++: A loop where the exit condition can never be met.

Unreachable Code
    Python/C++: Code after a return statement in a function.

Mutating Variables Unexpectedly
    Python/C++: Changing a global variable inside a function without realizing it's used elsewhere.

Inconsistent State
    Python/C++: An object that has been partially updated, leaving it in an inconsistent state.

You can safely ignore anything that is not correctness related, including the following:
- Security: Unsanitized inputs, buffer overflows, etc.
- Performance: Inefficient algorithm choice.
- Memory Management: Failure to free allocated memory (memory leak).
- Maintainability: Monolithic, hard-to-modify functions.
- Reliability: Absence of error handling for critical operations.
"""

CODE_MAINTAINABILITY_EXAMINATION_TEMPLATE = """You are examining code specifically for maintainability issues.  You should be looking for the following issues, as well as anything else you deem maintainability-related:

Inadequate Documentation
    Python/C++: A function with complex logic but no comments explaining what it does.

Magic Numbers
    Python/C++: Using a number like 3.14159 in a calculation instead of defining a constant like PI.

Long Functions or Methods
    Python/C++: A function that is hundreds of lines long.

Deeply Nested Code
    Python/C++: Having several levels of nested if or for statements.

Duplicate Code
    Python/C++: Having the same logic implemented in several places in the codebase.

Inconsistent Naming Conventions
    Python: Mixing snake_case and camelCase for variable names.
    C++: Mixing camelCase and PascalCase for function names.

Inconsistent Indentation or Formatting
    Python: Mixing spaces and tabs for indentation.
    C++: Not being consistent with the placement of braces {{}}.

Tightly Coupled Code
    Python/C++: Changing a single class or function requires changes in many other parts of the codebase.
    
Poorly Named Variables or Functions
    Python/C++: A variable named a or a function named do_stuff.

Hard-Coded Values
    Python/C++: Hard-coding a file path or a database connection string directly into the code.

Not Following SOLID Principles
    Python/C++: A class that has multiple responsibilities (violating the Single Responsibility Principle).
    
Code Clutter
    Python/C++: Leaving in commented-out code or unused variables.
    
Lack of Structure or Organization
    Python/C++: A file with several hundred lines of code with no clear organization or structure.
    
Over-complicated Expressions or Logic
    Python: Using a complex list comprehension when a simple for loop would be more readable.
    C++: Using an intricate combination of bitwise operations when a straightforward arithmetic operation would work.

You can safely ignore anything that isn't maintainability related, including the following:
- Security: Unsanitized inputs, buffer overflows, etc.
- Performance: Inefficient algorithm choice.
- Memory Management: Failure to free allocated memory (memory leak).
- Code Correctness: Incorrect conditional statement.
- Reliability: Absence of error handling for critical operations.
"""

CODE_RELIABILITY_EXAMINATION_TEMPLATE = """You are examining code specifically for reliability issues.  You should be looking for the following issues, as well as anything else you deem reliability-related:

Error Handling
    Python: Not catching exceptions from a function that can raise them.
    C++: Not catching exceptions from a function that can throw them.

Uninitialized Variables
    Python: Using a variable before it's initialized.
    C++: Using a pointer before it's initialized.

Lack of Fault Tolerance
    Python/C++: Not handling exceptions from a database operation, leading to a crash when the database is unavailable.

Resource Exhaustion
    Python/C++: Not handling out of memory errors when creating large data structures.

Improper Shutdown
    Python/C++: Not properly closing a file or network connection when done with it.

Thread Safety Issues
    Python/C++: A function that modifies a global variable without proper locking.

Poor Error Messages
    Python/C++: Catching an exception and logging a generic message, losing the original error information.

You can safely ignore anything that isn't reliability related, including the following:
- Security: Unsanitized inputs, buffer overflows, etc.
- Performance: Inefficient algorithm choice.
- Memory Management: Failure to free allocated memory (memory leak).
- Code Correctness: Incorrect conditional statement.
- Maintainability: Monolithic, hard-to-modify functions.
"""