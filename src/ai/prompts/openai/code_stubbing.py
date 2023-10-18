C_STUBBING_TEMPLATE = """Please take the following code and create a stub for it.  The goal is to have the stub you create be able to be used in place of the original code, and have the same behavior as the original code, only with a fake implementation.

--- BEGIN CODE TO STUB ---
{code}
--- END CODE TO STUB ---
{stub_dependencies_template}
Return only the stubbed code, nothing else.

In the stubbed file, we need to make sure we handle the various defines, as well.  For example, if we have defined a include guard in the original file, we need to make sure to define it in the stubbed file as well, but with some modifications.

If the original file contained the following include guard:
--- BEGIN EXAMPLE INPUT ---
// Include guard for the original file
#ifndef _MY_FILE_H
#define _MY_FILE_H

...
--- END EXAMPLE INPUT ---

The stubbed file output should contain a modified include guard for the stubbed file AND the original #define:
--- BEGIN EXAMPLE OUTPUT ---
// Create the include guard for stubbed file itself
#ifndef _MY_FILE_STUB_H
#define _MY_FILE_STUB_H

// Define the original file, so that files depending on this stubbed file do not 
#define _MY_FILE_H

...
--- END EXAMPLE OUTPUT ---

Include comment placeholders where stub functionality is needed. For instance, where a value must be returned by a stubbed function, insert a comment such as "Your stub code goes here".  Additionally, set all of the member variables in the stub code to their default values.

AI: Sure, here is the stubbed code (and only the code):
"""

STUB_DEPENDENCIES_TEMPLATE = """
Since there are child dependencies in the code you will be stubbing, I have stubbed out those child dependencies for you.  You can use the following stubbed dependencies in your stubbed code.

Child Dependencies:
{stub_dependencies}

"""