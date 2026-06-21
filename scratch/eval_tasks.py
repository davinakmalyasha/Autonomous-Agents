# 5th Generation Evaluation Task Definitions (Adaptive Consulting Intelligence)
# Rewritten to represent real-world daily coding requests and developer tasks.
# Simplified prompts to be human-like, high-level requests, with NO filenames mentioned in prompts.

UNIT_TASKS = [
    {
        "id": 1,
        "name": "Thread-Safe Concurrent Cache (LRU & TTL)",
        "prompt": "Build a thread-safe concurrent in-memory cache in Python. It needs to support LRU eviction, TTL expiration for keys, and backing up / restoring to a JSON file. Write a set of tests to verify it works correctly under concurrent thread pressure.",
        "verify_cmd": "python -m pytest test_concurrent_cache.py",
        "expected_files": ["concurrent_cache.py", "test_concurrent_cache.py"]
    },
    {
        "id": 2,
        "name": "Rich Markdown Compiler to Semantic HTML",
        "prompt": "Write a markdown to HTML compiler in Python. It should support headings, bold/italic inline styling, nested bullet and numbered lists, and full markdown tables. Create unit tests to check all of these formatting rules.",
        "verify_cmd": "python -m pytest test_markdown_compiler.py",
        "expected_files": ["markdown_compiler.py", "test_markdown_compiler.py"]
    },
    {
        "id": 3,
        "name": "Custom Async Event Loop & Task Runner",
        "prompt": "I want a custom asynchronous event loop and task runner in Python without using the built-in asyncio library. It needs to run coroutines/generators, handle non-blocking sleeps, and support offloading blocking tasks to a thread pool. Write tests to verify it works.",
        "verify_cmd": "python -m pytest test_custom_event_loop.py",
        "expected_files": ["custom_event_loop.py", "test_custom_event_loop.py"]
    },
    {
        "id": 4,
        "name": "Sliding Window Log Rate Limiter",
        "prompt": "Create a sliding window log rate limiter in Python that limits client requests (supporting multiple client keys) and persists request logs to a SQLite database. Write tests to verify the limits.",
        "verify_cmd": "python -m pytest test_rate_limiter.py",
        "expected_files": ["rate_limiter.py", "test_rate_limiter.py"]
    },
    {
        "id": 5,
        "name": "In-Memory Relational Engine",
        "prompt": "Implement an in-memory SQL-like relational engine in Python. It should parse custom query structures, execute INNER and LEFT joins, and optimize the execution plan (e.g. by filtering before joining). Write tests to verify its correctness.",
        "verify_cmd": "python -m pytest test_query_engine.py",
        "expected_files": ["query_engine.py", "test_query_engine.py"]
    },
    {
        "id": 6,
        "name": "Time-Expanded A* Pathfinder",
        "prompt": "Implement a time-expanded A* pathfinding solver in Python that finds the shortest path on a 2D grid while avoiding static and dynamic (moving) obstacles over time. Add tests to verify dynamic obstacle avoidance.",
        "verify_cmd": "python -m pytest test_astar_3d.py",
        "expected_files": ["astar_3d.py", "test_astar_3d.py"]
    },
    {
        "id": 7,
        "name": "Git Simulator Engine",
        "prompt": "Build a simple local version control simulator in Python. It should support git-like commands: initialize a repo, add/stage files, commit changes, show status, and checkout past commits. Write tests to verify commits and rollbacks.",
        "verify_cmd": "python -m pytest test_vcs_engine.py",
        "expected_files": ["vcs_engine.py", "test_vcs_engine.py"]
    },
    {
        "id": 8,
        "name": "DAG Execution Engine",
        "prompt": "Write a task execution engine in Python that runs tasks with dependencies concurrently using a thread pool. It must check for cycles in the dependency graph and handle task failures. Test it with unit tests.",
        "verify_cmd": "python -m pytest test_dag_engine.py",
        "expected_files": ["dag_engine.py", "test_dag_engine.py"]
    }
]

INTERACTIVE_TASKS = [
    {
        "id": 9,
        "name": "Resilient Client",
        "type": "self_heal",
        "prompt": "Create a resilient HTTP client wrapper in Python that handles timeouts, connection errors, and retries failed requests with exponential backoff. It should also implement a circuit breaker pattern. Write tests to verify this.",
        "verify_cmd": "python -m pytest test_resilient_client.py",
        "expected_files": ["resilient_client.py", "test_resilient_client.py"]
    },
    {
        "id": 10,
        "name": "Secure Password Vault",
        "type": "pivot",
        "prompt": "Design a secure password storage manager in Python that encrypts and decrypts credentials. Show me the design choices first.",
        "pivot_prompt": "Now, add a key-derivation iteration-backoff mechanism to the PasswordVault to prevent brute-force attacks. Each failed attempt should double the backoff/work. Update the code and tests to verify this.",
        "verify_cmd": "python -m pytest test_vault.py",
        "expected_files": ["vault.py", "test_vault.py"]
    },
    {
        "id": 11,
        "name": "HTTP Router with Middlewares",
        "type": "carryover",
        "prompt": "I need a custom HTTP request router in Python that matches methods and paths, supporting params like `/users/{id}`. Propose design choices.",
        "followup_prompt": "Now add global and route-specific middleware chain support. Middlewares should take request and next_fn. Update the router and write tests.",
        "verify_cmd": "python -m pytest test_router.py",
        "expected_files": ["router.py", "test_router.py"]
    },
    {
        "id": 12,
        "name": "Dynamic Port Scanning Server",
        "type": "port_conflict",
        "prompt": "Start a simple HTTP server in Python with a `/health` endpoint. If port 8000 is occupied, it should scan for a free port, start there, and save the port to a JSON file.",
        "verify_cmd": "",
        "expected_files": ["web_server.py"]
    },
    {
        "id": 13,
        "name": "Database Schema Compiler",
        "type": "vague_probe",
        "prompt": "I need a compiler that parses custom schema DSL strings and outputs SQL DDL statements. Propose some design choices.",
        "verify_cmd": "",
        "expected_files": ["schema_plan.md"]
    },
    {
        "id": 14,
        "name": "Billing Refactoring",
        "type": "refactor",
        "prompt": "Refactor the messy billing code. Show me the architectural options.",
        "verify_cmd": "python -m pytest test_billing.py",
        "expected_files": ["billing.py", "test_billing.py", "domain/order.py", "domain/tax.py", "domain/discount.py", "domain/invoice.py"]
    },
    {
        "id": 15,
        "name": "A* Pathfinding Solver",
        "type": "resume",
        "prompt": "Implement a 2D A* pathfinder in Python that finds the shortest path on a grid of obstacles. Write tests.",
        "verify_cmd": "python -m pytest test_astar.py",
        "expected_files": ["astar.py", "test_astar.py"]
    }
]
