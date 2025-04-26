# Engineering Principles for inXeption Codebase

## Core Principles

1. **NO DEFENSIVE CODING**
   ```python
   # WRONG: Hiding potential errors
   data = config.get('key', default_value)

   # RIGHT: Let errors surface
   data = config['key']  # Will raise KeyError if missing - GOOD!
   ```
   Errors are valuable signals of design problems. Let them surface.

2. **SINGLE QUOTES ALWAYS**
   ```python
   # WRONG
   message = "This is wrong"

   # RIGHT
   message = 'This is correct'

   # DOCSTRINGS TOO
   '''This is a correct docstring'''
   ```

3. **PYTHONIC CONSTRUCTS**
   ```python
   # WRONG: C-style iteration
   result = []
   for item in items:
       result.append(process(item))

   # RIGHT: List comprehension
   result = [process(item) for item in items]
   ```

4. **ARCHITECTURAL INTEGRITY**

   Each agent modifying this codebase creates a risk of entropy. After 10 agents make
   small "improvements," the codebase can lose its conceptual integrity entirely.

   ZOOM OUT BEFORE CODING:
   - Study the overall architecture and patterns
   - Understand component responsibilities and boundaries
   - Consider: "If every agent made changes like mine, would the codebase improve or degrade?"

   You are responsible for leaving the codebase MORE coherent than you found it, not less.
   Fix structural problems, don't just patch symptoms.

   ```python
   # WRONG: Quick fix approach
   # "I'll just add this flag to work around the issue"
   def process(data, skip_validation=False):
       if not skip_validation:
           validate(data)  # Added a flag to bypass validation

   # RIGHT: Address the root cause
   # "Why is validation failing? Let's fix the actual problem"
   def process(data):
       validate(data)  # Fix validation logic instead of bypassing it
   ```

5. **FAIL FAST AND VISIBLY**
   ```python
   # WRONG: Suppressing exceptions
   try:
       risky_operation()
   except Exception:
       pass  # Hiding problems

   # RIGHT: Let exceptions propagate
   risky_operation()  # If it fails, we WANT to know
   ```

Remember: Your job is to move the codebase toward an ideal state with each change.
Multiple agents will touch this code - make sure your changes are creating order, not chaos.

6. **GIT WORKFLOW**

   NEVER make a git commit unless instructed.

   When you DO make a git commit, chances are that the precommit hooks will auto-apply whitespace fixes. If that's all they did, you'll have to restage all the files they changed and complete the commit. Do NOT try to fix the whitespace yourself -- it's already done!
   Any greater issue, you'll have to come back to the human to discuss.
